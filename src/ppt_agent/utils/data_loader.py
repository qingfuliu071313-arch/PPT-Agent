"""Load real data from external files for chart/table/metrics slides.

Supports CSV, Excel (.xlsx), and JSON files.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from ppt_agent.models import ChartData


def load_chart_data(file_path: str, **overrides) -> ChartData:
    """Load chart data from a CSV, Excel, or JSON file.

    CSV/Excel format: first column = categories, remaining columns = series.
    First row = header (series names).

    JSON format: direct ChartData-compatible dict.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    ext = path.suffix.lower()
    if ext == ".json":
        return _load_json(path, overrides)
    elif ext == ".csv":
        return _load_csv(path, overrides)
    elif ext in (".xlsx", ".xls"):
        return _load_excel(path, overrides)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Use .csv, .xlsx, or .json")


def load_table_data(file_path: str) -> list[list[str]]:
    """Load table data from CSV or Excel. Returns 2D list (first row = header)."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    ext = path.suffix.lower()
    if ext == ".csv":
        return _read_csv_raw(path)
    elif ext in (".xlsx", ".xls"):
        return _read_excel_raw(path)
    elif ext == ".json":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and all(isinstance(row, list) for row in data):
            return [[str(cell) for cell in row] for row in data]
        raise ValueError("JSON must be a 2D array for table data")
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _load_json(path: Path, overrides: dict) -> ChartData:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data.update(overrides)
    return ChartData(**data)


def _load_csv(path: Path, overrides: dict) -> ChartData:
    rows = _read_csv_raw(path)
    return _rows_to_chart(rows, overrides)


def _load_excel(path: Path, overrides: dict) -> ChartData:
    rows = _read_excel_raw(path)
    return _rows_to_chart(rows, overrides)


def _read_csv_raw(path: Path) -> list[list[str]]:
    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f)
        return [row for row in reader if any(cell.strip() for cell in row)]


def _read_excel_raw(path: Path) -> list[list[str]]:
    try:
        import openpyxl
    except ImportError:
        raise ImportError("openpyxl required for Excel files: pip install openpyxl")

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(cell) if cell is not None else "" for cell in row])
    wb.close()
    return rows


def _rows_to_chart(rows: list[list[str]], overrides: dict) -> ChartData:
    """Convert tabular data to ChartData.

    Expected format:
    Header:     | Series1 | Series2 | ...
    Category1   | val1    | val2    | ...
    Category2   | val1    | val2    | ...
    """
    if len(rows) < 2:
        raise ValueError("Data must have at least a header row and one data row")

    header = rows[0]
    series_names = [h.strip() for h in header[1:] if h.strip()]
    categories = []
    series_data: list[list[float]] = [[] for _ in series_names]

    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        categories.append(row[0].strip())
        for i, name in enumerate(series_names):
            val = 0.0
            if i + 1 < len(row) and row[i + 1].strip():
                try:
                    val = float(row[i + 1].strip().replace(",", "").replace("%", ""))
                except ValueError:
                    val = 0.0
            series_data[i].append(val)

    series = [{"name": name, "values": vals} for name, vals in zip(series_names, series_data)]

    kwargs = {
        "categories": categories,
        "series": series,
        "chart_type": overrides.pop("chart_type", "column"),
        "title": overrides.pop("title", ""),
        "x_axis_title": overrides.pop("x_axis_title", ""),
        "y_axis_title": overrides.pop("y_axis_title", ""),
    }
    kwargs.update(overrides)
    return ChartData(**kwargs)
