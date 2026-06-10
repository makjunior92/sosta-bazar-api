"""initial schema

Revision ID: 001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), unique=True, nullable=False),
        sa.Column("slug", sa.String(50), unique=True, nullable=False),
        sa.Column("base_url", sa.String(255), nullable=False),
        sa.Column("adapter_key", sa.String(50), unique=True, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True),
        sa.Column("last_scraped_at", sa.DateTime(timezone=True)),
        sa.Column("health_ok", sa.Boolean(), default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("stores")
