# Configure IntelOwl for Taranis AI

Taranis AI sends IOC tags to IntelOwl through the disabled-by-default `IntelOwl Bot`. The bot asks IntelOwl for a fixed analyzer set by IOC type. If IntelOwl has those analyzers disabled, unconfigured, or missing, IntelOwl returns HTTP 400 with messages like:

```text
No Analyzers and Connectors can be run after filtering
OTXQuery won't run: is disabled or not configured
Object with name=NVD_CVE does not exist.
```

That is an IntelOwl configuration problem, not a Taranis worker connectivity problem.

## Required IntelOwl Analyzers

| IOC type | IntelOwl analyzers Taranis requests |
| --- | --- |
| CVE | `NVD_CVE`, `Vulners` |
| IP | `ThreatFox`, `URLhaus`, `AbuseIPDB`, `GreyNoiseCommunity`, `VirusTotal_v3_Get_Observable` |
| Domain | `URLhaus`, `ThreatFox`, `OTXQuery`, `VirusTotal_v3_Get_Observable` |
| URL | `URLhaus`, `UrlScan_Search`, `VirusTotal_v3_Get_Observable` |
| Hash | `MalwareBazaar_Get_Observable`, `YARAify_Search`, `VirusTotal_v3_Get_Observable` |
| Email | `EmailRep`, `HaveIBeenPwned` |

Taranis submits email IOC tags like other IOC tags. Email enrichment succeeds only when IntelOwl has at least one requested email analyzer enabled and configured.

## Check or Configure an IntelOwl Instance

Run the read-only config check from this repository:

```bash
read -rs INTEL_OWL_API_KEY
export INTEL_OWL_API_KEY
taranis-intelowl-setup --url http://127.0.0.1:18080
```

In a deployed Docker Compose environment, run it from a worker container:

```bash
docker exec -it taranis-ai-workers-1 taranis-intelowl-setup --url http://intelowl:80
```

To let the script enable analyzers and write supplied plugin secrets/parameters, add `--apply`:

```bash
export VIRUSTOTAL_API_KEY=...
export OTX_API_KEY=...
export ABUSE_CH_API_KEY=...
taranis-intelowl-setup --url http://127.0.0.1:18080 --apply
```

The script never invents provider keys. It can use environment variables or a JSON file:

```json
{
  "NVD_CVE": {"nvd_api_key": "nvd-token"},
  "VirusTotal_v3_Get_Observable": {"api_key_name": "vt-token"},
  "OTXQuery": {"api_key_name": "otx-token"},
  "ThreatFox": {"service_api_key": "abusech-token"},
  "URLhaus": {"service_api_key": "abusech-token"},
  "MalwareBazaar_Get_Observable": {"service_api_key": "abusech-token"}
}
```

```bash
taranis-intelowl-setup --url http://127.0.0.1:18080 --config-file intelowl-secrets.json --apply
```

For a definitive runtime check, submit sample observables. This creates IntelOwl jobs and may consume external provider quota:

```bash
taranis-intelowl-setup --url http://127.0.0.1:18080 --submit-probes
```

If an analyzer such as `NVD_CVE` is active in the IntelOwl UI but the detail API reports it as disabled, trust the runtime probe result. The setup script suppresses that ambiguous warning for IOC types whose probe is accepted.

The script ends with a colored pass/fail line: ready means each Taranis IOC type has at least one usable analyzer, unless `--strict` is set.

For a local self-signed HTTPS instance only:

```bash
taranis-intelowl-setup --url https://127.0.0.1:18443 --no-tls-verify
```

## Configure IntelOwl

1. Start IntelOwl using its supported Docker flow and wait for first-run migrations to finish.
1. Create an IntelOwl API token from the GUI `API Access/Sessions` page, or as an administrator from the Django admin token area.
1. In IntelOwl, open `Plugins` and search each analyzer listed above.
1. For every required analyzer:
   - If it is disabled, enable it for the instance or organization that owns the Taranis API token.
   - If it is unconfigured, open plugin configuration and set the missing required secrets or parameters.
   - If it is missing, update/import IntelOwl plugin definitions or use an IntelOwl version that still provides that analyzer name.
1. Re-run `taranis-intelowl-setup` until every IOC type has at least one `OK` analyzer. For full coverage, make every analyzer report `OK` or run the checker with `--strict`.
1. In Taranis, enable `IntelOwl Bot` and set:
   - `INTEL_OWL_URL`: the URL reachable from the Taranis worker container or pod.
   - `INTEL_OWL_API_KEY`: the IntelOwl token.
   - `INTEL_OWL_TLS_VERIFY`: keep `true` unless this is a local self-signed test instance.
   - `INTEL_OWL_TLP`: usually `CLEAR`.
   - `INTEL_OWL_POLL_TIMEOUT_SECONDS`: defaults to `1800`; stuck IntelOwl jobs are stored as failed after this.

`IOC Bot` must run before `IntelOwl Bot`; the seeded Taranis bot order already sets `IOC_BOT -> INTEL_OWL_BOT`.

## Viewing CTI in Taranis

CTI dialogs show the enrichment rows currently stored for matching IOC values. News items, stories, and reports use extracted IOC tags. Assets can also store typed observables such as CVE, IP, domain, URL, hash, and email values. The asset detail CTI button shows matches for that asset's observables and readable vulnerability reports. The Assets overview CTI button shows the same information across all readable assets.

## Minimal Useful Setup

For a low-cost first setup, configure the current no-paid-plan baseline:

| IOC type | Start with |
| --- | --- |
| CVE | `NVD_CVE` |
| IP | `ThreatFox` or `URLhaus` |
| Domain | `URLhaus` or `ThreatFox` |
| URL | `URLhaus` or `UrlScan_Search` |
| Hash | `MalwareBazaar_Get_Observable` or `YARAify_Search` |
| Email | `EmailRep` |

`NVD_CVE` can run without a paid provider key. The abuse.ch-backed analyzers (`ThreatFox`, `URLhaus`, `MalwareBazaar_Get_Observable`, `YARAify_Search`) need an abuse.ch API key in current IntelOwl, but that is a free account key, not a paid plan. `UrlScan_Search` can search without a key in IntelOwl's search mode, with lower limits. Taranis still requests the full analyzer list. IntelOwl only has to run at least one requested analyzer for a submitted IOC type; disabled or unconfigured siblings can remain unavailable, but each unavailable analyzer will be reported in IntelOwl warnings or errors.

If `NVD_CVE` reports an invalid header value, the NVD API key stored in IntelOwl likely has leading/trailing whitespace. Reapply it through `taranis-intelowl-setup --apply`; supplied string values are trimmed before they are written.

## Common Environment Variables

The setup script also checks generic names like `INTELOWL_<ANALYZER>_<PARAMETER>`, for example `INTELOWL_VIRUSTOTAL_V3_GET_OBSERVABLE_API_KEY_NAME`.

Useful aliases:
- `ABUSEIPDB_API_KEY`
- `ABUSE_CH_API_KEY` or `ABUSECH_API_KEY` for abuse.ch analyzers such as `ThreatFox`, `URLhaus`, and `MalwareBazaar_Get_Observable`
- `ALIENVAULT_OTX_API_KEY` or `OTX_API_KEY`
- `EMAILREP_API_KEY`
- `GREYNOISE_API_KEY`
- `HIBP_API_KEY`
- `NVD_API_KEY`
- `URLSCAN_API_KEY`
- `VIRUSTOTAL_API_KEY`
- `VULNERS_API_KEY`

## Security Notes

- Use a dedicated IntelOwl user/token for Taranis.
- Do not paste the IntelOwl token into logs, screenshots, commits, or shared config files.
- Do not commit `intelowl-secrets.json`; keep provider keys in a local secret store.
- Enable IntelOwl email analyzers only on instances approved to receive email address IOCs.
- Prefer HTTPS and `INTEL_OWL_TLS_VERIFY=true` outside local development.

References:
- IntelOwl installation: https://intelowlproject.github.io/docs/IntelOwl/installation/
- IntelOwl plugin configuration and enablement: https://intelowlproject.github.io/docs/IntelOwl/usage/
- PyIntelOwl token usage: https://github.com/intelowlproject/pyintelowl
