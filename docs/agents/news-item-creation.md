# News Item Creation

Load for: Assess news-item creation, method selection, manual entry, URL collection, or file-import retries.

## Contracts

The new-item route starts with a three-way chooser (From file, From URL, Manually), with no method selected. Switching methods preserves independent drafts, URL parameters, and selected files until navigation/reload. Keyboard selection moves focus to the chosen form heading. Existing-item editing has no chooser.

Manual entry requires either title or content. Blank Published defaults to current UTC time. Identity and duplicate rules belong in [Fuzzy Deduplication](fuzzy-deduplication.md).

URL collection defaults to a single article with automatic extraction and direct requests. Linked-article mode requires a container XPath and a positive item limit; the limit is submitted only in that mode. The frontend normalizes parameters through [Worker Parameters](worker-parameters.md) before contacting Core; the single-article worker path independently expands effective values. Explicit TLP applies to every returned item. Request headers are omitted from task descriptions.

Validation failures target notifications without replacing the editor or clearing inputs. File uploads are validated by parsing JSON regardless of MIME type; invalid JSON/encoding returns 400, unexpected local failures return 500, and Core failures preserve its status. Successful imports return to Assess. See [Story Export](story-export.md) for formats and import semantics.

## Code and Tests

Flow: `src/frontend/frontend/templates/assess/news_item_create.html`, `news_item_create_url.html`, and `src/frontend/frontend/views/story_views.py`.

Coverage: Core `test_revision_tracking.py` owns manual identity and update conflicts. Frontend `test_story_view.py` checks error routing and request validation; browser `test_news_item_creation_methods` covers chooser/draft/file recovery and editing, `test_url_news_item_creation` covers single/linked collection, and `test_story_file_import` covers import success. Worker `test_collector_tasks.py` covers extraction with native/string flags, browser lifecycle, and safe failure results. The isolated worker image has no Chromium, so browser rendering uses the worker test fixture.
