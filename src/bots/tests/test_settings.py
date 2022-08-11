def test_api_key():
    from bots.config import Config

    api_key = Config.API_KEY
    assert api_key == "test_key"
