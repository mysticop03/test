"""
core/probe_engine.py
Re-exports FileChecker as ProbeEngine for seamless backward compatibility.
See core/file_checker.py for the full implementation.
"""
from core.file_checker import (
    FileChecker,
    ProbeEngine,
    format_bytes_human,
    sanitize_file_path,
    sanitize_variable_name,
    extract_variable_value,
    parse_expected_size_safe,
    evaluate_size_match,
    extract_delivery_token,
    extract_trailing_delivery_token,
    matches_value
)

__all__ = [
    "FileChecker",
    "ProbeEngine",
    "format_bytes_human",
    "sanitize_file_path",
    "sanitize_variable_name",
    "extract_variable_value",
    "parse_expected_size_safe",
    "evaluate_size_match",
    "extract_delivery_token",
    "extract_trailing_delivery_token",
    "matches_value"
]
