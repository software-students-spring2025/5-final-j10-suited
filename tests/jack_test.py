import pytest
from unittest.mock import patch
from bson import ObjectId
import json
from app import app

@pytest.fixture
def client():
    return app.test_client()

@pytest.fixture
def sample_groups():
    return [
        {'_id': ObjectId(), 'name': 'Beta', 'members': ['user1', 'user2']},
        {'_id': ObjectId(), 'name': 'Alpha', 'members': ['user1']},
        {'_id': ObjectId(), 'name': 'Gamma', 'members': ['user1', 'user2', 'user3']}
    ]

def test_browse_groups(client):
    response = client.get('/group_browser')
    assert response.status_code == 200

def test_get_all_groups(client, sample_groups):
    with patch('app.db.Groups.find', return_value=sample_groups):
        response = client.get('/get_all_groups')
        assert response.status_code == 200
        groups = json.loads(response.data)
        print(groups)
        # Check that the groups are in original order
        assert groups[0]['name'] == 'Beta'
        assert groups[1]['name'] == 'Alpha'
        assert groups[2]['name'] == 'Gamma'

def test_get_all_groups_sort_newest(client, sample_groups):
    with patch('app.db.Groups.find', return_value=sample_groups):
        response = client.get('/get_all_groups?sort=newest')
        assert response.status_code == 200
        groups = json.loads(response.data)
        # Check that the groups are in reversed order
        assert groups[0]['name'] == 'Gamma'
        assert groups[1]['name'] == 'Alpha'
        assert groups[2]['name'] == 'Beta'

def test_get_all_groups_sort_members(client, sample_groups):
    with patch('app.db.Groups.find', return_value=sample_groups):
        response = client.get('/get_all_groups?sort=members')
        assert response.status_code == 200
        groups = json.loads(response.data)
        # Sorted by number of members descending
        assert groups[0]['name'] == 'Gamma'  # 3 members
        assert groups[1]['name'] == 'Beta'   # 2 members
        assert groups[2]['name'] == 'Alpha'  # 1 member

def test_get_all_groups_sort_alphabetical(client, sample_groups):
    with patch('app.db.Groups.find', return_value=sample_groups):
        response = client.get('/get_all_groups?sort=alphabetical')
        assert response.status_code == 200
        groups = json.loads(response.data)
        # Sorted alphabetically by name
        assert groups[0]['name'] == 'Alpha'
        assert groups[1]['name'] == 'Beta'
        assert groups[2]['name'] == 'Gamma'
