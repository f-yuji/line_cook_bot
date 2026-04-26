import json
import re
from datetime import datetime, timezone
from linebot.v3.messaging import (
    FlexMessage, FlexCarousel, FlexBubble, FlexBox, FlexText, FlexButton,
    MessageAction,
)


def now_jst() -> datetime:
    from datetime import timedelta
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9)))


def parse_json_safe(text: str) -> dict | None:
    """JSON文字列をパースする。マークダウンコードブロックも除去する。"""
    text = text.strip()
    # ```json ... ``` ブロックを除去
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 最初の { から最後の } を切り出して再試行
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
    return None


def format_recipes_message(recipes: list, mode: str, family_size: int) -> str:
    """レシピ一覧を LINE 返信テキストに整形する。"""
    lines = []
    buy_label = "買い足しあり" if mode == "with_buy" else "買い足しなし"
    lines.append(f"買い足し【{buy_label}】で作れるレシピ\n")
    for i, r in enumerate(recipes, 1):
        title = r.get("title", "レシピ")
        time_min = r.get("time_min", "?")
        cost = r.get("cost_yen", "?")
        desc = r.get("description", "")
        additional = r.get("additional_items", [])
        lines.append(f"{'①②③'[i-1]} {title}")
        lines.append(f"　調理時間：{time_min}分　概算：{cost * family_size if isinstance(cost, int) else cost}円")
        if desc:
            lines.append(f"　{desc}")
        if additional and mode == "with_buy":
            lines.append(f"　追加：{' / '.join(additional)}")
    lines.append("\n番号を送ると詳しく見れます。\n例：1 / 2詳しく")
    return "\n".join(lines)


def format_detail_message(detail: dict, family_size: int) -> str:
    """詳細レシピを LINE 返信テキストに整形する。"""
    title = detail.get("title", "レシピ")
    ingredients = detail.get("ingredients", [])
    steps = detail.get("steps", [])
    tips = detail.get("tips", "")
    storage = detail.get("storage", "")
    next_day = detail.get("next_day_arrange", "")

    lines = [f"【{title}】（{family_size}人分）\n"]
    lines.append("■ 材料")
    for ing in ingredients:
        lines.append(f"・{ing}")
    lines.append("\n■ 作り方")
    for j, step in enumerate(steps, 1):
        lines.append(f"{j}. {step}")
    if tips:
        lines.append(f"\n💡 コツ：{tips}")
    if storage:
        lines.append(f"🗃 保存：{storage}")
    if next_day:
        lines.append(f"🔄 翌日アレンジ：{next_day}")
    return "\n".join(lines)


def format_shopping_list_message(items: list) -> str:
    lines = ["【買い物リスト】\n"]
    for item in items:
        lines.append(f"・{item}")
    return "\n".join(lines)


_BUBBLE_COLORS = ["#FF6B35", "#4ECDC4", "#45B7D1"]
_NUMBERS = ["①", "②", "③"]


def _recipe_bubble(recipe: dict, idx: int, mode: str, family_size: int) -> FlexBubble:
    color = _BUBBLE_COLORS[idx]
    num = _NUMBERS[idx]
    title = recipe.get("title", "レシピ")
    time_min = recipe.get("time_min", "?")
    cost = recipe.get("cost_yen", "?")
    desc = recipe.get("description", "")
    additional = recipe.get("additional_items", [])
    total_cost = cost * family_size if isinstance(cost, int) else cost

    body_contents = [
        FlexBox(
            layout="horizontal",
            margin="sm",
            contents=[
                FlexText(text=f"⏱ {time_min}分", size="sm", color="#555555", flex=1),
                FlexText(text=f"💰 約{total_cost}円/人", size="sm", color="#555555", flex=1),
            ],
        )
    ]
    if desc:
        body_contents.append(
            FlexText(text=desc, size="xs", color="#888888", wrap=True, margin="sm")
        )
    if additional and mode == "with_buy":
        body_contents.append(
            FlexText(
                text="買い足し：" + "・".join(additional),
                size="xs", color="#E74C3C", wrap=True, margin="sm",
            )
        )

    return FlexBubble(
        header=FlexBox(
            layout="vertical",
            background_color=color,
            padding_all="12px",
            contents=[
                FlexText(text=num, color="#ffffff", size="xxl", weight="bold"),
                FlexText(text=title, color="#ffffff", size="sm", weight="bold", wrap=True),
            ],
        ),
        body=FlexBox(layout="vertical", contents=body_contents),
        footer=FlexBox(
            layout="vertical",
            contents=[
                FlexButton(
                    action=MessageAction(label="詳しく見る", text=str(idx + 1)),
                    style="primary",
                    color=color,
                    height="sm",
                )
            ],
        ),
    )


def build_recipes_flex(recipes: list, mode: str, family_size: int) -> FlexMessage:
    buy_label = "買い足しあり" if mode == "with_buy" else "買い足しなし"
    bubbles = [_recipe_bubble(r, i, mode, family_size) for i, r in enumerate(recipes[:3])]
    return FlexMessage(
        alt_text=f"買い足し【{buy_label}】レシピ3案",
        contents=FlexCarousel(contents=bubbles),
    )


def extract_number_from_text(text: str) -> int | None:
    """'1', '2詳しく', '①' などから番号を抽出する。"""
    text = text.strip()
    mapping = {"①": 1, "②": 2, "③": 3, "一": 1, "二": 2, "三": 3}
    for k, v in mapping.items():
        if k in text:
            return v
    m = re.search(r"[1-3１-３]", text)
    if m:
        c = m.group()
        if c in "１２３":
            return "１２３".index(c) + 1
        return int(c)
    return None
