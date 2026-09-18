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
