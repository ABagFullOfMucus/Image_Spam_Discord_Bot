/**
 * Image Spam Discord Bot
 *
 * Scrapes Zerochan for new images matching a search tag and posts the links
 * to a Discord channel. Designed to run periodically via GitHub Actions,
 * persisting its state between runs.
 */

import { loadConfig } from "./config.js";
import { logger } from "./logger.js";
import {
  loadPostedLinks,
  appendPostedLinks,
  readCurrentPage,
  writeCurrentPage,
} from "./state.js";
import { scrapeZerochan } from "./scraper.js";
import { DiscordClient } from "./discord.js";

async function main() {
  const config = loadConfig();
  logger.info("Starting bot run", {
    searchTag: config.searchTag,
    pagesPerRun: config.pagesPerRun,
  });

  const posted = await loadPostedLinks();
  const startPage = await readCurrentPage();
  logger.info(
    `Processing pages ${startPage} to ${startPage + config.pagesPerRun - 1}`
  );

  const { links, hitEmptyPage } = await scrapeZerochan({
    searchTag: config.searchTag,
    startPage,
    pagesPerRun: config.pagesPerRun,
    requestDelayMs: config.requestDelayMs,
    pageTimeoutMs: config.pageTimeoutMs,
  });

  const newLinks = links.filter((link) => !posted.has(link));
  logger.info(
    `Found ${newLinks.length} new links out of ${links.length} scraped`
  );

  if (newLinks.length > 0) {
    const discord = new DiscordClient({
      token: config.discordToken,
      channelId: config.discordChannelId,
      delayMs: config.discordDelayMs,
      maxRetries: config.maxRetries,
    });

    const postedLinks = await discord.postLinks(newLinks);
    if (postedLinks.length > 0) {
      await appendPostedLinks(postedLinks);
      logger.info(`Cached ${postedLinks.length} newly posted links`);
    }
  } else {
    logger.info("No new links to post.");
  }

  // Only advance the tracker if we didn't reach the end of available pages.
  const nextPage = hitEmptyPage ? 1 : startPage + config.pagesPerRun;
  await writeCurrentPage(nextPage);
  logger.info(`Next run will start at page ${nextPage}`);
}

main().catch((err) => {
  logger.error("Fatal error", { error: err.message, stack: err.stack });
  process.exitCode = 1;
});