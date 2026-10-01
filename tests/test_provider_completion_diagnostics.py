"""Offline regression tests for safe provider completion-envelope failures."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from standalone.providers import ChatCompletionClient, ProviderConfig, ProviderRequestError


class _Response:
    status = 200

    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.raw


class ProviderCompletionDiagnosticsTests(unittest.TestCase):
    def _client(self, attempts: list[int]) -> ChatCompletionClient:
        return ChatCompletionClient(
            ProviderConfig(
                name="kimi",
                model="kimi-k2.6",
                base_url="http://127.0.0.1:8765",
                api_key="mock",
                key_variable="TEST_KEY",
            ),
            on_attempt=attempts.append,
        )

    def _failure(self, payload: object, *, raw: bytes | None = None) -> tuple[ProviderRequestError, dict]:
        attempts: list[int] = []
        body = json.dumps(payload).encode() if raw is None else raw
        with patch(
            "standalone.providers.urllib.request.urlopen", return_value=_Response(body)
        ) as transport:
            with self.assertRaises(ProviderRequestError) as raised:
                self._client(attempts).complete(
                    [{"role": "user", "content": "Return one JSON object."}],
                    reasoning_option="disabled",
                    json_mode=True,
                )
        self.assertEqual(1, transport.call_count)
        self.assertEqual([1], attempts)
        error = raised.exception
        self.assertEqual(1, len(error.request_receipts))
        receipt = error.request_receipts[0]
        self.assertEqual(200, receipt["http_status"])
        self.assertTrue(receipt["request_dispatched"])
        self.assertEqual("disabled", receipt["reasoning_option"])
        self.assertEqual("STOP_NO_AUTOMATIC_RETRY", receipt["retry_decision"])
        self.assertEqual(0, receipt["max_transient_retries"])
        self.assertEqual("UNKNOWN", receipt["provider_outcome"])
        self.assertIsNotNone(receipt["finished_at"])
        self.assertEqual(str(error), receipt["error_summary"])
        self.assertLess(len(str(error)), 240)
        return error, receipt

    def test_empty_content_preserves_usage_and_finish_reason(self) -> None:
        for content in (None, "", " \n\t "):
            with self.subTest(content=content):
                _, receipt = self._failure({
                    "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
                    "usage": {
                        "prompt_tokens": 12,
                        "completion_tokens": 5,
                        "total_tokens": 17,
                        "prompt_tokens_details": {"cached_tokens": 4},
                        "completion_tokens_details": {"reasoning_tokens": 3},
                    },
                })
                self.assertEqual("EMPTY_COMPLETION_CONTENT", receipt["completion_error_code"])
                self.assertEqual("stop", receipt["finish_reason"])
                self.assertEqual("COMPLETE", receipt["usage_status"])
                self.assertEqual({
                    "prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17,
                    "cached_tokens": 4, "reasoning_tokens": 3,
                }, receipt["usage"])

    def test_truncated_completions_are_identified_without_accepting_partial_content(self) -> None:
        for content in (None, "", " ", '{"partial":', "{}"):
            with self.subTest(content=content):
                _, receipt = self._failure({
                    "choices": [{"message": {"content": content}, "finish_reason": "length"}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 8},
                })
                self.assertEqual("TRUNCATED_COMPLETION", receipt["completion_error_code"])
                self.assertEqual("length", receipt["finish_reason"])
                self.assertEqual("COMPLETE", receipt["usage_status"])

    def test_refusal_and_content_filter_never_expose_provider_text(self) -> None:
        marker = "private-refusal-and-reasoning-must-not-persist"
        for message, reason in (
            ({"content": None, "refusal": marker}, "stop"),
            ({"content": "{}", "refusal": marker}, "stop"),
            ({"content": None}, "content_filter"),
            ({"content": marker}, "content_filter"),
            ({"reasoning_content": marker}, "content_filter"),
        ):
            with self.subTest(reason=reason, fields=list(message)):
                error, receipt = self._failure({
                    "choices": [{"message": message, "finish_reason": reason}],
                    "usage": {"prompt_tokens": 8, "completion_tokens": 0},
                })
                self.assertEqual("REFUSED_COMPLETION", receipt["completion_error_code"])
                self.assertEqual(reason, receipt["finish_reason"])
                self.assertNotIn(marker, str(error) + json.dumps(receipt))

    def test_missing_content_never_uses_reasoning_as_the_answer(self) -> None:
        marker = "private-reasoning-must-not-become-final-content"
        for message in ({"reasoning_content": marker}, {"content": None, "reasoning_content": marker}):
            with self.subTest(fields=list(message)):
                error, receipt = self._failure({
                    "choices": [{"message": message, "finish_reason": "stop"}],
                    "usage": {"completion_tokens": 9},
                })
                expected = "EMPTY_COMPLETION_CONTENT" if "content" in message else "MISSING_COMPLETION_CONTENT"
                self.assertEqual(expected, receipt["completion_error_code"])
                self.assertEqual({"completion_tokens": 9}, receipt["usage"])
                self.assertEqual("PARTIAL", receipt["usage_status"])
                self.assertNotIn(marker, str(error) + json.dumps(receipt))

    def test_missing_and_malformed_envelopes_have_distinct_bounded_codes(self) -> None:
        cases = (
            ({}, "MISSING_COMPLETION_CONTENT"),
            ({"choices": []}, "MISSING_COMPLETION_CONTENT"),
            ({"choices": [{}]}, "MISSING_COMPLETION_CONTENT"),
            ({"choices": [{"message": {}}]}, "MISSING_COMPLETION_CONTENT"),
            (None, "INVALID_COMPLETION_ENVELOPE"),
            ([], "INVALID_COMPLETION_ENVELOPE"),
            ("private-raw-payload", "INVALID_COMPLETION_ENVELOPE"),
            ({"choices": None}, "INVALID_COMPLETION_ENVELOPE"),
            ({"choices": {}}, "INVALID_COMPLETION_ENVELOPE"),
            ({"choices": [None]}, "INVALID_COMPLETION_ENVELOPE"),
            ({"choices": [{"message": None}]}, "INVALID_COMPLETION_ENVELOPE"),
            ({"choices": [{"message": []}]}, "INVALID_COMPLETION_ENVELOPE"),
            ({"choices": [{"message": {"content": 42}}]}, "INVALID_COMPLETION_CONTENT"),
            ({"choices": [{"message": {"content": []}}]}, "INVALID_COMPLETION_CONTENT"),
            ({"choices": [{"message": {"content": {"text": "private-raw-payload"}}}]}, "INVALID_COMPLETION_CONTENT"),
        )
        for payload, expected in cases:
            with self.subTest(payload=payload):
                error, receipt = self._failure(payload)
                self.assertEqual(expected, receipt["completion_error_code"])
                self.assertNotIn("private-raw-payload", str(error) + json.dumps(receipt))
                self.assertEqual("UNKNOWN", receipt["usage_status"])

    def test_malformed_json_and_encoding_do_not_expose_raw_body(self) -> None:
        for raw in (b"private-raw-body-not-json", b"\xffprivate-raw-body-invalid-encoding"):
            with self.subTest(raw=raw[:1]):
                error, receipt = self._failure(None, raw=raw)
                self.assertEqual("INVALID_COMPLETION_ENVELOPE", receipt["completion_error_code"])
                self.assertEqual({}, receipt["usage"])
                self.assertIsNone(receipt["finish_reason"])
                self.assertNotIn("private-raw-body", str(error) + json.dumps(receipt))

    def test_only_finite_known_finish_reasons_are_retained(self) -> None:
        marker = "sk-synthetic-secret-value-never-persist"
        for reason in (marker, "other-unknown-value", 1, True, {}, [], None, "x" * 1000):
            with self.subTest(reason_type=type(reason).__name__):
                error, receipt = self._failure({
                    "choices": [{"message": {"content": None}, "finish_reason": reason}],
                })
                self.assertIsNone(receipt["finish_reason"])
                self.assertNotIn(marker, str(error) + json.dumps(receipt))

    def test_usage_is_allowlisted_and_requires_nonnegative_integer_counts(self) -> None:
        _, receipt = self._failure({
            "choices": [{"message": {"content": None}, "finish_reason": "stop"}],
            "usage": {
                "prompt_tokens": True,
                "completion_tokens": -1,
                "total_tokens": "12",
                "cached_tokens": 0,
                "reasoning_tokens": 1.5,
                "arbitrary_provider_text": "private-usage-marker",
                "prompt_tokens_details": {"cached_tokens": False},
                "completion_tokens_details": {"reasoning_tokens": "private-usage-marker"},
            },
        })
        self.assertEqual({"cached_tokens": 0}, receipt["usage"])
        self.assertEqual("PARTIAL", receipt["usage_status"])
        self.assertNotIn("private-usage-marker", json.dumps(receipt))
        for usage in (None, [], "private-usage-marker", 12):
            with self.subTest(usage_type=type(usage).__name__):
                _, receipt = self._failure({"choices": [], "usage": usage})
                self.assertEqual({}, receipt["usage"])
                self.assertEqual("UNKNOWN", receipt["usage_status"])

    def test_usage_survives_missing_choices(self) -> None:
        _, receipt = self._failure({"usage": {"prompt_tokens": 7, "completion_tokens": 0}})
        self.assertEqual({"prompt_tokens": 7, "completion_tokens": 0}, receipt["usage"])
        self.assertEqual("COMPLETE", receipt["usage_status"])

    def test_valid_nonreasoning_response_remains_successful(self) -> None:
        for reason in ("stop", None):
            with self.subTest(reason=reason):
                attempts: list[int] = []
                payload = {
                    "choices": [{"message": {"content": "  {}  "}, "finish_reason": reason}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 1},
                }
                with patch(
                    "standalone.providers.urllib.request.urlopen",
                    return_value=_Response(json.dumps(payload).encode()),
                ) as transport:
                    result = self._client(attempts).complete(
                        [{"role": "user", "content": "Return JSON."}],
                        reasoning_option="disabled",
                    )
                self.assertEqual(1, transport.call_count)
                self.assertEqual([1], attempts)
                request = json.loads(transport.call_args.args[0].data)
                self.assertEqual({"type": "disabled"}, request["thinking"])
                self.assertEqual("{}", result.content)
                self.assertEqual(reason, result.finish_reason)
                receipt = result.request_receipts[0]
                self.assertEqual("SUCCEEDED", receipt["provider_outcome"])
                self.assertEqual(reason, receipt["finish_reason"])
                self.assertEqual("COMPLETE", receipt["usage_status"])
                self.assertIsNone(receipt["completion_error_code"])


if __name__ == "__main__":
    unittest.main()
