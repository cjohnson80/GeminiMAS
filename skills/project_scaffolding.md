# Skill: Project Scaffolding (Atlas v9.0)

## CONTEXT
Use this skill when initializing a new mission in the Atlas workspace.

## THE SCAFFOLDING PROTOCOL
All scaffolding must occur strictly within the designated **Mission Space**.

### 1. Workspace Target
- Identify the target: `workspace/{project_name}/`.
- If the directory does not exist, create it: `mkdir -p workspace/{project_name}`.
- All subsequent commands (`npm init`, `mkdir`, etc.) MUST be prefixed with `cd workspace/{project_name} && ...`.

### 2. Standard Next.js Structure
Atlas defaults to Next.js 15+ with the App Router.
- `src/app/`: Routes and global layouts.
- `src/components/`: Reusable React components (subdivided: `/ui`, `/modules`).
- `src/lib/`: Shared utilities and DB clients.
- `src/hooks/`: Custom React hooks.
- `src/types/`: Strict TypeScript definitions.
- `public/`: Static assets.

### 3. Execution Steps
1. **Initialize:** `npm init -y` and install `next@latest`, `react@latest`, `react-dom@latest`, `typescript`, `tailwindcss`, `postcss`, `autoprefixer`.
2. **Configure:** Initialize Tailwind (`npx tailwindcss init -p`) and create a standard `tsconfig.json`.
3. **Blueprint Check:** Before building manually, check `library/blueprints/` to see if a matching foundation exists.
4. **Validation:** Run `npm run dev` and use `test_service` to verify the local environment is UP.

## MISSION COMPLETION
Report the workspace path and the local development URL to the Lead.
- Example: "Mission [Project Name] initialized in `workspace/{project_name}`. Dev server live at http://localhost:3000."
