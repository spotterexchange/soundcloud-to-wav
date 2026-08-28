@echo off
REM Double-click this file to start the SoundCloud -> WAV app.
REM On the first run it sets everything up (takes a minute); after that it's quick.
REM It opens the page in your browser automatically. Close this window to stop.

cd /d "%~dp0"

REM Find Python.
where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo Python is not installed. Install it from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add Python to PATH" during install, then try again.
    pause
    exit /b 1
  )
)

REM Create the virtual environment on first run.
if not exist ".venv" (
  echo First-time setup: creating environment...
  %PY% -m venv .venv
)

call .venv\Scripts\activate.bat

echo Checking dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo Starting the app...
python webapp.py

pause
