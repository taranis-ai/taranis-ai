# pyright: reportMissingTypeStubs=false

import ipaddress
import re
import time
from datetime import datetime, timezone
from typing import Any, Literal, cast

import ioc_fanger
from models.cti import CanonicalIOCType, normalize_ioc_type, normalize_ioc_value
from pyintelowl import IntelOwl

from worker.log import logger

from .base_bot import BaseBot


IntelOwlTLP = Literal["WHITE", "GREEN", "AMBER", "RED", "CLEAR"]
StoryPayload = dict[str, Any]
ObservablePayload = dict[str, Any]


class IntelOwlBot(BaseBot):
    analyzer_map: dict[str, list[str]] = {
        "cve": ["NVD_CVE", "Vulners"],
        "email": ["EmailRep", "HaveIBeenPwned"],
        "ip": ["ThreatFox", "URLhaus", "AbuseIPDB", "GreyNoiseCommunity", "VirusTotal_v3_Get_Observable"],
        "domain": ["URLhaus", "ThreatFox", "OTXQuery", "VirusTotal_v3_Get_Observable"],
        "url": ["URLhaus", "UrlScan_Search", "VirusTotal_v3_Get_Observable"],
        "hash": ["MalwareBazaar_Get_Observable", "YARAify_Search", "VirusTotal_v3_Get_Observable"],
    }
    intelowl_classification: dict[str, str] = {
        "cve": "generic",
        "email": "generic",
        "ip": "ip",
        "domain": "domain",
        "url": "url",
        "hash": "hash",
    }
    final_statuses = {"reported_without_fails", "reported_with_fails", "failed", "killed", "success", "completed"}
    poll_delay_seconds = 1.0
    poll_timeout_seconds = 30 * 60

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

        selected_stories = self.get_stories(parameters)
        if not selected_stories:
            return self._empty_result("No stories found")

        observables = self._extract_observables(selected_stories)
        if not observables:
            return self._empty_result("No IntelOwl observables found")

        client = self._create_client(instance_url, api_key, parameters.get("INTEL_OWL_TLS_VERIFY", "true"))
        existing = self._load_existing_enrichments(observables)
        logger.debug(f"Processing {len(observables)} via IntelOwl at {instance_url} with {len(existing)} existing enrichments")
        enrichments, errors = self._process_observables(
            client,
            observables,
            existing,
            api_key,
            cast(IntelOwlTLP, parameters.get("INTEL_OWL_TLP") or "CLEAR"),
            int(parameters.get("INTEL_OWL_POLL_TIMEOUT_SECONDS") or self.poll_timeout_seconds),
        )

        return {
            "message": f"Processed {len(enrichments)} IntelOwl observables",
            "enrichments": enrichments,
            "errors": errors,
        }

    @staticmethod
    def _empty_result(message: str) -> dict[str, Any]:
        return {"message": message, "enrichments": [], "errors": []}

    def _create_client(self, instance_url: str, api_key: str, tls_verify: str) -> IntelOwl:
        return IntelOwl(token=api_key, instance_url=instance_url.rstrip("/"), certificate=cast(Any, tls_verify == "true"))

    def _extract_observables(
        self,
        selected_stories: list[StoryPayload],
    ) -> dict[str, ObservablePayload]:
        observables: dict[str, ObservablePayload] = {}

        for story in selected_stories:
            for news_item in story.get("news_items", []):
                if not isinstance(news_item, dict) or not news_item.get("id"):
                    continue
                for tag in self._tags(news_item):
                    self._add_observable(tag.get("name", ""), tag.get("tag_type", ""), observables)

        return observables

    def _add_observable(
        self,
        raw_value: str,
        raw_type: str,
        observables: dict[str, ObservablePayload],
    ) -> None:
        observable = self._normalize_observable(raw_value, raw_type)
        if observable is None:
            return
        key, observable_type, value = observable
        observables.setdefault(key, {"type": observable_type, "value": value})

    def _normalize_observable(self, raw_value: str, raw_type: str) -> tuple[str, CanonicalIOCType, str] | None:
        value = ioc_fanger.fang(str(raw_value or "")).strip().strip(".,;:()[]{}<>\"'")
        if not value:
            return None

        observable_type = normalize_ioc_type(raw_type) or self._observable_type(value)
        if observable_type is None:
            return None

        normalized = normalize_ioc_value(value, observable_type)
        return f"{observable_type}:{normalized}", observable_type, normalized

    def _observable_type(self, value: str) -> CanonicalIOCType | None:
        if re.fullmatch(r"CVE-\d{4}-\d{4,}", value, re.IGNORECASE):
            return "cve"
        if "@" in value and "." in value.rsplit("@", 1)[-1]:
            return "email"
        if self._is_ip(value):
            return "ip"
        if value.lower().startswith(("http://", "https://")):
            return "url"
        if re.fullmatch(r"[a-fA-F0-9]{32,128}", value):
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
    def _tags(item: StoryPayload) -> list[dict[str, str]]:
        tags = item.get("tags") or []
        if isinstance(tags, list):
            return [tag for tag in tags if isinstance(tag, dict)]
        return []

    def _load_existing_enrichments(self, observables: dict[str, ObservablePayload]) -> dict[str, dict[str, Any]]:
        payload = [{"type": observable["type"], "value": observable["value"]} for observable in observables.values()]
        response = self.core_api.get_iocs(payload) or {}
        items = response.get("items", []) if isinstance(response, dict) else []
        existing: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            if not (ioc_type := normalize_ioc_type(item.get("ioc_type") or item.get("type"))):
                continue
            value = normalize_ioc_value(str(item.get("value") or ""), ioc_type)
            if value:
                existing[f"{ioc_type}:{value}"] = item
        return existing

    def _process_observables(
        self,
        client: IntelOwl,
        observables: dict[str, ObservablePayload],
        existing: dict[str, dict[str, Any]],
        api_key: str,
        tlp: IntelOwlTLP,
        poll_timeout_seconds: int,
    ) -> tuple[list[ObservablePayload], list[dict[str, str]]]:
        results: dict[str, ObservablePayload] = {}
        errors: list[dict[str, str]] = []

        for key, observable in observables.items():
            current = existing.get(key)
            if current and self._is_final_status(str(current.get("status") or "")):
                continue

            submitted, job_id = self._submit_observable(client, observable, api_key, tlp)
            final = self._wait_for_job(client, submitted, job_id, api_key, poll_timeout_seconds) if job_id else submitted
            results[key] = final
            if final.get("errors"):
                errors.extend({"observable": key, "error": error.get("message", str(error))} for error in final["errors"])
        return list(results.values()), errors

    def _submit_observable(
        self,
        client: IntelOwl,
        observable: ObservablePayload,
        api_key: str,
        tlp: IntelOwlTLP,
    ) -> tuple[ObservablePayload, str]:
        observable_type = observable["type"]
        submitted_at = self._now()
        try:
            response = client.send_observable_analysis_request(
                observable["value"],
                tlp=tlp,
                analyzers_requested=self.analyzer_map[observable_type],
                observable_classification=self.intelowl_classification[observable_type],
                tags_labels=["taranis-ai"],
            )
        except Exception as exc:
            return {
                "type": observable_type,
                "value": observable["value"],
                "status": "failed",
                "analyzers": [],
                "errors": [{"message": self._sanitize_error(str(exc), api_key)}],
                "submitted_at": submitted_at,
                "completed_at": submitted_at,
            }, ""

        job_id = str(response.get("job_id") or response.get("id") or "")
        status = str(response.get("status") or "submitted")
        is_final = self._is_final_status(status)
        if not job_id and not is_final:
            return (
                {
                    "type": observable_type,
                    "value": observable["value"],
                    "status": "failed",
                    "analyzers": [],
                    "errors": [{"message": "IntelOwl response did not include a job id"}],
                    "submitted_at": submitted_at,
                    "completed_at": submitted_at,
                },
                "",
            )
        return (
            {
                "type": observable_type,
                "value": observable["value"],
                "status": status,
                "analyzers": [],
                "errors": [],
                "submitted_at": submitted_at,
                "completed_at": submitted_at if is_final else None,
            },
            job_id,
        )

    def _wait_for_job(
        self,
        client: IntelOwl,
        enrichment: ObservablePayload,
        job_id: str,
        api_key: str,
        poll_timeout_seconds: int,
    ) -> ObservablePayload:
        deadline = time.monotonic() + poll_timeout_seconds
        while True:
            try:
                job = client.get_job_by_id(job_id)
            except Exception as exc:
                message = self._sanitize_error(str(exc), api_key)
                return {
                    **enrichment,
                    "status": "failed",
                    "errors": [{"message": message}],
                    "completed_at": self._now(),
                }

            enrichment = self._compact_job_result(enrichment, job)
            if self._is_final_status(str(enrichment.get("status") or "")):
                return enrichment
            if time.monotonic() >= deadline:
                return {
                    **enrichment,
                    "status": "failed",
                    "errors": [{"message": f"IntelOwl job timed out after {poll_timeout_seconds} seconds"}],
                    "completed_at": self._now(),
                }
            time.sleep(min(self.poll_delay_seconds, max(0, deadline - time.monotonic())))

    def _compact_job_result(self, enrichment: ObservablePayload, job: dict[str, Any]) -> ObservablePayload:
        status = str(job.get("status") or enrichment.get("status") or "")
        return {
            **enrichment,
            "status": status,
            "analyzers": self._compact_analyzers(job),
            "errors": self._compact_errors(job) or enrichment.get("errors") or [],
            "completed_at": self._now() if self._is_final_status(status) else None,
        }

    def _compact_analyzers(self, job: dict[str, Any]) -> list[dict[str, Any]]:
        reports = job.get("analyzer_reports") or job.get("reports") or job.get("analyzers") or []
        if isinstance(reports, dict):
            reports = [
                dict(value, name=name) if isinstance(value, dict) else {"name": name, "report": value} for name, value in reports.items()
            ]
        if not isinstance(reports, list):
            return []

        compact = []
        for report in reports:
            if not isinstance(report, dict):
                continue
            item = {
                key: self._compact_value(report[value_key])
                for key, value_key in {
                    "name": "name",
                    "analyzer_name": "analyzer_name",
                    "status": "status",
                    "report": "report",
                    "result": "result",
                    "data": "data",
                    "errors": "errors",
                    "error": "error",
                }.items()
                if value_key in report and report[value_key] not in (None, "")
            }
            if item:
                compact.append(item)
        return compact

    @classmethod
    def _compact_errors(cls, job: dict[str, Any]) -> list[dict[str, Any]]:
        raw_errors = job.get("errors") or job.get("error") or []
        if isinstance(raw_errors, str):
            return [{"message": cls._compact_value(raw_errors)}]
        if isinstance(raw_errors, dict):
            return [cls._compact_error(raw_errors)]
        if isinstance(raw_errors, list):
            return [cls._compact_error(error) for error in raw_errors]
        return []

    @classmethod
    def _compact_error(cls, error: Any) -> dict[str, Any]:
        if isinstance(error, dict):
            return {str(key): cls._compact_value(value) for key, value in list(error.items())[:40]}
        return {"message": cls._compact_value(str(error))}

    @classmethod
    def _compact_value(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value[:4000]
        if isinstance(value, list):
            return [cls._compact_value(item) for item in value[:20]]
        if isinstance(value, dict):
            return {str(key): cls._compact_value(item) for key, item in list(value.items())[:40]}
        return value

    @classmethod
    def _is_final_status(cls, status: str) -> bool:
        return status.strip().lower() in cls.final_statuses

    @staticmethod
    def _sanitize_error(message: str, api_key: str) -> str:
        return message.replace(api_key, "[redacted]") if api_key else message

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
