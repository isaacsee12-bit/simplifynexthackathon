"""Offline settings regression tests against the root ASGI application."""

import io
import json
import os
import unittest
from contextlib import redirect_stderr, redirect_stdout
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Prevent dotenv credentials from reaching an SDK constructor on standalone import.
with patch.dict(os.environ, {"VERCEL": "1", "GEMINI_API_KEY": ""}), \
        patch("google.genai.Client"), \
        patch("socket.socket.connect", side_effect=AssertionError("Network disabled")):
    from app import app

from fastapi.testclient import TestClient
from core.config import settings
from core import gemini_client as gemini_provider
import analyzers.rag_verifier as rag_module
import analyzers.text_analyzer as text_module


class ClientAddressApp:
    """Supply a real client address on Starlette versions without client= support."""

    def __init__(self, application):
        self.application = application
        self.client = ("127.0.0.1", 50000)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            scope = dict(scope, client=self.client)
        await self.application(scope, receive, send)


class SettingsTests(unittest.TestCase):
    endpoint = "/api/settings/gemini"
    secret = "fake-settings-secret-not-a-real-key"
    model = "gemini-offline-updated"
    text = "Studies show that regular exercise improves cardiovascular health."

    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"VERCEL": ""}))
        self.enterContext(patch.object(settings, "GEMINI_API_KEY", ""))
        self.enterContext(patch.object(settings, "GEMINI_MODEL", "gemini-offline-original"))
        self.enterContext(patch.object(gemini_provider, "gemini_client", None))
        self.sdk = Mock()
        self.constructor = self.enterContext(patch(
            "google.genai.Client", return_value=self.sdk,
        ))
        self.wrapper = ClientAddressApp(app)
        self.client = self.enterContext(TestClient(
            self.wrapper, base_url="http://localhost",
            headers={"x-verifyai-settings": "1"},
        ))
        # Initialize the Windows asyncio loopback socket pair before blocking I/O.
        for target in ("socket.socket.connect", "socket.getaddrinfo"):
            blocked = self.enterContext(patch(
                target, side_effect=AssertionError("Network disabled"),
            ))
            self.addCleanup(blocked.assert_not_called)
        self.wikipedia = self.enterContext(patch.object(
            rag_module.rag_verifier, "_query_wikipedia",
            return_value=[{"title": "Exercise", "url": "https://en.wikipedia.org/wiki/Exercise",
                           "excerpt": self.text}],
        ))
        self.duckduckgo = self.enterContext(patch.object(
            rag_module.rag_verifier, "_query_duckduckgo",
            side_effect=AssertionError("Unexpected search fallback"),
        ))

    def assert_settings(self, response, configured, model):
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {"configured": configured, "model": model})
        self.assertNotIn(self.secret, response.text)
        self.assertNotIn("api_key", response.text.lower())

    def configure(self):
        response = self.client.put(self.endpoint, json={
            "api_key": self.secret, "model": self.model,
        })
        self.assert_settings(response, True, self.model)
        self.assertEqual(settings.GEMINI_API_KEY, self.secret)
        self.assertEqual(settings.GEMINI_MODEL, self.model)
        self.assertIs(gemini_provider.gemini_client, self.sdk)
        return response

    def test_get_only_returns_configuration_status_and_model(self):
        self.assert_settings(self.client.get(self.endpoint), False, settings.GEMINI_MODEL)
        with patch.object(settings, "GEMINI_API_KEY", self.secret):
            self.assert_settings(self.client.get(self.endpoint), True, settings.GEMINI_MODEL)
        self.constructor.assert_not_called()

    def test_configured_text_route_uses_only_local_checks_without_claims(self):
        self.configure()
        with patch.object(text_module.text_analyzer, "analyze",
                          wraps=text_module.text_analyzer.analyze) as analyze:
            response = self.client.post("/api/analyze/text", json={
                "text": self.text, "check_claims": False,
            })
        analyze.assert_called_once_with(self.text, check_ai_generated=True,
                                        check_scam=True, use_llm=False)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["investigation"])
        self.assertEqual(response.json()["claims_verified"], 0)
        self.sdk.models.generate_content.assert_not_called()
        self.wikipedia.assert_not_called()
        self.duckduckgo.assert_not_called()

    def test_put_updates_live_investigation_client_and_model(self):
        old_sdk = Mock()
        gemini_provider.gemini_client = old_sdk
        self.configure()
        self.constructor.assert_called_once()
        self.assertEqual(self.constructor.call_args.kwargs["api_key"], self.secret)
        self.assertEqual(self.constructor.call_args.kwargs["http_options"].timeout, 30000)
        self.assertIs(rag_module.gemini_provider, gemini_provider)
        query = "exercise cardiovascular research"
        followup = {"tool": "duckduckgo", "query": "exercise independent clinical evidence"}
        citation = {"evidence_id": "c1-e1", "quote": self.text, "stance": "supported"}
        assessment = {"citations": [citation], "reasoning": "Offline updated provider evidence",
                      "uncertainties": [], "followup": followup}
        self.sdk.models.generate_content.side_effect = [
            SimpleNamespace(text=json.dumps(payload)) for payload in [
                {"claims": [self.text]},
                {"tool": "wikipedia", "query": query},
                assessment,
                {**assessment, "citations": [citation, {**citation, "evidence_id": "c1-e2"}]},
            ]
        ]
        self.duckduckgo.side_effect = None
        self.duckduckgo.return_value = [{"title": "Exercise research",
                                        "url": "https://www.reuters.com/science/exercise",
                                        "excerpt": self.text}]
        response = self.client.post("/api/analyze/text", json={
            "text": self.text, "check_claims": True,
            "check_ai_generated": False, "check_scam": False,
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["claims_verified"], 1)
        claim = response.json()["investigation"]["claims"][0]
        self.assertEqual(claim["text"], self.text)
        self.assertEqual(claim["verdict"], "supported")
        self.assertEqual({e["publisher"] for e in claim["evidence"]}, {"Wikipedia", "Reuters"})
        calls = self.sdk.models.generate_content.call_args_list
        self.assertEqual(len(calls), 4)
        for call, schema in zip(calls, [rag_module._Claims, rag_module._Plan,
                                       rag_module._Assessment, rag_module._Assessment]):
            self.assertEqual(call.kwargs["model"], self.model)
            self.assertEqual(call.kwargs["config"].response_mime_type, "application/json")
            self.assertEqual(call.kwargs["config"].response_schema["title"], schema.__name__)
            self.assertIn(self.text, call.kwargs["contents"])
        old_sdk.models.generate_content.assert_not_called()
        self.wikipedia.assert_called_once()
        self.assertEqual(self.wikipedia.call_args.args[0], query)
        self.duckduckgo.assert_called_once()
        self.assertEqual(self.duckduckgo.call_args.args[0], followup["query"])

    def test_blank_or_omitted_key_preserves_configured_secret(self):
        self.configure()
        for key_body in ({"api_key": ""}, {"api_key": "  \t "}, {"api_key": None}, {}):
            with self.subTest(body=key_body):
                self.constructor.reset_mock()
                response = self.client.put(self.endpoint, json={
                    **key_body, "model": "gemini-model-only",
                })
                self.assert_settings(response, True, "gemini-model-only")
                self.assertEqual(settings.GEMINI_API_KEY, self.secret)
                self.constructor.assert_called_once()
                self.assertEqual(self.constructor.call_args.kwargs["api_key"], self.secret)

    def test_delete_clears_memory_without_opening_files(self):
        self.configure()
        self.constructor.reset_mock()
        with patch("builtins.open", side_effect=AssertionError("Unexpected file access")) as opened, \
                patch("io.open", side_effect=AssertionError("Unexpected file access")) as io_opened:
            response = self.client.delete(self.endpoint)
        opened.assert_not_called()
        io_opened.assert_not_called()
        self.assert_settings(response, False, self.model)
        self.assertEqual(settings.GEMINI_API_KEY, "")
        self.assertIsNone(gemini_provider.gemini_client)
        self.constructor.assert_not_called()
        self.assert_settings(self.client.get(self.endpoint), False, self.model)

    def test_access_guards_reject_all_settings_methods_without_mutation(self):
        cases = [
            ("external client", ("203.0.113.10", 50000), {}, ""),
            ("missing client", None, {}, ""),
            ("external origin", ("127.0.0.1", 50000), {"origin": "https://example.com"}, ""),
            ("external host", ("127.0.0.1", 50000), {"host": "example.com"}, ""),
            ("missing header", ("127.0.0.1", 50000), {}, ""),
            ("vercel", ("127.0.0.1", 50000), {}, "1"),
        ]
        with patch.object(settings, "GEMINI_API_KEY", self.secret), \
                patch.object(gemini_provider, "gemini_client", self.sdk):
            for name, address, headers, vercel in cases:
                for method in ("GET", "PUT", "DELETE", "POST"):
                    with self.subTest(guard=name, method=method), \
                            patch.dict(os.environ, {"VERCEL": vercel}):
                        self.wrapper.client = address
                        request = self.client.build_request(method, self.endpoint + ("/test" if method == "POST" else ""), headers=headers,
                            json={"api_key": self.secret, "model": self.model} if method == "PUT" else None)
                        if name == "missing header":
                            del request.headers["x-verifyai-settings"]
                        response = self.client.send(request)
                        self.assertEqual(response.status_code, 403, response.text)
                        self.assertNotIn(self.secret, response.text)
                        self.assertEqual(settings.GEMINI_API_KEY, self.secret)
                        self.assertEqual(settings.GEMINI_MODEL, "gemini-offline-original")
                        self.assertIs(gemini_provider.gemini_client, self.sdk)
        self.constructor.assert_not_called()

    def test_connection_uses_saved_client_and_model(self):
        self.configure()
        self.sdk.models.generate_content.return_value = SimpleNamespace(text="OK", candidates=[], prompt_feedback=None)
        response = self.client.post(self.endpoint + "/test")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "completed")
        self.assertEqual(body["model"], self.model)
        self.assertTrue(body["coverage"]["submitted"])
        kwargs = self.sdk.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs["model"], self.model)
        self.assertEqual(kwargs["contents"], ["Reply with exactly OK."])
        self.assertLessEqual(kwargs["config"].max_output_tokens, 128)
        self.assertNotIn(self.secret, response.text + str(kwargs))

    def test_connection_without_key_sends_nothing(self):
        response = self.client.post(self.endpoint + "/test")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "not_configured")
        self.assertFalse(response.json()["coverage"]["submitted"])
        self.sdk.models.generate_content.assert_not_called()

    def test_connection_failures_are_sanitized(self):
        self.configure()
        for response_text, failure, expected in [("unexpected", None, "invalid_response"),
                                                 (None, RuntimeError(self.secret), "provider_error")]:
            self.sdk.models.generate_content.return_value = SimpleNamespace(text=response_text, candidates=[], prompt_feedback=None)
            self.sdk.models.generate_content.side_effect = failure
            response = self.client.post(self.endpoint + "/test")
            self.assertEqual(response.json()["status"], expected)
            self.assertNotIn(self.secret, response.text)

    def test_invalid_model_does_not_leak_submitted_key_or_mutate_settings(self):
        for model in ("", "bad model", "bad\nmodel", "x" * 201):
            with self.subTest(model=model):
                response = self.client.put(self.endpoint, json={"api_key": self.secret, "model": model})
                self.assertEqual(response.status_code, 422, response.text)
                self.assertNotIn(self.secret, response.text)
                self.assertEqual(settings.GEMINI_API_KEY, "")
                self.assertEqual(settings.GEMINI_MODEL, "gemini-offline-original")
                self.assertIsNone(gemini_provider.gemini_client)
        self.constructor.assert_not_called()

    def test_constructor_error_is_sanitized_and_preserves_configuration(self):
        self.configure()
        new_secret = "fake-rejected-secret-not-a-real-key"
        self.constructor.side_effect = RuntimeError("Private SDK failure: " + new_secret)
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            response = self.client.put(self.endpoint, json={
                "api_key": new_secret, "model": "gemini-rejected-model",
            })
        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(response.json(), {"detail": "Could not configure Gemini."})
        for private in (self.secret, new_secret, "Private SDK failure"):
            self.assertNotIn(private, response.text + output.getvalue())
        self.assertEqual(settings.GEMINI_API_KEY, self.secret)
        self.assertEqual(settings.GEMINI_MODEL, self.model)
        self.assertIs(gemini_provider.gemini_client, self.sdk)


if __name__ == "__main__":
    unittest.main()
