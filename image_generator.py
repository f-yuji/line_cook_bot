from openai import OpenAI
import config

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


def generate_dish_image(image_prompt: str) -> str | None:
    """
    料理の完成イメージ画像を生成してURLを返す。
    ENABLE_IMAGE_GENERATION=false の場合は None を返す。
    """
    if not config.ENABLE_IMAGE_GENERATION:
        return None
    try:
        res = get_client().images.generate(
            model="dall-e-2",
            prompt=f"Photo of {image_prompt}, Japanese home cooking style, appetizing, natural light",
            size="256x256",
            n=1,
        )
        return res.data[0].url
    except Exception as e:
        print(f"[image_generator] generate_dish_image error: {e}")
        return None
