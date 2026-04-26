import json
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import config

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
    return _client


# ── users ──────────────────────────────────────────────────────────────────

def get_user(user_id: str) -> dict | None:
    res = get_client().table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None


def create_user(user_id: str, display_name: str) -> dict:
    now = datetime.now(timezone.utc)
    trial_end = now + timedelta(days=7)
    row = {
        "user_id": user_id,
        "display_name": display_name,
        "plan": "trial",
        "mode": "no_buy",
        "family_size": 1,
        "nutrition_mode": "normal",
        "trial_started_at": now.isoformat(),
        "trial_end_at": trial_end.isoformat(),
    }
    res = get_client().table("users").insert(row).execute()
    return res.data[0]


def upsert_user_field(user_id: str, fields: dict) -> None:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    get_client().table("users").update(fields).eq("user_id", user_id).execute()


def get_or_create_user(user_id: str, display_name: str) -> dict:
    user = get_user(user_id)
    if user is None:
        user = create_user(user_id, display_name)
    return user


def is_active(user: dict) -> bool:
    """trialまたはpaid かつ期限内かどうかを返す。"""
    plan = user.get("plan", "free_expired")
    if plan == "paid":
        return True
    if plan == "trial":
        end_at_raw = user.get("trial_end_at")
        if end_at_raw:
            end_at = datetime.fromisoformat(end_at_raw)
            if end_at.tzinfo is None:
                end_at = end_at.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) <= end_at:
                return True
        # 期限切れ → plan を更新
        upsert_user_field(user["user_id"], {"plan": "free_expired"})
        return False
    return False


# ── pending_ingredients ────────────────────────────────────────────────────

def save_pending_ingredients(user_id: str, ingredients: list, source: str) -> None:
    row = {
        "user_id": user_id,
        "ingredients_json": ingredients,
        "source": source,
    }
    get_client().table("pending_ingredients").upsert(row, on_conflict="user_id").execute()


def get_pending_ingredients(user_id: str) -> dict | None:
    res = get_client().table("pending_ingredients").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None


def delete_pending_ingredients(user_id: str) -> None:
    get_client().table("pending_ingredients").delete().eq("user_id", user_id).execute()


# ── recipe_contexts ────────────────────────────────────────────────────────

def save_recipe_context(user_id: str, recipes: list) -> None:
    row = {"user_id": user_id, "recipes_json": recipes}
    get_client().table("recipe_contexts").insert(row).execute()


def get_latest_recipe_context(user_id: str) -> dict | None:
    res = (
        get_client()
        .table("recipe_contexts")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return res.data[0] if res.data else None


# ── saved_recipes ──────────────────────────────────────────────────────────

def save_recipe(user_id: str, recipe: dict) -> None:
    get_client().table("saved_recipes").insert({"user_id": user_id, "recipe_json": recipe}).execute()


def get_saved_recipes(user_id: str, limit: int = 10) -> list:
    res = (
        get_client()
        .table("saved_recipes")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


# ── usage_logs ─────────────────────────────────────────────────────────────

def log_action(user_id: str, action: str, metadata: dict | None = None) -> None:
    try:
        get_client().table("usage_logs").insert({
            "user_id": user_id,
            "action": action,
            "metadata": metadata or {},
        }).execute()
    except Exception as e:
        print(f"[log_action error] {e}")


# ── Stripe ─────────────────────────────────────────────────────────────────

def get_user_by_stripe_customer(customer_id: str) -> dict | None:
    res = get_client().table("users").select("*").eq("stripe_customer_id", customer_id).execute()
    return res.data[0] if res.data else None


def get_user_by_stripe_subscription(subscription_id: str) -> dict | None:
    res = get_client().table("users").select("*").eq("stripe_subscription_id", subscription_id).execute()
    return res.data[0] if res.data else None
