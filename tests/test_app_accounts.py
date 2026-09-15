"""Delegated admin accounts must remain separate from customer identities."""

from src.api.routes.app_accounts import (
    CreateAdminAccountRequest,
    UpdateAdminAccountRequest,
    create_admin_account,
    delete_admin_account,
    update_admin_account,
)
from src.database.models import AdminUser
from src.modules.subscription.subscription_models import ClientUser


def test_admin_account_creation_needs_no_email_and_creates_no_portal_user(db_session):
    result = create_admin_account(
        CreateAdminAccountRequest(
            username="support_agent",
            password="secure-password",
            role="manager",
            permissions=["support"],
        ),
        db_session,
    )

    assert result["username"] == "support_agent"
    assert result["role"] == "manager"
    assert result["permissions"] == ["support"]
    assert db_session.query(AdminUser).count() == 1
    assert db_session.query(ClientUser).count() == 0


def test_admin_account_changes_never_mutate_same_named_portal_user(db_session):
    customer = ClientUser(
        email="customer@example.test",
        username="shared_name",
        password_hash="customer-password-hash",
        is_active=True,
    )
    db_session.add(customer)
    db_session.commit()
    customer_id = customer.id

    account = create_admin_account(
        CreateAdminAccountRequest(
            username="shared_name",
            password="admin-password",
            role="manager",
            permissions=["support"],
        ),
        db_session,
    )
    update_admin_account(
        account["id"],
        UpdateAdminAccountRequest(password="changed-password", is_active=False),
        db_session,
    )

    customer = db_session.get(ClientUser, customer_id)
    assert customer is not None
    assert customer.password_hash == "customer-password-hash"
    assert customer.is_active is True

    delete_admin_account(account["id"], db_session)
    assert db_session.get(AdminUser, account["id"]) is None
    assert db_session.get(ClientUser, customer_id) is not None
