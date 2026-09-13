"""Preflight: confirm this copy of Sorter can actually run before it tries to.

The launchers call this first. Sorter has no third-party dependencies, so there
is no package install to verify — what can genuinely go wrong is a Python too
old for the syntax used, a stripped-down Python missing a standard-library
module, an incomplete copy of the folder, or an output directory that cannot be
written to (a read-only drive, a locked-down share).

Each of those produces a specific message saying what to do about it, rather
than a traceback from somewhere deep in a run.

Run directly to check a copy by hand:

    python3 -m sorter.selfcheck
"""

import importlib
import os
import sys
from pathlib import Path

MINIMUM_PYTHON = (3, 9)

# Standard library only. Listed explicitly so a stripped or embedded Python
# fails here with a clear message instead of part-way through a run.
REQUIRED_MODULES = [
    'argparse', 'csv', 'collections', 'datetime', 'importlib',
    'pathlib', 're', 'sys', 'unicodedata', 'zipfile',
    'xml.etree.ElementTree', 'xml.sax.saxutils',
]

# Files that must be present for the folder to be a complete copy.
REQUIRED_FILES = [
    'assign.py',
    'reassign.py',
    'sorter/__init__.py',
    'sorter/algorithm.py',
    'sorter/console.py',
    'sorter/sheet_reader.py',
    'sorter/sheets.py',
    'sorter/summary.py',
]

ROOT = Path(__file__).resolve().parent.parent


def problems() -> list[str]:
    found = []

    if sys.version_info < MINIMUM_PYTHON:
        found.append(
            f'Python {".".join(map(str, MINIMUM_PYTHON))} or newer is required, '
            f'but this is {sys.version.split()[0]}.\n'
            f'  Install a newer Python from https://www.python.org/downloads/'
        )
        # Nothing below will be meaningful on an old interpreter.
        return found

    missing_modules = []
    for name in REQUIRED_MODULES:
        try:
            importlib.import_module(name)
        except ImportError:
            missing_modules.append(name)
    if missing_modules:
        found.append(
            f'This Python is missing standard-library modules: '
            f'{", ".join(missing_modules)}.\n'
            f'  It may be a cut-down or embedded build. Install a full Python '
            f'from https://www.python.org/downloads/'
        )

    missing_files = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    if missing_files:
        found.append(
            f'This copy of Sorter is incomplete — missing: '
            f'{", ".join(missing_files)}.\n'
            f'  Copy the whole Sorter folder, not just the launcher.'
        )

    output = ROOT / 'output'
    try:
        output.mkdir(parents=True, exist_ok=True)
        probe = output / '.write-test'
        probe.write_text('ok', encoding='utf-8')
        probe.unlink()
    except OSError as exc:
        found.append(
            f'Cannot write to {output} ({exc.strerror or exc}).\n'
            f'  Move the Sorter folder somewhere writable — a read-only drive, '
            f'a disk image, or a protected folder will do this.'
        )

    return found


def main() -> int:
    issues = problems()
    if not issues:
        print(f'  [OK]    Ready — Python {sys.version.split()[0]}, no extra packages needed')
        return 0
    for issue in issues:
        first, _, rest = issue.partition('\n')
        print(f'  [ERROR] {first}', file=sys.stderr)
        if rest:
            print(rest, file=sys.stderr)
    return 1


if __name__ == '__main__':
    sys.exit(main())
