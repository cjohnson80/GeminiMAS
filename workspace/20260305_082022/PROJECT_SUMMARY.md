# Project Scratchpad

Goal: Research latest AI agent patterns and Next.js/TS coding standards. Store findings in /home/chrisj/gemini_agents/knowledge and then use CoreEvolver to propose improvements to gemini_mas.py.

## Acceptance Criteria
# Acceptance Criteria: Research & Core Evolution

## 1. AI Agent Pattern Research
- [ ] **Deliverable:** Create a markdown file named `knowledge/ai_agent_patterns_2024.md`.
- [ ] **Content Requirements:**
    - Must document at least **three** distinct agent architectures (e.g., ReAct, Plan-and-Solve, Multi-Agent Orchestration).
    - Must include a specific section on "Self-Correction/Reflection" mechanisms.
    - Must evaluate applicability to the current `gemini_mas.py` architecture.

## 2. Next.js & TypeScript Standards Research
- [ ] **Deliverable:** Create a markdown file named `knowledge/nextjs_ts_standards_2024.md`.
- [ ] **Content Requirements:**
    - Must define strict rules for **App Router** directory structure.
    - Must specify best practices for **Server Actions** and data fetching.
    - Must define TypeScript strictness guidelines (e.g., `noImplicitAny`, Zod validation).
    - Must include a "Golden Sample" code snippet for a UI component.

## 3. Knowledge Base Persistence
- [ ] **Verification:** Ensure both files are saved in the absolute path `/home/chrisj/gemini_agents/knowledge/`.
- [ ] **Format:** Files must be valid Markdown and readable by the system's indexing tools.

## 4. CoreEvolver Improvement Proposal
- [ ] **Action:** Analyze the current `bin/gemini_mas.py` source code against the findings in `ai_agent_patterns_2024.md`.
- [ ] **Deliverable:** Create a proposal file named `knowledge/gemini_mas_evolution_proposal.md`.
- [ ] **Content Requirements:**
    - Identify **two** specific areas (classes or functions) in `gemini_mas.py` for refactoring.
    - Propose concrete code changes to implement a new pattern (e.g., adding a dedicated *Reflection* step or asynchronous *Memory* management).
    - **Constraint Check:** Explicitly state how the proposal adheres to the **Conservation Principle** (ensuring no existing features are deleted, only disabled or enhanced).

## 5. Version Control
- [ ] **Git State:** All new files must be committed to a new feature branch named `research/agent-patterns`.

## Architecture
(To be defined by Architect)
