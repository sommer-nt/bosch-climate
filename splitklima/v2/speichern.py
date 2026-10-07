"""Konfiguration als JSON speichern und wieder laden (Version 2)."""

from __future__ import annotations

import json
import re
from datetime import datetime

from pydantic import ValidationError

from ..modell import Projekt

FORMAT = "bosch-climate-konfiguration"
VERSION = 1
MAX_BYTES = 2_000_000


class LadeFehler(ValueError):
    """Datei ist keine gültige Konfiguration."""


def exportieren(projekt: Projekt, auswahl: dict | None = None) -> str:
    """Projekt (inkl. Räume, Einstellungen, Zubehörmengen) und UI-Auswahl als JSON-Text."""
    return json.dumps({
        "format": FORMAT,
        "version": VERSION,
        "gespeichert": datetime.now().isoformat(timespec="seconds"),
        "projekt": projekt.model_dump(mode="json"),
        "auswahl": auswahl or {},
    }, ensure_ascii=False, indent=1)


def importieren(daten: bytes | str) -> tuple[Projekt, dict]:
    """JSON-Text prüfen und in ein Projekt umwandeln. Wirft ``LadeFehler`` mit verständlicher Meldung."""
    if isinstance(daten, bytes):
        if len(daten) > MAX_BYTES:
            raise LadeFehler("Datei ist zu groß für eine Konfiguration.")
        try:
            daten = daten.decode("utf-8-sig")
        except UnicodeDecodeError as fehler:
            raise LadeFehler("Datei ist keine Textdatei (UTF-8).") from fehler
    try:
        inhalt = json.loads(daten)
    except json.JSONDecodeError as fehler:
        raise LadeFehler(f"Kein gültiges JSON (Zeile {fehler.lineno}).") from fehler
    if not isinstance(inhalt, dict) or inhalt.get("format") != FORMAT:
        raise LadeFehler("Das ist keine gespeicherte Konfiguration dieses Programms.")
    if int(inhalt.get("version", 0)) > VERSION:
        raise LadeFehler("Die Datei stammt aus einer neueren Programmversion – bitte Programm aktualisieren.")
    try:
        projekt = Projekt.model_validate(inhalt.get("projekt") or {})
    except ValidationError as fehler:
        feld = ".".join(str(x) for x in fehler.errors()[0]["loc"]) if fehler.errors() else "?"
        raise LadeFehler(f"Konfiguration enthält ungültige Werte (Feld „{feld}“).") from fehler
    auswahl = inhalt.get("auswahl") if isinstance(inhalt.get("auswahl"), dict) else {}
    return projekt, auswahl


def dateiname(projekt: Projekt) -> str:
    name = re.sub(r"[^A-Za-z0-9ÄÖÜäöüß_-]+", "_", projekt.name or "Konfiguration").strip("_") or "Konfiguration"
    return f"Klima_{name}_{projekt.config_id}.json"
