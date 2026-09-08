# Notification Center

## When To Load

`/notifications`, frontend notification history, persistent notices, or browser storage.

## Contracts

Visible frontend/realtime notifications are stored only in the current tab's `sessionStorage`, capped at 100 entries, and cleared by logout or Clear all. Never persist/send this history server-side. My Tasks is a separate server-backed worker-result history.

Capture once at the event source: notification-fragment Alpine initialization, realtime display, or the unswapped HTMX response-error handler. Preserve error/warning/success/info levels. The page reads the stored array for Alpine rendering; follow the [event/state rules](frontend-development.md).

Server-rendered `persistent: true` notices remain until clicked. [Admin broadcasts](realtime-events.md) use the same history boundary and remain until dismissed.

## Entry Points and Coverage

`src/frontend/frontend/static/js/notification-center.js`, `src/frontend/frontend/templates/notification/index.html`, `src/frontend/frontend/templates/user_notifications/index.html`, `src/frontend/frontend/views/user_views.py`.

Tests: `src/frontend/tests/unit/views/test_user_notification_view.py`, `src/frontend/tests/playwright/test_notification_center_js.py`, `src/frontend/tests/playwright/test_main_js.py`, `src/frontend/tests/playwright/test_realtime_js.py`. Browser verification includes reload persistence within the tab and Clear all/logout cleanup.
