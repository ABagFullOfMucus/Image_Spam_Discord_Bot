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
    url = f"https://www.zerochan.net/{SEARCH_TAG}?rss"
    
    # Using a clean browser agent header to prevent Zerochan from serving blocked responses
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(f"Zerochan Server Response Code: {response.status}")
                if response.status != 200:
                    print(f"Failed to fetch Zerochan feed: HTTP {response.status}")
                    return
                raw_content = await response.text()

        # Debug: Print a tiny snippet of the source code to the GitHub log so you can see it
        print("--- SOURCE SNIPPET START ---")
        print(raw_content[:1000])
        print("--- SOURCE SNIPPET END ---")

        # Capture any link matching zerochan.net followed purely by digits
        # This matches <link>, <guid>, and standard text blocks!
        raw_links = re.findall(r"https://www\.zerochan\.net/\d+", raw_content)
        
        # Filter and clean up the found links
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
            print(f"Sending {len(new_items)} images to Discord...")
            channel_url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
            auth_headers = {"Authorization": f"Bot {TOKEN}"}

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
            print("No new images to post right now.")

    except Exception as e:
        print(f"An error occurred in main logic: {e}")

if __name__ == "__main__":
    asyncio.run(main())
