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

## Frontend API Configuration

The Angular operations console reads frontend API settings from:

```text
frontend/src/environments/environment.ts
```

Default local configuration:

```ts
export const environment = {
  kalyxApi: {
    apiBaseUrl: 'http://127.0.0.1:8000',
    apiKey: '',
  },
} as const;
```

Fields:

| Field | Required | Purpose | Default behavior |
| --- | --- | --- | --- |
| `kalyxApi.apiBaseUrl` | Yes | FastAPI base URL used by the Angular `KalyxApiService`. | Points at local FastAPI on `http://127.0.0.1:8000`. |
| `kalyxApi.apiKey` | No | Optional value sent as `X-KALYX-API-Key` on frontend API requests. | Blank means no API key header is sent. |

For protected backend deployments:

```ts
export const environment = {
  kalyxApi: {
    apiBaseUrl: 'http://127.0.0.1:8000',
    apiKey: 'example-dev-key',
  },
} as const;
```

Frontend API configuration is visible to anyone who can inspect the built
JavaScript bundle. Treat it as local coursework/demo configuration, not secure
secret storage. Do not use it as a replacement for real user authentication.
