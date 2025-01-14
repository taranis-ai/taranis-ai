from admin.config import Config


def test_jobindex(schedule_get_mock, client):
    response = client.get(f"{Config.APPLICATION_ROOT}/")
    print(response.text)
    assert response.status_code == 200
