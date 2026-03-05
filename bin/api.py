import json
import os
import urllib.request
import urllib.error
import base64
import mimetypes

class GeminiClient:
    def __init__(self, api_key, model="gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model.replace("models/", "")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models/"

    def generate(self, prompt, system_instruction=None, json_mode=False, history=None, images=None):
        url = f"{self.base_url}{self.model}:generateContent?key={self.api_key}"
        contents = []
        if history:
            for h in history: contents.append({"role": h["role"], "parts": [{"text": h["text"]}]})

        parts = [{"text": prompt}]
        if images:
            for img_path in images:
                if os.path.exists(img_path):
                    mime, _ = mimetypes.guess_type(img_path)
                    with open(img_path, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                    parts.append({"inlineData": {"mimeType": mime or "image/jpeg", "data": data}})

        contents.append({"role": "user", "parts": parts})
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}
        }
        if system_instruction: payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        if json_mode: payload["generationConfig"]["responseMimeType"] = "application/json"

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                   headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result['candidates'][0]['content']['parts'][0]['text']
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            return f"API Error {e.code}: {err_body}"
        except Exception as e:
            return f"Error: {str(e)}"

    def generate_stream(self, prompt, system_instruction=None, history=None, images=None):
        url = f"{self.base_url}{self.model}:streamGenerateContent?key={self.api_key}"
        contents = []
        if history:
            for h in history: contents.append({"role": h["role"], "parts": [{"text": h["text"]}]})

        parts = [{"text": prompt}]
        if images:
            for img_path in images:
                if os.path.exists(img_path):
                    mime, _ = mimetypes.guess_type(img_path)
                    with open(img_path, "rb") as f:
                        data = base64.b64encode(f.read()).decode("utf-8")
                    parts.append({"inlineData": {"mimeType": mime or "image/jpeg", "data": data}})

        contents.append({"role": "user", "parts": parts})
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192}
        }
        if system_instruction: payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                   headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw_data = response.read().decode("utf-8")
                chunks = json.loads(raw_data)
                for chunk in chunks:
                    yield chunk['candidates'][0]['content']['parts'][0]['text']
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            yield f"API Error {e.code}: {err_body}"
        except Exception as e:
            yield f"Error: {str(e)}"

    def embed(self, text):
        url = f"{self.base_url}gemini-embedding-001:embedContent?key={self.api_key}"
        payload = {"model": "models/gemini-embedding-001", "content": {"parts": [{"text": text}]}}
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                   headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result['embedding']['values']
        except: return None
