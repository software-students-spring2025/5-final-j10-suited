import os
import pytest
import pymongo
import mongomock
import mongomock.gridfs
from bson import ObjectId
from importlib import reload

# ── Patch BEFORE importing app.py ───────────────────────────
mongomock.gridfs.enable_gridfs_integration()
pymongo.MongoClient = mongomock.MongoClient

@pytest.fixture(autouse=True)
def client_and_db(monkeypatch):
    # Ensure MAIL_PORT is valid (no empty-string float/int error)
    monkeypatch.setenv("MAIL_PORT", "587")
    # Pick a fresh in-memory test DB name
    test_dbname = "test_j10_suited_db"
    monkeypatch.setenv("MONGO_DBNAME", test_dbname)

    # Import/reload your Flask app under the patched client + env
    import app
    reload(app)

    # Override module‐level mongo + db
    app.mongo = mongomock.MongoClient()
    app.db = app.mongo[test_dbname]

    app.app.config["TESTING"] = True
    client = app.app.test_client()

    # Clean slate
    app.mongo.drop_database(test_dbname)
    yield client
    app.mongo.drop_database(test_dbname)


def test_register_page_renders(client_and_db):
    resp = client_and_db.get("/register")
    assert resp.status_code == 200
    data = resp.data
    assert b'name="first_name"'       in data
    assert b'name="last_name"'        in data
    assert b'name="email"'            in data
    assert b'name="password"'         in data
    assert b'name="confirm_password"' in data

def test_register_rejects_non_nyu_email(client_and_db):
    resp = client_and_db.post(
        "/register",
        data={
            "first_name": "Test",
            "last_name":  "User",
            "email":      "test@gmail.com",
            "password":   "pw12345",
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
