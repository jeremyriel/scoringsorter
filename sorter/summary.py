"""The human-checkable summary: who has how much, and who is paired with whom.

The point of this file is that nobody has to take the assignment on trust. It
states the load each scorer carries, how often every pair of scorers shares a
project, and how those figures compare with the best that is mathematically
possible for the given numbers.
"""

from . import algorithm

HEADERS = ['Project ID', 'First Scorer', 'Second Scorer',
           'First Scorer Done', 'Second Scorer Done']


def sheet_rows(assignments, project_ids=None, completed=None) -> list[list]:
    completed = completed or set()
    rows = [HEADERS]
    for index, (first, second) in enumerate(assignments):
        project = project_ids[index] if project_ids else index + 1
        if isinstance(project, str) and project.isdigit():
            project = int(project)
        rows.append([
            project, first, second,
            'yes' if (index, 0) in completed else '',
            'yes' if (index, 1) in completed else '',
        ])
    return rows


def render(assignments, scorers, title, extra_lines=None) -> str:
    counts = algorithm.loads(assignments, scorers)
    pairs = algorithm.pair_counts(assignments)
    first_counts = {s: 0 for s in scorers}
    for first, _ in assignments:
        if first in first_counts:
            first_counts[first] += 1

    projects = len(assignments)
    possible_pairs = len(scorers) * (len(scorers) - 1) // 2
    best_pairing = algorithm.optimal_max_pairing(projects, len(scorers))
    worst_pairing = max(pairs.values()) if pairs else 0
    load_spread = max(counts.values()) - min(counts.values())

    out = ['=' * 64, title, '=' * 64, '']
    out.append(f'Projects:          {projects}')
    out.append(f'Scorers:           {len(scorers)}  (IDs: {_compact(scorers)})')
    out.append(f'Scoring slots:     {projects * 2}  (two per project)')
    out.append(f'Average per scorer: {projects * 2 / len(scorers):.2f}')
    out.extend(extra_lines or [])
    out.append('')

    out.append('-' * 64)
    out.append('LOAD PER SCORER')
    out.append('-' * 64)
    out.append(f'{"Scorer":>8}  {"Projects":>9}  {"As first":>9}  {"As second":>10}')
    for scorer in scorers:
        out.append(f'{scorer:>8}  {counts[scorer]:>9}  {first_counts[scorer]:>9}  '
                   f'{counts[scorer] - first_counts[scorer]:>10}')
    out.append('')
    out.append(f'Highest load: {max(counts.values())}   Lowest load: {min(counts.values())}   '
               f'Difference: {load_spread}')
    out.append(_verdict(
        load_spread <= 1,
        'Evenly split — no scorer carries more than one project above another.',
        f'Uneven: the busiest scorer has {load_spread} more projects than the quietest.',
    ))
    out.append('')

    out.append('-' * 64)
    out.append('PAIRING SPREAD')
    out.append('-' * 64)
    out.append(f'Distinct pairs possible with {len(scorers)} scorers: {possible_pairs}')
    out.append(f'Distinct pairs actually used:  {len(pairs)}')
    out.append(f'Most times any two scorers share a project: {worst_pairing}')
    out.append(f'Best achievable for these numbers:          {best_pairing}')
    out.append(_verdict(
        worst_pairing <= best_pairing,
        'Pairings are as spread out as the numbers allow.',
        'Pairings are more concentrated than necessary.',
    ))
    if projects <= possible_pairs:
        out.append(f'With {projects} projects and {possible_pairs} possible pairs, '
                   f'no two scorers need ever repeat.')
    out.append('')

    out.append('-' * 64)
    out.append('PAIRING MATRIX  (how many projects each pair shares)')
    out.append('-' * 64)
    out.extend(_matrix(scorers, pairs))
    out.append('')
    return '\n'.join(out) + '\n'


def _verdict(good: bool, yes: str, no: str) -> str:
    return f'  {"OK   " if good else "NOTE "} {yes if good else no}'


def _compact(scorers) -> str:
    """1..12 rather than a wall of numbers, when the IDs are contiguous."""
    if len(scorers) > 6 and scorers == list(range(scorers[0], scorers[-1] + 1)):
        return f'{scorers[0]}-{scorers[-1]}'
    return ', '.join(str(s) for s in scorers)


def _matrix(scorers, pairs) -> list[str]:
    if len(scorers) > 40:
        return ['  (too many scorers to draw a readable grid — see the pairing '
                'figures above)']
    width = max(3, len(str(max(scorers))) + 1)
    head = ' ' * (width + 1) + ''.join(f'{s:>{width}}' for s in scorers)
    lines = [head]
    for row in scorers:
        cells = []
        for col in scorers:
            if row == col:
                cells.append(f'{"-":>{width}}')
            else:
                cells.append(f'{pairs.get(tuple(sorted((row, col))), 0):>{width}}')
        lines.append(f'{row:>{width}} ' + ''.join(cells))
    return lines
