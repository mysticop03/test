"""
models/result.py
Structured status definitions and audit result representations.
Includes store_order_index for strict deterministic FCFS sorting.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import datetime

class AuditStatus:
    SUCCESS = "SUCCESS"
    SIZE_MISMATCH = "SIZE_MISMATCH"
    VERSION_MISMATCH = "VERSION_MISMATCH"
    BOTH_MISMATCH = "BOTH_MISMATCH"
    FOUND = "FOUND"
    FILE_MISSING = "FILE_MISSING"
    OFFLINE = "OFFLINE"
    TIMEOUT = "TIMEOUT"
    AUTH_FAIL = "AUTH_FAIL"
    ERROR = "ERROR"
    BLOCKED_COMMAND = "BLOCKED_COMMAND"

    @classmethod
    def is_mismatch(cls, status: str) -> bool:
        return status in (cls.SIZE_MISMATCH, cls.VERSION_MISMATCH, cls.BOTH_MISMATCH)

    @classmethod
    def is_failed(cls, status: str) -> bool:
        return status not in (cls.SUCCESS, cls.FOUND)

@dataclass
class AuditResult:
    store_code: str
    till_name: str
    till_num: int
    ip: str
    operation_mode: str          # 'version_war', 'file_info', 'command'
    status: str                  # From AuditStatus
    store_order_index: int = 0   # Ingestion order of the store (0 = Store 1, 1 = Store 2, etc.)
    latency_ms: float = 0.0
    
    # Mode 1 details (WAR & Version)
    war_size: str = "-"
    war_size_bytes: int = 0
    war_expected_bytes: int = 0
    war_modified: str = "-"
    delivery_version: str = "-"
    expected_version: str = "-"
    prop_variable: str = "-"

    # Generic output & preview
    preview_output: str = "-"
    full_output: str = ""
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_success(self) -> bool:
        return self.status in (AuditStatus.SUCCESS, AuditStatus.FOUND)

    @property
    def is_mismatch(self) -> bool:
        return AuditStatus.is_mismatch(self.status)

@dataclass
class AuditSummary:
    total_tills: int = 0
    completed_tills: int = 0
    success_count: int = 0
    size_mismatch_count: int = 0
    version_mismatch_count: int = 0
    both_mismatch_count: int = 0
    missing_count: int = 0
    offline_count: int = 0
    error_count: int = 0
    elapsed_seconds: float = 0.0

    @property
    def total_mismatches(self) -> int:
        return self.size_mismatch_count + self.version_mismatch_count + self.both_mismatch_count

    @property
    def pass_rate_percent(self) -> float:
        if self.completed_tills == 0:
            return 0.0
        return round((self.success_count / self.completed_tills) * 100, 1)
