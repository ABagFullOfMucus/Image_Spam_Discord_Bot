/**
 * Minimal structured logger with leveled output and ISO timestamps.
 *
 * Level is controlled via the LOG_LEVEL environment variable
 * (debug | info | warn | error), defaulting to info.
 */

const LEVELS = { debug: 10, info: 20, warn: 30, error: 40 };

const currentLevel = LEVELS[process.env.LOG_LEVEL] ?? LEVELS.info;

function format(level, message, meta) {
  const ts = new Date().toISOString();
  const base = `[${ts}] [${level.toUpperCase()}] ${message}`;
  return meta ? `${base} ${JSON.stringify(meta)}` : base;
}

export const logger = {
  debug(message, meta) {
    if (LEVELS.debug >= currentLevel) console.debug(format("debug", message, meta));
  },
  info(message, meta) {
    if (LEVELS.info >= currentLevel) console.log(format("info", message, meta));
  },
  warn(message, meta) {
    if (LEVELS.warn >= currentLevel) console.warn(format("warn", message, meta));
  },
  error(message, meta) {
    if (LEVELS.error >= currentLevel) console.error(format("error", message, meta));
  },
};