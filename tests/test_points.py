def test_point_by_path(client):
    response = client.get("/piwebapi/points", params={"path": "\\\\TEST-PI\\temperature"})
    assert response.status_code == 200
    body = response.json()
    assert body["WebId"] == "POINT_TEMP_001"
    assert body["Name"] == "temperature"
    assert body["EngineeringUnits"] == "degC"


def test_point_by_web_id(client):
    response = client.get("/piwebapi/points/POINT_TEMP_001")
    assert response.status_code == 200
    assert response.json()["Name"] == "temperature"


def test_point_by_name_fallback(client):
    response = client.get("/piwebapi/points/temperature")
    assert response.status_code == 200
    assert response.json()["WebId"] == "POINT_TEMP_001"


def test_list_points(client):
    response = client.get("/piwebapi/points")
    assert response.status_code == 200
    names = {item["Name"] for item in response.json()["Items"]}
    assert {"sinusoid", "temperature", "empty_tag"} <= names


def test_point_not_found(client):
    response = client.get("/piwebapi/points", params={"path": "\\\\TEST-PI\\DOES_NOT_EXIST"})
    assert response.status_code == 404
    assert response.json()["Errors"][0] == "PI Point not found."


def test_unknown_point_never_500(client):
    response = client.get("/piwebapi/points/UNKNOWN_TAG")
    assert response.status_code != 500
    assert response.status_code == 404


def test_create_point(client):
    response = client.post(
        "/mock/tags",
        json={"name": "custom", "point_type": "Float32", "snapshot": 1.5},
    )
    assert response.status_code == 200
    assert response.json()["WebId"] == "POINT_CUSTOM"
    fetched = client.get("/piwebapi/points/POINT_CUSTOM")
    assert fetched.status_code == 200
    value = client.get("/piwebapi/streams/POINT_CUSTOM/value")
    assert value.json()["Value"] == 1.5


def test_create_duplicate_point_conflict(client):
    response = client.post("/mock/tags", json={"name": "temperature"})
    assert response.status_code == 409


def test_create_point_bad_type(client):
    response = client.post("/mock/tags", json={"name": "weird", "point_type": "Blob"})
    assert response.status_code == 400
