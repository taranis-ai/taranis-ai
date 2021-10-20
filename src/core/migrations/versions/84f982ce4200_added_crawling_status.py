"""added crawling status

Revision ID: 84f982ce4200
Revises: 6f087820c021
Create Date: 2021-11-05 10:54:20.651770

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '84f982ce4200'
down_revision = '6f087820c021'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('osint_source', sa.Column('modified', sa.DateTime()))
    op.add_column('osint_source', sa.Column('last_collected', sa.DateTime()))
    op.add_column('osint_source', sa.Column('last_attempted', sa.DateTime()))
    op.add_column('osint_source', sa.Column('state', sa.SmallInteger()))
    op.add_column('osint_source', sa.Column('last_error_message', sa.String()))
    op.add_column('osint_source', sa.Column('screenshot', sa.LargeBinary()))


def downgrade():
    op.drop_column('osint_source', 'modified')
    op.drop_column('osint_source', 'last_collected')
    op.drop_column('osint_source', 'last_attempted')
    op.drop_column('osint_source', 'state')
    op.drop_column('osint_source', 'last_error_message')
    op.drop_column('osint_source', 'screenshot')
