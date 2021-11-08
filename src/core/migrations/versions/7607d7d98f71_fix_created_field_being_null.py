"""fix created field being null

Revision ID: 7607d7d98f71
Revises: 74e214f93e88
Create Date: 2021-11-18 13:17:43.606541

"""
from datetime import datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CollectorsNodeRev7607d7d98f71(Base):
    __tablename__ = 'collectors_node'
    id = sa.Column(sa.String(64), primary_key=True)
    created = sa.Column(sa.DateTime, default=datetime.now)
    last_seen = sa.Column(sa.DateTime, default=datetime.now)


class OSINTSourceRev7607d7d98f71(Base):
    __tablename__ = 'osint_source'
    id = sa.Column(sa.String(64), primary_key=True)
    modified = sa.Column(sa.DateTime, default=datetime.now)


# revision identifiers, used by Alembic.
revision = '7607d7d98f71'
down_revision = '74e214f93e88'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    to_update = session.query(CollectorsNodeRev7607d7d98f71).filter_by(created=None).all()
    for node in to_update:
        node.created = datetime.now()
        node.last_seen = datetime.now()
        session.add(node)
    session.commit()

    to_update = session.query(OSINTSourceRev7607d7d98f71).filter_by(modified=None).all()
    for source in to_update:
        source.modified = datetime.now()
        session.add(source)
    session.commit()


def downgrade():
    pass
