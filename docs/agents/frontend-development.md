# Frontend Development

## When To Load

Read this before every change under `src/frontend`, including Flask views, Jinja templates, HTMX behavior, Alpine state, styles, browser APIs, and static JavaScript.

## Expected Behavior

Taranis is server-rendered and keeps browser code to the absolute minimum. Use this order and stop at the first option that works:

1. Use HTMX for requests, server-rendered HTML, targeted swaps, and server-driven UI updates.
2. Use Alpine.js for small, local UI state and behavior that cannot be expressed with HTMX alone.
3. Write custom JavaScript only when neither HTMX nor Alpine can provide the required browser API or behavior. Any new custom JavaScript must have a concrete reason why the first two options are insufficient.

Known events must be handled at their source. The code that receives a realtime event, HTMX response, or user action must invoke the exact update it requires. Never add polling, a DOM-wide `MutationObserver`, repeated DOM scans, or broad lifecycle listeners to rediscover an event the application already receives. Do not add `DOMContentLoaded` handlers for deferred scripts; initialize directly or use the relevant HTMX or Alpine lifecycle.

## Code Paths

- Server-rendered UI: `src/frontend/frontend/views/`, `src/frontend/frontend/templates/`
- Browser code: `src/frontend/frontend/static/js/`
- HTMX and Alpine bundle: `src/frontend/vendor.js`
- Frontend tests: `src/frontend/tests/unit/`, `src/frontend/tests/playwright/`

## Data Flow

Prefer Flask view -> Jinja fragment -> HTMX targeted swap. Add Alpine only inside the owning component when local state is necessary. Custom JavaScript may expose a small browser-API boundary, such as `sessionStorage` or `EventSource`, but event producers must call that boundary directly.

## Testing

Run focused unit tests for changed views/templates and a focused Playwright test for browser behavior. Verify the real local UI when user-facing behavior changes, including the browser console for errors, repeated handlers, and long tasks.

## Pitfalls

- Do not generate HTML in JavaScript when Jinja can render it.
- Do not add global document/window listeners for component-local behavior.
- Do not duplicate state between server markup, Alpine, and custom JavaScript.
- Do not introduce a frontend dependency for behavior already covered by HTMX, Alpine, CSS, or a native browser API.
