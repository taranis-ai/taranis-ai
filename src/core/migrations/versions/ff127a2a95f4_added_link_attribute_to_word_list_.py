"""added link attribute to word list category

Revision ID: ff127a2a95f4
Revises: e46b55f712f9
Create Date: 2022-07-01 23:33:11.395700

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "ff127a2a95f4"
down_revision = "094b85ef4dcf"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_context().bind
    insp = inspect(bind)
    columns = insp.get_columns("word_list_category")
    column_names = [c["name"] for c in columns]
    if "link" not in column_names:
        op.add_column(
            "word_list_category",
            sa.Column("link", sa.String(), server_default=None, nullable=True),
        )


def downgrade():
    op.drop_column("word_list_category", "link")
