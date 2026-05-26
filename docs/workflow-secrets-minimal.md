# Minimal workflow secrets for TrendRadar (agy + R2)

This checklist is for `.github/workflows/crawler.yml` in this repo and enables:
- AI analysis
- AI translation
- AI filter
- report upload to R2 (same JSON delivery path used by `/trend-radar`)

## Required repository secrets

| Secret name | Recommended value | Notes |
| --- | --- | --- |
| `AI_ANALYSIS_ENABLED` | `true` | Enable analysis pipeline |
| `AI_TRANSLATION_ENABLED` | `true` | Enable translation pipeline |
| `AI_FILTER_ENABLED` | `true` | Enable AI filter pipeline |
| `R2_WARDROBE_BUCKET` | `<your-r2-bucket-name>` | Bucket that stores generated reports |
| `R2_ACCESS_KEY_ID` | `<cloudflare-r2-access-key-id>` | R2 access key id |
| `R2_SECRET_ACCESS_KEY` | `<cloudflare-r2-secret-access-key>` | R2 secret key |

## Workflow values already hardcoded (not secrets)

Current `crawler.yml` already sets:
- `AI_PROVIDER=agy`
- `AGY_BIN=/home/arthur/.local/bin/agy`
- `AGY_DANGEROUSLY_SKIP_PERMISSIONS=true`
- `AGY_TIMEOUT=180`
- `S3_ENDPOINT_URL=https://6748757663e36aa566fa418d53cce8a4.r2.cloudflarestorage.com`
- `S3_REGION=auto`

If your runner uses a different agy path, update `AGY_BIN` in workflow env.

## Optional notification secrets

You can leave these empty if you only need report generation + R2 delivery:
- `FEISHU_WEBHOOK_URL`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
- `DINGTALK_WEBHOOK_URL`
- `WEWORK_WEBHOOK_URL`, `WEWORK_MSG_TYPE`
- `NTFY_TOPIC`, `NTFY_SERVER_URL`, `NTFY_TOKEN`
- `BARK_URL`
- `SLACK_WEBHOOK_URL`
- `GENERIC_WEBHOOK_URL`, `GENERIC_WEBHOOK_TEMPLATE`
