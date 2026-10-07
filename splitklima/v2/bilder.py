"""Zuordnung Artikel → Produktbild (aus dem Katalog-PDF, siehe tools/katalog_bilder.py)."""

from __future__ import annotations

from pathlib import Path

from .katalog import Artikel

BILDER = Path(__file__).resolve().parent.parent / "daten" / "bilder"


def _farbe(a: Artikel) -> str:
    return (a.farbe or "weiß").replace("ß", "ss")


def _name(a: Artikel) -> str | None:
    linie = a.linie
    if linie == "Climate 5000i L":  # Large-Split (Ergänzungskatalog)
        basis = f"set_5000il_{(a.bauart_code or '4c').lower()}"
        zusatz = {2: "_twin", 3: "_triple", 4: "_double"}.get(a.anzahl_ie, "")
        if zusatz and (BILDER / f"{basis}{zusatz}.png").exists():
            return basis + zusatz
        return basis
    if a.aussen_typ:  # Set
        if "8000i" in linie:
            return f"set_8000i_{_farbe(a)}"
        if "7000i" in linie:
            return f"set_7000i_{_farbe(a)}"
        if "6000i" in linie:
            return "set_6000ip"
        if "3200i" in linie:
            return "set_3200i"
        if "3000i" in linie:
            return "set_3000i"
        return None
    if a.anschluesse:  # Multi-Außeneinheit
        return "ae_7000m" if "7000" in linie else "ae_5000m"
    if a.bauart == "Konsole":
        return "ie_konsole_5000i"
    if a.bauart == "Deckenkassette":
        return "ie_kassette_5001iu" if a.typ.startswith("CL5001") else "ie_kassette_5000i"
    if "7000i" in linie:
        return f"ie_7000i_{_farbe(a)}"
    if "3000i" in linie:
        return "ie_wand_3000i"
    return "ie_wand_3200i"


def bild(a: Artikel | None) -> Path | None:
    """Pfad zum Produktbild oder None, wenn keins vorhanden ist."""
    if a is None:
        return None
    name = _name(a)
    pfad = BILDER / f"{name}.png" if name else None
    return pfad if pfad and pfad.exists() else None


def bild_innen_set(a: Artikel) -> Path | None:
    """Nur die Inneneinheit eines Sets (für Raumkarten)."""
    if a.linie == "Climate 5000i L":
        return bild(a)
    linie, f = a.linie, _farbe(a)
    for name in ([f"ie_8000i_{f}"] if "8000i" in linie else [f"ie_7000i_{f}"] if "7000i" in linie
                 else ["ie_wand_3000i"] if "3000i" in linie else ["ie_wand_3200i"]):
        p = BILDER / f"{name}.png"
        if p.exists():
            return p
    return bild(a)
