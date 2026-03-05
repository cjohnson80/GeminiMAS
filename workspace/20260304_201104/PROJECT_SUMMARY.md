# Project Summary: GeminiMAS Frontend Service

## 1. Technical Stack Definition

*   **Framework:** React (with TypeScript/JavaScript, prioritizing JS for lower initial overhead on Celeron constraint).
*   **Build Tool:** Vite (Fast HMR and low build overhead, suitable for resource-constrained environments).
*   **Styling:** Tailwind CSS (Utility-first approach, enabling rapid development and avoiding large CSS-in-JS bundles).
*   **State Management:** Zustand (Minimal boilerplate, small bundle size, ideal for low-resource hardware constraints, prioritizing over Redux/large Context trees).

## 2. Directory Structure Plan

```
frontend_app/
├── node_modules/
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   │   ├── common/ (Reusable UI elements)
│   │   └── specific/ (Feature-specific components)
│   ├── hooks/
│   ├── store/ (Zustand stores)
│   │   ├── useAuthStore.ts
│   │   └── useSystemStore.ts
│   ├── utils/
│   ├── App.tsx
│   └── main.tsx (Entry point)
├── index.html
├── package.json
├── tsconfig.json (or jsconfig.json)
└── vite.config.js
```

## 3. State Management Strategy (Zustand)

Zustand will be used for global state management. This minimizes runtime overhead compared to deep Context providers or Redux.

*   **Data Flow:** Components subscribe only to the slices of state they need, preventing unnecessary re-renders.
*   **Initialization:** Stores will handle their own initialization, potentially loading initial configuration from the backend API (which will be proxied or called directly by the frontend).

## 4. Dependency Management & Optimization

*   **Constraint Adherence:** All chosen technologies (Vite, Zustand) are selected specifically to optimize for low-resource environments (e.g., avoiding heavy Webpack configurations or large state libraries).
*   **Next Steps:** Initialize the project structure using `npm create vite@latest` with React template, then integrate Tailwind CSS via PostCSS setup.