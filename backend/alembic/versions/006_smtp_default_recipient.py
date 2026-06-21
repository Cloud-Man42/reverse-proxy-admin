"""smtp default recipient email

Revision ID: 006_smtp_default_recipient
Revises: 005_smtp_tls_options
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa

revision = "006_smtp_default_recipient"
down_revision = "005_smtp_tls_options"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "smtp_settings",
        sa.Column("default_recipient_email", sa.String(length=255), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("smtp_settings", "default_recipient_email")
