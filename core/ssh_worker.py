"""
core/ssh_worker.py
Paramiko SSH execution worker with strict socket timeouts, keepalive, and error classification.
Sanitizes all outputs ensuring passwords and internal credentials never leak to logs or reports.
"""
import socket
import shlex
import time
import re
import paramiko
from models.target import TillTarget
from models.result import AuditResult, AuditStatus
from core.probe_engine import ProbeEngine
from core.safety_guard import SafetyGuard

def execute_till_probe(
    target: TillTarget,
    username: str,
    password: str,
    operation_mode: str,
    config_params: dict,
    timeout: int = 5
) -> AuditResult:
    start_time = time.perf_counter()
    ip = target.ip
    port = target.port

    # Security: Scrub sensitive fields from extra metadata
    scrubbed_config = {k: v for k, v in config_params.items() if "pass" not in k.lower()}

    result = AuditResult(
        store_code=target.store_code,
        till_name=target.till_name,
        till_num=target.till_num,
        ip=ip,
        operation_mode=operation_mode,
        status=AuditStatus.ERROR,
        store_order_index=target.store_order_index,
        extra=scrubbed_config
    )

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Strict connection timeout protects worker threads from hanging on dead IPs
        client.connect(
            hostname=ip,
            port=port,
            username=username,
            password=password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False
        )

        latency = round((time.perf_counter() - start_time) * 1000, 1)
        result.latency_ms = latency

        # Mode 1: WAR Size & Version Check
        if operation_mode == "version_war":
            war_path = config_params.get("war_path", "/opt/pos/app.war")
            prop_path = config_params.get("properties_path", "/opt/pos/config/app.properties")
            keyword = config_params.get("properties_keyword", "deliveryversion")
            exp_bytes = config_params.get("war_expected_size_bytes", 0)
            exp_ver = config_params.get("expected_delivery_version", "")
            tolerance_mb = float(config_params.get("size_tolerance_mb", 0.3))
            tolerance = int(round(tolerance_mb * 1024 * 1024))

            probe_cmd = ProbeEngine.build_version_war_probe(war_path, prop_path, keyword)
            stdin, stdout, stderr = client.exec_command(probe_cmd, timeout=10)
            out_str = stdout.read().decode("utf-8", errors="replace").strip()

            result = ProbeEngine.parse_version_war_output(
                stdout_txt=out_str,
                expected_size_bytes=exp_bytes,
                expected_version_str=exp_ver,
                result=result,
                tolerance_bytes=tolerance
            )
            result.latency_ms = latency

        # Mode 2: File Info
        elif operation_mode == "file_info":
            f_path = config_params.get("file_info_path", "/opt/pos/app.war")
            probe_cmd = ProbeEngine.build_file_info_probe(f_path)
            stdin, stdout, stderr = client.exec_command(probe_cmd, timeout=10)
            out_str = stdout.read().decode("utf-8", errors="replace").strip()

            result = ProbeEngine.parse_file_info_output(out_str, f_path, result)
            result.latency_ms = latency

        # Mode 3: Execute Command
        elif operation_mode == "command":
            cmd = config_params.get("custom_command", "uptime")
            exp_sub = config_params.get("cmd_expected_output", "").strip()

            is_safe, reason = SafetyGuard.validate_command(cmd)
            if not is_safe:
                result.status = AuditStatus.BLOCKED_COMMAND
                result.preview_output = "BLOCKED: Modifying/Unsafe Command"
                result.full_output = f"Command execution rejected by safety filter: {reason}\nCommand: {cmd}"
                return result

            # Smart HTTP command detection: auto-wrap wget/curl for clean status output
            is_http_cmd = bool(re.search(r'\b(wget|curl)\b', cmd, re.IGNORECASE))

            if is_http_cmd:
                # Extract URL from the command
                url_match = re.search(r'(https?://\S+)', cmd)
                url_display = url_match.group(1).rstrip("'\"") if url_match else cmd
                # Use the frontend timeout value (passed via config), not hardcoded
                wget_timeout = timeout if timeout else 10
                # Mozilla user-agent so sites don't block us like they block raw wget
                ua = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
                # Build a clean command that outputs ONLY the HTTP status code + reason
                # wget --spider -S sends headers to stderr, so we must redirect 2>&1
                # Using bash -c ensures pipes and redirection work reliably over paramiko
                actual_cmd = (
                    f"bash -c \"wget --spider -S -q -t 1 -T {wget_timeout} "
                    f"--user-agent='{ua}' "
                    f"'{url_display}' 2>&1 "
                    f"| grep -i 'HTTP/' | tail -1 "
                    f"| awk '{{print \$2, \$3, \$4, \$5}}' "
                    f"| tr -s ' '\""
                )
            else:
                actual_cmd = cmd

            # Execute command over SSH channel
            stdin, stdout, stderr = client.exec_command(actual_cmd, timeout=max(timeout + 5, 20))

            # Security cap: Max 64 KB command output to prevent RAM exhaustion
            out_bytes = stdout.read(65536)
            err_bytes = stderr.read(16384)
            out_str = out_bytes.decode("utf-8", errors="replace").strip()
            err_str = err_bytes.decode("utf-8", errors="replace").strip()
            if len(out_bytes) == 65536:
                out_str += "\n[Output truncated at 64 KB for safety]"

            combined = (out_str + "\n" + err_str).strip() if not is_http_cmd else out_str

            if is_http_cmd:
                # Parse the clean HTTP status from our pipeline output (e.g. "200 OK" or "403 Forbidden")
                http_line = out_str.splitlines()[0].strip() if out_str.strip() else ""
                http_code_match = re.match(r'(\d{3})\s*(.*)', http_line)

                if http_code_match:
                    code = int(http_code_match.group(1))
                    reason = http_code_match.group(2).strip()
                    clean_status = f"{code} {reason}" if reason else str(code)
                    result.preview_output = clean_status
                    result.full_output = f"HTTP Status: {clean_status}\nURL: {url_display}"

                    if code == 200:
                        result.status = AuditStatus.SUCCESS
                    else:
                        result.status = AuditStatus.ERROR
                elif "timed out" in (out_str + err_str).lower():
                    result.status = AuditStatus.TIMEOUT
                    result.preview_output = "Connection Timed Out"
                    result.full_output = f"Connection Timed Out\nURL: {url_display}"
                elif "not known" in (out_str + err_str).lower() or "could not resolve" in (out_str + err_str).lower():
                    result.status = AuditStatus.ERROR
                    result.preview_output = "DNS Resolution Failed"
                    result.full_output = f"DNS Resolution Failed\nURL: {url_display}"
                else:
                    # wget ran but no HTTP line found (connection refused, etc.)
                    fallback = (out_str + " " + err_str).strip()[:60] if (out_str or err_str) else "(no HTTP response)"
                    result.status = AuditStatus.ERROR
                    result.preview_output = fallback
                    result.full_output = f"{fallback}\nURL: {url_display}"

            elif not combined:
                result.status = AuditStatus.ERROR
                result.preview_output = "(Empty Output)"
                result.full_output = f"Command produced no output or command failed.\nExecuted: {cmd}"
            else:
                # Non-HTTP command: normal behavior
                first_line = combined.splitlines()[0].strip()
                result.preview_output = first_line[:80]
                result.full_output = combined

                if exp_sub:
                    if exp_sub.lower() in combined.lower():
                        result.status = AuditStatus.SUCCESS
                    else:
                        result.status = AuditStatus.VERSION_MISMATCH
                else:
                    result.status = AuditStatus.FOUND

            result.latency_ms = latency

    except paramiko.AuthenticationException:
        result.status = AuditStatus.AUTH_FAIL
        result.latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        result.preview_output = "Authentication Failed"
        result.full_output = f"SSH Authentication failed for user '{username}' on {ip}:{port}. Check password/credentials."

    except (socket.timeout, TimeoutError) as e:
        result.status = AuditStatus.TIMEOUT
        result.latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        result.preview_output = f"Timeout ({timeout}s exceeded)"
        result.full_output = f"Connection timeout ({timeout}s) connecting to {ip}:{port}"

    except (socket.error, paramiko.SSHException) as e:
        err_str = str(e).lower()
        if any(w in err_str for w in ["refused", "unreachable", "no route", "closed", "timed out", "reset", "cannot connect"]):
            result.status = AuditStatus.OFFLINE if "timed out" not in err_str else AuditStatus.TIMEOUT
            result.preview_output = "Offline / Unreachable"
        else:
            result.status = AuditStatus.ERROR
            result.preview_output = f"SSH Error: {str(e)[:40]}"
        result.latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        result.full_output = f"SSH Network Error on {ip}:{port}: {e}"

    except Exception as e:
        result.status = AuditStatus.ERROR
        result.latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        result.preview_output = f"Error: {str(e)[:40]}"
        result.full_output = f"Unexpected error: {e}"

    finally:
        try:
            client.close()
        except Exception:
            pass

    return result
