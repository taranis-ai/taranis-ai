---
title: "Mastodon Collector"
description: "Collect Mastodon hashtag, home, and account timelines through the Mastodon API."
weight: 5
aliases:
  - /docs/admin/mastodon-collector/
---

The Mastodon Collector imports posts from a Mastodon instance through scheduled API polling. It supports hashtag timelines, the access-token owner's home timeline, and public posts from a specific account.

Use the native collector when you need authenticated access, reliable pagination, or collection progress across runs. For simple public feeds, the [RSS alternative](_index.md#rss-alternative-for-mastodon-feeds) may be sufficient.

## Timeline modes

| Timeline | Collected posts | Target field | Access token | Recommended scopes |
|---|---|---|---|---|
| `hashtag` | Posts visible in the configured instance's hashtag timeline | `HASHTAG` | Optional only when the instance permits anonymous hashtag access | `read:statuses` when a token is required |
| `home` | The token owner's home timeline | None | Required | `profile` and `read:statuses` |
| `account` | Posts from a public account known to the configured instance | `ACCOUNT` | Required | `read:accounts` and `read:statuses` |

Mastodon instances decide whether anonymous hashtag access is allowed. A hashtag can therefore work without a token on one instance and require authentication on another. The instance's federation state, moderation policy, and knowledge of remote accounts also determine which posts are available; an instance is not a complete index of the Fediverse.

See Mastodon's API documentation for the [hashtag and home timeline endpoints](https://docs.joinmastodon.org/methods/timelines/), [account lookup and account-status endpoints](https://docs.joinmastodon.org/methods/accounts/), and [OAuth scopes](https://docs.joinmastodon.org/api/oauth-scopes/).

## Create an OSINT source

1. Open **Administration → OSINT Source**.
2. Select **New OSINT Source**.
3. Enter a name and select **Mastodon Collector**.
4. Configure the parameters described below.
5. Save the source.
6. Use **Preview** to verify the result without adding posts to Assess.
7. Use **Collect** when the preview is correct, or enable the source for scheduled collection.

### Parameters

| Parameter | Required | Description |
|---|---|---|
| `INSTANCE_URL` | Yes | Origin of the Mastodon instance, for example `https://chaos.social`. Do not include credentials, a path, query, or fragment. |
| `TIMELINE` | Yes | One of `hashtag`, `home`, or `account`. |
| `HASHTAG` | Hashtag mode | Hashtag with or without a leading `#`, for example `curl` or `#curl`. Letters, numbers, and underscores are accepted. |
| `ACCOUNT` | Account mode | Account handle without a URL, for example `alice@example.social`. A leading `@` is optional. |
| `ACCESS_TOKEN` | Home and account modes; sometimes hashtag mode | User access token created on the same Mastodon instance as `INSTANCE_URL`. |
| `USER_AGENT` | No | User-Agent sent to Mastodon. The default is `TaranisAI/1.0`. |
| `PROXY_SERVER` | No | Per-source HTTP(S) proxy URL. |
| `USE_GLOBAL_PROXY` | No | Uses the [default collector proxy](../settings.md#default-collector-proxy) instead of `PROXY_SERVER`. |
| `TLP_LEVEL` | No | TLP level assigned to imported News Items. |
| `REFRESH_INTERVAL` | No | Five-field cron schedule. If empty, the global collector interval applies. See [collector scheduling](../bots.md#common-settings). |

The global **Collector Entry Limit** in [Administration → Settings](../settings.md) limits the number of posts processed during each run.

### Example: `#curl` on `chaos.social`

| Parameter | Value |
|---|---|
| `INSTANCE_URL` | `https://chaos.social` |
| `TIMELINE` | `hashtag` |
| `HASHTAG` | `curl` |
| `ACCESS_TOKEN` | A token created on `chaos.social` with `read:statuses` |

If the token field is empty and the instance restricts anonymous hashtag access, collection fails with the actionable access-token-required message described under [Troubleshooting](#access-token-required).

## Create a Mastodon access token

Mastodon's web interface places access-token management under **Development**, not under the normal account or privacy settings. The token must be created on the instance configured in `INSTANCE_URL`; a token from another instance will not work.

1. Sign in to the Mastodon instance used by the source.
2. Open **Preferences → Development**. The direct URL is normally `https://INSTANCE/settings/applications`. For example, use [chaos.social Development](https://chaos.social/settings/applications) for `https://chaos.social`.
3. Select **New application**.
4. Enter an application name such as `Taranis AI`.
5. Leave **Application website** empty unless your organization wants to identify the deployment.
6. Leave the default redirect URI `urn:ietf:wg:oauth:2.0:oob`. Taranis does not use an interactive OAuth redirect.
7. Select only the scopes needed for the configured timeline:
   - Hashtag: `read:statuses`.
   - Home: `profile` and `read:statuses`.
   - Account: `read:accounts` and `read:statuses`.
8. Submit the application.
9. Open the created application and copy **Your access token**. Do not copy the client secret instead.
10. Paste the token into the Taranis source's `ACCESS_TOKEN` field and save the source.

Some Mastodon versions preselect `profile` on the new-application form. Clear it for hashtag or account collection when it is not listed above. For one application used by all three modes, select `profile`, `read:accounts`, and `read:statuses`. Do not select `write`, `follow`, `push`, or any `admin` scope. On Mastodon versions older than 4.3, use `read:accounts` instead of `profile` for home-timeline collection.

Mastodon's developer documentation describes [user tokens](https://docs.joinmastodon.org/api/oauth-tokens/), [granular scopes](https://docs.joinmastodon.org/api/oauth-scopes/), and the full [OAuth authorization flow](https://docs.joinmastodon.org/client/authorized/). The Development page is the shortest setup path for a Taranis administrator who controls the Mastodon account.

### Token security

- Treat the access token like a password. Do not paste it into tickets, chat, screenshots, shell history, or logs.
- Prefer a dedicated organizational Mastodon account rather than a personal account for production collection.
- Grant only the scopes listed for the selected timeline. The collector never needs write or administrator access.
- Taranis masks the stored secret after saving. Revealing or replacing it is an audited administrator action.
- If a token may have leaked, delete or revoke the Mastodon application, create a replacement, and update the Taranis source.

## Collection behavior

The collector polls Mastodon's REST API; it does not open a long-lived streaming connection and does not update Mastodon timeline markers.

On the first successful run, Taranis imports the newest posts up to the global Collector Entry Limit. Later runs request posts newer than the saved cursor. The cursor is stored with the latest collector task result and advances only after the collected News Items are published successfully. A failed Mastodon request or failed publication does not advance it.

Cursor state is intentionally best-effort. Deleting task history, retaining no task result for an inactive source, or restoring a database without recent task results can remove it. The next run then starts again from the newest posts. Core deduplication makes replay safe, but posts older than the entry limit may be skipped after such a reset.

Changing the instance, timeline mode, hashtag, token owner, or target account establishes a new timeline identity and starts a new cursor. Preview ignores the cursor and never changes collection progress.

### Mapping and deduplication

- Each Mastodon post becomes a News Item.
- Boosts are stored as the original post and deduplicate through the original post URL.
- Replies and boosts visible in the selected timeline are retained.
- A content warning becomes the title when present; otherwise Taranis derives the title from the post content.
- Media descriptions provide content when a post has no text.
- The source account, author, publication time, language, post URL, and plain-text content are retained when supplied by Mastodon.

See Mastodon's [Status entity](https://docs.joinmastodon.org/entities/Status/) for the upstream response fields.

## Troubleshooting

### Access token required

**Message:** `This Mastodon instance requires an access token to collect hashtags`

The instance does not permit the combined hashtag feed to be read anonymously. Create a token with `read:statuses`, add it to the source, and preview again. This is expected on instances that expose local hashtag posts publicly but require authentication for remote posts.

Mastodon documents this behavior on the [hashtag timeline endpoint](https://docs.joinmastodon.org/methods/timelines/#tag).

### Authentication failed or access was denied

Verify that:

- The token was created on exactly the same instance as `INSTANCE_URL`.
- The token was copied from **Your access token**, not **Client secret**.
- The application has the scopes required for the selected mode.
- The application or token has not been revoked.
- The Mastodon account is still active and permitted to use the timeline.

### Timeline or account not found

- Enter a hashtag without a URL. A leading `#` is optional.
- Enter an account as `user@example.social`, not as a profile URL.
- Confirm that the account is visible to and known by the instance in `INSTANCE_URL`.
- Open the hashtag or account from the instance's own web interface to confirm that it exists there.

### Rate limit exceeded

Increase `REFRESH_INTERVAL` or the global collector interval. Mastodon applies rate limits per account and IP address; see the [Mastodon rate-limit documentation](https://docs.joinmastodon.org/api/rate-limits/).

### Instance unavailable

Check DNS, TLS certificates, firewall rules, the configured proxy, and whether the instance API is reachable from the collector worker. `INSTANCE_URL` must be the instance origin, not a profile, hashtag, or API URL.

### No new statuses

This is a normal not-modified result. It means the timeline contains no posts newer than the saved cursor, or all returned posts already exist in Taranis.

## Official Mastodon references

- [Timeline API: hashtag and home timelines](https://docs.joinmastodon.org/methods/timelines/)
- [Accounts API: credential verification, lookup, and statuses](https://docs.joinmastodon.org/methods/accounts/)
- [OAuth token types](https://docs.joinmastodon.org/api/oauth-tokens/)
- [OAuth scopes and least-privilege guidance](https://docs.joinmastodon.org/api/oauth-scopes/)
- [OAuth authorization flow](https://docs.joinmastodon.org/client/authorized/)
- [Status response fields](https://docs.joinmastodon.org/entities/Status/)
- [API pagination](https://docs.joinmastodon.org/api/guidelines/#pagination)
- [API rate limits](https://docs.joinmastodon.org/api/rate-limits/)
