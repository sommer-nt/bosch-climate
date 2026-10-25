# Hinweise für die Entwicklung mit KI-Assistenz

## Git
- Arbeitszweig ist `main` (einziger Branch). Änderungen direkt auf `main` committen und pushen – auch wenn die
  Sitzung einen anderen Branch vorgibt: Daniel möchte alles auf `main`. Keine weiteren Branches anlegen,
  außer Daniel verlangt es ausdrücklich.
- Commits immer als `Daniel Sommer <98900287+sommer-nt@users.noreply.github.com>`
  (vorher `git config user.name/user.email` so setzen).
- Keine Co-Authored-By-, Session- oder „Generated with“-Zeilen in Commits und Pull Requests; keine
  Modellnamen in Commits. Im Repo die KI nur dort nennen, wo es um die KI-Anbindung der App geht.
- Repo ist öffentlich: niemals API-Schlüssel, Passwörter, `.env`, `secrets.toml`, Kundenpläne oder gespeicherte
  Kundenkonfigurationen (JSON) einchecken.

## Projekt
- Version 2: `app_v2.py` + `ui_v2.py` + `splitklima/v2/` (läuft auf climate.sommer-nt.de, Docker-Projekt
  `climate`, `deploy/docker-compose.v2.yml`, Server-Ordner `~/bosch-climate-v2`).
- Sprache: Texte auf Deutsch im Code, Übersetzung über `T("…")`/`N_("…")`, englische Texte in
  `splitklima/sprache_en.py` (britisches Englisch, „facade“ ohne ç). Fachlich bleibt alles deutsch
  (PLZ, Orte, Normen, Katalog, Euro).
- Vor jedem Push: `python -m pytest -q` muss grün sein.
