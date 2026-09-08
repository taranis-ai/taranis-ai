# Dashboard Cards

## When To Load

Dashboard workflow cards, weekly counts, or the analyst review entry.

## Contracts

Assess counts news items/stories, Analyze separates completed/in-progress reports, Publish counts products (not published or ready products), and Connectors separates story/news-item conflicts. Keep existing dashboard-wide scope and the [analyst review](analyst-review.md) permission gate.

Weekly counts run from Monday 00:00 UTC through now, inclusive, excluding future content. News items use publication time; stories/reports/products use creation time. This is not a rolling seven-day window. The shared Dashboard response uses the existing 30-second frontend cache.

## Entry Points and Coverage

`src/core/core/service/dashboard.py`, `src/models/models/dashboard.py`, `src/frontend/frontend/templates/dashboard/user_item_cards.html`.

Extend existing dashboard service coverage for calendar boundaries and the user dashboard browser workflow for navigation.
