"""add server-verified Google Play subscription state

Revision ID: 057_google_play_subscriptions
Revises: 056_balance_auto_renewal
"""

from alembic import op
import sqlalchemy as sa


revision = "057_google_play_subscriptions"
down_revision = "056_balance_auto_renewal"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "client_portal_subscriptions",
        sa.Column("billing_source", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "client_portal_subscriptions",
        sa.Column("billing_reference", sa.String(length=160), nullable=True),
    )
    op.create_index(
        "ix_cps_billing_reference",
        "client_portal_subscriptions",
        ["billing_source", "billing_reference"],
        unique=False,
    )
    op.create_table(
        "google_play_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purchase_token_hash", sa.String(length=64), nullable=False),
        sa.Column("purchase_token", sa.Text(), nullable=False),
        sa.Column("product_id", sa.String(length=100), nullable=False),
        sa.Column("base_plan_id", sa.String(length=100), nullable=False),
        sa.Column("plan_tier", sa.String(length=50), nullable=False),
        sa.Column("subscription_state", sa.String(length=80), nullable=False),
        sa.Column("expiry_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("auto_renewing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("order_id", sa.String(length=255), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["client_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_google_play_subscriptions_user_id",
        "google_play_subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_google_play_subscriptions_token_hash",
        "google_play_subscriptions",
        ["purchase_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_google_play_subscriptions_expiry",
        "google_play_subscriptions",
        ["expiry_time"],
        unique=False,
    )
    op.create_index(
        "ix_google_play_subscriptions_order_id",
        "google_play_subscriptions",
        ["order_id"],
        unique=False,
    )
    op.create_index(
        "ix_google_play_user_state",
        "google_play_subscriptions",
        ["user_id", "subscription_state"],
        unique=False,
    )


def downgrade():
    op.drop_table("google_play_subscriptions")
    op.drop_index(
        "ix_cps_billing_reference",
        table_name="client_portal_subscriptions",
    )
    op.drop_column("client_portal_subscriptions", "billing_reference")
    op.drop_column("client_portal_subscriptions", "billing_source")
