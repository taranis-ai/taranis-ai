# User Documentation

This directory is the source of the documentation published at
<https://taranis.ai/docs/>. The [taranis.ai](https://github.com/taranis-ai/taranis.ai)
website imports it as a Hugo module, so edit the docs here, not in the website
repository.

## Conventions

- Each page needs Hugo front matter (`title`, `description`, `weight`).
  Section pages are named `_index.md`.
- Link to other pages and images with relative paths, for example
  `[Bots](../admin/bots.md)` or `![Dashboard](images/dashboard.png)`, so links
  work both on GitHub and on the website.
- Store images in `images/`. Screenshots taken by the Playwright E2E tests can be
  copied there with `dev/sync_new_pictures.sh`.
- Use GitHub alerts such as `> [!NOTE]` for callouts. Hugo shortcodes do not
  render on GitHub.
- The website sidebar uses Docsy's compact, foldable navigation. Put child pages
  inside their parent section directory so they appear under that section.

## Pages to keep aligned

- The [Backup / Restore guide](admin/backup-restore.md) covers the Docker
  scripts and Kubernetes database and Core PVC recovery. Keep it aligned with
  [`docker/database/`](../../docker/database/) and [`deploy/`](../../deploy/).
- The [Chat guide](chat/_index.md) is paired with
  [provider settings](admin/chat.md) and
  [deployment instructions](getting-started/09_chat.md). Its screenshots
  (`images/chat-*.png`) show the local application's workspace, a live Story
  search, and configured provider settings.

## Preview locally

Clone the website next to this repository, then run the site against your
checkout:

```bash
git clone https://github.com/taranis-ai/taranis.ai.git ../taranis.ai
cd ../taranis.ai
npm ci
HUGO_MODULE_REPLACEMENTS="github.com/taranis-ai/taranis-ai -> $(realpath ../taranis-ai)" hugo server
```

Requirements: Git, Go, Node.js, and Hugo extended (see the website's README for
versions). Edits in this directory reload the preview.

## Publishing

Pull requests that change this directory build the website and check its links.
Merging to `master` triggers a website deployment.
