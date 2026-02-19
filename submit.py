import hashlib
import hmac
import json
import os
from datetime import datetime, timezone

import requests

# Application details
NAME = "Scott Lewis"
EMAIL = "scott@atomiclotus.net"
RESUME_LINK = "https://docs.google.com/document/d/1V7ZAM7KlU6fJrQHFEolbHs3sPyxKlFRW/edit?usp=sharing&ouid=112606029007623001234&rtpof=true&sd=true"
REPOSITORY_LINK = "https://github.com/iconifyit/b12-application"

SUBMISSION_URL = "https://b12.io/apply/submission"
HMAC_KEY = "hello-there-from-b12"


def _utc_timestamp() -> str:
    """Return the current UTC time as an ISO 8601 string with milliseconds ending in 'Z'."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def build_payload() -> dict:
    """Build the application payload with all required fields."""
    github_repository = os.environ.get("GITHUB_REPOSITORY", "iconifyit/b12-application")
    github_run_id = os.environ.get("GITHUB_RUN_ID", "0")

    # Construct the action run link dynamically from GitHub environment variables
    action_run_link = f"https://github.com/{github_repository}/actions/runs/{github_run_id}"

    return {
        "action_run_link": action_run_link,
        "email": EMAIL,
        "name": NAME,
        "repository_link": REPOSITORY_LINK,
        "resume_link": RESUME_LINK,
        # ISO 8601 UTC timestamp with milliseconds ending in "Z"
        "timestamp": _utc_timestamp(),
    }


def serialize_payload(payload: dict) -> bytes:
    """Serialize payload as canonical JSON (sorted keys, no whitespace) encoded as UTF-8."""
    # Canonical JSON: no extra whitespace, keys sorted alphabetically, UTF-8 encoded
    json_str = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    return json_str.encode("utf-8")


def compute_signature(body: bytes) -> str:
    """Compute HMAC-SHA256 over the raw UTF-8 body and return 'sha256=<hex_digest>'."""
    # HMAC-SHA256 signature computed over the raw UTF-8-encoded JSON body
    signature = hmac.new(HMAC_KEY.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def submit(payload_bytes: bytes, signature: str) -> None:
    """POST the signed payload to the B12 submission endpoint and print the receipt."""
    headers = {"X-Signature-256": signature}
    response = requests.post(SUBMISSION_URL, data=payload_bytes, headers=headers)
    response.raise_for_status()
    receipt = response.json().get("receipt")
    if receipt is None:
        raise ValueError("No receipt in response")
    print(receipt)


if __name__ == "__main__":
    payload = build_payload()
    payload_bytes = serialize_payload(payload)
    signature = compute_signature(payload_bytes)
    submit(payload_bytes, signature)
