"""
models/result.py
Structured status definitions and audit result representations.
Includes store_order_index for strict deterministic FCFS sorting.
Implements the 5 distinct status states per Section 7.2 of SYSTEM_RULES_AND_CONDITIONS.md:
Success, Offline, Mismatch, Miss, Blocked.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import datetime

class AuditStatus:
    # 5 Master Standard Status States
    SUCCESS = "Success"
    OFFLINE = "Offline"
    MISMATCH = "Mismatch"
    MISS = "Miss"
    BLOCKED = "Blocked"

    # Backward-compatible mappings
    FOUND = "Success"
    FILE_MISSING = "Miss"
    SIZE_MISMATCH = "Mismatch"
    VERSION_MISMATCH = "Mismatch"
    BOTH_MISMATCH = "Mismatch"
    TIMEOUT = "Offline"
    AUTH_FAIL = "Offline"
    ERROR = "Offline"
    BLOCKED_COMMAND = "Blocked"

    @classmethod
    def is_mismatch(cls, status: str) -> bool:
        return status in (cls.MISMATCH, "SIZE_MISMATCH", "VERSION_MISMATCH", "BOTH_MISMATCH")

    @classmethod
    def is_failed(cls, status: str) -> bool:
        return status not in (cls.SUCCESS, "FOUND")

@dataclass
class AuditResult:
    store_code: str
    till_name: str
    till_num: int
    ip: str
    operation_mode: str          # 'version_war', 'file_info', 'command'
    status: str = AuditStatus.OFFLINE
    store_order_index: int = 0   # Ingestion order of the store
    latency_ms: float = 0.0
    is_bo: bool = False
    device_type: str = "TILL"    # "TILL" or "BO"
    
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
        return self.status == AuditStatus.SUCCESS

    @property
    def is_mismatch(self) -> bool:
        return self.status == AuditStatus.MISMATCH

@dataclass
class AuditSummary:
    total_tills: int = 0
    completed_tills: int = 0
    success_count: int = 0
    mismatch_count: int = 0
    missing_count: int = 0
    offline_count: int = 0
    blocked_count: int = 0
    elapsed_seconds: float = 0.0

    # Compatibility properties
    @property
    def size_mismatch_count(self) -> int:
        return self.mismatch_count

    @property
    def version_mismatch_count(self) -> int:
        return 0

    @property
    def both_mismatch_count(self) -> int:
        return 0

    @property
    def total_mismatches(self) -> int:
        return self.mismatch_count

    @property
    def pass_rate_percent(self) -> float:
        if self.completed_tills == 0:
            return 0.0
        return round((self.success_count / self.completed_tills) * 100, 1)
