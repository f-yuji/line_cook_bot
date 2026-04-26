import base64
import requests
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


def fetch_line_image(message_id: str, access_token: str) -> bytes | None:
    """LINE APIから画像バイナリを取得する。"""
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        return res.content
    except Exception as e:
        print(f"[vision_analyzer] fetch_line_image error: {e}")
        return None


def analyze_ingredients_from_image(image_bytes: bytes) -> list | None:
    """画像バイナリから食材リストを返す。"""
    try:
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        res = get_client().chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}",
                                "detail": "low",
                            },
                        },
                        {"type": "text", "text": prompts.VISION_PROMPT},
                    ],
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=500,
        )
        text = res.choices[0].message.content or ""
        data = parse_json_safe(text)
        if data:
            return data.get("ingredients", [])
        return None
    except Exception as e:
        print(f"[vision_analyzer] analyze error: {e}")
        return None
