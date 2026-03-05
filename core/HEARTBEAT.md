# Active Goals
- [ ] **EVOLUTION PROTOCOL (GLOBAL):** Examine your source code in `$REPO_ROOT/bin/`. Invent a new lightweight feature or optimization for ALL machines.
      1. Use `run_shell` to `cd $REPO_ROOT`.
      2. Create a unique branch: `git checkout -b evolution-$CURRENT_MACHINE-$(date +%s)`.
      3. Implement the feature. **Mandate:** DO NOT delete existing features.
      4. Validate the code by running `python3 -m py_compile bin/*.py bin/tools/*.py`. Ensure it passes before committing.
      5. Use `run_shell` to `git add .` and `git commit -m "Global Optimization: [Feature Description]"`.
      6. Use `gh pr create --title "Evolution: [Feature Description]" --body "Automated evolution update."` to create a Pull Request instead of pushing directly.
      7. Notify the user via Telegram for approval.

- [ ] **EVOLUTION PROTOCOL (LOCAL):** Optimize your performance for this specific machine (`$CURRENT_MACHINE`).
      1. If you need to stop using a feature (e.g., too much RAM), update the `disabled_features` list in `$AGENT_ROOT/core/local_config.json`.
      2. DO NOT delete the code for that feature from the repo.

- [ ] **EVOLUTION PROTOCOL (IDENTITY):** Periodically analyze failures to improve yourself.
      1. Query DuckDB memory for tasks with a low `success_score`.
      2. Identify the root cause of these failures.
      3. Append a new constraint, rule, or learned lesson to `$AGENT_ROOT/core/SOUL.md` to prevent future occurrences.