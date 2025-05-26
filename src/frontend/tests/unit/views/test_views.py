import pytest


from frontend.views.base_view import BaseView


VIEW_ITEMS = BaseView._registry.items()
VIEW_IDS = list(BaseView._registry.keys())


class TestRegisteredViews:
    @pytest.mark.parametrize(
        "view_name,view_cls",
        VIEW_ITEMS,
        ids=VIEW_IDS,
    )
    def test_list_view_renders(self, view_name, view_cls, mock_core_endpoints, authenticated_client):
        """
        For each BaseView subclass:
          - GET its base route (list view) → 200
          - the unique name we injected in mock_data appears in the HTML
        """
        target_url = view_cls.get_base_route()
        resp = authenticated_client.get(target_url)

        assert resp.status_code == 200, f"{view_name!r} list-view did not return 200 (got {resp.status_code})"

        html = resp.get_data(as_text=True)
        payload = mock_core_endpoints[view_name]

        expected = payload.get("_expect_object", None)
        assert expected is not None, f"Expected: {expected} item in {view_name!r} not found in payload: {payload!r}"

        assert expected in html, f"Expected {expected!r} in the {view_name!r} HTML but did not find it.\nHTML snippet: {html[200:500]}…"
