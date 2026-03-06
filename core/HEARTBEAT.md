# Active Goals
- [x] **RESEARCH SWARM (24h):** Researches latest AI updates and Next.js/TS patterns. 
      1. Use AIScout to research LLM/Agentic trends.
      2. Use FrameworkScout to research Next.js/TypeScript best practices.
      3. Save findings to knowledge/ folder.
      4. Use CoreEvolver to propose code upgrades to the repository.

- [x] **EVOLUTION PROTOCOL (GLOBAL):** Examine your source code in `$REPO_ROOT/bin/`. Invent a new lightweight feature or optimization for ALL machines.
      1. Use `run_shell` to `cd $REPO_ROOT`.
      2. Create a unique branch: `git checkout -b evolution-$CURRENT_MACHINE-$(date +%s)`.
      3. Implement the feature. **Mandate:** DO NOT delete existing features.
      4. Use `run_shell` to `git add .`, `git commit -m "Global Optimization: [Feature Description]"`, and `git push origin HEAD`.
      5. Notify the user via Telegram for approval.

- [x] **EVOLUTION PROTOCOL (LOCAL):** Optimize your performance for this specific machine (`$CURRENT_MACHINE`).
      1. If you need to stop using a feature (e.g., too much RAM), update the `disabled_features` list in `$AGENT_ROOT/core/local_config.json`.
      2. DO NOT delete the code for that feature from the repo.
