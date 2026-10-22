# Dashboard Cards

Load for: Dashboard workflow cards, weekly counts, or the analyst review entry.

## Contracts

Assess counts news items/stories, Analyze separates completed/in-progress reports, Publish counts products (not published or ready products), and Connectors separates story/news-item conflicts. Keep existing dashboard-wide scope and the [analyst review](analyst-review.md) permission gate.

Weekly counts run from Monday 00:00 UTC through now, inclusive, excluding future content. News items use publication time; stories/reports/products use creation time. This is not a rolling seven-day window. The shared Dashboard response uses the 30-second frontend cache.

Source distribution respects per-user `show_charts` and `source_distribution_limit` (default 3, non-negative integer). Zero disables it, including Other; positive limits group remaining sources as Other. Profile saves invalidate the dashboard cache. The authenticated query uses the user profile; calls without a user retain the default.

The source query caps its SQL limit at the total news-item count, so even configured integers beyond the database's binding range show all available sources without overflowing. No fixed product maximum applies.

## Code and Tests

`src/core/core/service/dashboard.py`, `src/models/models/dashboard.py`, `src/frontend/frontend/templates/dashboard/user_item_cards.html`.

Extend existing dashboard service coverage for calendar boundaries and the user dashboard browser workflow for navigation.
