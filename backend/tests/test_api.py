"""Offline regression tests: python -m unittest discover -s backend/tests -p test_api.py."""

import io
import json
import os
import tempfile
import unittest
import wave
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import UUID

# Override inherited credentials before config loads either dotenv file.
os.environ["VERCEL"] = "1"
os.environ["GEMINI_API_KEY"] = ""

with patch("socket.socket.connect", side_effect=AssertionError("Network disabled")):
    from app import app

import cv2
import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

import analyzers.rag_verifier as rag_module
import analyzers.text_analyzer as text_module
from core.config import settings
from models.schemas import AnalysisResult, HealthResponse


class APITests(unittest.TestCase):
    text = "Studies show that regular exercise improves cardiovascular health."
    context = "<b>Regular exercise</b> improves cardiovascular health."

    def setUp(self):
        # Windows asyncio creates a loopback socket pair when starting its loop.
        self.client = self.enterContext(TestClient(app))
        # Requests use ASGI in-process; block network after loop initialization.
        network = self.enterContext(patch(
            "socket.socket.connect", side_effect=AssertionError("Network disabled")
        ))
        dns = self.enterContext(patch(
            "socket.getaddrinfo", side_effect=AssertionError("DNS disabled")
        ))
        self.addCleanup(network.assert_not_called)
        self.addCleanup(dns.assert_not_called)
        self.enterContext(patch.object(text_module, "gemini_provider", SimpleNamespace(gemini_client=None)))
        self.enterContext(patch.object(rag_module, "gemini_provider", SimpleNamespace(gemini_client=None)))
        self.wikipedia = self.enterContext(patch.object(
            rag_module.rag_verifier, "_query_wikipedia", return_value=self.context
        ))
        self.duckduckgo = self.enterContext(patch.object(
            rag_module.rag_verifier, "_query_duckduckgo",
            side_effect=AssertionError("Unexpected search fallback"),
        ))
        self.addCleanup(self.duckduckgo.assert_not_called)

    def fake_client(self, module, payload):
        generate = Mock(return_value=SimpleNamespace(text=json.dumps(payload)))
        self.enterContext(patch.object(
            module, "gemini_provider",
            SimpleNamespace(gemini_client=SimpleNamespace(models=SimpleNamespace(generate_content=generate))),
        ))
        return generate

    def assert_result(self, response, content_type):
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        AnalysisResult.model_validate_json(response.content, strict=True)
        self.assertEqual(set(body), set(AnalysisResult.model_fields))
        self.assertEqual(body["content_type"], content_type)
        UUID(body["id"])
        datetime.fromisoformat(body["timestamp"])
        if content_type == "text" and body["verdict"] != "inconclusive":
            self.assertGreaterEqual(body["trust_score"], 0)
            self.assertLessEqual(body["trust_score"], 100)
            self.assertIsInstance(body["is_authentic"], bool)
        else:
            self.assertIsNone(body["trust_score"])
            self.assertIsNone(body["is_authentic"])
            self.assertIsNone(body["risk_level"])
            self.assertEqual(body["verdict"], "inconclusive")
            if content_type != "text":
                self.assertEqual(body["provenance"][0]["status"], "not_configured")
        self.assertTrue(body["summary"])
        self.assertTrue(body["explanation"])
        self.assertGreaterEqual(body["processing_time_ms"], 0)
        for detail in body["details"]:
            self.assertEqual(set(detail), {"category", "finding", "confidence", "severity"})
            self.assertTrue(detail["finding"])
            self.assertGreaterEqual(detail["confidence"], 0)
            self.assertLessEqual(detail["confidence"], 1)
        return body

    def assert_generation(self, generate, temperature, tokens):
        generate.assert_called_once()
        kwargs = generate.call_args.kwargs
        self.assertEqual(kwargs["model"], settings.GEMINI_MODEL)
        self.assertIn("cardiovascular health", kwargs["contents"])
        self.assertEqual(kwargs["config"].response_mime_type, "application/json")
        self.assertEqual(kwargs["config"].temperature, temperature)
        self.assertEqual(kwargs["config"].max_output_tokens, tokens)

    def test_health_and_safe_configuration(self):
        self.assertEqual(os.environ["VERCEL"], "1")
        self.assertEqual(settings.GEMINI_API_KEY, "")
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        HealthResponse.model_validate(body, strict=True)
        self.assertEqual(body["status"], "healthy")
        self.assertEqual(body["app_name"], settings.APP_NAME)
        self.assertEqual(body["version"], settings.APP_VERSION)
        self.assertEqual(body["analyzers"], dict.fromkeys([
            "text_analyzer", "image_analyzer", "video_analyzer",
            "audio_analyzer", "ocr_engine", "rag_verifier",
        ], "active"))

    def test_vercel_requirements_are_flat_and_match_backend(self):
        root = Path(__file__).resolve().parents[2]
        requirements = []
        for path in (root / "requirements.txt", root / "backend/requirements.txt"):
            lines = [line.strip() for line in path.read_text().splitlines()
                     if line.strip() and not line.lstrip().startswith("#")]
            self.assertFalse(any(line.startswith("-") for line in lines))
            requirements.append(lines)
        self.assertEqual(requirements[0], requirements[1])

    def test_text_success_schema_model_and_config(self):
        finding = {"category": "AI Generation", "finding": "Offline model finding",
                   "confidence": 0.25, "severity": "low"}
        generate = self.fake_client(text_module, {
            "details": [finding],
            "scores": {"ai_score": 0.25, "scam_score": 0.1, "misinfo_score": 0.05},
        })
        with patch.object(settings, "GEMINI_MODEL", "offline-test-model"):
            body = self.assert_result(self.client.post("/api/analyze/text", json={
                "text": self.text, "check_claims": False,
            }), "text")
            self.assert_generation(generate, 0.1, 1500)
        self.assertIn(finding, body["details"])
        self.assertEqual(body["extracted_text"], self.text)
        self.wikipedia.assert_not_called()

    def test_text_all_toggles_off(self):
        text_generate = self.fake_client(text_module, {})
        rag_generate = self.fake_client(rag_module, {})
        body = self.assert_result(self.client.post("/api/analyze/text", json={
            "text": self.text, "check_claims": False,
            "check_ai_generated": False, "check_scam": False,
        }), "text")
        self.assertEqual(body["details"], [])
        self.assertEqual(body["claims_verified"], 0)
        self.assertEqual(body["claims_flagged"], 0)
        text_generate.assert_not_called()
        rag_generate.assert_not_called()
        self.wikipedia.assert_not_called()

    def test_rag_verdicts(self):
        for verdict, verified, flagged, severity in [
            ("supported", 1, 0, "low"),
            ("refuted", 0, 1, "high"),
            ("uncertain", 0, 0, "medium"),
        ]:
            with self.subTest(verdict=verdict):
                generate = self.fake_client(rag_module, {
                    "verdict": verdict, "reasoning": "Offline context evaluation",
                })
                body = self.assert_result(self.client.post("/api/analyze/text", json={
                    "text": self.text, "check_ai_generated": False, "check_scam": False,
                }), "text")
                self.assertEqual(body["claims_verified"], verified)
                self.assertEqual(body["claims_flagged"], flagged)
                self.assertEqual(len(body["details"]), 1)
                self.assertEqual(body["details"][0]["severity"], severity)
                self.assertIn("Offline context evaluation", body["details"][0]["finding"])
                self.assert_generation(generate, 0.0, 300)
                self.assertNotIn("<b>", generate.call_args.kwargs["contents"])
        self.assertEqual(self.wikipedia.call_count, 3)

    def test_llm_failures_are_sanitized(self):
        secret = "fake-api-key-not-a-real-credential"
        exception_message = "private upstream exception " + secret
        for module in (text_module, rag_module):
            for failure in ("malformed_json", "exception"):
                with self.subTest(module=module.__name__, failure=failure):
                    generate = self.fake_client(module, {})
                    if failure == "malformed_json":
                        generate.return_value = SimpleNamespace(text="not JSON " + secret)
                    else:
                        generate.side_effect = RuntimeError(exception_message)
                    is_rag = module is rag_module
                    output = io.StringIO()
                    with redirect_stdout(output), redirect_stderr(output):
                        response = self.client.post("/api/analyze/text", json={
                            "text": self.text, "check_claims": is_rag,
                            "check_ai_generated": not is_rag, "check_scam": False,
                        })
                    body = self.assert_result(response, "text")
                    self.assertEqual(body["claims_verified"], 0)
                    if is_rag:
                        self.assertIsNone(body["trust_score"])
                        self.assertIsNone(body["risk_level"])
                        self.assertEqual(body["verdict"], "inconclusive")
                    self.assertTrue(any(
                        "unavailable" in detail["finding"] for detail in body["details"]
                    ))
                    self.assertNotIn(secret, response.text + output.getvalue())
                    self.assertNotIn(exception_message, response.text + output.getvalue())
                    generate.assert_called_once()

    def test_absent_client_does_not_verify_claims(self):
        body = self.assert_result(self.client.post("/api/analyze/text", json={
            "text": self.text,
        }), "text")
        self.assertEqual(body["claims_verified"], 0)
        self.assertEqual(body["claims_flagged"], 0)
        self.assertTrue(any("not configured" in d["finding"] for d in body["details"]))
        self.assertTrue(any("Claim unverified" in d["finding"] for d in body["details"]))
        self.wikipedia.assert_called_once()

    def test_missing_retrieval_is_not_a_flagged_claim(self):
        self.wikipedia.return_value = None
        self.duckduckgo.side_effect = None
        self.duckduckgo.return_value = None
        body = self.assert_result(self.client.post("/api/analyze/text", json={
            "text": self.text, "check_ai_generated": False, "check_scam": False,
        }), "text")
        self.assertEqual(body["claims_flagged"], 0)
        self.assertEqual(body["verdict"], "inconclusive")
        self.duckduckgo.assert_called_once()
        self.duckduckgo.reset_mock()

    def test_real_png_image(self):
        buffer = io.BytesIO()
        Image.new("RGB", (128, 96), color=(80, 120, 160)).save(buffer, format="PNG")
        with patch("routers.image.ocr_engine.extract_text", return_value=None):
            body = self.assert_result(self.client.post("/api/analyze/image", files={
                "file": ("sample.png", buffer.getvalue(), "image/png"),
            }), "image")
        self.assertTrue(body["details"])
        self.assertIsNone(body["extracted_text"])
        self.assertTrue(any(d["category"] != "System Error" for d in body["details"]))

    def test_real_sine_wave_audio(self):
        rate = 22050
        samples = (np.sin(2 * np.pi * 440 * np.arange(rate * 2) / rate) * 12000).astype("<i2")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sine.wav"
            with wave.open(str(path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(rate)
                wav.writeframes(samples.tobytes())
            with path.open("rb") as audio:
                body = self.assert_result(self.client.post("/api/analyze/audio", files={
                    "file": (path.name, audio, "audio/wav"),
                }), "audio")
        self.assertTrue(body["details"])
        self.assertTrue(any(d["category"] != "System Error" for d in body["details"]))

    def test_real_mp4_video_frames(self):
        count = 6
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mp4"
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 6, (96, 64))
            try:
                self.assertTrue(writer.isOpened(), "OpenCV MP4 encoder is required")
                for index in range(count):
                    frame = np.full((64, 96, 3), 80 + index * 3, dtype=np.uint8)
                    cv2.rectangle(frame, (index * 5, 20), (index * 5 + 15, 40), (30, 140, 200), -1)
                    writer.write(frame)
            finally:
                writer.release()
            with path.open("rb") as video:
                body = self.assert_result(self.client.post("/api/analyze/video", files={
                    "file": (path.name, video, "video/mp4"),
                }), "video")
        self.assertEqual(body["total_frames"], count)
        self.assertEqual(len(body["frame_analyses"]), count)
        self.assertEqual([f["frame_number"] for f in body["frame_analyses"]], list(range(count)))
        self.assertIsNone(body["deepfake_frames"])
        for frame in body["frame_analyses"]:
            self.assertIsNone(frame["deepfake_probability"])
            self.assertIsNone(frame["is_deepfake"])
            self.assertTrue(frame["details"])

    def test_invalid_media_upload_types(self):
        for media in ("image", "audio", "video"):
            with self.subTest(media=media):
                response = self.client.post("/api/analyze/" + media, files={
                    "file": ("invalid.txt", b"not a media upload", "text/plain"),
                })
                self.assertEqual(response.status_code, 415)
                self.assertIn("Unsupported file type", response.json()["detail"])

    def test_unknown_api_routes_are_not_spa(self):
        for path in ("/api", "/api/not-a-real-route", "/api/analyze/unknown"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": "Not Found"})

    def test_frontend_root_and_spa(self):
        index = Path(__file__).resolve().parents[2] / "public" / "index.html"
        expected = index.read_bytes()
        for path in ("/", "/dashboard/offline-test"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("text/html", response.headers["content-type"])
                self.assertEqual(response.content, expected)
                self.assertIn('<div id="root">', response.text)


if __name__ == "__main__":
    unittest.main()
