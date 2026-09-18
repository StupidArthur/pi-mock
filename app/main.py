import argparse
import asyncio
import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from starlette.types import ASGIApp, Receive, Scope, Send

from app import repository
from app.api import batch, dataservers, mock_control, points, streams
from app.core import auth, fault
from typing import Optional

from app.core.config import Settings, settings
from app.core.logging import configure_logging, get_logger
from app.services import point_service

logger = get_logger("mock_pi.requests")

JSON_HEADERS = [(b"content-type", b"application/json")]


async def _send_json(send: Send, status: int, payload: dict, extra=None) -> None:
    body = json.dumps(payload).encode("utf-8")
    headers = list(JSON_HEADERS) + [(b"content-length", str(len(body)).encode())]
    if extra:
        headers.extend(extra)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


async def _send_raw(send: Send, status: int, body: bytes, extra=None) -> None:
    headers = list(JSON_HEADERS) + [(b"content-length", str(len(body)).encode())]
    if extra:
        headers.extend(extra)
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def _headers_dict(scope: Scope) -> dict:
    result = {}
    for key, value in scope.get("headers", []):
        result[key.decode("latin-1").lower()] = value.decode("latin-1")
    return result


def _extract_tag(path: str):
    parts = [part for part in path.split("/") if part]
    if "streams" in parts:
        index = parts.index("streams")
        if len(parts) > index + 1:
            return parts[index + 1]
    if "points" in parts:
        index = parts.index("points")
        if len(parts) > index + 1:
            return parts[index + 1]
    return None


def _modify_body(body: bytes) -> bytes:
    omit = fault.state.config.omit_fields
    if not omit:
        return body
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return body
    if isinstance(data, dict):
        for field in omit:
            data.pop(field, None)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for field in omit:
                    item.pop(field, None)
    return json.dumps(data).encode("utf-8")


class FaultMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope["path"]
        method = scope["method"]
        config = fault.state.config
        is_pi = path.startswith("/piwebapi")
        is_managed = path.startswith("/mock") or path == "/health"

        if is_pi and not is_managed:
            if not auth.check_auth(_headers_dict(scope)):
                await _send_json(
                    send,
                    401,
                    {"Errors": ["Authentication failed."]},
                    extra=[(b"www-authenticate", b'Basic realm="PI Web API"')],
                )
                self._record(scope, 401, 0.0)
                return

            endpoint_fault = fault.state.match_fault(method, path)
            delay = config.delay_ms
            if endpoint_fault and endpoint_fault.delay_ms:
                delay = max(delay, endpoint_fault.delay_ms)
            if delay:
                await asyncio.sleep(delay / 1000.0)

            forced_status = None
            if endpoint_fault and endpoint_fault.status:
                forced_status = endpoint_fault.status
            elif config.force_status:
                forced_status = config.force_status
            if forced_status:
                await _send_json(
                    send, forced_status, {"Errors": [f"Injected status {forced_status}."]}
                )
                self._record(scope, forced_status, delay)
                return

            if config.drop_connection:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [(b"content-length", b"100000")],
                    }
                )
                self._record(scope, 0, delay)
                return

            if config.invalid_json:
                await _send_raw(send, 200, b'{"Timestamp": ')
                self._record(scope, 200, delay)
                return

        started = time.perf_counter()
        status_holder = {"status": 500}
        omit_active = is_pi and bool(config.omit_fields)
        chunks = []
        start_message = {}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                if omit_active:
                    start_message.update(message)
                    return
            if message["type"] == "http.response.body":
                if omit_active:
                    chunks.append(message.get("body", b""))
                    return
            await send(message)

        await self.app(scope, receive, send_wrapper)

        if omit_active:
            body = _modify_body(b"".join(chunks))
            headers = [
                (key, value)
                for key, value in start_message.get("headers", [])
                if key.lower() != b"content-length"
            ]
            headers.append((b"content-length", str(len(body)).encode()))
            await send(
                {
                    "type": "http.response.start",
                    "status": start_message.get("status", status_holder["status"]),
                    "headers": headers,
                }
            )
            await send({"type": "http.response.body", "body": body})

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if is_pi:
            self._record(scope, status_holder["status"], elapsed_ms)

    def _record(self, scope: Scope, status: int, elapsed_ms: float) -> None:
        request_id = fault.state.next_request_id()
        client = scope.get("client") or ("unknown", 0)
        entry = {
            "RequestId": request_id,
            "Method": scope["method"],
            "Path": scope["path"],
            "Query": scope.get("query_string", b"").decode("latin-1"),
            "Status": status,
            "Timestamp": datetime.now(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%S")
            + ".000Z",
            "ElapsedMs": round(elapsed_ms, 3),
            "Client": client[0],
            "Tag": _extract_tag(scope["path"]),
            "UserAgent": _headers_dict(scope).get("user-agent"),
        }
        fault.state.record_request(entry)
        logger.info(
            "request_id=%s client=%s %s %s status=%s elapsed=%.0fms tag=%s",
            request_id,
            client[0],
            scope["method"],
            scope["path"],
            status,
            elapsed_ms,
            entry["Tag"],
        )


def create_app(runtime: Optional[Settings] = None) -> FastAPI:
    from app.core import config as config_module

    active = runtime or settings
    config_module.settings = active

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        configure_logging(active.log_level)
        repository.init_repo(active)
        point_service.bootstrap(active)
        logger.info(
            "Mock PI Server started server=%s storage=%s db=%s",
            active.server_name,
            active.storage_type,
            active.db_path,
        )
        yield

    application = FastAPI(
        title="Mock PI Web API",
        version="1.0",
        description="PI Web API compatible mock for testing",
        lifespan=lifespan,
    )
    application.add_middleware(FaultMiddleware)

    application.include_router(mock_control.router)
    application.include_router(dataservers.router)
    application.include_router(points.router)
    application.include_router(streams.router)
    application.include_router(batch.router)

    @application.get("/health")
    def health():
        return {"status": "ok"}

    @application.get("/piwebapi")
    def root():
        return {
            "ProductTitle": "Mock PI Web API",
            "Version": "1.0",
            "Links": {
                "DataServers": "/piwebapi/dataservers",
                "Points": "/piwebapi/points",
                "Streams": "/piwebapi/streams",
                "Batch": "/piwebapi/batch",
            },
        }

    return application


app = create_app(settings)


def run() -> None:
    parser = argparse.ArgumentParser(description="Mock PI Server")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--config", default=None)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--ssl-keyfile", default=None)
    parser.add_argument("--ssl-certfile", default=None)
    args = parser.parse_args()

    runtime = Settings.load(args.config, verbose=args.verbose)
    if args.host:
        runtime.host = args.host
    if args.port:
        runtime.port = args.port
    level = "DEBUG" if args.verbose else runtime.log_level
    configure_logging(level)

    import uvicorn

    application = create_app(runtime)

    uvicorn.run(
        application,
        host=runtime.host,
        port=runtime.port,
        log_level=level.lower(),
        reload=False,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile,
    )


if __name__ == "__main__":
    run()
