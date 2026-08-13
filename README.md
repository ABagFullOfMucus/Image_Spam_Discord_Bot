# Image Spam Discord Bot

Scrapes [Zerochan](https://www.zerochan.net) for new images matching a search tag and posts the links to a Discord channel. Designed to run periodically via GitHub Actions, persisting its state between runs.

## Features

- **Node.js 24** with native `fetch` — no extra HTTP dependencies
- **Playwright** for reliable browser-based scraping
- **Structured logging** with configurable log levels
- **Discord rate-limit handling** with automatic retry and backoff
- **Concurrency-safe** GitHub Actions workflow (no overlapping runs)
- **Cached dependencies & browsers** for faster CI runs
- **Fail-safe state tracking** — page tracker only advances on success

## Requirements

- Node.js 24+
- A Discord bot token with permission to post in the target channel
- A GitHub repository with the following secrets:
  - `DISCORD_TOKEN`
  - `DISCORD_CHANNEL_ID`

## Local Development

```bash
# Install dependencies
npm install

# Install Playwright browser
npx playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your Discord token and channel ID

# Run the bot
npm start
```

## Configuration

All configuration is via environment variables. See [.env.example](.env.example) for the full list with defaults.

| Variable | Default | Description |
| --- | --- | --- |
| `DISCORD_TOKEN` | — | Discord bot token (required) |
| `DISCORD_CHANNEL_ID` | — | Target channel ID (required) |
| `SEARCH_TAG` | `Satono+Diamond` | Zerochan search tag |
| `PAGES_PER_RUN` | `30` | Pages to scrape per run |
| `REQUEST_DELAY_MS` | `3000` | Delay between page requests |
| `DISCORD_DELAY_MS` | `2000` | Delay between Discord messages |
| `PAGE_TIMEOUT_MS` | `60000` | Page load timeout |
| `MAX_RETRIES` | `3` | Discord API retry attempts |
| `LOG_LEVEL` | `info` | `debug` \| `info` \| `warn` \| `error` |

## How It Works

1. Reads the current page from `current_page.txt` (defaults to 1).
2. Scrapes `PAGES_PER_RUN` pages of Zerochan search results.
3. Filters out links already present in `posted.txt`.
4. Posts new links to Discord, newest-first.
5. Appends successfully posted links to `posted.txt`.
6. Advances `current_page.txt` for the next run (or resets to 1 if the end of available pages was reached).

## GitHub Actions

The workflow runs every 15 minutes and:

- Uses Node.js 24 with npm dependency caching
- Caches Playwright browsers between runs
- Prevents overlapping runs via a concurrency group
- Commits state changes (`posted.txt`, `current_page.txt`) back to the repo

## Project Structure

```
├── .github/workflows/run-bot.yml   # CI/CD workflow
├── src/
│   ├── config.js                   # Env config loading & validation
│   ├── discord.js                  # Discord REST client with retries
│   ├── index.js                    # Entry point / orchestration
│   ├── logger.js                   # Structured logger
│   ├── scraper.js                  # Playwright scraping logic
│   └── state.js                    # Persistent state management
├── .env.example                    # Example environment config
├── package.json
└── README.md
```

## License

MIT