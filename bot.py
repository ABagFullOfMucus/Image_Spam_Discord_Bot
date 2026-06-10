import os
import re
import asyncio
from pathlib import Path
import aiohttp
from playwright.async_api import async_playwright

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
SEARCH_TAG = os.getenv("SEARCH_TAG", "Satono+Diamond")

# How many pages to progress through per 15-minute run
PAGES_PER_RUN = int(os.getenv("PAGES_PER_RUN", "30"))
CACHE_FILE = "posted.txt"
PAGE_TRACKER_FILE = "current_page.txt"


def load_cache():
    if not Path(CACHE_FILE).exists():
        return set()
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_cache(link):
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def get_and_update_start_page():
    """Reads the last scraped page and updates it for the next run."""
    start_page = 1
    if Path(PAGE_TRACKER_FILE).exists():
        try:
            start_page = int(Path(PAGE_TRACKER_FILE).read_text().strip())
        except ValueError:
            start_page = 1

    # Calculate where the NEXT run should start
    next_run_start = start_page + PAGES_PER_RUN
    Path(PAGE_TRACKER_FILE).write_text(str(next_run_start))
    
    return start_page


async def scrape_single_page(page, url):
    print(f"Scraping target: {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        anchors = await page.locator("a").evaluate_all(
            "elements => elements.map(e => e.href)"
        )
        return anchors
    except Exception as e:
        print(f"Failed to scrape {url}: {repr(e)}")
        return []


async def get_zerochan_posts(start_page):
    all_links = []
    end_page = start_page + PAGES_PER_RUN

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            )
        )

        try:
            for page_num in range(start_page, end_page):
                url = f"https://www.zerochan.net/{SEARCH_TAG}?p={page_num}"
                anchors = await scrape_single_page(page, url)
                
                page_links_count = 0
                for href in anchors:
                    if not href:
                        continue
                    match = re.search(r"zerochan\.net/(\d+)", href)
                    if match:
                        link = f"https://www.zerochan.net/{match.group(1)}"
                        if link not in all_links:
                            all_links.append(link)
                            page_links_count += 1
                
                print(f"Collected {page_links_count} links from Page {page_num}")
                
                # Check if we hit an empty page (meaning we finished all available pages)
                if page_links_count == 0:
                    print("Hit an empty page. Resetting tracker to page 1 for the next cycle.")
                    Path(PAGE_TRACKER_FILE).write_text("1")
                    break

                if page_num < end_page - 1:
                    await asyncio.sleep(3)

        finally:
            await browser.close()

    return all_links


async def send_to_discord(new_links):
    api = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
    headers = {"Authorization": f"Bot {TOKEN}"}

    async with aiohttp.ClientSession() as session:
        for link in reversed(new_links):
            payload = {"content": f"New image:\n{link}"}
            async with session.post(api, json=payload, headers=headers) as resp:
                if resp.status in (200, 201):
                    print("Posted:", link)
                    save_cache(link)
                else:
                    print("Discord error:", resp.status)
            await asyncio.sleep(2.0)


async def main():
    if not TOKEN or not CHANNEL_ID:
        raise ValueError("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID")

    seen = load_cache()
    start_page = get_and_update_start_page()
    print(f"--- Starting execution chunk: Pages {start_page} to {start_page + PAGES_PER_RUN - 1} ---")

    try:
        posts = await get_zerochan_posts(start_page)
        new_posts = [p for p in posts if p not in seen]
        print("Total New Items Found in this chunk:", len(new_posts))

        if new_posts:
            await send_to_discord(new_posts)
        else:
            print("No new updates in this page block.")

    except Exception as e:
        print("ERROR:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())
