#!/usr/bin/env python3
"""Sorter — assign two scorers to every project.

Asks how many projects and how many scorers, then works out who scores what so
that every project is scored by two different people, everyone gets about the
same number of projects, and the same two people are paired as rarely as the
numbers allow.

Writes a timestamped folder under output/ containing the assignment sheet as
both CSV and Excel, plus a summary you can check the split against.

No dependencies, no network, no configuration. Project-agnostic: it only ever
deals in counts and integer scorer IDs.

Usage:
    python3 assign.py
    python3 assign.py --projects 120 --scorers 8
    python3 assign.py --projects 120 --scorers 8 --yes
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from sorter import algorithm, console, sheets, summary  # noqa: E402

OUTPUT_DIR = HERE / 'output'


def parse_args():
    parser = argparse.ArgumentParser(description='Assign two scorers to each project')
    parser.add_argument('--projects', type=int, help='how many projects to score')
    parser.add_argument('--scorers', type=int, help='how many people are available to score')
    parser.add_argument('--yes', action='store_true', help='do not ask for confirmation')
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    console.banner('SORTER — ASSIGN SCORERS')
    print('  Works out which two people score each project, keeping the workload')
    print('  even and pairing everyone with as many different partners as possible.')

    console.section('Questions')
    # `is not None`, not truthiness: --projects 0 is a value the user supplied
    # and must be rejected with a clear message, not silently treated as "not
    # given" and turned into an interactive prompt.
    projects = args.projects if args.projects is not None else console.ask_int(
        'How many projects are you going to score?', minimum=1)
    scorers = args.scorers if args.scorers is not None else console.ask_int(
        'How many people are available to score?', minimum=2)

    if projects < 1:
        console.error(f'Cannot assign {projects} projects.',
                      'There has to be at least 1 project to score.')
        return 1
    if scorers < 2:
        console.error(f'Cannot split work between {scorers} scorer(s).',
                      'Each project has to be scored by two different people, '
                      'so at least 2 are needed.')
        return 1

    possible_pairs = scorers * (scorers - 1) // 2
    if scorers == 2:
        console.warn('With only 2 scorers, both of them score every project — '
                     'there is no other pairing available.')
    elif projects > possible_pairs:
        repeats = algorithm.optimal_max_pairing(projects, scorers)
        console.info(f'{projects} projects but only {possible_pairs} possible pairs, so some '
                     f'pairs must repeat — each at most {repeats} time(s).')
    else:
        console.info(f'{projects} projects and {possible_pairs} possible pairs — '
                     f'no two scorers need ever be paired twice.')

    console.section('Working it out')
    assignments = algorithm.assign(projects, scorers)
    ids = list(range(1, scorers + 1))
    counts = algorithm.loads(assignments, ids)
    pairs = algorithm.pair_counts(assignments)

    console.ok(f'{projects} projects assigned across {scorers} scorers')
    console.ok(f'each scorer has {min(counts.values())}-{max(counts.values())} projects '
               f'(average {projects * 2 / scorers:.1f})')
    console.ok(f'most-repeated pairing: {max(pairs.values())} '
               f'(best possible: {algorithm.optimal_max_pairing(projects, scorers)})')
    console.ok(f'{len(pairs)} distinct scorer pairs used')

    if not args.yes and not console.confirm('Write these assignments?'):
        console.info('Nothing was written.')
        return 0

    console.section('Writing')
    stamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = console.unique_dir(OUTPUT_DIR, stamp)
    out.mkdir(parents=True)

    rows = summary.sheet_rows(assignments)
    sheets.write_csv(out / 'assignments.csv', rows)
    console.ok('assignments.csv')
    sheets.write_xlsx(out / 'assignments.xlsx', rows)
    console.ok('assignments.xlsx')

    report = summary.render(
        assignments, ids, 'SCORER ASSIGNMENT SUMMARY',
        extra_lines=[f'Generated:         {stamp}'],
    )
    (out / 'summary.txt').write_text(report, encoding='utf-8')
    console.ok('summary.txt')

    (out / 'run_info.txt').write_text(
        'Sorter — assignment run\n'
        f'Generated:            {stamp}\n'
        f'Projects:             {projects}\n'
        f'Scorers:              {scorers}\n'
        f'Load per scorer:      {min(counts.values())}-{max(counts.values())}\n'
        f'Max pairing repeat:   {max(pairs.values())} '
        f'(best possible {algorithm.optimal_max_pairing(projects, scorers)})\n'
        f'Distinct pairs used:  {len(pairs)} of {possible_pairs} possible\n'
        '\n'
        'To reassign someone\'s projects later, run the reassign script and\n'
        'pick this folder.\n',
        encoding='utf-8')
    console.ok('run_info.txt')

    print()
    print(f'  Output: {out}')
    print('  Open assignments.xlsx to see who scores what, and summary.txt to check the split.')
    print()
    return 0


if __name__ == '__main__':
    try:
        code = main()
    except KeyboardInterrupt:
        console.info('Cancelled.')
        code = 130
    except Exception as exc:  # a double-clicked window must explain itself
        console.error(str(exc))
        code = 1
    console.hold()
    sys.exit(code)
