/**
 * Zerochan scraping logic using Playwright.
 *
 * Visits a range of search-result pages and extracts unique post links.
 */

import { chromium } from "playwright";
import { logger } from "./logger.js";

const USER_AGENT =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
  "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36";

const POST_ID_PATTERN = /zerochan\.net\/(\d+)/;

/**
 * Extract unique post links from a list of anchor hrefs.
 * @param {string[]} hrefs
 * @returns {string[]}
 */
function extractPostLinks(hrefs) {
  const links = new Set();
  for (const href of hrefs) {
    if (!href) continue;
    const match = POST_ID_PATTERN.exec(href);
    if (match) {
      links.add(`https://www.zerochan.net/${match[1]}`);
    }
  }
  return [...links];
}

/**
 * Scrape a single page and return its unique post links.
 * @param {import("playwright").Page} page
 * @param {string} url
 * @param {number} timeoutMs
 * @returns {Promise<string[]>}
 */
async function scrapePage(page, url, timeoutMs) {
  logger.info(`Scraping ${url}`);
  await page.goto(url, { wait_until: "domcontentloaded", timeout: timeoutMs });
  // Give the page a moment to render dynamic content.
  await page.waitForTimeout(2000);
  const hrefs = await page.locator("a").evaluateAll((els) => els.map((e) => e.href));
  return extractPostLinks(hrefs);
}

/**
 * Scrape a range of Zerochan search pages.
 *
 * @param {object} options
 * @param {string} options.searchTag
 * @param {number} options.startPage
 * @param {number} options.pagesPerRun
 * @param {number} options.requestDelayMs
 * @param {number} options.pageTimeoutMs
 * @returns {Promise<{ links: string[], hitEmptyPage: boolean }>}
 */
export async function scrapeZerochan({
  searchTag,
  startPage,
  pagesPerRun,
  requestDelayMs,
  pageTimeoutMs,
}) {
  const collected = new Set();
  const endPage = startPage + pagesPerRun;
  let hitEmptyPage = false;

  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext({ userAgent: USER_AGENT });
    const page = await context.newPage();

    for (let pageNum = startPage; pageNum < endPage; pageNum++) {
      const url = `https://www.zerochan.net/${searchTag}?p=${pageNum}`;
      const links = await scrapePage(page, url, pageTimeoutMs);

      for (const link of links) {
        collected.add(link);
      }
      logger.info(
        `Collected ${links.length} links from page ${pageNum} (total ${collected.size})`
      );

      if (links.length === 0) {
        logger.warn(
          `Page ${pageNum} returned no links; reached the end of available pages.`
        );
        hitEmptyPage = true;
        break;
      }

      if (pageNum < endPage - 1) {
        await new Promise((resolve) => setTimeout(resolve, requestDelayMs));
      }
    }

    await context.close();
  } finally {
    await browser.close();
  }

  return { links: [...collected], hitEmptyPage };
}