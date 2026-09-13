from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "available_tools" in data
    assert len(data["available_tools"]) > 0


def test_tools_endpoint():
    response = client.get("/tools")
    assert response.status_code == 200
    data = response.json()
    assert "total_tools" in data
    assert data["total_tools"] == 23
    assert len(data["tools"]) == 23


def test_sessions_endpoint():
    response = client.get("/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "total_sessions" in data
    assert "session_ids" in data


def test_delete_nonexistent_session():
    response = client.delete("/chat/non-existent-session-id-12345")
    assert response.status_code == 404


def test_dashboard_endpoint():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "Enterprise AI Employee" in response.text


def test_static_files():
    response = client.get("/static/style.css")
    assert response.status_code == 200
    assert "--bg-dark" in response.text

    response_js = client.get("/static/app.js")
    assert response_js.status_code == 200
    assert "DOMContentLoaded" in response_js.text

