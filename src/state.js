/**
 * Persistent state management for posted links and page tracking.
 *
 * State is stored in plain-text files so it can be committed back to the
 * repository between GitHub Actions runs, surviving container restarts.
 */

import { readFile, writeFile, appendFile, access } from "node:fs/promises";
import { constants } from "node:fs";

const POSTED_FILE = process.env.POSTED_FILE || "posted.txt";
const PAGE_FILE = process.env.PAGE_FILE || "current_page.txt";

async function fileExists(file) {
  try {
    await access(file, constants.F_OK);
    return true;
  } catch {
    return false;
  }
}

/**
 * Load the set of already-posted links from disk.
 * @returns {Promise<Set<string>>}
 */
export async function loadPostedLinks() {
  if (!(await fileExists(POSTED_FILE))) {
    return new Set();
  }
  const content = await readFile(POSTED_FILE, "utf8");
  return new Set(
    content
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean)
  );
}

/**
 * Append successfully posted links to the cache file.
 * @param {string[]} links
 */
export async function appendPostedLinks(links) {
  if (links.length === 0) return;
  const content = links.map((link) => `${link}\n`).join("");
  await appendFile(POSTED_FILE, content, "utf8");
}

/**
 * Read the current page tracker, defaulting to 1.
 * @returns {Promise<number>}
 */
export async function readCurrentPage() {
  if (!(await fileExists(PAGE_FILE))) {
    return 1;
  }
  try {
    const raw = (await readFile(PAGE_FILE, "utf8")).trim();
    const page = Number.parseInt(raw, 10);
    return Number.isNaN(page) || page < 1 ? 1 : page;
  } catch {
    return 1;
  }
}

/**
 * Persist the page tracker for the next run.
 * @param {number} page
 */
export async function writeCurrentPage(page) {
  await writeFile(PAGE_FILE, `${page}\n`, "utf8");
}