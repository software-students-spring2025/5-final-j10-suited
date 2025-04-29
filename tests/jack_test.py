import pytest
from bson import ObjectId
from importlib import reload


@pytest.fixture(autouse=True)
def configure_test_db(monkeypatch):
    monkeypatch.setenv("MONGO_DBNAME", "myapp_test")
    import app
    reload(app)
    return app


@pytest.fixture
def client(configure_test_db):
    app = configure_test_db
    app.app.config["TESTING"] = True
    return app.app.test_client()


@pytest.fixture
def db(configure_test_db):
    return configure_test_db.db


def create_sample_groups(db):
    groups = [
        {'name': 'Beta',  'members': ['user1', 'user2']},
        {'name': 'Alpha', 'members': ['user1']},
        {'name': 'Gamma', 'members': ['user1', 'user2', 'user3']},
    ]
    db.Groups.drop()
    ids = db.Groups.insert_many(groups).inserted_ids
    return list(db.Groups.find({"_id": {"$in": ids}}))


def test_get_all_groups_default_order(client, db):
    create_sample_groups(db)
    rv = client.get('/get_all_groups')
    assert rv.status_code == 200
    groups = rv.get_json()

    assert groups[0]['name'] == 'Beta'
    assert groups[1]['name'] == 'Alpha'
    assert groups[2]['name'] == 'Gamma'


def test_get_all_groups_sort_newest(client, db):
    create_sample_groups(db)
    rv = client.get('/get_all_groups?sort=newest')
    assert rv.status_code == 200
    groups = rv.get_json()

    assert groups[0]['name'] == 'Gamma'
    assert groups[1]['name'] == 'Alpha'
    assert groups[2]['name'] == 'Beta'


def test_get_all_groups_sort_members(client, db):
    create_sample_groups(db)
    rv = client.get('/get_all_groups?sort=members')
    assert rv.status_code == 200
    groups = rv.get_json()
    
    assert groups[0]['name'] == 'Gamma'
    assert groups[1]['name'] == 'Beta'
    assert groups[2]['name'] == 'Alpha'


def test_get_all_groups_sort_alphabetical(client, db):
    create_sample_groups(db)
    rv = client.get('/get_all_groups?sort=alphabetical')
    assert rv.status_code == 200
    groups = rv.get_json()

    assert groups[0]['name'] == 'Alpha'
    assert groups[1]['name'] == 'Beta'
    assert groups[2]['name'] == 'Gamma'
