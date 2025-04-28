import pytest
from bson import ObjectId
from werkzeug.security import generate_password_hash
from app import app, mongo, db

@pytest.fixture
def client():
    """Create a Flask test client and ensure a clean test database."""
    app.config["TESTING"] = True
    client = app.test_client()
    # Drop the test database before and after each test session
    mongo.drop_database(db.name)
    yield client
    mongo.drop_database(db.name)


@pytest.fixture
def create_user():
    """Helper to insert a user into db.Users."""
    def _create_user(
        email="test@nyu.edu",
        password="pw123",
        verified=False,
        first_name="First",
        last_name="Last",
        code="123456",
    ):
        user = {
            "first_name": first_name,
            "last_name":  last_name,
            "email":      email,
            "password":   generate_password_hash(password),
            "verified":   verified,
            "verification_code": code,
            "joined_groups":     [],
        }
        res = db.Users.insert_one(user)
        user["_id"] = res.inserted_id
        return user
    return _create_user


@pytest.fixture
def login_user(client, create_user):
    """Register & log in a verified user; returns (client, user_dict)."""
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
    # First & last name inputs
    assert b'name="first_name"' in html
    assert b'name="last_name"' in html
    # Email & password fields
    assert b'name="email"' in html
    assert b'name="password"' in html
    assert b'name="confirm_password"' in html


def test_verify_email_get_and_post(client, create_user):
    # GET
    user = create_user(email="verify@nyu.edu", code="999999")
    rv = client.get(f"/verify-email?email={user['email']}")
    assert rv.status_code == 200
    assert user["email"].encode() in rv.data
    assert b"Enter it below" in rv.data

    # POST wrong code
    rv2 = client.post(
        f"/verify-email?email={user['email']}",
        data={"code": "000000"}
    )
    assert b"Incorrect code" in rv2.data

    # POST correct code
    rv3 = client.post(
        f"/verify-email?email={user['email']}",
        data={"code": user["verification_code"]},
        follow_redirects=True
    )
    assert b"Email verified!" in rv3.data
    updated = db.Users.find_one({"email": user["email"]})
    assert updated.get("verified", False) is True


def test_users_list_requires_login(client):
    rv = client.get("/users", follow_redirects=True)
    assert b"Login using your NYU email" in rv.data


def test_users_list_shows_other_users(login_user, create_user):
    client, current = login_user
    # insert another user
    other = create_user(
        email="other@nyu.edu", verified=True,
        first_name="Other", last_name="User"
    )
    rv = client.get("/users")
    assert rv.status_code == 200
    html = rv.data
    # Should list the other, not the current
    assert b"other@nyu.edu" in html
    assert current["email"].encode() not in html


def test_chat_page_requires_login(client):
    fake_id = str(ObjectId())
    rv = client.get(f"/chat/{fake_id}", follow_redirects=True)
    assert b"Login using your NYU email" in rv.data


def test_chat_page_empty_history(login_user):
    client, current = login_user
    # Ensure messages collection is empty
    db.Messages.delete_many({})

    # create a second user
    other_doc = db.Users.insert_one({
        "first_name": "Chat",
        "last_name":  "Partner",
        "email":      "chat@nyu.edu",
        "password":   generate_password_hash("pw123"),
        "verified":   True,
        "verification_code": "",
        "joined_groups":     []
    })
    other_id = str(other_doc.inserted_id)

    rv = client.get(f"/chat/{other_id}")
    assert rv.status_code == 200
    # No server-rendered messages: ensure no <div class="message ...">
    assert b'class="message' not in rv.data


def test_chat_page_with_history(login_user):
    client, current = login_user
    # Clear any stray messages
    db.Messages.delete_many({})

    # create other user
    other_doc = db.Users.insert_one({
        "first_name": "Chat",
        "last_name":  "Friend",
        "email":      "friend@nyu.edu",
        "password":   generate_password_hash("pw123"),
        "verified":   True,
        "verification_code": "",
        "joined_groups":     []
    })
    other_id = str(other_doc.inserted_id)

    # insert one message
    from datetime import datetime, timezone
    room = "_".join(sorted([current["_id"].__str__(), other_id]))
    db.Messages.insert_one({
        "sender_id":    current["_id"],
        "recipient_id": other_doc.inserted_id,
        "body":         "Hello there!",
        "timestamp":    datetime.now(timezone.utc),
        "room":         room
    })

    rv = client.get(f"/chat/{other_id}")
    assert rv.status_code == 200
    assert b"Hello there!" in rv.data
    # Should show "You" in meta for your message
    assert b"You" in rv.data
