# Sorter — Save State / Orientation Doc

> Purpose: let a new Claude Code session get fully oriented on this tool without
> re-deriving anything. Written 2026-09-12 at the end of the build session.
> If code and this doc disagree, trust the code and update this doc.
>
> `DESIGN.md` is the outward-facing version of the same material (written for a
> newcomer or a methods section). This file is the working one: it records the
> decisions, the traps, and the things already tried and rejected.

---

## 1. What this is

A standalone terminal tool that assigns two human scorers to each of N projects,
and reassigns work when a scorer drops out. Two scripts, six launchers, no
dependencies.

Built alongside SkillTree (an LLM rubric-scoring app) because measuring
LLM-versus-human agreement needs a human baseline, and that baseline needs
double-scored projects. **But it imports nothing from SkillTree and references
it nowhere** — verified by grep. It is meant to be moved out of that repo and
used for any two-rater task.

**Anything that assumes a parent project is a bug.** Keep it that way.

## 2. Layout

```
assign.py            entry: ask N and S, compute, write a timestamped run dir
reassign.py          entry: read a sheet, refill only the vacated slots
sorter/
  algorithm.py       THE CORE. Pure functions, no I/O, no state. Read first.
  sheets.py          CSV + dependency-free .xlsx writer
  sheet_reader.py    reads a sheet back (CSV or .xlsx), loose header matching
  summary.py         sheet rows + the loads/pairing-matrix report
  console.py         prompts, [OK]/[WARN]/[ERROR] tags, unique_dir()
  selfcheck.py       preflight the launchers run before anything else
Start Main Assign.{command,sh,bat}
Start Reassign.{command,sh,bat}
DESIGN.md            outward-facing design + methodology
README.md            how to use it
output/              run dirs; gitignored where a repo is present
```

## 3. The algorithm, and why it is the way it is

**Construction: circle method (round-robin scheduling).** Enumerates all
`C(S,2)` pairs arranged into rounds where each scorer appears at most once per
round. Odd `S` gets a `None` placeholder so positions pair evenly; whoever faces
it sits that round out, once per full schedule.

Walk that sequence, cycling it, take `N` pairs. This gets both goals at once:

- pairings repeat only at `ceil(N / C(S,2))` — the provable minimum;
- each complete pass is perfectly balanced (every scorer appears `S-1` times).

**Balance repair is required, not optional.** A *partial* final pass skews loads
— spread hits 2 at e.g. `N=50, S=25`. Repair: while `max - min > 1`, move one
slot from the most-loaded to the least-loaded, rejecting moves that would
duplicate a scorer on a project or exceed the pairing cap.

> **Trap already hit:** the first repair triggered on
> `load > ceil(2N/S) AND someone < floor(2N/S)`. That misses the common case —
> with `N=7, S=5` loads came out `{4,3,3,2,2}`, nobody below the floor, so it
> never fired. The correct rule is the simple one: *while max−min > 1, move from
> argmax to argmin*. Don't reintroduce threshold logic.

**Orientation** (which of the pair is listed first): greedy, fewer-firsts wins.
Keeps each scorer's first/second split near 50/50.

**Reassignment fills vacated slots only.** Survivors keep everything. Each hole
goes to the remaining scorer who is not the partner, has fewest shared projects
with that partner, and is least loaded — in that order.

> **Trap already hit:** greedy fill alone left spread 2 in ~5% of scenarios
> (15/287), because it weighs pairing dispersion above load. Fixed with
> `_rebalance_vacancies`, which rebalances **only slots that were just vacated**
> — so no survivor is disturbed, which is the whole point of fill-only. After
> it: 0/287 failures.

Note `reassign()` re-derives its `changes` list after rebalancing, so the log
reflects the final sheet rather than the greedy's intermediate state.

## 4. Verification status

Everything below was actually run, not reasoned about.

- **assign()**: 585 (N,S) combos, S 2–40, N 1–1000. Spread ≤1 everywhere,
  pairing at theoretical optimum everywhere, no duplicate scorer.
- **reassign()**: 287 combos + 210 scenario checks. No departed scorer left, no
  duplicates, **0 survivors disturbed**, spread ≤1, change log exact.
- **End-to-end**: 9 configurations through the real scripts, output files
  re-read and re-verified independently, `.xlsx` confirmed identical to `.csv`.
- **Standalone**: copied to `/tmp` outside the repo, both scripts ran clean.
- **.xlsx validity**: the hand-written workbook was read back by `openpyxl` with
  correct types (ints stay ints) and correct escaping of `& < >` and quotes.

If you change `algorithm.py`, re-run the grid. It takes seconds and it is the
only thing standing between this tool and a silently biased study design.

## 5. Decisions made with the user — do not relitigate

1. **Zero dependencies, including Excel output.** `.xlsx` is written as zipped
   XML by hand (`sheets.py`). Rejected: openpyxl in an auto-venv. Reason: this
   must run offline, on any machine, with no install step.
2. **Reassignment disturbs nobody who stays.** Rejected: full reshuffle, and
   "fill then swap survivors if needed". Reason: people may already have started.
3. **Progress columns ship empty.** `First/Second Scorer Done` exist so
   reassignment can skip finished work. Ignoring them changes nothing.
4. **A summary file every run**, with loads + pairing matrix + attained-vs-optimal.

## 6. Bugs already found and fixed — do not reintroduce

- **Falsy-zero on `--projects 0`.** `args.projects if args.projects else ask()`
  sent an explicit `0` to the interactive prompt. Must be `is not None`. (This
  exact trap has bitten the neighbouring SkillTree project twice.)
- **Same-second run-directory collision.** Two runs in one second wrote to the
  same folder — a reassign round-trip overwrote the sheet it had just read.
  `console.unique_dir()` suffixes `-2`, `-3`.
- **Bad `--leaving` dropped into an interactive prompt** instead of failing.
  A flag is a deliberate instruction: reject it outright. A value typed at the
  prompt still just re-asks.

## 7. Behaviours worth knowing before changing anything

- `sheet_reader` matches headers loosely (case/punctuation stripped) so a sheet
  a human has tidied still loads. Done-values accepted: `y/yes/done/true/1/x/
  complete/completed`; anything else, including blank, means not done.
- Scorer IDs need not be contiguous after reassignment — a departing scorer with
  completed work legitimately remains in the sheet. `reassign` handles
  non-contiguous ID sets (verified on a round-trip producing IDs `1,3,4,6`).
- `find_sheets()` sorts run directories by name, which is chronological because
  names are timestamps. The `-2` suffix does not break this.
- Both entry points wrap `main()` and print errors rather than raising, then
  `console.hold()` keeps a double-clicked window open. Do not "clean up" that
  try/except.
- Launchers `exec` Python in the foreground of their process group — no `&`, no
  `nohup`, no `setsid`, and never `start`/`pythonw` on Windows — so closing the
  window stops the run.

## 8. Known limits (documented in DESIGN.md §6)

- Exactly two scorers per project; three would need a different construction.
- No availability, expertise, or conflict-of-interest constraints.
- `S=2` is degenerate: both score everything, tool warns and proceeds.
- Repeated reassignments gradually erode pairing dispersion, since the existing
  allocation is preserved each time. `summary.txt` shows the attained figure
  after every run, so the drift is visible rather than silent.
- Deterministic by design. For randomised assignment, shuffle which person holds
  which ID — that randomises without touching the combinatorics.

## 9. Where to look next

- `sorter/algorithm.py` — the whole method, ~200 lines, pure functions.
- `DESIGN.md` §2 for the formal statement and bounds, §4 for verification.
- `summary.py::render` — the attained-vs-optimal reporting a user reads.
