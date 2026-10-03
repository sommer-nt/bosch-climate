"""Preise und Stückliste (wirtschaftliche Bewertung).

Preise kommen aus ``daten/preise.json``. Solange ``freigegeben`` false ist,
handelt es sich um Platzhalter – die Oberfläche kennzeichnet das.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PREISE_JSON = Path(__file__).parent / "daten" / "preise.json"


@dataclass(frozen=True)
class Preisliste:
    aussen: dict[str, float]
    innen: dict[str, float]
    zubehoer: dict[str, float]
    freigegeben: bool
    waehrung: str
    preisbasis: str

    def preis(self, art: str, id_: str) -> float | None:
        return {"aussen": self.aussen, "innen": self.innen, "zubehoer": self.zubehoer}[art].get(id_)


def aus_json(text: str | bytes) -> Preisliste:
    d = json.loads(text)
    return Preisliste(
        aussen={k: float(v) for k, v in d.get("aussengeraete", {}).items()},
        innen={k: float(v) for k, v in d.get("innengeraete", {}).items()},
        zubehoer={k: float(v) for k, v in d.get("zubehoer", {}).items()},
        freigegeben=bool(d.get("freigegeben", False)),
        waehrung=d.get("waehrung", "EUR"),
        preisbasis=d.get("preisbasis", ""),
    )


@lru_cache(maxsize=1)
def standard() -> Preisliste:
    return aus_json(PREISE_JSON.read_text(encoding="utf-8"))


@dataclass
class Position:
    art: str  # aussen | innen | zubehoer
    id: str
    name: str
    artikel: str
    menge: int
    einzelpreis: float | None

    @property
    def summe(self) -> float | None:
        return None if self.einzelpreis is None else self.einzelpreis * self.menge


def stueckliste_zusammenfassen(positionen: list[Position]) -> list[Position]:
    """Fasst gleiche Artikel zusammen (Reihenfolge: Außen, Innen, Zubehör)."""
    gesammelt: dict[tuple[str, str], Position] = {}
    for pos in positionen:
        key = (pos.art, pos.id)
        if key in gesammelt:
            gesammelt[key].menge += pos.menge
        else:
            gesammelt[key] = Position(pos.art, pos.id, pos.name, pos.artikel, pos.menge, pos.einzelpreis)
    reihenfolge = {"set": 0, "aussen": 0, "innen": 1, "zubehoer": 2, "leistung": 3}
    return sorted(gesammelt.values(), key=lambda p: reihenfolge[p.art])


def gesamtpreis(positionen: list[Position]) -> float | None:
    """Summe aller Positionen; None, wenn ein Preis fehlt."""
    if any(p.einzelpreis is None for p in positionen):
        return None
    return sum(p.summe for p in positionen)


def fmt_eur(betrag: float | None) -> str:
    if betrag is None:
        return "auf Anfrage"
    return f"{betrag:,.0f} €".replace(",", ".")
