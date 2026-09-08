# News Item Ordering

## When To Load
Story news-item order, drag-and-drop, linked news items, conflict diffs, grouping, ungrouping, and title fallback.

## Expected Behavior
The story editor offers drag handles, keyboard move buttons, and a separate Save order action. The shared order is local to this instance. Saving order preserves unsaved story fields and does not change the title, content timestamps, revision, or MISP scheduling.

The story edit route and its order-save/reload route require ASSESS_UPDATE. Ordering controls exist only in the editor; there is no per-story capability flag. Core uses the existing ASSESS_UPDATE route decorator. Story.update and reorder share Story.allowed_to_update: the user must satisfy the story TLP and have write ACL access to every linked item. Trusted bot updates without a user retain their existing path. Single-item and RT-managed stories hide ordering controls.

Saved order survives import and conflict resolution. Grouping keeps destination order and appends source items in their source order. Ungrouped items use their own titles; removal of an item whose title matches the parent promotes the first remaining item's title. Other parent titles remain unchanged.

## Code Paths
- `src/core/core/model/story.py`: JSON order column, resolved ordering, serialization, title fallback.
- `src/core/core/service/story.py`, `src/core/core/api/assess.py`: order transaction and API.
- `src/core/core/service/story_operations.py`: append order on transfer.
- `src/core/core/model/story_conflict.py`: news-item comparison by ID.
- `src/frontend/frontend/views/story_views.py`, `src/frontend/frontend/templates/assess/news_item_order.html`: partial save and local SortableJS/Alpine behavior.

## Data Flow
The DOM and form-associated hidden inputs hold the proposed order. HTMX posts to the frontend; core PUT `/assess/stories/<id>/news-item-order` receives `news_item_ids` and `expected_news_item_ids`. Core locks the story row, compares the current resolved list, and validates an exact permutation. A changed list returns 409 without overwriting it; the UI retains the proposal and offers explicit reload. Successful saves invalidate existing story/report cache scopes and publish the existing Assess change notice.

`ordered_news_items` returns saved current IDs followed by unlisted IDs in deterministic ID order. Stale IDs never change membership. Existing stories initially use ID order. The storage field is excluded from external payloads. Conflict normalization sorts news-item copies by ID regardless of display order; it does not sort arbitrary lists.

## Testing
Core payload validation lives in the existing `test_assess_api.py` suite. Existing worker integration, revision/removal, and conflict normalization tests cover order preservation. The core RBAC test parameterizes PUT, PATCH, and reorder to cover the shared ACL/TLP policy; existing auth tests cover the permission decorator. The existing frontend story-edit test checks route permission gates; its dedicated connection-error test covers safe partial responses. The default CI browser suite includes `TestEndToEndUser.test_news_item_order` for drag, keyboard, persistence, draft preservation, and stale-save recovery. Run the complete `./dev/test_push_signoff.sh` gate after committing.

## Pitfalls
- Never trust order supplied by imported content or use it to move items between stories.
- Keep reorder swaps limited to the linked-item area; replacing the full editor loses unsaved content.
- SortableJS already ships in the vendor bundle. Initialize and destroy it with the owning Alpine component.
- The additive PostgreSQL migration runs during normal core startup. Application rollback may leave the unused column in place.
