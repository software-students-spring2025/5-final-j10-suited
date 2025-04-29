import os
import io
import pytest
import pymongo
import mongomock
import mongomock.gridfs
from bson import ObjectId
from importlib import reload
from flask_login import AnonymousUserMixin

mongomock.gridfs.enable_gridfs_integration()
pymongo.MongoClient = mongomock.MongoClient

class DummyAnon(AnonymousUserMixin):
    def __init__(self):
        super().__init__()
        self.first_name = "Guest"
        self.last_name = "User"
        self.id = "testid"

@pytest.fixture(autouse=True)
def configure_test_db(monkeypatch):
    monkeypatch.setenv("MAIL_PORT", "587")
    monkeypatch.setenv("MONGO_DBNAME", "public_board_test_db")

    import app
    reload(app)

    app.app.config['LOGIN_DISABLED'] = True
    app.login_manager.anonymous_user = DummyAnon

    app.mongo = mongomock.MongoClient()
    app.db = app.mongo["public_board_test_db"]
    return app

@pytest.fixture
def client(configure_test_db):
    app = configure_test_db
    app.app.config["TESTING"] = True
    return app.app.test_client()


def test_public_board_loads(client):
    response = client.get('/public_board')
    assert response.status_code == 200


def test_add_post_without_file(client, monkeypatch):
    import app as tested_app
    captured = {}
    def fake_insert(doc):
        captured['doc'] = doc
    monkeypatch.setattr(tested_app.db.PublicPosts, 'insert_one', fake_insert)

    response = client.post(
        '/add_post',
        data={'text': 'This is a test post'},
        follow_redirects=True
    )
    assert response.status_code == 200
    assert captured['doc']['text'] == 'This is a test post'
    assert 'timestamp' in captured['doc']


def test_add_post_with_file(client, monkeypatch):
    import app as tested_app
    captured = {}
    monkeypatch.setattr(tested_app.fs, 'put', lambda *args, **kwargs: ObjectId())
    def fake_insert(doc):
        captured['doc'] = doc
    monkeypatch.setattr(tested_app.db.PublicPosts, 'insert_one', fake_insert)

    data = {
        'text': 'Post with file',
        'file': (io.BytesIO(b"fake content"), 'file.jpg')
    }
    response = client.post(
        '/add_post',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True
    )
    assert response.status_code == 200
    assert 'file_id' in captured['doc']
    assert captured['doc']['text'] == 'Post with file'


def test_public_board_requires_login(configure_test_db):
    app = configure_test_db
    app.app.config['LOGIN_DISABLED'] = False
    client = app.app.test_client()
    response = client.get('/public_board', follow_redirects=True)
    assert response.status_code == 200
    assert b"login" in response.data.lower()
