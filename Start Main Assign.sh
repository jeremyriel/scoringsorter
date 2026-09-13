#!/usr/bin/env bash
#
# Sorter — assign scorers (Linux launcher).
#
# Run ./"Start Main Assign.sh" from a terminal (first time: chmod +x "Start Main Assign.sh").
#
# Everything resolves relative to this script, so the whole folder can be copied
# anywhere — another machine, a USB drive — and still work. There is nothing to
# install: the tool uses only the Python standard library.

cd "$(dirname "$0")" || exit 1
ROOT="$(pwd)"

BOLD='\033[1m'; GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

# Closing the terminal sends SIGHUP to this process group; kill 0 takes the
# whole group down so nothing is left running. EXIT is deliberately not trapped
# — it would fire on an ordinary exit and cut off the closing prompt.
trap 'kill 0' HUP INT TERM

echo
echo -e "  ${CYAN}==================================================================${NC}"
echo -e "  ${BOLD}                  SORTER — ASSIGN SCORERS                         ${NC}"
echo -e "  ${CYAN}==================================================================${NC}"
echo

PY=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
            PY="$candidate"; break
        fi
    fi
done

if [ -z "$PY" ]; then
    echo -e "  ${RED}[ERROR]${NC} Python 3.9 or newer was not found."
    echo    "          Install it with your package manager, for example:"
    echo    "            sudo apt install python3       (Debian/Ubuntu)"
    echo    "            sudo dnf install python3       (Fedora)"
    echo
    read -r -p "  Press Enter to close..."
    exit 1
fi
echo -e "  ${GREEN}[OK]${NC}    Using $($PY --version)"

# Confirm this copy can actually run before starting: Python version,
# standard-library modules, a complete folder, and a writable output dir.
if ! "$PY" -m sorter.selfcheck; then
    echo
    read -r -p "  Press Enter to close..."
    exit 1
fi

# exec keeps Python in this shell's process group and in the foreground, so a
# closed window really does stop the run. Do not background this.
exec "$PY" "$ROOT/assign.py" "$@"
