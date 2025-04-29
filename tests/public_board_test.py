import pytest
from flask import url_for
from bson import ObjectId

@pytest.fixture
def logged_in_client(client):
    """Helper to create a fake logged-in user."""
    with client.session_transaction() as sess:
        sess['_user_id'] = str(ObjectId()) 
    return client

def test_public_board_loads(logged_in_client):
    """Test that the public board page loads successfully."""
    response = logged_in_client.get('/public_board')
    assert response.status_code == 200
    assert b"Public Posts" in response.data  

def test_add_post_without_file(logged_in_client, mocker):
    """Test submitting a new post without uploading a file."""
    mock_insert = mocker.patch('app.db.PublicPosts.insert_one') 

    response = logged_in_client.post('/add_post', data={
        'text': 'This is a test post'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Public Posts" in response.data

    mock_insert.assert_called_once()
    args, kwargs = mock_insert.call_args
    assert args[0]['text'] == 'This is a test post'
    assert 'timestamp' in args[0]

def test_add_post_with_file(logged_in_client, mocker):
    """Test submitting a new post with an uploaded file."""
    mock_insert = mocker.patch('app.db.PublicPosts.insert_one')
    mock_put = mocker.patch('app.fs.put', return_value=ObjectId())

    data = {
        'text': 'Post with file',
        'file': (io.BytesIO(b"fake file content"), 'test_image.jpg')
    }

    response = logged_in_client.post('/add_post', data=data, content_type='multipart/form-data', follow_redirects=True)

    assert response.status_code == 200
    assert b"Public Posts" in response.data

    mock_put.assert_called_once()
    mock_insert.assert_called_once()
    args, kwargs = mock_insert.call_args
    assert args[0]['file_id'] is not None
    assert args[0]['text'] == 'Post with file'

def test_public_board_requires_login(client):
    """Test that you cannot access public board without logging in."""
    response = client.get('/public_board', follow_redirects=True)
    assert b"login" in response.data.lower()  
