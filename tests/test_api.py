
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["status"] == "ok"


def test_validate_json_success():
    response = client.post(
        "/v1/json/validate",
        json={"content": '{"hello": "world"}'}
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["type"] == "dict"


def test_validate_json_failure():
    response = client.post(
        "/v1/json/validate",
        json={"content": "{bad json}"}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_JSON"


def test_format_json():
    response = client.post(
        "/v1/json/format",
        json={"content": '{"a":1,"b":2}'}
    )

    assert response.status_code == 200
    assert response.json()["data"]["formatted"] == (
        '{\n  "a": 1,\n  "b": 2\n}'
    )


def test_sha256():
    response = client.post(
        "/v1/hash/sha256",
        json={"content": "hello"}
    )

    assert response.status_code == 200
    assert response.json()["data"]["hash"] == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29"
        "e1b161e5c1fa7425e73043362938b9824"
    )


def test_uuid_count():
    response = client.post(
        "/v1/uuid",
        json={"count": 3}
    )

    data = response.json()["data"]

    assert response.status_code == 200
    assert data["count"] == 3
    assert len(set(data["uuids"])) == 3


def test_empty_content_rejected():
    response = client.post(
        "/v1/json/validate",
        json={"content": ""}
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_whitespace_content_rejected():
    response = client.post(
        "/v1/hash/sha256",
        json={"content": "   "}
    )

    assert response.status_code == 422


def test_uuid_limit():
    response = client.post(
        "/v1/uuid",
        json={"count": 11}
    )

    assert response.status_code == 422


def test_extra_fields_rejected():
    response = client.post(
        "/v1/uuid",
        json={"count": 2, "unexpected": True}
    )

    assert response.status_code == 422


def test_large_request_rejected():
    response = client.post(
        "/v1/json/validate",
        json={"content": "a" * (130 * 1024)}
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
