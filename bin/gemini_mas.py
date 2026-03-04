__version__ = '0.1.0'

import time
import functools
import urllib.error
import urllib.request
import json
import os
import argparse
import sys

# Hardware Optimization: Using standard libs only to minimize memory footprint on Celeron
def retry_with_backoff(retries=4, backoff_in_seconds=5):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x < retries:
                        time.sleep(backoff_in_seconds * (2 ** x))
                        x += 1
                        continue
                    raise e
        return wrapper
    return decorator

class GeminiClient:
    def __init__(self, api_key=None, model='gemini-3.1-flash-lite-preview'):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        self.model = model.replace('models/', '')
        self.base_url = 'https://generativelanguage.googleapis.com/v1beta/models/'

    @retry_with_backoff()
    def generate(self, prompt, system_instruction=None):
        url = f'{self.base_url}{self.model}:generateContent?key={self.api_key}'
        payload = {'contents': [{'parts': [{'text': prompt}]}]}
        if system_instruction: payload['systemInstruction'] = {'parts': [{'text': system_instruction}]}
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=90) as response:
            return json.loads(response.read().decode('utf-8'))['candidates'][0]['content']['parts'][0]['text']

def run_heartbeat():
    # Evolution Protocol: Logic placeholder for internal self-improvement
    print("[*] Heartbeat running. Checking for codebase optimizations...")

def main():
    parser = argparse.ArgumentParser(description='GeminiMAS Core Engine')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('heartbeat')
    parser.add_argument('--prompt', type=str)
    args = parser.parse_args()

    if args.command == 'heartbeat':
        run_heartbeat()
    elif args.prompt:
        client = GeminiClient()
        print(client.generate(args.prompt))

if __name__ == '__main__':
    main()
