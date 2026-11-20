---
title: "IntelOwl Enrichment"
description: "Configure IntelOwl enrichment for indicators of compromise."
weight: 7
---

Taranis AI can send indicators of compromise (IOCs) to an IntelOwl instance through the disabled-by-default **IntelOwl Bot**. IntelOwl configuration errors, such as disabled or unconfigured analyzers, are reported by IntelOwl and are not worker-connectivity failures.

## Prerequisites

1. Deploy IntelOwl using its supported installation method and wait for its first-run migrations to finish.
2. Create a dedicated IntelOwl API token for Taranis AI.
3. Enable and configure at least one supported analyzer for every IOC type you intend to enrich.
4. In Taranis AI, enable **IOC Bot** and **IntelOwl Bot**. Keep IOC Bot before IntelOwl Bot in the bot run order.

Configure the IntelOwl Bot with:

| Setting | Purpose |
| --- | --- |
| `INTEL_OWL_URL` | IntelOwl URL reachable from the worker container or pod. |
| `INTEL_OWL_API_KEY` | Dedicated IntelOwl API token. |
| `INTEL_OWL_TLS_VERIFY` | Keep enabled except for a local self-signed test instance. |
| `INTEL_OWL_TLP` | TLP shared with IntelOwl; normally `CLEAR`. |
| `INTEL_OWL_POLL_TIMEOUT_SECONDS` | Maximum wait for IntelOwl processing; defaults to 1800 seconds. |

## Supported analyzers

Taranis AI supports the following IntelOwl analyzers for each IOC type. Configure at least one listed analyzer for each type you want to process.

| IOC type | Supported analyzers |
| --- | --- |
| CVE | `NVD_CVE`, `Vulners` |
| IP | `ThreatFox`, `URLhaus`, `AbuseIPDB`, `GreyNoiseCommunity`, `VirusTotal_v3_Get_Observable` |
| Domain | `URLhaus`, `ThreatFox`, `OTXQuery`, `VirusTotal_v3_Get_Observable` |
| URL | `URLhaus`, `UrlScan_Search`, `VirusTotal_v3_Get_Observable` |
| Hash | `MalwareBazaar_Get_Observable`, `YARAify_Search`, `VirusTotal_v3_Get_Observable` |
| Email | `EmailRep`, `HaveIBeenPwned` |

If IntelOwl reports that no analyzer can run, enable a listed analyzer and configure its required provider credentials. Check the job detail for the missing analyzer or credential.

## View enrichment results

You can view enrichment results for matching IOCs in the CTI dialogs for News Items, Stories, Reports, and Assets. Your normal permissions and TLP visibility still apply.

## Security

Use a dedicated token and store it in protected configuration. Do not put IntelOwl or provider credentials in logs, screenshots, commits, or shared configuration files. Use HTTPS with TLS verification outside local development, and enable email analyzers only when the IntelOwl instance is approved to receive email-address IOCs.

See the [IntelOwl installation documentation](https://intelowlproject.github.io/docs/IntelOwl/installation/) and [plugin configuration documentation](https://intelowlproject.github.io/docs/IntelOwl/usage/) for IntelOwl-specific setup.
