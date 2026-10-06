# Frontend strategy

The product already uses React, Vite, and TypeScript. This refinement makes that foundation explicit and maintainable while preserving the business workflows, light/red design, assistant-ui/Blume chat, and existing API/backend architecture.

## Chosen foundation

| Concern | Choice | Reason |
|---|---|---|
| Interface | React 19 | Existing component model and chat integrations. |
| Development/build | Vite 6.4 with React plugin | Existing verified build/proxy setup; major upgrades are separate compatibility work. |
| Type system | TypeScript 5.8 strict mode | Browser source, tooling, and tests receive explicit checks. |
| Routing | React Router 7 | Existing business destinations and product/revision scope. |
| Server data | Small shared read hook plus HTTP transport | Keep this local MVP lean; handle cancellation, scope changes, errors, refresh, and polling consistently. |
| Chat | assistant-ui + Blume, lazy-loaded | Retain the requested streaming/generative integrations and server-only LLM credentials. |
| Testing | Vitest + React Testing Library; Playwright/Axe | Fast seam tests for transport/hooks plus real browser journeys and accessibility. |
| Styling | Existing CSS/design tokens and Fontsource fonts | Preserve established UI and avoid a parallel styling system. |

The default is a lean foundation. Shared cross-page caching can be introduced when reuse/invalidation requirements justify it; local read state is not presented as a durable shared cache. There is no new global state store for form, selected-version, or chat state.

## Module ownership

- `src/main.tsx` only mounts the application and loads global styles/fonts.
- `src/app/` owns routing and application providers.
- `src/features/` owns business views; product context has a separate module so views do not import the workspace that imports them.
- `src/api/` owns HTTP transport, domain response types, and the shared read hook. No feature implements its own JSON error parsing/poll scheduler.
- `src/components/` remains the shared UI/design layer.
- `src/test/` holds focused frontend tests; `tests/e2e/` holds live browser workflows.

Product/revision context remains the authority for scoped UI requests. The scoped-path function is named as a React hook because it consumes context. Transport stays React-independent, and its consumer interface retains compatibility with existing feature calls.

## Data-handling contract

A changed request path immediately exposes a fresh loading state instead of showing the previous scope's data. Disabled reads expose empty state. Requests are cancelled on cleanup, invalidation, and scope change. Polling avoids overlapping reads; an obsolete response cannot replace current data. A same-scope refresh can retain last-known data while refreshing, but errors are explicit. Invalid successful JSON responses are errors rather than fabricated successful data.

`ApiError` preserves status/detail while parsing FastAPI string/object/validation-list errors from unknown input safely. JSON transport and Blume's plain-text chat stream remain separate contracts. Existing domain response interfaces describe the current app; generic backend response schemas do not make an automatically generated client fully runtime-validated.

## Quality gates

Use explicit scripts for type checking, unit tests, browser tests, formatting, and production build. Browser and Node/tooling TypeScript configurations are separate so Node globals do not leak into product source. Version and runtime requirements are explicit in the package configuration. Use Node 22.x at 22.12+, 24.x, or 26+; the verified local runtime is Node 24.12. Tests use jsdom 26 to remain compatible with that runtime. Test configuration and dependencies stay out of the shipped interface.

Run `make check-ui` for formatting, types, and unit tests, `make build` for production output, and `make test-e2e` against the running stack. `npm run preview --prefix frontend` serves the built frontend on port 4174 with the same API proxy.

Checks must verify behavior at seams: malformed responses, changing scopes, cancellation/polling/refresh, and actual business workflows. Preserve public paths, revision/release semantics, citations, safe Markdown/generative components, mobile behavior, and shader fallbacks.

Official references: [React application setup](https://react.dev/learn/build-a-react-app-from-scratch), [Vite guide](https://vite.dev/guide/), [TypeScript strict mode](https://www.typescriptlang.org/tsconfig/strict.html), and [Vitest guide](https://vitest.dev/guide/). Installed versions and compatibility, rather than a claim of being the newest release, determine this change.
