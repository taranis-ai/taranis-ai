# Notification Center

## When To Load
Load this memory for notification-center UI work, browser-session notifications, `/notifications`, notification history, or client-side notification storage.

## Expected Behavior
The Notification Center is available from the user menu below My Tasks. It records visible frontend and realtime notifications only for the current browser tab session. Data is held in `sessionStorage`, capped at 100 entries, and is cleared on logout or when the user selects Clear all. It must never be sent to or stored by core, the database, or another server-side persistence layer.

## Code Paths
- Route and view: `src/frontend/frontend/router/user.py`, `src/frontend/frontend/views/user_views.py`
- Page and menu: `src/frontend/frontend/templates/user_notifications/index.html`, `src/frontend/frontend/templates/partials/navbar.html`
- Client-side capture and rendering: `src/frontend/frontend/static/js/notification-center.js`
- Realtime event capture: `src/frontend/frontend/static/js/realtime.js`

## Testing
Use `cd src/frontend && uv run pytest tests/unit/views/test_user_notification_view.py` for route and menu coverage. Verify the Notification Center in a browser after a visible frontend or realtime notification; reload the page to confirm the entry remains for the current tab session, then use Clear all.

## Pitfalls
My Tasks is a separate, server-backed history of completed worker results. Do not merge it with notification history. Use `sessionStorage`, not `localStorage`, so entries do not survive beyond the current tab session or cross a logout boundary.
