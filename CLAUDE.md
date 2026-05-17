# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TrendRadar v6.6.0 — a hot-news aggregation and push notification tool. It crawls trending lists from Chinese platforms (Weibo, Zhihu, Bilibili, etc.) and RSS feeds, optionally filters via keyword matching or AI, then pushes summaries to notification channels (Feishu, Telegram, DingTalk, WeChat Work, etc.). AI features use LiteLLM to call DeepSeek/OpenAI/Gemini/etc.

## Commands

```bash
# Install dependencies (requires Python >=3.12)
pip install uv
uv sync --frozen --no-dev

# Run the main crawler/push pipeline
uv run python -m trendradar

# Run the MCP server (stdio mode, for Claude Desktop etc.)
uv run trendradar-mcp

# Run with Docker (includes web server on :8080, MCP server on :3333)
docker compose -f docker/docker-compose.yml up -d
```

There is no test suite in this repo. Validation is done by running the tool against live config.

## Architecture

### Entry Point & Orchestration

`trendradar/__main__.py` is the single entry point for the pipeline. It:
1. Loads config (`config/config.yaml` + optional env var overrides)
2. Resolves the current schedule via `Scheduler` → `ResolvedSchedule`
3. Crawls platforms and RSS feeds
4. Filters results (keyword or AI)
5. Builds report data, generates HTML
6. Runs AI analysis if enabled
7. Dispatches notifications

`trendradar/context.py` (`AppContext`) is a central dependency-injection object that wraps config-dependent operations (time formatting, storage, scheduling, filtering). Almost all major functions accept an `AppContext` instance rather than raw config.

### Key Modules

| Package | Purpose |
|---|---|
| `trendradar/core/` | Config loading (`loader.py`), keyword frequency analysis (`frequency.py`, `analyzer.py`), scheduling logic (`scheduler.py`) |
| `trendradar/crawler/` | Platform hot-list fetcher (`fetcher.py`) via newsnow API; RSS fetcher and parser (`rss/`) |
| `trendradar/ai/` | LiteLLM-backed AI client (`client.py`), content analysis (`analyzer.py`), AI filter (`filter.py`), translation (`translator.py`), prompt loading (`prompt_loader.py`) |
| `trendradar/storage/` | SQLite storage abstraction; local (`local.py`) and S3-compatible remote (`remote.py`) backends; manager auto-selects based on config |
| `trendradar/notification/` | Per-channel formatters, batching/splitting logic, dispatcher |
| `trendradar/report/` | HTML report generation, JSON export, RSS-format HTML |
| `mcp_server/` | FastMCP 2.0 server exposing TrendRadar data to AI clients (Claude Desktop etc.) over stdio or HTTP |

### Scheduling System

`config/timeline.yaml` defines time periods with per-period overrides for `collect`, `push`, `analyze`, `report_mode`, `ai_mode`, `once_*`. `config/config.yaml` → `schedule.preset` selects a named preset (`always_on`, `morning_evening`, `office_hours`, `night_owl`, `custom`). The `Scheduler` class resolves the current moment to a `ResolvedSchedule` dataclass used throughout `__main__.py` to gate behavior.

### Filtering

Two modes controlled by `filter.method` in `config.yaml`:
- `keyword` — regex-capable keyword groups in `config/frequency_words.txt`
- `ai` — LLM-based interest matching using `config/ai_interests.txt`; results are cached and only re-classified when interests change significantly (controlled by `ai_filter.reclassify_threshold`)

### Storage

Backend is auto-selected: GitHub Actions with S3 env vars → remote (S3-compatible); otherwise → local SQLite under `output/`. Each day's data lives in `output/news/YYYY-MM-DD.db`. The `StorageManager` in `trendradar/storage/manager.py` wraps both backends with the same interface.

### Configuration & Environment Variables

All secrets/webhooks should be passed as environment variables (GitHub Secrets or `.env` for Docker). Env vars override `config.yaml` values:

- `AI_API_KEY`, `AI_MODEL`, `AI_API_BASE` — override `ai` section
- `AI_ANALYSIS_ENABLED` — override `ai_analysis.enabled`
- `FEISHU_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`, `DINGTALK_WEBHOOK_URL`, `WEWORK_WEBHOOK_URL`, `NTFY_TOPIC`, `BARK_URL`, `SLACK_WEBHOOK_URL`, `GENERIC_WEBHOOK_URL` — notification channels
- `S3_ENDPOINT_URL`, `S3_BUCKET_NAME`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` — remote storage

Multiple accounts per channel: semicolon-separated values (e.g. `FEISHU_WEBHOOK_URL=url1;url2`).

### GitHub Actions

`.github/workflows/crawler.yml` runs the pipeline. The `crawl` job currently has `if: github.event_name != 'schedule'` which disables scheduled runs — only manual triggers work. Remove that condition to re-enable scheduled execution.
