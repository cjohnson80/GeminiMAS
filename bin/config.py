import os
import json

AGENT_ROOT = os.path.expanduser("~/gemini_agents")
WORKSPACE = os.path.join(AGENT_ROOT, "workspace")
DB_FILE = os.path.join(AGENT_ROOT, "memory/memory.db")
SOUL_FILE = os.path.join(AGENT_ROOT, "core/SOUL.md")
HEARTBEAT_FILE = os.path.join(AGENT_ROOT, "core/HEARTBEAT.md")
CHAT_LOG = os.path.join(AGENT_ROOT, "logs/chat_history.jsonl")
LOCAL_CONFIG = os.path.join(AGENT_ROOT, "core/local_config.json")
SKILLS_DIR = os.path.join(AGENT_ROOT, "skills")

def read_local_config():
    default_cfg = {
        "max_threads": 2,
        "cache_size": "512MB",
        "model_overrides": {},
        "disabled_features": []
    }
    if not os.path.exists(LOCAL_CONFIG):
        return default_cfg
    try:
        with open(LOCAL_CONFIG, 'r') as f:
            cfg = json.load(f)
            for k, v in default_cfg.items():
                if k not in cfg: cfg[k] = v
            return cfg
    except: return default_cfg

def is_feature_enabled(feature_name):
    cfg = read_local_config()
    return feature_name not in cfg.get("disabled_features", [])

def toggle_feature(feature_name, enable=True):
    cfg = read_local_config()
    disabled = cfg.get("disabled_features", [])
    if enable and feature_name in disabled:
        disabled.remove(feature_name)
    elif not enable and feature_name not in disabled:
        disabled.append(feature_name)
    cfg["disabled_features"] = disabled
    write_local_config(cfg)
    return f"Feature '{feature_name}' is now {'enabled' if enable else 'disabled'}."

def write_local_config(config):
    with open(LOCAL_CONFIG, 'w') as f:
        json.dump(config, f, indent=4)

def status(msg):
    print(f"{msg}", end="", flush=True)

def read_file_safe(path):
    if not os.path.exists(path): return ""
    with open(path, 'r') as f: return f.read()

class ResourceGuard:
    @staticmethod
    def is_under_pressure():
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
                total = int([l.split()[1] for l in lines if 'MemTotal' in l][0])
                avail = int([l.split()[1] for l in lines if 'MemAvailable' in l][0])
                return (avail / total) < 0.15
        except: return False
