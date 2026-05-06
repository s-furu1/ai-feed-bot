# ai-feed-bot

ai-feed-bot は、AI関連RSSを収集し、Ollamaで要約し、X投稿下書きを生成する backend/worker アプリです。Slack への投稿、ボタン、固定パネル管理は life-bot が internal API 経由で行います。

X自動投稿は行いません。採用操作は、人間が手動投稿するための状態変更だけです。X API token や投稿処理はこのリポジトリに置きません。

## 目的

- AI関連RSSの収集
- content_hash による重複排除
- Ollama HTTP API による要約とX下書き生成
- internal API 経由での採用 / 保留 / 破棄 / 再生成
- SQLite による永続化
- worker による定期実行の基盤

## RSS sources

初期source:

- Hugging Face Blog: `https://huggingface.co/blog/feed.xml`
- OpenAI News: `https://openai.com/news/rss.xml`
- Google DeepMind: `https://deepmind.google/blog/rss.xml`

TODO:

- Developers.IO はURL確定後に追加する
- Anthropic は公式RSSがないため運用方針を後で決める

## Ollama

Ollama は ai-feed-bot に内包しません。
`OLLAMA_BASE_URL` へ HTTP で接続し、`OLLAMA_MODEL` で指定したモデルを使います。

初期モデル名は設定値として `qwen3.5:9b` を想定します。実在確認やモデルpullはこのフェーズでは行いません。

## Slack gateway

Slack App と slash command は life-bot のみです。ai-feed-bot は実運用で Slack に直接接続しません。

life-bot から呼ばれる internal API:

- `GET /healthz`
- `POST /internal/feed/fetch`
- `GET /internal/drafts/pending`
- `GET /internal/drafts/held`
- `POST /internal/drafts/{draft_id}/approve`
- `POST /internal/drafts/{draft_id}/hold`
- `POST /internal/drafts/{draft_id}/reject`
- `POST /internal/drafts/{draft_id}/regenerate`

## ローカル起動

```bash
AI_FEED_DB_PATH=/tmp/ai-feed.db python -m app.main
```

internal APIを有効にする場合:

```bash
AI_FEED_ENABLE_WEB=true python -m app.main
```

workerを有効にする場合:

```bash
AI_FEED_ENABLE_WORKER=true python -m app.main
```

コンテナ運用では `AI_FEED_ENABLE_SLACK=false`、`AI_FEED_ENABLE_WORKER=true`、`AI_FEED_ENABLE_WEB=true` を前提にします。internal API は Docker network 内だけで使い、host port は公開しません。

## 環境変数

- `APP_ENV`
- `LOG_LEVEL`
- `AI_FEED_DB_PATH`
- `AI_FEED_ENABLE_SLACK` (deprecated; production は `false`)
- `AI_FEED_ENABLE_WORKER`
- `AI_FEED_ENABLE_WEB`
- `AI_FEED_WEB_HOST`
- `AI_FEED_WEB_PORT`
- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `AI_FEED_FETCH_INTERVAL_MINUTES`

secret 実値は `.env.example`、README、コードに書きません。

## DB

実運用時のDB配置想定:

```text
~/homeserver/docker/ai-feed-bot/data/ai-feed.db
```

ローカルデフォルトは `/data/ai-feed.db` です。テストでは `AI_FEED_DB_PATH` で一時DBを指定します。

## 次フェーズ

次フェーズは daily-report-bot 実装予定です。homeserver compose 整備はまだ行いません。
