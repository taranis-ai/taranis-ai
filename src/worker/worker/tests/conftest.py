import pytest

@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_url': 'memory://'
    }
