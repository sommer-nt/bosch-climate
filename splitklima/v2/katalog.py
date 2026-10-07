"""Produktkatalog für Version 2 (aus der Produktdaten-Excel, siehe tools/katalog_import.py)."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field, fields, replace
from functools import lru_cache
from pathlib import Path

KATALOG_JSON = Path(__file__).resolve().parent.parent / "daten" / "katalog.json"
ERGAENZUNG_JSON = KATALOG_JSON.with_name("katalog_ergaenzung.json")

FARBEN = ["weiß", "silber", "schwarz", "anthrazit", "rot"]
BAUARTEN = ["Wandgerät", "Deckenkassette", "Konsole", "Truhe/Decke"]


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
    # Ergänzungskatalog (Large-Split)
    anzahl_ie: int = 1  # Twin 2, Triple 3, Double Twin 4 – alle Geräte im selben Raum
    phasen: int = 1  # 3 = Drehstrom 400 V
    max_abstand: float | None = None  # m zwischen Innen- und Außeneinheit
    bauart_code: str = ""  # 4CC, 4C, CF, CNE
    auslauf: bool = False  # im Ergänzungskatalog 09/2026 nicht mehr enthalten
    datenfehler: str = ""  # widersprüchliche Katalogdaten (nur Nennwerte verwendet)

    @property
    def lieferhinweis(self) -> str | None:
        if self.auslauf:
            return "Auslaufartikel – nicht mehr im Ergänzungskatalog 09/2026 (Preis 03/2026)"
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

    def ohne_auslauf(self) -> Katalog:
        """Katalog ohne Auslaufartikel (Standard in der Oberfläche; Schalter „Auslaufartikel anzeigen“)."""
        if id(self) not in _OHNE_AUSLAUF:
            _OHNE_AUSLAUF[id(self)] = replace(self, sets=tuple(a for a in self.sets if not a.auslauf),
                                              aussen=tuple(a for a in self.aussen if not a.auslauf),
                                              innen=tuple(a for a in self.innen if not a.auslauf))
        return _OHNE_AUSLAUF[id(self)]

    @property
    def auslaufartikel(self) -> tuple[Artikel, ...]:
        return tuple(a for a in (*self.sets, *self.aussen, *self.innen) if a.auslauf)


_OHNE_AUSLAUF: dict[int, Katalog] = {}


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


def zusammenfuehren(basis: dict, erg: dict) -> dict:
    """Ergänzungskatalog in den Gesamtkatalog übernehmen: neue Geräte, Preise per Bestellnummer
    (UVP 09/2026), Lieferstatus „ab Q3/2026“ → lieferbar, wenn der Artikel mit Preis gelistet ist."""
    d = copy.deepcopy(basis)
    preise = erg.get("preise", {})
    aktualisiert = 0
    for liste in ("sets", "aussen", "innen", "zubehoer"):
        for a in d[liste]:
            neu = preise.get(a.get("bestellnr"))
            if neu is None:
                continue
            if a.get("preis") != neu:
                a["preis"] = neu
                aktualisiert += 1
            if liste != "zubehoer" and (not a.get("verfuegbar") or "ab Q3" in (a.get("lieferstatus") or "")):
                a["verfuegbar"] = True
                a["lieferstatus"] = "lieferbar (Ergänzungskatalog 09/2026)"
    if preise:  # im Ergänzungskatalog nicht mehr gelistet → Auslaufartikel (Preis 03/2026)
        for liste in ("sets", "aussen", "innen"):
            for a in d[liste]:
                if a.get("bestellnr") and a["bestellnr"] not in preise:
                    a["auslauf"] = True
    vorhanden = {a["typ"] for liste in ("sets", "aussen", "innen") for a in d[liste]}
    for liste in ("sets", "aussen", "innen"):
        d[liste] += [copy.deepcopy(a) for a in erg.get(liste, []) if a["typ"] not in vorhanden]
    for neu_ae in erg.get("aussen", []):  # neue Außeneinheit wie die bisherige kleinste derselben Reihe
        if neu_ae["typ"] == "CL5000M 53/3 E":
            for ie in d["innen"]:
                komp = ie.setdefault("aussen_kompatibel", [])
                if "CL5000M 53/2 E" in komp and neu_ae["typ"] not in komp:
                    komp.append(neu_ae["typ"])
    bekannt = {z["bestellnr"] for z in d["zubehoer"]}
    d["zubehoer"] += [copy.deepcopy(z) for z in erg.get("zubehoer", []) if z["bestellnr"] not in bekannt]
    d["kombinationen"] = d["kombinationen"] + erg.get("kombinationen", [])
    d["pruefhinweise"] = list(d.get("pruefhinweise", [])) + list(erg.get("pruefhinweise", []))
    d["quelle"] = "Gesamtkatalog 03/2026 + Ergänzungskatalog 09/2026"
    d["preisbasis"] = (f"{erg.get('preisbasis', '')}; Artikel ohne Eintrag im Ergänzungskatalog: Stand 03/2026"
                       if erg.get("preisbasis") else d.get("preisbasis", ""))
    d["preise_aktualisiert"] = aktualisiert
    return d


@lru_cache(maxsize=1)
def standard() -> Katalog:
    basis = json.loads(KATALOG_JSON.read_text(encoding="utf-8"))
    if ERGAENZUNG_JSON.exists():
        basis = zusammenfuehren(basis, json.loads(ERGAENZUNG_JSON.read_text(encoding="utf-8")))
    return aus_json(json.dumps(basis))
