import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def create_element(name):
    return OxmlElement(name)

def set_cell_background(cell, fill_hex):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    tblPr = table._element.xpath('w:tblPr')
    if tblPr:
        borders = parse_xml(
            f'<w:tblBorders {nsdecls("w")}>'
            f'<w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'<w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
            f'</w:tblBorders>'
        )
        tblPr[0].append(borders)

def build_docx(output_path):
    doc = docx.Document()

    # Page Margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.65)
        section.bottom_margin = Inches(0.65)
        section.left_margin = Inches(0.75)
        section.right_margin = Inches(0.75)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Calibri'
    normal_style.font.size = Pt(9.5)
    normal_style.font.color.rgb = RGBColor(30, 41, 59) # Slate 800

    # ==================== PAGE 1 ====================
    # Document Title
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("POS OPERATIONS HUB")
    run_title.font.name = 'Georgia'
    run_title.font.size = Pt(21)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(15, 23, 42)
    p_title.paragraph_format.space_after = Pt(12)

    # 4-Column Summary Grid Table
    grid_table = doc.add_table(rows=1, cols=4)
    grid_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(grid_table, color="CBD5E1", sz="4")

    cols_data = [
        ("PROBLEM", "Manually connecting to store BO servers and POS tills via terminal to check files, test URLs, or update configurations is slow, repetitive, and difficult to verify at scale."),
        ("SOLUTION", "A unified desktop application that connects to store systems in parallel to manage configurations, test URLs, verify release versions, and run routine daily commands."),
        ("IMPACT", "Eliminates manual terminal sessions, catches version mismatches and offline counters instantly, and exports clean Excel reports for team and management review."),
        ("SCALE", "Multi-threaded architecture that processes all POS counters in a store concurrently and supports batch multi-store execution.")
    ]

    for i, (title, text) in enumerate(cols_data):
        cell = grid_table.rows[0].cells[i]
        set_cell_background(cell, "F8FAFC")
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        
        p = cell.paragraphs[0]
        p.paragraph_format.space_after = Pt(4)
        run_h = p.add_run(title)
        run_h.font.bold = True
        run_h.font.size = Pt(8.5)
        run_h.font.color.rgb = RGBColor(15, 23, 42)

        p2 = cell.add_paragraph()
        p2.paragraph_format.space_after = Pt(0)
        p2.paragraph_format.line_spacing = 1.15
        run_b = p2.add_run(text)
        run_b.font.size = Pt(8)
        run_b.font.color.rgb = RGBColor(51, 65, 85)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Section 1: Core Capabilities
    p_sec1 = doc.add_paragraph()
    p_sec1.paragraph_format.space_before = Pt(6)
    p_sec1.paragraph_format.space_after = Pt(6)
    run_sec1 = p_sec1.add_run("1. Core Capabilities")
    run_sec1.font.bold = True
    run_sec1.font.size = Pt(11)
    run_sec1.font.color.rgb = RGBColor(30, 64, 175) # Blue 700

    capabilities = [
        ("Property Management & Updates: ", "Inspect any property key in configuration files across all tills, and update values in bulk with an automatic backup created before saving."),
        ("URL Check: ", "Concurrently checks and returns HTTP status codes for essential store URLs (such as central servers, replication endpoints, payment tenders, ClearTax, etc.) directly from the till."),
        ("Version & File Check: ", "Verifies application versions, file sizes, and last modified dates across BO and tills to ensure release consistency."),
        ("Routine Commands & Admin RBAC: ", "Quick execution of pre-configured daily operational tasks, alongside a separate Role-Based Access Control (RBAC) mode for unrestricted command execution when required.")
    ]

    for title, text in capabilities:
        p_bullet = doc.add_paragraph(style='List Bullet')
        p_bullet.paragraph_format.space_after = Pt(3)
        p_bullet.paragraph_format.line_spacing = 1.2
        r_bld = p_bullet.add_run(title)
        r_bld.font.bold = True
        r_bld.font.color.rgb = RGBColor(15, 23, 42)
        r_txt = p_bullet.add_run(text)
        r_txt.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Section 2: Production Architecture (Table Representation)
    p_arch = doc.add_paragraph()
    p_arch.paragraph_format.space_before = Pt(6)
    p_arch.paragraph_format.space_after = Pt(6)
    run_arch = p_arch.add_run("2. Production Architecture Overview")
    run_arch.font.bold = True
    run_arch.font.size = Pt(11)
    run_arch.font.color.rgb = RGBColor(30, 64, 175)

    arch_table = doc.add_table(rows=6, cols=2)
    arch_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(arch_table, color="CBD5E1", sz="4")

    arch_data = [
        ("Windows Desktop App\n(Admin / Operator)", "Desktop user interface console supporting operation mode selection (Properties, URLs, Versions, Commands), store IP / Excel input, live status grid, 1-click retry, and Excel report export."),
        ("SSH Network\n(Secure Channel)", "SSHv2 protocol (Port 22) handling secure authentication, connection pooling, and concurrent task dispatch across store wide-area network links."),
        ("Parallel Execution Engine\n(Operations Controller)", "Multi-threaded core orchestrator executing bulk property reading & updates, automated remote .bak file creation, URL HTTP status checking, version/size extraction, and RBAC routines."),
        ("Store Fleet\n(Ubuntu Linux Machines)", "Target store infrastructure comprising the Store BO Server and all POS Tills (Counters 1..N), hosting application WAR files, local .properties configuration files, and network routing to tender gateways."),
        ("Results Sorter & Retry Engine\n(Sequential Engine)", "Organizes incoming multi-threaded output into deterministic hierarchy (Store -> BO -> Tills 1..N), maintains dedicated mismatch & offline columns, and drives targeted 1-click retries."),
        ("Persistent Storage\n(Local config.json)", "Local JSON configuration retaining saved file paths history, tender URL aliases (with tab auto-completion), routine command catalogs, and user roles across application restarts.")
    ]

    for row_idx, (component, description) in enumerate(arch_data):
        cell_comp = arch_table.rows[row_idx].cells[0]
        cell_desc = arch_table.rows[row_idx].cells[1]

        set_cell_background(cell_comp, "F8FAFC")
        set_cell_margins(cell_comp, top=80, bottom=80, left=120, right=120)
        set_cell_margins(cell_desc, top=80, bottom=80, left=120, right=120)

        p_c = cell_comp.paragraphs[0]
        p_c.paragraph_format.space_after = Pt(0)
        r_c = p_c.add_run(component)
        r_c.font.bold = True
        r_c.font.size = Pt(8.5)
        r_c.font.color.rgb = RGBColor(15, 23, 42)

        p_d = cell_desc.paragraphs[0]
        p_d.paragraph_format.space_after = Pt(0)
        p_d.paragraph_format.line_spacing = 1.15
        r_d = p_d.add_run(description)
        r_d.font.size = Pt(8.2)
        r_d.font.color.rgb = RGBColor(51, 65, 85)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # Technology Stack
    p_tech = doc.add_paragraph()
    p_tech.paragraph_format.space_before = Pt(6)
    p_tech.paragraph_format.space_after = Pt(6)
    run_tech = p_tech.add_run("3. Technology Stack")
    run_tech.font.bold = True
    run_tech.font.size = Pt(11)
    run_tech.font.color.rgb = RGBColor(30, 64, 175)

    tech_table = doc.add_table(rows=3, cols=2)
    tech_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tech_table, color="CBD5E1", sz="4")

    tech_data = [
        ("Core & GUI", "Python 3, Tkinter (Desktop UI), Multi-Threading (ThreadPoolExecutor)"),
        ("Network & Security", "SSHv2 (Port 22)"),
        ("Storage & Reporting", "JSON (Config & History Persistence), OpenPyXL / Pandas (Excel & CSV Reports)")
    ]

    for row_idx, (k, v) in enumerate(tech_data):
        c0 = tech_table.rows[row_idx].cells[0]
        c1 = tech_table.rows[row_idx].cells[1]
        set_cell_background(c0, "F8FAFC")
        set_cell_margins(c0, top=70, bottom=70, left=100, right=100)
        set_cell_margins(c1, top=70, bottom=70, left=100, right=100)

        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(k)
        r0.font.bold = True
        r0.font.size = Pt(8.5)

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(v)
        r1.font.size = Pt(8.5)
        r1.font.color.rgb = RGBColor(51, 65, 85)

    # ==================== PAGE 2: IN-DEPTH WORKFLOW ====================
    doc.add_page_break()

    p_p2 = doc.add_paragraph()
    p_p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_p2 = p_p2.add_run("SYSTEM WORKFLOW & DETAILED DESIGN")
    r_p2.font.name = 'Georgia'
    r_p2.font.size = Pt(17)
    r_p2.font.bold = True
    r_p2.font.color.rgb = RGBColor(15, 23, 42)
    p_p2.paragraph_format.space_after = Pt(12)

    # End-to-End Execution Flow (Numbered Steps Table)
    p_flow = doc.add_paragraph()
    p_flow.paragraph_format.space_before = Pt(4)
    p_flow.paragraph_format.space_after = Pt(6)
    r_flow = p_flow.add_run("4. End-to-End Execution Flow")
    r_flow.font.bold = True
    r_flow.font.size = Pt(11)
    r_flow.font.color.rgb = RGBColor(30, 64, 175)

    steps = [
        ("Step 1: Target Selection", "Operator inputs single store IP or uploads an Excel store batch list. System resolves BO and counter offsets."),
        ("Step 2: Pre-Checks", "Validates IP network boundaries and checks user role (Standard Operator vs Privileged Admin RBAC)."),
        ("Step 3: Choose Action", "Operator selects target action: Property Update, URL Status Check, Version/File Inspection, or Routine Command."),
        ("Step 4: Parallel SSH", "Multi-threaded worker pool connects simultaneously to the store BO and all POS counters over SSHv2."),
        ("Step 5: Safe Execution", "For property updates, an automated .bak backup is saved first; for URLs, HTTP codes are captured; for files, size/date is extracted."),
        ("Step 6: Sorted Display", "Real-time results are sequenced into strict logical order: Store -> BO -> Tills 1..N, with separate mismatch/offline tracking."),
        ("Step 7: Reporting & Retry", "Formatted Excel (.xlsx) report is generated in 1 click; operators can re-test only the failed/offline counters with 1 click.")
    ]

    flow_table = doc.add_table(rows=len(steps), cols=2)
    flow_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(flow_table, color="CBD5E1", sz="4")

    for idx, (st, desc) in enumerate(steps):
        c0 = flow_table.rows[idx].cells[0]
        c1 = flow_table.rows[idx].cells[1]
        set_cell_background(c0, "F8FAFC")
        set_cell_margins(c0, top=60, bottom=60, left=100, right=100)
        set_cell_margins(c1, top=60, bottom=60, left=100, right=100)

        p0 = c0.paragraphs[0]
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(st)
        r0.font.bold = True
        r0.font.size = Pt(8.2)

        p1 = c1.paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        p1.paragraph_format.line_spacing = 1.15
        r1 = p1.add_run(desc)
        r1.font.size = Pt(8.2)
        r1.font.color.rgb = RGBColor(51, 65, 85)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Section 5: How the System Works in Detail (Plain Language)
    p_det = doc.add_paragraph()
    p_det.paragraph_format.space_before = Pt(6)
    p_det.paragraph_format.space_after = Pt(6)
    r_det = p_det.add_run("5. How the System Works in Detail")
    r_det.font.bold = True
    r_det.font.size = Pt(11)
    r_det.font.color.rgb = RGBColor(30, 64, 175)

    deep_points = [
        ("Parallel Connections (Why It Is Fast): ", "In standard operations, engineers connect to machines one after another, waiting for each command to finish before moving to the next. This application opens parallel SSH connections to the store BO and all POS tills simultaneously. Tasks across 15+ machines complete together in seconds rather than taking 20 to 30 minutes of manual waiting."),
        ("Automated Backups (Zero Risk File Edits): ", "Modifying configuration files manually carries the risk of typos that can stop a till from billing. Before this tool applies any property update, it automatically creates a timestamped backup copy on the remote machine. If an incorrect value is ever pushed, the previous working configuration can be restored immediately."),
        ("Direct Network URL Checks (Real Visibility): ", "Testing external URLs from an office laptop does not prove the store counters can connect to them. This tool commands each individual till to test payment gateway and central endpoints through its own local network. This immediately confirms whether that specific till can process payments or reach ClearTax."),
        ("Deterministic Ordering & Targeted Re-Tests: ", "Parallel results can return out of order as fast tills respond before slower ones. The built-in sorter reorganizes incoming data into clean logical order (Store -> BO -> Till 1 to N). Furthermore, if any counter was offline or mismatched, operators can re-test just those failed machines with one click without repeating the rest.")
    ]

    for title, text in deep_points:
        p_pt = doc.add_paragraph()
        p_pt.paragraph_format.space_after = Pt(4)
        p_pt.paragraph_format.line_spacing = 1.18
        r_bld = p_pt.add_run(title)
        r_bld.font.bold = True
        r_bld.font.color.rgb = RGBColor(15, 23, 42)
        r_txt = p_pt.add_run(text)
        r_txt.font.color.rgb = RGBColor(51, 65, 85)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # Section 6: Operational Impact & Benefits Table
    p_imp = doc.add_paragraph()
    p_imp.paragraph_format.space_before = Pt(6)
    p_imp.paragraph_format.space_after = Pt(6)
    r_imp = p_imp.add_run("6. Operational Impact & Benefits")
    r_imp.font.bold = True
    r_imp.font.size = Pt(11)
    r_imp.font.color.rgb = RGBColor(30, 64, 175)

    impact_table = doc.add_table(rows=6, cols=3)
    impact_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(impact_table, color="CBD5E1", sz="4")

    headers = ["Operational Area", "Traditional Manual Process", "With POS Operations Hub"]
    for i, h in enumerate(headers):
        c = impact_table.rows[0].cells[i]
        set_cell_background(c, "E2E8F0")
        set_cell_margins(c, top=80, bottom=80, left=100, right=100)
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(h)
        r.font.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(15, 23, 42)

    impact_data = [
        ("Config & Property Changes", "Logging into 10–15 counters individually via PuTTY to edit files by hand; high risk of human error.", "Bulk inspection and 1-click update across all counters simultaneously, with automated backup."),
        ("Payment & Tender URLs", "Discovered only when a billing till fails during live store operations or customer checkout.", "Pre-checks all payment, central, and tax URLs directly from the till, returning live HTTP status codes."),
        ("Release & Version Checks", "Manual spot-checking of a few sample machines; partial rollouts or mismatches go unnoticed.", "Comprehensive check of versions, file sizes, and edit dates across 100% of store endpoints."),
        ("Daily Routine Commands", "Typing long shell commands from memory; potential for mistakes or unauthorized system changes.", "Pre-configured routine command menu for the team, backed by an elevated admin RBAC mode."),
        ("Management Reporting", "Manually copying terminal outputs into spreadsheets; time-consuming and prone to missing data.", "Instant, formatted Excel (.xlsx) export with clear separation for matched, mismatched, and offline tills.")
    ]

    for row_idx, (area, trad, modern) in enumerate(impact_data, start=1):
        r = impact_table.rows[row_idx]
        for col_idx, text in enumerate([area, trad, modern]):
            c = r.cells[col_idx]
            if row_idx % 2 == 1:
                set_cell_background(c, "F8FAFC")
            set_cell_margins(c, top=65, bottom=65, left=100, right=100)
            p = c.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            run = p.add_run(text)
            run.font.size = Pt(8.2)
            if col_idx == 0:
                run.font.bold = True
                run.font.color.rgb = RGBColor(15, 23, 42)
            else:
                run.font.color.rgb = RGBColor(51, 65, 85)

    doc.save(output_path)
    print(f"Successfully generated Word document: {output_path}")

if __name__ == "__main__":
    build_docx(r"c:\Users\gamin\OneDrive\Desktop\projects\tills\POS_Operations_Hub.docx")

