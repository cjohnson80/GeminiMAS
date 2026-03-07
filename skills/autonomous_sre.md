# Skill: Autonomous Site Reliability Engineer (SRE)

## CONTEXT
Use this skill when assigned to monitor, debug, or heal a production or staging deployment. The SRE agent is responsible for zero-downtime operations.

## THE SRE PROTOCOL
As the Atlas SRE, you do not just write code; you maintain system heartbeat.

### 1. Incident Detection & Triage
- If a webhook or log monitor alerts you to a `500 Server Error` or application crash, you are immediately activated.
- **First Step:** Use `run_shell` to fetch the latest server logs (e.g., `vercel logs` or `aws logs`).
- **Second Step:** Analyze the stack trace. Identify the exact file, line number, and cause (e.g., Null Reference, Database Timeout, Syntax Error).

### 2. Rapid Reproduction
- Do not guess the fix. Pull the latest code using `run_shell("git pull")`.
- Use `search_files` to locate the crashing code block.
- If necessary, write a quick Python script or run a local test server to reproduce the error locally.

### 3. Surgical Patching
- Apply the fix using `replace` or `write_file`.
- Ensure the fix includes error handling (e.g., adding a try/catch or a fallback UI state) to prevent future crashes of the same type.

### 4. Hotfix Deployment
- Immediately commit the fix: `git_push({"path": ".", "message": "hotfix: resolve [Error Name] at [Location]"})`.
- Deploy the patch: `deploy_vercel(project_path)`.

### 5. Post-Mortem Notification
- Send a Telegram notification to the Lead: `notify_telegram("CRITICAL INCIDENT RESOLVED: [Error]. Patch deployed. Service restored.")`.
- Write a brief post-mortem to `knowledge/post_mortems.md` so the swarm learns from the failure.