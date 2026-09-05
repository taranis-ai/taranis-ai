# Software Bills of Materials

Taranis publishes two complementary SBOM views for its container images:

- Docker BuildKit generates a platform-specific SPDX SBOM for every image build. These attestations cover the deployed filesystem, including operating-system and installed Python packages, and are attached to the corresponding `linux/amd64` or `linux/arm64` image manifest.
- `uv export` uses the frozen `uv.lock` files to create CycloneDX 1.5 documents for the production Python dependency graphs of `core`, `frontend`, and `worker`. It excludes development and optional dependencies that are not installed in the production image.

The lock-derived CycloneDX document is attached to the final multi-architecture image-index digest as a signed GitHub artifact attestation. Release builds also publish the same JSON document as a directly downloadable GitHub release asset. The `uv` SBOM export feature is currently a preview feature.

Neither view replaces the other: the CycloneDX document describes the reproducible Python dependency graph, while the platform-specific BuildKit document describes what was found in a particular built image. Consumers assessing a deployed image should use both.
