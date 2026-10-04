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
        # Section 8.1: Strict Store Hierarchy Order
        # Store index -> BO (0) -> Tills (1..N)
        sorted_results = sorted(
            results,
            key=lambda r: (r.store_order_index, 0 if r.is_bo else (r.till_num or 1))
        )

        is_terminal = any(r.operation_mode in ("command", "terminal") for r in sorted_results)
        val_header = "Command Output" if is_terminal else "Variable / Version"

        headers = [
            "Store Code", "Device Name", "Device Type", "IP Address", "Latency (ms)",
            "File Size", "Last Modified", val_header, "Status", "Audit Timestamp"
        ]

        def result_to_row(r: AuditResult) -> List[Any]:
            dev_icon = "BO" if r.is_bo else "Till"
            var_or_output = r.preview_output if (r.operation_mode in ("command", "terminal") or (r.delivery_version == "-" and r.prop_variable == "-")) else (r.delivery_version if r.delivery_version != "-" else r.prop_variable)
            return [
                r.store_code,
                r.till_name,
                dev_icon,
                r.ip,
                f"{r.latency_ms} ms" if r.latency_ms > 0 else "-",
                r.war_size,
                r.war_modified,
                var_or_output,
                r.status,
                r.timestamp
            ]

        # 1. Sheet: All
        all_rows = [result_to_row(r) for r in sorted_results]

        # 2. Sheet: Success
        success_rows = [result_to_row(r) for r in sorted_results if r.status == AuditStatus.SUCCESS]

        # 3. Sheet: Offline (Unreachable machines - re-audit ready)
        offline_rows = [result_to_row(r) for r in sorted_results if r.status == AuditStatus.OFFLINE]

        # 4. Sheet: Mismatch
        mismatch_rows = [result_to_row(r) for r in sorted_results if r.status == AuditStatus.MISMATCH]

        # 5. Sheet: Miss
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
        is_terminal = any(r.operation_mode in ("command", "terminal") for r in sorted_results)
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
