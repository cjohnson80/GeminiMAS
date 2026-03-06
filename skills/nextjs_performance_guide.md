# Next.js Data Fetching Performance Optimization Guide

As a Performance Engineer, the goal is to minimize Time to First Byte (TTFB) and reduce client-side JavaScript execution overhead.

## 1. Server Components (RSC) Data Fetching (Recommended)

Next.js App Router automatically handles caching for native `fetch` calls within Server Components. This is the most performant strategy.

**Optimization Focus:**
*   **Automatic Caching:** Use `fetch(url, { next: { revalidate: 3600 } })` for time-based invalidation (revalidate every hour) or rely on Next.js's default caching.
*   **Static Caching:** For data that rarely changes, use `fetch(url, { cache: 'force-cache' })` (default) or set cache options to `'force-cache'` for maximum performance.
*   **No Fetching:** If data is truly static or derived entirely from build-time props, avoid `fetch` entirely within the component.

## 2. Client Components (CSR) Data Fetching (If Necessary)

If data fetching must occur client-side (e.g., user-specific actions, dynamic filtering after mount):

**Optimization Focus:**
*   **Caching Library:** Use optimized libraries like SWR or React Query to manage cache state, request deduplication, and background revalidation.
*   **HTTP Caching Headers:** Ensure the underlying API endpoints return aggressive caching headers:
    *   `Cache-Control: public, max-age=31536000, immutable` for static assets/APIs.
    *   `Cache-Control: public, max-age=60, stale-while-revalidate=300` for frequently updated data.
*   **Lazy Loading:** Defer client-side fetching using `useEffect` only after necessary layout components have loaded, or use dynamic imports for the component itself (`next/dynamic` with `ssr: false`).

## Performance Impact Summary
| Strategy | TTFB Impact | JS Bundle Size | Complexity | Recommendation |
|---|---|---|---|---|
| RSC Native Fetch | Lowest | Low | Low | Primary strategy. |
| CSR Fetching (SWR) | Higher (after initial load) | Medium | Medium | Use sparingly for interactive data. |
