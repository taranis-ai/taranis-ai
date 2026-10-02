from sqlalchemy import func, select

from core.model.organization import Organization
from core.model.report_item import ReportItem, ReportItemCpe
from core.model.word_list import WordList, WordListEntry


def test_filtered_count_preserves_group_filters_and_ignores_paging(session):
    organizations = [Organization(name=f"count-{index}", description=group) for index, group in enumerate(["a", "a", "b", "b", "c"])]
    session.add_all(organizations)
    session.flush()
    query = (
        select(Organization.description)
        .where(Organization.id.in_([organization.id for organization in organizations]))
        .group_by(Organization.description)
        .having(func.count() > 1)
        .order_by(Organization.description)
        .offset(1)
        .limit(1)
    )

    assert Organization.get_filtered_count(query) == 2
    assert session.execute(query).scalars().all() == ["b"]


def test_report_cpe_matches_return_each_report_once(session):
    report = ReportItem("CPE matches", None, report_item_cpes=[ReportItemCpe("cpe-a"), ReportItemCpe("cpe-b")])
    other = ReportItem("Other CPE", None, report_item_cpes=[ReportItemCpe("cpe-c")])
    session.add_all([report, other])

    assert ReportItem.get_by_cpe(["cpe-a", "cpe-b"]) == [report]
    assert ReportItem.get_by_cpe([]) == []


def test_word_list_entry_updates_skip_existing_values(session):
    word_list = WordList("Entry updates", entries=[WordListEntry("existing")])
    session.add(word_list)
    session.flush()
    entries = [{"value": "existing"}, {"value": "new"}]

    WordListEntry.update_word_list_entries(word_list.id, entries)
    WordListEntry.update_word_list_entries(word_list.id, entries)

    assert sorted(entry.value for entry in word_list.entries) == ["existing", "new"]
