"""
core/config_manager.py
Thread-safe persistent configuration manager with strict schema validation.
Enforces security boundaries, prevents password leakage, and manages user defaults.
"""
import json
import os
import threading
from typing import Dict, Any, List

DEFAULT_CONFIG: Dict[str, Any] = {
    "till_username": "",
    "bo_username": "",
    "default_username": "",
    "default_port": 22,
    "default_start_ip_offset": 112,
    "default_till_count": 13,
    "connection_timeout_seconds": 5,
    "store_concurrency": 1,
    "max_workers_per_store": 16,
    "size_tolerance_mb": 0.3,
    "last_ip_or_subnet": "",
    "last_store_code": "",
    "last_specific_tills": "",
    "operation_mode": "version_war",
    "till_war_path": "",
    "till_war_expected_size": "",
    "till_prop_path": "",
    "till_prop_variable": "",
    "till_expected_val": "",
    "bo_war_path": "",
    "bo_war_expected_size": "",
    "bo_prop_path": "",
    "bo_prop_variable": "",
    "bo_expected_val": "",
    "custom_command": "",
    "allowed_subnets": ["10.0.0.0/8", "192.168.0.0/16", "172.16.0.0/12", "127.0.0.1/32"],
    "saved_file_paths": [
        "/home/posuser/ETPSuite/ETPStoreFrontV5.5/app.war",
        "/home/posuser/ETPSuite/ETPStoreFrontV5.5/config/ETPLanguage_en_US.properties",
        "/home/posuser/ETPSuite/ETPBackOffice/app.war",
        "/home/posuser/ETPSuite/ETPBackOffice/config/app.properties"
    ],
    "tender_urls": {
        "pine": "https://pinelab.payment.internal/api/health",
        "pinelab": "https://pinelab.payment.internal/api/health",
        "paytm": "https://paytm.api.internal/health",
        "phonepe": "https://phonepe.api.internal/health",
        "loyalty": "https://loyalty.retailer.com/api/v1/ping"
    },
    "custom_whitelisted_commands": []
}

class ConfigManager:
    def __init__(self, config_file_path: str):
        self.config_path = config_file_path
        self._lock = threading.Lock()
        self._config = self._load()

    def _validate_and_sanitize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        cfg = dict(DEFAULT_CONFIG)
        if not isinstance(raw_data, dict):
            return cfg

        for k, v in raw_data.items():
            if "pass" in k.lower():
                continue

            if k in cfg:
                expected_type = type(DEFAULT_CONFIG[k])
                if isinstance(v, expected_type):
                    cfg[k] = v
                elif expected_type == float and isinstance(v, (int, float)):
                    cfg[k] = float(v)
                elif expected_type == int and isinstance(v, int):
                    cfg[k] = v

        cfg["connection_timeout_seconds"] = max(1, min(30, cfg.get("connection_timeout_seconds", 5)))
        cfg["store_concurrency"] = max(1, min(10, cfg.get("store_concurrency", 1)))
        cfg["size_tolerance_mb"] = max(0.0, min(10.0, cfg.get("size_tolerance_mb", 0.3)))

        return cfg

    def _load(self) -> Dict[str, Any]:
        with self._lock:
            if not os.path.exists(self.config_path):
                return dict(DEFAULT_CONFIG)
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return self._validate_and_sanitize(data)
            except Exception:
                return dict(DEFAULT_CONFIG)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default)

    def set(self, key: str, value: Any):
        self.update({key: value})

    def update(self, mapping: Dict[str, Any]):
        with self._lock:
            for k, v in mapping.items():
                if "pass" not in k.lower():
                    self._config[k] = v

    def save(self):
        with self._lock:
            clean_cfg = {k: v for k, v in self._config.items() if "pass" not in k.lower()}
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(clean_cfg, f, indent=2)
            except Exception:
                pass

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._config)
