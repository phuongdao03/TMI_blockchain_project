"""Bounded XLSX writer for explicitly selected HR report columns."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Literal

import xlsxwriter  # type: ignore[import-untyped]

CellKind = Literal["text", "integer", "decimal", "date", "datetime", "vnd"]
CellValue = str | int | float | Decimal | date | datetime | None

MAX_EXPORT_ROWS = 10_000
MAX_EXPORT_COLUMNS = 40
MAX_CELL_TEXT = 32_767
MAX_EXPORT_TEXT_BYTES = 16_000_000


@dataclass(frozen=True)
class ExportColumn:
    key: str
    header: str
    kind: CellKind = "text"
    width: int = 20


@dataclass(frozen=True)
class ExportSheet:
    name: str
    columns: tuple[ExportColumn, ...]
    rows: Sequence[Mapping[str, CellValue]]


def build_xlsx(sheets: Sequence[ExportSheet]) -> bytes:
    """Create an XLSX with no formulas, links, or unbounded source data."""
    if not sheets or len(sheets) > 12:
        raise ValueError("An export requires 1-12 sheets.")
    if sum(len(sheet.rows) for sheet in sheets) > MAX_EXPORT_ROWS:
        raise ValueError("The report exceeds its row limit.")
    if any(
        not sheet.columns or len(sheet.columns) > MAX_EXPORT_COLUMNS for sheet in sheets
    ):
        raise ValueError("A sheet must have 1-40 columns.")

    output = BytesIO()
    workbook = xlsxwriter.Workbook(
        output,
        {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
        },
    )
    header_style = workbook.add_format(
        {"bold": True, "bg_color": "#E8F0EC", "font_color": "#173A32"}
    )
    date_style = workbook.add_format({"num_format": "yyyy-mm-dd"})
    datetime_style = workbook.add_format({"num_format": 'yyyy-mm-dd hh:mm:ss "UTC"'})
    vnd_style = workbook.add_format({"num_format": '#,##0 "VND"'})
    text_bytes = 0
    for sheet in sheets:
        worksheet = workbook.add_worksheet(sheet.name)
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, max(1, len(sheet.rows)), len(sheet.columns) - 1)
        for column_index, column in enumerate(sheet.columns):
            worksheet.set_column(
                column_index, column_index, min(60, max(10, column.width))
            )
            worksheet.write_string(0, column_index, column.header, header_style)
        for row_index, row in enumerate(sheet.rows, start=1):
            for column_index, column in enumerate(sheet.columns):
                value = row.get(column.key)
                if value is None:
                    continue
                if column.kind == "date":
                    if not isinstance(value, date) or isinstance(value, datetime):
                        raise ValueError("An export date column contains another type.")
                    worksheet.write_datetime(row_index, column_index, value, date_style)
                elif column.kind == "datetime":
                    if not isinstance(value, datetime) or value.tzinfo is None:
                        raise ValueError("Export timestamps must have a timezone.")
                    worksheet.write_datetime(
                        row_index,
                        column_index,
                        value.astimezone(UTC).replace(tzinfo=None),
                        datetime_style,
                    )
                elif column.kind in ("integer", "decimal", "vnd"):
                    if isinstance(value, bool) or not isinstance(
                        value, (int, float, Decimal)
                    ):
                        raise ValueError("A numeric export column contains text.")
                    numeric = Decimal(str(value))
                    if not numeric.is_finite() or abs(numeric) > Decimal(
                        "999999999999999"
                    ):
                        raise ValueError("An export number exceeds Excel precision.")
                    if (
                        column.kind in ("integer", "vnd")
                        and numeric != numeric.to_integral_value()
                    ):
                        raise ValueError(
                            "An integer export column contains a fraction."
                        )
                    worksheet.write_number(
                        row_index,
                        column_index,
                        float(numeric),
                        vnd_style if column.kind == "vnd" else None,
                    )
                else:
                    if not isinstance(value, str):
                        raise ValueError("An export text column contains another type.")
                    text_value = str(value)
                    if len(text_value) > MAX_CELL_TEXT:
                        raise ValueError("An export cell exceeds Excel's text limit.")
                    text_bytes += len(text_value.encode("utf-8"))
                    if text_bytes > MAX_EXPORT_TEXT_BYTES:
                        raise ValueError("The report exceeds its text size limit.")
                    worksheet.write_string(row_index, column_index, text_value)
    workbook.close()
    return output.getvalue()
