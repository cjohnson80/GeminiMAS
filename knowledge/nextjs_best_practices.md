# Next.js Best Practices 2024-2025

- **App Router & React Server Components (RSC):** The App Router is now the standard. Shift heavy lifting to the server to ship zero JavaScript to the client where possible.
- **Server Actions:** Replacing traditional API routes (/pages/api) with Server Actions for direct, type-safe database mutations from client components.
- **Partial Prerendering (PPR):** Combining static and dynamic content in the same route. A static shell is served instantly, while dynamic holes are streamed in via Suspense.
- **Turbopack:** Replacing Webpack for significantly faster local development compilation times.
