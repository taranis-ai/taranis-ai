# Creating a Release

## News-item ordering upgrade

The news-item ordering feature adds the `story.news_item_order` JSON column through the normal core startup migration. Existing stories initially display their items in deterministic ID order. Deploy matching published core and frontend images: pull, restart core to complete the migration, restart frontend, then verify core readiness and saving/reloading a multi-item story's order. No image build or separate backfill is required. Story edits and reordering now share ACL/TLP checks; verify read-only source ACLs and insufficient TLP access reject both writes. Verify that users without `ASSESS_UPDATE` can read stories but cannot open the editor or save/reload item order.

For application rollback, restore the previous published images and leave the additive column in place to retain saved orders. Removing the column discards those orders and is not required for rollback.

## Release checklist

1. Make sure the release commit is on `master` and its CI and `:latest` image builds have passed.
2. Run [Release gate tests](https://github.com/taranis-ai/taranis-ai/actions/workflows/release_gate.yml), then wait for it to pass. The workflow checks out the current `master` and runs all gates. Do not tag a release if it fails.
3. Create and push the version tag (replace `1.X.X`):

   ```bash
   git switch master
   git pull --ff-only
   git tag -a 1.X.X -m "1.X.X"
   git push origin 1.X.X
   ```

4. Wait for [Release on pushed tags](https://github.com/taranis-ai/taranis-ai/actions/workflows/release.yaml) to finish successfully.
5. Open the new [GitHub release](https://github.com/taranis-ai/taranis-ai/releases), improve the generated description, and verify the three CycloneDX SBOM files are attached.
6. After authenticating to GHCR, verify the signed CycloneDX attestation attached to an image digest. Replace the example digest with the released image's digest:

   ```bash
   gh attestation verify oci://ghcr.io/taranis-ai/taranis-core@sha256:EXAMPLE \
     --repo taranis-ai/taranis-ai \
     --predicate-type https://cyclonedx.org/bom \
     --signer-workflow taranis-ai/taranis-ai/.github/workflows/release.yaml \
     --bundle-from-oci
   ```

   Repeat this check for `taranis-frontend` and `taranis-worker`.

## Frontend Upgrade Checks

For frontend upgrades, verify row deletion with and without JavaScript: a refused deletion must show a notification and retain the row; native source deletion must return to the source list. Include keyboard/screen-reader checks for named row actions.
Verify that users with module delete permission cannot delete reports/products hidden by ACLs or granted read-only access, or reports above their TLP clearance. Deploy the matching Core image to enforce these checks for both native and enhanced forms.

## Template API Contract

Deploy matching Core and Frontend images together when upgrading the template API from `id` to `name`. Update external clients to read `name` in template detail/list responses, send `name` in creation requests, and use `order=name_asc` or `order=name_desc`. Content remains base64 encoded, validation status retains its existing fields, and update/delete URLs still contain the filename. Existing template files need no migration.

Pull the selected published images, restart Core and Frontend, verify readiness, then check template listing, sorting, creation, editing, and deletion. If rolling back, restore both image versions and the corresponding client contract together.

## Assess Clustering Selection

The repeated-clustering fix needs only an updated Frontend image, with no database migration. After pulling and restarting Frontend, verify readiness, reload Assess, cluster two disposable stories, then select one more and cluster again. Only the surviving primary story should remain selected after each merge.
