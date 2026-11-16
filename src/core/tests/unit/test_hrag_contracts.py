import pytest
from models.hrag import CompactExtractionResult, ExtractionResult, bounded_content, entity_identity, input_fingerprint
from pydantic import ValidationError


def test_extraction_provenance_identity_and_tag_projection():
    content = "APT29 exploits CVE-2026-1234."
    result = ExtractionResult.model_validate(
        {
            "entities": [
                {"id": "a", "type": "GROUP", "name": "APT29", "evidence": {"start": 0, "end": 5, "quote": "APT29"}},
                {"id": "v", "type": "VULNERABILITY", "name": "CVE-2026-1234", "evidence": {"start": 15, "end": 28, "quote": "CVE-2026-1234"}},
            ],
            "relations": [
                {
                    "type": "EXPLOITS",
                    "source_id": "a",
                    "target_id": "v",
                    "evidence": {"start": 0, "end": len(content), "quote": content},
                }
            ],
        }
    ).validate_content(content)
    assert result.ner_tags() == {"APT29": "GROUP"}
    assert entity_identity(result.entities[0], "article-a", "v1") != entity_identity(result.entities[0], "article-b", "v1")
    assert entity_identity(result.entities[1], "article-a", "v1") == entity_identity(result.entities[1], "article-b", "v1")
    with pytest.raises(ValueError, match="Evidence does not match"):
        result.validate_content("A different article")
    payload = result.model_dump()
    payload["relations"][0]["target_id"] = "a"
    with pytest.raises(ValidationError, match="endpoint types"):
        ExtractionResult.model_validate(payload)


def test_bounded_inputs_have_independent_invalidation():
    original = "a" * 4000 + "b" * 16000
    changed = "a" * 4000 + "c" * 16000
    assert input_fingerprint(bounded_content(original, 4000), "embedding-v1") == input_fingerprint(
        bounded_content(changed, 4000), "embedding-v1"
    )
    assert input_fingerprint(bounded_content(original, 20000), "extraction-v1") != input_fingerprint(
        bounded_content(changed, 20000), "extraction-v1"
    )
    assert input_fingerprint(original, "model-v1") != input_fingerprint(original, "model-v2")
    assert bounded_content(None, 4000) == ""


def test_compact_extraction_resolves_unicode_repeated_quotes_and_validates_graph():
    quote = "APT29 did not use Mimikatz."
    content = f"Übersicht: {quote} {quote}"
    payload = {
        "entities": [{"id": "a", "name": "APT29", "type": "GROUP"}, {"id": "b", "name": "Mimikatz", "type": "TOOL"}],
        "relations": [{"source_id": "a", "target_id": "b", "type": "USES", "quote": quote, "assertion": "negated"}],
    }
    result = CompactExtractionResult.model_validate(payload).resolve(content)
    assert result.entities[0].evidence.model_dump() == {"start": 11, "end": 16, "quote": "APT29"}
    assert result.relations[0].evidence.model_dump() == {"start": 11, "end": 38, "quote": quote}
    assert result.relations[0].assertion == "negated" and result.relations[0].date == ""
    for invalid_content in (content.replace("Mimikatz", "another tool"), content.replace("did not use", "used")):
        with pytest.raises(ValueError, match="Evidence does not match"):
            CompactExtractionResult.model_validate(payload).resolve(invalid_content)
    payload["relations"][0]["target_id"] = "missing"
    with pytest.raises(ValueError, match="Invalid extracted relationship"):
        CompactExtractionResult.model_validate(payload).resolve(content)
    vulnerability = CompactExtractionResult.model_validate({"entities": [{"id": "v", "name": "CVE-2026-1234", "type": "VULNERABILITY"}]})
    with pytest.raises(ValueError, match="Vulnerability identifier is absent"):
        vulnerability.resolve("CVE-2026-12345")
