"""Reads an assignment sheet back in, so a run can be reassigned later.

Accepts either the CSV or the .xlsx this tool wrote — the .xlsx is unzipped and
parsed with the standard library, matching `sheets.py`'s dependency-free stance.

Column names are matched loosely (case and spacing ignored) so a sheet that has
been opened, tidied and re-saved by a person still loads.
"""

import csv
import re
import zipfile
from xml.etree import ElementTree

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

PROJECT_HEADERS = ('projectid', 'project', 'id')
FIRST_HEADERS = ('firstscorer', 'scorer1', 'first')
SECOND_HEADERS = ('secondscorer', 'scorer2', 'second')
FIRST_DONE_HEADERS = ('firstscorerdone', 'firstdone', 'scorer1done')
SECOND_DONE_HEADERS = ('secondscorerdone', 'seconddone', 'scorer2done')

# What counts as "this slot is finished". Anything else — including blank — is
# treated as not done, because the safe reading of an ambiguous mark is that
# the work still needs doing.
DONE_VALUES = {'y', 'yes', 'done', 'true', '1', 'x', 'complete', 'completed'}


class SheetError(Exception):
    pass


def _normalise(name: str) -> str:
    return re.sub(r'[^a-z0-9]', '', str(name or '').lower())


def _find_column(headers, candidates, label):
    normalised = [_normalise(h) for h in headers]
    for candidate in candidates:
        if candidate in normalised:
            return normalised.index(candidate)
    raise SheetError(
        f"Could not find the {label} column. Expected a header like "
        f"'{candidates[0]}'. Found: {', '.join(str(h) for h in headers if h)}"
    )


def _rows_from_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as handle:
        return [row for row in csv.reader(handle) if any(str(c).strip() for c in row)]


def _rows_from_xlsx(path):
    with zipfile.ZipFile(path) as book:
        shared = []
        if 'xl/sharedStrings.xml' in book.namelist():
            tree = ElementTree.fromstring(book.read('xl/sharedStrings.xml'))
            for item in tree.findall(f'{NS}si'):
                shared.append(''.join(t.text or '' for t in item.iter(f'{NS}t')))

        sheet_names = [n for n in book.namelist() if n.startswith('xl/worksheets/sheet')]
        if not sheet_names:
            raise SheetError(f'{path} contains no worksheet.')
        tree = ElementTree.fromstring(book.read(sorted(sheet_names)[0]))

    rows = []
    for row in tree.iter(f'{NS}row'):
        values = {}
        for cell in row.findall(f'{NS}c'):
            column = re.match(r'[A-Z]+', cell.get('r') or 'A').group()
            index = 0
            for char in column:
                index = index * 26 + (ord(char) - 64)
            kind = cell.get('t')
            if kind == 'inlineStr':
                text = ''.join(t.text or '' for t in cell.iter(f'{NS}t'))
            elif kind == 's':
                value = cell.find(f'{NS}v')
                text = shared[int(value.text)] if value is not None and value.text else ''
            else:
                value = cell.find(f'{NS}v')
                text = value.text if value is not None else ''
            values[index - 1] = text or ''
        if values:
            width = max(values) + 1
            rows.append([values.get(i, '') for i in range(width)])
    return [r for r in rows if any(str(c).strip() for c in r)]


def read_sheet(path):
    """Return (assignments, scorers, project_ids, completed).

    `assignments` is [[first, second], ...] in sheet order, `completed` is the
    set of (row_index, slot) already marked done.
    """
    path = str(path)
    rows = _rows_from_xlsx(path) if path.lower().endswith('.xlsx') else _rows_from_csv(path)
    if len(rows) < 2:
        raise SheetError(f'{path} has no data rows.')

    headers = rows[0]
    col_project = _find_column(headers, PROJECT_HEADERS, 'Project ID')
    col_first = _find_column(headers, FIRST_HEADERS, 'First Scorer')
    col_second = _find_column(headers, SECOND_HEADERS, 'Second Scorer')

    normalised = [_normalise(h) for h in headers]
    col_first_done = next((normalised.index(c) for c in FIRST_DONE_HEADERS if c in normalised), None)
    col_second_done = next((normalised.index(c) for c in SECOND_DONE_HEADERS if c in normalised), None)

    assignments, project_ids, completed = [], [], set()
    for line_number, row in enumerate(rows[1:], start=2):
        def cell(index):
            return row[index].strip() if index is not None and index < len(row) else ''

        raw_first, raw_second = cell(col_first), cell(col_second)
        if not raw_first and not raw_second:
            continue
        try:
            first, second = int(float(raw_first)), int(float(raw_second))
        except ValueError:
            raise SheetError(
                f'Line {line_number}: scorer IDs must be whole numbers, '
                f'found "{raw_first}" and "{raw_second}".'
            )
        if first == second:
            raise SheetError(
                f'Line {line_number}: the same scorer ({first}) is listed twice '
                f'on one project. Fix the sheet before reassigning.'
            )

        index = len(assignments)
        if cell(col_first_done).lower() in DONE_VALUES:
            completed.add((index, 0))
        if cell(col_second_done).lower() in DONE_VALUES:
            completed.add((index, 1))

        assignments.append([first, second])
        project_ids.append(cell(col_project) or str(index + 1))

    if not assignments:
        raise SheetError(f'{path} has headers but no assignment rows.')

    scorers = sorted({s for pair in assignments for s in pair})
    return assignments, scorers, project_ids, completed
