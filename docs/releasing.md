# Creating a Release

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

## Template API Contract

Deploy matching Core and Frontend images together when upgrading the template API from `id` to `name`. Update external clients to read `name` in template detail/list responses, send `name` in creation requests, and use `order=name_asc` or `order=name_desc`. Content remains base64 encoded, validation status retains its existing fields, and update/delete URLs still contain the filename. Existing template files need no migration.

Pull the selected published images, restart Core and Frontend, verify readiness, then check template listing, sorting, creation, editing, and deletion. If rolling back, restore both image versions and the corresponding client contract together.

## Assess Clustering Selection

The repeated-clustering fix needs only an updated Frontend image, with no database migration. After pulling and restarting Frontend, verify readiness, reload Assess, cluster two disposable stories, then select one more and cluster again. Only the surviving primary story should remain selected after each merge.
