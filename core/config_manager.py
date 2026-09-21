"""
core/config_manager.py
Thread-safe persistent configuration manager with strict schema validation.
Enforces security boundaries, prevents password leakage, and locks default store concurrency to 2.
"""
import json
import os
import threading
from typing import Dict, Any, List

DEFAULT_CONFIG: Dict[str, Any] = {
    "default_username": "posuser",
    "default_port": 22,
    "default_start_ip_offset": 112,
    "default_till_count": 13,
    "connection_timeout_seconds": 5,
    "store_concurrency": 2,
    "max_workers_per_store": 16,
    "size_tolerance_mb": 0.3,
    "last_ip_or_subnet": "10.14.22.12",
    "last_specific_tills": "1, 2, 5",
    "operation_mode": "version_war",
    "war_path": "/opt/pos/app.war",
    "war_expected_size_bytes": 0,
    "properties_path": "/opt/pos/config/app.properties",
    "properties_keyword": "deliveryversion",
    "expected_delivery_version": "",
    "file_info_path": "/opt/pos/app.war",
    "custom_command": "uptime",
    "cmd_expected_output": "",
    "allowed_subnets": ["10.0.0.0/8", "192.168.0.0/16", "127.0.0.1/32"],
    "allowed_commands": [
        "uptime", "df", "free", "ps", "pgrep", "uname", "date",
        "cat", "head", "tail", "ls", "stat", "hostname", "wc"
    ]
}

class ConfigManager:
    def __init__(self, config_file_path: str):
        self.config_path = config_file_path
        self._lock = threading.Lock()
        self._config = self._load()

    def _validate_and_sanitize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration types and clamp boundary limits."""
        cfg = dict(DEFAULT_CONFIG)
        if not isinstance(raw_data, dict):
            return cfg

        for k, v in raw_data.items():
            # Security: Never load or store passwords in config.json
            if "pass" in k.lower():
                continue

            if k in cfg:
                expected_type = type(DEFAULT_CONFIG[k])
                if isinstance(v, expected_type):
                    cfg[k] = v
                elif expected_type == float and isinstance(v, (int, float)):
                    cfg[k] = float(v)
                elif expected_type == int and isinstance(v, (int, float)):
                    cfg[k] = int(v)

        # Safety clamps
        cfg["connection_timeout_seconds"] = max(1, min(30, int(cfg.get("connection_timeout_seconds", 5))))
        cfg["store_concurrency"] = max(1, min(5, int(cfg.get("store_concurrency", 2))))
        cfg["size_tolerance_mb"] = max(0.0, min(10.0, float(cfg.get("size_tolerance_mb", 0.3))))

        # Subnet validation fallback
        if not cfg.get("allowed_subnets"):
            cfg["allowed_subnets"] = list(DEFAULT_CONFIG["allowed_subnets"])
        if not cfg.get("allowed_commands"):
            cfg["allowed_commands"] = list(DEFAULT_CONFIG["allowed_commands"])

        return cfg

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return self._validate_and_sanitize(data)
            except Exception:
                pass
        return dict(DEFAULT_CONFIG)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._config.get(key, default if default is not None else DEFAULT_CONFIG.get(key))

    def set(self, key: str, value: Any):
        if "pass" in key.lower():
            return  # Never store passwords
        with self._lock:
            self._config[key] = value

    def update(self, mapping: Dict[str, Any]):
        with self._lock:
            for k, v in mapping.items():
                if "pass" not in k.lower():
                    self._config[k] = v

    def save(self):
        with self._lock:
            try:
                # Sanitize output dictionary before writing to disk
                safe_data = {k: v for k, v in self._config.items() if "pass" not in k.lower()}
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(safe_data, f, indent=2)
            except Exception:
                pass

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._config)
