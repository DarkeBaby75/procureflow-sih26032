import tempfile
from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def app():
    with tempfile.TemporaryDirectory() as temp_dir:
        app = create_app({"TESTING": True, "DATABASE": str(Path(temp_dir) / "test.db"), "SECRET_KEY": "test", "SMTP_ENABLED": False})
        yield app


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email="farmer@demo.in", password="Farmer@123"):
    page = client.get("/login")
    with client.session_transaction() as session:
        csrf = session["csrf_token"]
    return client.post("/login", data={"email": email, "password": password, "csrf_token": csrf}, follow_redirects=True)


def csrf(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_farmer_can_login_and_see_schedules(client):
    response = login(client)
    assert response.status_code == 200
    assert b"Namaskar" in response.data
    response = client.get("/schedules")
    assert b"Find a schedule" in response.data


def test_farmer_can_book_token(client):
    login(client)
    response = client.post(
        "/book/1",
        data={"csrf_token": csrf(client), "quantity": "5", "identity": "yes", "bank": "yes", "land": "yes", "produce": "yes"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"PF-" in response.data
    assert b"Estimated wait" in response.data


def test_duplicate_booking_is_blocked(client):
    login(client)
    data = {"csrf_token": csrf(client), "quantity": "5", "identity": "yes", "bank": "yes", "land": "yes", "produce": "yes"}
    client.post("/book/1", data=data)
    response = client.post("/book/1", data={**data, "csrf_token": csrf(client)}, follow_redirects=True)
    assert b"already have an active token" in response.data


def test_staff_transition_flow(client):
    login(client)
    client.post("/book/1", data={"csrf_token": csrf(client), "quantity": "5", "identity": "yes", "bank": "yes", "land": "yes", "produce": "yes"})
    client.post("/logout", data={"csrf_token": csrf(client)})
    login(client, "staff@demo.in", "Staff@123")
    for action in ("checkin", "start", "complete"):
        response = client.post(f"/staff/booking/1/{action}", data={"csrf_token": csrf(client)}, follow_redirects=True)
        assert response.status_code == 200
    assert b"Completed" in response.data


def test_role_access_is_enforced(client):
    login(client)
    assert client.get("/admin").status_code == 403
    assert client.get("/staff").status_code == 403


@pytest.mark.parametrize("language", ["hi", "mr", "en"])
def test_language_switch_persists(client, language):
    client.get("/login")
    response = client.post(
        f"/language/{language}",
        data={"csrf_token": csrf(client), "next": "/login"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert f'lang="{language}"'.encode() in response.data
    with client.session_transaction() as saved_session:
        assert saved_session["language"] == language


def test_no_chatgpt_authentication_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"ChatGPT" not in response.data
    assert b"OpenAI" not in response.data


def test_language_survives_login_and_logout(client):
    client.get("/login")
    client.post("/language/mr", data={"csrf_token": csrf(client), "next": "/login"})
    login(client)
    with client.session_transaction() as saved_session:
        assert saved_session["language"] == "mr"
    client.post("/logout", data={"csrf_token": csrf(client)})
    with client.session_transaction() as saved_session:
        assert saved_session["language"] == "mr"
