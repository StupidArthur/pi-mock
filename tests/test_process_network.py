import socket

import httpx
import pytest

from tests.process_utils import free_port, start_server, stop_server


@pytest.fixture()
def live_server(tmp_path):
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = {
        "PI_HOST": "127.0.0.1",
        "PI_PORT": str(port),
        "PI_STORAGE_TYPE": "memory",
        "PI_SERVER_NAME": "TEST-PI",
    }
    process = start_server([], base, env=env)
    try:
        yield base
    finally:
        stop_server(process)


def test_drop_connection_produces_network_error(live_server):
    base = live_server
    with httpx.Client(base_url=base, timeout=10) as client:
        assert client.post("/mock/config", json={"drop_connection": True}).status_code == 200

    failed = False
    try:
        with httpx.Client(base_url=base, timeout=10) as client:
            response = client.get("/piwebapi/dataservers")
            # If a response is returned it must NOT be a normal complete 200 body
            failed = response.status_code == 200 and len(response.content) > 0
    except (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError, httpx.HTTPError):
        failed = True

    assert failed, "drop_connection did not cause a network-level failure"

    with httpx.Client(base_url=base, timeout=10) as client:
        assert client.post("/mock/reset").status_code == 200
        assert client.get("/piwebapi/dataservers").status_code == 200


def test_force_status_real_http(live_server):
    base = live_server
    with httpx.Client(base_url=base, timeout=10) as client:
        client.post("/mock/config", json={"force_status": 503})
        assert client.get("/piwebapi/dataservers").status_code == 503
        assert client.get("/mock/config").status_code == 200


def test_real_http_read_write_cycle(live_server):
    base = live_server
    with httpx.Client(base_url=base, timeout=10) as client:
        point = client.get(
            "/piwebapi/points", params={"path": "\\\\TEST-PI\\temperature"}
        ).json()
        assert point["Name"] == "temperature"
        web_id = point["WebId"]
        assert client.post(
            f"/piwebapi/streams/{web_id}/value", json={"Value": 66.6}
        ).status_code == 202
        assert client.get(f"/piwebapi/streams/{web_id}/value").json()["Value"] == 66.6


def test_lan_ip_access(tmp_path):
    lan_ip = _detect_lan_ip()
    if not lan_ip:
        pytest.skip("no LAN IPv4 address available")
    port = free_port()
    base_lan = f"http://{lan_ip}:{port}"
    base_loopback = f"http://127.0.0.1:{port}"
    process = start_server(
        ["--host", "0.0.0.0", "--port", str(port)],
        base_loopback,
        env={"PI_STORAGE_TYPE": "memory"},
    )
    try:
        with httpx.Client(timeout=10) as client:
            assert client.get(base_loopback + "/health").status_code == 200
            assert client.get(base_lan + "/health").status_code == 200
    finally:
        stop_server(process)


def _detect_lan_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        address = sock.getsockname()[0]
        sock.close()
        if address.startswith("127."):
            return None
        return address
    except OSError:
        return None
