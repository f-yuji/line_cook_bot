# レシピbot

LINEで食材を送るだけで、今日のご飯がすぐ決まる。冷蔵庫の写真でもOK。

---

## 機能

- 食材テキスト or 冷蔵庫写真 → レシピ3案提案
- 番号送信で詳細・手順・コツ表示
- 買い足しあり/なし切り替え
- 7日間無料トライアル → Stripe課金
- 余り物アレンジ対応
- 週間献立・買い物リスト生成
- 家族人数・栄養モード設定
- レシピ保存

---

## ファイル構成

```
app.py              Flask + Webhook受信
config.py           環境変数管理
db.py               Supabase CRUD
line_handlers.py    LINEメッセージ処理
recipe_generator.py OpenAI レシピ生成
vision_analyzer.py  OpenAI Vision 食材認識
image_generator.py  DALL-E 画像生成
billing.py          Stripe 課金処理
prompts.py          全プロンプト管理
utils.py            整形・パース補助
```

---

## セットアップ

### 1. Python 環境

```bash
cd C:\Users\f-yuj\dev\line_bot_cook
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. .env ファイル

プロジェクトルートに `.env` を作成。

```env
LINE_CHANNEL_ACCESS_TOKEN=YOUR_LINE_CHANNEL_ACCESS_TOKEN
LINE_CHANNEL_SECRET=YOUR_LINE_CHANNEL_SECRET
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=YOUR_SUPABASE_SERVICE_ROLE_KEY
STRIPE_SECRET_KEY=sk_live_xxxx
STRIPE_PRICE_ID=price_xxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxx
APP_BASE_URL=https://your-app.onrender.com
ENABLE_IMAGE_GENERATION=false
OPENAI_TEXT_MODEL=gpt-4o
OPENAI_VISION_MODEL=gpt-4o
OPENAI_IMAGE_MODEL=dall-e-3
```

---

## Supabase SQL

Supabase の SQL Editor で以下を実行してください。

```sql
-- users
create table if not exists users (
  user_id               text primary key,
  display_name          text,
  plan                  text default 'trial',
  mode                  text default 'no_buy',
  family_size           integer default 1,
  nutrition_mode        text default 'normal',
  trial_started_at      timestamptz,
  trial_end_at          timestamptz,
  stripe_customer_id    text,
  stripe_subscription_id text,
  created_at            timestamptz default now(),
  updated_at            timestamptz default now()
);

-- recipe_contexts
create table if not exists recipe_contexts (
  id          uuid primary key default gen_random_uuid(),
  user_id     text,
  recipes_json jsonb,
  created_at  timestamptz default now()
);
create index on recipe_contexts (user_id, created_at desc);

-- pending_ingredients
create table if not exists pending_ingredients (
  user_id          text primary key,
  ingredients_json jsonb,
  source           text,
  created_at       timestamptz default now()
);

-- saved_recipes
create table if not exists saved_recipes (
  id          uuid primary key default gen_random_uuid(),
  user_id     text,
  recipe_json jsonb,
  created_at  timestamptz default now()
);
create index on saved_recipes (user_id, created_at desc);

-- usage_logs
create table if not exists usage_logs (
  id         uuid primary key default gen_random_uuid(),
  user_id    text,
  action     text,
  metadata   jsonb,
  created_at timestamptz default now()
);
create index on usage_logs (user_id, created_at desc);

-- meal_plans
create table if not exists meal_plans (
  id         uuid primary key default gen_random_uuid(),
  user_id    text,
  plan_json  jsonb,
  created_at timestamptz default now()
);
create index on meal_plans (user_id, created_at desc);

-- recipe_library
create table if not exists recipe_library (
  id                     uuid primary key default gen_random_uuid(),
  ingredients_normalized text not null,
  mode                   text not null default 'mixed',
  nutrition_mode         text not null default 'normal',
  recipes_json           jsonb not null,
  use_count              integer not null default 0,
  created_at             timestamptz default now(),
  updated_at             timestamptz default now()
);
create index on recipe_library (mode, nutrition_mode, use_count desc);

-- pending_shopping
create table if not exists pending_shopping (
  user_id      text primary key,
  entries_json jsonb not null default '[]'::jsonb,
  updated_at   timestamptz default now()
);
```

---

## ローカル起動

```bash
python app.py
```

デフォルトポート: 8000

---

## ngrok接続（LINE Webhook開発時）

```bash
ngrok http 8000
```

表示された `https://xxxx.ngrok.io` を LINE Developers の Webhook URL に設定。

```
https://xxxx.ngrok.io/webhook
```

---

## LINE Webhook設定

1. LINE Developers Console → チャネル設定
2. Messaging API タブ
3. Webhook URL に `https://your-domain/webhook` を設定
4. 「Webhookの利用」を ON
5. 「応答メッセージ」を OFF（botが自動返信するため）

---

## Stripe Webhook設定

### ローカル開発

```bash
stripe listen --forward-to localhost:8000/stripe/webhook
```

表示される `whsec_xxxx` を `STRIPE_WEBHOOK_SECRET` に設定。

### 本番（Render / Fly.io）

Stripe Dashboard → Developers → Webhooks → Add endpoint

```
https://your-app.onrender.com/stripe/webhook
```

リッスンするイベント:
- `checkout.session.completed`
- `customer.subscription.deleted`
- `customer.subscription.canceled`
- `invoice.payment_failed`

---

## Render デプロイ

1. GitHub にプッシュ
2. Render で「New Web Service」
3. 環境変数をすべて設定
4. Start command:

```
gunicorn app:app --bind 0.0.0.0:$PORT
```

---

## Fly.io デプロイ

```bash
fly launch
fly secrets set LINE_CHANNEL_ACCESS_TOKEN=xxx LINE_CHANNEL_SECRET=xxx ...
fly deploy
```

`fly.toml` の `[[services]]` ポートを 8000 に合わせてください。

---

## クイックリプライ一覧

| ラベル | 動作 |
|---|---|
| 買い足しなし | mode = no_buy に変更 |
| 買い足しあり | mode = with_buy に変更 |
| 週間献立 | 7日分の献立生成 |
| 買い物リスト | 直近レシピ/献立から生成 |
| 保存 | 直近レシピを保存 |
| 使い方 | 操作ガイド表示 |

---

## その他コマンド

| 入力例 | 動作 |
|---|---|
| `人数 3人` | 家族人数を3人に設定 |
| `ヘルシー` / `ダイエット` / `がっつり` | 栄養モード変更 |
| `1` / `2詳しく` | 直近レシピの詳細表示 |
| `保存` / `1保存` | レシピを保存 |
| `昨日のカレー余ってる` | 余り物アレンジレシピ生成 |
