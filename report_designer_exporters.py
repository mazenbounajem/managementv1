"""
report_designer_exporters.py

Export helpers for the Report Designer.  They all take a definition plus
already-fetched rows so the UI can preview and export from the same
result set.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from connection import connection


# ---------------------------------------------------------------------------
# Display / formatting helpers
# ---------------------------------------------------------------------------
MONEY_FIELDS_HINT = ("amount", "price", "cost", "total", "subtotal",
                     "balance", "vat", "tax", "debit", "credit",
                     "salary", "discount", "profit", "rate")


def _friendly_header(name: str) -> str:
    out = name.replace("_", " ").strip()
    return out[:1].upper() + out[1:] if out else name


def _looks_like_money(name: str) -> bool:
    n = name.lower()
    return any(token in n for token in MONEY_FIELDS_HINT)


def _coerce_for_format(value: Any, fmt: str) -> Any:
    if value is None or value == "":
        return ""
    if fmt == "money":
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if fmt == "int":
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return value
    if fmt == "date":
        if isinstance(value, (datetime, date)):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("T", " ").split(".")[0])
        except ValueError:
            return value
    return value


def _format_cell_for_pdf(value: Any, fmt: str) -> str:
    if value is None or value == "":
        return ""
    if fmt == "money":
        try:
            return f"${float(value):,.2f}"
        except (TypeError, ValueError):
            return str(value)
    if fmt == "int":
        try:
            return f"{int(float(value)):,}"
        except (TypeError, ValueError):
            return str(value)
    if fmt == "date":
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M")
        if isinstance(value, date):
            return value.strftime("%Y-%m-%d")
        return str(value)
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".")
    return str(value)


def _company_name() -> str:
    try:
        info = connection.get_company_info()
        return info.get("company_name", "Company") if info else "Company"
    except Exception:
        return "Company"


# ---------------------------------------------------------------------------
# Column display choices
# ---------------------------------------------------------------------------
FORMAT_CHOICES = [
    {"value": "auto",  "label": "Auto"},
    {"value": "text",  "label": "Text"},
    {"value": "int",   "label": "Integer"},
    {"value": "money", "label": "Money"},
    {"value": "date",  "label": "Date / Time"},
]


def resolve_format(column_name: str, declared: str) -> str:
    if declared and declared != "auto":
        return declared
    if _looks_like_money(column_name):
        return "money"
    return "text"


# ---------------------------------------------------------------------------
# Common PDF styling (mirrors reports_framework.py so exported designer
# reports look like the rest of the system)
# ---------------------------------------------------------------------------
def _styles():
    s = getSampleStyleSheet()
    title = ParagraphStyle("RDTitle", parent=s["Heading1"], fontSize=16,
                           textColor=colors.HexColor("#538392"), spaceAfter=4)
    sub = ParagraphStyle("RDSub", parent=s["Normal"], fontSize=9,
                         textColor=colors.grey, spaceAfter=8)
    cell = ParagraphStyle("RDCell", parent=s["Normal"], fontSize=7.5,
                          leading=9, textColor=colors.black)
    return s, title, sub, cell


def _build_pdf_bytes(headers: List[str], rows: List[List[Any]],
                     column_meta: List[Dict[str, Any]],
                     title: str, subtitle: str) -> bytes:
    landscape_mode = max((len(h) for h in headers), default=0) > 6 or len(headers) > 8
    page = landscape(A4) if landscape_mode else A4

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=page,
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
    )
    _, title_s, sub_s, cell_s = _styles()
    company = _company_name()

    elements = [
        Paragraph(f"{company} &mdash; {title}", title_s),
        Paragraph(subtitle, sub_s),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#80B9AD")),
        Spacer(1, 4 * mm),
    ]

    fmts = [resolve_format(meta.get("name", ""), meta.get("format", "auto"))
            for meta in column_meta]

    data = [[Paragraph(_friendly_header(h), cell_s) for h in headers]]
    for row in rows:
        data.append([
            Paragraph(_format_cell_for_pdf(_coerce_for_format(c, fmts[i]), fmts[i]), cell_s)
            for i, c in enumerate(row)
        ])

    available_w = page[0] - 24 * mm
    weights = []
    for h in headers:
        w = max(40, min(120, 12 + 7 * len(h)))
        weights.append(w)
    total = sum(weights) or 1
    scale = available_w / total
    col_widths = [max(28, w * scale) for w in weights]

    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND",   (0, 0), (-1, 0),  colors.HexColor("#538392")),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  8),
        ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#B3E2A7")]),
        ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ])

    # Totals row for money / int columns
    totals = []
    for i, fmt in enumerate(fmts):
        if fmt not in ("money", "int"):
            totals.append("")
            continue
        total = 0.0
        saw = False
        for row in rows:
            v = _coerce_for_format(row[i] if i < len(row) else None, fmt)
            if isinstance(v, (int, float)):
                total += float(v)
                saw = True
        if not saw:
            totals.append("")
        elif fmt == "money":
            totals.append(f"${total:,.2f}")
        else:
            totals.append(f"{int(total):,}")

    if any(totals):
        data.append([Paragraph("<b>Totals</b>", cell_s) if i == 0
                     else Paragraph(f"<b>{tot}</b>", cell_s)
                     for i, tot in enumerate(totals)])
        totals_row = len(data) - 1
        style.add("BACKGROUND", (0, totals_row), (-1, totals_row), colors.HexColor("#dcfce7"))
        style.add("TEXTCOLOR",  (0, totals_row), (-1, totals_row), colors.HexColor("#538392"))
        style.add("FONTNAME",   (0, totals_row), (-1, totals_row), "Helvetica-Bold")

    table.setStyle(style)
    elements.append(table)
    doc.build(elements)
    pdf = buf.getvalue()
    buf.close()
    return pdf


# ---------------------------------------------------------------------------
# Public exporters
# ---------------------------------------------------------------------------
def export_pdf(report_name: str, headers: List[str], rows: List[List[Any]],
               column_meta: List[Dict[str, Any]]) -> bytes:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    return _build_pdf_bytes(
        headers, rows, column_meta,
        title=report_name or "Custom Report",
        subtitle=f"Generated {ts}  &middot;  {len(rows):,} rows",
    )


def export_xlsx(report_name: str, headers: List[str], rows: List[List[Any]],
                column_meta: List[Dict[str, Any]]) -> bytes:
    import pandas as pd

    fmts = [resolve_format(meta.get("name", ""), meta.get("format", "auto"))
            for meta in column_meta]

    clean_rows = []
    for row in rows:
        clean_rows.append([_coerce_for_format(c, fmts[i]) if i < len(fmts) else c
                           for i, c in enumerate(row)])

    df = pd.DataFrame(clean_rows, columns=[_friendly_header(h) for h in headers])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        sheet = (report_name or "Custom Report")[:31] or "Custom Report"
        df.to_excel(writer, sheet_name=sheet, index=False)
        try:
            wb = writer.book
            ws = writer.sheets[sheet]
            money_fmt = wb.add_format({"num_format": "$#,##0.00"})
            int_fmt = wb.add_format({"num_format": "#,##0"})
            date_fmt = wb.add_format({"num_format": "yyyy-mm-dd hh:mm"})
            for idx, fmt in enumerate(fmts):
                if fmt == "money":
                    ws.set_column(idx, idx, 18, money_fmt)
                elif fmt == "int":
                    ws.set_column(idx, idx, 14, int_fmt)
                elif fmt == "date":
                    ws.set_column(idx, idx, 20, date_fmt)
                else:
                    ws.set_column(idx, idx, 22)
        except Exception:
            pass
    out = buf.getvalue()
    buf.close()
    return out


def export_csv(headers: List[str], rows: List[List[Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([_friendly_header(h) for h in headers])
    for row in rows:
        out_row = []
        for cell in row:
            if isinstance(cell, (datetime, date)):
                out_row.append(cell.isoformat(sep=" "))
            elif isinstance(cell, Decimal):
                out_row.append(float(cell))
            else:
                out_row.append(cell)
        writer.writerow(out_row)
    return buf.getvalue().encode("utf-8-sig")
