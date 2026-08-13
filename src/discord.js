/**
 * Discord REST API client with retry and rate-limit handling.
 *
 * Uses Node's native fetch (stable since Node 21) and handles Discord's
 * 429 rate-limit responses by honoring the Retry-After header.
 */

import { logger } from "./logger.js";

const API_BASE = "https://discord.com/api/v10";

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export class DiscordClient {
  /**
   * @param {object} options
   * @param {string} options.token Bot token.
   * @param {string} options.channelId Target channel ID.
   * @param {number} options.delayMs Delay between messages.
   * @param {number} options.maxRetries Max attempts per message.
   */
  constructor({ token, channelId, delayMs, maxRetries }) {
    this.token = token;
    this.channelId = channelId;
    this.delayMs = delayMs;
    this.maxRetries = maxRetries;
  }

  /**
   * Post a single message, retrying on rate limits and server errors.
   * @param {string} content
   * @returns {Promise<boolean>} Whether the message was posted.
   */
  async postMessage(content) {
    const url = `${API_BASE}/channels/${this.channelId}/messages`;
    const headers = {
      Authorization: `Bot ${this.token}`,
      "Content-Type": "application/json",
    };

    for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
      const response = await fetch(url, {
        method: "POST",
        headers,
        body: JSON.stringify({ content }),
      });

      if (response.status === 200 || response.status === 201) {
        return true;
      }

      if (response.status === 429) {
        const retryAfter = Number(response.headers.get("retry-after")) || 1;
        logger.warn(`Rate limited; waiting ${retryAfter}s before retry.`);
        await sleep(retryAfter * 1000);
        continue;
      }

      if (response.status >= 500 && attempt < this.maxRetries) {
        const backoff = 2 ** attempt * 1000;
        logger.warn(`Server error ${response.status}; retrying in ${backoff}ms.`);
        await sleep(backoff);
        continue;
      }

      logger.error(
        `Discord API error: ${response.status} ${await response.text()}`
      );
      return false;
    }

    return false;
  }

  /**
   * Post a list of links, returning the ones that were successfully posted.
   * Posts newest-first to match the original behavior.
   * @param {string[]} links
   * @returns {Promise<string[]>}
   */
  async postLinks(links) {
    const posted = [];
    for (const link of [...links].reverse()) {
      const ok = await this.postMessage(`New image:\n${link}`);
      if (ok) {
        posted.push(link);
        logger.info(`Posted ${link}`);
      }
      await sleep(this.delayMs);
    }
    return posted;
  }
}