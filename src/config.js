/**
 * Configuration loader with validation.
 *
 * Reads environment variables and provides a typed, validated config object.
 * Fails fast with a clear message if required variables are missing or invalid.
 */

const REQUIRED_VARS = ["DISCORD_TOKEN", "DISCORD_CHANNEL_ID"];

function requireEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function intEnv(name, defaultValue) {
  const raw = process.env[name];
  if (raw === undefined || raw === "") {
    return defaultValue;
  }
  const parsed = Number.parseInt(raw, 10);
  if (Number.isNaN(parsed) || parsed <= 0) {
    throw new Error(
      `Environment variable ${name} must be a positive integer, got "${raw}"`
    );
  }
  return parsed;
}

export function loadConfig() {
  for (const name of REQUIRED_VARS) {
    requireEnv(name);
  }

  return {
    discordToken: process.env.DISCORD_TOKEN,
    discordChannelId: process.env.DISCORD_CHANNEL_ID,
    searchTag: process.env.SEARCH_TAG || "Satono+Diamond",
    pagesPerRun: intEnv("PAGES_PER_RUN", 30),
    requestDelayMs: intEnv("REQUEST_DELAY_MS", 3000),
    discordDelayMs: intEnv("DISCORD_DELAY_MS", 2000),
    pageTimeoutMs: intEnv("PAGE_TIMEOUT_MS", 60000),
    maxRetries: intEnv("MAX_RETRIES", 3),
  };
}