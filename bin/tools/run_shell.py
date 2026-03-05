import subprocess

def execute(payload):
    res = subprocess.run(payload, shell=True, capture_output=True, text=True, timeout=120)
    return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
