"""
models/target.py
Domain models for Stores and Till Targets.
Maintains store_order_index to guarantee strict FCFS ordering in reports.
Supports Re-Audit Mode: Direct specific till targets or per-store specific tills.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re

@dataclass
class TillTarget:
    store_code: str
    till_name: str
    till_num: int
    ip: str
    port: int = 22
    store_order_index: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        return f"{self.store_code} | {self.till_name} ({self.ip})"

@dataclass
class StoreRecord:
    store_code: str
    subnet_or_ip: str
    till_count: int = 13
    start_offset: int = 112
    store_order_index: int = 0
    specific_tills: str = ""
    direct_targets: List[TillTarget] = field(default_factory=list)
    extra_info: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def parse_specific_tills(spec_str: str) -> List[int]:
        if not spec_str or not spec_str.strip():
            return []
        res = set()
        parts = spec_str.replace(';', ',').split(',')
        for p in parts:
            p = p.strip()
            if not p:
                continue
            if '-' in p:
                try:
                    s, e = p.split('-', 1)
                    s_i, e_i = int(s.strip()), int(e.strip())
                    if s_i <= e_i:
                        res.update(range(s_i, e_i + 1))
                except ValueError:
                    pass
            elif p.isdigit():
                res.add(int(p))
        return sorted(list(res))

    def resolve_targets(self, specific_tills_str: str = "") -> List[TillTarget]:
        """
        Generate resolved TillTarget list:
        1. Direct Targets (Re-Audit Mode from failure CSV): Return specific failed tills directly.
        2. UAT 1-Till Rule: If till_count == 1 and 4th octet is NOT .12, use exact IP directly.
        3. Subnet Expansion: Generate tills from start_offset (.112) or specific tills list.
        """
        # Case 1: Direct specific till targets (Re-Audit Mode)
        if self.direct_targets:
            if specific_tills_str and specific_tills_str.strip():
                wanted = set(self.parse_specific_tills(specific_tills_str))
                return [t for t in self.direct_targets if t.till_num in wanted]
            return list(self.direct_targets)

        # Case 2: Standard resolution
        targets: List[TillTarget] = []
        raw = str(self.subnet_or_ip).strip()
        port = 22

        if ":" in raw and not raw.startswith("127."):
            parts_p = raw.split(":")
            if len(parts_p) == 2 and parts_p[1].isdigit():
                raw = parts_p[0]
                port = int(parts_p[1])

        spec_str = specific_tills_str if (specific_tills_str and specific_tills_str.strip()) else self.specific_tills
        spec_list = self.parse_specific_tills(spec_str)

        # Loopback testing support
        if raw.startswith("127.") or raw.lower().startswith("localhost"):
            nums = spec_list if spec_list else list(range(1, self.till_count + 1))
            for i in nums:
                targets.append(TillTarget(
                    store_code=self.store_code,
                    till_name=f"Till-{i:02d}",
                    till_num=i,
                    ip=raw,
                    port=port,
                    store_order_index=self.store_order_index
                ))
            return targets

        clean = raw.split("/")[0].strip()
        parts = [p.strip() for p in clean.rstrip(".").split(".") if p.strip()]

        # Rule 1: UAT 1-Till Rule
        if len(parts) == 4 and parts[3].isdigit():
            last_oct = int(parts[3])
            if self.till_count == 1 and last_oct != 12:
                exact_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.{parts[3]}"
                targets.append(TillTarget(
                    store_code=self.store_code,
                    till_name="Till-01",
                    till_num=1,
                    ip=exact_ip,
                    port=port,
                    store_order_index=self.store_order_index
                ))
                return targets

        # Rule 2: Production Store Subnet
        if len(parts) >= 3:
            prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."
        else:
            prefix = f"{clean.rstrip('.')}. "

        till_numbers = spec_list if spec_list else list(range(1, self.till_count + 1))

        for num in till_numbers:
            last_val = self.start_offset + (num - 1)
            full_ip = f"{prefix}{last_val}"
            targets.append(TillTarget(
                store_code=self.store_code,
                till_name=f"Till-{num:02d}",
                till_num=num,
                ip=full_ip,
                port=port,
                store_order_index=self.store_order_index
            ))

        return targets
