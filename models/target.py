"""
models/target.py
Domain models for Stores and Till/BO Targets.
Maintains store_order_index to guarantee strict FCFS ordering in reports.
Supports Re-Audit Mode: Direct specific till targets or per-store specific tills.
Supports Back Office (.15) and Tills (.112+) dual targeting per SYSTEM_RULES_AND_CONDITIONS.md.
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
    is_bo: bool = False
    device_type: str = "TILL"  # "TILL" or "BO"
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        icon = "🏢" if self.is_bo else "🖥️"
        return f"{self.store_code} | {icon} {self.till_name} ({self.ip})"

@dataclass
class StoreRecord:
    store_code: str
    subnet_or_ip: str
    till_count: int = 13
    start_offset: int = 112
    store_order_index: int = 0
    specific_tills: str = ""
    include_tills: bool = True
    include_bo: bool = False
    is_uat: bool = False
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

    def resolve_targets(
        self,
        specific_tills_str: str = "",
        include_tills: Optional[bool] = None,
        include_bo: Optional[bool] = None
    ) -> List[TillTarget]:
        """
        Generate resolved TillTarget list following Section 8.1 strict hierarchy:
        Store 1 -> Store 1 BO (.15) -> Store 1 Till 1 (.112) -> Till 2 (.113) ...
        """
        # Case 1: Direct specific till targets (Re-Audit Mode from failure CSV)
        if self.direct_targets:
            if specific_tills_str and specific_tills_str.strip():
                wanted = set(self.parse_specific_tills(specific_tills_str))
                return [t for t in self.direct_targets if t.till_num in wanted or t.is_bo]
            return list(self.direct_targets)

        do_tills = self.include_tills if include_tills is None else include_tills
        do_bo = self.include_bo if include_bo is None else include_bo

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
            if do_bo:
                targets.append(TillTarget(
                    store_code=self.store_code,
                    till_name="BO-01",
                    till_num=0,
                    ip=raw,
                    port=port,
                    store_order_index=self.store_order_index,
                    is_bo=True,
                    device_type="BO"
                ))
            if do_tills:
                nums = spec_list if spec_list else list(range(1, self.till_count + 1))
                for i in nums:
                    targets.append(TillTarget(
                        store_code=self.store_code,
                        till_name=f"Till-{i:02d}",
                        till_num=i,
                        ip=raw,
                        port=port,
                        store_order_index=self.store_order_index,
                        is_bo=False,
                        device_type="TILL"
                    ))
            return targets

        clean = raw.split("/")[0].strip()
        parts = [p.strip() for p in clean.rstrip(".").split(".") if p.strip()]

        # Section 4.3: UAT 1-Till Rule
        # When UAT is selected, connects exclusively to exact IP entered, ignoring .112 offset and till count
        if self.is_uat or (len(parts) == 4 and parts[3].isdigit() and self.till_count == 1 and int(parts[3]) != 12 and not do_bo):
            exact_ip = ".".join(parts[:4])
            targets.append(TillTarget(
                store_code=self.store_code,
                till_name="Till-01",
                till_num=1,
                ip=exact_ip,
                port=port,
                store_order_index=self.store_order_index,
                is_bo=False,
                device_type="TILL"
            ))
            return targets

        # Subnet Base: A.B.C. (e.g. 192.168.29.)
        if len(parts) >= 3:
            prefix = f"{parts[0]}.{parts[1]}.{parts[2]}."
        else:
            prefix = f"{clean.rstrip('.')}."

        # 1. Back Office (.12) in strict order (Section 8.1 & User Specification)
        if do_bo:
            bo_ip = f"{prefix}12"
            targets.append(TillTarget(
                store_code=self.store_code,
                till_name="BO-01",
                till_num=0,
                ip=bo_ip,
                port=port,
                store_order_index=self.store_order_index,
                is_bo=True,
                device_type="BO"
            ))

        # 2. Tills (.112+ start offset: A.B.C.(111 + i)) (Section 4.2)
        if do_tills:
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
                    store_order_index=self.store_order_index,
                    is_bo=False,
                    device_type="TILL"
                ))

        return targets
