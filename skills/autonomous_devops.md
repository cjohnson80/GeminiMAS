# Skill: Autonomous DevOps & Deployment

## CONTEXT
Use this skill when a mission requires taking a project from local code to a live production URL. This is an Elite Level operation.

## THE DEPLOYMENT PROTOCOL
As the Atlas Swarm Lead, you are responsible for the entire delivery lifecycle. Do not wait for the Operator to handle infrastructure.

### 1. Pre-Deployment Verification
- Before any deployment, you MUST run `verify_project`.
- If linting or build checks fail, you MUST fix the code before proceeding.
- Ensure all environment variables required by the project are documented.

### 2. Version Control (Git)
- Initialize a git repository if one doesn't exist.
- Use meaningful commit messages: `feat: initial architecture`, `fix: layout padding`, `deploy: production v1.0.0`.
- If a GitHub token is available, use `create_github_repo` to provision remote hosting.

### 3. Production Deployment (Vercel)
- Use the `deploy_vercel` tool to push the project to production.
- **Workflow:**
  1. Navigate to the project directory.
  2. Execute `deploy_vercel`.
  3. Capture the production URL from the output.
- If the deployment fails, read the logs using `run_shell`, diagnose the error, and push a fix.

### 4. Post-Deployment Audit
- Once the URL is live, use `visual_verify` on the production URL.
- Ensure the live site matches the local development state.
- Hand over the final URL to the Operator with a "Mission Success" report.

## MISSION SUCCESS CRITERIA
- 0% Human intervention in the deployment process.
- Code is verified and linted before hitting production.
- A working, high-performance URL is delivered to the Lead.
