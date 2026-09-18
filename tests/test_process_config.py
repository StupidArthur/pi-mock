import base64

import httpx
import pytest

from tests.process_utils import free_port, start_server, stop_server


def _basic(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_custom_config_applies(tmp_path):
    port = free_port()
    db_path = tmp_path / "custom.db"
    config_path = tmp_path / "custom.yaml"
    config_path.write_text(
        "\n".join(
            [
                "server:",
                "  host: 127.0.0.1",
                f"  port: {port}",
                "pi:",
                "  server_name: MY-CUSTOM-PI",
                "storage:",
                "  type: sqlite",
                f"  path: {db_path}",
                "logging:",
                "  level: INFO",
            ]
        ),
        encoding="utf-8",
    )
    base = f"http://127.0.0.1:{port}"
    process = start_server(["--config", str(config_path)], base)
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            body = client.get("/piwebapi/dataservers").json()
            assert body["Items"][0]["Name"] == "MY-CUSTOM-PI"
            assert body["Items"][0]["WebId"] == "SERVER_MY_CUSTOM_PI"
        assert db_path.exists()
    finally:
        stop_server(process)


def test_startup_auth_enabled_from_config(tmp_path):
    port = free_port()
    db_path = tmp_path / "auth.db"
    config_path = tmp_path / "auth.yaml"
    config_path.write_text(
        "\n".join(
            [
                "server:",
                "  host: 127.0.0.1",
                f"  port: {port}",
                "pi:",
                "  server_name: AUTH-PI",
                "auth:",
                "  enabled: true",
                "  type: basic",
                "  username: piuser",
                "  password: password123",
                "storage:",
                "  type: sqlite",
                f"  path: {db_path}",
            ]
        ),
        encoding="utf-8",
    )
    base = f"http://127.0.0.1:{port}"
    process = start_server(["--config", str(config_path)], base, env={})
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            assert client.get("/piwebapi/dataservers").status_code == 401
            response = client.get(
                "/piwebapi/dataservers", headers=_basic("piuser", "password123")
            )
            assert response.status_code == 200
            assert client.get("/mock/config").status_code == 200
    finally:
        stop_server(process)


def test_config_via_env_overrides(tmp_path):
    port = free_port()
    db_path = tmp_path / "env.db"
    base = f"http://127.0.0.1:{port}"
    process = start_server(
        [],
        base,
        env={
            "PI_HOST": "127.0.0.1",
            "PI_PORT": str(port),
            "PI_SERVER_NAME": "ENV-PI",
            "PI_STORAGE_TYPE": "sqlite",
            "PI_DB_PATH": str(db_path),
        },
    )
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            assert (
                client.get("/piwebapi/dataservers").json()["Items"][0]["Name"] == "ENV-PI"
            )
        assert db_path.exists()
    finally:
        stop_server(process)


def test_sqlite_creates_missing_directory(tmp_path):
    port = free_port()
    nested = tmp_path / "a" / "b" / "c" / "deep.db"
    base = f"http://127.0.0.1:{port}"
    process = start_server(
        [],
        base,
        env={
            "PI_HOST": "127.0.0.1",
            "PI_PORT": str(port),
            "PI_STORAGE_TYPE": "sqlite",
            "PI_DB_PATH": str(nested),
        },
    )
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            assert client.get("/health").json() == {"status": "ok"}
        assert nested.exists()
    finally:
        stop_server(process)
