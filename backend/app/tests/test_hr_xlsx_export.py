from datetime import UTC, date, datetime
from io import BytesIO
from zipfile import ZipFile

import pytest

from app.modules.hr.xlsx_export import ExportColumn, ExportSheet, build_xlsx


def test_xlsx_writer_keeps_untrusted_text_inert_and_formats_report() -> None:
    workbook = build_xlsx(
        (
            ExportSheet(
                name="Nhan vien",
                columns=(
                    ExportColumn("name", "Họ và tên"),
                    ExportColumn("code", "Mã nhân viên"),
                    ExportColumn("date", "Ngày vào", "date"),
                    ExportColumn("time", "Cập nhật UTC", "datetime"),
                    ExportColumn("salary", "Lương VND", "vnd"),
                ),
                rows=(
                    {
                        "name": '=HYPERLINK("https://example.test", "Mở")',
                        "code": "00123",
                        "date": date(2026, 9, 23),
                        "time": datetime(2026, 9, 23, 8, tzinfo=UTC),
                        "salary": 18_000_000,
                    },
                    {
                        "name": "https://example.test/nhân-sự",
                        "code": "+SUM(1,1)",
                    },
                ),
            ),
        )
    )

    with ZipFile(BytesIO(workbook)) as archive:
        names = archive.namelist()
        assert not any("externalLink" in name for name in names)
        sheet = archive.read("xl/worksheets/sheet1.xml")
        strings = archive.read("xl/sharedStrings.xml").decode("utf-8")
        styles = archive.read("xl/styles.xml").decode("utf-8")
        assert b"<f>" not in sheet and b"<f " not in sheet
        assert b'<autoFilter ref="A1:E3"' in sheet
        assert b'ySplit="1"' in sheet
        assert "Họ và tên" in strings
        assert '=HYPERLINK("https://example.test", "Mở")' in strings
        assert "https://example.test/nhân-sự" in strings
        assert "+SUM(1,1)" in strings
        assert "00123" in strings
        assert "yyyy-mm-dd" in styles
        assert "VND" in styles


def test_xlsx_writer_rejects_oversized_and_naive_datetime_reports() -> None:
    column = (ExportColumn("value", "Value"),)
    with pytest.raises(ValueError, match="row limit"):
        build_xlsx((ExportSheet("Too many", column, ({"value": "x"},) * 10_001),))
    with pytest.raises(ValueError, match="timezone"):
        build_xlsx(
            (
                ExportSheet(
                    "Bad time",
                    (ExportColumn("value", "Time", "datetime"),),
                    ({"value": datetime(2026, 9, 23, 8)},),
                ),
            )
        )
    with pytest.raises(ValueError, match="precision"):
        build_xlsx(
            (
                ExportSheet(
                    "Too much money",
                    (ExportColumn("value", "VND", "vnd"),),
                    ({"value": 1_000_000_000_000_000},),
                ),
            )
        )
