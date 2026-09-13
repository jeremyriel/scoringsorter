"""Writes the assignment sheet as CSV and as a real .xlsx workbook.

**No third-party libraries.** An .xlsx is a zip of XML parts, and the sheets
this tool produces are headers plus integers — so the workbook is written
directly with `zipfile` and a few hand-built XML documents. That keeps the whole
folder copyable to any machine with Python 3 and runnable offline with no pip
install, which is worth far more here than the formatting a spreadsheet library
would buy.

Text cells use inline strings (`t="inlineStr"`), which avoids needing a
sharedStrings part at all. Numbers are written as bare numeric cells so Excel
treats them as numbers, not text — important, because the scorer IDs get
sorted and filtered.
"""

import csv
import zipfile
from xml.sax.saxutils import escape

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""


def _workbook_xml(sheet_name: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(sheet_name)}" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )


def _column_letter(index: int) -> str:
    """1 -> A, 26 -> Z, 27 -> AA."""
    letters = ''
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _cell(ref: str, value) -> str:
    if value is None or value == '':
        return ''
    if isinstance(value, bool):
        value = str(value)
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{escape(str(value))}</t></is></c>'


def _sheet_xml(rows) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
        '<sheetData>',
    ]
    for row_index, row in enumerate(rows, start=1):
        cells = ''.join(
            _cell(f'{_column_letter(col_index)}{row_index}', value)
            for col_index, value in enumerate(row, start=1)
        )
        parts.append(f'<row r="{row_index}">{cells}</row>')
    parts.append('</sheetData></worksheet>')
    return ''.join(parts)


def write_xlsx(path, rows, sheet_name: str = 'Assignments') -> None:
    """Write `rows` (first row treated as the header) as a minimal workbook."""
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as book:
        book.writestr('[Content_Types].xml', CONTENT_TYPES)
        book.writestr('_rels/.rels', ROOT_RELS)
        book.writestr('xl/workbook.xml', _workbook_xml(sheet_name))
        book.writestr('xl/_rels/workbook.xml.rels', WORKBOOK_RELS)
        book.writestr('xl/worksheets/sheet1.xml', _sheet_xml(rows))


def write_csv(path, rows) -> None:
    # utf-8-sig so Excel on Windows opens it as UTF-8 rather than guessing.
    with open(path, 'w', newline='', encoding='utf-8-sig') as handle:
        csv.writer(handle).writerows(rows)
