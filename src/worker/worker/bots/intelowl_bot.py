# pyright: reportMissingTypeStubs=false

import ipaddress
import re
import time
from datetime import datetime, timezone
from typing import Any, Literal, cast

import ioc_fanger
from models.cti import CanonicalIOCType, normalize_ioc_type, normalize_ioc_value
from pyintelowl import IntelOwl

from .base_bot import BaseBot


IntelOwlTLP = Literal["WHITE", "GREEN", "AMBER", "RED", "CLEAR"]
StoryPayload = dict[str, Any]
ObservablePayload = dict[str, Any]


class IntelOwlBot(BaseBot):
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
    final_statuses = {"reported_without_fails", "reported_with_fails", "failed", "killed", "success", "completed"}
    poll_attempts = 3
    poll_delay_seconds = 1.0

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

        selected_stories = self._load_stories(parameters)
        if not selected_stories:
            return self._empty_result("No stories found")

        allow_email = self._is_enabled(parameters.get("INTEL_OWL_EMAIL_ENRICHMENT"))
        observables, skipped = self._extract_observables(selected_stories, allow_email)
        if not observables:
            return self._empty_result("No IntelOwl observables found", skipped=skipped)

        client = self._create_client(instance_url, api_key, parameters.get("INTEL_OWL_TLS_VERIFY", "true"))
        existing = self._load_existing_enrichments(observables)
        enrichments, errors = self._process_observables(
            client,
            observables,
            existing,
            instance_url,
            api_key,
            str(parameters.get("INTEL_OWL_TLP") or "CLEAR"),
        )

        return {
            "message": f"Processed {len(enrichments)} IntelOwl observables",
            "enrichments": enrichments,
            "observables": {f"{item['type']}:{item['value']}": item for item in enrichments},
            "skipped": skipped,
            "errors": errors,
        }

    @staticmethod
    def _empty_result(message: str, skipped: list[dict[str, str]] | None = None) -> dict[str, Any]:
        return {"message": message, "enrichments": [], "observables": {}, "skipped": skipped or [], "errors": []}

    def _create_client(self, instance_url: str, api_key: str, tls_verify: Any) -> IntelOwl:
        certificate: bool | str = self._is_enabled(tls_verify)
        return IntelOwl(token=api_key, instance_url=instance_url.rstrip("/"), certificate=cast(Any, certificate))

    def _load_stories(self, parameters: dict[str, Any]) -> dict[str, StoryPayload]:
        filter_data: dict[str, Any] = dict(parameters.get("filter") or {})
        if any(key.lower() in {"report_id", "report_ids"} for key in filter_data):
            raise ValueError("IntelOwl bot no longer supports report filters")
        return {story["id"]: story for story in self.get_stories(parameters) if isinstance(story, dict) and story.get("id")}

    def _extract_observables(
        self,
        selected_stories: dict[str, StoryPayload],
        allow_email: bool,
    ) -> tuple[dict[str, ObservablePayload], list[dict[str, str]]]:
        observables: dict[str, ObservablePayload] = {}
        skipped: list[dict[str, str]] = []

        for story in selected_stories.values():
            for news_item in story.get("news_items", []):
                if not isinstance(news_item, dict) or not news_item.get("id"):
                    continue
                for tag in self._tags(news_item):
                    self._add_observable(tag.get("name", ""), tag.get("tag_type", ""), observables, skipped, allow_email)

        return observables, skipped

    def _add_observable(
        self,
        raw_value: str,
        raw_type: str,
        observables: dict[str, ObservablePayload],
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
        if isinstance(tags, dict):
            return [
                {"name": value.get("name", name), "tag_type": value.get("tag_type", "")}
                if isinstance(value, dict)
                else {"name": name, "tag_type": str(value)}
                for name, value in tags.items()
            ]
        if isinstance(tags, list):
            return [tag for tag in tags if isinstance(tag, dict)]
        return []

    def _load_existing_enrichments(self, observables: dict[str, ObservablePayload]) -> dict[str, dict[str, Any]]:
        payload = [{"type": observable["type"], "value": observable["value"]} for observable in observables.values()]
        response = self.core_api.get_intelowl_enrichments(payload) or {}
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
        instance_url: str,
        api_key: str,
        tlp: str,
    ) -> tuple[list[ObservablePayload], list[dict[str, str]]]:
        results: dict[str, ObservablePayload] = {}
        pending: dict[str, ObservablePayload] = {}
        errors: list[dict[str, str]] = []

        for key, observable in observables.items():
            current = existing.get(key)
            if current and self._is_final_status(str(current.get("status") or "")):
                continue
            if current and current.get("job_id"):
                pending[key] = {"type": observable["type"], "value": observable["value"], **current}
                continue

            submitted = self._submit_observable(client, observable, instance_url, api_key, tlp)
            results[key] = submitted
            if submitted.get("job_id") and not self._is_final_status(str(submitted.get("status") or "")):
                pending[key] = submitted
            if submitted.get("errors"):
                errors.extend({"observable": key, "error": error.get("message", str(error))} for error in submitted["errors"])

        polled, poll_errors = self._poll_pending_jobs(client, pending, instance_url, api_key)
        results.update(polled)
        errors.extend(poll_errors)
        return list(results.values()), errors

    def _submit_observable(
        self,
        client: IntelOwl,
        observable: ObservablePayload,
        instance_url: str,
        api_key: str,
        tlp: str,
    ) -> ObservablePayload:
        observable_type = observable["type"]
        submitted_at = self._now()
        try:
            response = client.send_observable_analysis_request(
                observable["value"],
                tlp=self._tlp(tlp),
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
            }

        job_id = str(response.get("job_id") or response.get("id") or "")
        return {
            "type": observable_type,
            "value": observable["value"],
            "status": str(response.get("status") or "submitted"),
            "job_id": job_id,
            "job_url": self._job_url(instance_url, job_id),
            "analyzers": [],
            "errors": [],
            "submitted_at": submitted_at,
        }

    def _poll_pending_jobs(
        self,
        client: IntelOwl,
        pending: dict[str, ObservablePayload],
        instance_url: str,
        api_key: str,
    ) -> tuple[dict[str, ObservablePayload], list[dict[str, str]]]:
        results: dict[str, ObservablePayload] = {}
        errors: list[dict[str, str]] = []
        pending = dict(pending)

        for attempt in range(self.poll_attempts):
            for key, enrichment in list(pending.items()):
                job_id = enrichment.get("job_id")
                if not job_id:
                    pending.pop(key, None)
                    continue
                try:
                    job = client.get_job_by_id(job_id)
                except Exception as exc:
                    message = self._sanitize_error(str(exc), api_key)
                    enrichment["errors"] = [{"message": message}]
                    results[key] = enrichment
                    errors.append({"observable": key, "error": message})
                    pending.pop(key, None)
                    continue

                updated = self._compact_job_result(enrichment, job, instance_url)
                results[key] = updated
                if self._is_final_status(str(updated.get("status") or "")):
                    pending.pop(key, None)

            if not pending or attempt == self.poll_attempts - 1:
                break
            time.sleep(self.poll_delay_seconds)

        return results, errors

    def _compact_job_result(self, enrichment: ObservablePayload, job: dict[str, Any], instance_url: str) -> ObservablePayload:
        status = str(job.get("status") or enrichment.get("status") or "")
        job_id = str(job.get("id") or job.get("job_id") or enrichment.get("job_id") or "")
        return {
            **enrichment,
            "status": status,
            "job_id": job_id,
            "job_url": self._job_url(instance_url, job_id) or str(enrichment.get("job_url") or ""),
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
            return [{"message": raw_errors}]
        if isinstance(raw_errors, dict):
            return [raw_errors]
        if isinstance(raw_errors, list):
            return [error if isinstance(error, dict) else {"message": str(error)} for error in raw_errors]
        return []

    @classmethod
    def _compact_value(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value[:4000]
        if isinstance(value, list):
            return [cls._compact_value(item) for item in value[:20]]
        if isinstance(value, dict):
            return {str(key): cls._compact_value(item) for key, item in list(value.items())[:40]}
        return value

    @staticmethod
    def _job_url(instance_url: str, job_id: str) -> str:
        return f"{instance_url.rstrip('/')}/jobs/{job_id}" if job_id else ""

    @classmethod
    def _is_final_status(cls, status: str) -> bool:
        return status.strip().lower() in cls.final_statuses

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
    def _is_enabled(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
