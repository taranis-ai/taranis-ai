"""Regression tests for GH #1135: concurrent tag-cluster refreshes.

Two concurrent refreshes of the same (name, tag_type_key) used to race
between the delete and the insert in ``refresh_for_keys`` and violate the
composite primary key. The insert is now an upsert, so re-refreshing an
already materialized key must update in place instead of raising.
"""

import pytest

from core.managers.db_manager import db
from core.model.news_item import NewsItem
from core.model.news_item_tag import NewsItemTag, NewsItemTagCluster
from core.model.story import Story


@pytest.fixture
def story_with_tag_cluster(db, request):
    """One story carrying a tagged news item, cluster materialized once."""
    story = Story(title="cluster regression story")
    db.session.add(story)
    db.session.commit()

    item = NewsItem(
        title=f"cluster regression item ({request.node.name})",
        content=f"body {request.node.name}",
        story_id=story.id,
    )
    db.session.add(item)
    db.session.commit()

    tag = NewsItemTag(name="Apple", tag_type="CVE_VENDOR")
    tag.news_item_id = item.id
    db.session.add(tag)
    db.session.commit()

    NewsItemTagCluster.refresh_for_keys({("Apple", "CVE_VENDOR")})
    db.session.commit()
    return story


def test_refresh_twice_does_not_violate_primary_key(db, story_with_tag_cluster):
    """Re-refreshing a materialized cluster key updates in place (GH #1135)."""
    NewsItemTagCluster.refresh_for_keys({("Apple", "CVE_VENDOR")})
    db.session.commit()

    row = db.session.get(NewsItemTagCluster, ("Apple", "CVE_VENDOR"))
    assert row is not None


def test_stale_key_removed_when_source_tags_gone(db, story_with_tag_cluster):
    """Keys without source tags stay deleted after a refresh (issue acceptance)."""
    db.session.query(NewsItemTag).delete()
    db.session.commit()

    NewsItemTagCluster.refresh_for_keys({("Apple", "CVE_VENDOR")})
    db.session.commit()

    assert db.session.get(NewsItemTagCluster, ("Apple", "CVE_VENDOR")) is None
