import pytest
from core.service import template_service

@pytest.fixture(autouse=True)
def clear_cache():
    # Clear the cache before each test
    template_service._template_validation_cache.clear()


def test_caching_and_invalidation(monkeypatch):
    # Simulate template content and path
    path = "test_template.txt"
    content1 = "Hello {{ name }}!"
    content2 = "Hello {{ user }}!"

    # Patch get_template_content to return content1
    monkeypatch.setattr(template_service, "get_template_content", lambda p: content1 if p == path else None)

    # First call: should compute and cache
    resp1 = template_service.build_template_response(path)
    assert resp1["validation_status"]["is_valid"] is True
    assert (path, template_service._get_content_hash(content1)) in template_service._template_validation_cache

    # Second call: should use cache (simulate by changing validate_template_content to fail if called again)
    called = {}
    def fake_validate(content):
        called["called"] = True
        return {"is_valid": False, "error_message": "Should not be called!"}
    monkeypatch.setattr(template_service, "validate_template_content", fake_validate)
    resp2 = template_service.build_template_response(path)
    assert resp2["validation_status"]["is_valid"] is True  # Still cached
    assert "called" not in called

    # Invalidate cache and change content
    template_service.invalidate_template_validation_cache(path)
    monkeypatch.setattr(template_service, "get_template_content", lambda p: content2 if p == path else None)
    # Now, validate_template_content should be called again
    called2 = {}
    def real_validate(content):
        called2["called"] = True
        return {"is_valid": True, "error_message": ""}
    monkeypatch.setattr(template_service, "validate_template_content", real_validate)
    resp3 = template_service.build_template_response(path)
    assert resp3["validation_status"]["is_valid"] is True
    assert "called" in called2
    # Cache should now have new hash
    assert (path, template_service._get_content_hash(content2)) in template_service._template_validation_cache
