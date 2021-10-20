"""added collector status

Revision ID: 6f087820c021
Revises: 03be3f06fca4
Create Date: 2021-11-05 10:45:10.639212

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6f087820c021'
down_revision = '03be3f06fca4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('collectors_node', sa.Column('created', sa.DateTime()))
    op.add_column('collectors_node', sa.Column('last_seen', sa.DateTime()))


def downgrade():
    op.drop_column('collectors_node', 'created')
    op.drop_column('collectors_node', 'last_seen')
