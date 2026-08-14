# Notification Center

## When To Load
Load this memory for notification-center UI work, browser-session notifications, `/notifications`, notification history, or client-side notification storage.

## Expected Behavior
The Notification Center is available from the user menu below My Tasks. It records visible frontend and realtime notifications only for the current browser tab session. Data is held in `sessionStorage`, capped at 100 entries, and is cleared on logout or when the user selects Clear all. It must never be sent to or stored by core, the database, or another server-side persistence layer. Server-rendered notifications accept `persistent: true` to omit their timeout animation and remain visible until clicked.

Notification recording is explicitly event-driven. Server-rendered HTMX notification fragments use Alpine initialization to record themselves, realtime code records a notice when it displays one, and unswapped HTMX errors record at the existing response-error handler. The storage module must not observe or scan the DOM.

## Code Paths
- Route and view: `src/frontend/frontend/router/user.py`, `src/frontend/frontend/views/user_views.py`
- Page and menu: `src/frontend/frontend/templates/user_notifications/index.html`, `src/frontend/frontend/templates/partials/navbar.html`
- Client-side storage boundary: `src/frontend/frontend/static/js/notification-center.js`
- Notification capture and Alpine rendering: `src/frontend/frontend/templates/notification/index.html`, `src/frontend/frontend/templates/user_notifications/index.html`
- Realtime event capture: `src/frontend/frontend/static/js/realtime.js`

## Data Flow
HTMX swaps a server-rendered notification into `#notification-bar`; its Alpine `x-init` calls the storage boundary once. Realtime and unswapped HTMX errors call the same boundary at their known event source. Admin broadcasts render the exact event message as text, remain until dismissed, and are recorded through the same storage boundary. The Notification Center reads the browser-session array once and Alpine renders it. Clear all and logout remove the storage key directly.

## Testing
Use `cd src/frontend && uv run pytest tests/unit/views/test_user_notification_view.py` for route and menu coverage and `uv run pytest tests/playwright/test_notification_center_js.py tests/playwright/test_realtime_js.py --e2e-ci` for the explicit storage and realtime boundaries. Verify the Notification Center in a browser after a visible frontend or realtime notification; reload the page to confirm the entry remains for the current tab session, then use Clear all.

## Pitfalls
My Tasks is a separate, server-backed history of completed worker results. Do not merge it with notification history. Use `sessionStorage`, not `localStorage`, so entries do not survive beyond the current tab session or cross a logout boundary. Never restore DOM observation, polling, document-wide click handling, or lifecycle scans for notification capture.
