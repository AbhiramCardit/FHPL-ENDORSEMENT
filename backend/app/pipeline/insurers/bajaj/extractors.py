"""
Bajaj ER08 Deletion Endorsement sheet extractor.

Sheet structure:
  - Row 1  : Column headers (no merged cells, no pre-header metadata)
  - Rows 2+ : Data rows (members to be deleted)
  - Last row: SUM formula row (skipped automatically)

Usage
-----
    from app.pipeline.insurers.bajaj.extractors import extract_xls
    result = extract_xls("path/to/file.xlsx")

    result keys
    -----------
    "records"       : list[dict]  – one dict per member row
    "summary"       : dict – totals computed from numeric columns
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════
#  Sheet Adapters — uniform interface over xlrd / openpyxl
# ═══════════════════════════════════════════════════════════

class XlrdSheetAdapter:
    """Adapter for xlrd sheets (0-based indexing)."""

    def __init__(self, sheet) -> None:
        self._s = sheet
        self.nrows = sheet.nrows
        self.ncols = sheet.ncols

    def raw_value(self, r: int, c: int) -> Any:
        value = self._s.cell_value(r, c)
        return value if value != "" else None

    def merged_ranges(self):
        for rlo, rhi, clo, chi in self._s.merged_cells:
            yield rlo, rhi, clo, chi


class OpenpyxlSheetAdapter:
    """Adapter for openpyxl worksheets (converts 1-based to 0-based)."""

    def __init__(self, ws) -> None:
        self._ws = ws
        self.nrows = ws.max_row
        self.ncols = ws.max_column

    def raw_value(self, r: int, c: int) -> Any:
        # openpyxl is 1-based; adapter uses 0-based
        value = self._ws.cell(r + 1, c + 1).value
        return value if value is not None else None

    def merged_ranges(self):
        for merged_range in self._ws.merged_cells.ranges:
            yield (
                merged_range.min_row - 1,
                merged_range.max_row,
                merged_range.min_col - 1,
                merged_range.max_col,
            )


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════

def _load_sheet(path: str):
    """Load the first sheet from an XLS or XLSX file."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".xls":
        try:
            import xlrd
        except ImportError as exc:
            raise ImportError(
                "xlrd is required for .xls files: pip install xlrd==1.2.0"
            ) from exc
        wb = xlrd.open_workbook(path)
        return XlrdSheetAdapter(wb.sheet_by_index(0))
    if ext == ".xlsx":
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise ImportError(
                "openpyxl is required for .xlsx files: pip install openpyxl"
            ) from exc
        wb = load_workbook(path, data_only=True)
        return OpenpyxlSheetAdapter(wb.active)
    raise ValueError(f"Unsupported file extension: {ext}")


def _build_merged_lookup(sheet) -> dict:
    lookup: dict[tuple, Any] = {}
    for rlo, rhi, clo, chi in sheet.merged_ranges():
        top_left = sheet.raw_value(rlo, clo)
        for row in range(rlo, rhi):
            for col in range(clo, chi):
                lookup[(row, col)] = top_left
    return lookup


def _cell(sheet, row: int, col: int, merged: dict) -> Any:
    v = sheet.raw_value(row, col)
    return v if v is not None else merged.get((row, col))


def _clean(value: Any) -> Any:
    """Normalise a raw cell value: strip strings, convert datetime objects."""
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    return value


def _is_formula(value: Any) -> bool:
    """True when a cell still contains an unresolved formula string."""
    return isinstance(value, str) and value.startswith("=")


def _is_summary_row(row_dict: dict) -> bool:
    """Detect rows that are purely formula / SUM rows (no real member data)."""
    sno = row_dict.get("S.No")
    name = row_dict.get("Name of Member")
    return (sno is None or _is_formula(str(sno))) and (
        name is None or _is_formula(str(name or ""))
    )


# ═══════════════════════════════════════════════════════════
#  Core Extraction Logic
# ═══════════════════════════════════════════════════════════

def _extract_headers(sheet, merged: dict, header_row: int = 0) -> dict[int, str]:
    """Return {col_index: header_name} from the header row."""
    headers: dict[int, str] = {}
    for col in range(sheet.ncols):
        v = _cell(sheet, header_row, col, merged)
        if v is not None:
            label = str(v).strip()
            if label:
                headers[col] = label
    return headers


def _extract_records(
    sheet, merged: dict, headers: dict[int, str], data_start_row: int
) -> list[dict]:
    """Extract data rows into a list of dicts keyed by header name."""
    ordered = sorted(headers.keys())
    records: list[dict] = []

    for row in range(data_start_row, sheet.nrows):
        row_dict: dict[str, Any] = {}
        for col in ordered:
            raw = _cell(sheet, row, col, merged)
            row_dict[headers[col]] = _clean(raw)

        # Skip blank rows and formula-only rows (e.g. the SUM footer row)
        if all(v is None for v in row_dict.values()):
            continue
        if _is_summary_row(row_dict):
            continue

        records.append(row_dict)

    return records


SUMMARY_COLS = [
    "Prorata Premium Excl Service Tax (Del)",
    "Gst",
    "Prorata Premium Incl Service Tax (Del)",
]


def _compute_summary(records: list[dict]) -> dict:
    """Sum only the three prorata columns shown in the yellow footer row."""
    totals: dict[str, float] = {col: 0.0 for col in SUMMARY_COLS}
    for rec in records:
        for col in SUMMARY_COLS:
            value = rec.get(col)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                totals[col] += value
    return {k: round(v, 2) for k, v in totals.items()}


# ═══════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════

def extract_xls(path: str) -> dict:
    """
    Extract data from a Bajaj ER08 deletion endorsement sheet.

    Parameters
    ----------
    path : str
        Absolute or relative path to the .xlsx / .xls file.

    Returns
    -------
    dict with keys:
        "records"  – list of member dicts
        "summary"  – dict of column totals for numeric columns
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    logger.info("Bajaj XLS extraction starting", path=path)

    sheet = _load_sheet(path)
    merged = _build_merged_lookup(sheet)

    # Row 0 is the header row for this sheet type
    HEADER_ROW = 0
    DATA_START_ROW = 1

    headers = _extract_headers(sheet, merged, HEADER_ROW)
    records = _extract_records(sheet, merged, headers, DATA_START_ROW)
    summary = _compute_summary(records)

    logger.info(
        "Bajaj XLS extraction complete",
        records=len(records),
        summary_fields=len(summary),
    )

    return {
        "records": records,
        "summary": summary,
    }
