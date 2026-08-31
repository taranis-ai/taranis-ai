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

Taranis uses [HTMX 4](https://four.htmx.org/docs/). HTMX attributes are local by default, so add the `:inherited` modifier only when descendant request elements intentionally consume `hx-target`, `hx-select`, `hx-swap`, `hx-include`, `hx-push-url`, or `hx-boost`. Lifecycle integrations must use the colon-form event names, such as `htmx:config:request` and `htmx:after:swap`, and obtain request state from `event.detail.ctx`; after a swap, use `ctx.target` rather than `event.target`. Route error responses with native `hx-status` attributes. Authenticated pages preserve validation swaps with an exact `400` rule, suppress untargeted `4xx`/`5xx` swaps, and request elements that render errors must declare their exact `400`, `4xx`, and `5xx` target rules.

## Testing

Run focused unit tests for changed views/templates and a focused Playwright test for browser behavior. Verify the real local UI when user-facing behavior changes, including the browser console for errors, repeated handlers, and long tasks.

## Pitfalls

- Do not generate HTML in JavaScript when Jinja can render it.
- Do not add global document/window listeners for component-local behavior.
- Do not duplicate state between server markup, Alpine, and custom JavaScript.
- Do not introduce a frontend dependency for behavior already covered by HTMX, Alpine, CSS, or a native browser API.
