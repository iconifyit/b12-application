"""POST a signed application payload to the B12 submission endpoint."""

import hashlib
import hmac
import json
import os
import sys
from datetime import datetime, timezone

import requests

# ── Application details ─────────────────────────────────────────────
NAME = "Scott Lewis"
EMAIL = "scott@sketchandbuild.com"
RESUME_LINK = "https://example.com/resume-placeholder"
REPOSITORY_LINK = "https://github.com/iconifyit/b12-application"

SUBMISSION_URL = "https://b12.io/apply/submission"


# ── Helpers ──────────────────────────────────────────────────────────

def utc_timestamp() -> str:
    """Return the current UTC time as ISO 8601 with milliseconds, ending in 'Z'."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def build_payload() -> dict:
    """Assemble the application payload from env vars and constants."""
    repo = os.environ.get("GITHUB_REPOSITORY", "iconifyit/b12-application")
    run_id = os.environ.get("GITHUB_RUN_ID", "0")
    action_run_link = f"https://github.com/{repo}/actions/runs/{run_id}"

    return {
        "action_run_link": action_run_link,
        "email": EMAIL,
        "name": NAME,
        "repository_link": REPOSITORY_LINK,
        "resume_link": RESUME_LINK,
        "timestamp": utc_timestamp(),
    }


def canonicalize(payload: dict) -> bytes:
    """Serialize payload as compact, key-sorted JSON encoded to UTF-8."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def sign(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 and return 'sha256=<hex_digest>'."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def submit(payload_bytes: bytes, signature: str) -> str:
    """POST the signed payload and return the receipt string."""
    headers = {
        "Content-Type": "application/json",
        "X-Signature-256": signature,
    }
    resp = requests.post(SUBMISSION_URL, data=payload_bytes, headers=headers)
    resp.raise_for_status()
    data = resp.json()
    receipt = data.get("receipt")
    if receipt is None:
        raise ValueError(f"No receipt in response: {data}")
    return receipt


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    secret = os.environ.get("SIGNING_SECRET")
    if not secret:
        print("ERROR: SIGNING_SECRET environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    payload = build_payload()
    body = canonicalize(payload)
    signature = sign(body, secret)

    print(f"Payload: {body.decode('utf-8')}")
    print(f"Signature: {signature}")

    receipt = submit(body, signature)
    print(f"Receipt: {receipt}")


if __name__ == "__main__":
    main()
