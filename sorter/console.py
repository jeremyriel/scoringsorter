"""Terminal output and prompts.

Same look as the other launchers in this project: a centered banner, then
fixed-width status tags at a two-space indent. Colours switch off when output
is not a terminal, so a redirected run produces clean text instead of escape
codes.
"""

import os
import sys

_USE_COLOR = sys.stdout.isatty() and os.environ.get('NO_COLOR') is None

if _USE_COLOR and os.name == 'nt':
    # Windows 10+ understands ANSI, but only once the mode bit is set. If that
    # fails, drop to plain text rather than printing raw escape sequences.
    try:
        import ctypes

        _kernel32 = ctypes.windll.kernel32
        _kernel32.SetConsoleMode(_kernel32.GetStdHandle(-11), 7)
    except Exception:
        _USE_COLOR = False


def _c(code: str) -> str:
    return code if _USE_COLOR else ''


BOLD = _c('\033[1m')
GREEN = _c('\033[0;32m')
YELLOW = _c('\033[1;33m')
RED = _c('\033[0;31m')
CYAN = _c('\033[0;36m')
DIM = _c('\033[2m')
NC = _c('\033[0m')


def banner(title: str) -> None:
    line = '=' * 66
    print()
    print(f"  {CYAN}{line}{NC}")
    print(f"  {BOLD}{title.center(66)}{NC}")
    print(f"  {CYAN}{line}{NC}")
    print()


def section(title: str) -> None:
    print()
    print(f"  {BOLD}{CYAN}{title}{NC}")
    print(f"  {DIM}{'-' * len(title)}{NC}")


def ok(msg: str) -> None:
    print(f"  {GREEN}[OK]{NC}    {msg}")


def info(msg: str) -> None:
    print(f"  {DIM}[--]{NC}    {msg}")


def warn(msg: str) -> None:
    print(f"  {RED}[WARN]{NC}  {msg}")


def error(msg: str, fix: str = '') -> None:
    """Errors always say how to fix the problem, not just what went wrong."""
    print(f"  {RED}[ERROR]{NC} {msg}", file=sys.stderr)
    for line in filter(None, fix.split('\n')):
        print(f"          {line}", file=sys.stderr)


def detail(msg: str) -> None:
    print(f"          {DIM}{msg}{NC}")


def ask_int(question: str, minimum: int, maximum: int = 1_000_000) -> int:
    """Keep asking until a whole number in range is given.

    Re-prompting beats exiting: this is an interactive tool someone
    double-clicked, and a typo should not mean starting over.
    """
    while True:
        try:
            raw = input(f"  {BOLD}{question}{NC} ").strip()
        except EOFError:
            raise SystemExit(1)
        if raw.lower() in ('q', 'quit', 'exit'):
            raise SystemExit(0)
        try:
            value = int(raw.replace(',', ''))
        except ValueError:
            print(f"    {RED}Please enter a whole number (or q to quit).{NC}")
            continue
        if value < minimum:
            print(f"    {RED}Needs to be at least {minimum}.{NC}")
            continue
        if value > maximum:
            print(f"    {RED}That is above the maximum of {maximum:,}.{NC}")
            continue
        return value


def ask_text(question: str) -> str:
    try:
        return input(f"  {BOLD}{question}{NC} ").strip()
    except EOFError:
        raise SystemExit(1)


def confirm(question: str) -> bool:
    """Anything but an explicit yes is a no."""
    try:
        answer = input(f"  {BOLD}{question}{NC} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return answer in ('y', 'yes')


def unique_dir(parent, name: str):
    """A run folder that does not already exist.

    Folder names are timestamps to the second, so two runs started within the
    same second would otherwise collide — and a reassignment reading one run
    could overwrite the very sheet it just read. Seen in testing, not theorised.
    """
    candidate = parent / name
    suffix = 2
    while candidate.exists():
        candidate = parent / f'{name}-{suffix}'
        suffix += 1
    return candidate


def hold() -> None:
    """Stop a double-clicked window from vanishing before it can be read."""
    if sys.stdin.isatty():
        try:
            input("\n  (Press Enter to close this window) ")
        except (EOFError, KeyboardInterrupt):
            pass
