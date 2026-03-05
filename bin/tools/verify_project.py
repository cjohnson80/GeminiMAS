import subprocess
from config import status

def execute(payload):
    status(f" [Verifying Code]...")
    checks = [
        ("Linting", "npm run lint"),
        ("TypeScript", "npx tsc --noEmit")
    ]
    results = []
    for name, cmd in checks:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=payload)
        if res.returncode != 0:
            results.append(f"{name} Failed:\n{res.stderr[:1000]}")
    return "Project is clean!" if not results else "\n".join(results)
