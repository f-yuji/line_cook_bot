"""
LINEメッセージハンドラ。
テキスト・画像それぞれのユーザー入力を解釈し、適切な処理を呼び出す。
"""
import re
import config
import db
import recipe_generator
import vision_analyzer
import image_generator
import billing
from utils import (
    format_recipes_message,
    format_detail_message,
    format_shopping_list_message,
    extract_number_from_text,
    build_recipes_flex,
)
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction,
    FlexMessage,
    FlexBubble,
    FlexBox,
    FlexText,
    FlexButton,
    FlexSeparator,
)

# ── LINE API クライアント ─────────────────────────────────────────────────

def _get_line_api() -> MessagingApi:
    cfg = Configuration(access_token=config.LINE_CHANNEL_ACCESS_TOKEN)
    return MessagingApi(ApiClient(cfg))


def _quick_reply() -> QuickReply:
    items = [
        QuickReplyItem(action=MessageAction(label="買い足しなし", text="買い足しなし")),
        QuickReplyItem(action=MessageAction(label="買い足しあり", text="買い足しあり")),
        QuickReplyItem(action=MessageAction(label="買い物リスト", text="買い物リスト")),
        QuickReplyItem(action=MessageAction(label="保存リスト", text="保存リスト")),
        QuickReplyItem(action=MessageAction(label="保存", text="保存")),
        QuickReplyItem(action=MessageAction(label="使い方", text="使い方")),
    ]
    return QuickReply(items=items)


def _reply(reply_token: str, text: str) -> None:
    api = _get_line_api()
    msg = TextMessage(text=text, quick_reply=_quick_reply())
    api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=[msg]))


def _reply_flex(reply_token: str, recipes: list, mode: str, family_size: int) -> None:
    api = _get_line_api()
    msg = build_recipes_flex(recipes, mode, family_size)
    msg.quick_reply = _quick_reply()
    api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=[msg]))


def _reply_multi(reply_token: str, texts: list[str]) -> None:
    """最大5件のテキストメッセージを返信する。"""
    api = _get_line_api()
    messages = []
    for i, t in enumerate(texts[:5]):
        qr = _quick_reply() if i == len(texts) - 1 else None
        messages.append(TextMessage(text=t, quick_reply=qr))
    api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=messages))


# ── アクセス制御 ────────────────────────────────────────────────────────────

def _check_active_and_reply(user: dict, reply_token: str) -> bool:
    """非アクティブなら課金案内を送り True を返す。アクティブなら False を返す。"""
    if db.is_active(user):
        return False
    url = billing.create_checkout_session(user["user_id"])
    if url:
        msg = f"無料期間は終了しました。\n続ける場合はこちらから登録してください。\n\n{url}"
    else:
        msg = "無料期間は終了しました。決済ページを作成できませんでした。時間をおいて再度お試しください。"
    _reply(reply_token, msg)
    return True


# ── メインルーター ───────────────────────────────────────────────────────────

def handle_text_message(user_id: str, display_name: str, reply_token: str, text: str) -> None:
    user = db.get_or_create_user(user_id, display_name)
    text_s = text.strip()

    # ── モード・設定系コマンド（課金不要） ──
    if _handle_settings(user, reply_token, text_s):
        return

    # ── 使い方 ──
    if text_s in ("使い方", "ヘルプ", "help"):
        _reply(reply_token, _usage_text())
        return

    # ── 課金チェック ──
    if _check_active_and_reply(user, reply_token):
        return

    # ── 保存リスト選択フロー ──
    pending = db.get_pending_ingredients(user_id)
    if pending and pending.get("source") == "saved_list":
        num = extract_number_from_text(text_s)
        saved = pending["ingredients_json"]  # [{id, title}, ...]
        if num and 1 <= num <= len(saved):
            db.delete_pending_ingredients(user_id)
            _handle_saved_detail(user, reply_token, saved[num - 1]["title"])
            return
        # 料理名で検索
        matched = next((s for s in saved if s["title"] in text_s or text_s in s["title"]), None)
        if matched:
            db.delete_pending_ingredients(user_id)
            _handle_saved_detail(user, reply_token, matched["title"])
            return

    # ── 写真確認フロー（pending） ──
    if pending is None:
        pending = db.get_pending_ingredients(user_id)
    if pending and pending.get("source") == "awaiting_confirm":
        if text_s in ("この内容で提案", "はい", "yes", "OK", "ok", "提案"):
            _propose_from_pending(user, reply_token)
            return
        elif text_s in ("食材を修正する", "修正"):
            db.save_pending_ingredients(user_id, pending["ingredients_json"], "awaiting_edit")
            _reply(reply_token, "修正した食材を送ってください。\n例：卵、キャベツ、ネギ、豆腐")
            return

    if pending and pending.get("source") == "awaiting_edit":
        ingredients = [i.strip() for i in re.split(r"[、,，\s]+", text_s) if i.strip()]
        db.save_pending_ingredients(user_id, ingredients, "awaiting_confirm")
        _reply(
            reply_token,
            f"修正しました。\n\n{chr(10).join('・' + i for i in ingredients)}\n\nこの内容で提案しますか？",
        )
        return

    # ── 機能系コマンド ──
    if text_s == "買い足しなし":
        db.upsert_user_field(user_id, {"mode": "no_buy"})
        _reply(reply_token, "買い足しなしに変更しました。")
        return

    if text_s == "買い足しあり":
        db.upsert_user_field(user_id, {"mode": "with_buy"})
        _reply(reply_token, "買い足しありに変更しました。")
        return

    if text_s == "買い物リスト":
        _handle_shopping_list(user, reply_token)
        return

    if text_s == "保存リスト":
        _handle_saved_list(user, reply_token)
        return

    if text_s in ("保存", "保存する") or re.match(r"^[1-3①②③]保存", text_s):
        _handle_save(user, reply_token, text_s)
        return

    # ── 詳細表示（番号） ──
    num = extract_number_from_text(text_s)
    if num and re.search(r"(詳しく|詳細|[1-3①②③])", text_s):
        _handle_detail(user, reply_token, num)
        return
    # 数字のみ送信でも詳細を返す
    if re.fullmatch(r"[1-3１-３①②③]", text_s):
        if num:
            _handle_detail(user, reply_token, num)
            return

    # ── 食材入力 → レシピ生成 ──
    _handle_ingredient_text(user, reply_token, text_s)


def handle_image_message(user_id: str, display_name: str, reply_token: str, message_id: str) -> None:
    user = db.get_or_create_user(user_id, display_name)

    if _check_active_and_reply(user, reply_token):
        return

    image_bytes = vision_analyzer.fetch_line_image(message_id, config.LINE_CHANNEL_ACCESS_TOKEN)
    if image_bytes is None:
        _reply(reply_token, "写真を取得できませんでした。\n食材名を文字で送ってください。")
        return

    ingredients = vision_analyzer.analyze_ingredients_from_image(image_bytes)
    if not ingredients:
        _reply(reply_token, "写真から食材を読み取れませんでした。\n食材名を文字で送ってください。")
        db.log_action(user_id, "vision_failed")
        return

    db.save_pending_ingredients(user_id, ingredients, "awaiting_confirm")
    db.log_action(user_id, "vision_success", {"count": len(ingredients)})

    api = _get_line_api()
    msg = _build_confirm_flex(ingredients)
    api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=[msg]))


def _build_confirm_flex(ingredients: list) -> FlexMessage:
    ing_texts = [FlexText(text=f"・{i}", size="sm", color="#333333") for i in ingredients]
    return FlexMessage(
        alt_text="食材を確認してください",
        contents=FlexBubble(
            header=FlexBox(
                layout="vertical",
                background_color="#27AE60",
                padding_all="12px",
                contents=[
                    FlexText(text="📷 見つけた食材", color="#ffffff", weight="bold", size="md"),
                ],
            ),
            body=FlexBox(
                layout="vertical",
                spacing="sm",
                contents=ing_texts,
            ),
            footer=FlexBox(
                layout="vertical",
                spacing="sm",
                contents=[
                    FlexButton(
                        action=MessageAction(label="この内容で提案する", text="この内容で提案"),
                        style="primary",
                        color="#27AE60",
                    ),
                    FlexButton(
                        action=MessageAction(label="食材を修正する", text="食材を修正する"),
                        style="secondary",
                    ),
                ],
            ),
        ),
    )


# ── 内部ハンドラ ─────────────────────────────────────────────────────────────

def _handle_settings(user: dict, reply_token: str, text: str) -> bool:
    """設定系コマンドを処理。処理した場合 True を返す。"""
    user_id = user["user_id"]

    # 人数設定
    m = re.search(r"(?:人数|家族)\s*[はを]?\s*([0-9１-９]+)\s*人?", text)
    if m:
        n = int(m.group(1).translate(str.maketrans("１２３４５６７８９０", "1234567890")))
        db.upsert_user_field(user_id, {"family_size": n})
        _reply(reply_token, f"人数を{n}人に設定しました。")
        return True

    # 栄養モード
    mode_map = {
        "普通": "normal",
        "ヘルシー": "healthy",
        "がっつり": "hearty",
        "子供向け": "kids",
        "高タンパク": "high_protein",
        "ダイエット": "diet",
    }
    for label, mode in mode_map.items():
        if label in text:
            db.upsert_user_field(user_id, {"nutrition_mode": mode})
            _reply(reply_token, f"モードを{label}に変更しました。")
            return True

    return False


def _handle_ingredient_text(user: dict, reply_token: str, text: str) -> None:
    user_id = user["user_id"]
    recipes = recipe_generator.generate_recipes(
        text,
        user.get("mode", "no_buy"),
        user.get("family_size", 1),
        user.get("nutrition_mode", "normal"),
    )
    if not recipes:
        _reply(reply_token, "すみません、うまく作れませんでした。\n食材をもう一度送ってください。")
        db.log_action(user_id, "recipe_failed", {"input": text[:100]})
        return

    db.save_recipe_context(user_id, recipes)
    db.log_action(user_id, "recipe_generated", {"count": len(recipes)})
    _reply_flex(reply_token, recipes, user.get("mode", "no_buy"), user.get("family_size", 1))


def _propose_from_pending(user: dict, reply_token: str) -> None:
    user_id = user["user_id"]
    pending = db.get_pending_ingredients(user_id)
    if not pending:
        _reply(reply_token, "食材情報が見つかりません。\n食材名を送ってください。")
        return
    ingredients_str = "、".join(pending["ingredients_json"])
    db.delete_pending_ingredients(user_id)
    _handle_ingredient_text(user, reply_token, ingredients_str)


def _handle_detail(user: dict, reply_token: str, num: int) -> None:
    user_id = user["user_id"]
    ctx = db.get_latest_recipe_context(user_id)
    if not ctx:
        _reply(reply_token, "レシピが見つかりません。\n食材を送ってください。")
        return

    recipes = ctx["recipes_json"]
    if num < 1 or num > len(recipes):
        _reply(reply_token, f"1〜{len(recipes)}の番号を送ってください。")
        return

    recipe = recipes[num - 1]
    title = recipe.get("title", "")
    # 食材ヒントとして additional_items も含める
    ingredients_hint = ", ".join(recipe.get("additional_items", []))

    detail = recipe_generator.generate_recipe_detail(title, ingredients_hint, user.get("family_size", 1))
    if not detail:
        _reply(reply_token, "すみません、詳細を取得できませんでした。\nもう一度試してください。")
        return

    db.log_action(user_id, "detail_viewed", {"title": title})
    detail_text = format_detail_message(detail, user.get("family_size", 1))

    # 画像生成が有効なら画像URLも添付
    image_prompt = recipe.get("image_prompt", title)
    image_url = image_generator.generate_dish_image(image_prompt)

    if image_url:
        _reply_multi(reply_token, [detail_text, f"完成イメージ：\n{image_url}"])
    else:
        _reply(reply_token, detail_text)


def _handle_save(user: dict, reply_token: str, text: str) -> None:
    user_id = user["user_id"]
    ctx = db.get_latest_recipe_context(user_id)
    if not ctx:
        _reply(reply_token, "保存できるレシピが見つかりません。")
        return

    recipes = ctx["recipes_json"]
    num = extract_number_from_text(text)
    if num and 1 <= num <= len(recipes):
        db.save_recipe(user_id, recipes[num - 1])
    else:
        for r in recipes:
            db.save_recipe(user_id, r)

    db.log_action(user_id, "recipe_saved")
    _reply(reply_token, "保存しました。")


def _handle_saved_list(user: dict, reply_token: str) -> None:
    user_id = user["user_id"]
    rows = db.get_saved_recipes(user_id)
    if not rows:
        _reply(reply_token, "保存済みのレシピはありません。\nレシピを見たあと「保存」と送ると保存できます。")
        return

    lines = ["【保存済みレシピ】\n"]
    index = []
    for i, row in enumerate(rows, 1):
        title = row["recipe_json"].get("title", "不明")
        lines.append(f"{i}. {title}")
        index.append({"title": title})

    lines.append("\n番号または料理名を送ると詳細を表示します。")
    db.save_pending_ingredients(user_id, index, "saved_list")
    _reply(reply_token, "\n".join(lines))


def _handle_saved_detail(user: dict, reply_token: str, title: str) -> None:
    detail = recipe_generator.generate_recipe_detail(title, "", user.get("family_size", 1))
    if not detail:
        _reply(reply_token, "詳細を取得できませんでした。もう一度試してください。")
        return
    db.log_action(user["user_id"], "saved_detail_viewed", {"title": title})
    _reply(reply_token, format_detail_message(detail, user.get("family_size", 1)))


def _handle_shopping_list(user: dict, reply_token: str) -> None:
    user_id = user["user_id"]

    # 直近レシピまたは週間献立からコンテキストを作る
    ctx = db.get_latest_recipe_context(user_id)

    context_parts = []
    if ctx:
        for r in ctx["recipes_json"]:
            context_parts.append(r.get("title", ""))

    if not context_parts:
        _reply(reply_token, "レシピか献立が見つかりません。\n先に食材を送ってください。")
        return

    context_str = "\n".join(context_parts)
    items = recipe_generator.generate_shopping_list(context_str)
    if not items:
        _reply(reply_token, "すみません、リストを生成できませんでした。\nもう一度試してください。")
        return

    db.log_action(user_id, "shopping_list_generated")
    _reply(reply_token, format_shopping_list_message(items))


def _usage_text() -> str:
    return (
        "【使い方】\n\n"
        "▶ 食材を送る\n"
        "例：卵、キャベツ、豚こま\n\n"
        "▶ 冷蔵庫の写真を送る\n"
        "食材を自動で認識します。\n\n"
        "▶ 番号で詳細確認\n"
        "例：1 / 2詳しく\n\n"
        "▶ 買い足しあり/なしを切り替え\n"
        "クイックリプライで選べます。\n\n"
        "▶ その他\n"
        "買い物リスト・保存\n"
        "人数 3人 → 人数設定\n"
        "ヘルシー / ダイエット → モード変更"
    )
