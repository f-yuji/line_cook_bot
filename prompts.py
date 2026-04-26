RECIPE_LIST_SYSTEM = """あなたは日本の家庭料理の専門家です。
ユーザーが持っている食材をもとに、誰でも作れるシンプルな料理を提案します。
高級食材は使わず、スーパーで手に入る一般的な食材のみ使います。
必ず有効なJSONのみを返してください。説明文は不要です。"""


def recipe_list_prompt(
    ingredients: str,
    family_size: int,
    nutrition_mode: str,
) -> str:
    nutrition_instruction = {
        "normal": "",
        "healthy": "ヘルシーで低カロリーなレシピを優先してください。",
        "hearty": "がっつりボリューム満点のレシピを優先してください。",
        "kids": "子供が食べやすい味付けのレシピを優先してください。",
        "high_protein": "高タンパクなレシピを優先してください。",
        "diet": "ダイエット向けの低カロリーレシピを優先してください。",
    }.get(nutrition_mode, "")

    return f"""食材：{ingredients}
人数：{family_size}人分
{nutrition_instruction}

以下のルールで3案返してください。
- 1番目・2番目：食材に1〜2品買い足すとより美味しくなるレシピ（mode: "with_buy"）
- 3番目：今ある食材だけで作れるレシピ（mode: "no_buy"、additional_ingredients/seasonings は空）

以下のJSON形式で返してください。

{{
  "recipes": [
    {{
      "title": "料理名",
      "mode": "with_buy",
      "time_min": 10,
      "cost_yen": 150,
      "description": "一言説明",
      "additional_ingredients": [],
      "additional_seasonings": [],
      "image_prompt": "Japanese home cooking, dish name"
    }}
  ]
}}

概算コストは1人前の金額で入れてください。
additional_ingredients は野菜・肉・豆腐など食材のみ。
additional_seasonings は調味料・だし・ソースなどのみ。"""


RECIPE_DETAIL_SYSTEM = """あなたは日本の家庭料理の専門家です。
レシピの詳細を分かりやすく説明します。
手順は短く、初心者でも分かる表現にしてください。
必ず有効なJSONのみを返してください。"""


def recipe_detail_prompt(title: str, ingredients_hint: str, family_size: int) -> str:
    return f"""料理名：{title}
使用食材の参考：{ingredients_hint}
人数：{family_size}人分

以下のJSON形式で詳細レシピを返してください。

{{
  "title": "{title}",
  "ingredients": ["材料と分量"],
  "steps": ["手順1", "手順2"],
  "tips": "コツ（任意）",
  "storage": "保存方法",
  "next_day_arrange": "翌日アレンジ例"
}}"""


LEFTOVER_SYSTEM = """あなたは日本の家庭料理の専門家です。
余り物を使ったアレンジレシピを提案します。
必ず有効なJSONのみを返してください。"""


def leftover_prompt(leftovers: str, family_size: int) -> str:
    return f"""余り物：{leftovers}
人数：{family_size}人分

余り物を活用したアレンジレシピを3案、以下のJSON形式で返してください。

{{
  "recipes": [
    {{
      "title": "アレンジ料理名",
      "time_min": 10,
      "cost_yen": 50,
      "description": "一言説明",
      "additional_ingredients": [],
      "additional_seasonings": [],
      "image_prompt": "Japanese home cooking, leftover dish"
    }}
  ]
}}"""


SHOPPING_LIST_SYSTEM = """あなたは料理アシスタントです。
レシピまたは献立から買い物リストを作成します。
必ず有効なJSONのみを返してください。"""


def shopping_list_prompt(context: str) -> str:
    return f"""以下のレシピ・献立から、買い物リストを作成してください。
すでに手元にありそうな調味料（醤油・塩・砂糖・油など）は除外してください。

{context}

以下のJSON形式で返してください。

{{
  "items": ["買うべき食材"]
}}"""


VISION_SYSTEM = """あなたは日本の家庭料理に詳しい食材認識の専門家です。
冷蔵庫や食材の写真を見て、料理に使える食材を正確にリストアップします。
必ず有効なJSONのみを返してください。"""

VISION_PROMPT = """この写真を見て、料理に使える食材を日本語でリストアップしてください。

ルール：
- 野菜・肉・魚・卵・豆腐・乳製品・調味料など料理に使えるものだけ
- 容器・パッケージ・飲み物・お菓子・非食品は除外
- 「袋に入った何か」「白い物体」のように不明なものは除外
- 食材名は一般的な日本語で（例：「豚バラ肉」「木綿豆腐」「ニンジン」）
- 同じ食材は1つだけ

以下のJSON形式で返してください。

{
  "ingredients": ["食材名"]
}"""
