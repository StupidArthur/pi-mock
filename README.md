# Mock PI Server

PI Web API compatible mock for testing.

A controllable, scriptable mock server that emulates the commonly used behaviour of
AVEVA / OSIsoft PI Web API so that clients with a PI data source connection can be
tested without a real PI Data Archive / PI Web API Server.

## Purpose

- Provide deterministic PI Web API endpoints for functional testing.
- Inject faults (HTTP errors, delays, invalid JSON, bad quality, timestamps, large data).
- Control everything at runtime through a management API (`/mock/*`) so tests never need
  to edit files or restart the process.

## What this project does NOT do

- It does **not** implement the private PI Data Archive protocol on TCP 5450.
- It is **not** 100% PI compatible and is **not** a PI Server replacement.
- It does **not** implement the real AF data model (AF Database, Element, Attribute,
  Event Frame, Analysis, Notification).
- AF SDK, PI SDK, PI API, ODBC/JDBC are out of scope.

The TCP 5450 component only simulates network faults (accept / close / hang / reset).

## Requirements

- Python >= 3.11
- See `requirements.txt` (FastAPI, Uvicorn, Pydantic, PyYAML, httpx, pytest)

## Install

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m app.main
```

or:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

With verbose protocol inspection (headers, User-Agent, auth, URL):

```bash
python -m app.main --verbose
```

### Default URLs

| Purpose        | URL                                    |
| -------------- | -------------------------------------- |
| PI Web API     | http://127.0.0.1:8080/piwebapi         |
| Mock control   | http://127.0.0.1:8080/mock             |
| Health check   | http://127.0.0.1:8080/health           |

## Docker

```bash
docker compose up -d
curl http://localhost:8080/health
```

Ports `8080` (HTTP) and `5450` (TCP fault) are published. A Docker healthcheck polls
`GET /health`.

## Default Server and Tags

```text
Name  = TEST-PI
WebId = SERVER_TEST_PI
Path  = \\TEST-PI
Port  = 5450
```

| Tag           | WebId             | Type    | Units |
| ------------- | ----------------- | ------- | ----- |
| sinusoid      | POINT_SIN_001     | Float32 |       |
| temperature   | POINT_TEMP_001    | Float32 | degC  |
| pressure      | POINT_PRESS_001   | Float32 | kPa   |
| flow          | POINT_FLOW_001    | Float32 | L/min |
| status        | POINT_STATUS_001  | String  |       |
| counter       | POINT_COUNT_001   | Int32   | count |
| bad_quality   | POINT_BAD_001     | Float32 | degC  |
| empty_tag     | POINT_EMPTY       | Float32 | degC  |

`bad_quality` is Good=false / Questionable=true by default.
`empty_tag` has a point but no snapshot or history (reads return empty, never 404).

## Read Data Examples

Point by path:

```bash
curl "http://127.0.0.1:8080/piwebapi/points?path=%5C%5CTEST-PI%5Ctemperature"
```

Current value:

```bash
curl http://127.0.0.1:8080/piwebapi/streams/POINT_TEMP_001/value
```

Recorded values:

```bash
curl "http://127.0.0.1:8080/piwebapi/streams/POINT_TEMP_001/recorded?startTime=2026-01-01T00:00:00Z&endTime=2026-01-01T01:00:00Z&maxCount=100"
```

## Write Data Examples

Write current value:

```bash
curl -X POST http://127.0.0.1:8080/piwebapi/streams/POINT_TEMP_001/value \
  -H "Content-Type: application/json" \
  -d '{"Timestamp":"2026-09-18T10:30:00Z","Value":27.6}'
```

Batch write recorded values:

```bash
curl -X POST http://127.0.0.1:8080/piwebapi/streams/POINT_TEMP_001/recorded \
  -H "Content-Type: application/json" \
  -d '[{"Timestamp":"2026-09-18T10:30:00Z","Value":20.1},{"Timestamp":"2026-09-18T10:31:00Z","Value":20.2}]'
```

## Large Data Generation

```bash
curl -X POST http://127.0.0.1:8080/mock/data/generate \
  -H "Content-Type: application/json" \
  -d '{"tag":"temperature","start":"2026-01-01T00:00:00Z","count":100000,"interval_ms":1000,"generator":"sin"}'
```

Generators: `sin`, `linear`, `random`, `step`, `constant`.
Timestamp modes: `normal`, `epoch`, `future`, `no_tz`, `bad_format`, `null` (`timestamp_mode`).

## Fault Injection Examples

Force HTTP 500 for all PI endpoints (management API stays available):

```bash
curl -X POST http://127.0.0.1:8080/mock/config \
  -H "Content-Type: application/json" -d '{"force_status":500}'
```

Delay all PI requests by 30s:

```bash
curl -X POST http://127.0.0.1:8080/mock/config \
  -H "Content-Type: application/json" -d '{"delay_ms":30000}'
```

Invalid JSON, dropped connection, omitted fields, history order:

```bash
curl -X POST http://127.0.0.1:8080/mock/config \
  -H "Content-Type: application/json" \
  -d '{"invalid_json":true,"omit_fields":["Timestamp","Good"],"history_order":"desc"}'
```

Endpoint-level fault (only that path):

```bash
curl -X POST http://127.0.0.1:8080/mock/fault \
  -H "Content-Type: application/json" \
  -d '{"method":"GET","path":"/piwebapi/streams/POINT_TEMP_001/value","status":500,"delay_ms":10000}'
```

Bad quality for a tag:

```bash
curl -X POST http://127.0.0.1:8080/mock/tags/temperature/quality \
  -H "Content-Type: application/json" \
  -d '{"good":false,"questionable":true,"substituted":false}'
```

## Authentication Example

```bash
curl -X POST http://127.0.0.1:8080/mock/config \
  -H "Content-Type: application/json" \
  -d '{"auth_enabled":true,"auth_type":"basic","username":"piuser","password":"password123"}'

curl -u piuser:password123 http://127.0.0.1:8080/piwebapi/dataservers
```

Wrong credentials return `401 Unauthorized`. `/mock/*` is never protected.

## HTTPS Example

Generate a self-signed certificate and start with TLS:

```bash
mkdir cert
openssl req -x509 -newkey rsa:2048 -nodes -keyout cert/server.key \
  -out cert/server.crt -days 365 -subj "/CN=localhost"

python -m app.main --port 8443 --ssl-keyfile ./cert/server.key --ssl-certfile ./cert/server.crt
```

Equivalent uvicorn form:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile ./cert/server.key --ssl-certfile ./cert/server.crt
```

## Reset

```bash
curl -X POST http://127.0.0.1:8080/mock/reset
```

Restores default server/tags, deletes test writes, disables fault injection, restores
authentication defaults, delay and status codes. Response: `{"success": true}`.

## Request History

```bash
curl http://127.0.0.1:8080/mock/requests
curl -X DELETE http://127.0.0.1:8080/mock/requests
```

Each entry includes Method, Path, Query, Status, Timestamp, ElapsedMs, Client, Tag,
UserAgent. This lets automation confirm whether the client actually contacted the server.

## Configuration

`config/default.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8080
pi:
  server_name: TEST-PI
auth:
  enabled: false
storage:
  type: sqlite
logging:
  level: INFO
```

Environment variables override YAML: `PI_HOST`, `PI_PORT`, `PI_SERVER_NAME`,
`PI_AUTH_ENABLED`, `PI_STORAGE_TYPE`, `PI_DB_PATH`, `PI_LOG_LEVEL`.

Storage modes: `sqlite` (default, survives restart) and `memory` (wiped on restart,
convenient for tests).

## pytest

```bash
pytest -v
```

Expected: `0 failed`.

## Smoke Test

```bash
bash scripts/smoke_test.sh
```

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
```

Outputs `Mock PI Server smoke test PASSED` when all checks pass.

## TCP Fault Server (5450)

Network-only fault simulation. It does **not** answer with any PI protocol data.

```bash
python tcp_fault_server/server.py --host 0.0.0.0 --port 5450 --mode close
```

Modes: `accept`, `close`, `hang`, `reset`, `random-close`.

- `close`: accept then immediately close (tests disconnect/reconnect).
- `hang`: accept then never read/write/close (tests read/handshake timeout).
- `reset`: force an RST.
- `random-close`: randomly close or hang.

## Client Verification Flow

1. Start the Mock PI Web API.
2. Watch whether the client contacts 8080/8443.
3. Check `GET /mock/requests`.
4. If HTTP requests appear, the client uses PI Web API — continue compatibility testing.
5. If not, listen on TCP 5450 to detect AF SDK / PI SDK / PI API usage.
6. Use the TCP Fault Server to verify timeout / disconnect / retry behaviour.
7. Real PI reads/writes still require a genuine PI Test Server.

## Project Layout

```text
app/
  main.py              FastAPI app, fault middleware, CLI entry
  api/                 dataservers, points, streams, batch, mock_control
  core/                config, auth, fault, logging
  models/              point, value, mock schemas
  services/            point_service, stream_service, data_generator
  repository/          memory, sqlite
tcp_fault_server/      network fault simulator
tests/                 pytest suite
config/default.yaml    configuration
data/example.json      seed data
scripts/               smoke tests
```
