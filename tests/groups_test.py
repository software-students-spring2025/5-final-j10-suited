import os
import pytest
from bson import ObjectId
from app import app, mongo
from importlib import reload

@pytest.fixture(autouse=True)
def client_and_db(monkeypatch):
    test_dbname = "test_j10_suited_db"
    monkeypatch.setenv("MONGO_DBNAME", test_dbname)
    import app
    reload(app)
    app.app.config["TESTING"] = True
    client = app.app.test_client()

    app.mongo.drop_database(test_dbname)
    yield client

    app.mongo.drop_database(test_dbname)


def test_register_page_renders(client_and_db):
    resp = client_and_db.get("/register")
    assert resp.status_code == 200
    data = resp.data
    # should have all form fields
    assert b'name="first_name"' in data
    assert b'name="last_name"'  in data
    assert b'name="email"'      in data
    assert b'name="password"'   in data
    assert b'name="confirm_password"' in data


def test_register_rejects_non_nyu_email(client_and_db):
    resp = client_and_db.post(
        "/register",
        data={
            "first_name": "Test",
            "last_name": "User",
            "email": "test@gmail.com",
            "password": "pw12345",
            "confirm_password": "pw12345"
        },
        follow_redirects=True
    )
    assert resp.status_code == 200
    assert b"Must be an NYU email." in resp.data


def test_login_page_and_invalid_login(client_and_db):
    # GET login form
    resp = client_and_db.get("/login")
    assert resp.status_code == 200
    assert b'name="email"'    in resp.data
    assert b'name="password"' in resp.data

    # POST wrong credentials
    resp2 = client_and_db.post(
        "/login",
        data={"email": "nouser@nyu.edu", "password": "wrong"},
        follow_redirects=True
    )
    assert resp2.status_code == 200
    assert b"Invalid email or password" in resp2.data


def test_post_detail_404_for_missing(client_and_db):
    random_id = str(ObjectId())
    resp = client_and_db.get(f"/post/{random_id}")
    assert resp.status_code == 404
