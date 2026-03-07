# Enterprise Next.js App Router & TypeScript Architecture Standards

## 1. Architectural Philosophy: Server-First
The App Router fundamentally shifts React from a client-side SPA model to a server-first paradigm.
- **Default to Server Components (RSC):** Every component is a Server Component unless explicitly marked with `'use client'`. Do not leak client boundaries upwards.
- **Push Client Boundaries Down:** Isolate state (`useState`), effects (`useEffect`), and browser APIs to the absolute lowest leaf nodes in your component tree.
- **Network Waterfalls:** Acknowledge them. Use `Promise.all` for parallel fetching or leverage `<Suspense>` to stream distinct UI chunks independently.

## 2. Uncompromising TypeScript (Strict Mode)
TypeScript is a compiler, not a linter. We enforce absolute type safety.
- **tsconfig.json:** Must include `"strict": true`, `"noImplicitAny": true`, `"strictNullChecks": true`.
- **Type vs Interface:** Use `interface` for object shapes and component props. Use `type` for unions, intersections, and utility types.
- **No `any`:** The use of `any` is strictly prohibited. Use `unknown` and type narrowing if the shape is truly dynamic.
- **Branded Types:** For domain-specific primitives (e.g., `type UserId = string & { readonly __brand: 'UserId' }`), use branded types to prevent accidental cross-assignment.

## 3. Data Fetching & State Caching
Next.js caching is a primary architectural pillar.
- **RSC Fetching:** Fetch data directly in Server Components using native `fetch`.
- **Request Memoization:** React automatically deduplicates `fetch` requests with the same URL and options during a single render pass. Do not manually cache these.
- **Data Cache:** Explicitly define cache behavior using `cache: 'force-cache'` (default) or `next: { revalidate: 3600 }`.
- **Server Actions:** Use Server Actions exclusively for mutations. Never use API routes (`route.ts`) for internal app mutations unless interacting with external webhooks.

## 4. Server Action Patterns
Server Actions must be treated as untrusted network boundaries.
- **Input Validation:** Every Server Action MUST validate its input using a schema validation library (e.g., Zod).
- **Return Signatures:** Return discriminated unions for predictable client-side error handling:
  ```typescript
  type ActionResponse<T> = 
    | { success: true; data: T }
    | { success: false; error: string; issues?: ZodIssue[] };
  ```
- **Revalidation:** Always call `revalidatePath` or `revalidateTag` upon successful mutation to purge the Router Cache and sync UI state.

## 5. Directory & Colocation Strategy
- **/app:** Strictly for routing (`page.tsx`, `layout.tsx`, `loading.tsx`, `error.tsx`).
- **/components:** Reusable UI. Subdivide into `/ui` (dumb components), `/forms`, `/layout`.
- **/lib:** Pure functions, database clients, generic utilities.
- **/types:** Global TypeScript definitions, Zod schemas, and branded types.
- **/actions:** Colocate Server Actions here if they are reused, otherwise colocate them near the feature component.
