"""Anlagenvorschlag: Welche Split-Anlagen kommen für die Räume infrage?

Vergleicht drei Anlagenkonzepte mit dem unveränderten Rechenkern:
  1. Ein Multi-Split-System für alle Räume (bei Bedarf mehrere Außengeräte)
  2. Multi-Split je Geschoss (Geschoss mit nur einem Raum → Single-Split)
  3. Single-Split je Raum
und empfiehlt das wirtschaftlichste Konzept mit vollständiger Deckung (niedrigster Preis;
ohne Preise: wenigste Außengeräte).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .auswahl import Kombination, ig_gewaehlt, ig_status, kombinationen
from .berechnung import gebaeude_last
from .bewertung import zubehoer
from .modell import Projekt, Raum
from .preise import Position, Preisliste, gesamtpreis, stueckliste_zusammenfassen
from .produkte import Produktdaten


@dataclass
class Teilsystem:
    bezeichnung: str
    raeume: list[Raum]
    kombination: Kombination | None
    alternativen: list[Kombination]
    last_kuehlen: float
    last_heizen: float
    projekt: Projekt | None = None  # Teilprojekt mit diesen Räumen (für Inneneinheiten/Zubehör)

    @property
    def gedeckt(self) -> bool:
        return self.kombination is not None

    def positionen(self, pd: Produktdaten, preise: Preisliste) -> list[Position]:
        """Außengeräte, Inneneinheiten je Raum und Pflichtzubehör."""
        pos: list[Position] = []
        if self.kombination:
            for d in self.kombination.items:
                pos.append(Position("aussen", d.id, d.name, d.article or "-", 1, preise.preis("aussen", d.id)))
        if self.projekt is not None:
            for r in self.projekt.raeume:
                u = ig_gewaehlt(r, self.projekt, pd)
                if u:
                    pos.append(Position("innen", u.id, u.name, "-", 1, preise.preis("innen", u.id)))
            for z in zubehoer(self.projekt, self.kombination, pd)["pflicht"]:
                pos.append(Position("zubehoer", z.id, z.name, z.article, z.qty, preise.preis("zubehoer", z.id)))
        return pos

    def alle_raeume_versorgt(self, pd: Produktdaten) -> bool:
        return self.projekt is not None and all(ig_gewaehlt(r, self.projekt, pd) for r in self.projekt.raeume)

    @property
    def aussengeraete(self) -> int:
        return len(self.kombination.items) if self.kombination else 0

    @property
    def deckung_kuehlen(self) -> float:
        return self.kombination.t.cool / max(0.01, self.last_kuehlen) * 100 if self.kombination else 0.0

    @property
    def deckung_heizen(self) -> float:
        return self.kombination.t.heat / max(0.01, self.last_heizen) * 100 if self.kombination else 0.0

    @property
    def schall_max(self) -> float | None:
        werte = [d.soundOutdoor for d in self.kombination.items if d.soundOutdoor] if self.kombination else []
        return max(werte) if werte else None


@dataclass
class Konzept:
    key: str
    name: str
    beschreibung: str
    teilsysteme: list[Teilsystem] = field(default_factory=list)
    empfohlen: bool = False

    @property
    def gedeckt(self) -> bool:
        return bool(self.teilsysteme) and all(t.gedeckt for t in self.teilsysteme)

    @property
    def aussengeraete(self) -> int:
        return sum(t.aussengeraete for t in self.teilsysteme)

    @property
    def reserve_kuehlen(self) -> float:
        return sum(t.kombination.t.cool - t.last_kuehlen for t in self.teilsysteme if t.kombination)

    @property
    def schall_max(self) -> float | None:
        werte = [t.schall_max for t in self.teilsysteme if t.schall_max]
        return max(werte) if werte else None

    @property
    def geraete_text(self) -> str:
        return " + ".join(t.kombination.label for t in self.teilsysteme if t.kombination) or "–"

    def stueckliste(self, pd: Produktdaten, preise: Preisliste) -> list[Position]:
        return stueckliste_zusammenfassen([p for t in self.teilsysteme for p in t.positionen(pd, preise)])

    def preis(self, pd: Produktdaten, preise: Preisliste) -> float | None:
        return gesamtpreis(self.stueckliste(pd, preise))

    def vollstaendig(self, pd: Produktdaten) -> bool:
        """Außengeräte decken die Last und jeder Raum hat eine passende Inneneinheit."""
        return self.gedeckt and all(t.alle_raeume_versorgt(pd) for t in self.teilsysteme)


def _teilsystem(projekt: Projekt, bezeichnung: str, raeume: list[Raum], systemart: str,
                pd: Produktdaten) -> Teilsystem:
    teil = projekt.model_copy(deep=True)
    teil.raeume = [r.model_copy(deep=True) for r in raeume]
    teil.einstellungen.systemart = systemart
    teil.gewaehltes_system = None
    last = gebaeude_last(teil)
    combos = kombinationen(teil, last, pd)
    return Teilsystem(bezeichnung, raeume, combos[0] if combos else None, combos, last.cool, last.heat, teil)


def geschosse(raeume: list[Raum]) -> dict[str, list[Raum]]:
    gruppen: dict[str, list[Raum]] = {}
    for r in raeume:
        gruppen.setdefault(r.geschoss or "ohne Geschoss", []).append(r)
    return gruppen


def anlagenkonzepte(projekt: Projekt, pd: Produktdaten, preise: Preisliste | None = None,
                    wunsch: str = "auto") -> list[Konzept]:
    """Infrage kommende Konzepte. ``wunsch``: "auto" (alle), "single" oder "multi"."""
    raeume = projekt.raeume
    if not raeume:
        return []
    konzepte: list[Konzept] = []
    multi_moeglich = len(raeume) > 1

    if multi_moeglich and wunsch in ("auto", "multi"):
        k = Konzept("multi_gesamt", "Ein Multi-Split-System",
                    "Alle Räume an einem Multi-Split-System. Wenige Außengeräte, aber längere Kältemittelleitungen "
                    "über Geschosse hinweg.")
        k.teilsysteme.append(_teilsystem(projekt, "Gebäude", raeume, "auto", pd))
        konzepte.append(k)

    gruppen = geschosse(raeume)
    if multi_moeglich and wunsch in ("auto", "multi") and len(gruppen) > 1 \
            and any(len(g) > 1 for g in gruppen.values()):
        k = Konzept("multi_geschoss", "Multi-Split je Geschoss",
                    "Je Geschoss ein eigenes System. Kurze Leitungswege je Etage; Geschosse mit nur einem Raum "
                    "erhalten ein Single-Split-Gerät.")
        for g, liste in gruppen.items():
            k.teilsysteme.append(_teilsystem(projekt, g, liste, "auto", pd))
        konzepte.append(k)

    if wunsch in ("auto", "single") or not multi_moeglich:
        k = Konzept("single", "Single-Split je Raum",
                    "Jeder Raum erhält ein eigenes Außengerät. Höchste Effizienz und Unabhängigkeit, aber mehr "
                    "Außengeräte an der Fassade.")
        for r in raeume:
            k.teilsysteme.append(_teilsystem(projekt, r.name, [r], "single", pd))
        konzepte.append(k)

    empfehlung_setzen(konzepte, pd, preise)
    return konzepte


def empfehlung_setzen(konzepte: list[Konzept], pd: Produktdaten, preise: Preisliste | None) -> None:
    """Wirtschaftlichstes vollständiges Konzept: niedrigster Preis, dann wenigste Außengeräte."""
    for k in konzepte:
        k.empfohlen = False
    kandidaten = [k for k in konzepte if k.vollstaendig(pd)] or [k for k in konzepte if k.gedeckt]
    if not kandidaten:
        return

    def schluessel(k: Konzept):
        preis = k.preis(pd, preise) if preise else None
        return (preis if preis is not None else float("inf"), k.aussengeraete, k.reserve_kuehlen)

    min(kandidaten, key=schluessel).empfohlen = True


def inneneinheiten_uebersicht(projekt: Projekt, pd: Produktdaten) -> list[dict]:
    zeilen = []
    for r in projekt.raeume:
        u = ig_gewaehlt(r, projekt, pd)
        st = ig_status(r, u, projekt)
        zeilen.append({"raum": r, "geraet": u, "status": st})
    return zeilen
