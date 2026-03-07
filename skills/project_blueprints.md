# Skill: Foundational Project Blueprints

## CONTEXT
Use this skill when tasked with creating a completely new project (e.g., "Build a new SaaS app", "Start a CRM").

## THE BLUEPRINT PROTOCOL
Atlas does not scaffold projects from a blank state. To maintain NextStepDigital's high-quality standards, we use verified "Foundations" (Blueprints) stored in `library/blueprints`.

### 1. Blueprint Selection
- Check what blueprints are available by listing the `library/blueprints` directory or using the `search_vault` tool with blueprint keywords.
- Examples of Blueprints might include:
  - `nextjs_saas_foundation`: Includes Auth, Stripe, Tailwind, and a standard dashboard layout.
  - `marketing_site_core`: Includes Hero, Testimonials, Framer Motion animations, and a contact form.

### 2. Cloning the Foundation
- Use the `clone_blueprint` tool to copy a foundational blueprint into your current workspace.
- Provide the name of the blueprint and the target destination.

### 3. Customization & Assembly
- Once the foundation is cloned, use the `Modular Assembly` skill to swap out components (e.g., replacing the default Hero with a specialized one from the vault).
- Modify the `tailwind.config.ts` or `globals.css` to match the client's branding.

### 4. Creating New Blueprints
- If you build a highly customized project that represents a completely new archetype (e.g., an AI Chatbot Interface), you can save the entire directory structure into `library/blueprints/` using bash commands (`cp -r`) so it becomes a new foundation for future missions.
