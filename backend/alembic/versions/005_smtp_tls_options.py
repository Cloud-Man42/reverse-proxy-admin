"""smtp tls verification options

Revision ID: 005_smtp_tls_options
Revises: 004_imported_certificates
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa

revision = "005_smtp_tls_options"
down_revision = "004_imported_certificates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "smtp_settings",
        sa.Column("tls_server_name", sa.String(length=255), nullable=False, server_default=""),
    )
    op.add_column(
        "smtp_settings",
        sa.Column("verify_tls_certificate", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("smtp_settings", "verify_tls_certificate")
    op.drop_column("smtp_settings", "tls_server_name")
