"""Regression tests for GH #1135: concurrent tag-cluster refreshes.

Two concurrent refreshes of the same (name, tag_type_key) can interleave
the delete and insert phases of ``refresh_for_keys``: the losing writer
runs its insert phase on a key the winner already wrote, without a prior
delete, and the plain INSERT violated the composite primary key. The
insert phase is now an upsert, so re-inserting a materialized key must
update in place instead of raising.
"""

import pytest

from core.model.news_item import NewsItem
from core.model.news_item_tag import NewsItemTag, NewsItemTagCluster
from core.model.story import Story


@pytest.fixture
def story_with_tag_cluster(session):
    """One story carrying a tagged news item; the cluster materialized once.

    Runs inside the transactional ``session`` fixture, so every commit is
    rolled back when the test ends.
    """
    story = Story(title="cluster regression story")
    session.add(story)
    session.flush()

    item = NewsItem(title="cluster regression item", content="body", story_id=story.id)
    session.add(item)
    session.flush()

    tag = NewsItemTag(name="Apple", tag_type="CVE_VENDOR")
    tag.news_item_id = item.id
    session.add(tag)
    session.flush()

    NewsItemTagCluster.refresh_for_keys({("Apple", "CVE_VENDOR")}, session=session)
    session.flush()
    return story


def test_insert_current_keys_upserts_materialized_cluster(session, story_with_tag_cluster):
    """Re-inserting a materialized key updates in place (GH #1135).

    The test drives the insert phase directly, because that is the only way
    to observe the race deterministically: a concurrent refresh reaches
    ``_insert_current_keys`` while the winner's rows are already in the
    table. With the old plain INSERT this raised a primary-key violation,
    so the test fails on the old code and passes with the upsert.
    """
    assert session.get(NewsItemTagCluster, ("Apple", "CVE_VENDOR")) is not None

    NewsItemTagCluster._insert_current_keys({("Apple", "CVE_VENDOR")}, session=session)
    session.flush()

    row = session.get(NewsItemTagCluster, ("Apple", "CVE_VENDOR"))
    assert row is not None
    assert row.get_count() >= 1


def test_refresh_twice_keeps_cluster_row(session, story_with_tag_cluster):
    """A full re-refresh of a materialized key keeps exactly one row (GH #1135)."""
    NewsItemTagCluster.refresh_for_keys({("Apple", "CVE_VENDOR")}, session=session)
    session.flush()

    rows = (
        session.query(NewsItemTagCluster)
        .filter(NewsItemTagCluster.name == "Apple", NewsItemTagCluster.tag_type_key == "CVE_VENDOR")
        .all()
    )
    assert len(rows) == 1


def test_stale_key_removed_when_source_tags_gone(session, story_with_tag_cluster):
    """Keys without source tags stay deleted after a refresh (issue acceptance)."""
    session.query(NewsItemTag).delete()

    NewsItemTagCluster.refresh_for_keys({("Apple", "CVE_VENDOR")}, session=session)
    session.flush()

    assert session.get(NewsItemTagCluster, ("Apple", "CVE_VENDOR")) is None
