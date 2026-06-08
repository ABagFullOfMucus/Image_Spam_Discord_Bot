import os
import sys
import aiohttp
import re
import asyncio

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
SEARCH_TAG = os.getenv("SEARCH_TAG", "Hatsune+Miku")

CACHE_FILE = "posted.txt"

def load_cached_links():
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def save_to_cache(link):
    with open(CACHE_FILE, "a") as f:
        f.write(f"{link}\n")

async def main():
    if not TOKEN or not CHANNEL_ID:
        print("Missing environment variables: DISCORD_TOKEN or DISCORD_CHANNEL_ID")
        sys.exit(1)

    seen_images = load_cached_links()
    
    # 1. Format the core target URL
    target_url = f"https://www.zerochan.net/{SEARCH_TAG}?rss"
    
    # 2. Use corsproxy.io to mask the GitHub cloud data center signature
    url = f"https://corsproxy.io/?{target_url}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"Proxy Response Code: {response.status}")
                if response.status != 200:
                    print(f"Failed to fetch RSS feed via proxy fallback. HTTP {response.status}")
                    return
                
                # corsproxy.io streams raw data transparently without an annoying JSON container
                raw_content = await response.text()

        # Look for explicit zerochan link patterns in the raw text stream
        raw_links = re.findall(r"https://www\.zerochan\.net/\d+", raw_content)
        
        unique_links = []
        for l in raw_links:
            if l not in unique_links:
                unique_links.append(l)

        new_items = []
        for img_link in unique_links:
            if img_link not in seen_images:
                new_items.append(img_link)

        print(f"Total Unique Image Links parsed from feed: {len(unique_links)}")
        print(f"New images not found in cache: {len(new_items)}")

        if new_items:
            print(f"Forwarding {len(new_items)} elements to Discord...")
            channel_url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
            auth_headers = {"Authorization": f"Bot {TOKEN}"}

            for link in reversed(new_items):
                payload = {"content": f"🚨 **New upload spotted!** 🚨\n{link}"}
                async with session.post(channel_url, json=payload, headers=auth_headers) as resp:
                    if resp.status in (200, 201):
                        save_to_cache(link)
                        print(f"Successfully posted: {link}")
                    else:
                        print(f"Failed to post to Discord: HTTP {resp.status}")
                await asyncio.sleep(1.5)
        else:
            print("Sync complete. No new updates to distribute.")

    except Exception as e:
        print(f"An unexpected runtime exception stopped execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())
