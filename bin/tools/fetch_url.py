import urllib.request
import urllib.error

def execute(payload):
    req = urllib.request.Request(payload, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return response.read().decode('utf-8')[:10000]
