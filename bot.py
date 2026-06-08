import os
import sys
import aiohttp
import re
import asyncio

# Retrieve secrets securely from GitHub Actions Environment
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
SEARCH_TAG = os.getenv("SEARCH_TAG", "Hatsune+Miku")

CACHE_FILE = "posted.txt"

def load_cached_links():
    """Loads previously posted links from the repository text file."""
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_to_cache(link):
    """Appends a newly posted link to the local text file."""
    with open(CACHE_FILE, "a") as f:
        f.write(f"{link}\n")

async def main():
    if not TOKEN or not CHANNEL_ID:
        print("Missing environment variables: DISCORD_TOKEN or DISCORD_CHANNEL_ID")
        sys.exit(1)

    seen_images = load_cached_links()
    url = f"https://www.zerochan.net/{SEARCH_TAG}?rss"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GHActionBot/4.0"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    print(f"Failed to fetch Zerochan feed: HTTP {response.status}")
                    return
                raw_html_xml = await response.text()

        # Match any <link>https://www.zerochan.net/XXXXXX</link> format cleanly using Regex
        # This completely avoids using strict XML tree parsers that crash on broken tags.
        raw_links = re.findall(r"<link>(https://www\.zerochan\.net/\d+)</link>", raw_html_xml)
        
        # Deduplicate while preserving order
        unique_links = []
        for l in raw_links:
            if l not in unique_links:
                unique_links.append(l)

        new_items = []
        for img_link in unique_links:
            if img_link not in seen_images:
                new_items.append(img_link)

        # Force Spam/Testing Override:
        # If your posted.txt is empty, we bypass the "first run safeguard" to make sure it works!
        if not seen_images:
            print(f"First run / empty cache detected. Testing mode active: sending {len(new_items)} images.")
            # If you don't want it to spam all existing images right now, uncomment the lines below:
            # for link in new_items:
            #     save_to_cache(link)
            # return

        if new_items:
            print(f"Found {len(new_items)} images to process! Sending to Discord...")
            
            channel_url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
            auth_headers = {"Authorization": f"Bot {TOKEN}"}

            # Loop through images chronologically (oldest to newest)
            for link in reversed(new_items):
                payload = {"content": f"🚨 **New upload spotted!** 🚨\n{link}"}
                async with aiohttp.ClientSession() as session:
                    async with session.post(channel_url, json=payload, headers=auth_headers) as resp:
                        if resp.status in (200, 201):
                            save_to_cache(link)
                            print(f"Successfully posted: {link}")
                        else:
                            print(f"Failed to post to Discord: HTTP {resp.status}")
                await asyncio.sleep(1.5)
        else:
            print("No new images found.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
