# Security Policy

## Supported Versions

Security fixes are applied to the latest released version and the current `master` branch.
Older releases may receive fixes when the project maintainers determine that the risk and upgrade impact justify backporting.

## Dependency Updates

Python dependency resolution uses uv's `exclude-newer = "1 week"` setting in each component to avoid resolving packages immediately after release.
Dependabot uv updates use the matching seven-day cooldown so automated lockfile updates follow the same policy.

## Reporting a Vulnerability

Please report suspected vulnerabilities through GitHub's private vulnerability reporting for this repository or send an email to taranis@list.ait.ac.at.

Include as much detail as possible:

- affected version or commit;
- vulnerable component or configuration;
- reproduction steps or proof of concept;
- expected impact;
- any known mitigations.

We will acknowledge valid reports and coordinate disclosure timelines through the private report.
