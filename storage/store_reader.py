"""
storage/store_reader.py
Store list ingestion engine with enterprise security controls:
1. CIDR & IP Validation: Restricts targets strictly to 10.0.0.0/8, 192.168.0.0/16, and 127.0.0.1.
2. Zip Bomb Defense: Limits total uncompressed XML size to 50 MB and member count to 100 in .xlsx reader.
"""
import os
import re
import csv
import zipfile
import ipaddress
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Optional
from models.target import StoreRecord, TillTarget

# Default allowed subnets (Store network: 10.x, Home testing: 192.168.x, Local: 127.0.0.1)
DEFAULT_ALLOWED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("127.0.0.0/8")
]

def is_ip_authorized(ip_str: str, allowed_cidrs: Optional[List[str]] = None) -> bool:
    """Validate if an IP address belongs to approved private store networks."""
    clean_ip = ip_str.strip().split("/")[0].split(":")[0].strip()
    if clean_ip.lower() == "localhost":
        return True

    # Check if string is a subnet prefix (e.g. 10.14.22.12 or 10.14.22.)
    test_ip = clean_ip
    if test_ip.endswith("."):
        test_ip = test_ip + "1"
    parts = test_ip.split(".")
    if len(parts) == 3:
        test_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.1"

    try:
        ip_obj = ipaddress.ip_address(test_ip)
    except ValueError:
        return False

    networks = DEFAULT_ALLOWED_NETWORKS
    if allowed_cidrs:
        custom_nets = []
        for c in allowed_cidrs:
            try:
                custom_nets.append(ipaddress.ip_network(c.strip()))
            except ValueError:
                pass
        if custom_nets:
            networks = custom_nets

    return any(ip_obj in net for net in networks)

def read_xlsx_rows(file_path: str) -> List[List[str]]:
    """Zero-dependency Excel (.xlsx) reader with Zip Bomb & Memory Exhaustion defenses."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Limit compressed file size on disk
    if os.path.getsize(file_path) > 50 * 1024 * 1024:
        raise ValueError("Security Violation: Excel file exceeds 50 MB compressed limit.")

    rows: List[List[str]] = []
    try:
        with zipfile.ZipFile(file_path, "r") as z:
            # Zip Bomb Defense: Check uncompressed size and entry count
            infolist = z.infolist()
            if len(infolist) > 100:
                raise ValueError(f"Security Violation: Excel archive contains too many files ({len(infolist)} > 100).")

            total_uncompressed = sum(info.file_size for info in infolist)
            if total_uncompressed > 50 * 1024 * 1024:  # 50 MB uncompressed cap
                raise ValueError(f"Security Violation: Excel uncompressed content ({total_uncompressed // (1024*1024)} MB) exceeds 50 MB safety threshold.")

            shared_strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for elem in tree.iter():
                    if elem.tag.endswith("}t"):
                        shared_strings.append(elem.text or "")

            sheet_path = "xl/worksheets/sheet1.xml"
            if sheet_path not in z.namelist():
                for n in z.namelist():
                    if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"):
                        sheet_path = n
                        break

            tree = ET.fromstring(z.read(sheet_path))
            for row in tree.iter():
                if row.tag.endswith("}row"):
                    row_vals: List[str] = []
                    for c in row.iter():
                        if c.tag.endswith("}c"):
                            cell_type = c.attrib.get("t", "")
                            val = ""
                            for child in c.iter():
                                if child.tag.endswith("}v") or child.tag.endswith("}t"):
                                    if child.text:
                                        val = child.text
                                        break
                            if cell_type == "s":
                                try:
                                    idx = int(val)
                                    val = shared_strings[idx] if idx < len(shared_strings) else val
                                except (ValueError, IndexError):
                                    pass
                            row_vals.append(str(val).strip())
                    if any(r for r in row_vals):
                        rows.append(row_vals)
    except Exception as e:
        raise ValueError(f"Failed to read Excel (.xlsx) file: {e}")
    return rows

def normalize_header(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(h).lower())

def parse_store_rows(rows: List[List[str]], allowed_cidrs: Optional[List[str]] = None) -> List[StoreRecord]:
    if not rows:
        return []

    header_row = rows[0]
    norm_headers = [normalize_header(h) for h in header_row]

    code_idx = -1
    till_idx = -1
    ip_idx = -1
    count_idx = -1
    spec_idx = -1
    mode_idx = -1
    status_idx = -1
    mismatch_idx = -1
    offline_idx = -1

    for i, nh in enumerate(norm_headers):
        if nh in ("storecode", "storeid", "store", "storename", "code"):
            code_idx = i
        elif nh in ("tillname", "till", "tillno", "tillnum", "tillnumber", "tillid", "device", "devicename", "dev", "target", "targetname"):
            till_idx = i
        elif nh in ("ipaddress", "ip", "targetip", "host", "storeip", "subnet", "subnetorip", "tillip", "tillipaddress", "ipaddr"):
            ip_idx = i
        elif nh in ("tillcount", "tills", "notills", "tillcnt", "count", "numtills"):
            count_idx = i
        elif nh in ("specifictills", "specifictill", "tillslist", "targettills", "specific"):
            spec_idx = i
        elif nh in ("mode", "tillmode", "scopemode", "scope"):
            mode_idx = i
        elif nh in ("status", "auditstatus"):
            status_idx = i
        elif nh in ("mismatchversion", "mismatchtills", "mismatch", "versionmismatch"):
            mismatch_idx = i
        elif nh in ("offline", "offlinetills"):
            offline_idx = i

    # Detect if row 0 is actually a header row
    has_header_words = any(
        any(k in nh for k in ("store", "code", "till", "device", "ip", "subnet", "host", "count", "status", "version", "name", "latency", "mismatch", "offline", "mode"))
        for nh in norm_headers
    )
    start_row = 1 if has_header_words else 0

    # BRANCH 0: RE-AUDIT FROM VERSION CHECK REPORT (Store Code, IP, Mismatch Version, Offline, Status)
    if (mismatch_idx != -1 or offline_idx != -1) and ip_idx != -1:
        stores: List[StoreRecord] = []
        for row in rows[start_row:]:
            if not row or not any(row):
                continue
            raw_ip = row[ip_idx].strip().strip("'\"") if 0 <= ip_idx < len(row) else ""
            if not raw_ip:
                continue
            if not is_ip_authorized(raw_ip, allowed_cidrs):
                raise ValueError(f"Security Policy Violation: Target IP '{raw_ip}' is outside authorized store subnets (10.x / 192.168.x).")
            raw_code = row[code_idx].strip().strip("'\"") if 0 <= code_idx < len(row) else f"Store-{len(stores) + 1:03d}"

            mismatches = ""
            if 0 <= mismatch_idx < len(row):
                m_val = row[mismatch_idx].strip().strip("'\"")
                if m_val and "matched" not in m_val.lower() and m_val != "-":
                    mismatches = m_val

            offlines = ""
            is_all_offline = False
            if 0 <= offline_idx < len(row):
                o_val = row[offline_idx].strip().strip("'\"")
                if o_val:
                    if "all offline" in o_val.lower():
                        is_all_offline = True
                    elif "offline" not in o_val.lower() and o_val != "-":
                        offlines = o_val

            raw_status = row[status_idx].strip().strip("'\"").lower() if 0 <= status_idx < len(row) else ""
            if raw_status == "offline" and not mismatches and not offlines:
                is_all_offline = True

            # If all online tills matched and store was not offline -> bypass on re-audit
            if not mismatches and not offlines and not is_all_offline:
                continue

            if is_all_offline:
                # The entire store was offline! Re-audit all tills in the store
                stores.append(StoreRecord(
                    store_code=raw_code,
                    subnet_or_ip=raw_ip,
                    till_count=10,
                    store_order_index=len(stores),
                    specific_tills=""
                ))
            else:
                target_tills_list = []
                if mismatches:
                    target_tills_list.extend(StoreRecord.parse_specific_tills(mismatches))
                if offlines:
                    target_tills_list.extend(StoreRecord.parse_specific_tills(offlines))

                if not target_tills_list:
                    continue

                spec_tills = ",".join(str(n) for n in sorted(set(target_tills_list)))
                stores.append(StoreRecord(
                    store_code=raw_code,
                    subnet_or_ip=raw_ip,
                    till_count=len(target_tills_list),
                    store_order_index=len(stores),
                    specific_tills=spec_tills
                ))
        return stores

    if ip_idx == -1:
        if len(header_row) == 1:
            ip_idx = 0
        elif len(header_row) == 2:
            c0 = header_row[0].strip().strip("'\"")
            if re.match(r"^\d{1,3}\.\d{1,3}", c0):
                ip_idx = 0
                count_idx = 1
            else:
                code_idx = 0
                ip_idx = 1
        elif len(header_row) >= 3:
            c1 = header_row[1].strip().strip("'\"")
            c2 = header_row[2].strip().strip("'\"").lower() if len(header_row) > 2 else ""
            if re.search(r"(?i)till|device", c1):
                code_idx = 0
                till_idx = 1
                ip_idx = 2
            elif c2 in ("all", "specific", "uat") or "mode" in c2:
                # 5-column positional: Store, IP, Mode, Till Count, Specific Tills
                code_idx = 0
                ip_idx = 1
                mode_idx = 2
                count_idx = 3 if len(header_row) > 3 else -1
                spec_idx = 4 if len(header_row) > 4 else -1
            else:
                code_idx = 0
                ip_idx = 1
                count_idx = 2
                if len(header_row) >= 4 and spec_idx == -1:
                    spec_idx = 3

    # BRANCH 1: RE-AUDIT SPECIFIC TILLS / DEVICES (from failure CSV / Action List / Export)
    if till_idx != -1 and ip_idx != -1:
        store_map: Dict[str, Tuple[int, List[TillTarget]]] = {}
        store_order_counter = 0

        for row in rows[start_row:]:
            if not row or not any(row):
                continue

            raw_code = row[code_idx].strip().strip("'\"") if 0 <= code_idx < len(row) else ""
            raw_till = row[till_idx].strip().strip("'\"") if 0 <= till_idx < len(row) else ""
            raw_ip = row[ip_idx].strip().strip("'\"") if 0 <= ip_idx < len(row) else ""

            if not raw_ip:
                continue

            # Security: CIDR boundary check
            if not is_ip_authorized(raw_ip, allowed_cidrs):
                raise ValueError(f"Security Policy Violation: Target IP '{raw_ip}' is outside authorized store subnets (10.x / 192.168.x).")

            if not raw_code:
                raw_code = "Store-001"

            is_bo = bool(re.search(r"\bbo\b|backoffice", raw_till, re.IGNORECASE))
            till_digits = re.findall(r"\d+", raw_till)
            if is_bo:
                till_num = 0
                formatted_till = "BO-01"
            else:
                till_num = int(till_digits[0]) if till_digits else 1
                formatted_till = f"Till-{till_num:02d}"

            if raw_code not in store_map:
                store_map[raw_code] = (store_order_counter, [])
                store_order_counter += 1

            s_idx, t_list = store_map[raw_code]
            t_list.append(TillTarget(
                store_code=raw_code,
                till_name=formatted_till,
                till_num=till_num,
                ip=raw_ip,
                port=22,
                store_order_index=s_idx,
                is_bo=is_bo,
                device_type="BO" if is_bo else "TILL"
            ))

        stores: List[StoreRecord] = []
        for code, (s_idx, t_list) in store_map.items():
            first_ip = t_list[0].ip
            ip_parts = first_ip.split(".")
            base_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.12" if len(ip_parts) == 4 else first_ip

            has_bo = any(t.is_bo for t in t_list)
            has_tills = any(not t.is_bo for t in t_list)

            stores.append(StoreRecord(
                store_code=code,
                subnet_or_ip=base_ip,
                till_count=len(t_list),
                store_order_index=s_idx,
                include_tills=has_tills,
                include_bo=has_bo,
                direct_targets=t_list
            ))
        return stores

    # BRANCH 2: BULK STORE SUBNET LIST
    stores: List[StoreRecord] = []
    for row in rows[start_row:]:
        if not row or not any(row):
            continue

        raw_ip = row[ip_idx].strip().strip("'\"") if 0 <= ip_idx < len(row) else ""
        if not raw_ip:
            continue

        # Security: CIDR boundary check
        if not is_ip_authorized(raw_ip, allowed_cidrs):
            raise ValueError(f"Security Policy Violation: Store IP/Subnet '{raw_ip}' is outside authorized store subnets (10.x / 192.168.x).")

        raw_code = row[code_idx].strip().strip("'\"") if 0 <= code_idx < len(row) else ""
        if not raw_code:
            raw_code = f"Store-{len(stores) + 1:03d}"

        raw_mode = row[mode_idx].strip().strip("'\"").lower() if 0 <= mode_idx < len(row) else ""
        is_uat = (raw_mode in ("uat", "lab") or "uat" in raw_code.lower())

        raw_count = 10
        spec_tills = ""

        if raw_mode in ("all", "all tills", "alltills"):
            # When Mode is 'all', Specific Tills is empty; Till Count is used (default 10)
            if 0 <= count_idx < len(row):
                cnt_str = row[count_idx].strip()
                if cnt_str.isdigit():
                    raw_count = max(1, min(140, int(cnt_str)))
            spec_tills = ""

        elif raw_mode in ("specific", "spec", "specific tills"):
            # When Mode is 'specific', check if Till Count column is provided or if trailing tills are given
            # Support both:
            #   001, 10.12.12.12, specific, 10, "2,35,3,4"  (5 columns)
            #   001, 10.12.12.12, specific, , "2,35,3,4"   (5 columns, blank count)
            #   001, 10.12.12.12, specific, 2, 35, 3, 4    (unquoted trailing commas)
            if 0 <= spec_idx < len(row) and row[spec_idx].strip():
                spec_tills = row[spec_idx].strip()
                if 0 <= count_idx < len(row) and row[count_idx].strip().isdigit():
                    raw_count = max(1, min(140, int(row[count_idx].strip())))
            elif 0 <= count_idx < len(row):
                remaining = [c.strip() for c in row[count_idx:] if c.strip()]
                if len(remaining) > 1 or (remaining and not remaining[0].isdigit()):
                    spec_tills = ",".join(remaining)
                elif remaining and remaining[0].isdigit():
                    spec_tills = remaining[0]

        else:
            # Backward compatibility (when Mode column is omitted)
            if 0 <= count_idx < len(row):
                cnt_str = row[count_idx].strip()
                if cnt_str.isdigit():
                    raw_count = max(1, min(140, int(cnt_str)))

            if 0 <= spec_idx < len(row):
                spec_tills = row[spec_idx].strip()

        # Backward compatibility for offline store rows (e.g. from an exported report)
        raw_status = row[status_idx].strip().strip("'\"").lower() if 0 <= status_idx < len(row) else ""
        if raw_status == "offline" and not spec_tills:
            # Entire store was offline -> audit all tills
            spec_tills = ""

        stores.append(StoreRecord(
            store_code=raw_code,
            subnet_or_ip=raw_ip,
            till_count=raw_count,
            store_order_index=len(stores),
            specific_tills=spec_tills,
            is_uat=is_uat
        ))

    # Security cap: Max 2000 stores per scan
    if len(stores) > 2000:
        raise ValueError(f"Security Violation: Target list contains {len(stores)} stores, exceeding maximum safety limit of 2,000 stores.")

    return stores

def load_stores_from_file(file_path: str, allowed_cidrs: Optional[List[str]] = None) -> List[StoreRecord]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".xlsx":
        rows = read_xlsx_rows(file_path)
        return parse_store_rows(rows, allowed_cidrs)
    else:
        encodings = ["utf-8-sig", "utf-8", "cp1252", "latin1"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc, errors="replace") as f:
                    content = f.read()
                    dialect = csv.Sniffer().sniff(content[:4096], delimiters=",\t;|")
                    f.seek(0)
                    reader = csv.reader(f, dialect)
                    rows = [row for row in reader if row]
                    return parse_store_rows(rows, allowed_cidrs)
            except Exception:
                continue

        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            rows = [line.strip().split(",") for line in f if line.strip()]
            return parse_store_rows(rows, allowed_cidrs)

def parse_stores_from_text(raw_text: str, allowed_cidrs: Optional[List[str]] = None) -> List[StoreRecord]:
    import io
    rows = []
    for line in raw_text.strip().splitlines():
        line_s = line.strip()
        if not line_s:
            continue
        delim = "\t" if "\t" in line_s else ("|" if "|" in line_s else (";" if ";" in line_s and "," not in line_s else ","))
        try:
            reader = csv.reader(io.StringIO(line_s), delimiter=delim)
            r = next(reader)
            parts = [p.strip() for p in r]
            if any(parts):
                rows.append(parts)
        except Exception:
            parts = [p.strip() for p in line_s.split(",") if p.strip()]
            if parts:
                rows.append(parts)
    return parse_store_rows(rows, allowed_cidrs)
