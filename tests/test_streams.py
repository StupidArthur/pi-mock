def test_current_value(client):
    response = client.get("/piwebapi/streams/POINT_TEMP_001/value")
    assert response.status_code == 200
    body = response.json()
    assert body["Value"] == 25.5
    assert body["Good"] is True
    assert body["Questionable"] is False
    assert body["Substituted"] is False
    assert body["UnitsAbbreviation"] == "degC"
    assert body["Timestamp"].endswith("Z")


def test_current_value_not_found(client):
    response = client.get("/piwebapi/streams/POINT_UNKNOWN/value")
    assert response.status_code == 404


def test_empty_tag_current_value(client):
    response = client.get("/piwebapi/streams/POINT_EMPTY/value")
    assert response.status_code == 404


def test_empty_tag_history_is_empty_list(client):
    response = client.get("/piwebapi/streams/POINT_EMPTY/recorded")
    assert response.status_code == 200
    assert response.json() == {"Items": []}


def test_recorded_range_and_max_count(client):
    client.post(
        "/mock/data/generate",
        json={
            "tag": "temperature",
            "start": "2026-01-01T00:00:00Z",
            "count": 120,
            "interval_ms": 1000,
            "generator": "sin",
        },
    )
    response = client.get(
        "/piwebapi/streams/POINT_TEMP_001/recorded",
        params={
            "startTime": "2026-01-01T00:00:10Z",
            "endTime": "2026-01-01T00:00:20Z",
            "maxCount": 5,
        },
    )
    assert response.status_code == 200
    items = response.json()["Items"]
    assert len(items) == 5
    assert items[0]["Timestamp"] == "2026-01-01T00:00:10.000Z"
    assert items[-1]["Timestamp"] == "2026-01-01T00:00:14.000Z"
    assert items[0]["Good"] is True


def test_recorded_default_ascending(client):
    client.post(
        "/mock/data/generate",
        json={
            "tag": "temperature",
            "start": "2026-01-01T00:00:00Z",
            "count": 3,
            "interval_ms": 1000,
        },
    )
    timestamps = [
        item["Timestamp"]
        for item in client.get("/piwebapi/streams/POINT_TEMP_001/recorded").json()["Items"]
    ]
    assert timestamps == sorted(timestamps)


def test_recorded_accepts_timezone_offsets(client):
    response = client.get(
        "/piwebapi/streams/POINT_TEMP_001/recorded",
        params={"startTime": "2026-01-01T08:00:00+08:00"},
    )
    assert response.status_code == 200


def test_recorded_invalid_start_time_returns_400(client):
    response = client.get(
        "/piwebapi/streams/POINT_TEMP_001/recorded",
        params={"startTime": "invalid-time"},
    )
    assert response.status_code == 400
    assert "Invalid startTime" in response.json()["Errors"][0]


def test_recorded_invalid_end_time_returns_400(client):
    response = client.get(
        "/piwebapi/streams/POINT_TEMP_001/recorded",
        params={"startTime": "2026-01-01T00:00:00Z", "endTime": "not-a-time"},
    )
    assert response.status_code == 400
    assert "Invalid endTime" in response.json()["Errors"][0]


def test_history_order_desc(client):
    client.post(
        "/mock/data/generate",
        json={"tag": "temperature", "start": "2026-01-01T00:00:00Z", "count": 3, "interval_ms": 1000},
    )
    client.post("/mock/config", json={"history_order": "desc"})
    timestamps = [
        item["Timestamp"]
        for item in client.get("/piwebapi/streams/POINT_TEMP_001/recorded").json()["Items"]
    ]
    assert timestamps == sorted(timestamps, reverse=True)


def test_large_history(client):
    response = client.post(
        "/mock/data/generate",
        json={
            "tag": "temperature",
            "start": "2026-01-01T00:00:00Z",
            "count": 100000,
            "interval_ms": 1000,
        },
    )
    assert response.status_code == 200
    assert response.json()["Generated"] == 100000
    result = client.get(
        "/piwebapi/streams/POINT_TEMP_001/recorded", params={"maxCount": 100000}
    )
    assert result.status_code == 200
    assert len(result.json()["Items"]) == 100000


def test_timestamp_modes(client):
    for mode in ("epoch", "future", "no_tz", "bad_format", "null"):
        response = client.post(
            "/mock/data/generate",
            json={
                "tag": "sinusoid",
                "start": "2026-01-01T00:00:00Z",
                "count": 2,
                "interval_ms": 1000,
                "timestamp_mode": mode,
            },
        )
        assert response.status_code == 200
    client.post(
        "/mock/data/generate",
        json={"tag": "sinusoid", "count": 2, "timestamp_mode": "null"},
    )
    items = client.get("/piwebapi/streams/POINT_SIN_001/recorded").json()["Items"]
    assert any(item["Timestamp"] is None for item in items)


def test_duplicate_timestamps(client):
    client.post(
        "/mock/data/generate",
        json={
            "tag": "sinusoid",
            "start": "2026-01-01T00:00:00Z",
            "count": 6,
            "interval_ms": 1000,
            "duplicate_every": 2,
        },
    )
    items = client.get("/piwebapi/streams/POINT_SIN_001/recorded").json()["Items"]
    timestamps = [item["Timestamp"] for item in items]
    assert len(timestamps) != len(set(timestamps))
