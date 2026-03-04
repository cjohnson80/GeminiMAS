import asyncio, json, os, subprocess, aiohttp, sys

sys.path.append(os.path.expanduser('~/GeminiMAS_Repo/bin'))
from gemini_mas import env_caps, processing_engine

async def notify_admin(text):
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    admin_id = os.getenv('TELEGRAM_USER_ID')
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with aiohttp.ClientSession() as session:
        await session.post(url, json={"chat_id": admin_id, "text": text})

async def main():
    startup_msg = f"System Online. AVX: {env_caps['avx']}. Engine: {processing_engine}."
    await notify_admin(startup_msg)
    # ... rest of gateway loop ...

if __name__ == '__main__':
    asyncio.run(main())