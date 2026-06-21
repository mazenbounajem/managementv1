"""
report_designer_ui.py

The Report Designer page.  Lets the user pick a curated data source,
choose columns, add filters / sorts, preview the result on screen,
save the definition, and export to PDF / XLSX / CSV.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from nicegui import ui

from connection import connection
from modern_design_system import ModernDesignSystem as MDS
from navigation_improvements import EnhancedNavigation
from report_designer_exporters import (
    FORMAT_CHOICES,
    export_csv,
    export_pdf,
    export_xlsx,
    resolve_format,
)
from report_designer_service import (
    CURATED_TABLES,
    QueryBuildError,
    ReportDefinitionError,
    build_query,
    delete_report,
    ensure_table,
    get_columns,
    get_curated_tables,
    list_saved_reports,
    run_query,
    save_report,
)
from session_storage import session_storage


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def report_designer_content(standalone: bool = True) -> None:
    """Render the Report Designer inside ModernPageLayout."""
    ensure_table()

    user = session_storage.get("user")
    if not user:
        ui.notify("Please login to access the Report Designer", color="red")
        ui.run_javascript('window.location.href = "/login"')
        return

    if not connection.check_page_permission(user["role_id"], "reports"):
        ui.notify("You do not have permission to access reports", color="red")
        ui.run_javascript('window.location.href = "/dashboard"')
        return

    if standalone:
        permissions = connection.get_user_permissions(user["role_id"])
        navigation = EnhancedNavigation(permissions, user)
        navigation.create_navigation_header()
        navigation.create_navigation_drawer()

        ui.add_head_html(MDS.get_global_styles())
        ui.add_head_html(f'<script>{MDS.get_theme_switcher_js()}</script>')

        with ui.column().classes(
            "w-full p-6 overflow-y-auto"
        ).style("background: var(--bg-main); min-height: 100vh;"):
            ui.label("Report Designer").classes(
                "text-3xl font-black mb-1"
            ).style("font-family: 'Outfit', sans-serif; color: #538392;")
            ui.label(
                "Build a report without writing SQL. "
                "Pick a data source, choose columns, add filters, then preview and export."
            ).classes("text-sm text-gray-500 mb-6")

            ReportDesignerUI()
    else:
        ReportDesignerUI()


@ui.page("/report-designer")
def report_designer_page():
    report_designer_content(standalone=True)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
class ReportDesignerUI:
    """The actual designer.  Keeps all state on `self` and rebuilds small
    sections rather than fighting NiceGUI's reactive model."""

    def __init__(self) -> None:
        self.definition: Dict[str, Any] = {
            "table": "",
            "columns": [],          # [{"name": "...", "alias": "...", "format": "auto"}]
            "filters": [],          # [{"column": "...", "op": "...", "value": ...}]
            "sort": [],             # [{"column": "...", "direction": "ASC"}]
            "group_by": [],
            "row_limit": 1000,
            "options": {"show_totals": True, "orientation": "portrait"},
        }
        self.current_columns: List[Dict[str, str]] = []
        self.last_headers: List[str] = []
        self.last_rows: List[List[Any]] = []
        self.last_error: str = ""
        self.last_meta: List[Dict[str, Any]] = []  # parallel to last_headers
        self.saved_reports: List[Dict[str, Any]] = []

        # Build the skeleton once.  Smaller pieces get rebuilt on demand.
        self._build_skeleton()
        self._refresh_saved_reports_list()

    # ------------------------------------------------------------------
    # Skeleton layout
    # ------------------------------------------------------------------
    def _build_skeleton(self) -> None:
        with ui.row().classes("w-full gap-6 items-start"):

            # ---------------- LEFT: definition builder ----------------
            with ui.column().classes("flex-1 min-w-0 gap-4"):

                # 1. Data source + name
                self._build_meta_card()

                # 2. Columns
                self._build_columns_card()

                # 3. Filters
                self._build_filters_card()

                # 4. Sort, limit, options
                self._build_options_card()

                # 5. Actions (Preview, Save, Clear, Run saved)
                self._build_actions_card()

            # ---------------- RIGHT: preview + saved reports ----------
            with ui.column().classes("w-[44rem] max-w-full gap-4"):

                self._build_saved_reports_card()
                self._build_preview_card()

    # ------------------------------------------------------------------
    # Cards
    # ------------------------------------------------------------------
    def _build_meta_card(self) -> None:
        with ui.card().classes("w-full p-5 glass border border-white/40"):
            with ui.row().classes("w-full items-center gap-2 mb-3"):
                ui.icon("database", size="sm").classes("text-[#80B9AD]")
                ui.label("Report Info").classes("text-base font-black text-[#538392]")

            with ui.grid(columns=2).classes("w-full gap-3"):
                self.name_input = ui.input(
                    "Report name",
                    placeholder="e.g. Sales by customer this month",
                ).props("outlined dense").classes("w-full")

                self.desc_input = ui.input(
                    "Description (optional)",
                    placeholder="What is this report for?",
                ).props("outlined dense").classes("w-full")

            # Data source dropdown
            with ui.row().classes("w-full items-end gap-3 mt-3"):
                self.source_select = ui.select(
                    options={t["key"]: t["label"] for t in get_curated_tables()},
                    label="Data source",
                    with_input=True,
                ).props("outlined dense").classes("flex-1")
                self.source_select.on("update:model-value", self._on_source_change)

                ui.button("Refresh columns", icon="refresh",
                          on_click=lambda: self._on_source_change(
                              self.source_select.value, refresh=True
                          )).props("flat dense").classes(
                    "text-xs text-[#80B9AD] font-bold"
                )

            # Friendly description of the chosen table
            self.source_caption = ui.label("") \
                .classes("text-xs text-gray-500 mt-2")

    def _build_columns_card(self) -> None:
        with ui.card().classes("w-full p-5 glass border border-white/40"):
            with ui.row().classes("w-full items-center justify-between mb-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("view_column", size="sm").classes("text-[#80B9AD]")
                    ui.label("Columns").classes("text-base font-black text-[#538392]")
                ui.label("Pick what to show and how to format it") \
                    .classes("text-xs text-gray-500")

            # Column picker
            with ui.row().classes("w-full items-end gap-3"):
                self.column_select = ui.select(
                    options={},
                    label="Add column",
                    with_input=True,
                ).props("outlined dense clearable").classes("flex-1")
                self.column_select.on("update:model-value", self._on_add_column)

            # Added columns list (rebuilt on change)
            self.columns_container = ui.column().classes("w-full gap-2 mt-3")
            self._refresh_columns_list()

    def _build_filters_card(self) -> None:
        with ui.card().classes("w-full p-5 glass border border-white/40"):
            with ui.row().classes("w-full items-center justify-between mb-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("filter_alt", size="sm").classes("text-[#80B9AD]")
                    ui.label("Filters").classes("text-base font-black text-[#538392]")
                ui.label("Narrow the data before showing it") \
                    .classes("text-xs text-gray-500")

            self.filters_container = ui.column().classes("w-full gap-2 mt-1")
            self._refresh_filters_list()

            with ui.row().classes("w-full mt-3 items-end gap-3"):
                self.filter_column = ui.select(
                    options={}, label="Column", with_input=True,
                ).props("outlined dense clearable").classes("flex-1")

                self.filter_op = ui.select(
                    options={
                        "eq": "equals",
                        "neq": "not equals",
                        "gt": "greater than",
                        "gte": "greater or equal",
                        "lt": "less than",
                        "lte": "less or equal",
                        "contains": "contains",
                        "startswith": "starts with",
                        "endswith": "ends with",
                        "between": "between",
                        "in": "in (comma list)",
                        "isnull": "is empty",
                        "isnotnull": "is not empty",
                        "isempty": "is empty text",
                        "isnotempty": "is not empty text",
                    },
                    label="Operator",
                    value="eq",
                ).props("outlined dense").classes("w-48")

                self.filter_value = ui.input(
                    "Value (use YYYY-MM-DD for dates, A,B,C for 'in')",
                ).props("outlined dense").classes("flex-1")

                self.filter_add_btn = ui.button(
                    "Add filter", icon="add", on_click=self._on_add_filter
                ).props("unelevated color=#80B9AD dense").classes(
                    "text-xs font-bold px-4"
                )

    def _build_options_card(self) -> None:
        with ui.card().classes("w-full p-5 glass border border-white/40"):
            with ui.row().classes("w-full items-center gap-2 mb-2"):
                ui.icon("tune", size="sm").classes("text-[#80B9AD]")
                ui.label("Sort & Limits").classes(
                    "text-base font-black text-[#538392]"
                )

            with ui.row().classes("w-full items-end gap-3"):
                self.sort_column = ui.select(
                    options={}, label="Sort column", with_input=True,
                ).props("outlined dense clearable").classes("flex-1")

                self.sort_direction = ui.select(
                    options={"ASC": "Ascending", "DESC": "Descending"},
                    label="Direction", value="ASC",
                ).props("outlined dense").classes("w-40")

                ui.button("Add sort", icon="swap_vert", on_click=self._on_add_sort) \
                    .props("unelevated color=#80B9AD dense").classes(
                        "text-xs font-bold px-4"
                    )

            self.sort_container = ui.column().classes("w-full gap-2 mt-3")
            self._refresh_sort_list()

            with ui.row().classes("w-full items-end gap-3 mt-3"):
                self.row_limit = ui.number(
                    "Row limit (max 10,000)", value=1000, min=1, max=10000, step=100
                ).props("outlined dense").classes("w-48")

                self.show_totals = ui.switch(
                    "Show totals row in PDF export", value=True
                ).classes("text-sm text-gray-700")

    def _build_actions_card(self) -> None:
        with ui.card().classes("w-full p-4 glass border border-white/40"):
            with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                ui.button(
                    "Preview", icon="play_arrow", on_click=self._on_preview
                ).props("unelevated color=#80B9AD").classes(
                    "px-5 py-2 rounded-xl font-black text-sm shadow-lg "
                    "shadow-green-500/20"
                )
                ui.button(
                    "Save report", icon="save", on_click=self._on_save
                ).props("unelevated color=#538392").classes(
                    "px-5 py-2 rounded-xl font-black text-sm text-white"
                )
                ui.button(
                    "Reset", icon="refresh", on_click=self._on_reset
                ).props("flat").classes(
                    "px-4 py-2 rounded-xl text-sm text-gray-600"
                )

    def _build_saved_reports_card(self) -> None:
        with ui.card().classes("w-full p-4 glass border border-white/40"):
            with ui.row().classes("w-full items-center justify-between mb-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("bookmark", size="sm").classes("text-[#80B9AD]")
                    ui.label("My saved reports").classes(
                        "text-base font-black text-[#538392]"
                    )
                ui.button(icon="refresh", on_click=self._refresh_saved_reports_list) \
                    .props("flat dense round").classes("text-gray-500")

            self.saved_reports_container = ui.column().classes("w-full gap-2")
            self._render_saved_reports()

    def _build_preview_card(self) -> None:
        with ui.card().classes("w-full p-4 glass border border-white/40"):
            with ui.row().classes("w-full items-center justify-between mb-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("preview", size="sm").classes("text-[#80B9AD]")
                    ui.label("Preview").classes(
                        "text-base font-black text-[#538392]"
                    )
                self.preview_summary = ui.label("") \
                    .classes("text-xs text-gray-500")

            with ui.row().classes("w-full gap-2 mb-2 flex-wrap"):
                self.pdf_btn = ui.button(
                    "Export PDF", icon="picture_as_pdf", on_click=self._on_export_pdf
                ).props("unelevated color=#538392").classes(
                    "text-xs font-bold px-4 text-white"
                )
                self.xlsx_btn = ui.button(
                    "Export Excel", icon="table_chart", on_click=self._on_export_xlsx
                ).props("unelevated color=positive").classes(
                    "text-xs font-bold px-4"
                )
                self.csv_btn = ui.button(
                    "Export CSV", icon="description", on_click=self._on_export_csv
                ).props("unelevated color=#1976D2").classes(
                    "text-xs font-bold px-4 text-white"
                )
                for btn in (self.pdf_btn, self.xlsx_btn, self.csv_btn):
                    btn.disable()

            self.preview_table = ui.table(
                columns=[], rows=[], row_key="__idx"
            ).classes("w-full").props("dense flat bordered")

    # ------------------------------------------------------------------
    # Reactive refresh helpers
    # ------------------------------------------------------------------
    def _refresh_columns_list(self) -> None:
        self.columns_container.clear()
        with self.columns_container:
            if not self.definition["columns"]:
                ui.label("No columns yet. Add some from the dropdown above.") \
                    .classes("text-xs text-gray-500 italic")
                return

            for idx, col in enumerate(self.definition["columns"]):
                with ui.card().classes("w-full p-3 bg-white/70 border border-gray-200"):
                    with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                        ui.icon("drag_indicator").classes("text-gray-400")
                        ui.label(col.get("name", "")).classes(
                            "font-mono text-sm font-bold text-[#538392]"
                        )

                        alias_in = ui.input(
                            value=col.get("alias", ""),
                            placeholder="Display label (optional)",
                        ).props("outlined dense").classes("w-56")
                        alias_in.on(
                            "update:model-value",
                            lambda e, i=idx: self._on_update_column_alias(i, e),
                        )

                        fmt_sel = ui.select(
                            options={c["value"]: c["label"] for c in FORMAT_CHOICES},
                            value=col.get("format", "auto"),
                            label="Format",
                        ).props("outlined dense").classes("w-36")
                        fmt_sel.on(
                            "update:model-value",
                            lambda e, i=idx: self._on_update_column_format(i, e),
                        )

                        ui.space()

                        ui.button(
                            icon="arrow_upward",
                            on_click=lambda i=idx: self._on_move_column(i, -1),
                        ).props("flat dense round").classes(
                            "text-gray-500"
                        ).tooltip("Move up")
                        ui.button(
                            icon="arrow_downward",
                            on_click=lambda i=idx: self._on_move_column(i, +1),
                        ).props("flat dense round").classes(
                            "text-gray-500"
                        ).tooltip("Move down")
                        ui.button(
                            icon="delete",
                            on_click=lambda i=idx: self._on_remove_column(i),
                        ).props("flat dense round").classes(
                            "text-red-500"
                        ).tooltip("Remove column")

    def _refresh_filters_list(self) -> None:
        self.filters_container.clear()
        with self.filters_container:
            if not self.definition["filters"]:
                ui.label("No filters. Showing every row in the source table.") \
                    .classes("text-xs text-gray-500 italic")
                return

            for idx, f in enumerate(self.definition["filters"]):
                with ui.card().classes("w-full p-2 bg-white/70 border border-gray-200"):
                    with ui.row().classes("w-full items-center gap-2"):
                        ui.label(f.get("column", "")).classes(
                            "font-mono text-sm font-bold text-[#538392]"
                        )
                        ui.label(f.get("op", "")).classes(
                            "text-xs font-bold text-[#80B9AD]"
                        )
                        ui.label(_stringify_value(f.get("value"))).classes(
                            "text-xs text-gray-700 flex-1"
                        )
                        ui.button(
                            icon="close",
                            on_click=lambda i=idx: self._on_remove_filter(i),
                        ).props("flat dense round").classes("text-red-500")

    def _refresh_sort_list(self) -> None:
        self.sort_container.clear()
        with self.sort_container:
            if not self.definition["sort"]:
                ui.label("No sort. Rows show in database order.") \
                    .classes("text-xs text-gray-500 italic")
                return

            for idx, s in enumerate(self.definition["sort"]):
                with ui.row().classes("w-full items-center gap-2 bg-white/70 p-2 rounded-lg border border-gray-200"):
                    ui.label(s.get("column", "")).classes(
                        "font-mono text-sm font-bold text-[#538392]"
                    )
                    ui.label(s.get("direction", "ASC")).classes(
                        "text-xs font-bold text-[#80B9AD]"
                    )
                    ui.space()
                    ui.button(
                        icon="close",
                        on_click=lambda i=idx: self._on_remove_sort(i),
                    ).props("flat dense round").classes("text-red-500")

    def _render_saved_reports(self) -> None:
        self.saved_reports_container.clear()
        with self.saved_reports_container:
            if not self.saved_reports:
                ui.label("Nothing saved yet. Build a report and click Save.") \
                    .classes("text-xs text-gray-500 italic")
                return

            for r in self.saved_reports:
                with ui.card().classes(
                    "w-full p-3 bg-white/80 border border-gray-200"
                ):
                    with ui.row().classes("w-full items-center gap-2"):
                        ui.icon("description", color="#80B9AD").classes("text-lg")
                        with ui.column().classes("flex-1 min-w-0"):
                            ui.label(r["name"]).classes(
                                "font-bold text-sm text-[#538392] truncate"
                            )
                            tbl = next(
                                (t["label"] for t in CURATED_TABLES
                                 if t["table"] == r["base_table"]),
                                r["base_table"],
                            )
                            line = f"{tbl}  ·  {len(r['definition'].get('columns', []))} columns"
                            if r.get("description"):
                                line = f"{r['description']}  ·  {line}"
                            ui.label(line).classes(
                                "text-xs text-gray-500 truncate"
                            )
                        ui.button(
                            "Load", icon="folder_open",
                            on_click=lambda r=r: self._on_load_saved(r),
                        ).props("unelevated color=#80B9AD dense").classes(
                            "text-xs font-bold px-3"
                        )
                        ui.button(
                            icon="delete", on_click=lambda r=r: self._on_delete_saved(r)
                        ).props("flat dense round").classes("text-red-500")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_source_change(self, value, refresh: bool = False) -> None:
        if not value:
            self.definition["table"] = ""
            self.current_columns = []
            self.source_caption.text = ""
            self._refresh_column_options()
            return

        entry = next((t for t in CURATED_TABLES if t["key"] == value), None)
        if not entry:
            return
        self.definition["table"] = entry["table"]
        self.source_caption.text = entry.get("description", "")

        # Reset columns + filters + sort when source changes
        self.definition["columns"] = []
        self.definition["filters"] = []
        self.definition["sort"] = []

        try:
            self.current_columns = get_columns(entry["table"], refresh=refresh)
        except Exception as ex:
            self.current_columns = []
            ui.notify(f"Could not read columns: {ex}", color="red")

        self._refresh_column_options()
        self._refresh_columns_list()
        self._refresh_filters_list()
        self._refresh_sort_list()

    def _refresh_column_options(self) -> None:
        opts = {c["name"]: f"{c['name']}  ({c['type']})" for c in self.current_columns}
        # Preserve selected values still in the option list
        if self.column_select.value not in opts and self.column_select.value is not None:
            self.column_select.value = None
        if self.filter_column.value not in opts and self.filter_column.value is not None:
            self.filter_column.value = None
        if self.sort_column.value not in opts and self.sort_column.value is not None:
            self.sort_column.value = None

        self.column_select.options = opts
        self.column_select.update()
        self.filter_column.options = opts
        self.filter_column.update()
        self.sort_column.options = opts
        self.sort_column.update()

    def _on_add_column(self, value) -> None:
        if not value:
            return
        if any(c["name"] == value for c in self.definition["columns"]):
            ui.notify(f"Column '{value}' is already added.", color="warning")
            self.column_select.value = None
            return
        self.definition["columns"].append({"name": value, "alias": "", "format": "auto"})
        self.column_select.value = None
        self._refresh_columns_list()

    def _on_update_column_alias(self, idx: int, event) -> None:
        value = event if isinstance(event, str) else getattr(event, "value", event)
        if 0 <= idx < len(self.definition["columns"]):
            self.definition["columns"][idx]["alias"] = value or ""

    def _on_update_column_format(self, idx: int, event) -> None:
        value = event if isinstance(event, str) else getattr(event, "value", event)
        if 0 <= idx < len(self.definition["columns"]):
            self.definition["columns"][idx]["format"] = value or "auto"

    def _on_move_column(self, idx: int, delta: int) -> None:
        cols = self.definition["columns"]
        new_idx = idx + delta
        if not (0 <= new_idx < len(cols)):
            return
        cols[idx], cols[new_idx] = cols[new_idx], cols[idx]
        self._refresh_columns_list()

    def _on_remove_column(self, idx: int) -> None:
        if 0 <= idx < len(self.definition["columns"]):
            del self.definition["columns"][idx]
            self._refresh_columns_list()

    def _on_add_filter(self) -> None:
        col = self.filter_column.value
        op = self.filter_op.value
        raw = self.filter_value.value
        if not col or not op:
            ui.notify("Pick a column and an operator first.", color="warning")
            return

        value = _parse_filter_value(op, raw)
        if op in ("between", "in") and value is None:
            ui.notify(
                "For 'between' use A-B or A,B (two values); for 'in' use A,B,C.",
                color="warning",
            )
            return

        self.definition["filters"].append(
            {"column": col, "op": op, "value": value}
        )
        self.filter_value.value = ""
        self._refresh_filters_list()

    def _on_remove_filter(self, idx: int) -> None:
        if 0 <= idx < len(self.definition["filters"]):
            del self.definition["filters"][idx]
            self._refresh_filters_list()

    def _on_add_sort(self) -> None:
        col = self.sort_column.value
        direction = self.sort_direction.value or "ASC"
        if not col:
            ui.notify("Pick a column to sort by.", color="warning")
            return
        # Replace existing sort for that column
        self.definition["sort"] = [
            s for s in self.definition["sort"] if s.get("column") != col
        ]
        self.definition["sort"].append({"column": col, "direction": direction})
        self._refresh_sort_list()

    def _on_remove_sort(self, idx: int) -> None:
        if 0 <= idx < len(self.definition["sort"]):
            del self.definition["sort"][idx]
            self._refresh_sort_list()

    def _on_reset(self) -> None:
        self.definition = {
            "table": "",
            "columns": [],
            "filters": [],
            "sort": [],
            "group_by": [],
            "row_limit": 1000,
            "options": {"show_totals": True, "orientation": "portrait"},
        }
        self.source_select.value = None
        self.name_input.value = ""
        self.desc_input.value = ""
        self.row_limit.value = 1000
        self.show_totals.value = True
        self.current_columns = []
        self.last_headers = []
        self.last_rows = []
        self.last_error = ""
        self.last_meta = []
        self._refresh_column_options()
        self._refresh_columns_list()
        self._refresh_filters_list()
        self._refresh_sort_list()
        self._render_preview(headers=[], rows=[])
        self.preview_summary.text = ""

    def _on_preview(self) -> None:
        try:
            self.last_error = ""
            definition = self._current_definition()
            headers, rows = run_query(definition)
            self.last_headers = headers
            self.last_rows = rows
            self.last_meta = [
                {
                    "name": c.get("name", h),
                    "alias": c.get("alias", ""),
                    "format": c.get("format", "auto"),
                }
                for c, h in zip(definition.get("columns", []), headers)
            ]
            self._render_preview(headers, rows)
            self.preview_summary.text = (
                f"{len(rows):,} row{'s' if len(rows) != 1 else ''} from "
                f"{definition['table']}"
            )
            for btn in (self.pdf_btn, self.xlsx_btn, self.csv_btn):
                btn.enable()
        except (QueryBuildError, ReportDefinitionError) as ex:
            ui.notify(str(ex), color="warning")
        except Exception as ex:
            self.last_error = str(ex)
            ui.notify(f"Preview failed: {ex}", color="negative")
            import traceback
            traceback.print_exc()

    def _render_preview(self, headers, rows) -> None:
        if not headers:
            self.preview_table.columns = []
            self.preview_table.rows = []
            self.preview_table.update()
            return

        # Truncate to 500 rows for the on-screen preview
        max_rows = 500
        truncated = len(rows) > max_rows
        shown_rows = rows[:max_rows]

        cols = []
        for i, h in enumerate(headers):
            meta = self.last_meta[i] if i < len(self.last_meta) else {"format": "auto"}
            fmt = resolve_format(meta.get("name", ""), meta.get("format", "auto"))
            col_def = {
                "name": h,
                "label": h,
                "field": h,
                "align": "left",
            }
            if fmt == "money":
                col_def["format"] = lambda v: (
                    f"${float(v):,.2f}" if isinstance(v, (int, float)) else (v or "")
                )
                col_def["align"] = "right"
            elif fmt == "int":
                col_def["format"] = lambda v: (
                    f"{int(float(v)):,}" if isinstance(v, (int, float)) else (v or "")
                )
                col_def["align"] = "right"
            elif fmt == "date":
                col_def["format"] = lambda v: (
                    v.replace("T", " ") if isinstance(v, str) else (v or "")
                )
            cols.append(col_def)

        table_rows = []
        for idx, r in enumerate(shown_rows):
            row = {"__idx": str(idx)}
            for i, h in enumerate(headers):
                row[h] = r[i] if i < len(r) else None
            table_rows.append(row)

        self.preview_table.columns = cols
        self.preview_table.rows = table_rows
        self.preview_table.update()

        if truncated:
            self.preview_summary.text = (
                f"{self.preview_summary.text or ''}  -  showing first {max_rows:,} rows"
            )

    def _on_save(self) -> None:
        try:
            definition = self._current_definition()
            name = (self.name_input.value or "").strip()
            if not name:
                # Auto-name from the table
                name = f"{definition['table']} report"
            description = (self.desc_input.value or "").strip()
            save_report(name, description, definition)
            ui.notify(f"Saved '{name}'", color="positive")
            self._refresh_saved_reports_list()
        except (ReportDefinitionError, QueryBuildError) as ex:
            ui.notify(str(ex), color="warning")
        except Exception as ex:
            ui.notify(f"Save failed: {ex}", color="negative")

    def _refresh_saved_reports_list(self) -> None:
        try:
            self.saved_reports = list_saved_reports()
        except Exception as ex:
            self.saved_reports = []
            ui.notify(f"Could not load saved reports: {ex}", color="warning")
        self._render_saved_reports()

    def _on_load_saved(self, report):
        definition = report.get("definition") or {}
        if not isinstance(definition, dict):
            ui.notify("Saved report is corrupted.", color="negative")
            return
        self.definition = {
            "table": definition.get("table", ""),
            "columns": list(definition.get("columns") or []),
            "filters": list(definition.get("filters") or []),
            "sort": list(definition.get("sort") or []),
            "group_by": list(definition.get("group_by") or []),
            "row_limit": int(definition.get("row_limit") or 1000),
            "options": definition.get("options") or {"show_totals": True, "orientation": "portrait"},
        }
        self.name_input.value = report.get("name", "")
        self.desc_input.value = report.get("description", "")
        entry = next((t for t in CURATED_TABLES if t["table"] == self.definition["table"]), None)
        self.source_select.value = entry["key"] if entry else None
        if entry:
            self.source_caption.text = entry.get("description", "")
            try:
                self.current_columns = get_columns(entry["table"])
            except Exception:
                self.current_columns = []
        else:
            self.current_columns = []
        self._refresh_column_options()
        self._refresh_columns_list()
        self._refresh_filters_list()
        self._refresh_sort_list()
        self.row_limit.value = self.definition.get("row_limit") or 1000
        self.show_totals.value = bool(self.definition.get("options", {}).get("show_totals", True))
        ui.notify(f"Loaded '{report.get('name')}'. Click Preview to run it.", color="info")

    def _on_delete_saved(self, report):
        try:
            delete_report(report["id"])
            ui.notify(f"Deleted '{report.get('name')}'", color="positive")
            self._refresh_saved_reports_list()
        except Exception as ex:
            ui.notify(f"Delete failed: {ex}", color="negative")

    def _on_export_pdf(self):
        if not self.last_headers:
            ui.notify("Run Preview first.", color="warning")
            return
        pdf = export_pdf(
            self.name_input.value or "Custom Report",
            self.last_headers, self.last_rows, self.last_meta,
        )
        fname = (self.name_input.value or "custom_report").replace(" ", "_") + ".pdf"
        ui.download(pdf, fname)
        self._show_pdf_modal(pdf, fname, self.name_input.value or "Custom Report")

    def _on_export_xlsx(self):
        if not self.last_headers:
            ui.notify("Run Preview first.", color="warning")
            return
        xlsx = export_xlsx(
            self.name_input.value or "Custom Report",
            self.last_headers, self.last_rows, self.last_meta,
        )
        fname = (self.name_input.value or "custom_report").replace(" ", "_") + ".xlsx"
        ui.download(xlsx, fname)

    def _on_export_csv(self):
        if not self.last_headers:
            ui.notify("Run Preview first.", color="warning")
            return
        csv_bytes = export_csv(self.last_headers, self.last_rows)
        fname = (self.name_input.value or "custom_report").replace(" ", "_") + ".csv"
        ui.download(csv_bytes, fname)

    def _show_pdf_modal(self, pdf_bytes, filename, title):
        try:
            from pdf_viewer_helper import show_pdf_modal
            show_pdf_modal(pdf_bytes, filename=filename, title=title)
        except Exception:
            pass

    def _current_definition(self):
        defn = dict(self.definition)
        defn["columns"] = [
            {
                "name": c.get("name", ""),
                "alias": (c.get("alias") or "").strip(),
                "format": c.get("format", "auto"),
            }
            for c in self.definition["columns"]
            if c.get("name")
        ]
        defn["row_limit"] = int(self.row_limit.value or 0) if self.row_limit.value else 0
        defn["options"] = {
            "show_totals": bool(self.show_totals.value),
            "orientation": "portrait",
        }
        return defn


# ---------------------------------------------------------------------------
# Value parsing helpers
# ---------------------------------------------------------------------------
def _stringify_value(v):
    if v is None:
        return ""
    if isinstance(v, list):
        return ", ".join(str(x) for x in v)
    return str(v)


def _parse_filter_value(op, raw):
    if op in ("isnull", "isnotnull", "isempty", "isnotempty"):
        return None
    if raw is None or raw == "":
        return None
    text = str(raw).strip()
    if op == "between":
        for sep in (",", "-"):
            if sep in text:
                a, b = text.split(sep, 1)
                return [a.strip(), b.strip()]
        return None
    if op == "in":
        return [p.strip() for p in text.split(",") if p.strip()]
    if op in ("gt", "gte", "lt", "lte", "eq", "neq"):
        try:
            if "." in text:
                return float(text)
            return int(text)
        except ValueError:
            return text
    return text
