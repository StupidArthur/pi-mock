import httpx
import pytest

from tests.process_utils import free_port, start_server, stop_server


@pytest.fixture()
def server_env(tmp_path):
    port = free_port()
    db_path = tmp_path / "persist.db"
    base = f"http://127.0.0.1:{port}"
    files = []
    env = {
        "PI_STORAGE_TYPE": "sqlite",
        "PI_DB_PATH": str(db_path),
        "PI_SERVER_NAME": "TEST-PI",
    }
    args = ["--host", "127.0.0.1", "--port", str(port)]

    def _launch(**overrides):
        merged = dict(env)
        merged.update(overrides)
        return start_server(args, base, env=merged)

    yield base, str(db_path), _launch
    for process in files:
        stop_server(process)


def test_sqlite_survives_process_restart(server_env):
    base, db_path, launch = server_env

    process = launch()
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            response = client.post(
                "/piwebapi/streams/POINT_TEMP_001/value",
                json={"Timestamp": "2026-09-18T12:00:00Z", "Value": 424.2},
            )
            assert response.status_code == 202
            assert (
                client.get("/piwebapi/streams/POINT_TEMP_001/value").json()["Value"]
                == 424.2
            )
    finally:
        stop_server(process)

    process = launch()
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            body = client.get("/piwebapi/streams/POINT_TEMP_001/value").json()
            assert body["Value"] == 424.2
            assert body["Timestamp"] == "2026-09-18T12:00:00.000Z"
    finally:
        stop_server(process)


def test_sqlite_reset_restores_defaults(server_env):
    base, db_path, launch = server_env
    process = launch()
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            client.post("/piwebapi/streams/POINT_TEMP_001/value", json={"Value": 424.2})
            assert (
                client.get("/piwebapi/streams/POINT_TEMP_001/value").json()["Value"]
                == 424.2
            )
            assert client.post("/mock/reset").json() == {"success": True}
            value = client.get("/piwebapi/streams/POINT_TEMP_001/value").json()
            assert value["Value"] == 25.5
            assert (
                client.get("/piwebapi/streams/POINT_TEMP_001/recorded").json()["Items"]
                == []
            )
    finally:
        stop_server(process)


def test_sqlite_reset_persists_across_delete(server_env):
    base, db_path, launch = server_env
    process = launch()
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            client.post("/piwebapi/streams/POINT_TEMP_001/value", json={"Value": 7.7})
            client.post("/mock/reset")
    finally:
        stop_server(process)

    process = launch()
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            assert (
                client.get("/piwebapi/streams/POINT_TEMP_001/value").json()["Value"]
                == 25.5
            )
    finally:
        stop_server(process)
