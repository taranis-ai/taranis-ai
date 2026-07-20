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
5. Open the new [GitHub release](https://github.com/taranis-ai/taranis-ai/releases), improve the generated description, and verify the attached files.
