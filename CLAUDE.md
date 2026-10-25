# Hinweise für Claude Code

## Git
- Arbeitszweig ist `version-2`. Änderungen dort committen und pushen, keine anderen Branches anlegen oder
  pushen, außer Daniel verlangt es ausdrücklich.
- Commits immer als `Daniel Sommer <98900287+sommer-nt@users.noreply.github.com>`
  (vorher `git config user.name/user.email` so setzen).
- Keine Co-Authored-By-, Claude-Session- oder „Generated with Claude“-Zeilen in Commits und Pull Requests;
  keine Modellnamen in Commits.
- Repo ist öffentlich: niemals API-Schlüssel, Passwörter, `.env`, `secrets.toml`, Kundenpläne oder gespeicherte
  Kundenkonfigurationen (JSON) einchecken.

## Projekt
- Version 2: `app_v2.py` + `ui_v2.py` + `splitklima/v2/` (läuft auf climate.sommer-nt.de, Docker-Projekt
  `climate`, `deploy/docker-compose.v2.yml`). Version 1 (`app.py`, klima.sommer-nt.de) nicht verändern.
- Sprache: Texte auf Deutsch im Code, Übersetzung über `T("…")`/`N_("…")`, englische Texte in
  `splitklima/sprache_en.py` (britisches Englisch, „facade“ ohne ç). Fachlich bleibt alles deutsch
  (PLZ, Orte, Normen, Katalog, Euro).
- Vor jedem Push: `python -m pytest -q` muss grün sein.
