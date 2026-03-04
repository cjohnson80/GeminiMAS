import json
import time
import os

CACHE_FILE = "/tmp/api_cache.json"

def get_cache(key):
    if not os.path.exists(CACHE_FILE): return None
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
        if key in cache and cache[key]["exp"] > time.time():
            return cache[key]["data"]
    return None

def set_cache(key, data, ttl=300):
    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
    cache[key] = {"data": data, "exp": time.time() + ttl}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)
