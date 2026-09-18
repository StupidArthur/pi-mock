def test_write_then_read(client):
    response = client.post(
        "/piwebapi/streams/POINT_TEMP_001/value",
        json={"Timestamp": "2026-09-18T11:00:00Z", "Value": 66.6},
    )
    assert response.status_code == 202
    value = client.get("/piwebapi/streams/POINT_TEMP_001/value").json()
    assert value["Value"] == 66.6
    assert value["Timestamp"] == "2026-09-18T11:00:00.000Z"


def test_write_persists_to_history(client):
    client.post(
        "/piwebapi/streams/POINT_TEMP_001/value",
        json={"Timestamp": "2026-09-18T11:00:00Z", "Value": 66.6},
    )
    items = client.get("/piwebapi/streams/POINT_TEMP_001/recorded").json()["Items"]
    assert any(item["Value"] == 66.6 for item in items)


def test_write_no_content_mode(client):
    client.post("/mock/config", json={"write_status": 204})
    response = client.post(
        "/piwebapi/streams/POINT_TEMP_001/value", json={"Value": 10.0}
    )
    assert response.status_code == 204


def test_batch_write(client):
    response = client.post(
        "/piwebapi/streams/POINT_TEMP_001/recorded",
        json=[
            {"Timestamp": "2026-09-18T10:30:00Z", "Value": 20.1},
            {"Timestamp": "2026-09-18T10:31:00Z", "Value": 20.2},
        ],
    )
    assert response.status_code == 202
    items = client.get("/piwebapi/streams/POINT_TEMP_001/recorded").json()["Items"]
    values = [item["Value"] for item in items]
    assert 20.1 in values and 20.2 in values


def test_write_unknown_point(client):
    response = client.post("/piwebapi/streams/UNKNOWN/value", json={"Value": 1})
    assert response.status_code == 404


def test_type_error_returns_400(client):
    response = client.post(
        "/piwebapi/streams/POINT_TEMP_001/value", json={"Value": "not-a-number"}
    )
    assert response.status_code == 400


def test_string_point_type(client):
    response = client.post(
        "/piwebapi/streams/POINT_STATUS_001/value", json={"Value": "STOPPED"}
    )
    assert response.status_code == 202
    assert client.get("/piwebapi/streams/POINT_STATUS_001/value").json()["Value"] == "STOPPED"


def test_int_point_rejects_string(client):
    response = client.post(
        "/piwebapi/streams/POINT_COUNT_001/value", json={"Value": "abc"}
    )
    assert response.status_code == 400


def test_int_point_accepts_integer(client):
    response = client.post("/piwebapi/streams/POINT_COUNT_001/value", json={"Value": 42})
    assert response.status_code == 202
    assert client.get("/piwebapi/streams/POINT_COUNT_001/value").json()["Value"] == 42


def test_batch_api(client):
    response = client.post(
        "/piwebapi/batch",
        json={
            "Requests": [
                {"Method": "GET", "Resource": "/piwebapi/streams/POINT_TEMP_001/value"},
                {
                    "Method": "POST",
                    "Resource": "/piwebapi/streams/POINT_TEMP_001/value",
                    "Content": {"Value": 77.7},
                },
            ]
        },
    )
    assert response.status_code == 200
    responses = response.json()["Responses"]
    assert responses[0]["Status"] == 200
    assert responses[1]["Status"] == 202
