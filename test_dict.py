"""辞書推薦をLINE表示っぽく確認するローカルテスト用スクリプト。"""
import sys

from services.recipe_recommender import build_candidates


QUICK_REPLIES = ["買い物リスト", "保存リスト", "保存", "使い方"]


def _as_line_recipe(candidate: dict) -> dict:
    return {
        "title": candidate.get("name", "レシピ"),
        "slot": candidate.get("slot", ""),
        "slot_label": candidate.get("slot_label", ""),
        "mode": candidate.get("mode", "no_buy"),
        "time_min": candidate.get("time_minutes", "?"),
        "cost_yen": candidate.get("cost_yen", "?"),
        "description": candidate.get("summary", ""),
        "additional_ingredients": candidate.get("additional_ingredients", []),
        "additional_seasonings": candidate.get("seasonings", []),
        "image_prompt": candidate.get("image_prompt", ""),
        "score": candidate.get("score", 0),
    }


def _format_items(items: list) -> str:
    return " / ".join(items) if items else "なし"


def _print_line_card(recipe: dict, index: int, family_size: int) -> None:
    buy_label = "あり" if recipe["mode"] == "with_buy" else "なし"
    cost = recipe["cost_yen"]
    total_cost = cost * family_size if isinstance(cost, int) else cost
    buy_items = recipe["additional_ingredients"] + recipe["additional_seasonings"]

    print(f"【カード {index}】")
    print(f"番号        : {index}")
    print(f"枠          : {recipe['slot_label'] or recipe['slot'] or 'なし'}")
    print(f"買い足し    : {buy_label}")
    print(f"料理名      : {recipe['title']}")
    print(f"時間        : {recipe['time_min']}分")
    print(f"目安        : 約{total_cost}円（{family_size}人分）")
    print(f"説明        : {recipe['description'] or 'なし'}")

    if recipe["mode"] == "with_buy":
        print(f"追加で買うもの: {_format_items(recipe['additional_ingredients'])}")
        print(f"調味料      : {_format_items(recipe['additional_seasonings'])}")
    else:
        print(f"調味料      : {_format_items(recipe['additional_seasonings'])}")

    print(f"画像プロンプト: {recipe['image_prompt'] or 'なし'}")
    print(f"スコア      : {recipe['score']}")
    print(f"ボタン      : 詳しく見る -> LINE送信テキスト「{index}」")
    if buy_items:
        print(f"詳細画面ボタン: 買い物リストに登録 -> LINE送信テキスト「買い物リスト登録:{index}」")
    print()


def run(ingredients: str, family_size: int = 1) -> None:
    result = build_candidates(ingredients)
    candidates = [_as_line_recipe(c) for c in result["candidates"]]
    sufficient = result["sufficient"]

    print()
    print("=" * 64)
    print("LINE表示プレビュー")
    print("=" * 64)
    print(f"入力食材    : {ingredients}")
    print(f"人数        : {family_size}人")
    print(f"候補数      : {len(candidates)}件")
    print(f"GPT整形対象 : {'はい（②は本番で少しアレンジ可）' if sufficient else 'いいえ（本番はGPT生成へフォールバック）'}")
    print(f"alt_text    : レシピ3案をご提案します")
    print()

    if not candidates:
        print("LINE返信: すみません、うまく作れませんでした。")
        print("         食材をもう一度送ってください。")
        print()
        return

    for i, recipe in enumerate(candidates, 1):
        _print_line_card(recipe, i, family_size)

    print("クイックリプライ:")
    for label in QUICK_REPLIES:
        print(f"- {label}")
    print()

    if not sufficient:
        print("注意:")
        print("辞書候補が3件未満なので、本番LINEではこのあとGPTのゼロ生成結果が表示される。")
        print("ここでは辞書で拾えた候補だけを表示してる。")
        print()


def main() -> None:
    if len(sys.argv) > 1:
        run(" ".join(sys.argv[1:]).strip())
        return

    print("食材を入力してね（例: 卵、ネギ、トマト）  終了: q")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if line.lower() in ("q", "quit", "exit"):
            break
        if line:
            run(line)


if __name__ == "__main__":
    main()
