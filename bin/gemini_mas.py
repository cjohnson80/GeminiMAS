__version__ = '0.1.1'

import time
import functools
import urllib.error
import urllib.request
import json
import os
import argparse
import sys
import subprocess

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
    def __init__(self, api_key=None, model='gemini-3.5-pro-preview'):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY')
        self.model = model.replace('models/', '')
        self.base_url = 'https://generativelanguage.googleapis.com/v1beta/models/'

    @retry_with_backoff()
    def generate(self, prompt, system_instruction=None):
        if not self.api_key:
            return "Error: GEMINI_API_KEY not found."
        url = f'{self.base_url}{self.model}:generateContent?key={self.api_key}'
        payload = {'contents': [{'parts': [{'text': prompt}]}]}
        if system_instruction: payload['systemInstruction'] = {'parts': [{'text': system_instruction}]}
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=90) as response:
            return json.loads(response.read().decode('utf-8'))['candidates'][0]['content']['parts'][0]['text']

def run_heartbeat():
    # Evolution Protocol: Logic placeholder for internal self-improvement
    print("[*] Heartbeat running. Checking for codebase optimizations...")

    # Simple check for disk space as a "heartbeat" task
    try:
        usage = subprocess.check_output(['df', '-h', '/']).decode()
        print(f"[*] System Health Check:\n{usage}")
    except Exception as e:
        print(f"[!] Error during health check: {e}")

def run_repl():
    print(f"GeminiMAS Core v{__version__} - Interactive Terminal Interface")
    print("Type 'exit' or 'quit' to leave.\n")
    client = GeminiClient()

    # Basic conversation history (last 5 exchanges to save tokens/memory on Celeron)
    history = []

    while True:
        try:
            prompt = input("gagent> ").strip()
            if not prompt: continue
            if prompt.lower() in ['exit', 'quit']: break

            # Simple context management
            full_prompt = "\n".join(history + [prompt])
            response = client.generate(full_prompt)
            print(f"\n{response}\n")

            history.append(f"User: {prompt}")
            history.append(f"Assistant: {response}")
            if len(history) > 10: history = history[-10:]

        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}\n")

def main():
    parser = argparse.ArgumentParser(description='GeminiMAS Core Engine')
    subparsers = parser.add_subparsers(dest='command')
    subparsers.add_parser('heartbeat')

    # Allow prompt as positional argument OR via --prompt
    parser.add_argument('positional_prompt', nargs='?', type=str, help='The prompt to send to Gemini')
    parser.add_argument('--prompt', type=str, help='The prompt to send to Gemini (alternative)')

    args = parser.parse_args()

    if args.command == 'heartbeat':
        run_heartbeat()
    else:
        prompt = args.prompt or args.positional_prompt
        if prompt:
            client = GeminiClient()
            print(client.generate(prompt))
        elif not sys.stdin.isatty():
            # If piped input, read from stdin
            piped_prompt = sys.stdin.read().strip()
            if piped_prompt:
                client = GeminiClient()
                print(client.generate(piped_prompt))
            else:
                parser.print_help()
        else:
            # Interactive terminal if no args and is a TTY
            run_repl()

if __name__ == '__main__':
    main()
