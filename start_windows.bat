@echo off
REM BOSCH Climate Split-Klima-Konfigurator lokal starten (Windows)
REM Doppelklick genügt. Beim ersten Start werden die Pakete installiert (einige Minuten).
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    echo Lege Python-Umgebung an ...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if not exist .venv\Scripts\python.exe (
        echo FEHLER: Python wurde nicht gefunden. Bitte Python 3.11 oder neuer installieren:
        echo https://www.python.org/downloads/  ^(Haken bei "Add python.exe to PATH" setzen^)
        pause
        exit /b 1
    )
)
echo Installiere/aktualisiere Pakete ...
.venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r requirements.txt
if errorlevel 1 (
    echo FEHLER bei der Paketinstallation. Im Firmennetz ggf. Proxy setzen, z. B.:
    echo   set HTTPS_PROXY=http://proxy.firma:8080
    pause
    exit /b 1
)
if not exist .streamlit\secrets.toml (
    echo Hinweis: Fuer die KI-Planerkennung .streamlit\secrets.toml anlegen
    echo          ^(Vorlage: .streamlit\secrets.toml.beispiel^).
)
echo Starte App ... der Browser oeffnet sich automatisch (http://localhost:8501)
.venv\Scripts\python.exe -m streamlit run app.py
pause
