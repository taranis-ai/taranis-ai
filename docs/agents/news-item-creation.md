# News Item Creation

## When To Load
Assess news-item creation, method selection, manual entry, URL collection, or file-import retries.

## Contracts
The new-item route starts with a three-way chooser (From file, From URL, Manually). Each choice reveals only its own form. Change creation method returns to the chooser; Alpine hides forms without removing them, preserving manual drafts, URL parameters, and selected files until navigation/reload. Native buttons support keyboard activation and focus moves to the selected form heading. Existing-item editing has no chooser.

Manual entry requires either title or content, as enforced by the shared NewsItem model. Published is optional and an empty value defaults to current UTC time through the existing date validator. URL and file fields are required only in their independent forms. The dedicated URL form keeps collection settings inline: single article (default) or linked articles, direct requests or browser rendering, TLP, optional content XPath, and advanced user-agent/proxy/JSON headers. Linked articles require an XPath selecting a container of article links; the positive item limit is shown/submitted only in that mode. Switching modes preserves entered settings. One-off collection has no scheduling controls.

The frontend validates/normalizes URL parameters through the shared worker contract before contacting Core; invalid settings return curated field labels without clearing inputs. The worker independently expands and normalizes parameters before extraction, including string booleans, header JSON, and numeric limits. Explicit TLP is applied to every returned item. Worker failures persist a static message and log details server-side; request headers are not logged in the task description.

Validation failures target notifications without replacing the editor. File-import failures preserve Core's status and return static local errors for invalid JSON, unsupported file types, and unexpected failures; successful imports redirect to Assess. See [Story Export](story-export.md) for import formats and duplicate semantics.

## Entry Points and Coverage
`src/frontend/frontend/templates/assess/news_item_create.html` and `src/frontend/frontend/views/story_views.py` own the flow. Existing frontend story-view unit coverage checks notification targeting, typed URL payloads, and invalid settings. Worker collector-task tests exercise actual extraction with native/string browser flags, disabled splitting, browser lifecycle calls, and safe failure results (browser transport uses the existing fixture). The full-stack `test_url_news_item_creation` browser workflow covers single/linked collection with direct loading, item limits, classification, and validation recovery; the isolated worker image has no Chromium installation. `TestEndToEndAdmin.test_news_item_creation_methods` covers keyboard selection, draft and file preservation, manual validation, content-only creation with a default publication time, and editing without choices. `test_story_file_import` covers successful imports from the chooser.
