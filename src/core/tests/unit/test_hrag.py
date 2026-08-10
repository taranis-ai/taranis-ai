import pytest

from core.model.hrag import HragAge


def test_hrag_age_accepts_a_parameterized_read_only_query():
    HragAge._validate_read_only_query(
        "MATCH (n:Malware {name: $name}) RETURN n AS result",
        {"name": "Example"},
    )


@pytest.mark.parametrize(
    "cypher",
    [
        "MATCH (n) RETURN n",
        "MATCH (n) DELETE n RETURN n AS result",
        "MATCH (n) RETURN n AS result; MATCH (m) RETURN m AS result",
        "MATCH (n) RETURN n AS result // comment",
    ],
)
def test_hrag_age_rejects_unsafe_or_ambiguous_queries(cypher: str):
    with pytest.raises(ValueError):
        HragAge._validate_read_only_query(cypher, {})


def test_hrag_age_requires_all_declared_parameters():
    with pytest.raises(ValueError, match="missing parameters: name"):
        HragAge._validate_read_only_query("MATCH (n {name: $name}) RETURN n AS result", {})


def test_hrag_age_renders_list_parameters_as_cypher_literals():
    assert HragAge._literal(["one", 2, None]) == "['one', 2, null]"


def test_hrag_age_dollar_quotes_queries_with_a_non_conflicting_tag():
    assert HragAge._dollar_quote("MATCH (n) RETURN n AS result") == "$hrag$MATCH (n) RETURN n AS result$hrag$"
    assert HragAge._dollar_quote("RETURN '$hrag$' AS result") == "$hrag_1$RETURN '$hrag$' AS result$hrag_1$"
