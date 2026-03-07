import os
import time
import subprocess
import requests
import logging

# Configuration
BACKEND_URL = "http://localhost:8000/status"
FRONTEND_URL = "http://localhost:3000"
CHECK_INTERVAL = 60  # Check every minute
LOG_FILE = os.path.expanduser("~/atlas_agents/logs/sentinel.log")

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [SENTINEL] %(levelname)s: %(message)s'
)

def is_process_running(name):
    try:
        output = subprocess.check_output(["pgrep", "-f", name])
        return len(output) > 0
    except subprocess.CalledProcessError:
        return False

def check_url(url):
    try:
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except:
        return False

def heal():
    logging.warning("System degradation detected. Initiating automated recovery...")
    # Use the existing start_web.sh but detached
    try:
        subprocess.run(["/home/chrisj/atlas_agents/start_web.sh"], capture_output=True)
        # Manually ensure TG is up as well
        if not is_process_running("tg_gateway.py"):
            subprocess.Popen(["/home/chrisj/atlas_agents/venv/bin/python3", "/home/chrisj/atlas_agents/bin/tg_gateway.py"])
        logging.info("Recovery sequence complete. Systems operational.")
    except Exception as e:
        logging.error(f"Heal failed: {e}")

def monitor():
    logging.info("Atlas Sentinel active. Monitoring Swarm health...")
    while True:
        backend_up = check_url(BACKEND_URL)
        frontend_up = check_url(FRONTEND_URL)
        tg_up = is_process_running("tg_gateway.py")

        if not backend_up or not frontend_up or not tg_up:
            status = f"B:{'OK' if backend_up else 'FAIL'} F:{'OK' if frontend_up else 'FAIL'} T:{'OK' if tg_up else 'FAIL'}"
            logging.warning(f"Health Check Failed: {status}")
            heal()
            # Wait longer after a heal to let things settle
            time.sleep(30)
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        monitor()
    except Exception as e:
        logging.critical(f"Sentinel crashed: {e}")
