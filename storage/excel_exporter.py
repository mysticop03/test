"""
storage/excel_exporter.py
Zero-dependency OpenXML (.xlsx) multi-sheet workbook generator.
Strictly implements Section 8.1 & 8.2 of SYSTEM_RULES_AND_CONDITIONS.md:
1. Strict Store Hierarchy Order:
   Store 1 -> Store 1 BO (.12) -> Store 1 Till 1 (.112) -> Till 2 (.113) ... -> Store 2 -> Store 2 BO (.12) ...
2. Multi-Sheet Architecture:
   Sheet 1: All
   Sheet 2: Success
   Sheet 3: Offline (re-audit ready)
   Sheet 4: Mismatch
   Sheet 5: Miss
"""
import zipfile
import xml.sax.saxutils as saxutils
from typing import List, Any
from models.result import AuditResult, AuditSummary, AuditStatus

def escape_xml(s: Any) -> str:
    val = str(s) if s is not None else ""
    # CSV / Formula Injection defense
    if val and val[0] in ("=", "+", "-", "@") and not (val.startswith("-") and val[1:].isdigit()):
        val = "'" + val
    return saxutils.escape(val)

def col_to_letter(col_idx: int) -> str:
    letters = ""
    while col_idx > 0:
        col_idx, remainder = divmod(col_idx - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters

def build_sheet_xml(headers: List[str], data_rows: List[List[Any]]) -> str:
    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetData>'
    ]

    # Header row
    xml_parts.append('<row r="1">')
    for c_idx, h in enumerate(headers, start=1):
        ref = f"{col_to_letter(c_idx)}1"
        xml_parts.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape_xml(h)}</t></is></c>')
    xml_parts.append('</row>')

    # Data rows
    for r_idx, row in enumerate(data_rows, start=2):
        xml_parts.append(f'<row r="{r_idx}">')
        for c_idx, val in enumerate(row, start=1):
            ref = f"{col_to_letter(c_idx)}{r_idx}"
            xml_parts.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape_xml(val)}</t></is></c>')
        xml_parts.append('</row>')

    xml_parts.append('</sheetData>')
    xml_parts.append('</worksheet>')
    return "".join(xml_parts)

class ExcelExporter:
    @staticmethod
    def export_audit_workbook(
        file_path: str,
        summary: AuditSummary,
        results: List[AuditResult]
    ):
        if not results:
            return

        is_version_check = any(r.operation_mode == "version_check" for r in results)
        is_terminal = any(r.operation_mode in ("command", "terminal") for r in results)

        # -------------------------------------------------------------
        # Case 1: Version Check (5-Column Aggregated Store Format)
        # -------------------------------------------------------------
        if is_version_check:
            headers = ["Store Code", "IP", "Mismatch Version", "Offline", "Status"]
            store_map: Dict[str, Dict[str, Any]] = {}
            for r in results:
                code = r.store_code
                if code not in store_map:
                    parts = r.ip.split(".")
                    base_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.12" if len(parts) == 4 else r.ip
                    store_map[code] = {
                        "order": r.store_order_index,
                        "ip": base_ip,
                        "mismatches": [],
                        "offlines": [],
                        "matched": []
                    }
                info = store_map[code]
                dev_tag = "BO" if r.is_bo else (r.till_num if r.till_num is not None else 1)
                if r.status == AuditStatus.SUCCESS:
                    info["matched"].append(dev_tag)
                elif r.status in (AuditStatus.MISMATCH, AuditStatus.MISS):
                    info["mismatches"].append(dev_tag)
                elif r.status == AuditStatus.OFFLINE:
                    info["offlines"].append(dev_tag)

            all_rows = []
            success_rows = []
            mismatch_rows = []
            offline_rows = []

            def _sort_dev(x):
                return (0, 0) if str(x).upper() == "BO" else (1, int(x))

            for code, info in sorted(store_map.items(), key=lambda x: x[1]["order"]):
                has_mismatch = bool(info["mismatches"])
                has_offline = bool(info["offlines"])

                if has_mismatch:
                    m_str = ",".join(str(n) for n in sorted(set(info["mismatches"]), key=_sort_dev))
                    st = AuditStatus.MISMATCH
                elif info["matched"]:
                    m_str = "All Matched"
                    st = AuditStatus.OFFLINE if has_offline else AuditStatus.SUCCESS
                else:
                    m_str = "-"
                    st = AuditStatus.OFFLINE

                if has_offline:
                    if not info["matched"] and not has_mismatch:
                        o_str = "All Offline"
                    else:
                        o_str = ",".join(str(n) for n in sorted(set(info["offlines"]), key=_sort_dev))
                else:
                    o_str = "-"

                row = [code, info["ip"], m_str, o_str, st]
                all_rows.append(row)
                if st == AuditStatus.SUCCESS:
                    success_rows.append(row)
                elif st == AuditStatus.MISMATCH:
                    mismatch_rows.append(row)
                elif st == AuditStatus.OFFLINE:
                    offline_rows.append(row)

            sheets_data = [
                ("All", all_rows),
                ("Success", success_rows),
                ("Mismatch", mismatch_rows),
                ("Offline", offline_rows)
            ]
        else:
            # Section 8.1: Strict Store Hierarchy Order
            sorted_results = sorted(
                results,
                key=lambda r: (r.store_order_index, 0 if r.is_bo else (r.till_num or 1))
            )

            if is_terminal:
                headers = [
                    "Store Code", "Device Name", "Device Type", "IP Address", "Latency (ms)",
                    "Command Output", "Status", "Audit Timestamp"
                ]
                def result_to_row(r: AuditResult) -> List[Any]:
                    dev_icon = "BO" if r.is_bo else "Till"
                    return [
                        r.store_code,
                        r.till_name,
                        dev_icon,
                        r.ip,
                        f"{r.latency_ms} ms" if r.latency_ms > 0 else "-",
                        r.preview_output,
                        r.status,
                        r.timestamp
                    ]
            else:
                has_size = any(r.war_size != "-" for r in sorted_results)
                has_var = any((r.delivery_version != "-" or r.prop_variable != "-") for r in sorted_results)

                headers = ["Store Code", "Device Name", "Device Type", "IP Address", "Latency (ms)"]
                if has_size and not has_var:
                    headers.extend(["File Size", "Last Modified"])
                elif has_var and not has_size:
                    headers.extend(["Variable / Value", "Last Modified"])
                else:
                    headers.extend(["File Size", "Last Modified", "Variable / Value"])
                headers.extend(["Status", "Audit Timestamp"])

                def result_to_row(r: AuditResult) -> List[Any]:
                    dev_icon = "BO" if r.is_bo else "Till"
                    var_display = r.delivery_version if r.delivery_version != "-" else r.prop_variable
                    row_data = [
                        r.store_code,
                        r.till_name,
                        dev_icon,
                        r.ip,
                        f"{r.latency_ms} ms" if r.latency_ms > 0 else "-"
                    ]
                    if has_size and not has_var:
                        row_data.extend([r.war_size, r.war_modified])
                    elif has_var and not has_size:
                        row_data.extend([var_display, r.war_modified])
                    else:
                        row_data.extend([r.war_size, r.war_modified, var_display])
                    row_data.extend([r.status, r.timestamp])
                    return row_data

            all_rows = [result_to_row(r) for r in sorted_results]
            success_rows = [result_to_row(r) for r in sorted_results if r.status == AuditStatus.SUCCESS]
            offline_rows = [result_to_row(r) for r in sorted_results if r.status == AuditStatus.OFFLINE]
            mismatch_rows = [result_to_row(r) for r in sorted_results if r.status == AuditStatus.MISMATCH]
            miss_rows = [result_to_row(r) for r in sorted_results if r.status in (AuditStatus.MISS, AuditStatus.BLOCKED)]

            sheets_data = [
                ("All", all_rows),
                ("Success", success_rows),
                ("Offline", offline_rows),
                ("Mismatch", mismatch_rows),
                ("Miss", miss_rows)
            ]

        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet4.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet5.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        )

        root_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )

        workbook_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            '<sheet name="All" sheetId="1" r:id="rId1"/>'
            '<sheet name="Success" sheetId="2" r:id="rId2"/>'
            '<sheet name="Offline" sheetId="3" r:id="rId3"/>'
            '<sheet name="Mismatch" sheetId="4" r:id="rId4"/>'
            '<sheet name="Miss" sheetId="5" r:id="rId5"/>'
            '</sheets>'
            '</workbook>'
        )

        workbook_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>'
            '<Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet4.xml"/>'
            '<Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet5.xml"/>'
            '</Relationships>'
        )

        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", content_types)
            z.writestr("_rels/.rels", root_rels)
            z.writestr("xl/workbook.xml", workbook_xml)
            z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            for idx, (_, rows) in enumerate(sheets_data, start=1):
                sheet_xml = build_sheet_xml(headers, rows)
                z.writestr(f"xl/worksheets/sheet{idx}.xml", sheet_xml)

    @staticmethod
    def export_filtered_workbook(
        file_path: str,
        sheet_name: str,
        results: List[AuditResult]
    ):
        sorted_results = sorted(
            results,
            key=lambda r: (r.store_order_index, 0 if r.is_bo else (r.till_num or 1))
        )
        is_version_check = any(r.operation_mode == "version_check" for r in sorted_results)
        is_terminal = any(r.operation_mode in ("command", "terminal") for r in sorted_results)

        if is_version_check:
            headers = ["Store Code", "IP", "Mismatch Version", "Offline", "Status"]
            store_map: Dict[str, Dict[str, Any]] = {}
            for r in sorted_results:
                code = r.store_code
                if code not in store_map:
                    parts = r.ip.split(".")
                    base_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.12" if len(parts) == 4 else r.ip
                    store_map[code] = {
                        "order": r.store_order_index,
                        "ip": base_ip,
                        "mismatches": [],
                        "offlines": [],
                        "matched": []
                    }
                info = store_map[code]
                dev_tag = "BO" if r.is_bo else (r.till_num if r.till_num is not None else 1)
                if r.status == AuditStatus.SUCCESS:
                    info["matched"].append(dev_tag)
                elif r.status in (AuditStatus.MISMATCH, AuditStatus.MISS):
                    info["mismatches"].append(dev_tag)
                elif r.status == AuditStatus.OFFLINE:
                    info["offlines"].append(dev_tag)

            def _sort_dev(x):
                return (0, 0) if str(x).upper() == "BO" else (1, int(x))

            rows = []
            for code, info in sorted(store_map.items(), key=lambda x: x[1]["order"]):
                has_mismatch = bool(info["mismatches"])
                has_offline = bool(info["offlines"])
                if has_mismatch:
                    m_str = ",".join(str(n) for n in sorted(set(info["mismatches"]), key=_sort_dev))
                    st = AuditStatus.MISMATCH
                elif info["matched"]:
                    m_str = "All Matched"
                    st = AuditStatus.OFFLINE if has_offline else AuditStatus.SUCCESS
                else:
                    m_str = "-"
                    st = AuditStatus.OFFLINE

                if has_offline:
                    if not info["matched"] and not has_mismatch:
                        o_str = "All Offline"
                    else:
                        o_str = ",".join(str(n) for n in sorted(set(info["offlines"]), key=_sort_dev))
                else:
                    o_str = "-"
                rows.append([code, info["ip"], m_str, o_str, st])
        else:
            val_header = "Command Output" if is_terminal else "Variable / Version"
            headers = [
                "Store Code", "Device Name", "Device Type", "IP Address", "Latency (ms)",
                "File Size", "Last Modified", val_header, "Status", "Audit Timestamp"
            ]

            def result_to_row(r: AuditResult) -> List[Any]:
                dev_type = "BO" if r.is_bo else "Till"
                var_or_output = r.preview_output if (r.operation_mode in ("command", "terminal") or (r.delivery_version == "-" and r.prop_variable == "-")) else (r.delivery_version if r.delivery_version != "-" else r.prop_variable)
                return [
                    r.store_code,
                    r.till_name,
                    dev_type,
                    r.ip,
                    f"{r.latency_ms} ms" if r.latency_ms > 0 else "-",
                    r.war_size,
                    r.war_modified,
                    var_or_output,
                    r.status,
                    r.timestamp
                ]

            rows = [result_to_row(r) for r in sorted_results]
        clean_sheet_name = saxutils.escape(sheet_name[:31]) or "Results"

        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '</Types>'
        )

        root_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            '</Relationships>'
        )

        workbook_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            f'<sheet name="{clean_sheet_name}" sheetId="1" r:id="rId1"/>'
            '</sheets>'
            '</workbook>'
        )

        workbook_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '</Relationships>'
        )

        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", content_types)
            z.writestr("_rels/.rels", root_rels)
            z.writestr("xl/workbook.xml", workbook_xml)
            z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            sheet_xml = build_sheet_xml(headers, rows)
            z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
