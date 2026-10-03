"""Klimadaten je PLZ (DIN/TS 12831-1) übernehmen – aus einer Datei oder direkt von der BWP-Klimakarte.

Aufruf:
  python tools/normtemperatur_import.py --bwp                 # von waermepumpe.de/werkzeuge/klimakarte laden
  python tools/normtemperatur_import.py <Tabelle.xlsx|.csv>   # z. B. Export der Klimakarte

Ergebnis: splitklima/daten/normaussentemperatur_plz.csv. Geprüft wird: PLZ 5-stellig (fehlende
führende Null aus Excel wird ergänzt), Wertebereiche, widersprüchliche Doppel-Einträge, Vollständigkeit.
Bei Fehlern wird nichts geschrieben – eine vorhandene Tabelle bleibt unverändert.
"""

from __future__ import annotations

import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from splitklima.klima_plz import NORMTABELLE_CSV  # noqa: E402
from splitklima.klimadaten import aus_datei, von_bwp_laden  # noqa: E402


def importiere(pfad: Path, ziel: Path = NORMTABELLE_CSV) -> int:
    ok, meldungen = aus_datei(Path(pfad), ziel)
    print("\n".join(meldungen))
    print(f"Geschrieben: {ziel}" if ok else "FEHLER – nichts geschrieben.")
    return 0 if ok else 1


def bwp(ziel: Path = NORMTABELLE_CSV) -> int:
    ok, meldungen = von_bwp_laden(ziel)
    print("\n".join(meldungen))
    print(f"Geschrieben: {ziel}" if ok else "FEHLER – nichts geschrieben.")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(bwp() if sys.argv[1] == "--bwp" else importiere(Path(sys.argv[1])))
