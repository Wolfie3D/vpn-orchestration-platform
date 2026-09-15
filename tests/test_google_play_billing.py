import base64
import json
from datetime import datetime, timedelta, timezone

import pytest

from src.modules.plugin_loader.state import set_plugin_enabled
from src.modules.subscription.google_play_billing import (
    BasePlan,
    GooglePlayConfigurationError,
    GooglePlayVerificationError,
    PlayConfig,
    VerifiedSubscription,
    apply_verified_subscription,
    decode_rtdn,
    get_config,
    obfuscated_account_id,
    token_hash,
    verify_pubsub_identity,
    verify_purchase,
    verify_rtdn_purchase,
)
from src.modules.subscription.subscription_models import (
    ClientPortalPayment,
    ClientPortalSubscription,
    ClientUser,
    GooglePlaySubscription,
    SubscriptionPlan,
    SubscriptionStatus,
)


def config(tmp_path) -> PlayConfig:
    credentials = tmp_path / "service-account.json"
    credentials.write_text("{}", encoding="utf-8")
    return PlayConfig(
        enabled=True,
        package_name="us.aiii.back2home",
        product_id="unlimited_access",
        service_account_file=str(credentials),
        account_secret="test-binding-secret-with-enough-entropy",
        base_plans={
            "monthly": BasePlan(30, "premium", 3.50),
            "quarterly": BasePlan(90, "premium", 10.00),
        },
        rtdn_audience="https://console.example/client-portal/webhooks/google-play/rtdn",
        rtdn_service_account_email="push@example.iam.gserviceaccount.com",
    )


def seed(db_session):
    user = ClientUser(username="play-user", password_hash="not-used", is_active=True)
    other = ClientUser(username="other-user", password_hash="not-used", is_active=True)
    plan = SubscriptionPlan(
        tier="premium",
        name="Unlimited",
        description="test",
        max_devices=5,
        traffic_limit_gb=None,
        bandwidth_limit_mbps=None,
        price_monthly_usd=3.50,
        is_active=True,
        is_visible=True,
    )
    db_session.add_all([user, other, plan])
    db_session.commit()
    return user, other


def publisher_payload(cfg, user_id, *, state="SUBSCRIPTION_STATE_ACTIVE", expiry=None):
    return {
        "kind": "androidpublisher#subscriptionPurchaseV2",
        "subscriptionState": state,
        "acknowledgementState": "ACKNOWLEDGEMENT_STATE_PENDING",
        "externalAccountIdentifiers": {
            "obfuscatedExternalAccountId": obfuscated_account_id(user_id, cfg),
        },
        "lineItems": [{
            "productId": cfg.product_id,
            "expiryTime": (expiry or (datetime.now(timezone.utc) + timedelta(days=30))).isoformat(),
            "latestSuccessfulOrderId": "GPA.1234-5678-9012-34567",
            "offerDetails": {"basePlanId": "monthly"},
            "autoRenewingPlan": {"autoRenewEnabled": True},
        }],
    }


def test_configuration_fails_closed_until_every_secret_exists(monkeypatch, tmp_path):
    monkeypatch.setenv("FLIREXA_PLUGIN_STATE_FILE", str(tmp_path / "plugin-state.json"))
    monkeypatch.setenv("GOOGLE_PLAY_BILLING_ENABLED", "1")
    monkeypatch.setenv("GOOGLE_PLAY_PACKAGE_NAME", "us.aiii.back2home")
    monkeypatch.setenv("GOOGLE_PLAY_SUBSCRIPTION_PRODUCT_ID", "unlimited_access")
    monkeypatch.delenv("GOOGLE_PLAY_ACCOUNT_BINDING_SECRET", raising=False)
    monkeypatch.delenv("GOOGLE_PLAY_SERVICE_ACCOUNT_FILE", raising=False)
    monkeypatch.delenv("GOOGLE_PLAY_BASE_PLANS_JSON", raising=False)
    assert get_config().enabled is False

    key = tmp_path / "service.json"
    key.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_PLAY_ACCOUNT_BINDING_SECRET", "s" * 32)
    monkeypatch.setenv("GOOGLE_PLAY_SERVICE_ACCOUNT_FILE", str(key))
    monkeypatch.setenv(
        "GOOGLE_PLAY_BASE_PLANS_JSON",
        json.dumps({"monthly": {"duration_days": 30, "plan_tier": "premium", "amount_usd": 3.5}}),
    )
    assert get_config(require_enabled=True).enabled is True


def test_operator_can_disable_google_play_without_removing_configuration(monkeypatch, tmp_path):
    state_file = tmp_path / "plugin-state.json"
    monkeypatch.setenv("FLIREXA_PLUGIN_STATE_FILE", str(state_file))
    monkeypatch.setenv("GOOGLE_PLAY_BILLING_ENABLED", "1")
    monkeypatch.setenv("GOOGLE_PLAY_PACKAGE_NAME", "us.aiii.back2home")
    monkeypatch.setenv("GOOGLE_PLAY_SUBSCRIPTION_PRODUCT_ID", "unlimited_access")
    monkeypatch.setenv("GOOGLE_PLAY_ACCOUNT_BINDING_SECRET", "s" * 32)
    credentials = tmp_path / "service.json"
    credentials.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("GOOGLE_PLAY_SERVICE_ACCOUNT_FILE", str(credentials))
    monkeypatch.setenv(
        "GOOGLE_PLAY_BASE_PLANS_JSON",
        json.dumps({"monthly": {"duration_days": 30, "plan_tier": "premium", "amount_usd": 3.5}}),
    )

    assert get_config(require_enabled=True).enabled is True
    set_plugin_enabled("google-play-billing", False)
    disabled = get_config(require_enabled=False)
    assert disabled.enabled is False
    assert disabled.configured is True
    with pytest.raises(GooglePlayConfigurationError, match="not fully configured"):
        get_config(require_enabled=True)

    set_plugin_enabled("google-play-billing", True)
    assert get_config(require_enabled=True).enabled is True


@pytest.mark.asyncio
async def test_verification_binds_google_purchase_to_portal_user(monkeypatch, tmp_path):
    cfg = config(tmp_path)
    payload = publisher_payload(cfg, 17)

    async def fake_request(*args, **kwargs):
        return payload

    monkeypatch.setattr(
        "src.modules.subscription.google_play_billing._publisher_request",
        fake_request,
    )
    verified = await verify_purchase("x" * 64, expected_user_id=17, config=cfg)
    assert verified.product_id == "unlimited_access"
    assert verified.base_plan_id == "monthly"
    assert verified.plan_tier == "premium"
    assert verified.entitled is True

    with pytest.raises(GooglePlayVerificationError, match="another portal account"):
        await verify_purchase("x" * 64, expected_user_id=18, config=cfg)


@pytest.mark.asyncio
async def test_rtdn_resolves_out_of_app_resubscription_through_expired_token(
    monkeypatch, db_session, tmp_path
):
    cfg = config(tmp_path)
    user, _ = seed(db_session)
    old_token = "old-" + "o" * 60
    old = VerifiedSubscription(
        purchase_token=old_token,
        product_id=cfg.product_id,
        base_plan_id="monthly",
        plan_tier="premium",
        duration_days=30,
        amount_usd=3.50,
        subscription_state="SUBSCRIPTION_STATE_EXPIRED",
        expiry_time=datetime.now(timezone.utc) - timedelta(days=1),
        auto_renewing=False,
        acknowledged=True,
        order_id="GPA.0000-1111-2222-33333",
        obfuscated_account_id=obfuscated_account_id(user.id, cfg),
    )
    apply_verified_subscription(db_session, old, user_id=user.id)

    payload = publisher_payload(cfg, user.id)
    payload.pop("externalAccountIdentifiers")
    payload["outOfAppPurchaseContext"] = {
        "expiredPurchaseToken": old_token,
        "expiredExternalAccountIdentifiers": {
            "obfuscatedExternalAccountId": obfuscated_account_id(user.id, cfg),
        },
    }

    async def fake_request(*args, **kwargs):
        return payload

    monkeypatch.setattr(
        "src.modules.subscription.google_play_billing._publisher_request",
        fake_request,
    )
    resolved = await verify_rtdn_purchase(db_session, "new-" + "n" * 60, config=cfg)
    assert resolved is not None
    verified, resolved_user_id = resolved
    assert resolved_user_id == user.id
    assert verified.entitled is True


@pytest.mark.asyncio
async def test_rtdn_leaves_unknown_unlinked_purchase_unclaimed(monkeypatch, db_session, tmp_path):
    cfg = config(tmp_path)
    user, _ = seed(db_session)
    payload = publisher_payload(cfg, user.id)

    async def fake_request(*args, **kwargs):
        return payload

    monkeypatch.setattr(
        "src.modules.subscription.google_play_billing._publisher_request",
        fake_request,
    )
    assert await verify_rtdn_purchase(db_session, "new-" + "u" * 60, config=cfg) is None


def test_apply_is_idempotent_and_uses_exact_google_expiry(db_session, tmp_path):
    user, _ = seed(db_session)
    expiry = datetime.now(timezone.utc) + timedelta(days=29, hours=4)
    verified = VerifiedSubscription(
        purchase_token="token-" + "a" * 50,
        product_id="unlimited_access",
        base_plan_id="monthly",
        plan_tier="premium",
        duration_days=30,
        amount_usd=3.50,
        subscription_state="SUBSCRIPTION_STATE_ACTIVE",
        expiry_time=expiry,
        auto_renewing=True,
        acknowledged=False,
        order_id="GPA.1111-2222-3333-44444",
        obfuscated_account_id="opaque",
    )

    first = apply_verified_subscription(db_session, verified, user_id=user.id)
    second = apply_verified_subscription(db_session, verified, user_id=user.id)
    assert first.id == second.id
    assert db_session.query(GooglePlaySubscription).count() == 1
    assert db_session.query(ClientPortalPayment).count() == 1
    subscription = db_session.query(ClientPortalSubscription).filter_by(user_id=user.id).one()
    actual_expiry = subscription.expiry_date
    if actual_expiry.tzinfo is None:
        actual_expiry = actual_expiry.replace(tzinfo=timezone.utc)
    assert actual_expiry == expiry
    assert subscription.billing_source == "google_play"
    assert subscription.billing_reference == token_hash(verified.purchase_token)


def test_purchase_token_cannot_move_between_accounts(db_session, tmp_path):
    user, other = seed(db_session)
    verified = VerifiedSubscription(
        purchase_token="token-" + "b" * 50,
        product_id="unlimited_access",
        base_plan_id="monthly",
        plan_tier="premium",
        duration_days=30,
        amount_usd=3.50,
        subscription_state="SUBSCRIPTION_STATE_ACTIVE",
        expiry_time=datetime.now(timezone.utc) + timedelta(days=30),
        auto_renewing=True,
        acknowledged=True,
        order_id="GPA.9999-2222-3333-44444",
        obfuscated_account_id="opaque",
    )
    apply_verified_subscription(db_session, verified, user_id=user.id)
    with pytest.raises(GooglePlayVerificationError, match="another account"):
        apply_verified_subscription(db_session, verified, user_id=other.id)


def test_expiry_does_not_require_active_plan_and_cannot_revoke_newer_rail(db_session, tmp_path):
    user, _ = seed(db_session)
    token = "token-" + "c" * 50
    active = VerifiedSubscription(
        purchase_token=token,
        product_id="unlimited_access",
        base_plan_id="monthly",
        plan_tier="premium",
        duration_days=30,
        amount_usd=3.50,
        subscription_state="SUBSCRIPTION_STATE_ACTIVE",
        expiry_time=datetime.now(timezone.utc) + timedelta(days=30),
        auto_renewing=True,
        acknowledged=True,
        order_id="GPA.7777-2222-3333-44444",
        obfuscated_account_id="opaque",
    )
    apply_verified_subscription(db_session, active, user_id=user.id)

    plan = db_session.query(SubscriptionPlan).filter_by(tier="premium").one()
    plan.is_active = False
    db_session.commit()
    expired = VerifiedSubscription(
        **{
            **active.__dict__,
            "subscription_state": "SUBSCRIPTION_STATE_EXPIRED",
            "expiry_time": datetime.now(timezone.utc) - timedelta(minutes=1),
            "auto_renewing": False,
        }
    )
    apply_verified_subscription(db_session, expired, user_id=user.id)
    subscription = db_session.query(ClientPortalSubscription).filter_by(user_id=user.id).one()
    assert subscription.status == SubscriptionStatus.EXPIRED

    subscription.status = SubscriptionStatus.ACTIVE
    subscription.billing_source = "admin"
    subscription.billing_reference = "manual-extension"
    protected_expiry = datetime.now(timezone.utc) + timedelta(days=90)
    subscription.expiry_date = protected_expiry
    db_session.commit()
    apply_verified_subscription(db_session, expired, user_id=user.id)
    db_session.refresh(subscription)
    actual_expiry = subscription.expiry_date
    if actual_expiry.tzinfo is None:
        actual_expiry = actual_expiry.replace(tzinfo=timezone.utc)
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.billing_source == "admin"
    assert actual_expiry == protected_expiry


def test_rtdn_requires_matching_package_and_product(tmp_path):
    cfg = config(tmp_path)
    notification = {
        "packageName": cfg.package_name,
        "subscriptionNotification": {
            "subscriptionId": cfg.product_id,
            "purchaseToken": "t" * 64,
            "notificationType": 2,
        },
    }
    body = {
        "message": {
            "data": base64.b64encode(json.dumps(notification).encode()).decode(),
        }
    }
    assert decode_rtdn(body, cfg) == "t" * 64
    notification["packageName"] = "evil.example"
    body["message"]["data"] = base64.b64encode(json.dumps(notification).encode()).decode()
    with pytest.raises(GooglePlayVerificationError, match="package"):
        decode_rtdn(body, cfg)


@pytest.mark.asyncio
async def test_rtdn_invalid_oidc_token_is_rejected_cleanly(monkeypatch, tmp_path):
    cfg = config(tmp_path)

    def reject_token(*args, **kwargs):
        raise ValueError("bad signature")

    monkeypatch.setattr("google.oauth2.id_token.verify_oauth2_token", reject_token)
    with pytest.raises(GooglePlayVerificationError, match="Invalid Pub/Sub identity token"):
        await verify_pubsub_identity("Bearer forged-token", cfg)
