# Next.js Coding Agent Architecture

## 1. Core Philosophy
- **Performance First**: Optimize for Intel Celeron (minimal memory footprint).
- **App Router Priority**: Prefer Server Components for data fetching; use Client Components only for interactivity.
- **Type Safety**: Enforce strict TypeScript interfaces for all data-fetching layers.

## 2. Directory Structure
- `/app`: App Router routing and page layouts.
- `/components`: Atomic component design (UI, Features, Layouts).
- `/lib`: Server-side utilities, API wrappers, and database clients.
- `/hooks`: Client-side state management.

## 3. System Instructions
- Always prioritize `async/await` patterns in Server Components.
- Use `revalidatePath` and `revalidateTag` for ISR/Cache management.
- Avoid heavy client-side libraries; prefer native Web APIs where possible.

## 4. Tool Requirements
- `verify_project`: Must run `eslint` and `tsc --noEmit` before any commit.
- `read_file`: Must be used to audit `layout.tsx` before modifying routing structures.
- `write_file`: Must be used with atomic updates to prevent corruption on low-resource storage.