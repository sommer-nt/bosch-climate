"""Geräteauswahl: Inneneinheiten je Raum, Außengeräte-Kombinationen, Raumzuordnung."""

from __future__ import annotations

from dataclasses import dataclass

from .berechnung import GebaeudeLast, RaumLast, raum_last
from .modell import Projekt, Raum
from .produkte import Aussengeraet, Innengeraet, Produktdaten


# ---------------------------------------------------------------- Inneneinheiten
@dataclass
class Passung:
    ok: bool
    c: float  # Kühl-Deckung %
    h: float  # Heiz-Deckung %
    eval_pct: float


@dataclass
class IgStatus:
    cls: str  # ok | warn | orange | bad
    txt: str
    detail: str


def ig_passung(u: Innengeraet, l: RaumLast, betriebsart: str) -> Passung:
    c = u.cool / max(0.01, l.cool) * 100
    h = u.heat / max(0.01, l.heat) * 100
    if betriebsart == "heat":
        return Passung(h >= 100, c, h, h)
    return Passung(c >= 100, c, h, c)


def ig_kandidaten(raum: Raum, projekt: Projekt, pd: Produktdaten) -> list[Innengeraet]:
    l = raum_last(raum, projekt.einstellungen)
    ba = projekt.einstellungen.betriebsart
    passend = [
        u for u in pd.innen
        if (raum.ig_bauart == "auto" or u.type == raum.ig_bauart) and ig_passung(u, l, ba).ok
    ]
    return sorted(passend, key=lambda u: u.cool)


def ig_gewaehlt(raum: Raum, projekt: Projekt, pd: Produktdaten) -> Innengeraet | None:
    """Manuell gewählte Einheit oder kleinste passende (Automatik)."""
    if raum.ig_manuell:
        return pd.innen_nach_id(raum.ig_id)
    k = ig_kandidaten(raum, projekt, pd)
    return k[0] if k else None


def ig_status(raum: Raum, u: Innengeraet | None, projekt: Projekt) -> IgStatus:
    if u is None:
        return IgStatus("bad", "Passt nicht", "keine passende Einheit")
    f = ig_passung(u, raum_last(raum, projekt.einstellungen), projekt.einstellungen.betriebsart)
    detail = f"Kühlen {f.c:.0f}% · Heizen {f.h:.0f}%"
    if not f.ok:
        return IgStatus("bad", "Passt nicht", detail)
    if f.eval_pct <= 130:
        return IgStatus("ok", "Passend", detail)
    if f.eval_pct <= 180:
        return IgStatus("warn", "Passend, Überdimensionierung prüfen", detail)
    return IgStatus("orange", "Stark überdimensioniert", detail)


def aktuelle_inneneinheiten(projekt: Projekt, pd: Produktdaten) -> list[Innengeraet]:
    return [u for r in projekt.raeume if (u := ig_gewaehlt(r, projekt, pd))]


# ---------------------------------------------------------------- Außengeräte
@dataclass
class Summe:
    cool: float
    heat: float
    ports: int


@dataclass
class Kombination:
    id: str
    items: list[Aussengeraet]
    t: Summe
    score: float

    @property
    def label(self) -> str:
        return kombi_label(self.items)


def produkt_modus(projekt: Projekt, last: GebaeudeLast) -> str:
    s = projekt.einstellungen.systemart
    if s in ("single", "multi"):
        return s
    return "single" if last.rooms == 1 else "multi"


def geraete_pool(projekt: Projekt, last: GebaeudeLast, pd: Produktdaten) -> list[Aussengeraet]:
    m = produkt_modus(projekt, last)
    return sorted((d for d in pd.aussen if d.system == m), key=lambda d: d.cool)


def kombi_summe(items: list[Aussengeraet]) -> Summe:
    return Summe(sum(d.cool for d in items), sum(d.heat for d in items), sum(d.ports for d in items))


def kombi_label(items: list[Aussengeraet]) -> str:
    anzahl: dict[str, int] = {}
    namen: dict[str, str] = {}
    for d in items:
        anzahl[d.id] = anzahl.get(d.id, 0) + 1
        namen[d.id] = d.name
    return " + ".join(f"{n}× {namen[i]}" if n > 1 else namen[i] for i, n in anzahl.items())


def kombinationen(projekt: Projekt, last: GebaeudeLast, pd: Produktdaten) -> list[Kombination]:
    """Bis zu 6 wirtschaftliche Außengeräte-Lösungen, beste zuerst."""
    pool = geraete_pool(projekt, last, pd)
    combos: list[Kombination] = []

    def add(items: list[Aussengeraet]) -> None:
        t = kombi_summe(items)
        if t.ports >= last.rooms and t.cool >= last.cool and t.heat >= last.heat:
            reserve = t.cool - last.cool
            score = reserve * 2 + (t.ports - last.rooms) * 0.3 + len(items) * 0.8
            combos.append(Kombination("_".join(d.id for d in items), items, t, score))

    for d in pool:
        add([d])

    mehrere = projekt.einstellungen.systemart == "auto" and produkt_modus(projekt, last) == "multi"
    if mehrere and not combos:
        def rec(start: int, items: list[Aussengeraet], maximum: int) -> None:
            if items:
                add(items)
            if len(items) >= maximum:
                return
            for i in range(start, len(pool)):
                rec(i, items + [pool[i]], maximum)

        rec(0, [], 5)

    gesehen: set[str] = set()
    ergebnis = []
    for c in sorted(combos, key=lambda c: c.score):
        if c.label in gesehen:
            continue
        gesehen.add(c.label)
        ergebnis.append(c)
    return ergebnis[:6]


def gewaehlte_kombination(projekt: Projekt, combos: list[Kombination]) -> Kombination | None:
    return next((c for c in combos if c.id == projekt.gewaehltes_system), combos[0] if combos else None)


@dataclass
class Zuordnung:
    system: int
    outdoor: Aussengeraet
    rooms: list[Raum]


def raum_zuordnung(projekt: Projekt, combo: Kombination | None) -> list[Zuordnung]:
    """Verteilt die Räume der Reihe nach auf die Außengeräte (je nach Anschlüssen)."""
    if not combo or not combo.items:
        return []
    raeume = projekt.raeume
    res: list[Zuordnung] = []
    idx = 0
    for n, d in enumerate(combo.items):
        count = max(1, min(d.ports or len(raeume), len(raeume) - idx))
        teil = raeume[idx: idx + count]
        if teil:
            res.append(Zuordnung(n + 1, d, teil))
        idx += count
    if idx < len(raeume) and res:
        res[-1].rooms = res[-1].rooms + raeume[idx:]
    return res
