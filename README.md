# B12 Application Submission

This project submits a job application payload to B12 via a GitHub Actions workflow.

## What it does

`submit.py` builds a JSON payload containing applicant details, signs it with an HMAC-SHA256
signature, and POSTs it to `https://b12.io/apply/submission`. On success, it prints the
`receipt` value returned by the server.

## Canonical JSON serialization

The payload is serialized using `json.dumps` with `separators=(',', ':')` and `sort_keys=True`.
This produces compact JSON (no extra whitespace) with alphabetically sorted keys — a consistent,
deterministic byte representation required for a valid HMAC signature.

## HMAC signature generation

The HMAC-SHA256 signature is computed over the raw UTF-8-encoded JSON body using the key
`"hello-there-from-b12"`. The resulting hex digest is included in the request as:

```
X-Signature-256: sha256=<hex_digest>
```

This allows the server to verify the integrity and authenticity of the request body.

## How the GitHub Action constructs `action_run_link`

The workflow runs on `workflow_dispatch` (manual trigger only). During execution, GitHub
populates `GITHUB_REPOSITORY` (e.g. `owner/repo`) and `GITHUB_RUN_ID` automatically.
`submit.py` reads these environment variables to construct:

```
https://github.com/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}
```

## Running manually

Trigger the workflow from the **Actions** tab in GitHub by selecting **Apply to B12** and
clicking **Run workflow**.
