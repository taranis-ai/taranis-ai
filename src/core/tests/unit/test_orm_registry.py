"""Bookkeeping only: no application or database fixtures are needed."""

import json

from tests.performance.orm.registry import BASELINE, inventory_signature
from tests.performance.orm.scenarios import scenarios


def test_orm_inventory_accounts_for_source_declarations():
    expected = json.loads((BASELINE / "declarations-v1.json").read_text())
    actual = inventory_signature()
    assert actual == expected, "Reconcile changed declarations and regenerate the reviewed ORM inventory"
    specifications = scenarios()
    assert len({case.id for case in specifications}) == len(specifications)
