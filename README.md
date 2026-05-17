# TrendRadar v6.6.0

热榜聚合与推送工具，抓取多平台热搜 + RSS 订阅，按关键词或 AI 兴趣筛选后推送到各通知渠道。

---

## 功能

- **热榜抓取**：今日头条、百度、微博、知乎、抖音、bilibili、澎湃、凤凰网、华尔街见闻、财联社、贴吧
- **RSS 订阅**：支持任意 RSS/Atom 源，默认含 Hacker News、阮一峰、V2EX、TechCrunch 等
- **筛选方式**：关键词匹配（`frequency_words.txt`）或 AI 智能筛选（`ai_interests.txt`，用自然语言描述兴趣）
- **推送模式**：当前榜单 / 增量（仅新增）/ 全天汇总，三种模式可按时间段切换
- **AI 分析**：通过 LiteLLM 调用 DeepSeek / OpenAI / Gemini 等，生成热点趋势摘要
- **AI 翻译**：推送内容多语言翻译
- **调度系统**：基于 `timeline.yaml`，按时间段控制采集/推送/分析行为，内置5种预设
- **存储**：本地 SQLite，或远程 S3 兼容存储（Cloudflare R2 / OSS / COS 等）
- **MCP Server**：对接 Claude Desktop 等 AI 客户端，支持自然语言查询历史数据

---

## 推送渠道

飞书 · 钉钉 · 企业微信（含个人微信） · Telegram · Slack · Bark · ntfy · 通用 Webhook

---

## 部署

### GitHub Actions（手动触发）

1. Fork 本仓库
2. 在 `Settings → Secrets and variables → Actions` 中配置至少一个推送渠道的 Secret（见下方环境变量列表）
3. 手动触发 `Get Hot News` workflow

> 若要恢复定时自动运行，删除 `.github/workflows/crawler.yml` 中 `crawl` job 的 `if: github.event_name != 'schedule'` 条件。

### Docker

```bash
git clone https://github.com/sansan0/TrendRadar.git
cd TrendRadar

# 配置环境变量（通知渠道 + AI）
cp .env.example .env  # 或直接编辑 docker-compose.yml

docker compose -f docker/docker-compose.yml up -d
```

默认每 30 分钟运行一次（`CRON_SCHEDULE=*/30 * * * *`）。网页报告访问 `http://localhost:8080`（需启用 `ENABLE_WEBSERVER=true`）。

MCP 服务独立运行在 `localhost:3333`。

### 本地运行

```bash
pip install uv
uv sync --frozen --no-dev
uv run python -m trendradar
```

---

## 配置文件

| 文件 | 说明 |
|---|---|
| `config/config.yaml` | 主配置：平台、RSS 源、推送渠道、AI、存储、调度预设 |
| `config/timeline.yaml` | 时间段调度：每个时段的采集/推送/分析行为 |
| `config/frequency_words.txt` | 关键词配置，支持正则语法 `/pattern/` 和显示名别名 `=> 名称` |
| `config/ai_interests.txt` | AI 筛选兴趣描述（`filter.method: ai` 时生效） |
| `config/ai_analysis_prompt.txt` | AI 分析提示词（可自定义分析角色和输出格式） |

在线编辑器：https://sansan0.github.io/TrendRadar/

---

## 主要环境变量

GitHub Actions 通过 Secrets 传入，Docker 通过 `.env` 或 `docker-compose.yml` 配置。

| 变量 | 说明 |
|---|---|
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Telegram Bot |
| `DINGTALK_WEBHOOK_URL` | 钉钉机器人 Webhook |
| `WEWORK_WEBHOOK_URL` / `WEWORK_MSG_TYPE` | 企业微信（`markdown` 群机器人 / `text` 个人微信）|
| `NTFY_TOPIC` / `NTFY_SERVER_URL` / `NTFY_TOKEN` | ntfy |
| `BARK_URL` | Bark |
| `SLACK_WEBHOOK_URL` | Slack |
| `GENERIC_WEBHOOK_URL` / `GENERIC_WEBHOOK_TEMPLATE` | 通用 Webhook（Discord、Matrix 等）|
| `AI_API_KEY` / `AI_MODEL` / `AI_API_BASE` | AI 模型配置（覆盖 config.yaml）|
| `S3_ENDPOINT_URL` / `S3_BUCKET_NAME` / `S3_ACCESS_KEY_ID` / `S3_SECRET_ACCESS_KEY` | 远程存储 |

多账号用分号分隔，如 `FEISHU_WEBHOOK_URL=url1;url2`。

---

## 调度预设

`config/config.yaml` 中 `schedule.preset` 可选：

| 预设 | 说明 |
|---|---|
| `always_on` | 全天候，有新增即推送 |
| `morning_evening` | 早晚各推一次汇总（默认）|
| `office_hours` | 工作日三段式（到岗/午间/收工）|
| `night_owl` | 午后速览 + 深夜全天汇总 |
| `custom` | 完全自定义，详见 `timeline.yaml` |

---

## 数据来源

热榜数据来自 [newsnow](https://github.com/ourongxing/newsnow) 项目 API，感谢作者提供的服务。
