import psutil, json, os

def get_system_load():
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    return {'cpu': cpu, 'mem': mem}

if __name__ == '__main__':
    metrics = get_system_load()
    with open('/tmp/mas_load.json', 'w') as f:
        json.dump(metrics, f)
