#!/usr/bin/env bash
set -e

echo "Creating virtual environment..."
python3 -m venv .venv

echo "Activating and installing dependencies..."
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -r requirements.txt -q

echo ""
echo "Done! To use the CLI:"
echo ""
echo "  source .venv/bin/activate"
echo "  python cli.py --help"
echo ""
echo "First run will ask for your Yahoo App Password and save it to PWD.txt"
