#!/usr/bin/env python3
"""Sorter — hand a departing scorer's projects to the people who remain.

Reads an existing assignment sheet, asks which scorer IDs can no longer do their
work, and fills only the slots those people held. Everyone who stays keeps every
project they already had, so nobody is told that work they may have started is
no longer theirs.

Replacements are chosen by the same principles as the original assignment: never
the same person twice on one project, pair with as many different partners as
possible, and keep the workload even.

Slots marked done in the sheet are left alone, even when the person who did them
is leaving — that work is already finished.

Usage:
    python3 reassign.py
    python3 reassign.py --input output/2026-09-12_143005/assignments.csv
    python3 reassign.py --input <sheet> --leaving 3,7 --yes
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from sorter import algorithm, console, sheet_reader, sheets, summary  # noqa: E402

OUTPUT_DIR = HERE / 'output'
SLOT_NAMES = {0: 'First Scorer', 1: 'Second Scorer'}


def parse_args():
    parser = argparse.ArgumentParser(description="Reassign a departing scorer's projects")
    parser.add_argument('--input', help='path to an existing assignments sheet (.csv or .xlsx)')
    parser.add_argument('--leaving', help='comma separated scorer IDs to reassign')
    parser.add_argument('--yes', action='store_true', help='do not ask for confirmation')
    return parser.parse_args()


def find_sheets() -> list[Path]:
    """Previous runs, newest first. Folder names are timestamps, so sorting the
    names reverse-chronologically is the same as sorting by date."""
    if not OUTPUT_DIR.is_dir():
        return []
    found = []
    for folder in sorted(OUTPUT_DIR.iterdir(), reverse=True):
        if not folder.is_dir():
            continue
        sheet = folder / 'assignments.csv'
        if sheet.is_file():
            found.append(sheet)
    return found


def choose_sheet(args) -> Path:
    if args.input:
        path = Path(args.input).expanduser().resolve()
        if not path.is_file():
            console.error(f'No such file: {path}',
                          'Check the path, or run with no arguments to pick from previous runs.')
            raise SystemExit(1)
        return path

    found = find_sheets()
    if not found:
        console.error(
            f'No previous assignment runs found in {OUTPUT_DIR}',
            'Run the main assign script first, or pass a sheet directly:\n'
            '  python3 reassign.py --input /path/to/assignments.csv')
        raise SystemExit(1)

    if len(found) == 1:
        return found[0]

    console.section('Which assignment sheet?')
    for number, path in enumerate(found, start=1):
        print(f'    {number}. {path.parent.name}')
    print()
    while True:
        answer = console.ask_text(f'Enter a number (1-{len(found)}), or q to quit:')
        if answer.lower() in ('q', 'quit'):
            raise SystemExit(0)
        if answer.isdigit() and 1 <= int(answer) <= len(found):
            return found[int(answer) - 1]
        print('    Not a valid choice.')


def ask_leaving(args, scorers, counts) -> set[int]:
    """Ask until a usable set of departing scorer IDs is given.

    A bad value typed at the prompt just re-asks — this is interactive and a
    typo should not end the run. A bad `--leaving` is different: it was a
    deliberate instruction that cannot be satisfied, so it fails outright
    rather than silently dropping into a prompt a script would never answer.
    """
    from_flag = args.leaving is not None

    def reject(message: str):
        if from_flag:
            console.error(message, 'Correct the --leaving value and run again.')
            raise SystemExit(1)
        print(f'    {message}')

    while True:
        raw = args.leaving if args.leaving is not None else console.ask_text(
            'Which scorer IDs need their projects reassigned? (comma separated):')
        args.leaving = None  # honour the flag once, then fall back to asking

        if not raw.strip():
            reject('Enter at least one scorer ID.')
            continue

        try:
            wanted = [int(part.strip()) for part in raw.split(',') if part.strip()]
        except ValueError:
            reject('Scorer IDs must be whole numbers, e.g. 3,7')
            continue

        unknown = [s for s in wanted if s not in scorers]
        if unknown:
            reject(f'Not in this sheet: {", ".join(map(str, unknown))}. '
                   f'Available: {", ".join(map(str, scorers))}')
            continue

        leaving = set(wanted)
        if len(scorers) - len(leaving) < 2:
            reject(f'That would leave {len(scorers) - len(leaving)} scorer(s). '
                   f'At least 2 must stay, since every project needs two different people.')
            continue

        total = sum(counts[s] for s in leaving)
        console.info(f'{len(leaving)} scorer(s) leaving, holding {total} project slots between them')
        return leaving


def main() -> int:
    args = parse_args()

    console.banner('SORTER — REASSIGN SCORERS')
    print('  Moves a departing scorer\'s projects to the people who remain.')
    print('  Everyone who stays keeps the projects they already had.')

    console.section('Reading the existing sheet')
    path = choose_sheet(args)
    try:
        assignments, scorers, project_ids, completed = sheet_reader.read_sheet(path)
    except sheet_reader.SheetError as exc:
        console.error(str(exc), 'Fix the sheet, or point at a different one with --input.')
        return 1

    counts = algorithm.loads(assignments, scorers)
    console.ok(f'read {path.parent.name}/{path.name}')
    console.detail(f'Projects: {len(assignments)}')
    console.detail(f'Scorers:  {len(scorers)}  (IDs {", ".join(map(str, scorers))})')
    console.detail('Current load: ' + '  '.join(f'{s}:{counts[s]}' for s in scorers))
    if completed:
        console.detail(f'Marked done: {len(completed)} slot(s) — these will not be reassigned')

    console.section('Who is leaving?')
    leaving = ask_leaving(args, scorers, counts)

    console.section('Working it out')
    try:
        updated, changes = algorithm.reassign(assignments, leaving, scorers, completed)
    except ValueError as exc:
        console.error(str(exc))
        return 1

    remaining = [s for s in scorers if s not in leaving]
    if not changes:
        console.warn('Nothing to reassign — every slot held by those scorers is already marked done.')
        return 0

    new_counts = algorithm.loads(updated, remaining)
    stuck = [(i, s) for (i, s) in completed if updated[i][s] in leaving]

    console.ok(f'{len(changes)} slot(s) reassigned across {len(remaining)} remaining scorers')
    console.ok(f'each remaining scorer now has {min(new_counts.values())}-{max(new_counts.values())} projects')
    console.ok('every project kept by a remaining scorer is unchanged')
    if stuck:
        console.info(f'{len(stuck)} completed slot(s) left with their original scorer')

    print()
    preview = changes[:10]
    for index, slot, previous, new in preview:
        print(f'    Project {project_ids[index]:>6}  {SLOT_NAMES[slot]:<14} '
              f'{previous} -> {new}')
    if len(changes) > len(preview):
        print(f'    ... and {len(changes) - len(preview)} more (see changes.csv)')
    print()

    if not args.yes and not console.confirm('Write the updated assignments?'):
        console.info('Nothing was written. The original sheet is untouched.')
        return 0

    console.section('Writing')
    stamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = console.unique_dir(OUTPUT_DIR, f'{stamp}_reassigned')
    out.mkdir(parents=True)

    rows = summary.sheet_rows(updated, project_ids, completed)
    sheets.write_csv(out / 'assignments.csv', rows)
    console.ok('assignments.csv')
    sheets.write_xlsx(out / 'assignments.xlsx', rows)
    console.ok('assignments.xlsx')

    change_rows = [['Project ID', 'Slot', 'Previous Scorer', 'New Scorer']]
    for index, slot, previous, new in changes:
        project = project_ids[index]
        change_rows.append([int(project) if str(project).isdigit() else project,
                            SLOT_NAMES[slot], previous, new])
    sheets.write_csv(out / 'changes.csv', change_rows)
    console.ok(f'changes.csv — {len(changes)} row(s)')

    report = summary.render(
        updated, remaining, 'SCORER REASSIGNMENT SUMMARY',
        extra_lines=[
            f'Generated:         {stamp}',
            f'Source sheet:      {path.parent.name}/{path.name}',
            f'Reassigned away:   {", ".join(map(str, sorted(leaving)))}',
            f'Slots reassigned:  {len(changes)}',
        ],
    )
    (out / 'summary.txt').write_text(report, encoding='utf-8')
    console.ok('summary.txt')

    (out / 'run_info.txt').write_text(
        'Sorter — reassignment run\n'
        f'Generated:           {stamp}\n'
        f'Source sheet:        {path}\n'
        f'Scorers before:      {", ".join(map(str, scorers))}\n'
        f'Reassigned away:     {", ".join(map(str, sorted(leaving)))}\n'
        f'Scorers remaining:   {", ".join(map(str, remaining))}\n'
        f'Slots reassigned:    {len(changes)}\n'
        f'Completed slots kept with their original scorer: {len(stuck)}\n'
        '\n'
        'The source sheet was not modified.\n',
        encoding='utf-8')
    console.ok('run_info.txt')

    print()
    print(f'  Output: {out}')
    print(f'  The original sheet is unchanged. See changes.csv for exactly what moved.')
    print()
    return 0


if __name__ == '__main__':
    try:
        code = main()
    except KeyboardInterrupt:
        console.info('Cancelled.')
        code = 130
    except Exception as exc:
        console.error(str(exc))
        code = 1
    console.hold()
    sys.exit(code)
