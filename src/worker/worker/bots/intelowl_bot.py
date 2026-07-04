# pyright: reportMissingTypeStubs=false

import ipaddress
import re
from typing import Any, Literal, cast

import ioc_fanger
from ioc_finder import find_iocs
from pyintelowl import IntelOwl

from worker.log import logger

from .base_bot import BaseBot
from .tagging_content import _news_item_content_for_tagging


IntelOwlTLP = Literal["WHITE", "GREEN", "AMBER", "RED", "CLEAR"]
StoryPayload = dict[str, Any]
ObservablePayload = dict[str, str]


class IntelOwlBot(BaseBot):
    ioc_types: list[str] = [
        "cves",
        "email_addresses",
        "ipv4s",
        "ipv4_cidrs",
        "ipv6s",
        "domains",
        "urls",
        "md5s",
        "sha1s",
        "sha256s",
        "sha512s",
    ]
    analyzer_map: dict[str, list[str]] = {
        "cve": ["NIST_CVE_DB", "Vulners"],
        "email": ["EmailRep", "HaveIBeenPwned"],
        "ip": ["AbuseIPDB", "GreyNoiseCommunity", "VirusTotal_v3_Get_Observable", "ThreatFox"],
        "domain": ["VirusTotal_v3_Get_Observable", "OTXQuery", "URLhaus", "ThreatFox"],
        "url": ["UrlScan_Search", "URLhaus", "VirusTotal_v3_Get_Observable"],
        "hash": ["MalwareBazaar_Get_Observable", "VirusTotal_v3_Get_Observable", "YARAify_Search"],
    }
    intelowl_classification: dict[str, str] = {
        "cve": "generic",
        "email": "generic",
        "ip": "ip",
        "domain": "domain",
        "url": "url",
        "hash": "hash",
    }

    def __init__(self):
        super().__init__()
        self.type = "INTEL_OWL_BOT"
        self.name = "IntelOwl Bot"
        self.description = "Bot for submitting observables to IntelOwl"

    def execute(self, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
        parameters = parameters or {}
        instance_url = str(parameters.get("INTEL_OWL_URL") or "").strip()
        api_key = str(parameters.get("INTEL_OWL_API_KEY") or "").strip()
        if not instance_url or not api_key:
            raise ValueError("IntelOwl bot requires INTEL_OWL_URL and INTEL_OWL_API_KEY")

        selected_stories, report_stories = self._load_stories(parameters)
        if not selected_stories and not report_stories:
            return {"message": "No stories found", "stories": {}, "reports": {}, "observables": {}, "skipped": [], "errors": []}

        allow_email = self._is_enabled(parameters.get("INTEL_OWL_EMAIL_ENRICHMENT"))
        observables, targets, skipped = self._extract_observables(selected_stories, report_stories, allow_email)
        submitted: dict[str, ObservablePayload] = {}
        errors: list[dict[str, str]] = []
        if observables:
            client = self._create_client(
                instance_url,
                api_key,
                parameters.get("INTEL_OWL_TLS_VERIFY", "true"),
            )
            submitted, errors = self._submit_observables(
                client, observables, instance_url, api_key, str(parameters.get("INTEL_OWL_TLP") or "CLEAR")
            )

        story_results = {
            story_id: {
                "attribute": {
                    "key": "intelowl_enrichment",
                    "value": self._summary(
                        [key for key, target_set in targets.items() if f"story:{story_id}" in target_set], submitted, errors
                    ),
                }
            }
            for story_id in selected_stories
        }
        report_attribute_title = str(parameters.get("REPORT_ATTRIBUTE_TITLE") or "IntelOwl Enrichment")
        report_results = {
            report_id: {
                "attribute_title": report_attribute_title,
                "value": self._summary(
                    [key for key, target_set in targets.items() if f"report:{report_id}" in target_set], submitted, errors
                ),
            }
            for report_id in report_stories
        }

        return {
            "message": f"Submitted {len(submitted)} IntelOwl observables" if observables else "No IntelOwl observables found",
            "stories": story_results,
            "reports": report_results,
            "observables": submitted,
            "skipped": skipped,
            "errors": errors,
        }

    def _create_client(self, instance_url: str, api_key: str, tls_verify: Any) -> IntelOwl:
        certificate: bool | str = self._is_enabled(tls_verify)
        return IntelOwl(token=api_key, instance_url=instance_url.rstrip("/"), certificate=cast(Any, certificate))

    def _load_stories(self, parameters: dict[str, Any]) -> tuple[dict[str, StoryPayload], dict[str, list[StoryPayload]]]:
        filter_data: dict[str, Any] = dict(parameters.get("filter") or {})
        has_story_filter = any(key.lower() in {"story_id", "story_ids"} for key in filter_data)
        has_report_filter = any(key.lower() in {"report_id", "report_ids"} for key in filter_data)
        selected_stories = (
            {story["id"]: story for story in self.get_stories(parameters) if story.get("id")} if has_story_filter or not filter_data else {}
        )

        report_stories: dict[str, list[StoryPayload]] = {}
        for report_id in self._id_list(filter_data.get("report_ids") or filter_data.get("report_id")):
            report = self.core_api.get_report_item(report_id)
            if not isinstance(report, dict) or report.get("error"):
                logger.warning(f"IntelOwl report lookup failed for report {report_id}")
                continue
            report_stories[report_id] = [story for story in report.get("stories", []) if isinstance(story, dict) and story.get("id")]

        if filter_data and not has_story_filter and not has_report_filter:
            selected_stories = {story["id"]: story for story in self.get_stories(parameters) if story.get("id")}

        return selected_stories, report_stories

    def _extract_observables(
        self,
        selected_stories: dict[str, StoryPayload],
        report_stories: dict[str, list[StoryPayload]],
        allow_email: bool,
    ) -> tuple[dict[str, ObservablePayload], dict[str, set[str]], list[dict[str, str]]]:
        observables: dict[str, ObservablePayload] = {}
        targets: dict[str, set[str]] = {}
        skipped: list[dict[str, str]] = []

        for story_id, story in selected_stories.items():
            self._collect_story_observables(story, observables, targets, f"story:{story_id}", skipped, allow_email)

        for report_id, stories in report_stories.items():
            for story in stories:
                self._collect_story_observables(story, observables, targets, f"report:{report_id}", skipped, allow_email)

        return observables, targets, skipped

    def _collect_story_observables(
        self,
        story: StoryPayload,
        observables: dict[str, ObservablePayload],
        targets: dict[str, set[str]],
        target: str,
        skipped: list[dict[str, str]],
        allow_email: bool,
    ) -> None:
        for tag in self._story_tags(story):
            self._add_observable(tag.get("name", ""), tag.get("tag_type", ""), observables, targets, target, skipped, allow_email)

        for news_item in story.get("news_items", []):
            if not isinstance(news_item, dict):
                continue
            for tag in self._story_tags(news_item):
                self._add_observable(tag.get("name", ""), tag.get("tag_type", ""), observables, targets, target, skipped, allow_email)
            for key, values in find_iocs(text=_news_item_content_for_tagging(news_item), included_ioc_types=self.ioc_types).items():
                for value in values:
                    self._add_observable(str(value), key, observables, targets, target, skipped, allow_email)

    def _add_observable(
        self,
        raw_value: str,
        raw_type: str,
        observables: dict[str, ObservablePayload],
        targets: dict[str, set[str]],
        target: str,
        skipped: list[dict[str, str]],
        allow_email: bool,
    ) -> None:
        observable = self._normalize_observable(raw_value, raw_type)
        if observable is None:
            return
        key, observable_type, value = observable
        if observable_type == "email" and not allow_email:
            skipped.append({"type": "email", "value": value, "reason": "email_enrichment_disabled"})
            return
        observables.setdefault(key, {"type": observable_type, "value": value})
        targets.setdefault(key, set()).add(target)

    def _normalize_observable(self, raw_value: str, raw_type: str) -> tuple[str, str, str] | None:
        value = ioc_fanger.fang(str(raw_value or "")).strip().strip(".,;:()[]{}<>\"'")
        if not value:
            return None

        raw_type = str(raw_type or "").lower()
        observable_type = self._observable_type(value, raw_type)
        if observable_type is None:
            return None

        normalized = value.upper() if observable_type == "cve" else value.lower()
        return f"{observable_type}:{normalized}", observable_type, normalized

    def _observable_type(self, value: str, raw_type: str) -> str | None:
        if raw_type in {"cves", "cve"} or re.fullmatch(r"CVE-\d{4}-\d{4,}", value, re.IGNORECASE):
            return "cve"
        if raw_type in {"email_addresses", "email"} or ("@" in value and "." in value.rsplit("@", 1)[-1]):
            return "email"
        if raw_type in {"ipv4s", "ipv4_cidrs", "ipv6s", "ip"} or self._is_ip(value):
            return "ip"
        if raw_type in {"urls", "url"} or value.lower().startswith(("http://", "https://")):
            return "url"
        if raw_type in {"domains", "domain"}:
            return "domain"
        if raw_type in {"md5s", "sha1s", "sha256s", "sha512s", "hash"} or re.fullmatch(r"[a-fA-F0-9]{32,128}", value):
            return "hash"
        return None

    @staticmethod
    def _is_ip(value: str) -> bool:
        with_value = value.split("/", 1)[0]
        try:
            ipaddress.ip_address(with_value)
        except ValueError:
            return False
        return True

    @staticmethod
    def _story_tags(story: StoryPayload) -> list[dict[str, str]]:
        tags = story.get("tags") or []
        if isinstance(tags, dict):
            result = []
            for name, value in tags.items():
                if isinstance(value, dict):
                    result.append({"name": value.get("name", name), "tag_type": value.get("tag_type", "")})
                else:
                    result.append({"name": name, "tag_type": str(value)})
            return result
        if isinstance(tags, list):
            return [tag for tag in tags if isinstance(tag, dict)]
        return []

    def _submit_observables(
        self,
        client: IntelOwl,
        observables: dict[str, ObservablePayload],
        instance_url: str,
        api_key: str,
        tlp: str,
    ) -> tuple[dict[str, ObservablePayload], list[dict[str, str]]]:
        submitted: dict[str, ObservablePayload] = {}
        errors: list[dict[str, str]] = []

        for key, observable in observables.items():
            observable_type = observable["type"]
            try:
                response = client.send_observable_analysis_request(
                    observable["value"],
                    tlp=self._tlp(tlp),
                    analyzers_requested=self.analyzer_map[observable_type],
                    observable_classification=self.intelowl_classification[observable_type],
                    tags_labels=["taranis-ai"],
                )
            except Exception as exc:
                errors.append({"observable": key, "error": self._sanitize_error(str(exc), api_key)})
                continue

            job_id = str(response.get("job_id") or response.get("id") or "")
            submitted[key] = {
                "type": observable_type,
                "value": observable["value"],
                "status": str(response.get("status") or "submitted"),
                "job_id": job_id,
                "url": self._job_url(instance_url, job_id),
            }

        return submitted, errors

    @staticmethod
    def _job_url(instance_url: str, job_id: str) -> str:
        return f"{instance_url.rstrip('/')}/jobs/{job_id}" if job_id else ""

    @staticmethod
    def _summary(keys: list[str], submitted: dict[str, ObservablePayload], errors: list[dict[str, str]]) -> str:
        parts: list[str] = []
        for key in keys:
            if result := submitted.get(key):
                label = f"{result['type']} {result['value']}"
                job = f" job {result['job_id']}" if result.get("job_id") else ""
                url = f" {result['url']}" if result.get("url") else ""
                parts.append(f"{label}: {result['status']}{job}{url}")
        error_by_observable = {error["observable"]: error["error"] for error in errors}
        parts.extend(f"{key}: failed ({error_by_observable[key]})" for key in keys if key in error_by_observable)
        return "IntelOwl enrichment: " + "; ".join(parts) if parts else "IntelOwl enrichment: no submitted observables"

    @staticmethod
    def _sanitize_error(message: str, api_key: str) -> str:
        return message.replace(api_key, "[redacted]") if api_key else message

    @staticmethod
    def _tlp(value: str) -> IntelOwlTLP:
        normalized = value.strip().upper()
        if normalized in {"WHITE", "GREEN", "AMBER", "RED", "CLEAR"}:
            return cast(IntelOwlTLP, normalized)
        return "CLEAR"

    @staticmethod
    def _id_list(value: Any) -> list[str]:
        values = value if isinstance(value, list) else [value]
        return [str(item).strip() for item in values if str(item or "").strip()]

    @staticmethod
    def _is_enabled(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
