# Mastodon Collector

The Mastodon collector imports statuses through scheduled API polling. It does not keep a streaming connection open or modify Mastodon's timeline markers.

## Source configuration

Create an OSINT source and select **Mastodon Collector**. Configure:

- **Instance URL**: the Mastodon instance used for API requests, such as `https://mastodon.social`.
- **Timeline**:
  - `hashtag` collects the configured hashtag. The access token is optional when the instance permits public timeline access.
  - `home` collects the access token owner's home timeline.
  - `account` collects statuses for the configured public account handle.
- **Hashtag**: required for `hashtag`; a leading `#` is optional.
- **Account**: required for `account`, for example `user@example.social`.
- **Access token**: required for `home` and `account`. Use a read-only token with account and status read access; write access is not needed.

Some instances restrict anonymous hashtag timelines. If hashtag collection reports that an access token is required, configure a read-only token from that Mastodon instance even though tokens are normally optional for hashtag sources.

The optional user-agent, collector proxy, TLP, and refresh interval settings use the same behavior as other scheduled collectors. Secrets are masked after saving and can be replaced, cleared, or revealed through the audited administrator action.

## Collection behavior

The global **Collector Entry Limit** in Admin Settings limits both Mastodon and RSS processing per run. New sources import the newest statuses up to that limit. Later runs continue forward from a cursor retained in the latest collector task result; if more statuses are waiting than one run permits, later scheduled runs continue the backlog without moving the cursor past unprocessed statuses.

Cursor state follows the task-history lifecycle. Deleting task history, leaving a source inactive beyond the configured retention period, or restoring the database without recent task results resets the source to a newest-status bootstrap. Existing news-item deduplication makes replay safe, but older backlog beyond the entry limit may be skipped after such a reset.

Changing the instance, timeline, hashtag, token owner, or target account establishes a different timeline identity and starts a new cursor. Preview always shows current statuses without reading or advancing stored progress.

Boosts are stored as the original post so repeated boosts deduplicate on the original URL. Replies and boosts visible in the selected timeline are included.

## Deployment and rollback

Deploy compatible shared-model, core, frontend, and worker images together. Core startup synchronizes the collector enum before the new source type is used.

Before rolling back to a release without `MASTODON_COLLECTOR`, export and remove Mastodon sources or restore a verified database snapshot. Older releases do not understand the new collector enum value.
