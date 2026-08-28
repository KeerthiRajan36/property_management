import io
from typing import List, Sequence

from openpyxl import Workbook


def build_excel_report(title: str, headers: Sequence[str], rows: List[Sequence]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31] if title else "Report"

    ws.append(list(headers))
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)

    for row in rows:
        ws.append(list(row))

    for col_cells in ws.columns:
        max_len = max((len(str(c.value)) for c in col_cells if c.value is not None), default=10)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 40)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.read()
