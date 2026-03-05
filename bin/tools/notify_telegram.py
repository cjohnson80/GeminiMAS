import os
import json
import urllib.request

def execute(payload):
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_USER_ID")
    if not bot_token or not chat_id: return "Telegram credentials missing."
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    req = urllib.request.Request(url, data=json.dumps({"chat_id": chat_id, "text": f"[Evolution Protocol]\n{payload}"}).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req)
    return "Telegram notification sent."
