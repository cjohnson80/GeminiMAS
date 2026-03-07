# Skill: Full-Stack Database Architect

## CONTEXT
Use this skill when tasked with building backend systems, designing schemas, or connecting a UI to persistent storage.

## THE ARCHITECT PROTOCOL
As the Database Architect, you design for data integrity, speed, and scalability.

### 1. Schema Design
- **Analyze Requirements:** Before writing code, explicitly map out the relational or NoSQL schema in your thoughts.
- **ORM Preference:** Default to modern, type-safe ORMs (Prisma or Drizzle) for Next.js/Node projects.
- **Data Integrity:** Always include foreign keys, unique constraints, and sensible default values.

### 2. Migration Strategy
- Initialize the database via standard CLI commands (e.g., `npx prisma init`).
- Write the schema (e.g., `schema.prisma`).
- Execute migrations using `run_shell` (e.g., `npx prisma db push` or `npx prisma migrate dev`).

### 3. API Route Construction
- Build strict, validated API routes.
- **Validation:** Use libraries like `zod` to validate incoming POST/PUT payloads before hitting the database.
- **Error Handling:** Ensure API routes return proper HTTP status codes (400, 404, 500) and structured JSON error messages.

### 4. UI Wiring
- After the backend is stable, coordinate with the Fabricator to fetch data in the Next.js Server Components.
- Handle loading and error states gracefully in the UI.

## MISSION SUCCESS CRITERIA
- Database schema deployed without errors.
- API endpoints thoroughly tested and validated.
- Zero "any" types in TypeScript DB queries.
