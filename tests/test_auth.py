import base64


def _basic(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_auth_disabled_by_default(client):
    assert client.get("/piwebapi/dataservers").status_code == 200


def test_auth_enabled_rejects_missing(client):
    client.post(
        "/mock/config",
        json={
            "auth_enabled": True,
            "auth_type": "basic",
            "username": "piuser",
            "password": "password123",
        },
    )
    response = client.get("/piwebapi/dataservers")
    assert response.status_code == 401
    assert "www-authenticate" in {key.lower() for key in response.headers}


def test_auth_enabled_accepts_valid(client):
    client.post(
        "/mock/config",
        json={"auth_enabled": True, "username": "piuser", "password": "password123"},
    )
    response = client.get("/piwebapi/dataservers", headers=_basic("piuser", "password123"))
    assert response.status_code == 200


def test_auth_rejects_wrong_password(client):
    client.post(
        "/mock/config",
        json={"auth_enabled": True, "username": "piuser", "password": "password123"},
    )
    response = client.get("/piwebapi/dataservers", headers=_basic("piuser", "wrong"))
    assert response.status_code == 401


def test_mock_api_not_protected_by_auth(client):
    client.post("/mock/config", json={"auth_enabled": True})
    assert client.get("/mock/config").status_code == 200
    assert client.post("/mock/reset").status_code == 200


def test_reset_disables_auth(client):
    client.post("/mock/config", json={"auth_enabled": True})
    client.post("/mock/reset")
    assert client.get("/piwebapi/dataservers").status_code == 200


def test_invalid_auth_type_rejected(client):
    response = client.post("/mock/config", json={"auth_type": "kerberos"})
    assert response.status_code == 400


def test_auth_cannot_fail_open(client):
    client.post("/mock/config", json={"auth_enabled": True, "auth_type": "basic"})
    assert client.get("/piwebapi/dataservers").status_code == 401
    client.post("/mock/reset")
    client.post("/mock/config", json={"auth_enabled": True})
    assert client.get("/piwebapi/dataservers").status_code == 401
    assert client.get("/piwebapi/dataservers", headers=_basic("piuser", "password123")).status_code == 200
