"""POST a signed application payload to the B12 submission endpoint."""

import hashlib
import hmac
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone

import requests

# ── Application details ─────────────────────────────────────────────
NAME            = "Scott Lewis"
EMAIL           = "scott@sketchandbuild.com"
REPOSITORY_LINK = "https://github.com/iconifyit/b12-application"
RESUME_LINK     = "https://sketchandbuild.com/assets/b12/resume.pdf"
SUBMISSION_URL  = "https://b12.io/apply/submission"

# ── Request settings ────────────────────────────────────────────────
CONNECT_TIMEOUT = 5      # seconds to establish a connection
READ_TIMEOUT = 15        # seconds to wait for a response body
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0    # seconds; doubles each retry
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

log = logging.getLogger(__name__)


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
    """POST the signed payload with retry/backoff and return the receipt.

    Retries on transient network errors and retryable HTTP status codes
    (429, 5xx) using exponential backoff. Raises immediately on client
    errors (4xx other than 429) since those indicate a bad payload or
    signature and retrying won't help.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Signature-256": signature,
    }

    last_exception: BaseException | None = None
    backoff = INITIAL_BACKOFF

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info("POST %s (attempt %d/%d)", SUBMISSION_URL, attempt, MAX_RETRIES)
            resp = requests.post(
                SUBMISSION_URL,
                data=payload_bytes,
                headers=headers,
                timeout=(CONNECT_TIMEOUT, READ_TIMEOUT),
            )

            if resp.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                log.warning(
                    "Retryable HTTP %d on attempt %d; backing off %.1fs",
                    resp.status_code, attempt, backoff,
                )
                time.sleep(backoff)
                backoff *= 2
                continue

            resp.raise_for_status()

            data = resp.json()
            receipt = data.get("receipt")
            if receipt is None:
                raise ValueError(f"No receipt in response: {data}")
            return receipt

        except requests.ConnectionError as exc:
            last_exception = exc
            if attempt < MAX_RETRIES:
                log.warning(
                    "Connection error on attempt %d; backing off %.1fs: %s",
                    attempt, backoff, exc,
                )
                time.sleep(backoff)
                backoff *= 2
            else:
                raise

        except requests.Timeout as exc:
            last_exception = exc
            if attempt < MAX_RETRIES:
                log.warning(
                    "Timeout on attempt %d; backing off %.1fs: %s",
                    attempt, backoff, exc,
                )
                time.sleep(backoff)
                backoff *= 2
            else:
                raise

    # Should only be reached if all retries returned a retryable status code
    raise requests.HTTPError(
        f"All {MAX_RETRIES} attempts failed (last status: {resp.status_code})",
        response=resp,
    )


# ── Main ─────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        format="%(asctime)s [%(levelname)s] %(message)s",
        level=logging.INFO,
    )

    secret = os.environ.get("SIGNING_SECRET")
    if not secret:
        log.error("SIGNING_SECRET environment variable is not set.")
        sys.exit(1)

    payload = build_payload()
    body = canonicalize(payload)
    signature = sign(body, secret)

    log.info("Payload: %s", body.decode("utf-8"))
    log.info("Signature: %s", signature)

    try:
        receipt = submit(body, signature)
    except requests.HTTPError as exc:
        log.error("Submission failed with HTTP error: %s", exc)
        sys.exit(2)
    except requests.ConnectionError as exc:
        log.error("Could not connect to %s: %s", SUBMISSION_URL, exc)
        sys.exit(3)
    except requests.Timeout as exc:
        log.error("Request to %s timed out: %s", SUBMISSION_URL, exc)
        sys.exit(4)
    except ValueError as exc:
        log.error("Unexpected response: %s", exc)
        sys.exit(5)

    print(receipt)


if __name__ == "__main__":
    main()
