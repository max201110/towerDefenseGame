import pytest

from app import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'ok'


def test_index_is_available(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'<canvas' in response.data


def test_start_game_resets_state(client):
    response = client.post('/start_game')
    assert response.status_code == 200
    assert response.get_json()['status'] == 'success'
