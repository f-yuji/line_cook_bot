from services.recipe_dictionary import (
    get_recipes, get_compatibility_score, normalize_ingredients_list,
    get_image_prompt_for_recipe,
)

_COMMON_SEASONINGS = {
    "醤油", "塩", "こしょう", "塩こしょう", "砂糖", "みりん", "酒", "めんつゆ",
    "だし", "鶏ガラ", "ごま油", "マヨネーズ", "ケチャップ", "味噌",
    "サラダ油", "オリーブオイル", "バター", "酢", "からし", "片栗粉", "コンソメ",
}


def _score_recipe(recipe: dict, user_ingredients: set[str]) -> float:
    score = 0.0
    must_have = set(recipe.get("must_have", []))
    nice_to_have = set(recipe.get("nice_to_have", []))
    avoid_with = set(recipe.get("avoid_with", []))
    buy_optional = set(recipe.get("buy_optional", []))

    for bad in avoid_with:
        if bad in user_ingredients:
            score -= 15

    matched_must = must_have & user_ingredients
    missing_must = must_have - user_ingredients
    score += len(matched_must) * 40

    buyable_missing = missing_must & buy_optional
    non_buyable_missing = missing_must - buy_optional
    score -= len(buyable_missing) * 10
    score -= len(non_buyable_missing) * 35

    matched_nice = nice_to_have & user_ingredients
    score += len(matched_nice) * 15

    all_used = matched_must | matched_nice
    for i, a in enumerate(list(all_used)):
        for b in list(all_used)[i + 1:]:
            cs = get_compatibility_score(a, b)
            score += cs * 0.15

    usage_bonus = min(len(all_used) / max(len(user_ingredients), 1) * 20, 20)
    score += usage_bonus

    return score


def _determine_mode(recipe: dict, user_ingredients: set[str]) -> str:
    must_have = set(recipe.get("must_have", []))
    missing = must_have - user_ingredients
    return "no_buy" if not missing else "with_buy"


def _build_additional_ingredients(recipe: dict, user_ingredients: set[str]) -> list[str]:
    must_have = set(recipe.get("must_have", []))
    missing_must = must_have - user_ingredients
    # must_have で足りないものだけを「追加で買うもの」とする
    return list(missing_must)


def _build_entry(score: float, recipe: dict, user_ingredients: set[str], slot: str, slot_label: str) -> dict:
    mode = _determine_mode(recipe, user_ingredients)
    return {
        "id": recipe.get("id"),
        "name": recipe["name"],
        "slot": slot,
        "slot_label": slot_label,
        "mode": mode,
        "time_minutes": recipe.get("time_minutes", 15),
        "cost_yen": recipe.get("cost_yen", 150),
        "summary": recipe.get("summary", ""),
        "additional_ingredients": _build_additional_ingredients(recipe, user_ingredients),
        "seasonings": recipe.get("seasonings", []),
        "image_prompt": get_image_prompt_for_recipe(recipe),
        "score": round(score, 1),
    }


def build_candidates(user_input: str) -> dict:
    """
    ①定番 ②ちょいアレンジ ③買い足しなし の候補を返す。
    Returns: {"candidates": [...], "sufficient": bool}
    """
    user_ingredients = set(normalize_ingredients_list(user_input))
    recipes = get_recipes()

    scored = []
    for recipe in recipes:
        must_have = set(recipe.get("must_have", []))
        if must_have:
            matched = must_have & user_ingredients
            if len(matched) < len(must_have) / 2:
                continue
        s = _score_recipe(recipe, user_ingredients)
        if s > 0:
            scored.append((s, recipe))

    scored.sort(key=lambda x: -x[0])

    standard = None
    creative = None
    no_buy = None
    seen_ids = set()

    for s, recipe in scored:
        rid = recipe.get("id")
        mode = _determine_mode(recipe, user_ingredients)

        if standard is None and mode == "with_buy":
            standard = _build_entry(s, recipe, user_ingredients, "standard", "定番")
            seen_ids.add(rid)
            continue

        if no_buy is None and mode == "no_buy":
            no_buy = _build_entry(s, recipe, user_ingredients, "no_buy", "買い足しなし")
            seen_ids.add(rid)

        if standard is not None and no_buy is not None:
            break

    for s, recipe in scored:
        rid = recipe.get("id")
        if rid in seen_ids:
            continue
        if _determine_mode(recipe, user_ingredients) != "with_buy":
            continue
        creative = _build_entry(s, recipe, user_ingredients, "creative", "ちょいアレンジ")
        seen_ids.add(rid)
        break

    if standard is None:
        for s, recipe in scored:
            rid = recipe.get("id")
            if rid in seen_ids:
                continue
            standard = _build_entry(s, recipe, user_ingredients, "standard", "定番")
            seen_ids.add(rid)
            break

    if creative is None:
        for s, recipe in scored:
            rid = recipe.get("id")
            if rid in seen_ids:
                continue
            creative = _build_entry(s, recipe, user_ingredients, "creative", "ちょいアレンジ")
            seen_ids.add(rid)
            break

    candidates = [c for c in (standard, creative, no_buy) if c is not None]
    return {
        "candidates": candidates,
        "sufficient": len(candidates) >= 3,
    }
