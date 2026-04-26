import json
import re
from datetime import datetime, timezone
from linebot.v3.messaging import (
    FlexMessage, FlexCarousel, FlexBubble, FlexBox, FlexText, FlexButton,
    FlexImage, MessageAction,
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


def _recipe_bubble(recipe: dict, idx: int, family_size: int) -> FlexBubble:
    mode = recipe.get("mode", "no_buy")
    color = _BUBBLE_COLORS[idx]
    num_str = str(idx + 1)
    title = recipe.get("title", "レシピ")
    time_min = recipe.get("time_min", "?")
    cost = recipe.get("cost_yen", "?")
    desc = recipe.get("description", "")
    additional = recipe.get("additional_ingredients", recipe.get("additional_items", []))
    seasonings = recipe.get("additional_seasonings", [])
    image_url = recipe.get("image_url")
    total_cost = cost * family_size if isinstance(cost, int) else cost

    # 画像＋バッジオーバーレイ or カラーヘッダー
    if image_url:
        top_section = FlexBox(
            layout="vertical",
            contents=[
                FlexImage(url=image_url, size="full", aspect_ratio="20:13", aspect_mode="cover"),
                FlexBox(
                    layout="vertical",
                    position="absolute",
                    offset_top="8px",
                    offset_start="8px",
                    background_color=color,
                    corner_radius="16px",
                    width="32px",
                    height="32px",
                    contents=[
                        FlexText(text=num_str, color="#ffffff", weight="bold", size="sm",
                                 align="center", gravity="center")
                    ],
                ),
            ],
        )
        title_box = FlexText(text=title, weight="bold", size="md", wrap=True,
                             padding_start="12px", padding_end="12px", padding_top="10px")
    else:
        top_section = FlexBox(
            layout="vertical",
            background_color=color,
            padding_all="12px",
            contents=[
                FlexText(text=num_str, color="#ffffff", size="xxl", weight="bold"),
                FlexText(text=title, color="#ffffff", size="sm", weight="bold", wrap=True),
            ],
        )
        title_box = None

    # 買い足しラベル
    buy_label = "あり" if mode == "with_buy" else "なし"
    buy_color = "#E74C3C" if mode == "with_buy" else "#27AE60"
    subtitle = FlexBox(
        layout="horizontal",
        padding_start="12px",
        padding_end="12px",
        padding_top="10px",
        padding_bottom="6px",
        contents=[
            FlexText(text="買い足し ", size="xs", color="#888888", flex=0),
            FlexBox(
                layout="vertical",
                background_color=buy_color,
                corner_radius="4px",
                padding_start="5px",
                padding_end="5px",
                flex=0,
                contents=[FlexText(text=buy_label, color="#ffffff", size="xxs", weight="bold")],
            ),
            FlexText(text=" のおすすめレシピ", size="xs", color="#888888", flex=0),
        ],
    )

    body_contents = [subtitle, top_section]
    if title_box:
        body_contents.append(title_box)

    # 時間・コスト
    body_contents.append(
        FlexBox(
            layout="horizontal",
            padding_start="12px",
            padding_end="12px",
            padding_top="8px",
            contents=[
                FlexText(text=f"⏱ {time_min}分", size="sm", color="#555555", flex=1),
                FlexText(text=f"💰 約{total_cost}円/1人分", size="sm", color="#555555", flex=1),
            ],
        )
    )

    # 追加購入ボックス
    if mode == "with_buy" and (additional or seasonings):
        box_contents = [FlexText(text="追加で買うもの", size="xs", color="#888888", weight="bold")]
        if additional:
            box_contents.append(
                FlexText(text="　".join([f"・{a}" for a in additional]),
                         size="xs", color="#333333", wrap=True, margin="xs")
            )
        if seasonings:
            box_contents.append(FlexText(text="調味料", size="xs", color="#888888", weight="bold", margin="sm"))
            box_contents.append(
                FlexText(text="　".join([f"・{s}" for s in seasonings]),
                         size="xs", color="#333333", wrap=True, margin="xs")
            )
        body_contents.append(
            FlexBox(
                layout="vertical",
                background_color="#F5F5F5",
                corner_radius="6px",
                padding_all="8px",
                margin_start="12px",
                margin_end="12px",
                margin_top="8px",
                contents=box_contents,
            )
        )

    # 説明
    if desc:
        body_contents.append(
            FlexText(text=desc, size="xs", color="#888888", wrap=True,
                     padding_start="12px", padding_end="12px", padding_top="6px", padding_bottom="8px")
        )

    return FlexBubble(
        size="kilo",
        body=FlexBox(layout="vertical", padding_all="0px", contents=body_contents),
        footer=FlexBox(
            layout="vertical",
            padding_all="12px",
            contents=[
                FlexButton(
                    action=MessageAction(label="詳しく見る", text=num_str),
                    style="primary",
                    color=color,
                    height="sm",
                )
            ],
        ),
    )


def build_detail_flex(detail: dict, family_size: int, image_url: str | None) -> FlexMessage:
    title = detail.get("title", "レシピ")
    ingredients = detail.get("ingredients", [])
    steps = detail.get("steps", [])
    tips = detail.get("tips", "")
    storage = detail.get("storage", "")
    next_day = detail.get("next_day_arrange", "")

    body_contents = []

    # タイトル
    body_contents.append(
        FlexText(text=f"【{title}】（{family_size}人分）", weight="bold", size="md",
                 wrap=True, padding_bottom="8px")
    )

    # 材料
    body_contents.append(FlexText(text="■ 材料", weight="bold", size="sm", color="#333333"))
    for ing in ingredients:
        body_contents.append(FlexText(text=f"・{ing}", size="sm", color="#555555", wrap=True))

    # 作り方
    body_contents.append(
        FlexText(text="■ 作り方", weight="bold", size="sm", color="#333333", margin="md")
    )
    for i, step in enumerate(steps, 1):
        body_contents.append(FlexText(text=f"{i}. {step}", size="sm", color="#555555", wrap=True))

    # コツ・保存・翌日アレンジ
    for icon, val in [("💡 コツ", tips), ("🗃 保存", storage), ("🔄 翌日アレンジ", next_day)]:
        if val:
            body_contents.append(
                FlexText(text=f"{icon}：{val}", size="xs", color="#888888", wrap=True, margin="sm")
            )

    hero = FlexImage(
        url=image_url, size="full", aspect_ratio="20:13", aspect_mode="cover"
    ) if image_url else None

    return FlexMessage(
        alt_text=f"{title}の詳細レシピ",
        contents=FlexBubble(
            hero=hero,
            body=FlexBox(layout="vertical", spacing="sm", contents=body_contents),
        ),
    )


def build_recipes_flex(recipes: list, family_size: int) -> FlexMessage:
    bubbles = [_recipe_bubble(r, i, family_size) for i, r in enumerate(recipes[:3])]
    return FlexMessage(
        alt_text="レシピ3案をご提案します",
        contents=FlexCarousel(contents=bubbles),
    )


def normalize_ingredients(text: str) -> str:
    items = re.split(r"[、,，\s]+", text.strip())
    items = [i.strip().lower() for i in items if i.strip()]
    return "、".join(sorted(set(items)))


def jaccard_similarity(a: str, b: str) -> float:
    set_a = set(re.split(r"[、,，\s]+", a.lower()))
    set_b = set(re.split(r"[、,，\s]+", b.lower()))
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


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
