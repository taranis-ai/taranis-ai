from admin.config import Config
from pprint import pprint



def test_dashboard(dashboard_get_mock, client):
    response = client.get(f"{Config.APPLICATION_ROOT}/")
    print(response.text)
    pprint(response.__dict__ )
    assert response.status_code == 200
