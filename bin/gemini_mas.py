import time
import functools
import urllib.error
import urllib.request
import json
import os
import threading
import argparse

def retry_with_backoff(retries=4, backoff_in_seconds=5):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except urllib.error.HTTPError as e:
                    if e.code == 503 and x < retries:
                        sleep_time = (backoff_in_seconds * (2 ** x))
                        time.sleep(sleep_time)
                        x += 1
                        continue
                    raise e
        return wrapper
    return decorator

class GeminiClient:
    def __init__(self, api_key, model="gemini-3.1-flash-lite-preview"):
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/"

    @retry_with_backoff(retries=4, backoff_in_seconds=5)
    def generate(self, prompt, system_instruction=None, json_mode=False):
        url = f"{self.base_url}{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}}
        if system_instruction: payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if json_mode: payload["generationConfig"]["responseMimeType"] = "application/json"
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))['candidates'][0]['content']['parts'][0]['text']