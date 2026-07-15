#!/usr/bin/env python3

import argparse
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit


REQUIRED_ANALYZERS: dict[str, list[str]] = {
    "cve": ["NVD_CVE", "Vulners"],
    "email": ["EmailRep", "HaveIBeenPwned"],
    "ip": ["ThreatFox", "URLhaus", "AbuseIPDB", "GreyNoiseCommunity", "VirusTotal_v3_Get_Observable"],
    "domain": ["URLhaus", "ThreatFox", "OTXQuery", "VirusTotal_v3_Get_Observable"],
    "url": ["URLhaus", "UrlScan_Search", "VirusTotal_v3_Get_Observable"],
    "hash": ["MalwareBazaar_Get_Observable", "YARAify_Search", "VirusTotal_v3_Get_Observable"],
}
SAMPLES = {
    "cve": ("CVE-2021-44228", "generic"),
    "ip": ("8.8.8.8", "ip"),
    "domain": ("example.com", "domain"),
    "url": ("https://example.com/", "url"),
    "hash": ("44d88612fea8a8f36de82e1278abb02f", "hash"),
    "email": ("security@example.com", "generic"),
}
ENV_ALIASES: dict[tuple[str, str], list[str]] = {
    ("AbuseIPDB", "api_key_name"): ["ABUSEIPDB_API_KEY"],
    ("EmailRep", "api_key_name"): ["EMAILREP_API_KEY"],
    ("GreyNoiseCommunity", "api_key_name"): ["GREYNOISE_API_KEY", "GREYNOISE_COMMUNITY_API_KEY"],
    ("HaveIBeenPwned", "api_key_name"): ["HIBP_API_KEY", "HAVEIBEENPWNED_API_KEY"],
    ("NVD_CVE", "nvd_api_key"): ["NVD_API_KEY", "NIST_NVD_API_KEY"],
    ("OTXQuery", "api_key_name"): ["OTX_API_KEY", "ALIENVAULT_OTX_API_KEY"],
    ("UrlScan_Search", "api_key_name"): ["URLSCAN_API_KEY"],
    ("Vulners", "api_key_name"): ["VULNERS_API_KEY"],
    ("VirusTotal_v3_Get_Observable", "api_key_name"): ["VIRUSTOTAL_API_KEY", "VT_API_KEY"],
    ("YARAify_Search", "api_key_name"): ["YARAIFY_API_KEY", "MALPEDIA_API_KEY"],
}
ABUSE_CH_ANALYZERS = {"MalwareBazaar_Get_Observable", "ThreatFox", "URLhaus", "YARAify_Search"}
AMBIGUOUS_DISABLED_MESSAGE = "detail endpoint disabled flag is ambiguous"
CHECK_MARK = "\N{CHECK MARK}"
CROSS_MARK = "\N{BALLOT X}"
GREEN = "\033[32m"
RED = "\033[31m"
RESET = "\033[0m"


class IntelOwlRequestError(Exception):
    def __init__(self, message: str, body: Any | None = None):
        super().__init__(message)
        self.body = body


def main() -> int:
    args = parse_args()
    if args.self_test:
        self_test()
        return 0

    api_key = read_api_key(args)
    if not args.url or not api_key:
        print("Set --url plus INTEL_OWL_API_KEY, --api-key, or --api-key-file.", file=sys.stderr)
        return 2

    required = dict(REQUIRED_ANALYZERS)
    settings = load_settings(args.config_file)
    context = None if args.tls_verify else ssl._create_unverified_context()

    if args.apply:
        print("Applying IntelOwl configuration for Taranis AI.")
        apply_configuration(required, args.url, api_key, context, args.timeout, settings)

    probe_ok_ioc_types: set[str] = set()
    probe_had_issues = False
    if args.submit_probes:
        probe_had_issues, probe_ok_ioc_types = print_probe_report(required, args.url, api_key, context, args.timeout)
    else:
        print("\nRuntime probes not submitted. Add --submit-probes for the definitive end-to-end check.")

    configs = fetch_analyzer_configs(args.url, api_key, context, args.timeout, all_analyzers(required))
    had_issues = print_config_report(required, configs, args.strict, probe_ok_ioc_types) or probe_had_issues

    if had_issues and args.apply:
        print("\nRemaining FIX items need provider keys, a newer IntelOwl plugin set, or an admin/org-admin token.")
    print_final_result(had_issues)
    return 1 if had_issues else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check or configure IntelOwl for Taranis AI enrichment.")
    parser.add_argument("--url", default=os.environ.get("INTEL_OWL_URL", ""), help="IntelOwl base URL, for example http://127.0.0.1:18080")
    parser.add_argument("--api-key", default="", help="IntelOwl API token. Prefer INTEL_OWL_API_KEY or --api-key-file.")
    parser.add_argument("--api-key-file", default="", help="Path to a file containing the IntelOwl API token.")
    parser.add_argument("--config-file", default="", help="JSON file with analyzer parameter values to apply.")
    parser.add_argument("--apply", action="store_true", help="Enable analyzers and write supplied plugin parameter values.")
    parser.add_argument(
        "--no-tls-verify", action="store_false", dest="tls_verify", help="Disable TLS verification for local/self-signed instances."
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds.")
    parser.add_argument("--submit-probes", action="store_true", help="Submit sample observables to verify runtime filtering.")
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if any requested analyzer is unavailable.")
    parser.add_argument("--self-test", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def read_api_key(args: argparse.Namespace) -> str:
    if args.api_key_file:
        with open(args.api_key_file, encoding="utf-8") as handle:
            return handle.read().strip()
    return (args.api_key or os.environ.get("INTEL_OWL_API_KEY", "")).strip()


def load_settings(path: str) -> dict[str, Any]:
    if not path:
        return {}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit("--config-file must contain a JSON object")
    return data


def all_analyzers(required: dict[str, list[str]]) -> list[str]:
    return sorted({analyzer for analyzers in required.values() for analyzer in analyzers})


def apply_configuration(
    required: dict[str, list[str]],
    base_url: str,
    api_key: str,
    context: ssl.SSLContext | None,
    timeout: float,
    settings: dict[str, Any],
) -> None:
    analyzers = all_analyzers(required)
    configs = fetch_analyzer_configs(base_url, api_key, context, timeout, analyzers)
    for analyzer in analyzers:
        if analyzer not in configs:
            print(f"  MISSING {analyzer}: cannot configure a plugin IntelOwl does not expose")
            continue
        enable_analyzer(base_url, api_key, context, timeout, analyzer, configs[analyzer])
        configure_plugin_values(base_url, api_key, context, timeout, analyzer, settings)


def enable_analyzer(
    base_url: str,
    api_key: str,
    context: ssl.SSLContext | None,
    timeout: float,
    analyzer: str,
    config: dict[str, Any],
) -> None:
    enable_org_analyzer(base_url, api_key, context, timeout, analyzer)
    if not config.get("disabled") or has_ambiguous_detail_disabled_flag(config):
        return
    try:
        request_json(build_url(base_url, f"/api/analyzer/{analyzer}"), api_key, context, timeout, {"disabled": False}, method="PATCH")
    except IntelOwlRequestError as exc:
        print(f"  WARN {analyzer}: could not enable globally ({short_error(exc)})")
    else:
        print(f"  OK {analyzer}: global disabled flag set to false")


def enable_org_analyzer(
    base_url: str,
    api_key: str,
    context: ssl.SSLContext | None,
    timeout: float,
    analyzer: str,
) -> None:
    try:
        request_json(build_url(base_url, f"/api/analyzer/{analyzer}/organization"), api_key, context, timeout, method="DELETE")
    except IntelOwlRequestError as exc:
        detail = short_error(exc)
        if "already enabled" not in detail.lower() and "permission" not in detail.lower() and "403" not in detail:
            print(f"  WARN {analyzer}: could not enable for organization ({detail})")
    else:
        print(f"  OK {analyzer}: organization disabled flag removed")


def configure_plugin_values(
    base_url: str,
    api_key: str,
    context: ssl.SSLContext | None,
    timeout: float,
    analyzer: str,
    settings: dict[str, Any],
) -> None:
    try:
        config = fetch_plugin_config(base_url, api_key, context, timeout, analyzer)
    except IntelOwlRequestError as exc:
        print(f"  WARN {analyzer}: could not read plugin config ({short_error(exc)})")
        return

    updates: list[dict[str, Any]] = []
    creates: list[dict[str, Any]] = []
    missing_required: list[str] = []
    for param in config.get("user_config", []):
        if not isinstance(param, dict):
            continue
        attribute = str(param.get("attribute") or "")
        value, source = configured_value(analyzer, attribute, param, settings)
        if value is None:
            if param.get("required") and not param.get("exist"):
                missing_required.append(attribute)
            continue
        item = {"parameter": param["parameter"], "value": value, "analyzer_config": analyzer}
        if param.get("exist") and param.get("id"):
            item["id"] = param["id"]
            updates.append(item)
        else:
            creates.append(item)
        print(f"  SET {analyzer}.{attribute}: from {source}")

    if creates:
        try:
            request_json(build_url(base_url, f"/api/analyzer/{analyzer}/plugin_config"), api_key, context, timeout, creates, method="POST")
        except IntelOwlRequestError as exc:
            print(f"  FIX {analyzer}: could not create plugin config ({short_error(exc)})")
    if updates:
        try:
            request_json(build_url(base_url, f"/api/analyzer/{analyzer}/plugin_config"), api_key, context, timeout, updates, method="PATCH")
        except IntelOwlRequestError as exc:
            print(f"  FIX {analyzer}: could not update plugin config ({short_error(exc)})")
    for attribute in missing_required:
        print(f"  FIX {analyzer}.{attribute}: no value supplied; set {env_hint(analyzer, attribute)} or use --config-file")


def configured_value(
    analyzer: str,
    attribute: str,
    param: dict[str, Any],
    settings: dict[str, Any],
) -> tuple[Any | None, str]:
    value = setting_value(settings, analyzer, attribute)
    if value is not None:
        return cast_value(value, str(param.get("type") or "")), "--config-file"

    for env_name in env_candidates(analyzer, attribute):
        if env_name in os.environ:
            return cast_value(os.environ[env_name], str(param.get("type") or "")), env_name

    if attribute == "disable":
        return False, "default"
    return None, ""


def setting_value(settings: dict[str, Any], analyzer: str, attribute: str) -> Any | None:
    analyzer_settings = settings.get(analyzer)
    if isinstance(analyzer_settings, dict) and attribute in analyzer_settings:
        return analyzer_settings[attribute]
    if attribute in settings:
        return settings[attribute]
    return None


def env_candidates(analyzer: str, attribute: str) -> list[str]:
    cleaned_attr = normalize_name(attribute)
    candidates = [
        f"INTELOWL_{normalize_name(analyzer)}_{cleaned_attr}",
        f"INTELOWL_{cleaned_attr}",
    ]
    candidates.extend(ENV_ALIASES.get((analyzer, attribute.lstrip("_")), []))
    candidates.extend(ENV_ALIASES.get((analyzer, attribute), []))
    if analyzer in ABUSE_CH_ANALYZERS and attribute in {"service_api_key", "_service_api_key"}:
        candidates.extend(["ABUSECH_API_KEY", "ABUSE_CH_API_KEY"])
    return list(dict.fromkeys(filter(None, candidates)))


def env_hint(analyzer: str, attribute: str) -> str:
    return env_candidates(analyzer, attribute)[0]


def normalize_name(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value.strip("_").upper()).strip("_")


def cast_value(value: Any, param_type: str) -> Any:
    if not isinstance(value, str):
        return value
    value = value.strip()
    if param_type == "bool":
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if param_type == "int":
        return int(value)
    return value


def fetch_analyzer_configs(
    base_url: str,
    api_key: str,
    context: ssl.SSLContext | None,
    timeout: float,
    required_names: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}
    next_url = build_url(base_url, "/api/analyzer")
    while next_url:
        data = request_json(next_url, api_key, context, timeout)
        items, next_url = unpack_list_response(data)
        next_url = build_url(base_url, next_url) if next_url else ""
        for item in items:
            if isinstance(item, dict) and item.get("name"):
                item = dict(item)
                item["_taranis_config_source"] = "list"
                configs[str(item["name"])] = item

    for analyzer in required_names or []:
        if analyzer in configs:
            continue
        try:
            data = request_json(build_url(base_url, f"/api/analyzer/{analyzer}"), api_key, context, timeout)
        except IntelOwlRequestError:
            continue
        if isinstance(data, dict) and data.get("name"):
            data = dict(data)
            data["_taranis_config_source"] = "detail"
            configs[str(data["name"])] = data
    return configs


def fetch_plugin_config(
    base_url: str,
    api_key: str,
    context: ssl.SSLContext | None,
    timeout: float,
    analyzer: str,
) -> dict[str, Any]:
    data = request_json(build_url(base_url, f"/api/analyzer/{analyzer}/plugin_config"), api_key, context, timeout)
    return data if isinstance(data, dict) else {}


def unpack_list_response(data: Any) -> tuple[list[Any], str]:
    if isinstance(data, list):
        return data, ""
    if isinstance(data, dict):
        results = data.get("results", [])
        return results if isinstance(results, list) else [], str(data.get("next") or "")
    return [], ""


def print_config_report(
    required: dict[str, list[str]],
    configs: dict[str, dict[str, Any]],
    strict: bool,
    probe_ok_ioc_types: set[str] | None = None,
) -> bool:
    probe_ok_ioc_types = probe_ok_ioc_types or set()
    print("\nAnalyzer readiness:")
    had_issues = False
    for ioc_type, analyzers in required.items():
        statuses = [(analyzer, *analyzer_config_status(configs.get(analyzer))) for analyzer in analyzers]
        has_ready_analyzer = any(ok for _, ok, _, _ in statuses)
        if ioc_type in probe_ok_ioc_types and not strict:
            print(f"  OK {ioc_type}: runtime probe accepted")
        for analyzer, ok, mark, message in statuses:
            if ioc_type in probe_ok_ioc_types and not strict and message == AMBIGUOUS_DISABLED_MESSAGE:
                continue
            if not ok and has_ready_analyzer and not strict:
                mark = "WARN"
            print(f"  {mark} {ioc_type}/{analyzer}: {message}")
        if not has_ready_analyzer:
            print(f"  FAIL {ioc_type}: no analyzer is ready")
        had_issues = had_issues or not has_ready_analyzer or (strict and not all(ok for _, ok, _, _ in statuses))
    return had_issues


def analyzer_config_status(config: dict[str, Any] | None) -> tuple[bool, str, str]:
    if config is None:
        return False, "MISSING", "not returned by /api/analyzer"
    if has_ambiguous_detail_disabled_flag(config):
        return True, "WARN", AMBIGUOUS_DISABLED_MESSAGE
    if config.get("disabled"):
        return False, "FIX", "disabled"

    verification_raw = config.get("verification")
    verification = verification_raw if isinstance(verification_raw, dict) else {}
    if verification.get("configured") is False:
        details = str(verification.get("details") or "required secret/config is missing")
        return False, "FIX", details
    return True, "OK", "enabled and configured"


def has_ambiguous_detail_disabled_flag(config: dict[str, Any]) -> bool:
    return bool(config.get("disabled")) and config.get("_taranis_config_source") == "detail" and "verification" not in config


def print_probe_report(
    required: dict[str, list[str]],
    base_url: str,
    api_key: str,
    context: ssl.SSLContext | None,
    timeout: float,
) -> tuple[bool, set[str]]:
    print("\nRuntime probes:")
    had_issues = False
    probe_ok_ioc_types: set[str] = set()
    for ioc_type, analyzers in required.items():
        observable, classification = SAMPLES[ioc_type]
        try:
            response = submit_probe(base_url, api_key, context, timeout, observable, classification, analyzers)
        except IntelOwlRequestError as exc:
            print(f"  FAIL {ioc_type}: {observable}")
            for line in explain_probe_error(exc.body):
                print(f"    {line}")
            had_issues = True
            continue

        job_id = response.get("job_id") or response.get("id") or "unknown"
        status = response.get("status") or "submitted"
        print(f"  OK {ioc_type}: {observable} job={job_id} status={status}")
        probe_ok_ioc_types.add(ioc_type)
    return had_issues, probe_ok_ioc_types


def print_final_result(had_issues: bool) -> None:
    if had_issues:
        print(f"\n{colorize(RED, f'{CROSS_MARK} IntelOwl still needs config')}")
    else:
        print(f"\n{colorize(GREEN, f'{CHECK_MARK} IntelOwl instance is ready for Taranis AI')}")


def colorize(color: str, text: str) -> str:
    if os.environ.get("NO_COLOR"):
        return text
    return f"{color}{text}{RESET}"


def submit_probe(
    base_url: str,
    api_key: str,
    context: ssl.SSLContext | None,
    timeout: float,
    observable: str,
    classification: str,
    analyzers: list[str],
) -> dict[str, Any]:
    payload = {
        "observable_name": observable,
        "observable_classification": classification,
        "analyzers_requested": analyzers,
        "connectors_requested": [],
        "tlp": "CLEAR",
        "tags_labels": ["taranis-ai-config-check"],
        "runtime_configuration": {},
    }
    data = request_json(build_url(base_url, "/api/analyze_observable"), api_key, context, timeout, payload, method="POST")
    return data if isinstance(data, dict) else {}


def request_json(
    url: str,
    api_key: str,
    context: ssl.SSLContext | None,
    timeout: float,
    payload: Any | None = None,
    method: str = "GET",
) -> Any:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Accept": "application/json",
            "Authorization": f"Token {api_key.strip()}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            return parse_json(response.read())
    except urllib.error.HTTPError as exc:
        data = parse_json(exc.read())
        raise IntelOwlRequestError(f"HTTP {exc.code} from {url}", data) from exc
    except urllib.error.URLError as exc:
        raise IntelOwlRequestError(str(exc.reason)) from exc


def parse_json(raw: bytes) -> Any:
    text = raw.decode("utf-8", errors="replace")
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"raw": text}


def explain_probe_error(body: Any) -> list[str]:
    errors = body.get("errors", body) if isinstance(body, dict) else body
    lines: list[str] = []
    if isinstance(errors, dict):
        lines.extend(detail_lines(errors.get("detail")))
        for item in errors.get("analyzers_requested", []):
            lines.append(str(item))
    elif errors:
        lines.append(str(errors))
    return lines or ["No JSON error detail returned."]


def detail_lines(detail: Any) -> Iterable[str]:
    values = detail if isinstance(detail, list) else [detail]
    for value in values:
        if not value:
            continue
        for line in str(value).splitlines():
            if line and not line.startswith("No Analyzers and Connectors can be run"):
                yield line


def short_error(exc: IntelOwlRequestError) -> str:
    lines = explain_probe_error(exc.body)
    return lines[0] if lines else str(exc)


def build_url(base_url: str, path: str) -> str:
    candidate = path if path.startswith(("http://", "https://")) else f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    base = urlsplit(base_url)
    target = urlsplit(candidate)
    if base.scheme not in {"http", "https"} or not base.hostname:
        raise IntelOwlRequestError("IntelOwl base URL must use http or https")
    base_origin = (base.scheme.lower(), base.hostname.lower(), base.port or (443 if base.scheme.lower() == "https" else 80))
    target_origin = (
        target.scheme.lower(),
        target.hostname.lower() if target.hostname else "",
        target.port or (443 if target.scheme.lower() == "https" else 80),
    )
    if target_origin != base_origin:
        raise IntelOwlRequestError("Refusing URL outside the configured IntelOwl origin")
    return candidate


def self_test() -> None:
    assert "INTELOWL_VIRUSTOTAL_V3_GET_OBSERVABLE_API_KEY_NAME" in env_candidates("VirusTotal_v3_Get_Observable", "api_key_name")
    assert read_api_key(argparse.Namespace(api_key=" token\n", api_key_file="")) == "token"
    assert cast_value("true", "bool") is True
    try:
        build_url("https://intelowl.example", "https://attacker.example/api/analyzer?page=2")
    except IntelOwlRequestError:
        pass
    else:
        raise AssertionError("Cross-origin IntelOwl pagination URL was accepted")
    print("self-test ok")


if __name__ == "__main__":
    raise SystemExit(main())
