import os
import secrets

import pytest
from _pytest.monkeypatch import MonkeyPatch
from starlette.testclient import TestClient

from app.auth import security


@pytest.fixture
def user_data():
    return {"email": "test@rickhenry.dev", "full_name": "Test Person"}


@pytest.fixture
def user1(db, user_data):
    result = db.users.insert_one(user_data)
    return {**user_data, "id": result.inserted_id}


@pytest.fixture
def disabled_user(db):
    data = {"email": "disabled@rickhenry.dev", "disabled": True}
    result = db.users.insert_one(data)
    return {**data, "id": result.inserted_id}


def test_register(
    test_client: TestClient, user_data: dict, monkeypatch: MonkeyPatch, async_db, db
):
    """Test creating a new user"""
    monkeypatch.setattr("app.auth.crud.db", async_db)
    response = test_client.post("/auth/register", json=user_data)

    assert response.status_code == 201
    user_in_db = db.users.find_one({"email": user_data["email"]})

    assert user_in_db["full_name"] == user_data["full_name"]


def test_request_login(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    """Test request login sends email"""
    monkeypatch.setattr("app.auth.crud.db", async_db)
    monkeypatch.setattr(secrets, "choice", lambda args: "1")

    async def fake_send_email(to, subject, text):
        assert to == "test@rickhenry.dev"
        assert subject == "Your One Time Password"
        assert text == "Your password is 11111111"

    monkeypatch.setattr("app.auth.router.send_email", fake_send_email)
    response = test_client.post("/auth/request", json={"email": user1["email"]})
    assert response.status_code == 200
    assert response.text == '"Please check your email for a single use password."'


def test_request_login_disabled_fails(
    test_client: TestClient, disabled_user: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)

    async def fake_send_email(*_args, **_kwargs):
        assert False, "Should not have been called"

    monkeypatch.setattr("app.auth.router.send_email", fake_send_email)
    response = test_client.post("/auth/request", json={"email": disabled_user["email"]})
    assert response.status_code == 401


def test_request_magic_link(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    monkeypatch.setattr(secrets, "token_urlsafe", lambda: "123456789")
    hostname = os.getenv("HOSTNAME", "localhost")

    async def fake_send_email(to, subject, text):
        assert to == "test@rickhenry.dev"
        assert subject == "Your magic sign in link"
        assert text == f"Click this link to sign in\n{hostname}?secret=123456789"

    monkeypatch.setattr("app.auth.router.send_email", fake_send_email)
    response = test_client.post("/auth/request-magic", json={"email": user1["email"]})

    assert response.status_code == 200
    assert response.text == '"Please check your email for your sign in link."'


def test_request_magic_disabled_fails(
    test_client: TestClient, disabled_user: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)

    async def fake_send_email(*_args, **_kwargs):
        assert False, "Should not have been called"

    monkeypatch.setattr("app.auth.router.send_email", fake_send_email)
    response = test_client.post(
        "/auth/request-magic", json={"email": disabled_user["email"]}
    )
    assert response.status_code == 401


def test_confirm_login(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    otp = security.generate_otp(user1["email"])

    response = test_client.post(
        "/auth/confirm", json={"email": user1["email"], "code": otp}
    )

    assert response.status_code == 200
    assert response.cookies.get("token") is not None


def test_confirm_login_wrong_code_fails(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    _otp = security.generate_otp(user1["email"])

    response = test_client.post(
        "/auth/confirm", json={"email": user1["email"], "code": "123456"}
    )

    assert response.status_code == 400
    assert response.cookies.get("token") is None


def test_confirm_login_wrong_email_fails(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    otp = security.generate_otp(user1["email"])

    response = test_client.post(
        "/auth/confirm", json={"email": "fail@rickhenry.dev", "code": otp}
    )

    assert response.status_code == 400
    assert response.cookies.get("token") is None


def test_confirm_magic(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    magic_url = security.generate_magic_link(user1["email"])
    url_secret = magic_url.split("=")[-1]
    response = test_client.post(
        "/auth/confirm-magic", json={"email": user1["email"], "secret": url_secret}
    )

    assert response.status_code == 200
    assert response.cookies.get("token") is not None


def test_confirm_magic_wrong_email_fails(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    magic_url = security.generate_magic_link(user1["email"])
    url_secret = magic_url.split("=")[-1]
    response = test_client.post(
        "/auth/confirm-magic",
        json={"email": "fail@rickhenry.dev", "secret": url_secret},
    )

    assert response.status_code == 400
    assert response.cookies.get("token") is None


def test_confirm_magic_wrong_secret_fails(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    magic_url = security.generate_magic_link(user1["email"])
    url_secret = magic_url.split("=")[-1]
    response = test_client.post(
        "/auth/confirm-magic", json={"email": user1["email"], "secret": "123456789"}
    )

    assert response.status_code == 400
    assert response.cookies.get("token") is None


def test_logged_in_get_user_info(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    otp = security.generate_otp(user1["email"])

    _response = test_client.post(
        "/auth/confirm", json={"email": user1["email"], "code": otp}
    )

    response2 = test_client.get("/auth/me")

    assert response2.status_code == 200


def test_not_logged_in_cant_get_user_info(
    test_client: TestClient, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    response = test_client.get("/auth/me")

    assert response.status_code == 401


def test_log_out(
    test_client: TestClient, user1: dict, monkeypatch: MonkeyPatch, async_db
):
    monkeypatch.setattr("app.auth.crud.db", async_db)
    otp = security.generate_otp(user1["email"])

    response = test_client.post(
        "/auth/confirm", json={"email": user1["email"], "code": otp}
    )

    assert response.cookies.get("token") is not None

    response2 = test_client.get("/auth/sign-out")

    assert response2.status_code == 200
    assert response2.cookies.get("token") == '""'

    response3 = test_client.get("/auth/me")

    assert response3.status_code == 401
