"""Produktdaten (DM-0.1): Außen- und Inneneinheiten."""

from __future__ import annotations

import json
from dataclasses import dataclass, fields
from functools import lru_cache
from pathlib import Path

PRODUKTE_JSON = Path(__file__).parent / "daten" / "produkte.json"

DETAIL_FELDER = [
    "article", "seer", "scop", "refrigerant", "soundOutdoor", "dimensions", "weight",
    "powerSupply", "opCool", "opHeat", "refrigerantCharge", "co2eq",
]


@dataclass(frozen=True)
class Aussengeraet:
    id: str
    name: str
    line: str
    system: str  # "single" | "multi"
    cool: float
    heat: float
    ports: int
    article: str | None = None
    seer: str | None = None
    scop: str | None = None
    refrigerant: str | None = None
    soundOutdoor: float | None = None
    dimensions: str | None = None
    weight: str | None = None
    powerSupply: str | None = None
    opCool: str | None = None
    opHeat: str | None = None
    refrigerantCharge: str | None = None
    co2eq: str | None = None
    dataQuality: str | None = None

    def meta_zeile(self) -> str:
        return (f"Art.-Nr. {self.article or '-'} · Effizienz {self.seer or '-'}/{self.scop or '-'} · "
                f"{self.refrigerant or '-'} · Außen {self.soundOutdoor or '-'} dB(A)")


@dataclass(frozen=True)
class Innengeraet:
    id: str
    name: str
    type: str  # Bauart
    cool: float
    heat: float
    sound: float | None = None


@dataclass(frozen=True)
class Produktdaten:
    aussen: tuple[Aussengeraet, ...]
    innen: tuple[Innengeraet, ...]

    def aussen_nach_id(self, id_: str) -> Aussengeraet:
        return next(d for d in self.aussen if d.id == id_)

    def innen_nach_id(self, id_: str | None) -> Innengeraet | None:
        return next((u for u in self.innen if u.id == id_), None)

    def vollstaendigkeit(self) -> dict:
        total = len(self.aussen) * len(DETAIL_FELDER)
        filled = sum(1 for d in self.aussen for f in DETAIL_FELDER if getattr(d, f))
        return {"filled": filled, "total": total, "pct": round(filled / total * 100) if total else 0}


def _bauen(cls, daten: dict):
    erlaubt = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in daten.items() if k in erlaubt})


def aus_json(text: str | bytes) -> Produktdaten:
    d = json.loads(text)
    return Produktdaten(
        aussen=tuple(_bauen(Aussengeraet, x) for x in d["aussengeraete"]),
        innen=tuple(_bauen(Innengeraet, x) for x in d["innengeraete"]),
    )


@lru_cache(maxsize=1)
def standard() -> Produktdaten:
    return aus_json(PRODUKTE_JSON.read_text(encoding="utf-8"))
