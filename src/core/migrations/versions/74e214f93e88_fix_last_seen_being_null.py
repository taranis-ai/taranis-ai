"""fix last_seen being null

Revision ID: 74e214f93e88
Revises: a131dbce9c3c
Create Date: 2021-11-18 10:48:53.156339

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import orm

# revision identifiers, used by Alembic.
revision = '74e214f93e88'
down_revision = 'a131dbce9c3c'
branch_labels = None
depends_on = None

from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class CollectorsNodeRev74e214f93e88(Base):
    __tablename__ = 'collectors_node'
    id = sa.Column(sa.String(64), primary_key=True)
    name = sa.Column(sa.String(), unique=True, nullable=False)
    description = sa.Column(sa.String())
    api_url = sa.Column(sa.String(), nullable=False)
    api_key = sa.Column(sa.String(), nullable=False)
    created = sa.Column(sa.DateTime, default=datetime.now)
    last_seen = sa.Column(sa.DateTime, default=datetime.now)


def upgrade():
    bind = op.get_bind()
    session = orm.Session(bind=bind)

    to_update = session.query(CollectorsNodeRev74e214f93e88).filter_by(last_seen=None).all()
    for node in to_update:
        node.last_seen = node.created
        session.add(node)
    session.commit()

    op.alter_column('collectors_node', 'created', server_default=sa.func.current_timestamp())
    op.alter_column('collectors_node', 'last_seen', server_default=sa.func.current_timestamp())


def downgrade():
    pass
