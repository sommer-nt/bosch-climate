#!/usr/bin/env bash
# BOSCH Climate Split-Klima-Konfigurator lokal starten (macOS/Linux)
set -e
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
[ -f .streamlit/secrets.toml ] || echo "Hinweis: Für die KI-Planerkennung .streamlit/secrets.toml anlegen (Vorlage: .streamlit/secrets.toml.beispiel)."
exec .venv/bin/python -m streamlit run app.py
