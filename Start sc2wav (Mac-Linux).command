#!/usr/bin/env bash
# Double-click this file to start the SoundCloud → WAV app.
# On the first run it sets everything up (takes a minute); after that it's quick.
# It opens the page in your browser automatically. Close the window to stop.

set -e
cd "$(dirname "$0")"

# Find a Python 3.
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python 3 is not installed. Install it from https://www.python.org/downloads/ and try again."
  read -r -p "Press Return to close."
  exit 1
fi

# Create the virtual environment on first run.
if [ ! -d ".venv" ]; then
  echo "First-time setup: creating environment..."
  "$PY" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

# Install/refresh dependencies (fast if already installed).
echo "Checking dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "Starting the app..."
python webapp.py
