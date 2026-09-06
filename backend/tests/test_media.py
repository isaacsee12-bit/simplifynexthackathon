"""Offline media payload, provider failure, and SDK serialization regressions."""

import asyncio
import base64
import io
import json
import os
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

with patch.dict(os.environ, {"VERCEL": "1", "GEMINI_API_KEY": ""}), \
        patch("socket.socket.connect", side_effect=AssertionError("Network disabled")):
    from app import app

import cv2
import httpx
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from google import genai
from google.genai import types
from analyzers.media_analyzer import request_gemini
from analyzers.audio_analyzer import audio_analyzer
from core import gemini_client as provider
from core.config import settings
from core.trust_score import trust_engine
from models.schemas import AnalysisCoverage, AnalysisDetail, RiskLevel


PAYLOAD = {"verdict": "suspicious", "summary": "A visible boundary needs review.",
           "observations": ["An inconsistent boundary is visible in the supplied sample."],
           "limitations": ["This sample cannot establish the source or authenticity."]}


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.client = self.enterContext(TestClient(app))
        self.generate = Mock(return_value=SimpleNamespace(text=json.dumps(PAYLOAD), candidates=[], prompt_feedback=None))
        self.enterContext(patch.object(provider, "gemini_client", SimpleNamespace(models=SimpleNamespace(generate_content=self.generate))))
        self.enterContext(patch.object(settings, "GEMINI_MODEL", "offline-media-model"))
        self.enterContext(patch("routers.image.ocr_engine.extract_text", return_value=None))
        for target in ("socket.socket.connect", "socket.getaddrinfo"):
            blocked = self.enterContext(patch(target, side_effect=AssertionError("Network disabled")))
            self.addCleanup(blocked.assert_not_called)

    def upload(self, kind, data, mime):
        response = self.client.post("/api/analyze/" + kind, files={"file": ("sample", data, mime)})
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertIsNone(body["trust_score"])
        self.assertIsNone(body["is_authentic"])
        self.assertIsNone(body["risk_level"])
        self.assertEqual(body["verdict"], "suspicious")
        report = body["provenance"][0]
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["provider"], "Google Gemini")
        self.assertEqual(report["model"], "offline-media-model")
        self.assertTrue(report["coverage"]["submitted"])
        self.assertGreaterEqual(report["duration_ms"], 0)
        self.assertEqual(report["observations"], PAYLOAD["observations"])
        self.generate.assert_called_once()
        kwargs = self.generate.call_args.kwargs
        self.assertEqual(kwargs["model"], "offline-media-model")
        self.assertEqual(kwargs["config"].response_mime_type, "application/json")
        media = [part for part in kwargs["contents"] if isinstance(part, types.Part) and part.inline_data]
        self.assertEqual(len(media), report["coverage"]["media_parts"])
        self.assertTrue(body["details"], "Local supplementary checks must remain")
        return body, media

    def test_image_request_contains_decodable_pixels_not_ocr(self):
        image = io.BytesIO()
        Image.new("RGB", (1600, 800), (20, 100, 180)).save(image, format="PNG")
        body, parts = self.upload("image", image.getvalue(), "image/png")
        self.assertEqual(parts[0].inline_data.mime_type, "image/jpeg")
        with Image.open(io.BytesIO(parts[0].inline_data.data)) as sent:
            self.assertEqual(sent.size, (1536, 768))
            self.assertLess(abs(sent.getpixel((10, 10))[2] - 180), 5)
        self.assertIsNone(body["extracted_text"])

    def test_audio_request_contains_decodable_pcm_not_transcript(self):
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes((np.sin(np.arange(44100) * 0.1) * 8000).astype("<i2").tobytes())
        body, parts = self.upload("audio", output.getvalue(), "audio/wav")
        self.assertEqual(parts[0].inline_data.mime_type, "audio/wav")
        with wave.open(io.BytesIO(parts[0].inline_data.data)) as sent:
            self.assertEqual(sent.getnchannels(), 1)
            self.assertEqual(sent.getframerate(), 22050)
            self.assertEqual(sent.getnframes(), 44100)
            self.assertGreater(np.std(np.frombuffer(sent.readframes(44100), dtype="<i2")), 100)
        self.assertEqual(body["provenance"][0]["coverage"]["analyzed_duration_seconds"], 2)

    def test_audio_decoder_caps_real_source_at_sixty_seconds(self):
        output = io.BytesIO()
        with wave.open(output, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(22050)
            wav.writeframes(np.zeros(22050 * 61, dtype="<i2").tobytes())
        samples, rate = audio_analyzer._load_audio(output.getvalue(), "WAV")
        self.assertEqual(len(samples) / rate, 60)
        self.generate.assert_not_called()

    def test_video_reuses_bounded_timestamped_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.mp4"
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (96, 64))
            try:
                self.assertTrue(writer.isOpened())
                for index in range(40):
                    writer.write(np.full((64, 96, 3), 30 + index * 3, dtype=np.uint8))
            finally:
                writer.release()
            body, parts = self.upload("video", path.read_bytes(), "video/mp4")
        coverage = body["provenance"][0]["coverage"]
        self.assertEqual(len(parts), 15)
        self.assertEqual(coverage["total_frames"], 40)
        self.assertEqual(coverage["media_duration_seconds"], 4)
        timestamps = coverage["frame_timestamps_seconds"]
        self.assertEqual(timestamps, [round(f["frame_number"] / 10, 3) for f in body["frame_analyses"]])
        self.assertEqual((timestamps[0], timestamps[-1]), (0, 3.9))
        self.assertIn("No video audio", coverage["description"])
        contents = self.generate.call_args.kwargs["contents"]
        for i, part in enumerate(parts):
            self.assertEqual(part.inline_data.mime_type, "image/jpeg")
            self.assertIn(f"{timestamps[i]:.3f} seconds", contents[1 + 2 * i].text)
            with Image.open(io.BytesIO(part.inline_data.data)) as image:
                self.assertEqual(image.size, (96, 64))
        self.assertTrue(all(f["deepfake_probability"] is None for f in body["frame_analyses"]))

    def test_undecodable_media_is_inconclusive_without_provider_request(self):
        for kind, mime in [("image", "image/png"), ("video", "video/mp4"), ("audio", "audio/wav")]:
            with self.subTest(kind=kind):
                response = self.client.post("/api/analyze/" + kind, files={"file": ("broken", b"broken media", mime)})
                self.assertEqual(response.status_code, 200, response.text)
                body = response.json()
                self.assertEqual(body["verdict"], "inconclusive")
                self.assertEqual(body["provenance"][0]["status"], "insufficient_media")
                self.assertFalse(body["provenance"][0]["coverage"]["submitted"])
                self.assertIsNone(body["trust_score"])
        self.generate.assert_not_called()

    def test_failed_provider_never_becomes_content_risk(self):
        image = io.BytesIO()
        Image.new("RGB", (40, 40)).save(image, format="PNG")
        self.generate.side_effect = RuntimeError("private upstream key")
        response = self.client.post("/api/analyze/image", files={"file": ("sample.png", image.getvalue(), "image/png")})
        body = response.json()
        self.assertEqual(body["verdict"], "inconclusive")
        self.assertIsNone(body["risk_level"])
        self.assertIsNone(body["trust_score"])
        self.assertEqual(body["provenance"][0]["status"], "provider_error")
        self.assertNotIn("private upstream key", response.text)
        self.assertFalse(any("Gemini" in d["finding"] for d in body["details"]))


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.generate = Mock(return_value=SimpleNamespace(text=json.dumps(PAYLOAD), candidates=[], prompt_feedback=None))
        self.enterContext(patch.object(provider, "gemini_client", SimpleNamespace(models=SimpleNamespace(generate_content=self.generate))))
        self.parts = [types.Part.from_bytes(data=b"sample", mime_type="image/jpeg")]

    async def request(self):
        return await request_gemini(self.parts, AnalysisCoverage(description="Test sample", media_parts=1))

    async def test_missing_key(self):
        with patch.object(provider, "gemini_client", None):
            report = await self.request()
        self.assertEqual(report.status, "not_configured")
        self.assertFalse(report.coverage.submitted)
        self.generate.assert_not_called()

    async def test_invalid_and_inconsistent_structured_outputs(self):
        invalid = ["not JSON secret", "", "{}", json.dumps({**PAYLOAD, "verdict": "authentic"}),
                   json.dumps({**PAYLOAD, "observations": []}), json.dumps({**PAYLOAD, "limitations": []}),
                   json.dumps({**PAYLOAD, "observations": [123]}), json.dumps({**PAYLOAD, "summary": " "}),
                   json.dumps({**PAYLOAD, "confidence": 99}), json.dumps({**PAYLOAD, "observations": [" "]})]
        for text in invalid:
            with self.subTest(text=text):
                self.generate.return_value.text = text
                report = await self.request()
                self.assertEqual(report.status, "invalid_response")
                self.assertEqual(report.verdict, "inconclusive")
                self.assertEqual(report.observations, [])
                self.assertNotIn("secret", report.model_dump_json())

    async def test_valid_no_indicators_and_inconclusive_never_claim_authenticity(self):
        for verdict in ("no_indicators", "inconclusive"):
            self.generate.return_value.text = json.dumps({**PAYLOAD, "verdict": verdict})
            report = await self.request()
            self.assertEqual(report.status, "completed")
            self.assertEqual(report.verdict, verdict)

    async def test_provider_failure_statuses_are_sanitized(self):
        cases = [(401, "authentication_error"), (403, "authentication_error"), (404, "model_unavailable"),
                 (429, "quota_exceeded"), (503, "provider_error"), (504, "timeout")]
        for code, expected in cases:
            error = RuntimeError("secret provider body")
            error.code = code
            self.generate.side_effect = error
            report = await self.request()
            self.assertEqual(report.status, expected)
            self.assertEqual(report.verdict, "inconclusive")
            self.assertNotIn("secret", report.model_dump_json())
        for error in (TimeoutError("secret"), httpx.ReadTimeout("secret")):
            self.generate.side_effect = error
            self.assertEqual((await self.request()).status, "timeout")

    async def test_safety_block_and_empty_response(self):
        self.generate.return_value = SimpleNamespace(prompt_feedback=SimpleNamespace(block_reason="SAFETY"), candidates=[])
        self.assertEqual((await self.request()).status, "blocked")
        self.generate.return_value = SimpleNamespace(prompt_feedback=None, candidates=[SimpleNamespace(finish_reason="SAFETY")])
        self.assertEqual((await self.request()).status, "blocked")

    async def test_truncated_response_is_rejected_even_if_json_is_valid(self):
        self.generate.return_value.candidates = [SimpleNamespace(finish_reason="MAX_TOKENS")]
        self.assertEqual((await self.request()).status, "invalid_response")

    async def test_unspecified_block_reason_does_not_hide_success(self):
        self.generate.return_value.prompt_feedback = SimpleNamespace(block_reason="BLOCKED_REASON_UNSPECIFIED")
        self.assertEqual((await self.request()).status, "completed")

    async def test_sdk_work_is_off_event_loop(self):
        loop_thread = threading.get_ident()
        def generate(**kwargs):
            self.assertNotEqual(threading.get_ident(), loop_thread)
            return SimpleNamespace(text=json.dumps(PAYLOAD), candidates=[], prompt_feedback=None)
        self.generate.side_effect = generate
        self.assertEqual((await self.request()).status, "completed")

    async def test_real_installed_sdk_serializes_inline_media_and_schema_offline(self):
        sdk = genai.Client(api_key="fake-offline-key")
        response = types.HttpResponse(headers={}, body=json.dumps({
            "candidates": [{"content": {"role": "model", "parts": [{"text": json.dumps(PAYLOAD)}]}, "finishReason": "STOP"}],
        }))
        try:
            with patch.object(provider, "gemini_client", sdk), \
                    patch.object(sdk._api_client, "request", return_value=response) as transport:
                report = await self.request()
            self.assertEqual(report.status, "completed", report.message)
            transport.assert_called_once()
            serialized = transport.call_args.args[2]
            inline = serialized["contents"][0]["parts"][1]["inlineData"]
            self.assertEqual(inline["mimeType"], "image/jpeg")
            self.assertEqual(base64.b64decode(inline["data"]), b"sample")
            self.assertIn("responseSchema", serialized["generationConfig"])
        finally:
            sdk.close()


class RiskTests(unittest.TestCase):
    def test_system_errors_never_raise_content_risk(self):
        for category in ("System Error", "system_error"):
            details = [AnalysisDetail(category=category, finding="Provider unavailable", confidence=1,
                                      severity=RiskLevel.CRITICAL)] * 3
            self.assertEqual(trust_engine.calculate_trust_score(details), 0)
            self.assertEqual(trust_engine.determine_risk_level(0, details), RiskLevel.LOW)


if __name__ == "__main__":
    unittest.main()
