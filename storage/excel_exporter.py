"""
storage/excel_exporter.py
Zero-dependency OpenXML (.xlsx) multi-sheet workbook generator.
Strictly guarantees First-Come, First-Served (FCFS) order:
Store 1 (Tills 1-13), then Store 2 (Tills 1-13), irrespective of status!
"""
import zipfile
import xml.sax.saxutils as saxutils
from typing import List, Any
from models.result import AuditResult, AuditSummary, AuditStatus

def escape_xml(s: Any) -> str:
    return saxutils.escape(str(s) if s is not None else "")

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

    # Header row (row 1)
    xml_parts.append('<row r="1">')
    for c_idx, h in enumerate(headers, start=1):
        ref = f"{col_to_letter(c_idx)}1"
        xml_parts.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape_xml(h)}</t></is></c>')
    xml_parts.append('</row>')

    # Data rows (row 2 onward)
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
        # STRICT FCFS SORTING:
        # 1. Order by store index in input file (Store 1, Store 2, Store 3...)
        # 2. Within each store, order by till number (Till 1, Till 2, Till 3... Till 13)
        # Irrespective of status!
        sorted_results = sorted(results, key=lambda r: (r.store_order_index, r.till_num))

        # Sheet 1: Summary Data
        summary_headers = ["Metric", "Value", "Notes"]
        summary_rows = [
            ["Total Tills Audited", summary.total_tills, "Total Ubuntu POS targets in scan"],
            ["Completed Tills", summary.completed_tills, "Processed till targets"],
            ["Success Count", summary.success_count, "Both WAR exact size and Delivery Version matched"],
            ["Size Mismatches", summary.size_mismatch_count, "Version matched, but WAR size differed"],
            ["Version Mismatches", summary.version_mismatch_count, "WAR size matched, but Delivery Version differed"],
            ["Both Mismatches", summary.both_mismatch_count, "Neither WAR size nor Delivery Version matched"],
            ["File Missing", summary.missing_count, "WAR or Properties file missing on till"],
            ["Offline / Unreachable", summary.offline_count, "Offline, connection timeout, or auth failure"],
            ["Pass Rate", f"{summary.pass_rate_percent}%", "Percentage of successful tills"],
            ["Total Elapsed Time", f"{summary.elapsed_seconds} seconds", "Duration of audit run"]
        ]

        # Sheet 2: All Tills Audit (In strict Store 1 [1-13], Store 2 [1-13] order)
        all_headers = [
            "Store Code", "Till Name", "IP Address", "Latency (ms)",
            "WAR Size", "WAR Last Modified", "Delivery Version",
            "Status", "Expected Version", "Variable Details", "Audit Timestamp"
        ]
        all_rows = []
        for r in sorted_results:
            all_rows.append([
                r.store_code,
                r.till_name,
                r.ip,
                r.latency_ms,
                r.war_size,
                r.war_modified,
                r.delivery_version,
                r.status,
                r.expected_version,
                r.prop_variable,
                r.timestamp
            ])

        # Sheet 3: Action List (Mismatches & Failures - also in strict Store -> Till order)
        action_headers = [
            "Store Code", "Till Name", "IP Address", "Status Issue",
            "Actual WAR Size", "Actual Delivery Version", "Expected Delivery Version",
            "Action Required", "Timestamp"
        ]
        action_rows = []
        for r in sorted_results:
            if AuditStatus.is_failed(r.status):
                action = "Investigate Failure"
                if r.status == AuditStatus.SIZE_MISMATCH:
                    action = "Redeploy/Inspect WAR File Size"
                elif r.status == AuditStatus.VERSION_MISMATCH:
                    action = "Update Delivery Version in Properties"
                elif r.status == AuditStatus.BOTH_MISMATCH:
                    action = "Full Store Version Reinstallation Required"
                elif r.status == AuditStatus.FILE_MISSING:
                    action = "Deploy Missing Configuration/WAR"
                elif r.status in (AuditStatus.OFFLINE, AuditStatus.TIMEOUT):
                    action = "Check Till Power / Store Network Switch"

                action_rows.append([
                    r.store_code,
                    r.till_name,
                    r.ip,
                    r.status,
                    r.war_size,
                    r.delivery_version,
                    r.expected_version,
                    action,
                    r.timestamp
                ])

        sheet1_xml = build_sheet_xml(summary_headers, summary_rows)
        sheet2_xml = build_sheet_xml(all_headers, all_rows)
        sheet3_xml = build_sheet_xml(action_headers, action_rows)

        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet3.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
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
            '<sheet name="Audit Summary" sheetId="1" r:id="rId1"/>'
            '<sheet name="All Tills Audit" sheetId="2" r:id="rId2"/>'
            '<sheet name="Action List (Mismatches)" sheetId="3" r:id="rId3"/>'
            '</sheets>'
            '</workbook>'
        )

        workbook_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet3.xml"/>'
            '</Relationships>'
        )

        with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", content_types)
            z.writestr("_rels/.rels", root_rels)
            z.writestr("xl/workbook.xml", workbook_xml)
            z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            z.writestr("xl/worksheets/sheet1.xml", sheet1_xml)
            z.writestr("xl/worksheets/sheet2.xml", sheet2_xml)
            z.writestr("xl/worksheets/sheet3.xml", sheet3_xml)
