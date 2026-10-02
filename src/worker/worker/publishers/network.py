import math
from typing import Any

from paramiko.ssh_exception import NoValidConnectionsError
from rq import get_current_job

from worker.log import logger


class PublisherNetworkTimeout(RuntimeError):
    def __init__(self, publisher_type: str, operation: str):
        self.publisher_type = publisher_type.lower()
        self.operation = operation
        name = {"email_publisher": "Email", "ftp_publisher": "FTP", "sftp_publisher": "SFTP"}.get(self.publisher_type, "Publisher")
        self.public_message = f"{name} publisher timed out during {operation}"
        super().__init__(self.public_message)


def effective_network_timeout(parameters: dict[str, Any]) -> float:
    """Keep each network wait below a finite positive RQ job timeout."""
    timeout = float(parameters.get("NETWORK_TIMEOUT", 30))
    job = get_current_job()
    job_timeout = job.timeout if job else None
    if isinstance(job_timeout, (int, float)) and math.isfinite(job_timeout) and job_timeout > 0:
        timeout = min(timeout, job_timeout / 2)
    logger.info(f"Publisher effective network timeout: timeout={timeout:g}s")
    return timeout


def is_network_timeout(error: BaseException) -> bool:
    """Recognize socket timeouts, including exceptions wrapped by protocols."""
    pending = [error]
    visited = set()
    while pending:
        current = pending.pop()
        if id(current) in visited:
            continue
        visited.add(id(current))
        if isinstance(current, TimeoutError):
            return True
        if isinstance(current, NoValidConnectionsError):
            pending.extend(current.errors.values())
        if current.__cause__ is not None:
            pending.append(current.__cause__)
        elif current.__context__ is not None:
            pending.append(current.__context__)
    return False
