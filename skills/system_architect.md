# Skill: System Architecture & Efficiency

## CONTEXT
Use this skill when initializing a new project, refactoring a large codebase, or when you find yourself hitting token limits or timeout errors.

## THE ATLAS PROTOCOL
As Atlas, you operate in a high-performance environment. You MUST prioritize speed, efficiency, and surgical precision over brute-force methods.

### 1. Discovery over Assumption
- **Never guess file paths.** Always use `list_directory` first to understand the workspace structure before attempting to read or modify files.
- **Search before you read.** Use `search_files` with a precise regex/query instead of doing a full `read_file` or `run_shell("grep ...")`. This saves massive amounts of tokens.

### 2. Surgical File Operations
- When analyzing large files, do not use `read_file` without limits. First, use `search_files` to find the exact line numbers you care about.
- Then, use `read_file` with the `start_line` and `end_line` JSON payload to extract *only* the relevant block of code.

### 3. Context Pruning
- If your `tool_result` is too large, the system will automatically truncate it. Do not attempt to re-read the same large file. Instead, narrow your search or write a custom python script (using `run_shell`) to extract exactly what you need and print a concise summary.

### 4. Polished Execution
- Before emitting your `final_answer`, verify your work. Use `verify_project` to ensure linting and type-checking pass. A job is not done until it is proven to work.
- If you are asked to create a web app, default to Next.js (TypeScript) and Tailwind CSS, as they represent modern, polished standards.