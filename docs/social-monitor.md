# Social monitoring

In **Assess → Social monitor**, choose configured sources and save the combination as a personal beat. **Show new activity** refreshes the feed. Expand a Reddit thread or Mastodon post to inspect individual contributions and images. Select contributions, review the selection, then name a Story or search for an existing one. Reports continue to use Stories.

## Configure collection

- Create a Mastodon source using the [Mastodon setup guide](mastodon.md). New sources deliver to the monitor. Existing sources continue delivering to Stories until an administrator changes **Deliver to**. Monitor collection accepts public statuses. For instances using a separate media server, enter its trusted HTTPS hostname.
- For Reddit, configure the subreddit, approved application client ID and secret, and an identifying user agent. Use credentials approved for your deployment and use case. Each poll reads up to 100 recent submissions and 100 recent comments, fetches their available submissions, and reconciles stored contributions due for review. Schedule polls often enough for the community's volume. Counts describe the replies Taranis has collected. [Reddit API access](https://support.reddithelp.com/hc/en-us/articles/16160319875092)
- Set a collection schedule and run the worker cron process for automatic collection and source rechecks. Source IDs scope upstream identities and access. Private beats store only filters. An attachment creates a source-scoped News Item referencing the contribution, so clustering and reporting retain existing Story membership rules. The original text and media are resolved on display.

## Images and reports

The monitor stores ordered static PNG, JPEG, and WebP assets up to 12 MiB and 40 megapixels apiece. Unavailable attachments retain their position and alternative text. Open a thumbnail to inspect or zoom. Content warnings collapse sensitive material. Videos remain at the original post.

In Analyze, **Insert image from linked Stories** opens the figure picker. Choose images, caption them, set alternative text and order, and save. HTML and PDF products embed the selected images with attribution. Publication requires both the source and the containing Story to be TLP:CLEAR. Source, Story, and Report access are rechecked server-side.

Collector rechecks remove deleted contributions and their stored images. Changing a figure, tightening TLP, or deleting an image requires a fresh render before that product can be distributed again. An already-published edition stays at its URL until republished. External deliveries and previously downloaded documents cannot be recalled. Source administrators should keep Reddit collection and rechecks running while retaining material.
