"""
core/config_manager.py
Thread-safe persistent configuration manager.
Stores only saved_file_paths and tender_urls in config.json.
Provides in-memory defaults for internal operational constants.
"""
import json
import os
import threading
from typing import Dict, Any, List

DEFAULT_CONFIG: Dict[str, Any] = {
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
    }
}

# In-memory operational fallbacks for keys not stored in config.json
OPERATIONAL_DEFAULTS: Dict[str, Any] = {
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
    "max_display_rows": 100,
    "allowed_subnets": ["10.0.0.0/8"]
}

class ConfigManager:
    def __init__(self, config_file_path: str):
        self.config_path = config_file_path
        self._lock = threading.RLock()
        self._config = self._load()

    def _validate_and_sanitize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        cfg: Dict[str, Any] = {
            "saved_file_paths": list(DEFAULT_CONFIG["saved_file_paths"]),
            "tender_urls": dict(DEFAULT_CONFIG["tender_urls"])
        }
        if not isinstance(raw_data, dict):
            return cfg

        if "saved_file_paths" in raw_data and isinstance(raw_data["saved_file_paths"], list):
            cfg["saved_file_paths"] = [str(p).strip() for p in raw_data["saved_file_paths"] if str(p).strip()]

        if "tender_urls" in raw_data and isinstance(raw_data["tender_urls"], dict):
            cfg["tender_urls"] = {str(k).strip(): str(v).strip() for k, v in raw_data["tender_urls"].items() if str(k).strip()}

        return cfg

    def _load(self) -> Dict[str, Any]:
        with self._lock:
            if not os.path.exists(self.config_path):
                return {
                    "saved_file_paths": list(DEFAULT_CONFIG["saved_file_paths"]),
                    "tender_urls": dict(DEFAULT_CONFIG["tender_urls"])
                }
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return self._validate_and_sanitize(data)
            except Exception:
                return {
                    "saved_file_paths": list(DEFAULT_CONFIG["saved_file_paths"]),
                    "tender_urls": dict(DEFAULT_CONFIG["tender_urls"])
                }

    def reload(self) -> Dict[str, Any]:
        """Re-reads config.json from disk to capture dynamic user edits immediately."""
        with self._lock:
            self._config = self._load()
            return dict(self._config)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            if key in self._config:
                return self._config[key]
            if default is not None:
                return default
            return OPERATIONAL_DEFAULTS.get(key, None)

    def set(self, key: str, value: Any):
        self.update({key: value})

    def update(self, mapping: Dict[str, Any]):
        with self._lock:
            for k, v in mapping.items():
                if "pass" not in k.lower():
                    self._config[k] = v

    def save(self):
        with self._lock:
            # Strictly save only saved_file_paths and tender_urls
            clean_cfg = {
                "saved_file_paths": self._config.get("saved_file_paths", []),
                "tender_urls": self._config.get("tender_urls", {})
            }
            try:
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(clean_cfg, f, indent=2)
            except Exception:
                pass

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            merged = dict(OPERATIONAL_DEFAULTS)
            merged.update(self._config)
            return merged
