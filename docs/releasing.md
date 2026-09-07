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
