# News Item Creation

## When To Load
Assess news-item creation, method selection, manual entry, URL collection, or file-import retries.

## Contracts
The new-item route starts with a three-way chooser (From file, From URL, Manually). Each choice reveals only its own form. Change creation method returns to the chooser; Alpine hides forms without removing them, preserving manual drafts, URL parameters, and selected files until navigation/reload. Native buttons support keyboard activation and focus moves to the selected form heading. Existing-item editing has no chooser.

Manual entry requires either title or content, as enforced by the shared NewsItem model. Published is optional and an empty value defaults to current UTC time through the existing date validator. URL and file fields are required only in their independent forms. Collection parameters remain associated with the URL form.

Validation failures target notifications without replacing the editor. File-import failures preserve Core's status and return static local errors for invalid JSON, unsupported file types, and unexpected failures; successful imports redirect to Assess. See [Story Export](story-export.md) for import formats and duplicate semantics.

## Entry Points and Coverage
`src/frontend/frontend/templates/assess/news_item_create.html` and `src/frontend/frontend/views/story_views.py` own the flow. Existing frontend story-view unit coverage checks notification targeting and URL payloads. `TestEndToEndAdmin.test_news_item_creation_methods` covers keyboard selection, draft and file preservation, manual validation, content-only creation with a default publication time, and editing without choices. `test_story_file_import` covers successful imports from the chooser.
