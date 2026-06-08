import os
import re
import asyncio
from pathlib import Path
import aiohttp
from playwright.async_api import async_playwright

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = os.getenv("DISCORD_CHANNEL_ID")
SEARCH_TAG = os.getenv("SEARCH_TAG", "Satono+Diamond")

# Adjust this number to decide how many pages to scan per run
PAGES_TO_SCRAPE = int(os.getenv("PAGES_TO_SCRAPE", "3"))
CACHE_FILE = "posted.txt"


def load_cache():
    if not Path(CACHE_FILE).exists():
        return set()

    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def save_cache(link):
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")


async def scrape_single_page(page, url):
    """Scrapes a single page and extracts Zerochan links."""
    print(f"Scraping target: {url}")
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)  # Gentle delay to let elements settle
        
        anchors = await page.locator("a").evaluate_all(
            "elements => elements.map(e => e.href)"
        )
        return anchors
    except Exception as e:
        print(f"Failed to scrape {url}: {repr(e)}")
        return []


async def get_zerochan_posts():
    all_links = []

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
            # Loop through the pages (Page 1 up to PAGES_TO_SCRAPE)
            for page_num in range(1, PAGES_TO_SCRAPE + 1):
                # Page 1 works fine without ?p=1, but adding it explicitly keeps the loop clean
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
                
                print(f"Collected {page_links_count} unique links from Page {page_num}")
                
                # Sneak in a tiny rest between pages so Zerochan stays happy
                if page_num < PAGES_TO_SCRAPE:
                    await asyncio.sleep(2)

        finally:
            await browser.close()

    print(f"Total unique links extracted across all pages: {len(all_links)}")
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
                    text = await resp.text()
                    print("Discord error:", resp.status, text)

            await asyncio.sleep(1.5)


async def main():
    if not TOKEN or not CHANNEL_ID:
        raise ValueError("Missing DISCORD_TOKEN or DISCORD_CHANNEL_ID")

    seen = load_cache()

    try:
        posts = await get_zerochan_posts()
        print("Grand Total Found:", len(posts))

        new_posts = [p for p in posts if p not in seen]
        print("Total New Items to Post:", len(new_posts))

        if new_posts:
            await send_to_discord(new_posts)
        else:
            print("No updates across monitored pages.")

    except Exception as e:
        print("ERROR:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())
