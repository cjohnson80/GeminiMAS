# Next.js & TypeScript Best Practices (v1.0)

- **App Router:** Favor Server Components (default) for performance. Use "use client" only when strictly necessary for interactivity (hooks like useState, useEffect).
- **TypeScript:** Enforce strict typing. Avoid "any". Use Interface for object shapes and Type for unions/intersections.
- **Data Fetching:** Use Server Actions for mutations. Use the native `fetch` with Next.js revalidate/cache tags for efficient data retrieval.
- **Optimization:** Use next/image for automatic image optimization. Use next/font for local self-hosting of fonts.
- **Architecture:** Maintain a clean directory structure: /app, /components, /lib, /hooks, /types.
