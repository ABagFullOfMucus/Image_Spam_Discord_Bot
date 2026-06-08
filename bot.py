import os
import sys
import aiohttp
import asyncio
import urllib.parse

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
    
    # Target Zerochan target URL
    target_feed = f"https://www.zerochan.net/{SEARCH_TAG}?rss"
    # Safely encode it to pass through the JSON proxy pipeline
    encoded_feed = urllib.parse.quote_plus(target_feed)
    
    # Requesting via the API gateway mirror to slip past Cloudflare filters smoothly
    proxy_url = f"https://api.rss2json.com/v1/api.json?rss_url={encoded_feed}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(proxy_url) as response:
                print(f"Proxy Gateway Response Code: {response.status}")
                if response.status != 200:
                    print(f"Failed to reach the feed mirror: HTTP {response.status}")
                    return
                
                data = await response.json()

        if data.get("status") != "ok":
            print(f"Mirror returned an error: {data.get('message', 'Unknown error')}")
            return

        items = data.get("items", [])
        print(f"Total entries downloaded from feed provider: {len(items)}")

        # Extract post links from the JSON payload structure
        unique_links = []
        for item in items:
            link = item.get("link", "")
            if "zerochan.net" in link:
                # Strip out any lingering query tags for a cleaner look
                clean_link = link.split('?')[0]
                if clean_link not in unique_links:
                    unique_links.append(clean_link)

        new_items = []
        for img_link in unique_links:
            if img_link not in seen_images:
                new_items.append(img_link)

        print(f"New images ready to distribute: {len(new_items)}")

        if new_items:
            print(f"Pushing updates to Discord channel {CHANNEL_ID}...")
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
            print("No new content found to distribute at this moment.")

    except Exception as e:
        print(f"An exception occurred inside the workflow runtime: {e}")

if __name__ == "__main__":
    asyncio.run(main())
