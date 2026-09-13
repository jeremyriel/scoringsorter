@echo off
REM Sorter - assign scorers (Windows launcher).
REM
REM Double-click it, or run it from a command prompt.
REM
REM Everything resolves relative to this script (%~dp0), so the whole folder can
REM be copied anywhere and still work. There is nothing to install: the tool uses
REM only the Python standard library.
REM
REM Python runs in the FOREGROUND of this console on purpose - never via "start"
REM and never pythonw - so closing the window stops the run instead of leaving it
REM going detached.

setlocal
cd /d "%~dp0"
set "ROOT=%~dp0"

echo.
echo   ==================================================================
echo                     SORTER - ASSIGN SCORERS
echo   ==================================================================
echo.

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)

if not defined PY (
    echo   [ERROR] Python 3.9 or newer was not found.
    echo           Install it from https://www.python.org/downloads/
    echo           During setup, tick "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

REM Confirm this copy can actually run before starting.
%PY% -m sorter.selfcheck
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)

%PY% "%ROOT%assign.py" %*

echo.
pause
endlocal
