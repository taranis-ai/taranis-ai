from __future__ import annotations

import contextlib
import time
from collections.abc import Generator
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from rq.job import Job
from rq.timeouts import JobTimeoutException

from worker.log import logger


PUBLISHER_DIAGNOSTICS_META_KEY = "publisher_diagnostics"
DEFAULT_NETWORK_TIMEOUT = 30


def publisher_display_name(publisher_type: str | None) -> str:
    return {
        "email_publisher": "Email",
        "ftp_publisher": "FTP",
        "sftp_publisher": "SFTP",
    }.get((publisher_type or "").lower(), "Publisher")


class PublisherNetworkTimeout(RuntimeError):
    def __init__(self, publisher_type: str | None, phase: str):
        self.publisher_type = publisher_type
        self.phase = phase
        super().__init__(f"{publisher_display_name(publisher_type)} publisher timed out during {phase}")


@dataclass
class PublisherExecutionContext:
    product_id: str
    publisher_id: str
    job: Job | None = None
    publisher_type: str | None = None
    phase: str | None = None
    failure_phase: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_monotonic: float = field(default_factory=time.monotonic)
    phase_started_at: datetime | None = None
    phase_started_monotonic: float | None = None

    def activate(self) -> Token[PublisherExecutionContext | None]:
        logger.info(
            f"Publisher task started: job={self.job.id if self.job else 'manual'} product={self.product_id} publisher={self.publisher_id}"
        )
        return _current_context.set(self)

    @staticmethod
    def deactivate(token: Token[PublisherExecutionContext | None]) -> None:
        _current_context.reset(token)

    def set_publisher_type(self, publisher_type: str) -> None:
        self.publisher_type = publisher_type.lower()
        self._save_metadata()

    def start_phase(self, phase: str) -> None:
        now_monotonic = time.monotonic()
        if self.phase is not None and self.phase_started_monotonic is not None:
            logger.info(
                f"Publisher phase completed: type={self.publisher_type or 'unknown'} phase={self.phase} "
                f"elapsed={now_monotonic - self.phase_started_monotonic:.3f}s"
            )
        self.phase = phase
        self.phase_started_at = datetime.now(UTC)
        self.phase_started_monotonic = now_monotonic
        self._save_metadata()
        logger.info(
            f"Publisher phase started: type={self.publisher_type or 'unknown'} phase={phase} "
            f"product={self.product_id} publisher={self.publisher_id}"
        )

    def mark_failure(self, phase: str | None = None) -> None:
        self.failure_phase = phase or self.phase

    def finish(self, *, failed: bool = False, phase: str | None = None) -> None:
        now_monotonic = time.monotonic()
        elapsed = now_monotonic - self.started_monotonic
        phase_elapsed = now_monotonic - self.phase_started_monotonic if self.phase_started_monotonic is not None else elapsed
        final_phase = phase or self.failure_phase or self.phase or "unknown"
        outcome = "failed" if failed else "completed"
        logger.info(
            f"Publisher task {outcome}: type={self.publisher_type or 'unknown'} phase={final_phase} "
            f"product={self.product_id} publisher={self.publisher_id} phase_elapsed={phase_elapsed:.3f}s elapsed={elapsed:.3f}s"
        )

    def effective_network_timeout(self, configured_timeout: float) -> float:
        timeout = float(configured_timeout)
        job_timeout = self.job.timeout if self.job else None
        if isinstance(job_timeout, (int, float)) and job_timeout > 0:
            timeout = min(timeout, job_timeout / 2)
        logger.info(
            f"Publisher network timeout: type={self.publisher_type or 'unknown'} timeout={timeout:g}s "
            f"product={self.product_id} publisher={self.publisher_id}"
        )
        return timeout

    def diagnostic_data(self, *, phase: str | None = None) -> dict[str, str]:
        data = {
            "product_id": self.product_id,
            "publisher_id": self.publisher_id,
        }
        if self.publisher_type:
            data["publisher_type"] = self.publisher_type
        selected_phase = phase or self.failure_phase or self.phase
        if selected_phase:
            data["publisher_phase"] = selected_phase
        return data

    def _save_metadata(self) -> None:
        if not self.job:
            return
        metadata: dict[str, Any] = {
            "task_started_at": self.started_at.isoformat(),
            "product_id": self.product_id,
            "publisher_id": self.publisher_id,
        }
        if self.publisher_type:
            metadata["publisher_type"] = self.publisher_type
        if self.phase:
            metadata["phase"] = self.phase
        if self.phase_started_at:
            metadata["phase_started_at"] = self.phase_started_at.isoformat()
        try:
            self.job.meta[PUBLISHER_DIAGNOSTICS_META_KEY] = metadata
            self.job.save_meta()
        except JobTimeoutException:
            raise
        except Exception as exc:
            logger.error(f"Failed to persist publisher phase metadata: exception_type={type(exc).__name__}")


_current_context: ContextVar[PublisherExecutionContext | None] = ContextVar("publisher_execution_context", default=None)


def get_publisher_context() -> PublisherExecutionContext | None:
    return _current_context.get()


def start_publisher_phase(phase: str) -> None:
    if context := get_publisher_context():
        context.start_phase(phase)


def effective_network_timeout(parameters: dict[str, Any]) -> float:
    configured_timeout = parameters.get("NETWORK_TIMEOUT", DEFAULT_NETWORK_TIMEOUT)
    if context := get_publisher_context():
        return context.effective_network_timeout(configured_timeout)
    return float(configured_timeout)


@contextlib.contextmanager
def publisher_network_phase(phase: str, publisher_type: str) -> Generator[None]:
    context = get_publisher_context()
    if context:
        context.start_phase(phase)
    try:
        yield
    except JobTimeoutException:
        if context:
            context.mark_failure(phase)
        raise
    except Exception as exc:
        if context:
            context.mark_failure(phase)
        if isinstance(exc, TimeoutError) or isinstance(exc.__cause__ or exc.__context__, TimeoutError):
            raise PublisherNetworkTimeout(publisher_type, phase) from exc
        raise


@contextlib.contextmanager
def publisher_cleanup() -> Generator[None]:
    """Ignore ordinary cleanup errors while preserving the RQ deadline."""
    try:
        yield
    except JobTimeoutException:
        raise
    except Exception as exc:
        logger.warning(f"Publisher connection cleanup failed: exception_type={type(exc).__name__}")
