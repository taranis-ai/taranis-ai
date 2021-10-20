"""fix typo occurence -> occurrence in column names

Revision ID: 03be3f06fca4
Revises: 35855286ef98
Create Date: 2021-10-31 20:59:55.786769

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03be3f06fca4'
down_revision = '35855286ef98'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('attribute_group_item', 'min_occurence', new_column_name='min_occurrence')
    op.alter_column('attribute_group_item', 'max_occurence', new_column_name='max_occurrence')


def downgrade():
    op.alter_column('attribute_group_item', 'min_occurrence', new_column_name='min_occurence')
    op.alter_column('attribute_group_item', 'max_occurrence', new_column_name='max_occurence')
