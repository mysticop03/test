"""
core/ssh_worker.py
Paramiko SSH execution worker with strict socket timeouts, keepalive, and error classification.
Supports dual credentials and parameters for Tills (.112+) and Back Office (.15).
Executes commands including piped commands (e.g. 'ps -ef | grep jre') and dotnet safely.
Implements the 5 standard status states: Success, Offline, Mismatch, Miss, Blocked.
"""
import socket
import shlex
import time
import re
from typing import List, Optional, Union, Dict, Any, Callable
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
    timeout: int = 5,
    on_sub_result: Optional[Callable[[AuditResult], None]] = None
) -> Union[AuditResult, List[AuditResult]]:
    start_time = time.perf_counter()
    ip = target.ip
    port = target.port

    # Build candidate credentials to test (primary + seamless fallback)
    if target.is_bo:
        primary_user = config_params.get("bo_username") or username or ""
        primary_pass = config_params.get("bo_password") or password or ""
        alt_user = config_params.get("till_username") or ""
        alt_pass = config_params.get("till_password") or ""
    else:
        primary_user = config_params.get("till_username") or username or ""
        primary_pass = config_params.get("till_password") or password or ""
        alt_user = config_params.get("bo_username") or ""
        alt_pass = config_params.get("bo_password") or ""

    candidates = []
    def add_cand(u, p):
        cu = (u or "").strip()
        cp = (p or "").strip("\r\n")
        if cu and (cu, cp) not in candidates:
            candidates.append((cu, cp))

    add_cand(primary_user, primary_pass)
    if alt_user and alt_user != primary_user:
        add_cand(alt_user, primary_pass)
    if alt_pass and alt_pass != primary_pass:
        add_cand(primary_user, alt_pass)
    if alt_user and alt_pass and (alt_user != primary_user or alt_pass != primary_pass):
        add_cand(alt_user, alt_pass)

    if not candidates:
        candidates.append(((primary_user or "").strip(), (primary_pass or "").strip("\r\n")))

    target_user = primary_user
    target_pass = primary_pass

    # Scrub credentials from extra metadata
    scrubbed_config = {k: v for k, v in config_params.items() if "pass" not in k.lower()}

    result = AuditResult(
        store_code=target.store_code,
        till_name=target.till_name,
        till_num=target.till_num,
        ip=ip,
        operation_mode=operation_mode,
        status=AuditStatus.OFFLINE,
        store_order_index=target.store_order_index,
        is_bo=target.is_bo,
        device_type=target.device_type,
        extra=scrubbed_config
    )

    # Pre-parse command & URLs so exception handlers always have safe scope references
    cmd = config_params.get("custom_command", "").strip()
    urls: List[str] = [u.rstrip(',; "\'') for u in re.findall(r'https?://[^\s,;"\'<>]+', cmd)] if (cmd and operation_mode in ("command", "terminal")) else []

    client = None
    last_auth_exc = None

    try:
        # Multi-candidate connection: tries primary credentials, then seamless fallbacks
        for c_user, c_pass in candidates:
            candidate_client = paramiko.SSHClient()
            candidate_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                candidate_client.connect(
                    hostname=ip,
                    port=port,
                    username=c_user,
                    password=c_pass if c_pass else None,
                    timeout=timeout,
                    banner_timeout=max(15, timeout * 2),
                    auth_timeout=max(15, timeout * 2),
                    look_for_keys=True,
                    allow_agent=True
                )
                client = candidate_client
                target_user = c_user
                target_pass = c_pass
                break
            except paramiko.AuthenticationException as ae:
                last_auth_exc = ae
                try:
                    candidate_client.close()
                except Exception:
                    pass
                continue
            except Exception:
                try:
                    candidate_client.close()
                except Exception:
                    pass
                raise

        if client is None:
            if last_auth_exc is not None:
                raise last_auth_exc
            raise paramiko.SSHException(f"Failed to establish SSH connection to {ip}:{port}")

        latency = round((time.perf_counter() - start_time) * 1000, 1)
        result.latency_ms = latency

        # Mode 1: File Check & Mode 2: Version Check
        if operation_mode in ("version_war", "file_check", "version_check"):
            # Device-specific config (Till vs Back Office)
            if target.is_bo:
                war_path = config_params.get("bo_war_path", "")
                prop_path = config_params.get("bo_prop_path", "")
                variable = config_params.get("bo_prop_variable", "timeout")
                exp_size = config_params.get("bo_war_expected_size", "")
                exp_val = config_params.get("bo_expected_val", "")
            else:
                war_path = config_params.get("till_war_path", "")
                prop_path = config_params.get("till_prop_path", "")
                variable = config_params.get("till_prop_variable", "timeout")
                exp_size = config_params.get("till_war_expected_size", "")
                exp_val = config_params.get("till_expected_val", "")

            tolerance_mb = float(config_params.get("size_tolerance_mb", 0.3))
            tolerance_bytes = int(round(tolerance_mb * 1024 * 1024))

            probe_cmd = ProbeEngine.build_version_war_probe(war_path, prop_path, variable)
            stdin, stdout, stderr = client.exec_command(probe_cmd, timeout=max(timeout + 3, 6))
            out_str = stdout.read().decode("utf-8", errors="replace").strip()

            result = ProbeEngine.parse_version_war_output(
                stdout_txt=out_str,
                expected_size_bytes=exp_size,
                expected_val_str=exp_val,
                result=result,
                tolerance_bytes=tolerance_bytes,
                is_delivery_mode=(operation_mode == "version_check")
            )
            result.latency_ms = latency

        # Mode 2: Command / Terminal Console Execution
        elif operation_mode in ("command", "terminal"):
            cmd = config_params.get("custom_command", "uptime").strip()
            exp_sub = config_params.get("cmd_expected_output", "").strip()

            # Enforce Section 1.1 (Tills) & 1.2 (Back Office) SafetyGuard rules
            is_safe, reason = SafetyGuard.validate_command(cmd, is_bo=target.is_bo)
            if not is_safe:
                result.status = AuditStatus.BLOCKED
                result.preview_output = "BLOCKED: Security Violation"
                result.full_output = f"[BLOCKED BY POLICY] {reason}\nTarget: {target.display_name}\nCommand: {cmd}"
                return result

            # Detect HTTP URL checks (supports multiple comma/space separated URLs strictly with wget e.g. "wget https://google.com, https://youtube.com")
            urls = [u.rstrip(',; "\'') for u in re.findall(r'https?://[^\s,;"\'<>]+', cmd)]
            is_http_cmd = len(urls) > 0 and cmd.strip().lower().startswith("wget")

            if is_http_cmd:
                http_timeout = timeout if timeout else 5
                ua = "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0"
                prefix_tool = "wget "

                sub_results: List[AuditResult] = []

                for url_idx, url_display in enumerate(urls, start=1):
                    url_start = time.perf_counter()
                    # Enforce strict OS timeout:
                    # Linux 'timeout {http_timeout}s wget ...' guarantees process termination within http_timeout seconds!
                    actual_cmd = (
                        f"timeout {http_timeout}s wget --spider -S -t 1 -T {http_timeout} "
                        f"--dns-timeout={http_timeout} --connect-timeout={http_timeout} "
                        f"--prefer-family=IPv4 --user-agent='{ua}' '{url_display}' 2>&1"
                    )
                    run_cmd = f"bash -c {shlex.quote(actual_cmd)}"

                    url_res = AuditResult(
                        store_code=target.store_code,
                        till_name=target.till_name,
                        till_num=target.till_num,
                        ip=target.ip,
                        store_order_index=target.store_order_index,
                        is_bo=target.is_bo,
                        device_type=target.device_type,
                        operation_mode=operation_mode,
                        extra={"url": url_display, "custom_command": cmd}
                    )

                    try:
                        stdin, stdout, stderr = client.exec_command(run_cmd, timeout=max(http_timeout + 3, 7))
                        out_bytes = stdout.read(65536)
                        err_bytes = stderr.read(16384)
                        out_str = out_bytes.decode("utf-8", errors="replace").strip()
                        err_str = err_bytes.decode("utf-8", errors="replace").strip()
                        combined = (out_str + "\n" + err_str).strip() if err_str else out_str
                        url_latency = round((time.perf_counter() - url_start) * 1000, 1)
                        url_res.latency_ms = url_latency

                        # Strictly capture 3-digit numeric HTTP status code (e.g. 200, 301, 404, 500)
                        http_match = re.search(r'HTTP/[0-9.]+\s+(\d{3})\b', combined, re.IGNORECASE)
                        if http_match:
                            code = int(http_match.group(1))
                            # Strictly status code for display and export:
                            url_res.preview_output = str(code)
                            url_res.full_output = (
                                f"URL: {url_display}\n"
                                f"Command: {prefix_tool}{url_display}\n"
                                f"Target Machine: {target.display_name}\n"
                                f"HTTP Status Code: {code}\n"
                                f"Latency: {url_latency} ms"
                            )
                            url_res.status = AuditStatus.SUCCESS if code in (200, 301, 302, 307, 308) else AuditStatus.OFFLINE
                        elif any(w in combined.lower() for w in ["timed out", "timeout", "operation timed out"]) or url_latency >= (http_timeout * 1000 * 0.95):
                            url_res.status = AuditStatus.OFFLINE
                            url_res.preview_output = f"Timeout ({http_timeout}s)"
                            url_res.full_output = (
                                f"URL: {url_display}\n"
                                f"Command: {prefix_tool}{url_display}\n"
                                f"Target Machine: {target.display_name}\n"
                                f"HTTP Status Code: Timeout ({http_timeout}s)\n"
                                f"Latency: {url_latency} ms"
                            )
                        elif any(w in combined.lower() for w in ["could not resolve", "unable to resolve", "name or service not known"]):
                            url_res.status = AuditStatus.OFFLINE
                            url_res.preview_output = "DNS Failed"
                            url_res.full_output = (
                                f"URL: {url_display}\n"
                                f"Command: {prefix_tool}{url_display}\n"
                                f"Target Machine: {target.display_name}\n"
                                f"HTTP Status Code: DNS Failed\n"
                                f"Latency: {url_latency} ms"
                            )
                        elif any(w in combined.lower() for w in ["connection refused", "network is unreachable", "no route to host"]):
                            url_res.status = AuditStatus.OFFLINE
                            url_res.preview_output = "Refused"
                            url_res.full_output = (
                                f"URL: {url_display}\n"
                                f"Command: {prefix_tool}{url_display}\n"
                                f"Target Machine: {target.display_name}\n"
                                f"HTTP Status Code: Connection Refused\n"
                                f"Latency: {url_latency} ms"
                            )
                        else:
                            url_res.status = AuditStatus.OFFLINE
                            url_res.preview_output = "Failed"
                            url_res.full_output = (
                                f"URL: {url_display}\n"
                                f"Command: {prefix_tool}{url_display}\n"
                                f"Target Machine: {target.display_name}\n"
                                f"HTTP Status Code: Failed\n"
                                f"Latency: {url_latency} ms"
                            )

                    except (socket.timeout, TimeoutError):
                        url_latency = round((time.perf_counter() - url_start) * 1000, 1)
                        url_res.latency_ms = url_latency
                        url_res.status = AuditStatus.OFFLINE
                        url_res.preview_output = f"Timeout ({http_timeout}s)"
                        url_res.full_output = (
                            f"URL: {url_display}\n"
                            f"Command: {prefix_tool}{url_display}\n"
                            f"Target Machine: {target.display_name}\n"
                            f"HTTP Status Code: Timeout ({http_timeout}s)\n"
                            f"Latency: {url_latency} ms"
                        )

                    sub_results.append(url_res)
                    if on_sub_result:
                        try:
                            on_sub_result(url_res)
                        except Exception:
                            pass

                return sub_results if len(sub_results) > 1 else sub_results[0]
            else:
                actual_cmd = cmd

                # Piped or compound commands (e.g. 'ps -ef | grep jre' or 'uptime; free -h') safely executed via bash -c
                if any(c in actual_cmd for c in ["|", ">", "<", ";", "&", " "]):
                    run_cmd = f"bash -c {shlex.quote(actual_cmd)}"
                else:
                    run_cmd = actual_cmd

                try:
                    stdin, stdout, stderr = client.exec_command(run_cmd, timeout=max(timeout + 3, 7))
                    out_bytes = stdout.read(65536)
                    err_bytes = stderr.read(16384)
                except (socket.timeout, TimeoutError):
                    result.latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
                    result.status = AuditStatus.OFFLINE
                    result.preview_output = f"Cmd Timeout ({timeout}s)"
                    result.full_output = f"Command timed out after {timeout}s on {target.display_name} ({ip}:{port}):\n{cmd}"
                    return result

                out_str = out_bytes.decode("utf-8", errors="replace").strip()
                err_str = err_bytes.decode("utf-8", errors="replace").strip()

                if len(out_bytes) == 65536:
                    out_str += "\n[Output capped at 64 KB for safety]"

                combined = (out_str + "\n" + err_str).strip() if err_str else out_str

                if not combined:
                    result.status = AuditStatus.SUCCESS
                    result.preview_output = "(Empty Output)"
                    result.full_output = f"Command completed with empty output.\nCommand: {cmd}"
                else:
                    first_line = combined.splitlines()[0].strip()
                    result.preview_output = first_line[:80]
                    result.full_output = combined

                    if exp_sub:
                        if exp_sub.lower() in combined.lower():
                            result.status = AuditStatus.SUCCESS
                        else:
                            result.status = AuditStatus.MISMATCH
                    else:
                        result.status = AuditStatus.SUCCESS

                result.latency_ms = latency

    except paramiko.AuthenticationException:
        result.status = AuditStatus.OFFLINE
        result.latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        result.preview_output = "Auth Failed"
        tested_users = ", ".join([f"'{u}'" for u, _ in candidates if u]) or f"'{target_user}'"
        result.full_output = (
            f"SSH Authentication failed on {ip}:{port} for {target.display_name}.\n"
            f"Attempted username(s): {tested_users}\n\n"
            f"Diagnosis & Fix:\n"
            f"1. Is the Linux username on the Back Office machine correct? (e.g. 'posuser' vs 'boadmin' vs 'root')\n"
            f"2. Is the password entered in 'BO Pass:' correct?\n"
            f"3. Does /etc/ssh/sshd_config on the Back Office allow password authentication ('PasswordAuthentication yes')?"
        )
        if urls and len(urls) > 1:
            return [
                AuditResult(
                    store_code=target.store_code, till_name=target.till_name, till_num=target.till_num,
                    ip=target.ip, store_order_index=target.store_order_index, is_bo=target.is_bo,
                    device_type=target.device_type, operation_mode=operation_mode, status=AuditStatus.OFFLINE,
                    latency_ms=result.latency_ms, preview_output=f"[{u.split('//')[-1].split('/')[0]}] Auth Failed",
                    full_output=result.full_output, extra={"url": u}
                ) for u in urls
            ]

    except (socket.timeout, TimeoutError):
        result.status = AuditStatus.OFFLINE
        result.latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        result.preview_output = f"Timeout ({timeout}s)"
        result.full_output = f"Connection timeout ({timeout}s) connecting to {ip}:{port}"
        if urls and len(urls) > 1:
            fail_list = [
                AuditResult(
                    store_code=target.store_code, till_name=target.till_name, till_num=target.till_num,
                    ip=target.ip, store_order_index=target.store_order_index, is_bo=target.is_bo,
                    device_type=target.device_type, operation_mode=operation_mode, status=AuditStatus.OFFLINE,
                    latency_ms=result.latency_ms, preview_output=f"Timeout ({timeout}s)",
                    full_output=result.full_output, extra={"url": u}
                ) for u in urls
            ]
            if on_sub_result:
                for sub_r in fail_list:
                    try:
                        on_sub_result(sub_r)
                    except Exception:
                        pass
            return fail_list

    except (socket.error, paramiko.SSHException) as e:
        err_str = str(e).lower()
        result.status = AuditStatus.OFFLINE
        if any(w in err_str for w in ["refused", "unreachable", "no route", "closed", "timed out", "reset"]):
            result.preview_output = "Offline / Unreachable"
        else:
            result.preview_output = f"SSH Error: {str(e)[:40]}"
        result.latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        result.full_output = f"SSH Network Error on {ip}:{port}: {e}"
        if urls and len(urls) > 1:
            fail_list = [
                AuditResult(
                    store_code=target.store_code, till_name=target.till_name, till_num=target.till_num,
                    ip=target.ip, store_order_index=target.store_order_index, is_bo=target.is_bo,
                    device_type=target.device_type, operation_mode=operation_mode, status=AuditStatus.OFFLINE,
                    latency_ms=result.latency_ms, preview_output=result.preview_output,
                    full_output=result.full_output, extra={"url": u}
                ) for u in urls
            ]
            if on_sub_result:
                for sub_r in fail_list:
                    try:
                        on_sub_result(sub_r)
                    except Exception:
                        pass
            return fail_list

    except Exception as e:
        result.status = AuditStatus.OFFLINE
        result.latency_ms = round((time.perf_counter() - start_time) * 1000, 1)
        result.preview_output = f"Error: {str(e)[:40]}"
        result.full_output = f"Unexpected error: {e}"
        if urls and len(urls) > 1:
            fail_list = [
                AuditResult(
                    store_code=target.store_code, till_name=target.till_name, till_num=target.till_num,
                    ip=target.ip, store_order_index=target.store_order_index, is_bo=target.is_bo,
                    device_type=target.device_type, operation_mode=operation_mode, status=AuditStatus.OFFLINE,
                    latency_ms=result.latency_ms, preview_output=result.preview_output,
                    full_output=result.full_output, extra={"url": u}
                ) for u in urls
            ]
            if on_sub_result:
                for sub_r in fail_list:
                    try:
                        on_sub_result(sub_r)
                    except Exception:
                        pass
            return fail_list

    finally:
        try:
            client.close()
        except Exception:
            pass

    return result
