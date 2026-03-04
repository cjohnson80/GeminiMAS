# Active Goals
- [ ] **EVOLUTION PROTOCOL:** Examine your source code in `~/GeminiMAS_Repo/bin/`. Invent a new lightweight feature or optimization. 
      1. Use `run_shell` to `cd ~/GeminiMAS_Repo` and run `git checkout -b upgrade-feature-name`.
      2. Use `write_file` or `run_shell` to implement the feature in the code.
      3. Use `run_shell` to `git add .`, `git commit -m "Auto-Upgrade: [Feature]"`, and `git push origin HEAD`.
      4. Use the `notify_telegram` tool to send a summary of the upgrade to the user, instructing them to reply with `/approve [branch_name]`.
