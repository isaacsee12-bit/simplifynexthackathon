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
    context = "Regular exercise improves cardiovascular health."

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
            rag_module.rag_verifier, "_query_wikipedia", return_value=[{
                "title": "Exercise research", "url": "https://reuters.com/science/exercise",
                "excerpt": self.context,
            }]
        ))
        self.duckduckgo = self.enterContext(patch.object(
            rag_module.rag_verifier, "_query_duckduckgo",
            return_value=[{
                "title": "Independent research", "url": "https://bbc.com/news/exercise",
                "excerpt": self.context,
            }],
        ))

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
            self.assertIsNone(body["is_authentic"])
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

    def investigation_client(self, stance="supported"):
        generate = self.fake_client(rag_module, {})

        def respond(**kwargs):
            schema = kwargs["config"].response_schema["title"]
            if schema == "_Claims":
                payload = {"claims": [self.text]}
            elif schema == "_Plan":
                payload = {"tool": "wikipedia", "query": "exercise cardiovascular health"}
            else:
                self.assertEqual(schema, "_Assessment")
                data = json.loads(kwargs["contents"].split("DATA: ", 1)[1])
                payload = {
                    "citations": [{"evidence_id": source["id"], "quote": self.context,
                                   "stance": stance} for source in data["sources"]],
                    "reasoning": "Offline context evaluation", "uncertainties": [],
                    "followup": {"tool": "duckduckgo", "query": "exercise independent evidence"},
                }
            return SimpleNamespace(text=json.dumps(payload))

        generate.side_effect = respond
        return generate

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
        self.assertEqual(body["analyzers"]["text_analyzer"], "local_heuristics")
        self.assertEqual(body["analyzers"]["rag_verifier"], "not_configured")
        self.assertEqual(body["analyzers"]["gemini"], "not_configured")
        self.assertIn(body["analyzers"]["ocr_engine"], ("available", "unavailable"))
        self.assertNotIn("*", settings.CORS_ORIGINS)

    def test_vercel_requirements_are_flat_and_match_backend(self):
        root = Path(__file__).resolve().parents[2]
        requirements = []
        for path in (root / "requirements.txt", root / "backend/requirements.txt"):
            lines = [line.strip() for line in path.read_text().splitlines()
                     if line.strip() and not line.lstrip().startswith("#")]
            self.assertFalse(any(line.startswith("-") for line in lines))
            requirements.append(lines)
        self.assertEqual(requirements[0], requirements[1])

    def test_text_local_checks_never_use_unsourced_llm(self):
        generate = self.fake_client(text_module, {})
        text = "In conclusion, act now! Urgent: send money and your password."
        for ai, scam, categories in [
            (True, False, {"AI Generation"}),
            (False, True, {"Scam Phishing"}),
            (True, True, {"AI Generation", "Scam Phishing"}),
        ]:
            with self.subTest(ai=ai, scam=scam):
                body = self.assert_result(self.client.post("/api/analyze/text", json={
                    "text": text, "check_claims": False,
                    "check_ai_generated": ai, "check_scam": scam,
                }), "text")
                self.assertEqual({d["category"] for d in body["details"]}, categories)
                self.assertIsNotNone(body["trust_score"])
                self.assertEqual(body["extracted_text"], text)
                self.assertIsNone(body["investigation"])
                self.assertIn("Factual claims were not checked.", body["uncertainties"])
        generate.assert_not_called()
        self.wikipedia.assert_not_called()
        self.duckduckgo.assert_not_called()

    def test_text_all_toggles_off(self):
        text_generate = self.fake_client(text_module, {})
        rag_generate = self.fake_client(rag_module, {})
        body = self.assert_result(self.client.post("/api/analyze/text", json={
            "text": self.text, "check_claims": False,
            "check_ai_generated": False, "check_scam": False,
        }), "text")
        self.assertEqual(body["details"], [])
        self.assertIsNone(body["investigation"])
        self.assertEqual(body["verdict"], "inconclusive")
        self.assertEqual(body["claims_verified"], 0)
        self.assertEqual(body["claims_flagged"], 0)
        text_generate.assert_not_called()
        rag_generate.assert_not_called()
        self.wikipedia.assert_not_called()
        self.duckduckgo.assert_not_called()

    def test_investigation_verdicts_and_structured_provider_contract(self):
        for verdict, verified, flagged, severity in [
            ("supported", 1, 0, "low"),
            ("refuted", 0, 1, "high"),
            ("uncertain", 0, 0, "medium"),
        ]:
            with self.subTest(verdict=verdict):
                generate = self.investigation_client(verdict)
                with patch.object(settings, "GEMINI_MODEL", "offline-test-model"):
                    body = self.assert_result(self.client.post("/api/analyze/text", json={
                        "text": self.text, "check_ai_generated": False, "check_scam": False,
                    }), "text")
                self.assertEqual(body["claims_verified"], verified)
                self.assertEqual(body["claims_flagged"], flagged)
                self.assertEqual(len(body["details"]), 1)
                self.assertEqual(body["details"][0]["severity"], severity)
                self.assertIn("Offline context evaluation", body["details"][0]["finding"])
                investigation = body["investigation"]
                claim = investigation["claims"][0]
                self.assertEqual(claim["text"], self.text)
                self.assertEqual(claim["verdict"], verdict)
                self.assertEqual({e["publisher"] for e in claim["evidence"]}, {"Reuters", "BBC"})
                self.assertEqual([e["id"] for e in claim["evidence"]], ["c1-e1", "c1-e2"])
                self.assertTrue(all(e["retrieved_at"] and e["excerpt"] == self.context
                                    for e in claim["evidence"]))
                self.assertEqual(body["recommended_action"], investigation["recommended_action"])
                self.assertTrue(set(investigation["uncertainties"]) <= set(body["uncertainties"]))
                trace = investigation["trace"]
                self.assertEqual([e["sequence"] for e in trace], list(range(1, len(trace) + 1)))
                self.assertTrue({"plan", "act", "observe", "adapt", "conclude"} <=
                                {e["phase"] for e in trace})
                self.assertEqual(generate.call_count, 4)
                for call in generate.call_args_list:
                    self.assertEqual(call.kwargs["model"], "offline-test-model")
                    config = call.kwargs["config"]
                    self.assertEqual(config.response_mime_type, "application/json")
                    self.assertEqual(config.temperature, 0)
                    self.assertEqual(config.max_output_tokens, 1800)
                    self.assertEqual(config.http_options.retry_options.attempts, 1)
                if verdict == "uncertain":
                    self.assertEqual(body["verdict"], "inconclusive")
                else:
                    self.assertIsNotNone(body["trust_score"])
        self.assertEqual(self.wikipedia.call_count, 3)
        self.assertEqual(self.duckduckgo.call_count, 3)

    def test_investigation_provider_failures_are_sanitized(self):
        secret = "fake-api-key-not-a-real-credential"
        exception_message = "private upstream exception " + secret
        for schema in (rag_module._Claims, rag_module._Plan, rag_module._Assessment):
            for failure in ("malformed_json", "exception"):
                with self.subTest(schema=schema.__name__, failure=failure):
                    generate = self.investigation_client()
                    respond = generate.side_effect

                    def fail(**kwargs):
                        if kwargs["config"].response_schema["title"] == schema.__name__:
                            if failure == "malformed_json":
                                return SimpleNamespace(text="not JSON " + secret)
                            raise RuntimeError(exception_message)
                        return respond(**kwargs)

                    generate.side_effect = fail
                    output = io.StringIO()
                    with redirect_stdout(output), redirect_stderr(output):
                        response = self.client.post("/api/analyze/text", json={
                            "text": self.text, "check_claims": True,
                            "check_ai_generated": False, "check_scam": False,
                        })
                    body = self.assert_result(response, "text")
                    self.assertEqual(body["claims_flagged"], 0)
                    if schema is rag_module._Assessment:
                        self.assertEqual(body["claims_verified"], 0)
                        self.assertEqual(body["verdict"], "inconclusive")
                    else:
                        # Extraction/planning failures can recover through explicit fallbacks.
                        self.assertEqual(body["claims_verified"], 1)
                    self.assertTrue(any(
                        "unavailable" in event["message"] for event in body["investigation"]["trace"]
                    ))
                    self.assertNotIn(secret, response.text + output.getvalue())
                    self.assertNotIn(exception_message, response.text + output.getvalue())
                    self.assertTrue(any(call.kwargs["config"].response_schema["title"] == schema.__name__
                                        for call in generate.call_args_list))

    def test_absent_client_does_not_verify_claims(self):
        body = self.assert_result(self.client.post("/api/analyze/text", json={
            "text": self.text,
        }), "text")
        self.assertEqual(body["claims_verified"], 0)
        self.assertEqual(body["claims_flagged"], 0)
        self.assertEqual(body["verdict"], "inconclusive")
        claim = body["investigation"]["claims"][0]
        self.assertEqual(claim["verdict"], "uncertain")
        self.assertEqual(claim["evidence"], [])
        self.assertTrue(any("not configured" in u for u in claim["uncertainties"]))
        self.assertTrue(any("fallback" in u for u in body["uncertainties"]))
        self.wikipedia.assert_not_called()
        self.duckduckgo.assert_not_called()

    def test_missing_retrieval_is_not_a_flagged_claim(self):
        generate = self.investigation_client()
        self.wikipedia.return_value = []
        self.duckduckgo.return_value = []
        body = self.assert_result(self.client.post("/api/analyze/text", json={
            "text": self.text, "check_ai_generated": False, "check_scam": False,
        }), "text")
        self.assertEqual(body["claims_flagged"], 0)
        self.assertEqual(body["verdict"], "inconclusive")
        self.assertEqual(body["claims_verified"], 0)
        self.assertEqual(body["investigation"]["claims"][0]["evidence"], [])
        self.assertEqual(generate.call_count, 2)
        self.wikipedia.assert_called_once()
        self.duckduckgo.assert_called_once()

    def test_single_publisher_cannot_verify_or_refute(self):
        for stance in ("supported", "refuted"):
            with self.subTest(stance=stance):
                self.investigation_client(stance)
                self.duckduckgo.return_value[0]["url"] = "https://reuters.com/another-story"
                body = self.assert_result(self.client.post("/api/analyze/text", json={
                    "text": self.text, "check_ai_generated": False, "check_scam": False,
                }), "text")
                self.assertEqual(body["claims_verified"], 0)
                self.assertEqual(body["claims_flagged"], 0)
                self.assertEqual(body["verdict"], "inconclusive")
                claim = body["investigation"]["claims"][0]
                self.assertEqual(claim["verdict"], "uncertain")
                self.assertEqual(len(claim["evidence"]), 2)
                self.assertIn("Abstain", body["recommended_action"])

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
