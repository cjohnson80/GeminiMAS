# Next.js Scaffolding Blueprint (v1.0)

When starting a new Next.js project, always use the following structure:
- `/app`: Files for routes and layouts (App Router).
- `/components`: Reusable UI components (subdivided into /ui, /forms, /layout).
- `/lib`: Shared utilities, database clients, and server-side logic.
- `/hooks`: Custom React hooks.
- `/types`: TypeScript interfaces and type definitions.
- `/public`: Static assets.

**Steps for Scaffolding:**
1. Check if `package.json` exists. If not, run `npm init -y` and install `next`, `react`, `react-dom`, and `typescript`.
2. Create the folder structure using `mkdir -p`.
3. Set up `tsconfig.json` and `next.config.mjs`.
4. Use `npm run dev` to verify the environment.
5. Report the local URL (usually http://localhost:3000) to the user.
