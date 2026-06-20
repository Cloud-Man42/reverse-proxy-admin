"""imported certificates table

Revision ID: 004_imported_certificates
Revises: 003_platform_extensions
Create Date: 2026-06-20
"""

from alembic import op
import sqlalchemy as sa

revision = "004_imported_certificates"
down_revision = "003_platform_extensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imported_certificates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("primary_domain", sa.String(length=255), nullable=False),
        sa.Column("domains_json", sa.Text(), nullable=False, server_default="'[]'"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_imported_certificates_name", "imported_certificates", ["name"], unique=True)
    op.create_index("ix_imported_certificates_primary_domain", "imported_certificates", ["primary_domain"])


def downgrade() -> None:
    op.drop_index("ix_imported_certificates_primary_domain", table_name="imported_certificates")
    op.drop_index("ix_imported_certificates_name", table_name="imported_certificates")
    op.drop_table("imported_certificates")
