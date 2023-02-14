def test_api_key():
    from bots.config import settings

    api_key = settings.API_KEY
    assert api_key == "test_key"
