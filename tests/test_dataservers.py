def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root(client):
    response = client.get("/piwebapi")
    assert response.status_code == 200
    body = response.json()
    assert body["ProductTitle"] == "Mock PI Web API"
    assert body["Links"]["DataServers"] == "/piwebapi/dataservers"


def test_list_dataservers(client):
    response = client.get("/piwebapi/dataservers")
    assert response.status_code == 200
    items = response.json()["Items"]
    assert len(items) == 1
    assert items[0]["WebId"] == "SERVER_TEST_PI"
    assert items[0]["Name"] == "TEST-PI"
    assert items[0]["Path"] == "\\\\TEST-PI"


def test_dataserver_by_web_id(client):
    response = client.get("/piwebapi/dataservers/SERVER_TEST_PI")
    assert response.status_code == 200
    assert response.json()["Name"] == "TEST-PI"


def test_dataserver_not_found(client):
    response = client.get("/piwebapi/dataservers/SERVER_UNKNOWN")
    assert response.status_code == 404


def test_dataserver_by_name(client):
    response = client.get("/piwebapi/dataservers", params={"name": "TEST-PI"})
    assert response.status_code == 200
    body = response.json()
    assert body["Name"] == "TEST-PI"
    assert "Items" not in body


def test_dataserver_by_path(client):
    response = client.get("/piwebapi/dataservers", params={"path": "\\\\TEST-PI"})
    assert response.status_code == 200
    assert response.json()["WebId"] == "SERVER_TEST_PI"


def test_dataserver_by_name_not_found(client):
    response = client.get("/piwebapi/dataservers", params={"name": "NOPE"})
    assert response.status_code == 404


def test_dataserver_points(client):
    response = client.get("/piwebapi/dataservers/SERVER_TEST_PI/points")
    assert response.status_code == 200
    names = {item["Name"] for item in response.json()["Items"]}
    assert {"sinusoid", "temperature", "empty_tag"} <= names


def test_dataserver_points_name_filter(client):
    response = client.get(
        "/piwebapi/dataservers/SERVER_TEST_PI/points", params={"nameFilter": "temp*"}
    )
    assert response.status_code == 200
    items = response.json()["Items"]
    assert len(items) == 1
    assert items[0]["Name"] == "temperature"


def test_dataserver_points_name_filter_case_insensitive(client):
    response = client.get(
        "/piwebapi/dataservers/SERVER_TEST_PI/points", params={"nameFilter": "TEMP*"}
    )
    assert response.status_code == 200
    assert response.json()["Items"][0]["Name"] == "temperature"


def test_dataserver_points_name_filter_question_mark(client):
    response = client.get(
        "/piwebapi/dataservers/SERVER_TEST_PI/points", params={"nameFilter": "??????"}
    )
    assert response.status_code == 200
    names = {item["Name"] for item in response.json()["Items"]}
    assert "status" in names
    assert "counter" not in names


def test_dataserver_points_max_count(client):
    response = client.get(
        "/piwebapi/dataservers/SERVER_TEST_PI/points", params={"maxCount": 2}
    )
    assert len(response.json()["Items"]) == 2


def test_dataserver_points_unknown_server(client):
    response = client.get("/piwebapi/dataservers/SERVER_UNKNOWN/points")
    assert response.status_code == 404
