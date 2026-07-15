import base64
from datetime import datetime
from urllib.parse import quote

import pytest

from tests.application.support.api_test_base import BaseTest


class TestPublishApi(BaseTest):
    base_uri = "/api/publish"

    def test_post_Product(self, client, auth_header, cleanup_product):
        """
        This test queries the /api/publish/products endpoint with a POST request.
        It expects a valid data and a valid status-code
        """
        response = self.assert_post_ok(client, "products", auth_header=auth_header, json_data=cleanup_product)
        assert response.get_json()["id"] == cleanup_product["id"]

    def test_get_Products(self, client, auth_header, cleanup_product):
        """
        This test queries the /api/publish/products endpoint.
        It expects a valid data and a valid status-code
        """
        response = self.assert_get_ok(client, "products", auth_header)
        assert response.get_json()["total_count"] == 1
        assert response.get_json()["items"][0]["title"] == cleanup_product["title"]

    def test_rendered_product_download_returns_attachment(self, app, client, auth_header, pdf_product):
        file_bytes = b"This is a pdf"
        pdf_product.update_render(base64.b64encode(file_bytes).decode())
        expected_filename = f"Test Product_{datetime.now().strftime('%d-%m-%Y_%H-%M')}.pdf"

        response = client.get(self.concat_url(f"products/{pdf_product.id}/render"), headers=auth_header)
        assert response.status_code == 200
        assert response.data == file_bytes
        assert response.mimetype == "application/pdf"
        assert response.headers.get("Content-Disposition") == f'attachment; filename="{expected_filename}"'

    def test_taranis_publish_stores_and_serves_report_without_authentication(
        self, app, client, auth_header, api_header, monkeypatch, pdf_product, tmp_path
    ):
        invalidations = []

        def capture_invalidation(status, **kwargs):
            invalidations.append((status, kwargs))

        file_bytes = b"Public report"
        pdf_product.last_published_url = "https://previous.example/report.pdf"
        pdf_product.update_render(base64.b64encode(file_bytes).decode())
        monkeypatch.chdir(tmp_path)
        monkeypatch.setitem(app.config, "DATA_FOLDER", "taranis_data")
        monkeypatch.setattr("core.api.worker.invalidate_frontend_cache_on_success", capture_invalidation)

        unauthorized_response = client.post(f"/api/worker/products/{pdf_product.id}/publish")
        assert unauthorized_response.status_code == 401

        publish_response = client.post(f"/api/worker/products/{pdf_product.id}/publish", headers=api_header)
        assert publish_response.status_code == 200
        assert publish_response.get_json()["url"] == f"/reports/{pdf_product.id}"
        assert (tmp_path / "taranis_data" / "published-reports" / pdf_product.id).read_bytes() == file_bytes
        assert pdf_product.last_published_url == f"/reports/{pdf_product.id}"
        assert invalidations == [
            (
                200,
                {
                    "scopes": ("publish_views",),
                    "object_ids": {"product": pdf_product.id},
                },
            )
        ]

        from core.managers.db_manager import db

        db.session.expire_all()
        detail_response = client.get(self.concat_url(f"products/{pdf_product.id}"), headers=auth_header)
        assert detail_response.status_code == 200
        assert detail_response.get_json()["last_published_url"] == f"/reports/{pdf_product.id}"

        public_response = client.get(f"/reports/{pdf_product.id}")
        assert public_response.status_code == 200
        assert public_response.data == file_bytes
        assert public_response.mimetype == "application/pdf"
        assert public_response.headers["Content-Security-Policy"] == "sandbox allow-scripts allow-downloads"
        assert public_response.headers["X-Content-Type-Options"] == "nosniff"

    def test_failed_taranis_publish_keeps_previous_url(self, app, monkeypatch, pdf_product, tmp_path):
        from core.managers.db_manager import db
        from core.service.product import ProductService

        previous_url = "https://previous.example/report.pdf"
        pdf_product.last_published_url = previous_url
        pdf_product.update_render(base64.b64encode(b"Public report").decode())
        monkeypatch.setitem(app.config, "DATA_FOLDER", str(tmp_path))

        def fail_replace(self, target):
            raise OSError("storage unavailable")

        monkeypatch.setattr("core.service.product.Path.replace", fail_replace)

        with pytest.raises(OSError, match="storage unavailable"):
            ProductService.publish_to_taranis(pdf_product.id)

        db.session.refresh(pdf_product)
        assert pdf_product.last_published_url == previous_url

    def test_unknown_public_report_returns_not_found(self, client):
        response = client.get("/reports/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    @pytest.mark.parametrize("product_id", ["..", "<script>alert(1)</script>"])
    def test_untrusted_product_ids_are_not_used_in_paths_or_responses(self, app, client, api_header, monkeypatch, product_id, tmp_path):
        monkeypatch.setitem(app.config, "DATA_FOLDER", str(tmp_path))
        encoded_product_id = quote(product_id, safe="")

        publish_response = client.post(f"/api/worker/products/{encoded_product_id}/publish", headers=api_header)
        public_response = client.get(f"/reports/{encoded_product_id}")

        assert publish_response.status_code == 404
        assert public_response.status_code == 404
        assert product_id not in publish_response.get_data(as_text=True)
        assert product_id not in public_response.get_data(as_text=True)
        assert not (tmp_path / "published-reports").exists()

    def test_get_publisher_presets(self, client, auth_header, publish_publisher_preset):
        response = self.assert_get_ok(client, f"publisher-presets?search={publish_publisher_preset['name']}", auth_header)

        assert response.get_json()["items"][0]["id"] == publish_publisher_preset["id"]
        assert response.get_json()["items"][0]["name"] == publish_publisher_preset["name"]
        assert response.get_json()["items"][0]["type"] == publish_publisher_preset["type"]
        assert response.get_json()["items"][0]["description"] == publish_publisher_preset["description"]
        assert "parameters" not in response.get_json()["items"][0]

    def test_default_taranis_publisher_is_always_available(self, client, auth_header):
        from core.model.publisher_preset import PublisherPreset

        response = self.assert_get_ok(client, "publisher-presets?search=Taranis+Publisher", auth_header)

        assert response.get_json()["items"] == [
            {
                "id": PublisherPreset.DEFAULT_TARANIS_ID,
                "name": "Taranis Publisher",
                "description": "Publisher for making products publicly available in Taranis",
                "type": "taranis_publisher",
            }
        ]

    def test_default_taranis_publisher_cannot_be_deleted(self, client, auth_header):
        from core.model.publisher_preset import PublisherPreset

        response = client.delete(f"/api/config/publishers-presets/{PublisherPreset.DEFAULT_TARANIS_ID}", headers=auth_header)

        assert response.status_code == 400
        assert response.get_json() == {"error": "The default Taranis publisher cannot be deleted"}

    def test_get_publisher_preset_detail(self, client, auth_header, publish_publisher_preset):
        response = self.assert_get_ok(client, f"publisher-presets/{publish_publisher_preset['id']}", auth_header)

        assert response.get_json()["id"] == publish_publisher_preset["id"]
        assert response.get_json()["name"] == publish_publisher_preset["name"]
        assert response.get_json()["type"] == publish_publisher_preset["type"]
        assert response.get_json()["description"] == publish_publisher_preset["description"]
        assert "parameters" not in response.get_json()


def test_default_taranis_publisher_is_restored_when_missing(session):
    from core.managers.db_manager import db
    from core.managers.db_seed_manager import pre_seed_update
    from core.model.publisher_preset import PublisherPreset

    db.session.execute(db.delete(PublisherPreset).where(PublisherPreset.id == PublisherPreset.DEFAULT_TARANIS_ID))
    db.session.commit()

    pre_seed_update(db.engine)
    pre_seed_update(db.engine)

    restored = PublisherPreset.get(PublisherPreset.DEFAULT_TARANIS_ID)
    count = db.session.scalar(
        db.select(db.func.count()).select_from(PublisherPreset).where(PublisherPreset.id == PublisherPreset.DEFAULT_TARANIS_ID)
    )
    assert restored is not None
    assert restored.id == PublisherPreset.DEFAULT_TARANIS_ID
    assert count == 1


def test_default_taranis_publisher_recovers_from_concurrent_insert(session, monkeypatch):
    from sqlalchemy.exc import IntegrityError

    from core.managers.db_manager import db
    from core.model.publisher_preset import PublisherPreset

    db.session.execute(db.delete(PublisherPreset).where(PublisherPreset.id == PublisherPreset.DEFAULT_TARANIS_ID))
    db.session.commit()
    add = PublisherPreset.add

    def add_then_conflict(data):
        add(data)
        raise IntegrityError("insert", {}, Exception("duplicate key"))

    monkeypatch.setattr(PublisherPreset, "add", staticmethod(add_then_conflict))

    preset = PublisherPreset.ensure_default_taranis()

    assert preset.id == PublisherPreset.DEFAULT_TARANIS_ID
