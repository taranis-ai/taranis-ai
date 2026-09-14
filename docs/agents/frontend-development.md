# Frontend Development

## When To Load

Before any `src/frontend` change.

## Rendering and State

Use HTMX for server-rendered requests and targeted swaps, then Alpine for component-local state. Custom JavaScript needs a concrete browser capability neither can provide. Keep HTML in Jinja, one owner per state value, and reuse existing native/browser/framework capabilities before adding dependencies.

Handle known events at their producer. Do not rediscover them with polling, DOM-wide observers/scans, or broad lifecycle listeners. Deferred scripts initialize directly; component-local behavior must not add global listeners.

Shared controls own selection, accessibility, styling, and shortcut behavior across consumers. Keep selection backed by native inputs where forms submit it; do not add a parallel selection store. Assess shortcuts use the shared guard to avoid firing in editable controls or open dialogs. The selection bar's no-JavaScript hiding rule belongs in `base.html`, never in swappable fragments.

Shared row actions have accessible names. Delete actions retain native CSRF-protected POST forms and explicitly target notifications on HTMX 400/4xx/5xx failures.
Native delete dispatch rejects create placeholder IDs with 405 before contacting Core.

## HTMX and Forms

Taranis uses HTMX 4:

- Attributes apply only to their element unless explicitly marked `:inherited`.
- Lifecycle names use colons (`htmx:config:request`, `htmx:after:swap`); request/swap context is `event.detail.ctx`, and the swap target is `ctx.target`.
- Authenticated pages swap 400 validation responses into the normal target and suppress other 4xx/5xx swaps. Intentional error rendering needs local `hx-status:400`, `hx-status:4xx`, and `hx-status:5xx` target rules, plus compatible select/swap rules.
- Complete table-container responses require `outerHTML` on that container; notification-only actions must receive only notifications. Error responses must not inherit an append or table-selection swap.

Shared table navigation retains native links/GET forms and `restoreSearchAfterSwap`; `hx-preserve` does not replace request-derived search restoration. Page-size events stay local to the form. Import controls retain the list URL for refresh after success. Assess token filters still require JavaScript.

Preserve selected IDs and retry context on validation errors. Report/clustering dialogs close only on success. Non-HTMX forms retain CSRF protection and safe result/retry redirects.

## Specific Integration Traps

- Analyze Clone Report and row/bulk delete return `analyze/report_table.html` including `#report`; replace that wrapper with outerHTML.
- Analyze New Report and Assess Add to Report share `analyze/report.html`. Report Type is required in both UI and core; the existing `test_user_analyze` workflow covers both entry paths.

## Entry Points and Verification

Views/templates: `src/frontend/frontend/views/`, `src/frontend/frontend/templates/`; browser code: `src/frontend/frontend/static/js/`; bundle: `src/frontend/vendor.js`.

Use existing unit/browser workflows and the [shared validation process](development-workflow.md). For user-facing changes, verify the real local UI and browser console, including repeated handlers and long tasks.
