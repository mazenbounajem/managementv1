from nicegui import ui
from datetime import date
from connection import connection
from io import BytesIO
import base64

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

from report_scope_ensure import ensure_report_scope_tables
from session_storage import session_storage


def _q(sql, params=None):
    rows = []
    connection.contogetrows(sql, rows, params) if params else connection.contogetrows(sql, rows)
    return rows


def _company():
    try:
        info = connection.get_company_info()
        return info.get("company_name", "Company") if info else "Company"
    except Exception:
        return "Company"


def _ts(header_color="#8a2be2"):
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_color)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5edff")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#ccc0dd")),
            ("FONTSIZE", (0, 1), (-1, -1), 7.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def _build(elements, landscape_mode=False):
    buf = BytesIO()
    ps = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(
        buf,
        pagesize=ps,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    doc.build(elements)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _show(b64, title):
    data_url = f"data:application/pdf;base64,{b64}"
    with ui.dialog() as d:
        with ui.card().classes("w-screen h-screen max-w-none max-h-none m-0 rounded-none"):
            with ui.row().classes("w-full justify-between items-center p-3 bg-gray-900 border-b border-white/10"):
                ui.label(title).classes("text-white font-bold text-lg")
                ui.button("X Close", on_click=d.close).classes("bg-red-600 text-white px-4 py-1 rounded text-sm")
            ui.html(
                f'<iframe src="{data_url}" width="100%" height="100%" style="border:none; min-height:calc(100vh - 56px);"></iframe>'
            ).classes("w-full flex-1")
    d.open()


def _hdr(name, fd, td, accent="#8a2be2"):
    s = getSampleStyleSheet()
    ts_style = ParagraphStyle("t", parent=s["Heading1"], fontSize=16, spaceAfter=4)
    ss_style = ParagraphStyle("s", parent=s["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=8)
    return [
        Paragraph(f"{_company()} — {name}", ts_style),
        Paragraph(f"Period: {fd}  to  {td}", ss_style),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor(accent)),
        Spacer(1, 6 * mm),
    ]


def _totrow(ts_obj, idx, bg="#4b0082"):
    ts_obj.add("BACKGROUND", (0, idx), (-1, idx), colors.HexColor(bg))
    ts_obj.add("TEXTCOLOR", (0, idx), (-1, idx), colors.yellow)
    ts_obj.add("FONTNAME", (0, idx), (-1, idx), "Helvetica-Bold")


# ─────────────────────────────────────────────────────────────────────────────
# UI selection helpers (legacy)
# ─────────────────────────────────────────────────────────────────────────────

def _get_selected_aux():
    """
    AuxiliaryUI-driven selection (statement/trial-balance detail).
    """
    try:
        from auxiliaryui import AuxiliaryUI

        for instance in AuxiliaryUI.instances:
            if hasattr(instance, "get_selected_aux_number"):
                aux = instance.get_selected_aux_number()
                if aux:
                    return aux
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Audience + scope + audit logging (auditors / MOF / owners / QA)
# ─────────────────────────────────────────────────────────────────────────────

def _get_current_user():
    try:
        u = session_storage.get("user", None)
        return u
    except Exception:
        return None


def _get_audience_key_for_role(role_name: str):
    if not role_name:
        return "owner"
    rn = str(role_name).strip().lower()
    if "auditor" in rn:
        return "auditor"
    if "ministry" in rn or rn in ("mof", "mo f", "ministry of finance"):
        return "mof"
    if "quality" in rn or rn in ("qa",):
        return "qa"
    if "owner" in rn or "business" in rn:
        return "owner"
    return "owner"


def _get_role_id():
    user = _get_current_user() or {}
    return user.get("role_id")


def _get_audience_scope_prefixes(audience_key: str):
    """
    Returns list[str] of allowed auxiliary prefixes from role_report_scope.allowed_aux_prefixes.
    If missing, returns None => no scoping (allow all).
    """
    try:
        ensure_report_scope_tables()
        role_id = _get_role_id()
        if not role_id:
            return None

        rows = []
        connection.contogetrows(
            """
            SELECT allowed_aux_prefixes
            FROM role_report_scope
            WHERE role_id = ? AND audience_key = ?
            """,
            rows,
            (role_id, audience_key),
        )
        if not rows:
            return None

        allowed = rows[0][0]
        if allowed is None:
            return None

        allowed = str(allowed).strip()
        if not allowed or allowed.lower() in ("none", "null", "%"):
            return None

        return [p.strip() for p in allowed.split(",") if p.strip()] or None
    except Exception:
        return None


def _build_aux_scoped_predicate(alias: str, audience_key: str):
    """
    Build SQL predicate for table alias `alias`:
      (a.number LIKE ? OR a.number LIKE ? ...)
    with params being prefix% patterns.
    If no scope configured, returns ('1=1', []).
    """
    prefixes = _get_audience_scope_prefixes(audience_key)
    if not prefixes:
        return "1=1", []

    predicate_parts = []
    params = []
    for p in prefixes:
        predicate_parts.append(f"{alias}.number LIKE ?")
        params.append(f"{p}%")

    return "(" + " OR ".join(predicate_parts) + ")", params


def _log_report_audit(
        audience_key: str,
        report_key: str,
        from_date,
        to_date,
        auxiliary_id=None,
        ledger_root_prefix=None,
        status="SUCCESS",
        error_message=None,
):
    """
    Immutable audit trail of report generations.

    Populates filters_json with structured report context (and best-effort request metadata).
    """
    try:
        ensure_report_scope_tables()
        user = _get_current_user() or {}

        # Best-effort: if NiceGUI request context is available, include method/path.
        request_meta = None
        try:
            # NiceGUI exposes Starlette request on nicegui.app.request (when available).
            from nicegui import app as nicegui_app  # type: ignore

            req = getattr(nicegui_app, "request", None)
            if req:
                request_meta = {
                    "method": getattr(req, "method", None),
                    "path": getattr(req.url, "path", None) if getattr(req, "url", None) else None,
                    "client_ip": getattr(getattr(req, "client", None), "host", None) if getattr(req, "client", None) else None,
                }
        except Exception:
            request_meta = None

        filters = {
            "audience_key": audience_key,
            "report_key": report_key,
            "from_date": str(from_date) if from_date is not None else None,
            "to_date": str(to_date) if to_date is not None else None,
            "auxiliary_id": auxiliary_id,
            "ledger_root_prefix": ledger_root_prefix,
        }
        if request_meta:
            filters["request"] = request_meta

        # Local import to avoid changing global imports at top of file.
        import json

        ensure_json = json.dumps(filters, ensure_ascii=False)

        connection.insertingtodatabase(
            """
            INSERT INTO report_audit_log
              (user_id, role_id, role_name, audience_key, report_key, from_date, to_date,
               auxiliary_id, ledger_root_prefix, status, error_message, filters_json)
            VALUES
              (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user.get("user_id"),
                user.get("role_id"),
                user.get("role_name"),
                audience_key,
                report_key,
                from_date,
                to_date,
                auxiliary_id,
                ledger_root_prefix,
                status,
                error_message,
                ensure_json,
            ),
        )
    except Exception:
        pass


def _current_audience_key():
    user = _get_current_user() or {}
    return _get_audience_key_for_role(user.get("role_name"))


# ─────────────────────────────────────────────────────────────────────────────
# REPORTS
# ─────────────────────────────────────────────────────────────────────────────

def report_auxiliary_statement(fd, td, aux_num=None):
    if not aux_num:
        aux_num = _get_selected_aux()
    if not aux_num:
        ui.notify("Please select an auxiliary from the table first.", color="warning")
        return

    # auxiliaryui passes auxiliary.number (e.g. '4111.000001').
    # But accounting_transaction_lines may store:
    #   - auxiliary_id (INT) when the line is a real auxiliary,
    #   - or NULL auxiliary_id and only account_number (e.g. '5300.000001') for cash/ledger.
    #
    # So we LEFT JOIN auxiliary and filter by either:
    #   - a.number = aux_num (real auxiliary lines)
    #   - OR l.account_number = aux_num OR l.account_number LIKE base+'.%' (cash/ledger lines)
    base = str(aux_num).split(".")[0]

    sql = """
        SELECT CONVERT(varchar(10), ht.transaction_date, 23),
               ht.reference_type, ht.jv_id, l.debit, l.credit, ht.description
        FROM accounting_transactions ht
        JOIN accounting_transaction_lines l ON ht.jv_id = l.jv_id
        LEFT JOIN auxiliary a ON l.auxiliary_id = a.id
        WHERE (
                a.number = ?
             OR l.account_number = ?
             OR l.account_number LIKE ? + '.%'
        )
          AND CONVERT(date, ht.transaction_date) >= ?
          AND CONVERT(date, ht.transaction_date) <= ?
        ORDER BY ht.transaction_date ASC, ht.jv_id ASC
    """
    rows = _q(sql, (aux_num, aux_num, base, fd, td))
    if not rows:
        ui.notify("No transactions found for this account.", color="warning")
        return

    # Prefer auxiliary account name if it exists; otherwise show aux_num/base.
    name_row = _q("SELECT account_name FROM auxiliary WHERE number=?", (aux_num,))
    acc_name = str(name_row[0][0]) if name_row else aux_num

    elements = _hdr(f"Statement of Account — {acc_name} ({aux_num})", fd, td)
    hdr = ["Date", "Type", "JV ID", "Description", "Debit", "Credit", "Balance"]
    data = [hdr]
    ts_obj = _ts()
    running = 0.0

    open_sql = """
        SELECT SUM(ISNULL(l.debit,0)) - SUM(ISNULL(l.credit,0))
        FROM accounting_transactions ht
        JOIN accounting_transaction_lines l ON ht.jv_id = l.jv_id
        LEFT JOIN auxiliary a ON l.auxiliary_id = a.id
        WHERE (
                a.number = ?
             OR l.account_number = ?
             OR l.account_number LIKE ? + '.%'
        )
          AND CONVERT(date, ht.transaction_date) < ?
    """
    open_res = _q(open_sql, (aux_num, aux_num, base, fd))
    if open_res and open_res[0][0]:
        running = float(open_res[0][0])
        data.append(["", "OPENING", "", "Opening Balance", "", "", f"${running:.2f}"])

    tot_deb, tot_cred = 0.0, 0.0
    for i, r in enumerate(rows, len(data)):
        deb = float(r[3] or 0)
        cred = float(r[4] or 0)
        tot_deb += deb
        tot_cred += cred
        running += deb - cred

        data.append(
            [
                str(r[0] or ""),
                str(r[1] or ""),
                str(r[2] or ""),
                str(r[5] or ""),
                f"${deb:.2f}",
                f"${cred:.2f}",
                f"${running:.2f}",
            ]
        )
        if running < 0:
            ts_obj.add("TEXTCOLOR", (6, i), (6, i), colors.red)

    data.append(["TOTAL", "", "", "", f"${tot_deb:.2f}", f"${tot_cred:.2f}", f"${running:.2f}"])
    _totrow(ts_obj, len(data) - 1)

    ps = A4
    avail = ps[0] - 30 * mm
    cw = [avail * w for w in [0.12, 0.13, 0.08, 0.31, 0.12, 0.12, 0.12]]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements), "Statement of Account")


def report_auxiliary_trial_balance(fd, td):
    aux_num = _get_selected_aux()
    if not aux_num:
        prefix = "%"
    else:
        prefix = aux_num.split(".")[0] + ".%"

    sql = """
        SELECT a.number, a.account_name,
               ISNULL(SUM(l.debit), 0) AS d, ISNULL(SUM(l.credit), 0) AS c
        FROM auxiliary a
        JOIN accounting_transaction_lines l ON a.id = l.auxiliary_id
        JOIN accounting_transactions t ON l.jv_id = t.jv_id
        WHERE a.number LIKE ?
          AND CONVERT(date, t.transaction_date) >= ?
          AND CONVERT(date, t.transaction_date) <= ?
        GROUP BY a.number, a.account_name
        ORDER BY a.number
    """
    rows = _q(sql, (prefix, fd, td))
    if not rows:
        ui.notify("No trial balance data.", color="warning")
        return

    elements = _hdr("Trial Balance", fd, td)
    hdr = ["Aux Number", "Account Name", "Total Debit", "Total Credit", "Net Balance"]
    data = [hdr]
    ts_obj = _ts()

    tot_d, tot_c = 0.0, 0.0
    for r in rows:
        d = float(r[2])
        c = float(r[3])
        tot_d += d
        tot_c += c
        bal = d - c
        data.append([str(r[0]), str(r[1]), f"${d:.2f}", f"${c:.2f}", f"{bal:.2f}"])

    data.append(["TOTAL", "", f"${tot_d:.2f}", f"${tot_c:.2f}", f"${(tot_d - tot_c):.2f}"])
    _totrow(ts_obj, len(data) - 1)

    ps = A4
    avail = ps[0] - 30 * mm
    cw = [avail * w for w in [0.20, 0.35, 0.15, 0.15, 0.15]]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements), "Trial Balance")


def report_auxiliary_transactions(fd, td):
    sql = """
        SELECT CONVERT(varchar(10), t.transaction_date, 23),
               t.jv_id,
               a.number,
               a.account_name,
               l.debit,
               l.credit,
               ht.description
        FROM accounting_transactions t
        JOIN accounting_transaction_lines l ON t.jv_id = l.jv_id
        JOIN auxiliary a ON l.auxiliary_id = a.id
        JOIN accounting_transactions ht ON t.jv_id = ht.jv_id
        WHERE CONVERT(date, t.transaction_date) >= ?
          AND CONVERT(date, t.transaction_date) <= ?
        ORDER BY t.transaction_date DESC, t.jv_id DESC
    """
    rows = _q(sql, (fd, td))
    if not rows:
        ui.notify("No transactions for this period.", color="warning")
        return

    elements = _hdr("Auxiliary Ledger Transactions", fd, td)
    hdr = ["Date", "JV", "Aux Number", "Account Name", "Debit", "Credit", "Description"]
    data = [hdr]
    ts_obj = _ts()

    td_deb, td_cred = 0.0, 0.0
    for r in rows:
        d = float(r[4] or 0)
        c = float(r[5] or 0)
        td_deb += d
        td_cred += c
        data.append([str(r[0]), str(r[1]), str(r[2]), str(r[3]), f"${d:.2f}", f"${c:.2f}", str(r[6] or "")])

    data.append(["TOTAL", "", "", "", f"${td_deb:.2f}", f"${td_cred:.2f}", ""])
    _totrow(ts_obj, len(data) - 1)

    ps = landscape(A4)
    avail = ps[0] - 30 * mm
    cw = [avail * w for w in [0.10, 0.06, 0.12, 0.22, 0.10, 0.10, 0.30]]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements, landscape_mode=True), "Ledger Transactions")


def report_global_auxiliary_balance(fd, td, audience_key: str = None):
    """
    Global auxiliary report for auditor/MOF/owner/QA:
      - Debit totals per auxiliary (up to <= td)
      - Credit totals per auxiliary (up to <= td)
      - Net balance = debit - credit
    Scoping differs per audience via role_report_scope.allowed_aux_prefixes.

    Implemented with GROUP BY aggregation (no correlated subqueries).
    """
    if not audience_key:
        audience_key = _current_audience_key()

    ensure_report_scope_tables()
    _log_report_audit(audience_key, "aux_global", fd, td, status="SUCCESS")

    aux_predicate, aux_params = _build_aux_scoped_predicate("a", audience_key)

    sql = f"""
        SELECT
            a.number,
            a.account_name,
            l.Name_en,
            ISNULL(SUM(al.debit), 0) AS total_debit,
            ISNULL(SUM(al.credit), 0) AS total_credit,
            (ISNULL(SUM(al.debit), 0) - ISNULL(SUM(al.credit), 0)) AS net_balance
        FROM auxiliary a
        LEFT JOIN Ledger l ON a.auxiliary_id = l.AccountNumber
        LEFT JOIN accounting_transaction_lines al ON al.auxiliary_id = a.id
        LEFT JOIN accounting_transactions at ON al.jv_id = at.jv_id
        WHERE a.status = 1
          AND {aux_predicate}
          AND CONVERT(date, at.transaction_date) <= ?
        GROUP BY
            a.number,
            a.account_name,
            l.Name_en
        ORDER BY net_balance DESC, a.number
    """

    # td param used once (aggregation)
    rows = _q(sql, (td,) + tuple(aux_params))
    if not rows:
        ui.notify("No active auxiliaries found.", color="warning")
        return

    # PDF title varies slightly by audience
    elements = _hdr("Global Auxiliary Balance", fd, td, accent="#8a2be2")
    hdr = ["Aux Number", "Account Name", "Ledger", "Debit", "Credit", "Net Balance"]
    data = [hdr]
    ts_obj = _ts()

    tot_deb, tot_cred = 0.0, 0.0
    for r in rows:
        aux_no = str(r[0] or "")
        acc_name = str(r[1] or "")
        ledger = str(r[2] or "")
        deb = float(r[3] or 0)
        cred = float(r[4] or 0)
        net = float(r[5] or 0)

        tot_deb += deb
        tot_cred += cred

        data.append([aux_no, acc_name, ledger, f"${deb:.2f}", f"${cred:.2f}", f"${net:.2f}"])

    tot_net = tot_deb - tot_cred
    data.append(["TOTAL", "", "", f"${tot_deb:.2f}", f"${tot_cred:.2f}", f"${tot_net:.2f}"])
    _totrow(ts_obj, len(data) - 1)

    ps = A4
    avail = ps[0] - 30 * mm
    cw = [avail * w for w in [0.16, 0.28, 0.20, 0.12, 0.12, 0.12]]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements), "Global Balance")


# ─────────────────────────────────────────────────────────────────────────────
# Report Center UI
# ─────────────────────────────────────────────────────────────────────────────

# ── New Reports: Sale/Purchase and VAT ──────────────────────────────────────

def report_sale_and_vat(fd, td, aux_num=None):
    if not aux_num:
        aux_num = _get_selected_aux()
    
    sql = """
        SELECT s.invoice_number, CONVERT(varchar(10), s.sale_date, 23),
               c.customer_name, s.subtotal, s.total_vat, s.total_amount
        FROM sales s
        INNER JOIN customers c ON s.customer_id = c.id
        WHERE s.status = 'Sale'
          AND (c.auxiliary_number = ? OR ? IS NULL)
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
        ORDER BY s.sale_date, s.invoice_number
    """
    rows = _q(sql, (aux_num, aux_num, fd, td))
    if not rows:
        ui.notify("No sales data for this period.", color="warning")
        return

    elements = _hdr(f"Sale and VAT Report" + (f" — {aux_num}" if aux_num else ""), fd, td)
    hdr = ["Invoice #", "Date", "Customer", "Base HT", "VAT", "Total TTC"]
    data = [hdr]
    ts_obj = _ts()
    
    tot_ht, tot_vat, tot_ttc = 0.0, 0.0, 0.0
    for r in rows:
        ht, vat, ttc = float(r[3] or 0), float(r[4] or 0), float(r[5] or 0)
        tot_ht += ht; tot_vat += vat; tot_ttc += ttc
        data.append([str(r[0]), str(r[1]), str(r[2]), f"${ht:.2f}", f"${vat:.2f}", f"${ttc:.2f}"])
    
    data.append(["TOTAL", "", "", f"${tot_ht:.2f}", f"${tot_vat:.2f}", f"${tot_ttc:.2f}"])
    _totrow(ts_obj, len(data)-1)
    
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [0.15, 0.12, 0.31, 0.14, 0.14, 0.14]]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements), "Sale and VAT")

def report_return_sales_and_vat(fd, td, aux_num=None):
    if not aux_num:
        aux_num = _get_selected_aux()
    
    sql = """
        SELECT sr.invoice_number, CONVERT(varchar(10), sr.return_date, 23),
               c.customer_name, sr.subtotal, sr.total_vat, sr.total_amount
        FROM sales_returns sr
        INNER JOIN customers c ON sr.customer_id = c.id
        WHERE (c.auxiliary_number = ? OR ? IS NULL)
          AND CONVERT(date, sr.return_date) >= ?
          AND CONVERT(date, sr.return_date) <= ?
        ORDER BY sr.return_date, sr.invoice_number
    """
    rows = _q(sql, (aux_num, aux_num, fd, td))
    if not rows:
        ui.notify("No return sales data for this period.", color="warning")
        return

    elements = _hdr(f"Return Sales and VAT Report" + (f" — {aux_num}" if aux_num else ""), fd, td, accent="#dc2626")
    hdr = ["Invoice #", "Date", "Customer", "Base HT", "VAT", "Total TTC"]
    data = [hdr]
    # Use red-ish theme for returns
    ts_obj = _ts(header_color="#dc2626")
    ts_obj.add('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff1f2")])
    
    tot_ht, tot_vat, tot_ttc = 0.0, 0.0, 0.0
    for r in rows:
        ht, vat, ttc = float(r[3] or 0), float(r[4] or 0), float(r[5] or 0)
        tot_ht += ht; tot_vat += vat; tot_ttc += ttc
        data.append([str(r[0]), str(r[1]), str(r[2]), f"${ht:.2f}", f"${vat:.2f}", f"${ttc:.2f}"])
    
    data.append(["TOTAL", "", "", f"${tot_ht:.2f}", f"${tot_vat:.2f}", f"${tot_ttc:.2f}"])
    _totrow(ts_obj, len(data)-1, bg="#991b1b")
    
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [0.15, 0.12, 0.31, 0.14, 0.14, 0.14]]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements), "Return Sales and VAT")

def report_purchase_and_vat(fd, td, aux_num=None):
    if not aux_num:
        aux_num = _get_selected_aux()
    
    sql = """
        SELECT p.invoice_number, CONVERT(varchar(10), p.purchase_date, 23),
               s.name, p.subtotal, ISNULL(p.total_vat,0), p.final_total
        FROM purchases p
        INNER JOIN suppliers s ON p.supplier_id = s.id
        WHERE (s.auxiliary_number = ? OR ? IS NULL)
          AND CONVERT(date, p.purchase_date) >= ?
          AND CONVERT(date, p.purchase_date) <= ?
        ORDER BY p.purchase_date, p.invoice_number
    """
    rows = _q(sql, (aux_num, aux_num, fd, td))
    if not rows:
        ui.notify("No purchase data for this period.", color="warning")
        return

    elements = _hdr(f"Purchase and VAT Report" + (f" — {aux_num}" if aux_num else ""), fd, td, accent="#2563eb")
    hdr = ["Invoice #", "Date", "Supplier", "Base HT", "VAT", "Total TTC"]
    data = [hdr]
    ts_obj = _ts(header_color="#2563eb")
    ts_obj.add('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#eff6ff")])
    
    tot_ht, tot_vat, tot_ttc = 0.0, 0.0, 0.0
    for r in rows:
        ht, vat, ttc = float(r[3] or 0), float(r[4] or 0), float(r[5] or 0)
        tot_ht += ht; tot_vat += vat; tot_ttc += ttc
        data.append([str(r[0]), str(r[1]), str(r[2]), f"${ht:.2f}", f"${vat:.2f}", f"${ttc:.2f}"])
    
    data.append(["TOTAL", "", "", f"${tot_ht:.2f}", f"${tot_vat:.2f}", f"${tot_ttc:.2f}"])
    _totrow(ts_obj, len(data)-1, bg="#1e40af")
    
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [0.15, 0.12, 0.31, 0.14, 0.14, 0.14]]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements), "Purchase and VAT")

def report_return_purchase_and_vat(fd, td, aux_num=None):
    if not aux_num:
        aux_num = _get_selected_aux()
    
    # Using purchase_returns table
    sql = """
        SELECT pr.invoice_number, CONVERT(varchar(10), pr.return_date, 23),
               s.name, pr.subtotal, pr.total_vat, pr.total_amount
        FROM purchase_returns pr
        INNER JOIN suppliers s ON pr.supplier_id = s.id
        WHERE (s.auxiliary_number = ? OR ? IS NULL)
          AND CONVERT(date, pr.return_date) >= ?
          AND CONVERT(date, pr.return_date) <= ?
        ORDER BY pr.return_date, pr.invoice_number
    """
    rows = _q(sql, (aux_num, aux_num, fd, td))
    if not rows:
        ui.notify("No return purchase data for this period.", color="warning")
        return

    elements = _hdr(f"Return Purchase and VAT Report" + (f" — {aux_num}" if aux_num else ""), fd, td, accent="#ea580c")
    hdr = ["Invoice #", "Date", "Supplier", "Base HT", "VAT", "Total TTC"]
    data = [hdr]
    ts_obj = _ts(header_color="#ea580c")
    ts_obj.add('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff7ed")])
    
    tot_ht, tot_vat, tot_ttc = 0.0, 0.0, 0.0
    for r in rows:
        ht, vat, ttc = float(r[3] or 0), float(r[4] or 0), float(r[5] or 0)
        tot_ht += ht; tot_vat += vat; tot_ttc += ttc
        data.append([str(r[0]), str(r[1]), str(r[2]), f"${ht:.2f}", f"${vat:.2f}", f"${ttc:.2f}"])
    
    data.append(["TOTAL", "", "", f"${tot_ht:.2f}", f"${tot_vat:.2f}", f"${tot_ttc:.2f}"])
    _totrow(ts_obj, len(data)-1, bg="#9a3412")
    
    avail = A4[0] - 30*mm
    cw = [avail*w for w in [0.15, 0.12, 0.31, 0.14, 0.14, 0.14]]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)
    _show(_build(elements), "Return Purchase and VAT")


def _vat_sum_components_sales(fd, td, aux_num=None):
    """
    Sales VAT components:
      non_taxable_base = SUM(total_price where vat_percentage=0)
      taxable_base     = SUM(total_price where vat_percentage>0)
      vat_total        = SUM(vat_amount)
    """
    if not aux_num:
        aux_num = _get_selected_aux()

    sql = """
        SELECT
            SUM(CASE WHEN ISNULL(si.vat_percentage,0) = 0 THEN ISNULL(si.total_price,0) ELSE 0 END) AS non_tax_base,
            SUM(CASE WHEN ISNULL(si.vat_percentage,0) > 0 THEN ISNULL(si.total_price,0) ELSE 0 END) AS tax_base,
            SUM(ISNULL(si.vat_amount,0)) AS vat_total
        FROM sales s
        INNER JOIN customers c ON c.id = s.customer_id
        INNER JOIN sale_items si ON si.sales_id = s.id
        WHERE s.status = 'Sale'
          AND (c.auxiliary_number = ? OR ? IS NULL)
          AND CONVERT(date, s.sale_date) >= ?
          AND CONVERT(date, s.sale_date) <= ?
    """
    rows = _q(sql, (aux_num, aux_num, fd, td))
    if not rows:
        return 0.0, 0.0, 0.0
    r = rows[0]
    non_tax = float(r[0] or 0)
    tax = float(r[1] or 0)
    vat = float(r[2] or 0)
    return non_tax, tax, vat


def _vat_sum_components_sales_returns(fd, td, aux_num=None):
    if not aux_num:
        aux_num = _get_selected_aux()

    sql = """
        SELECT
            SUM(CASE WHEN ISNULL(sri.vat_percentage,0) = 0 THEN ISNULL(sri.total_price,0) ELSE 0 END) AS non_tax_base,
            SUM(CASE WHEN ISNULL(sri.vat_percentage,0) > 0 THEN ISNULL(sri.total_price,0) ELSE 0 END) AS tax_base,
            SUM(ISNULL(sri.vat_amount,0)) AS vat_total
        FROM sales_returns sr
        INNER JOIN customers c ON c.id = sr.customer_id
        INNER JOIN sales_return_items sri ON sri.sales_return_id = sr.id
        WHERE (c.auxiliary_number = ? OR ? IS NULL)
          AND CONVERT(date, sr.return_date) >= ?
          AND CONVERT(date, sr.return_date) <= ?
    """
    rows = _q(sql, (aux_num, aux_num, fd, td))
    if not rows:
        return 0.0, 0.0, 0.0
    r = rows[0]
    return float(r[0] or 0), float(r[1] or 0), float(r[2] or 0)


def _vat_sum_components_purchases(fd, td, aux_num=None):
    if not aux_num:
        aux_num = _get_selected_aux()

    sql = """
        SELECT
            SUM(CASE WHEN ISNULL(pi.vat_percentage,0) = 0 THEN ISNULL(pi.total_cost,0) ELSE 0 END) AS non_tax_base,
            SUM(CASE WHEN ISNULL(pi.vat_percentage,0) > 0 THEN ISNULL(pi.total_cost,0) ELSE 0 END) AS tax_base,
            SUM(ISNULL(pi.vat_amount,0)) AS vat_total
        FROM purchases p
        INNER JOIN suppliers s ON s.id = p.supplier_id
        INNER JOIN purchase_items pi ON pi.purchase_id = p.id
        WHERE (s.auxiliary_number = ? OR ? IS NULL)
          AND CONVERT(date, p.purchase_date) >= ?
          AND CONVERT(date, p.purchase_date) <= ?
    """
    rows = _q(sql, (aux_num, aux_num, fd, td))
    if not rows:
        return 0.0, 0.0, 0.0
    r = rows[0]
    return float(r[0] or 0), float(r[1] or 0), float(r[2] or 0)


def _vat_sum_components_purchase_returns(fd, td, aux_num=None):
    if not aux_num:
        aux_num = _get_selected_aux()

    sql = """
        SELECT
            SUM(CASE WHEN ISNULL(pri.vat_percentage,0) = 0 THEN ISNULL(pri.total_cost,0) ELSE 0 END) AS non_tax_base,
            SUM(CASE WHEN ISNULL(pri.vat_percentage,0) > 0 THEN ISNULL(pri.total_cost,0) ELSE 0 END) AS tax_base,
            SUM(ISNULL(pri.vat_amount,0)) AS vat_total
        FROM purchase_returns pr
        INNER JOIN suppliers s ON s.id = pr.supplier_id
        INNER JOIN purchase_return_items pri ON pri.purchase_return_id = pr.id
        WHERE (s.auxiliary_number = ? OR ? IS NULL)
          AND CONVERT(date, pr.return_date) >= ?
          AND CONVERT(date, pr.return_date) <= ?
    """
    rows = _q(sql, (aux_num, aux_num, fd, td))
    if not rows:
        return 0.0, 0.0, 0.0
    r = rows[0]
    return float(r[0] or 0), float(r[1] or 0), float(r[2] or 0)


def report_vat_summary_center(fd, td, aux_num=None):
    """
    VAT Summary (requested):
      Line 1: Sales non-tax, tax, total, VAT
      Line 2: Sales Return non-tax, tax, total, VAT
      Line 3: Sales - Return non-tax, tax, total, VAT
      Line 4: Purchase ...
      Line 5: Purchase Return ...
      Line 6: Purchase - Return ...
      Line 7: Sales - Purchase ...
    """
    if not aux_num:
        aux_num = _get_selected_aux()

    s_nt, s_t, s_vat = _vat_sum_components_sales(fd, td, aux_num)
    sr_nt, sr_t, sr_vat = _vat_sum_components_sales_returns(fd, td, aux_num)

    net_s_nt = s_nt - sr_nt
    net_s_t = s_t - sr_t
    net_s_vat = s_vat - sr_vat
    net_s_total = net_s_nt + net_s_t

    p_nt, p_t, p_vat = _vat_sum_components_purchases(fd, td, aux_num)
    pr_nt, pr_t, pr_vat = _vat_sum_components_purchase_returns(fd, td, aux_num)

    net_p_nt = p_nt - pr_nt
    net_p_t = p_t - pr_t
    net_p_vat = p_vat - pr_vat
    net_p_total = net_p_nt + net_p_t

    diff_sp_nt = s_nt - p_nt
    diff_sp_t = s_t - p_t
    diff_sp_vat = s_vat - p_vat
    diff_sp_total = diff_sp_nt + diff_sp_t

    elements = _hdr(f"VAT Summary Center — {aux_num}", fd, td, accent="#0ea5e9")

    hdr = ["Section", "Non Taxable Base", "Taxable Base", "Total Base", "VAT"]
    data = [hdr]
    ts_obj = _ts(header_color="#0ea5e9")

    def add_row(section, nt, t, vat):
        data.append([
            section,
            f"${nt:.2f}",
            f"${t:.2f}",
            f"${(nt + t):.2f}",
            f"${vat:.2f}",
        ])

    add_row("1) Sales", s_nt, s_t, s_vat)
    add_row("2) Sales Return", sr_nt, sr_t, sr_vat)
    add_row("3) Sales - Return", net_s_nt, net_s_t, net_s_vat)

    add_row("4) Purchase", p_nt, p_t, p_vat)
    add_row("5) Purchase Return", pr_nt, pr_t, pr_vat)
    add_row("6) Purchase - Return", net_p_nt, net_p_t, net_p_vat)

    add_row("7) Sales - Purchase", diff_sp_nt, diff_sp_t, diff_sp_vat)

    # Styling: total-like row not required; just highlight header.
    avail = A4[0] - 30 * mm
    cw = [avail * 0.30, avail * 0.18, avail * 0.18, avail * 0.18, avail * 0.16]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(ts_obj)
    elements.append(t)

    _show(_build(elements), "VAT Summary")


# ─────────────────────────────────────────────────────────────────────────────
# Report Center UI
# ─────────────────────────────────────────────────────────────────────────────

def open_print_special_dialog():
    today = date.today().strftime("%Y-%m-%d")
    first_of_month = date.today().replace(day=1).strftime("%Y-%m-%d")
    selected_aux = _get_selected_aux()

    REPORTS = {
        "stmt": ("Statement of Account", lambda f, t, a: report_auxiliary_statement(f, t, a)),
        "sale_vat": ("Sale and VAT", lambda f, t, a: report_sale_and_vat(f, t, a)),
        "ret_sale_vat": ("Return Sales and VAT", lambda f, t, a: report_return_sales_and_vat(f, t, a)),
        "pur_vat": ("Purchase and VAT", lambda f, t, a: report_purchase_and_vat(f, t, a)),
        "ret_pur_vat": ("Return Purchase and VAT", lambda f, t, a: report_return_purchase_and_vat(f, t, a)),
        "vat_summary_center": ("VAT Summary Center", lambda f, t, a: report_vat_summary_center(f, t, a)),
        "auditor": ("Global Balance (Auditor)", lambda f, t, a: report_global_auxiliary_balance(f, t, "auditor")),
        "mof": ("Global Balance (MOF)", lambda f, t, a: report_global_auxiliary_balance(f, t, "mof")),
        "owner": ("Global Balance (Business Owner)", lambda f, t, a: report_global_auxiliary_balance(f, t, "owner")),
        "qa": ("Global Balance (Quality Assurance)", lambda f, t, a: report_global_auxiliary_balance(f, t, "qa")),
    }

    DESCRIPTIONS = {
        "stmt": "Formal Statement of Account for a specific auxiliary, including opening balance and running totals.",
        "sale_vat": "Detailed listing of sales invoices with Base HT and VAT breakdown for the selected auxiliary.",
        "ret_sale_vat": "Listing of sales returns with Base HT and VAT breakdown for the selected auxiliary.",
        "pur_vat": "Detailed listing of purchase invoices with Base HT and VAT breakdown for the selected auxiliary.",
        "ret_pur_vat": "Listing of purchase returns with Base HT and VAT breakdown for the selected auxiliary.",
        "vat_summary_center": "Aggregated VAT summary center: Sales / Sales Returns / Sales-Return, Purchase / Purchase Return / Purchase-Return, then Sales - Purchase totals (Non-taxable base, Taxable base, Total base, VAT).",
        "auditor": "Auditor view: global auxiliary balance scoped by configured auditor auxiliary prefixes.",
        "mof": "Ministry of Finance view: global auxiliary balance scoped by configured MOF auxiliary prefixes.",
        "owner": "Business owner view: global auxiliary balance scoped by configured owner auxiliary prefixes.",
        "qa": "Quality Assurance view: global auxiliary balance scoped by configured QA auxiliary prefixes.",
    }

    btns = {}
    refs = {}
    default_key = "stmt"
    state = {"report_key": default_key, "from_date": first_of_month, "to_date": today, "aux": selected_aux or ""}

    def select(key):
        state["report_key"] = key
        for k, b in btns.items():
            sty = (
                "background:rgba(138,43,226,0.25);border:1px solid rgba(138,43,226,0.5);"
                if k == key
                else "background:rgba(255,255,255,0.04);border:none;"
            )
            b.style(sty)
        if "n" in refs:
            refs["n"].text = REPORTS[key][0]
        if "d" in refs:
            refs["d"].text = DESCRIPTIONS.get(key, "")

    with ui.dialog() as dlg:
        dlg.props("maximized persistent")
        with ui.card().classes("w-full h-full m-0 rounded-none p-0").style("background:#0d1525; border-radius:0;"):
            with ui.row().classes("w-full items-center justify-between px-6 py-3").style(
                "background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.08);"
            ):
                with ui.row().classes("items-center gap-3"):
                    ui.icon("account_tree", size="1.5rem").classes("text-purple-400")
                    ui.label("Auxiliary Report Center").classes("text-white font-black text-xl").style(
                        'font-family:"Outfit",sans-serif;'
                    )
                ui.button("X  Close", on_click=dlg.close).classes("bg-red-600/80 text-white px-4 py-1 rounded-lg text-sm font-bold")

            with ui.row().classes("w-full gap-0 overflow-hidden").style("height:calc(100vh - 56px);"):
                with ui.column().classes("h-full p-4 gap-2 overflow-y-auto").style(
                    "width:250px; min-width:250px;background:rgba(255,255,255,0.03);border-right:1px solid rgba(255,255,255,0.08);"
                ):
                    ui.label("SELECT REPORT").classes("text-[10px] font-black text-purple-400 uppercase tracking-widest mb-2")
                    for k, (lbl, _fn) in REPORTS.items():
                        b = (
                            ui.button(lbl, on_click=lambda k=k: select(k))
                            .classes("w-full px-4 py-3 rounded-xl text-sm font-bold text-white")
                            .style("background:rgba(255,255,255,0.04); text-align:left; justify-content:flex-start;")
                        )
                        btns[k] = b

                with ui.column().classes("flex-1 h-full p-6 gap-5 overflow-auto"):
                    refs["n"] = ui.label(REPORTS[state["report_key"]][0]).classes("text-white font-black text-2xl").style(
                        'font-family:"Outfit",sans-serif;'
                    )

                    with ui.row().classes("items-end gap-6 glass p-5 rounded-2xl border border-white/10 w-full flex-wrap"):
                        with ui.column().classes("gap-1"):
                            ui.label("FROM").classes("text-[9px] font-black text-purple-400 uppercase tracking-widest")
                            ui.input(value=first_of_month).props(
                                "type=date outlined dense dark color=purple stack-label"
                            ).classes("text-white font-bold w-44").on_value_change(
                                lambda e: state.update({"from_date": e.value})
                            )
                        with ui.column().classes("gap-1"):
                            ui.label("TO").classes("text-[9px] font-black text-purple-400 uppercase tracking-widest")
                            ui.input(value=today).props(
                                "type=date outlined dense dark color=purple stack-label"
                            ).classes("text-white font-bold w-44").on_value_change(
                                lambda e: state.update({"to_date": e.value})
                            )
                        
                        with ui.column().classes("gap-1"):
                            ui.label("AUXILIARY #").classes("text-[9px] font-black text-purple-400 uppercase tracking-widest")
                            ui.input(value=state["aux"]).props(
                                "outlined dense dark color=purple"
                            ).classes("text-white font-bold w-44").on_value_change(
                                lambda e: state.update({"aux": e.value})
                            )

                        def _run():
                            k = state["report_key"]
                            f = state["from_date"]
                            t = state["to_date"]
                            a = state["aux"]
                            if not f or not t:
                                ui.notify("Select dates.", color="warning")
                                return
                            if f > t:
                                ui.notify("From before To.", color="negative")
                                return
                            try:
                                REPORTS[k][1](f, t, a)
                            except Exception as ex:
                                ui.notify(f"Error: {ex}", color="negative")
                                import traceback

                                traceback.print_exc()

                        ui.button("View Report", icon="visibility", on_click=_run).props("unelevated color=purple").classes(
                            "px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest"
                        )

                    with ui.column().classes("w-full glass p-5 rounded-2xl border border-white/10 gap-2"):
                        ui.label("DESCRIPTION").classes("text-[9px] font-black text-purple-400 uppercase tracking-widest")
                        refs["d"] = ui.label(DESCRIPTIONS.get(state["report_key"], "")).classes(
                            "text-sm text-gray-300 font-medium leading-relaxed"
                        )

            select(state["report_key"])
        dlg.open()
