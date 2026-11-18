from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects import postgresql

from core.model.organization import Organization
from core.model.report_item import ReportItem, ReportItemCpe
from core.model.story import ReportItemStory, Story
from core.model.task import Task
from core.model.user import User
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


def test_row_locks_compile_for_postgres(session):
    # SQLite ignores FOR UPDATE, and PostgreSQL rejects it together with DISTINCT.
    admin = User.find_by_name("admin")
    assert admin is not None
    report_ids = select(ReportItemStory.report_item_id).where(ReportItemStory.story_id.in_(["story-a"]))
    statements = [
        ("story", Story.lock_select(["story-b", "story-a"])),
        ("story", Story.visible_query(admin, Story.lock_select(["story-a"]))),
        ("report_item", ReportItem.lock_select(["report-a"])),
        ("report_item", ReportItem.lock_select(report_ids)),
    ]

    for table, statement in statements:
        sql = str(statement.compile(dialect=postgresql.dialect()))
        assert sql.rstrip().endswith("FOR UPDATE"), sql
        assert f"ORDER BY {table}.id" in sql, sql
        assert "DISTINCT" not in sql, sql


def test_word_list_entry_updates_skip_existing_values(session):
    word_list = WordList("Entry updates", entries=[WordListEntry("existing")])
    session.add(word_list)
    session.flush()
    entries = [{"value": "existing"}, {"value": "new"}]

    WordListEntry.update_word_list_entries(word_list.id, entries)
    WordListEntry.update_word_list_entries(word_list.id, entries)

    assert sorted(entry.value for entry in word_list.entries) == ["existing", "new"]


def test_schedule_history_matches_legacy_and_cron_runs_without_manual_jobs(session):
    legacy = Task(id="collect-source", task="collector_task")
    older = Task(id="cron_source_1", task="collector_task")
    latest = Task(id="cron_source_2", task="collector_task")
    bot = Task(id="bot-schedule", task="bot-schedule")
    manual = Task(id="manual-bot", task="bot-schedule", worker_id="bot-schedule")
    wrong_task = Task(id="cron_source_3", task="other_task")
    tasks = [legacy, older, latest, bot, manual, wrong_task]
    for index, task in enumerate(tasks):
        task.last_run = datetime(2025, 1, 1, 0, index)
    # Equal timestamps use job IDs as the final tie-breaker.
    older.last_run = latest.last_run
    session.add_all(tasks)
    session.flush()

    results = Task.get_latest_for_schedules(
        {
            "collect-source": ("cron_source_", "collector_task"),
            "bot-schedule": ("cron_bot_", "bot-schedule"),
            "missing": ("cron_missing_", "collector_task"),
        }
    )

    assert results == {"collect-source": latest, "bot-schedule": bot}
    assert Task.get_latest_for_schedules({}) == {}
