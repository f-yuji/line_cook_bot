import json
import re
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"
_cache: dict = {}


def _load(filename: str):
    if filename not in _cache:
        with open(_DATA_DIR / filename, encoding="utf-8") as f:
            _cache[filename] = json.load(f)
    return _cache[filename]


def get_ingredients() -> dict:
    return _load("ingredients.json")


def get_recipes() -> list:
    return _load("recipes.json")


def get_compatibility() -> dict:
    return _load("compatibility.json")


def get_image_map() -> dict:
    return _load("image_map.json")


def normalize_ingredient(name: str) -> str:
    name = name.strip()
    ingredients = get_ingredients()
    if name in ingredients:
        return name
    for canonical, data in ingredients.items():
        if name in data.get("aliases", []):
            return canonical
    return name


def normalize_ingredients_list(raw: str) -> list[str]:
    items = re.split(r"[、,，\s]+", raw.strip())
    return [normalize_ingredient(i.strip()) for i in items if i.strip()]


def get_compatibility_score(a: str, b: str) -> float:
    compat = get_compatibility()
    return compat.get(f"{a}+{b}", compat.get(f"{b}+{a}", 0))


def get_image_prompt_for_recipe(recipe: dict) -> str:
    image_map = get_image_map()
    fallbacks = image_map.get("pattern_fallback", {})
    pattern = recipe.get("pattern", "")
    base = fallbacks.get(pattern, fallbacks.get("default", "Japanese home cooking"))
    return f"{recipe['name']}, {base}, simple plate, warm natural light, realistic"
