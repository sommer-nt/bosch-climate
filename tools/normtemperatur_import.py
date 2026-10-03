"""Importiert die offizielle PLZ-Tabelle der DIN/TS 12831-1 (Norm-Außentemperatur je PLZ).

Aufruf:  python tools/normtemperatur_import.py <Tabelle.xlsx|.csv>
Ergebnis: splitklima/daten/normaussentemperatur_plz.csv  (plz;theta_e;theta_m)

Die Spalten werden an der Überschrift erkannt (Reihenfolge egal):
  PLZ / Postleitzahl · Norm-Außentemperatur / θe / Theta_e · Jahresmittel / θm,e (optional)
Geprüft wird: PLZ 5-stellig (fehlende führende Null aus Excel wird ergänzt), Wertebereiche,
widersprüchliche Doppel-Einträge, Abdeckung gegenüber dem PLZ-Verzeichnis. Bei Fehlern wird
nichts geschrieben.
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

from splitklima.klima_plz import NORMTABELLE_CSV, plz_normalisieren, verzeichnis  # noqa: E402

THETA_E_BEREICH = (-25.0, 0.0)
THETA_M_BEREICH = (2.0, 14.0)


def _zahl(x) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace("−", "-").replace("–", "-").replace("°C", "").replace(" ", "")
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _zeilen(pfad: Path) -> list[list]:
    if pfad.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        import openpyxl

        wb = openpyxl.load_workbook(pfad, read_only=True, data_only=True)
        alle = []
        for ws in wb.worksheets:  # erstes Blatt mit erkennbarer Kopfzeile gewinnt
            zeilen = [list(z) for z in ws.iter_rows(values_only=True)]
            if _spalten(zeilen)[0] is not None:
                return zeilen
            alle = alle or zeilen
        return alle
    text = pfad.read_bytes()
    for kod in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            inhalt = text.decode(kod)
            break
        except UnicodeDecodeError:
            continue
    dialekt = csv.Sniffer().sniff(inhalt[:4000], delimiters=";,\t")
    return [list(z) for z in csv.reader(inhalt.splitlines(), dialekt)]


def _spalten(zeilen: list[list]) -> tuple[int | None, int | None, int | None, int]:
    """(Spalte PLZ, Spalte θe, Spalte θm, Index der Kopfzeile)."""
    for i, z in enumerate(zeilen[:30]):
        kopf = [re.sub(r"\s+", " ", str(c or "")).strip().lower() for c in z]
        plz = next((j for j, k in enumerate(kopf) if k in ("plz", "postleitzahl") or k.startswith("plz")), None)
        te = next((j for j, k in enumerate(kopf) if ("norm" in k and "au" in k) or k in ("θe", "theta_e", "te")
                   or "norm-außentemperatur" in k or "normaussentemperatur" in k), None)
        tm = next((j for j, k in enumerate(kopf) if "mittel" in k or k in ("θm,e", "θme", "theta_m", "tm")), None)
        if plz is not None and te is not None:
            return plz, te, tm, i
    return None, None, None, -1


def importiere(pfad: Path, ziel: Path = NORMTABELLE_CSV) -> int:
    zeilen = _zeilen(pfad)
    sp_plz, sp_te, sp_tm, kopf = _spalten(zeilen)
    if sp_plz is None:
        print("FEHLER: Keine Kopfzeile mit „PLZ“ und „Norm-Außentemperatur“ gefunden.")
        return 2

    werte: dict[str, tuple[float, float | None]] = {}
    fehler: list[str] = []
    for nr, z in enumerate(zeilen[kopf + 1:], start=kopf + 2):
        if not any(c not in (None, "") for c in z):
            continue
        roh = z[sp_plz] if sp_plz < len(z) else None
        plz = plz_normalisieren(roh)
        te = _zahl(z[sp_te]) if sp_te < len(z) else None
        tm = _zahl(z[sp_tm]) if sp_tm is not None and sp_tm < len(z) else None
        if plz is None:
            fehler.append(f"Zeile {nr}: ungültige PLZ „{roh}“")
            continue
        if te is None or not THETA_E_BEREICH[0] <= te <= THETA_E_BEREICH[1]:
            fehler.append(f"Zeile {nr}: PLZ {plz} – Norm-Außentemperatur „{z[sp_te]}“ fehlt oder unplausibel")
            continue
        if tm is not None and not THETA_M_BEREICH[0] <= tm <= THETA_M_BEREICH[1]:
            fehler.append(f"Zeile {nr}: PLZ {plz} – Jahresmitteltemperatur {tm} unplausibel")
            continue
        if plz in werte and werte[plz] != (te, tm):
            fehler.append(f"Zeile {nr}: PLZ {plz} doppelt mit abweichenden Werten {werte[plz]} / {(te, tm)}")
            continue
        werte[plz] = (te, tm)

    vz = verzeichnis()
    unbekannt = sorted(set(werte) - set(vz))
    fehlend = sorted(set(vz) - set(werte))
    print(f"Gelesen: {len(werte)} PLZ aus {pfad.name} (Kopfzeile {kopf + 1}).")
    print(f"Abdeckung PLZ-Verzeichnis: {len(set(werte) & set(vz))} von {len(vz)} "
          f"({100 * len(set(werte) & set(vz)) / len(vz):.1f} %).")
    if unbekannt:
        print(f"Hinweis: {len(unbekannt)} PLZ nicht im Verzeichnis (z. B. Postfach-PLZ): {', '.join(unbekannt[:10])} …")
    if fehlend:
        print(f"Hinweis: {len(fehlend)} PLZ ohne Tabellenwert – dort gilt die nächstgelegene PLZ "
              f"(≤ 15 km): {', '.join(fehlend[:10])} …")
    for p in ("72622", "70173", "80331", "10115", "20095", "01067"):
        if p in werte:
            print(f"  Stichprobe {p} {vz[p].ort if p in vz else ''}: θe = {werte[p][0]} °C, θm,e = {werte[p][1]} °C")
    if fehler:
        print(f"FEHLER: {len(fehler)} Zeilen fehlerhaft – nichts geschrieben.")
        for f in fehler[:25]:
            print("  " + f)
        return 1
    if len(werte) < 1000:
        print("FEHLER: Weniger als 1000 PLZ – das ist nicht die vollständige Tabelle. Nichts geschrieben.")
        return 1

    with ziel.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["plz", "theta_e", "theta_m"])
        for p in sorted(werte):
            te, tm = werte[p]
            w.writerow([p, f"{te:g}", "" if tm is None else f"{tm:g}"])
    print(f"Geschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(importiere(Path(sys.argv[1])))
