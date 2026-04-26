import re
from openai import OpenAI
import config
import prompts
from utils import parse_json_safe

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def _chat(system: str, user: str, retries: int = 2) -> dict | None:
    for attempt in range(retries + 1):
        try:
            res = get_client().chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
            )
            text = res.choices[0].message.content or ""
            data = parse_json_safe(text)
            if data is not None:
                return data
            print(f"[recipe_generator] JSON parse failed (attempt {attempt}): {text[:200]}")
        except Exception as e:
            print(f"[recipe_generator] API error (attempt {attempt}): {e}")
    return None


def generate_recipes(
    ingredients: str,
    mode: str,
    family_size: int,
    nutrition_mode: str,
) -> list | None:
    """レシピ一覧3案を生成して返す。"""
    # 余り物っぽいキーワードを検出してプロンプトを切り替える
    leftover_keywords = ["余", "残", "昨日", "アレンジ"]
    is_leftover = any(kw in ingredients for kw in leftover_keywords)

    if is_leftover:
        data = _chat(prompts.LEFTOVER_SYSTEM, prompts.leftover_prompt(ingredients, family_size))
    else:
        data = _chat(
            prompts.RECIPE_LIST_SYSTEM,
            prompts.recipe_list_prompt(ingredients, mode, family_size, nutrition_mode),
        )
    if data is None:
        return None
    return data.get("recipes", [])


def generate_recipe_detail(title: str, ingredients_hint: str, family_size: int) -> dict | None:
    """レシピ詳細を生成して返す。"""
    data = _chat(
        prompts.RECIPE_DETAIL_SYSTEM,
        prompts.recipe_detail_prompt(title, ingredients_hint, family_size),
    )
    return data


def generate_shopping_list(context: str) -> list | None:
    """買い物リストを生成して返す。"""
    data = _chat(prompts.SHOPPING_LIST_SYSTEM, prompts.shopping_list_prompt(context))
    if data is None:
        return None
    return data.get("items", [])
