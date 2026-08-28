# Mastodon Collector

The Mastodon collector imports statuses through scheduled API polling. It does not keep a streaming connection open or modify Mastodon's timeline markers.

## Source configuration

Create an OSINT source and select **Mastodon Collector**. Configure:

- **Instance URL**: the Mastodon instance origin used for API requests, such as `https://mastodon.social`. Paths, queries, fragments, and embedded credentials are not accepted.
- **Timeline**:
  - `hashtag` collects the configured hashtag. The access token is optional when the instance permits public timeline access.
  - `home` collects the access token owner's home timeline.
  - `account` collects statuses for the configured public account handle.
- **Collection mode**:
  - `complete` is the default and collects every status newer than the cursor, following as many API pages as required until the source is caught up.
  - `latest` collects only the newest API page. When older statuses are skipped to stay current, the task result displays an explicit warning.
- **Hashtag**: required for `hashtag`; a leading `#` is optional.
- **Account**: required for `account`, for example `user@example.social`.
- **Access token**: required for `home` and `account`. Use a read-only token with account and status read access; write access is not needed. Any source with an access token must use an HTTPS instance URL; tokenless hashtag collection may use HTTP for development-only instances.

Some instances restrict anonymous hashtag timelines. If hashtag collection reports that an access token is required, configure a read-only token from that Mastodon instance even though tokens are normally optional for hashtag sources.

The optional user-agent, collector proxy, TLP, and refresh interval settings use the same behavior as other scheduled collectors. Secrets are masked after saving and can be replaced, cleared, or revealed through the audited administrator action.

## Collection behavior

Mastodon does not use the RSS collector entry limit. New sources import the newest API page in either mode. Later `complete` runs use `min_id` to paginate from the cursor until every waiting status has been collected. Later `latest` runs use `since_id` to import at most the newest 40 statuses and probe the oldest status after the cursor to determine whether anything was skipped.

Complete mode preserves continuity but a run after extended downtime can make many API requests, consume substantial worker memory, and encounter the instance's rate limit. Latest mode keeps collection current and bounded, but its warning means older statuses were permanently skipped. Switching from latest to complete cannot recover statuses skipped before the latest cursor was saved.

Cursor state follows the task-history lifecycle. Deleting task history, leaving a source inactive beyond the configured retention period, or restoring the database without recent task results resets the source to a newest-page bootstrap. Existing news-item deduplication makes replay safe, but older history may be skipped after such a reset.

Changing the instance, timeline, hashtag, token owner, or target account establishes a different timeline identity and starts a new cursor. Preview always shows current statuses without reading or advancing stored progress.

Boosts are stored as the original post so repeated boosts deduplicate on the original URL. Replies and boosts visible in the selected timeline are included.

## Deployment and rollback

Deploy compatible shared-model, core, frontend, and worker images together. Core startup synchronizes the collector enum before the new source type is used.

Before rolling back to a release without `MASTODON_COLLECTOR`, restore the verified pre-deployment database snapshot and redeploy the previous images. Exporting and removing Mastodon sources alone does not reverse the release's other database migrations.
