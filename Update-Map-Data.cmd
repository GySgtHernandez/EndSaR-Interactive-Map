@echo off
rem Double-click to check MI School Data for new CEPI seclusion/restraint files,
rem rebuild the map data, run the accuracy checks, and preview the result.
rem Nothing is published: the public site changes only when the change reaches GitHub (see README).
cd /d "%~dp0"
title EndSaR - update map data
python -c "import sys" >nul 2>nul
if not %errorlevel%==0 (
  echo Python is not installed. Install it from https://www.python.org/downloads/ ^(tick "Add python.exe to PATH"^), then run this again.
  echo You can also run the update on GitHub instead: Actions tab ^> "Check for CEPI data updates" ^> Run workflow.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" python -m venv .venv
".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
if not exist reports mkdir reports
echo Downloading CEPI files and rebuilding the map data. This takes about a minute...
".venv\Scripts\python.exe" scripts\run_pipeline.py --discover --allow-change > reports\last-update-log.txt 2>&1
if not %errorlevel%==0 (
  echo.
  echo The update STOPPED because a step failed. The map data was not changed by a failed check.
  echo Details are in reports\last-update-log.txt
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\make_pr_body.py
echo.
type build\pr-body.md
echo.
echo The summary above is also saved in build\pr-body.md
echo Opening a preview of the updated map...
call "%~dp0Preview-Map.cmd"
