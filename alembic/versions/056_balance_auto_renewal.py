"""add explicit balance-funded subscription auto-renewal consent

Revision ID: 056_balance_auto_renewal
Revises: 055_dns_protection
"""

from alembic import op
import sqlalchemy as sa


revision = "056_balance_auto_renewal"
down_revision = "055_dns_protection"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "client_portal_subscriptions",
        sa.Column("auto_renew_source", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "client_portal_subscriptions",
        sa.Column("auto_renew_duration_days", sa.Integer(), nullable=True),
    )
    op.add_column(
        "client_portal_subscriptions",
        sa.Column("auto_renew_consent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_subscription_auto_renew_source",
        "client_portal_subscriptions",
        "auto_renew_source IS NULL OR auto_renew_source = 'balance'",
    )
    op.create_check_constraint(
        "ck_subscription_auto_renew_duration",
        "client_portal_subscriptions",
        "auto_renew_duration_days IS NULL OR auto_renew_duration_days IN (30, 90, 365)",
    )


def downgrade():
    op.drop_constraint(
        "ck_subscription_auto_renew_duration",
        "client_portal_subscriptions",
        type_="check",
    )
    op.drop_constraint(
        "ck_subscription_auto_renew_source",
        "client_portal_subscriptions",
        type_="check",
    )
    op.drop_column("client_portal_subscriptions", "auto_renew_consent_at")
    op.drop_column("client_portal_subscriptions", "auto_renew_duration_days")
    op.drop_column("client_portal_subscriptions", "auto_renew_source")
