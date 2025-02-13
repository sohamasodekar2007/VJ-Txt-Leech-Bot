import os
import re
import sys
import json
import asyncio
import requests
import logging
from aiohttp import ClientSession
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from vars import API_ID, API_HASH, BOT_TOKEN
from utils import progress_bar
import core as helper

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@bot.on_message(filters.command("start"))
async def start(bot: Client, m: Message):
    await m.reply_text(f"Hello {m.from_user.mention} 👋\n\nI am a bot to download files from your .txt links and upload them to Telegram.\n\nUse /upload to start.")

@bot.on_message(filters.command("stop"))
async def stop_handler(_, m):
    await m.reply_text("**Stopped** 🚦")
    os.execl(sys.executable, sys.executable, *sys.argv)

@bot.on_message(filters.command("upload"))
async def upload(bot: Client, m: Message):
    try:
        editable = await m.reply_text("Send a .txt file containing download links 🔗")
        input_file: Message = await bot.listen(editable.chat.id)
        file_path = await input_file.download()
        await input_file.delete()

        # Read links from the file
        with open(file_path, "r") as f:
            links = [line.strip() for line in f if line.strip()]
        os.remove(file_path)

        if not links:
            await m.reply_text("No valid links found in the file.")
            return

        await editable.edit(f"**Total links found:** {len(links)}\nEnter starting position (default = 1)")
        input_start: Message = await bot.listen(editable.chat.id)
        start_pos = int(input_start.text) if input_start.text.isdigit() else 1
        await input_start.delete()

        await editable.edit("Enter batch name:")
        input_batch: Message = await bot.listen(editable.chat.id)
        batch_name = input_batch.text.strip()
        await input_batch.delete()

        await editable.edit("Enter resolution (144, 240, 360, 480, 720, 1080):")
        input_res: Message = await bot.listen(editable.chat.id)
        resolution = input_res.text.strip()
        await input_res.delete()

        res_map = {"144": "256x144", "240": "426x240", "360": "640x360", "480": "854x480", "720": "1280x720", "1080": "1920x1080"}
        res_choice = res_map.get(resolution, "UN")

        await editable.edit("Enter a caption for the uploaded files:")
        input_caption: Message = await bot.listen(editable.chat.id)
        caption = input_caption.text.strip()
        await input_caption.delete()

        await editable.edit("Send thumbnail URL or type 'no' to skip:")
        input_thumb: Message = await bot.listen(editable.chat.id)
        thumb_url = input_thumb.text.strip()
        await input_thumb.delete()
        thumb_path = "thumb.jpg" if (thumb_url.lower() != "no" and thumb_url.startswith("http")) else None

        if thumb_path:
            os.system(f"wget '{thumb_url}' -O '{thumb_path}'")
        
        await editable.edit("**Starting downloads...**")
        
        count = start_pos
        for link in links[start_pos-1:]:
            try:
                if "visionias" in link:
                    async with ClientSession() as session:
                        async with session.get(link) as resp:
                            text = await resp.text()
                            link = re.search(r"(https://.*?playlist.m3u8.*?)\"", text).group(1)
                
                file_name = f"{str(count).zfill(3)}_{batch_name}.mp4"
                download_cmd = f"yt-dlp -f 'b[height<={res_choice}]' -o '{file_name}' '{link}'"
                os.system(download_cmd)
                
                await bot.send_document(m.chat.id, document=file_name, caption=caption, thumb=thumb_path)
                os.remove(file_name)
                count += 1
            except FloodWait as e:
                await asyncio.sleep(e.x)
            except Exception as e:
                logging.error(f"Error downloading {link}: {e}")

        await m.reply_text("✅ **All downloads completed!**")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await m.reply_text("❌ An error occurred during the process.")

bot.run()
