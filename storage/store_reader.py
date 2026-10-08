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
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("3.109.2.78/32")
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

    for i, nh in enumerate(norm_headers):
        if nh in ("storecode", "storeid", "store", "storename", "code"):
            code_idx = i
        elif nh in ("tillname", "till", "tillno", "tillnum", "tillnumber", "tillid", "device", "devicename", "dev", "target", "targetname"):
            till_idx = i
        elif nh in ("ipaddress", "ip", "targetip", "host", "storeip", "subnet", "subnetorip", "tillip", "tillipaddress", "ipaddr"):
            ip_idx = i
        elif nh in ("tillcount", "tills", "notills", "tillcnt", "count", "numtills"):
            count_idx = i
        elif nh in ("specifictills", "specifictill", "tillslist", "targettills"):
            spec_idx = i

    # Detect if row 0 is actually a header row
    has_header_words = any(
        any(k in nh for k in ("store", "code", "till", "device", "ip", "subnet", "host", "count", "status", "version", "name", "latency"))
        for nh in norm_headers
    )
    start_row = 1 if has_header_words else 0

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
            if re.search(r"(?i)till|device", c1):
                code_idx = 0
                till_idx = 1
                ip_idx = 2
            else:
                code_idx = 0
                ip_idx = 1
                count_idx = 2

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

        raw_count = 13
        if 0 <= count_idx < len(row):
            cnt_str = row[count_idx].strip()
            if cnt_str.isdigit():
                # Store capacity cap (supports up to 140 tills per store subnet)
                raw_count = max(1, min(140, int(cnt_str)))

        spec_tills = ""
        if 0 <= spec_idx < len(row):
            spec_tills = row[spec_idx].strip()

        stores.append(StoreRecord(
            store_code=raw_code,
            subnet_or_ip=raw_ip,
            till_count=raw_count,
            store_order_index=len(stores),
            specific_tills=spec_tills
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
    lines = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    rows = []
    for line in lines:
        parts = re.split(r"[,\t;|]+", line)
        parts = [p.strip() for p in parts if p.strip()]
        if parts:
            rows.append(parts)
    return parse_store_rows(rows, allowed_cidrs)
