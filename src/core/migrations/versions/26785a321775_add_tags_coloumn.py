"""add tags coloumn

Revision ID: 26785a321775
Revises: 094b85ef4dcf
Create Date: 2022-02-28 13:34:55.172694

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '26785a321775'
down_revision = '094b85ef4dcf'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('news_item_data', sa.Column('tags', sa.ARRAY(sa.String())))

def downgrade():
    op.drop_column('news_item_data', 'tags')
