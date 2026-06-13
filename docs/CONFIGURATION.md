# Configuration

KALYX is designed to run from a local checkout with minimal configuration. No
environment variables are required for the default CLI workflow.

## Environment Variables

| Variable | Required | Purpose | Default when absent | Example |
| --- | --- | --- | --- | --- |
| `KALYX_API_KEY` | No | Protects FastAPI operational endpoints such as ingestion, verification, and detection with the `X-KALYX-API-Key` request header. | Protected endpoints are allowed without an API key for local development. | `example-dev-key` |

## Local Example

`.env.example` is a non-secret reference file. KALYX does not automatically load
dotenv files, so export the variable in your shell or configure it in your process
manager. Do not commit real secrets.

```bash
export KALYX_API_KEY=example-dev-key
kalyx-api
```

Authenticated API request:

```bash
curl -X POST http://127.0.0.1:8000/verify \
  -H 'X-KALYX-API-Key: example-dev-key'
```

This API key mechanism is lightweight local API protection. It is not user
authentication, sessions, OAuth, JWT, RBAC, source attestation, or protection
against full host compromise.
