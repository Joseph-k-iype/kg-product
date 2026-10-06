from typing import Protocol


class JobRunner(Protocol):
    """Execution seam: local PostgreSQL worker today, external queue runner later."""

    def run_once(self, worker_id: str) -> bool: ...
