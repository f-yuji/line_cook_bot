import stripe
import config
import db

stripe.api_key = config.STRIPE_SECRET_KEY


def create_checkout_session(user_id: str) -> str | None:
    """Stripe Checkout URLを作成して返す。"""
    try:
        user = db.get_user(user_id)
        customer_id = user.get("stripe_customer_id") if user else None

        params: dict = {
            "mode": "subscription",
            "line_items": [{"price": config.STRIPE_PRICE_ID, "quantity": 1}],
            "success_url": f"{config.APP_BASE_URL}/stripe/success?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{config.APP_BASE_URL}/stripe/cancel",
            "metadata": {"user_id": user_id},
            "allow_promotion_codes": True,
        }
        if customer_id:
            params["customer"] = customer_id
        else:
            params["client_reference_id"] = user_id

        session = stripe.checkout.Session.create(**params)
        return session.url
    except Exception as e:
        print(f"[billing] create_checkout_session error: {e}")
        return None


def handle_stripe_webhook(payload: bytes, sig_header: str) -> tuple[bool, str]:
    """
    Stripe Webhookを処理する。
    戻り値: (成功フラグ, メッセージ)
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.STRIPE_WEBHOOK_SECRET
        )
    except stripe.errors.SignatureVerificationError as e:
        print(f"[billing] webhook signature error: {e}")
        return False, "invalid signature"
    except Exception as e:
        print(f"[billing] webhook parse error: {e}")
        return False, "parse error"

    event_type = event["type"]
    print(f"[billing] webhook event: {event_type}")

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id") or session.get("client_reference_id")
        if not user_id:
            return True, "no user_id"
        customer_id = session.get("customer")
        subscription_id = session.get("subscription")
        db.upsert_user_field(user_id, {
            "plan": "paid",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
        })
        print(f"[billing] user {user_id} upgraded to paid")

    elif event_type in ("customer.subscription.deleted", "customer.subscription.canceled"):
        sub = event["data"]["object"]
        subscription_id = sub.get("id")
        if subscription_id:
            user = db.get_user_by_stripe_subscription(subscription_id)
            if user:
                db.upsert_user_field(user["user_id"], {"plan": "free_expired"})
                print(f"[billing] user {user['user_id']} downgraded to free_expired")

    elif event_type == "invoice.payment_failed":
        invoice = event["data"]["object"]
        customer_id = invoice.get("customer")
        if customer_id:
            user = db.get_user_by_stripe_customer(customer_id)
            if user:
                print(f"[billing] payment failed for user {user['user_id']}")

    return True, "ok"
