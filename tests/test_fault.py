import time

import pytest


def test_force_status(client):
    client.post("/mock/config", json={"force_status": 500})
    assert client.get("/piwebapi/dataservers").status_code == 500
    assert client.get("/mock/config").status_code == 200
    assert client.get("/health").status_code == 200


def test_force_status_503(client):
    client.post("/mock/config", json={"force_status": 503})
    assert client.get("/piwebapi/points").status_code == 503


def test_invalid_json(client):
    client.post("/mock/config", json={"invalid_json": True})
    response = client.get("/piwebapi/streams/POINT_TEMP_001/value")
    assert response.status_code == 200
    with pytest.raises(Exception):
        response.json()


def test_omit_fields(client):
    client.post("/mock/config", json={"omit_fields": ["Timestamp", "Good"]})
    body = client.get("/piwebapi/streams/POINT_TEMP_001/value").json()
    assert "Timestamp" not in body
    assert "Good" not in body
    assert "Value" in body


def test_delay(client):
    client.post("/mock/config", json={"delay_ms": 300})
    start = time.perf_counter()
    response = client.get("/piwebapi/dataservers")
    elapsed = (time.perf_counter() - start) * 1000
    assert response.status_code == 200
    assert elapsed >= 250
    start = time.perf_counter()
    client.get("/mock/config")
    assert (time.perf_counter() - start) * 1000 < 250


def test_delay_bounds(client):
    assert client.post("/mock/config", json={"delay_ms": 999999}).status_code == 422
    assert client.post("/mock/config", json={"delay_ms": -1}).status_code == 422


def test_endpoint_fault(client):
    client.post(
        "/mock/fault",
        json={"method": "GET", "path": "/piwebapi/streams/POINT_TEMP_001/value", "status": 500},
    )
    assert client.get("/piwebapi/streams/POINT_TEMP_001/value").status_code == 500
    assert client.get("/piwebapi/streams/POINT_SIN_001/value").status_code == 200


def test_endpoint_fault_delay_and_times(client):
    client.post(
        "/mock/fault",
        json={
            "method": "GET",
            "path": "/piwebapi/dataservers",
            "status": 502,
            "times": 1,
        },
    )
    assert client.get("/piwebapi/dataservers").status_code == 502
    assert client.get("/piwebapi/dataservers").status_code == 200


def test_reset_clears_faults(client):
    client.post("/mock/config", json={"force_status": 500, "delay_ms": 1000})
    client.post("/mock/fault", json={"method": "GET", "path": "/piwebapi/points", "status": 503})
    client.post("/mock/reset")
    assert client.get("/piwebapi/dataservers").status_code == 200
    assert client.get("/piwebapi/points").status_code == 200
    assert client.get("/mock/config").json()["force_status"] is None
    assert client.get("/mock/config").json()["delay_ms"] == 0


def test_reset_restores_quality_and_data(client):
    client.post(
        "/mock/tags/temperature/quality",
        json={"good": False, "questionable": True, "substituted": True},
    )
    assert client.get("/piwebapi/streams/POINT_TEMP_001/value").json()["Good"] is False
    client.post(
        "/piwebapi/streams/POINT_TEMP_001/value", json={"Value": 999.0}
    )
    client.post("/mock/reset")
    value = client.get("/piwebapi/streams/POINT_TEMP_001/value").json()
    assert value["Value"] == 25.5
    assert value["Good"] is True
    assert value["Questionable"] is False
    assert client.get("/piwebapi/streams/POINT_TEMP_001/recorded").json()["Items"] == []


def test_bad_quality_tag(client):
    body = client.get("/piwebapi/streams/POINT_BAD_001/value").json()
    assert body["Good"] is False
    assert body["Questionable"] is True
    assert body["Substituted"] is False


def test_set_quality(client):
    response = client.post(
        "/mock/tags/sinusoid/quality",
        json={"good": False, "questionable": True, "substituted": False},
    )
    assert response.status_code == 200
    body = client.get("/piwebapi/streams/POINT_SIN_001/value").json()
    assert body["Good"] is False
    assert body["Questionable"] is True


def test_request_history(client):
    client.delete("/mock/requests")
    client.get("/piwebapi/streams/POINT_TEMP_001/value")
    items = client.get("/mock/requests").json()["Items"]
    assert len(items) >= 1
    last = items[-1]
    assert last["Method"] == "GET"
    assert last["Path"] == "/piwebapi/streams/POINT_TEMP_001/value"
    assert last["Status"] == 200
    assert last["Tag"] == "POINT_TEMP_001"
    assert "Timestamp" in last
    assert "ElapsedMs" in last


def test_clear_request_history(client):
    client.get("/piwebapi/dataservers")
    client.delete("/mock/requests")
    assert client.get("/mock/requests").json()["Items"] == []


def test_mock_api_not_affected_by_faults(client):
    client.post(
        "/mock/config",
        json={"force_status": 503, "delay_ms": 2000, "invalid_json": True},
    )
    assert client.get("/mock/config").status_code == 200
    assert client.post("/mock/reset").json() == {"success": True}
