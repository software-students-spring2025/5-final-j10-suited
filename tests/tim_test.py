import pytest
import pymongo
import mongomock
import mongomock.gridfs
from bson import ObjectId
from werkzeug.security import generate_password_hash
from importlib import reload

# ── Patch BEFORE importing app.py ───────────────────────────
mongomock.gridfs.enable_gridfs_integration()
pymongo.MongoClient = mongomock.MongoClient

@pytest.fixture(autouse=True)
def configure_test_db(monkeypatch):
    # Point at a throw‐away in-memory test database
    monkeypatch.setenv("MONGO_DBNAME", "myapp_test")

    # Import/reload your Flask app under the patched client
    import app
    reload(app)

    # Override module‐level mongo + db
    app.mongo = mongomock.MongoClient()
    app.db = app.mongo["myapp_test"]
    return app

@pytest.fixture
def client(configure_test_db):
    app = configure_test_db
    app.app.config["TESTING"] = True
    return app.app.test_client()

@pytest.fixture
def db(configure_test_db):
    return configure_test_db.db

@pytest.fixture
def create_user(db):
    def _create_user(
        email="test@nyu.edu",
        password="pw123",
        verified=False,
        first_name="First",
        last_name="Last",
        code="123456",
    ):
        user = {
            "first_name":         first_name,
            "last_name":          last_name,
            "email":              email,
            "password":           generate_password_hash(password),
            "verified":           verified,
            "verification_code":  code,
            "joined_groups":      [],
        }
        res = db.Users.insert_one(user)
        user["_id"] = res.inserted_id
        return user
    return _create_user

@pytest.fixture
def login_user(client, create_user):
    # Create a verified user and log in
    user = create_user(verified=True, password="pw123")
    resp = client.post(
        "/login",
        data={"email": user["email"], "password": "pw123"},
        follow_redirects=True
    )
    assert b"Logged in successfully." in resp.data
    return client, user

def test_register_page_structure(client):
    rv = client.get("/register")
    assert rv.status_code == 200
    html = rv.data
    assert b'name="first_name"'       in html
    assert b'name="last_name"'        in html
    assert b'name="email"'            in html
    assert b'name="password"'         in html
    assert b'name="confirm_password"' in html

def test_verify_email_get_and_post(client, create_user, db):
    user = create_user(email="verify@nyu.edu", code="999999")

    # GET shows the form
    rv = client.get(f"/verify-email?email={user['email']}")
    assert rv.status_code == 200
    assert user["email"].encode() in rv.data

    # POST bad code
    rv2 = client.post(
        f"/verify-email?email={user['email']}",
        data={"code": "000000"}
    )
    assert rv2.status_code == 200
    assert b"Incorrect code" in rv2.data

    # POST correct code
    rv3 = client.post(
        f"/verify-email?email={user['email']}",
        data={"code": user["verification_code"]},
        follow_redirects=True
    )
    assert rv3.status_code == 200

    # Verify in DB
    updated = db.Users.find_one({"email": user["email"]})
    assert updated.get("verified", False) is True

def test_users_list_requires_login(client):
    rv = client.get("/users", follow_redirects=True)
    assert rv.status_code == 200
    assert b"Login using your NYU email" in rv.data

def test_users_list_shows_other_users(login_user, create_user):
    client, current = login_user
    other = create_user(
        email="other@nyu.edu", verified=True,
        first_name="Other", last_name="User"
    )
    rv = client.get("/users")
    assert rv.status_code == 200
    assert b"other@nyu.edu" in rv.data

def test_chat_page_requires_login(client):
    fake_id = str(ObjectId())
    rv = client.get(f"/chat/{fake_id}", follow_redirects=True)
    assert rv.status_code == 200
    assert b"Login using your NYU email" in rv.data

def test_chat_page_empty_history(login_user, create_user):
    client, current = login_user
    other = create_user(
        email="chat@nyu.edu",
        first_name="Chat",
        last_name="Partner",
        verified=True
    )
    rv = client.get(f"/chat/{str(other['_id'])}")
    assert rv.status_code == 200

def test_chat_page_with_history(login_user, create_user, db):
    client, current = login_user
    other = create_user(
        email="friend@nyu.edu",
        first_name="Chat",
        last_name="Friend",
        verified=True
    )

    from datetime import datetime, timezone
    room = "_".join(sorted([str(current["_id"]), str(other["_id"])]))
    db.Messages.insert_one({
        "sender_id":    current["_id"],
        "recipient_id": other["_id"],
        "body":         "Hello there!",
        "timestamp":    datetime.now(timezone.utc),
        "room":         room
    })

    rv = client.get(f"/chat/{str(other['_id'])}")
    assert rv.status_code == 200
