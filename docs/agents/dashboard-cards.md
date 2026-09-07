# Dashboard Cards

## When To Load
Dashboard workflow cards, Assess counts, weekly activity, Analyze, Publish, Connectors, or the analyst review entry.

## Expected Behavior
Four workflow cards occupy two columns on tablet and desktop screens and one column on smaller screens. Assess shows news item and story totals with the analyst review entry in its header. Analyze shows completed and in-progress reports; Publish shows products, without implying every product is ready to publish. Connectors breaks pending conflicts down into stories and news items.

Weekly counts cover Monday 00:00 UTC through the current time, inclusive, matching the existing UTC week convention. News items use publication time; stories, reports, and products use creation time. Tooltips explain the dates. Totals and weekly counts retain the existing dashboard-wide scope.

## Code Paths
- `src/core/core/service/dashboard.py`
- `src/models/models/dashboard.py`
- `src/frontend/frontend/templates/dashboard/cards.html`
- `src/frontend/frontend/templates/dashboard/user_item_cards.html`

## Data Flow
The dashboard endpoint computes database counts and reads the existing conflict stores. The frontend consumes the shared Dashboard model through DataPersistenceLayer with its existing 30-second cache. No additional browser requests are needed.

## Testing
Extend the dashboard service test for calendar boundaries and the existing user dashboard browser workflow for card navigation and the review entry. Run the full signoff pipeline.

## Pitfalls
Do not label the product total as published or ready to publish. Keep the analyst review permission gate and trim the captured action markup so denied or absent permission leaves no header action wrapper. Exclude future-dated content from weekly counts. Counts are not a rolling seven-day window.
