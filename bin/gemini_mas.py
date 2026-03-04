import os, psutil, hashlib

def resource_guard():
    if psutil.virtual_memory().percent > 90:
        os.system('renice -n 19 -p ' + str(os.getpid()))

def heartbeat_daemon():
    # Hash check optimization
    current_hash = hashlib.md5(open('/home/chrisj/gemini_agents/core/HEARTBEAT.md', 'rb').read()).hexdigest()
    if current_hash != getattr(heartbeat_daemon, 'last_hash', None):
        heartbeat_daemon.last_hash = current_hash
        return True
    return False

def triage_lite(task):
    # Resource-aware triage
    if psutil.virtual_memory().percent > 85:
        return 'CHAT_LITE'
    return 'PROCESS'