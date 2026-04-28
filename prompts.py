RECIPE_LIST_SYSTEM = """あなたは日本の家庭料理の専門家です。
ユーザーが持っている食材をもとに、誰でも作れるシンプルな料理を提案します。
以下のルールを厳守してください。
- 実際に日本の家庭で作られている既存の料理のみ提案する（創作料理・オリジナルレシピは禁止）
- 料理名はレシピサイトや料理本に載っているような一般的な名前にする
- 高級食材は使わず、スーパーで手に入る一般的な食材のみ使う
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
- 1番目：安心して作れる定番レシピ（slot: "standard", slot_label: "定番", mode: "with_buy"）
- 2番目：家庭料理の範囲で少し変化球のレシピ（slot: "creative", slot_label: "ちょいアレンジ", mode: "with_buy"）
  ※ 追加食材は1〜2品以内。奇抜すぎる創作・高級食材・難しい手順は禁止
  ※ 追加食材はあくまで補助。今ある食材が主役になること
- 3番目：今ある食材だけで作れるレシピ（slot: "no_buy", slot_label: "買い足しなし", mode: "no_buy"、additional_ingredients は空、additional_seasonings には使う主な調味料を入れる）

以下のJSON形式で返してください。

{{
  "recipes": [
    {{
      "title": "料理名",
      "slot": "standard",
      "slot_label": "定番",
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


RECIPE_FORMAT_SYSTEM = """あなたは日本の家庭料理の表示文面を整える専門家です。
以下を厳守してください。
- 1番目のslot=standardは、料理名を変更しない
- 2番目のslot=creativeは、家庭料理として成立する範囲で少しだけ変化球にしてよい
- creativeでも、奇抜すぎる創作・高級食材・手順が増える料理は禁止
- 3番目のslot=no_buyは、料理名を変更しない
- 渡された「slot」「slot_label」「mode」「additional_ingredients」「seasonings」は変更しない
- standard/no_buyでは辞書にない新しい料理名を作らない
- creativeで料理名を変える場合も、一般的な家庭料理として自然な名前に留める
- 説明文は1〜2文の自然な日本語にする
- 手順は3〜5ステップで初心者でも分かる表現にする
- 必ず有効なJSONのみを返す"""


def recipe_format_prompt(
    ingredients: str, family_size: int, candidates: list, nutrition_mode: str
) -> str:
    import json
    nutrition_instruction = {
        "normal": "",
        "healthy": "ヘルシーで低カロリーな観点で説明を添えてください。",
        "hearty": "ボリューム感を強調した説明にしてください。",
        "kids": "子供向けの優しい表現にしてください。",
        "high_protein": "高タンパクな点を説明に添えてください。",
        "diet": "低カロリーな点を説明に添えてください。",
    }.get(nutrition_mode, "")

    candidates_str = json.dumps(candidates, ensure_ascii=False, indent=2)
    return f"""ユーザーの食材：{ingredients}
人数：{family_size}人分
{nutrition_instruction}

以下の候補レシピを整形してください。
slotごとの役割：
- standard: 安心して作れる定番。料理名は変更禁止。
- creative: いつもと違う「ちょいアレンジ」。料理名は少し変えてよいが、元の料理から離れすぎない。
- no_buy: 今ある食材で詰まない現実解。料理名は変更禁止。

slot・slot_label・mode・additional_ingredients・seasonings は変更禁止です。
creativeでも additional_ingredients は増やさず、調味料・切り方・仕上げで変化を出してください。

{candidates_str}

以下のJSON形式で返してください：
{{
  "recipes": [
    {{
      "title": "料理名（creativeのみ少し変更可）",
      "slot": "standard / creative / no_buy（変更禁止）",
      "slot_label": "定番 / ちょいアレンジ / 買い足しなし（変更禁止）",
      "mode": "with_buy または no_buy（変更禁止）",
      "time_min": 所要時間（分・整数）,
      "cost_yen": 1人前の概算円（整数）,
      "description": "家庭料理らしい1〜2文の説明",
      "additional_ingredients": ["買い足す食材（変更禁止）"],
      "additional_seasonings": ["使う主な調味料（変更禁止）"],
      "image_prompt": "English dish description for image generation"
    }}
  ]
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
