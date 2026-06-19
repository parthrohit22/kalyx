# Configuration

KALYX is designed to run from a local checkout with minimal configuration. No
environment variables are required for the default CLI workflow.

## Environment Variables

| Variable | Required | Purpose | Default when absent | Example |
| --- | --- | --- | --- | --- |
| `KALYX_API_KEY` | No | Protects FastAPI operational endpoints such as ingestion, verification, and detection with the `X-KALYX-API-Key` request header. | Protected endpoints are allowed without an API key for local development. | `example-dev-key` |
| `KALYX_ANCHOR_URL` | No | Raspberry Pi or local anchor service URL used by `kalyx anchor`, `kalyx anchor-status`, `GET /anchor/status`, and `POST /anchor`. | `http://127.0.0.1:8081` | `http://192.168.1.50:8081` |
| `KALYX_LEDGER_ID` | No | Ledger identifier submitted to and queried from the anchor service. | `kalyx-main-host` | `kalyx-demo` |

## Local Example

`.env.example` is a non-secret reference file. KALYX does not automatically load
dotenv files, so export the variable in your shell or configure it in your process
manager. Do not commit real secrets.

```bash
export KALYX_API_KEY=example-dev-key
export KALYX_ANCHOR_URL=http://127.0.0.1:8081
export KALYX_LEDGER_ID=kalyx-main-host
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

## Anchor Configuration

The host API and CLI use the same anchor configuration:

```bash
export KALYX_ANCHOR_URL=http://<pi-ip>:8081
export KALYX_LEDGER_ID=kalyx-demo
```

`KALYX_ANCHOR_URL` is read by the host process. It should point from the host running `kalyx-api` to the Raspberry Pi anchor service. Angular does not use this value and should not be configured to call the Pi directly.

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

Demo environments may need a reachable host address instead of localhost. For example, the AT3 UTM setup points Angular at the UTM host API:

```ts
export const environment = {
  kalyxApi: {
    apiBaseUrl: 'http://192.168.64.2:8000',
    apiKey: '',
  },
} as const;
```

This is still Angular-to-host communication. Host-to-Pi anchoring remains controlled by `KALYX_ANCHOR_URL`.

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
