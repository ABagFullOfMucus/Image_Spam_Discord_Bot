import os
import sys
import aiohttp
import xml.etree.ElementTree as ET
import asyncio

# Retrieve secrets securely from GitHub Actions Environment
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID"))
SEARCH_TAG = os.getenv("SEARCH_TAG", "Satono+Diamond")

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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GHActionBot/3.0"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    print(f"Failed to fetch Zerochan feed: HTTP {response.status}")
                    return
                xml_data = await response.text()

        root = ET.fromstring(xml_data)
        new_items = []

        for item in root.findall(".//item"):
            img_link = item.find("link").text
            if img_link not in seen_images:
                new_items.append(img_link)

        # If it's a brand new repo setup and cache is empty, seed it so it doesn't spam history
        if not seen_images:
            print("First run detected. Seeding cache file with current feed to prevent spam.")
            for link in new_items:
                save_to_cache(link)
            return

        if new_items:
            print(f"Found {len(new_items)} new images! Sending to Discord...")
            
            # Using raw aiohttp webhook execution or a lightweight bot client initialization
            # Since GitHub Actions runs as a short script, a standard Webhook execution is cleanest.
            # However, since you have a Bot Token, we use a basic HTTP POST to Discord's channel endpoint:
            channel_url = f"https://discord.com/api/v10/channels/{CHANNEL_ID}/messages"
            auth_headers = {"Authorization": f"Bot {TOKEN}"}

            for link in reversed(new_items):
                payload = {"content": f"🚨 **New upload spotted!** 🚨\n{link}"}
                async with aiohttp.ClientSession() as session:
                    async with session.post(channel_url, json=payload, headers=auth_headers) as resp:
                        if resp.status == 200 or resp.status == 201:
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