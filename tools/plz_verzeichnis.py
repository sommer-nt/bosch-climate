"""Erzeugt das PLZ-Verzeichnis (alle deutschen Postleitzahlen mit Ort, Bundesland, Koordinaten).

Quelle: GeoNames Postal Codes DE (https://www.geonames.org), Lizenz CC BY 4.0.
Aufruf:  python tools/plz_verzeichnis.py [geonames_DE.txt]
Ergebnis: splitklima/daten/plz_verzeichnis.csv  (plz;ort;bundesland;lat;lon)
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
QUELLE = WURZEL / "splitklima" / "daten" / "quellen" / "geonames_DE.txt"
ZIEL = WURZEL / "splitklima" / "daten" / "plz_verzeichnis.csv"


def main(quelle: Path) -> None:
    eintraege: dict[str, list[tuple[str, str, float, float]]] = defaultdict(list)
    with quelle.open(encoding="utf-8") as f:
        for z in csv.reader(f, delimiter="\t"):
            if len(z) < 11 or z[0] != "DE" or not z[1].isdigit() or len(z[1]) != 5:
                continue
            eintraege[z[1]].append((z[2].strip(), z[3].strip(), float(z[9]), float(z[10])))
    with ZIEL.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["plz", "ort", "bundesland", "lat", "lon"])
        for plz in sorted(eintraege):
            orte = eintraege[plz]
            # Reihenfolge wie bei GeoNames (Hauptort zuerst); Ortsteile wie „Hamburg Altstadt“ fallen weg,
            # wenn der Ort selbst („Hamburg“) schon genannt ist
            namen = list(dict.fromkeys(o[0] for o in orte))
            namen = [n for n in namen if not any(n != m and n.startswith(m + " ") for m in namen)]
            ort = namen[0] if len(namen) == 1 else f"{namen[0]} ({', '.join(namen[1:3])}{' …' if len(namen) > 3 else ''})"
            lat = sum(o[2] for o in orte) / len(orte)
            lon = sum(o[3] for o in orte) / len(orte)
            w.writerow([plz, ort, orte[0][1], f"{lat:.4f}", f"{lon:.4f}"])
    print(f"{len(eintraege)} Postleitzahlen → {ZIEL.relative_to(WURZEL)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else QUELLE)
