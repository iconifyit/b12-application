# B12 Application Instructions

To submit an application, create the following Python script that is executed 
via a GitHub Action (or continuous integration on any other Git forge). The script should:

POST to https://b12.io/apply/submission with the following 
JSON-encoded payload in the body. All fields are required:

```json
{
    "timestamp"       : "2026-01-06T16:59:37.571Z",
    "name"            : "Your name",
    "email"           : "you@example.com",
    "resume_link"     : "https://pdf-or-html-or-linkedin.example.com",
    "repository_link" : "https://link-to-github-or-other-forge.example.com/your/repository",
    "action_run_link" : "https://link-to-github-or-another-forge.example.com/your/repository/actions/runs/run_id"
}
```

1. Make the timestamp an ISO 8601 timestamp
2. The action_run_link is a page similar to https://github.com/marcua/ayb/actions/runs/20561457327 (might differ if you’re using a forge other than GitHub), which allows us to see the continuous integration run that POSTed to B12
3. We’ve pretty-printed for readability here, but the post body should contain no extra whitespace (compact separators), 
4. have keys sorted alphabetically, 
5. and be UTF-8-encoded. For example, the canonicalized payload above is

```json
{"action_run_link":"https://link-to-github-or-another-forge.example.com/your/repository/actions/runs/run_id","email":"you@example.com","name":"Your name","repository_link":"https://link-to-github-or-other-forge.example.com/your/repository","resume_link":"https://pdf-or-html-or-linkedin.example.com","timestamp":"2026-01-06T16:59:37.571Z"}
```

6. Include a header called X-Signature-256 in the post request
7. The value of the header should be sha256={hex-digest}, where the hex digest is the HMAC-SHA256 of the raw UTF-8-encoded JSON request body, using the signing secret as the key.
8. Use a signing secret of `*******` (See .env file for signing secret) (yes, it’s public, but treat it like a secret in your implementation ;) )

As an example, the payload above will have a hex digest of `c5db257a56e3c258ec1162459c9a295280871269f4cf70146d2c9f1b52671d45`

- If the POST is successful, you will receive an HTTP 200 with a response of `{"success": true, "receipt": "your-submission-receipt"}`
- Print that receipt in your continuous integration task
- To confirm your submission, copy/paste the receipt into the field below