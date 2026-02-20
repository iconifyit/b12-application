"""Unit tests for submit.py — validates canonicalization and HMAC signing."""

import json
import sys
import unittest

from submit import canonicalize, sign


# ── B12's reference example ──────────────────────────────────────────
# These values come directly from the challenge description so we can
# prove our implementation matches the expected output.

EXAMPLE_PAYLOAD = {
    "timestamp": "2026-01-06T16:59:37.571Z",
    "name": "Your name",
    "email": "you@example.com",
    "resume_link": "https://pdf-or-html-or-linkedin.example.com",
    "repository_link": "https://link-to-github-or-other-forge.example.com/your/repository",
    "action_run_link": "https://link-to-github-or-another-forge.example.com/your/repository/actions/runs/run_id",
}

EXPECTED_CANONICAL = (
    '{"action_run_link":"https://link-to-github-or-another-forge.example.com'
    '/your/repository/actions/runs/run_id","email":"you@example.com",'
    '"name":"Your name","repository_link":"https://link-to-github-or-other'
    '-forge.example.com/your/repository","resume_link":"https://pdf-or-html'
    '-or-linkedin.example.com","timestamp":"2026-01-06T16:59:37.571Z"}'
)

EXPECTED_DIGEST = "c5db257a56e3c258ec1162459c9a295280871269f4cf70146d2c9f1b52671d45"
SIGNING_SECRET = "hello-there-from-b12"

PASS = "\033[32m PASS \033[0m"
FAIL = "\033[31m FAIL \033[0m"
DIVIDER = "\033[90m" + "─" * 72 + "\033[0m"


# ── Logging helper ───────────────────────────────────────────────────

def log(title: str, rows: list[tuple[str, object]]) -> None:
    """Pretty-print a titled block of label/value pairs for test output.

    Args:
        title: Section heading shown above the rows.
        rows:  List of (label, value) tuples. A special label "result"
               renders the value as a colour-coded PASS/FAIL badge.
    """
    print(f"\n{DIVIDER}", file=sys.stdout)
    print(f"  \033[1m{title}\033[0m", file=sys.stdout)
    print(DIVIDER, file=sys.stdout)

    label_width = max(len(label) for label, _ in rows)

    for label, value in rows:
        if label == "result":
            badge = PASS if value else FAIL
            print(f"  {'':>{label_width}}  {badge}", file=sys.stdout)
        else:
            print(f"  \033[36m{label:>{label_width}}\033[0m  {value}", file=sys.stdout)

    print(file=sys.stdout)


class TestCanonicalize(unittest.TestCase):
    """Verify that canonicalize() produces compact, sorted, UTF-8 JSON."""

    def test_compact_sorted_json(self):
        body = canonicalize(EXAMPLE_PAYLOAD)
        actual = body.decode("utf-8")
        match = actual == EXPECTED_CANONICAL
        log("Compact sorted JSON", [
            ("input keys", list(EXAMPLE_PAYLOAD.keys())),
            ("expected", EXPECTED_CANONICAL),
            ("actual", actual),
            ("result", match),
        ])
        self.assertEqual(actual, EXPECTED_CANONICAL)

    def test_no_extra_whitespace(self):
        body = canonicalize(EXAMPLE_PAYLOAD)
        text = body.decode("utf-8")
        parsed = json.loads(text)
        re_encoded = json.dumps(parsed, separators=(",", ":"), sort_keys=True)
        match = text == re_encoded
        log("No extra whitespace", [
            ("canonical length", f"{len(text)} bytes"),
            ("re-encoded length", f"{len(re_encoded)} bytes"),
            ("result", match),
        ])
        self.assertEqual(text, re_encoded)

    def test_keys_are_sorted(self):
        body = canonicalize(EXAMPLE_PAYLOAD)
        parsed = json.loads(body)
        keys = list(parsed.keys())
        match = keys == sorted(keys)
        log("Keys are sorted", [
            ("key order", keys),
            ("sorted", sorted(keys)),
            ("result", match),
        ])
        self.assertEqual(keys, sorted(keys))


class TestSign(unittest.TestCase):
    """Verify that sign() produces the correct HMAC-SHA256 digest."""

    def test_example_payload_signature(self):
        """The critical test: B12's example payload must produce their expected digest."""
        body = canonicalize(EXAMPLE_PAYLOAD)
        signature = sign(body, SIGNING_SECRET)
        expected = f"sha256={EXPECTED_DIGEST}"
        match = signature == expected
        log("Example payload signature (B12 reference vector)", [
            ("body", f"({len(body)} bytes) {body.decode('utf-8')[:72]}..."),
            ("secret", SIGNING_SECRET),
            ("expected", expected),
            ("actual", signature),
            ("result", match),
        ])
        self.assertEqual(signature, expected)

    def test_signature_format(self):
        """Signature must be 'sha256=' followed by a 64-char hex string."""
        body = canonicalize(EXAMPLE_PAYLOAD)
        signature = sign(body, SIGNING_SECRET)
        hex_part = signature.removeprefix("sha256=")
        has_prefix = signature.startswith("sha256=")
        correct_len = len(hex_part) == 64
        log("Signature format", [
            ("signature", signature),
            ("has prefix", f"sha256= → {has_prefix}"),
            ("hex length", f"{len(hex_part)} (expected 64)"),
            ("result", has_prefix and correct_len),
        ])
        self.assertTrue(has_prefix)
        self.assertEqual(len(hex_part), 64)
        int(hex_part, 16)

    def test_different_payload_different_signature(self):
        """Changing any field should produce a different digest."""
        modified = {**EXAMPLE_PAYLOAD, "name": "Someone else"}
        body = canonicalize(modified)
        signature = sign(body, SIGNING_SECRET)
        original = f"sha256={EXPECTED_DIGEST}"
        different = signature != original
        log("Different payload → different signature", [
            ("original name", "'Your name'"),
            ("modified name", "'Someone else'"),
            ("original sig", original),
            ("modified sig", signature),
            ("result", different),
        ])
        self.assertNotEqual(signature, original)

    def test_different_secret_different_signature(self):
        """Using a different key must produce a different digest."""
        body = canonicalize(EXAMPLE_PAYLOAD)
        correct_sig = sign(body, SIGNING_SECRET)
        wrong_sig = sign(body, "wrong-secret")
        different = correct_sig != wrong_sig
        log("Different secret → different signature", [
            (f"'{SIGNING_SECRET}'", correct_sig),
            ("'wrong-secret'", wrong_sig),
            ("result", different),
        ])
        self.assertNotEqual(wrong_sig, f"sha256={EXPECTED_DIGEST}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
