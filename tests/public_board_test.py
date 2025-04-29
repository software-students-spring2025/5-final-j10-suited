import io
import pytest
import pymongo
import mongomock
from bson import ObjectId
from importlib import reload

mongomock.gridfs.enable_gridfs_integration()
pymongo.MongoClient = mongomock.MongoClient

@pytest.fixture(autouse=True)
def configure_test_db(monkeypatch):
    monkeypatch.setenv("MONGO_DBNAME", "myapp_test")

    import app
    reload(app)

    app.mongo = mongomock.MongoClient()
    app.db = app.mongo["myapp_test"]
    app.fs = mongomock.gridfs.GridFS(app.db)
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
def logged_in_client(client):
    with client.session_transaction() as sess:
        sess['_user_id'] = str(ObjectId())  
    return client

def test_public_board_loads(logged_in_client, db):
    """Test that the public board page loads successfully."""
    response = logged_in_client.get('/public_board')
    assert response.status_code == 200
    assert b"Public Posts" in response.data

def test_add_post_without_file(logged_in_client, db):
    """Test submitting a new post without uploading a file."""
    response = logged_in_client.post('/add_post', data={
        'text': 'This is a test post'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Public Posts" in response.data

    inserted_post = db.PublicPosts.find_one({'text': 'This is a test post'})
    assert inserted_post is not None
    assert inserted_post['text'] == 'This is a test post'
    assert 'timestamp' in inserted_post

def test_add_post_with_file(logged_in_client, db):
    """Test submitting a new post with an uploaded file."""
    data = {
        'text': 'Post with file',
        'file': (io.BytesIO(b"fake file content"), 'test_image.jpg')
    }
    response = logged_in_client.post('/add_post', data=data, content_type='multipart/form-data', follow_redirects=True)

    assert response.status_code == 200
    assert b"Public Posts" in response.data

    inserted_post = db.PublicPosts.find_one({'text': 'Post with file'})
    assert inserted_post is not None
    assert inserted_post['text'] == 'Post with file'
    assert 'file_id' in inserted_post
    file_id = inserted_post['file_id']
    assert db.fs.files.find_one({'_id': file_id}) is not None  

def test_public_board_requires_login(client):
    """Test that you cannot access public board without logging in."""
    response = client.get('/public_board', follow_redirects=True)
    assert b"login" in response.data.lower()
