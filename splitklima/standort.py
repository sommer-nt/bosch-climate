"""Standort → Klimaregion (CLIM-0.1): Norm-Außentemperatur und Sommer-Auslegung."""

from __future__ import annotations

import re
from dataclasses import dataclass

ORTE = [
    ("70173", "Stuttgart"), ("72622", "Nürtingen"), ("72644", "Oberboihingen"),
    ("73240", "Wendlingen am Neckar"), ("73249", "Wernau (Neckar)"), ("73728", "Esslingen am Neckar"),
    ("80331", "München"), ("10115", "Berlin"),
]
DEFAULT_ORT = ("72622", "Nürtingen")


@dataclass(frozen=True)
class Klimaregion:
    von: int
    bis: int
    norm_aussen: float
    sommer: float
    name: str


KLIMAREGIONEN = [
    Klimaregion(70000, 79999, -12, 33, "Baden-Württemberg"),
    Klimaregion(80000, 89999, -16, 32, "Bayern"),
    Klimaregion(10000, 19999, -10, 31, "Nordost"),
]


def _norm(s: str) -> str:
    s = (s or "").lower()
    for a, b in (("ü", "ue"), ("ö", "oe"), ("ä", "ae"), ("ß", "ss")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def finde_ort(eingabe: str) -> tuple[str, str] | None:
    q = _norm(eingabe)
    if not q:
        return None
    ziffern = re.sub(r"\D", "", q)
    for z, n in ORTE:
        if _norm(f"{z} {n}") == q or _norm(n) == q or z == ziffern:
            return z, n
    for z, n in ORTE:
        if (len(ziffern) >= 3 and z.startswith(ziffern)) or q in _norm(n):
            return z, n
    return None


def klimaregion(plz: str) -> Klimaregion:
    """Klimaregion nach PLZ-Bereich; außerhalb der Tabelle → erste Region (wie v6.9.1)."""
    try:
        p = int(plz)
    except (TypeError, ValueError):
        return KLIMAREGIONEN[0]
    return next((k for k in KLIMAREGIONEN if k.von <= p <= k.bis), KLIMAREGIONEN[0])
