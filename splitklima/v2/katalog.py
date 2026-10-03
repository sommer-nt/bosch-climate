"""Produktkatalog für Version 2 (aus der Produktdaten-Excel, siehe tools/katalog_import.py)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from functools import lru_cache
from pathlib import Path

KATALOG_JSON = Path(__file__).resolve().parent.parent / "daten" / "katalog.json"

FARBEN = ["weiß", "silber", "schwarz", "anthrazit", "rot"]
BAUARTEN = ["Wandgerät", "Deckenkassette", "Konsole"]


@dataclass(frozen=True)
class Artikel:
    typ: str
    bestellnr: str
    linie: str
    preis: float | None = None
    verfuegbar: bool = True
    lieferstatus: str = ""
    beschreibung: str | None = None
    effizienz: str | None = None
    seite: int | None = None
    kuehl: float | None = None
    kuehl_min: float | None = None
    kuehl_max: float | None = None
    heiz: float | None = None
    heiz_min: float | None = None
    heiz_max: float | None = None
    seer: float | None = None
    scop: float | None = None
    schall_aussen: float | None = None
    schall_innen_min: float | None = None
    schall_innen_max: float | None = None
    kaeltemittel: str | None = None
    datenquelle: str = "Katalog"
    bauart: str = ""
    farbe: str = ""
    hinweis: str | None = None
    # Set
    aussen_typ: str | None = None
    innen_typ: str | None = None
    # Außeneinheit
    anschluesse: int | None = None
    min_ie: int = 1
    einschraenkung: str | None = None
    # Inneneinheit
    klasse: float | None = None
    aussen_kompatibel: tuple[str, ...] = ()

    @property
    def lieferhinweis(self) -> str | None:
        s = self.lieferstatus.lower()
        if "ab q3" in s:
            return "verfügbar ab Q3/2026"
        if "vorrat" in s:
            return "nur solange Vorrat reicht"
        if "bis q3" in s:
            return "verfügbar bis Q3/2026"
        return None


@dataclass(frozen=True)
class Zubehoer:
    kategorie: str
    name: str
    bestellnr: str
    preis: float | None
    beschreibung: str | None = None
    passend: str | None = None
    seite: int | None = None


@dataclass(frozen=True)
class Katalog:
    sets: tuple[Artikel, ...]
    aussen: tuple[Artikel, ...]
    innen: tuple[Artikel, ...]
    kombinationen: dict[str, tuple[tuple[float, ...], ...]]
    zubehoer: tuple[Zubehoer, ...]
    merkmale: dict[str, tuple[str, ...]] = field(default_factory=dict)
    einsatz: tuple[dict, ...] = ()
    pruefhinweise: tuple[str, ...] = ()
    preisbasis: str = ""
    preise_freigegeben: bool = True
    quelle: str = ""

    def artikel(self, typ: str) -> Artikel | None:
        return next((a for a in (*self.sets, *self.aussen, *self.innen) if a.typ == typ), None)

    def zubehoer_nr(self, bestellnr: str) -> Zubehoer | None:
        return next((z for z in self.zubehoer if z.bestellnr == bestellnr), None)


def _artikel(d: dict) -> Artikel:
    erlaubt = {f.name for f in fields(Artikel)}
    werte = {k: v for k, v in d.items() if k in erlaubt}
    if "aussen_kompatibel" in werte:
        werte["aussen_kompatibel"] = tuple(werte["aussen_kompatibel"])
    return Artikel(**werte)


def aus_json(text: str | bytes) -> Katalog:
    d = json.loads(text)
    kombis: dict[str, list[tuple[float, ...]]] = {}
    for k in d["kombinationen"]:
        kombis.setdefault(k["aussen"], []).append(tuple(sorted(k["klassen"], reverse=True)))
    return Katalog(
        sets=tuple(_artikel(x) for x in d["sets"]),
        aussen=tuple(_artikel(x) for x in d["aussen"]),
        innen=tuple(_artikel(x) for x in d["innen"]),
        kombinationen={k: tuple(dict.fromkeys(v)) for k, v in kombis.items()},
        zubehoer=tuple(Zubehoer(**{k: z.get(k) for k in ("kategorie", "name", "bestellnr", "preis", "beschreibung",
                                                          "passend", "seite")}) for z in d["zubehoer"]),
        merkmale={k: tuple(v) for k, v in d.get("merkmale", {}).items()},
        einsatz=tuple(d.get("einsatz", [])),
        pruefhinweise=tuple(d.get("pruefhinweise", [])),
        preisbasis=d.get("preisbasis", ""),
        preise_freigegeben=bool(d.get("preise_freigegeben", True)),
        quelle=d.get("quelle", ""),
    )


@lru_cache(maxsize=1)
def standard() -> Katalog:
    return aus_json(KATALOG_JSON.read_text(encoding="utf-8"))
