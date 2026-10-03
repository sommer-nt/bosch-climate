"""Norm-Außentemperatur über die Postleitzahl (DIN/TS 12831-1).

Zwei Datenquellen:

* ``daten/plz_verzeichnis.csv`` – alle deutschen Postleitzahlen mit Ort, Bundesland und Koordinaten
  (GeoNames, CC BY 4.0). Dient der Prüfung der PLZ, der Ortsanzeige und der Nachbarsuche.
* ``daten/normaussentemperatur_plz.csv`` – die **offizielle Tabelle der DIN/TS 12831-1**
  (Norm-Außentemperatur θe und Jahresmitteltemperatur θm,e je PLZ). Sie wird mit
  ``tools/normtemperatur_import.py`` aus der gelieferten Datei erzeugt und geprüft.

Ermittlung – es wird nie ein Wert erfunden:

1. PLZ steht in der offiziellen Tabelle → Wert 1:1 (Status ``din``).
2. PLZ fehlt in der Tabelle (z. B. neu vergebene PLZ) → Wert der geografisch nächsten PLZ der
   Tabelle, höchstens ``NACHBAR_MAX_KM`` entfernt (Status ``nachbar``, mit Angabe der PLZ und Entfernung).
3. Keine Tabelle bzw. kein Nachbar → Richtwert der Klimaregion aus v6.9.1 (Status ``richtwert``),
   deutlich gekennzeichnet und manuell überschreibbar.
"""

from __future__ import annotations

import csv
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .standort import klimaregion

DATEN = Path(__file__).resolve().parent / "daten"
VERZEICHNIS_CSV = DATEN / "plz_verzeichnis.csv"
NORMTABELLE_CSV = DATEN / "normaussentemperatur_plz.csv"
NACHBAR_MAX_KM = 15.0
KLIMAKARTE_URL = "https://www.waermepumpe.de/werkzeuge/klimakarte/"


@dataclass(frozen=True)
class PlzEintrag:
    plz: str
    ort: str
    bundesland: str
    lat: float
    lon: float

    @property
    def text(self) -> str:
        return f"{self.plz} {self.ort}"


@dataclass(frozen=True)
class NormWert:
    plz: str
    ort: str
    theta_e: float  # Norm-Außentemperatur °C
    theta_m: float | None  # Jahresmitteltemperatur °C (nur aus der offiziellen Tabelle)
    status: str  # din | nachbar | richtwert
    quelle: str  # Kurztext für Anzeige und PDF
    hoehe: float | None = None  # m ü. NN (aus der Tabelle)
    klimazone: str = ""  # Klimazone (aus der Tabelle)

    @property
    def offiziell(self) -> bool:
        return self.status in ("din", "nachbar")


# ---------------------------------------------------------------- Daten laden
def _norm_text(s: str) -> str:
    s = (s or "").lower()
    for a, b in (("ü", "ue"), ("ö", "oe"), ("ä", "ae"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


@lru_cache(maxsize=1)
def verzeichnis() -> dict[str, PlzEintrag]:
    out: dict[str, PlzEintrag] = {}
    with VERZEICHNIS_CSV.open(encoding="utf-8") as f:
        for z in csv.DictReader(f, delimiter=";"):
            out[z["plz"]] = PlzEintrag(z["plz"], z["ort"], z["bundesland"], float(z["lat"]), float(z["lon"]))
    return out


def _zeilen_normtabelle(pfad: Path) -> list[dict]:
    if not pfad.exists():
        return []
    with pfad.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def lade_normtabelle(pfad: Path = NORMTABELLE_CSV) -> dict[str, tuple[float, float | None]]:
    """Offizielle Tabelle: PLZ → (θe, θm,e). Leeres dict, wenn (noch) nicht hinterlegt."""
    out: dict[str, tuple[float, float | None]] = {}
    for z in _zeilen_normtabelle(pfad):
        tm = (z.get("theta_m") or "").strip()
        out[z["plz"]] = (float(z["theta_e"]), float(tm) if tm else None)
    return out


@lru_cache(maxsize=1)
def normtabelle() -> dict[str, tuple[float, float | None]]:
    return lade_normtabelle()


@lru_cache(maxsize=1)
def normtabelle_zusatz() -> dict[str, dict[str, str]]:
    """Zusatzangaben je PLZ aus der Tabelle: ort, hoehe, klimazone, quelle."""
    return {z["plz"]: {k: (z.get(k) or "").strip() for k in ("ort", "hoehe", "klimazone", "quelle")}
            for z in _zeilen_normtabelle(NORMTABELLE_CSV)}


def tabellenstand() -> str:
    """Herkunft der hinterlegten Tabelle (z. B. „BWP-Klimakarte …, geladen am …“) oder ""."""
    zusatz = normtabelle_zusatz()
    return next(iter(zusatz.values()), {}).get("quelle", "") if zusatz else ""


def tabelle_vorhanden() -> bool:
    return bool(normtabelle())


# ---------------------------------------------------------------- PLZ prüfen und suchen
def plz_normalisieren(eingabe: str | int | None) -> str | None:
    """5-stellige PLZ aus einer Eingabe (auch „1067“ aus Excel → „01067“); None bei ungültiger Form."""
    if eingabe is None:
        return None
    if isinstance(eingabe, (int, float)):
        eingabe = str(int(eingabe))
    m = re.fullmatch(r"\s*(?:D-?\s*)?(\d{4,5})\s*", str(eingabe), flags=re.I)
    if not m:
        return None
    plz = m.group(1).zfill(5)
    return plz if "01001" <= plz <= "99998" else None


def eintrag(plz: str) -> PlzEintrag | None:
    return verzeichnis().get(plz_normalisieren(plz) or "")


def suche(eingabe: str, max_treffer: int = 12) -> list[PlzEintrag]:
    """PLZ, PLZ-Anfang oder Ortsname (auch „72622 Nürtingen“) → passende Einträge."""
    text = re.sub(r"^\s*D\s*-?\s*(?=\d)", "", (eingabe or "").strip(), flags=re.I)
    if not text:
        return []
    ziffern = re.match(r"\s*(\d{1,5})", text)
    rest = _norm_text(re.sub(r"^\s*\d{1,5}", "", text))
    vz = verzeichnis()
    if ziffern:
        z = ziffern.group(1)
        if len(z) == 5 or (len(z) == 4 and plz_normalisieren(z) in vz and not rest):
            e = vz.get(plz_normalisieren(z) or "")
            if e:
                return [e]
        treffer = [e for p, e in vz.items() if p.startswith(z)]
        if rest:
            treffer = [e for e in treffer if rest in _norm_text(e.ort)]
        return treffer[:max_treffer]
    q = _norm_text(text)
    exakt = [e for e in vz.values() if _norm_text(e.ort.split(" (")[0]) == q]
    teil = [e for e in vz.values() if e not in exakt and q in _norm_text(e.ort)]
    return (exakt + teil)[:max_treffer]


# ---------------------------------------------------------------- Norm-Außentemperatur
def _km(a: PlzEintrag, b: PlzEintrag) -> float:
    r = 6371.0
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dp, dl = p2 - p1, math.radians(b.lon - a.lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def de(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def norm_aussentemperatur(plz: str, tabelle: dict[str, tuple[float, float | None]] | None = None) -> NormWert | None:
    """Norm-Außentemperatur für eine PLZ; None, wenn die PLZ ungültig ist oder nicht existiert."""
    tab = normtabelle() if tabelle is None else tabelle
    p = plz_normalisieren(plz)
    if p is None:
        return None
    e = verzeichnis().get(p)
    if e is None and p not in tab:
        return None
    ort = e.ort if e else ""

    def zusatz(q: str) -> dict:
        z = normtabelle_zusatz().get(q, {}) if tabelle is None else {}
        h = z.get("hoehe", "")
        return {"hoehe": float(h) if h else None, "klimazone": z.get("klimazone", "")}

    if p in tab:
        te, tm = tab[p]
        if not ort:
            ort = (normtabelle_zusatz().get(p, {}) if tabelle is None else {}).get("ort", "")
        return NormWert(p, ort, te, tm, "din", "DIN/TS 12831-1", **zusatz(p))

    if tab and e is not None:
        vz = verzeichnis()
        kandidaten = [(_km(e, vz[q]), q) for q in tab if q in vz]
        if kandidaten:
            dist, q = min(kandidaten)
            if dist <= NACHBAR_MAX_KM:
                te, tm = tab[q]
                return NormWert(p, ort, te, tm, "nachbar",
                                f"DIN/TS 12831-1, Wert der Nachbar-PLZ {q} ({de(dist)} km)", **zusatz(q))

    kr = klimaregion(p)
    bereich = kr.von <= int(p) <= kr.bis
    quelle = (f"Richtwert Klimaregion {kr.name} (v6.9.1) – bitte prüfen" if bereich
              else "Standardwert (keine ortsgenaue Angabe) – bitte prüfen")
    return NormWert(p, ort, kr.norm_aussen, None, "richtwert", quelle)
