import pytest
from flask import url_for


@pytest.mark.parametrize(
    ("endpoint", "expected_tab"),
    [
        ("admin.scheduler", "scheduled"),
        ("admin.scheduler_jobs_table", "scheduled"),
        ("admin.scheduler_active_jobs", "active"),
        ("admin.scheduler_failed_jobs", "failed"),
        ("admin.scheduler_history", "history"),
    ],
)
def test_scheduler_deep_link_renders_dashboard(endpoint, expected_tab, authenticated_client, scheduler_api_mocks):
    with authenticated_client.application.app_context():
        url = url_for(endpoint)

    response = authenticated_client.get(url)

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert f'class="tab tab-active" data-tab="{expected_tab}"' in html
    assert f'id="{expected_tab}-tab" class="tab-panel ' in html
    assert f'id="{expected_tab}-tab" class="tab-panel hidden"' not in html


def test_scheduler_tab_query_param_overrides_initial(authenticated_client, scheduler_api_mocks):
    with authenticated_client.application.app_context():
        url = url_for("admin.scheduler_active_jobs", tab="scheduled")

    response = authenticated_client.get(url)

    assert response.status_code == 200

    html = response.get_data(as_text=True)
    assert 'class="tab tab-active" data-tab="scheduled"' in html
    assert 'id="scheduled-tab" class="tab-panel hidden"' not in html

