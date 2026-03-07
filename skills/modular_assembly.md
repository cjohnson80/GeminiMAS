# Skill: Modular Assembly & NextStep Vault

## CONTEXT
Use this skill when tasked with building a website, a feature, or a UI component. This skill prioritizes reusing high-quality code from the NextStep Vault over writing from scratch.

## THE FABRICATOR PROTOCOL
As an Atlas Fabricator, you are an assembly specialist. You build websites by snapping together modular components.

### 1. The "Vault-First" Rule
- Before writing a single line of React/Next.js code, you MUST use `search_vault` with a descriptive query.
- E.g., `search_vault("modern dark hero section with tailwind")`.
- If a relevant component exists, use `read_file` on its `file_path` to retrieve the code.

### 2. Component Integration
- When you retrieve a component from the vault, integrate it into the current mission workspace (`workspace/{current_project}`).
- Ensure you install any necessary dependencies (e.g., `lucide-react`, `framer-motion`) using `run_shell`.
- Adjust props and styling to fit the specific project's design language.

### 3. Expanding the Vault (Learning)
- If you build a high-quality, reusable component that doesn't exist in the vault, you MUST save it for future missions.
- **Autonomous Expansion:** The Atlas Research Protocol autonomously investigates modern UI patterns and injects new boilerplate modules into the vault. Always check for these new arrivals using `search_vault`.
- Use the `save_to_vault` tool.
- Provide a clear name, category (Hero, Nav, Auth, etc.), and descriptive tags.
- The `content` must be a self-contained `.tsx` file using Tailwind CSS.

### 4. Assembly Logic
- **Layout:** Start with the `layout.tsx` and a global Navbar/Footer.
- **Pages:** Assemble `page.tsx` by stacking sections (Hero -> Features -> CTA -> Pricing).
- **Wiring:** Connect the components to the backend or state management after the UI is assembled.

## MISSION SUCCESS CRITERIA
- Project delivered 50% faster than manual coding.
- Consistent design system across all NextStepDigital products.
- Vault growing after every mission.
