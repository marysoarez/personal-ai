---
name: react-frontend
description: Build, refactor, debug, and review React frontend applications. Use for React components, hooks, routing, forms, state management, data fetching, accessibility, performance, and UI tests. Follow the repository's existing framework, conventions, and dependencies.
---

# React Frontend

## Core workflow

1. Inspect the repository before editing. Identify the package manager, React version, framework, entry points, route structure, styling system, and existing tests.
2. Read nearby components and follow their naming, file organization, data flow, and styling conventions.
3. Make the smallest coherent change that meets the request. Reuse existing dependencies and shared components.
4. Keep rendering declarative. Use effects only to synchronize with external systems; derive values during render when possible.
5. Run the relevant formatter, lint, type-check, and focused tests when the user requests verification or the repository workflow requires it.

## Before editing

Use fast discovery commands, adapting them to the environment:

```sh
rg --files -g 'package.json' -g '*lock*' -g 'vite.config.*' -g 'next.config.*' -g 'src/**' -g 'app/**' -g 'pages/**'
rg 'createRoot|useState|useEffect|useContext|createBrowserRouter|next/router|next/navigation' .
```

Inspect `package.json` and its lockfile before adding or changing dependencies. Determine whether the app uses JavaScript or TypeScript and retain that choice in touched code.

## Component and state guidelines

- Keep components focused around a clear responsibility. Extract shared UI only when it improves clarity or reuse.
- Use function components and the Hooks patterns already used by the project.
- Keep state as close as practical to the components that own it. Lift it only when multiple parts need to coordinate.
- Use stable, meaningful keys for rendered collections; do not use array indexes when items can be reordered or removed.
- Keep effects narrowly scoped, include the correct dependencies, and clean up subscriptions, timers, and event listeners.
- Handle loading, empty, error, and success states for asynchronous UI.
- Avoid unnecessary memoization, abstractions, global state, and new dependencies.
- Keep API and business logic out of presentational components when the repository already separates these concerns.

## UI quality and accessibility

- Preserve the app's established design system, responsive behavior, and browser support.
- Use semantic HTML and native controls where suitable.
- Ensure interactive elements work with a keyboard, have visible focus, and expose accessible names and state.
- Associate form labels and validation feedback with their controls. Do not rely on color alone to convey errors or status.
- Prefer existing CSS, CSS Modules, utility classes, or component libraries over introducing another styling approach.
- When the project has no defined accessibility target, use [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) as a practical review baseline, while respecting applicable product and legal requirements.

## Review checklist

- Does the change match the app's framework and existing patterns?
- Are state transitions and asynchronous failure paths covered?
- Are effects necessary, correctly dependent, and cleaned up?
- Are list keys stable and form controls labeled?
- Does the UI work at relevant screen sizes and with keyboard navigation?
- Are types and errors handled without hiding real failures?
- Are tests or stories updated where the project expects them?

## Framework-specific notes

- In Next.js, follow the existing App Router or Pages Router structure. Add client components only when browser interactivity or client-only APIs require them.
- In Vite or another client-rendered app, follow the existing router and build setup.
- Do not introduce Next.js, a router, a state library, a UI kit, or a data-fetching library unless requested or needed by the existing architecture.

