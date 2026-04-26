import hashlib
import hmac
import base64

from flask import Flask, request, abort, jsonify

import config
import billing
import line_handlers
from linebot.v3.webhooks import MessageEvent, TextMessageContent, ImageMessageContent
from linebot.v3 import WebhookParser
from linebot.v3.webhook import WebhookPayload
from linebot.v3.exceptions import InvalidSignatureError

app = Flask(__name__)

parser = WebhookParser(config.LINE_CHANNEL_SECRET)


# ── LINE Webhook ──────────────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        payload: WebhookPayload = parser.parse(body, signature, as_payload=True)
    except InvalidSignatureError:
        abort(400, "Invalid signature")
    except Exception as e:
        print(f"[app] webhook parse error: {e}")
        abort(400)

    try:
        for event in payload.events:
            if not isinstance(event, MessageEvent):
                continue

            user_id = event.source.user_id
            reply_token = event.reply_token

            display_name = _get_display_name(user_id)

            if isinstance(event.message, TextMessageContent):
                line_handlers.handle_text_message(
                    user_id, display_name, reply_token, event.message.text
                )
            elif isinstance(event.message, ImageMessageContent):
                line_handlers.handle_image_message(
                    user_id, display_name, reply_token, event.message.id
                )
    except Exception as e:
        import traceback
        traceback.print_exc()
        return "OK", 200

    return "OK", 200


def _get_display_name(user_id: str) -> str:
    import requests as req
    url = f"https://api.line.me/v2/bot/profile/{user_id}"
    headers = {"Authorization": f"Bearer {config.LINE_CHANNEL_ACCESS_TOKEN}"}
    try:
        res = req.get(url, headers=headers, timeout=5)
        if res.ok:
            return res.json().get("displayName", user_id)
    except Exception:
        pass
    return user_id


# ── Stripe Webhook ────────────────────────────────────────────────────────

@app.route("/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    ok, msg = billing.handle_stripe_webhook(payload, sig_header)
    if not ok:
        abort(400, msg)
    return jsonify({"status": "ok"}), 200


@app.route("/stripe/success")
def stripe_success():
    return "決済が完了しました。LINEに戻って続けてください。", 200


@app.route("/stripe/cancel")
def stripe_cancel():
    return "決済をキャンセルしました。", 200


# ── Health Check ──────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


# ── Entry Point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
