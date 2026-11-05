"""Preisausweis und technischer Gesamtstatus (Lastenheft v0.7, S-005 und S-020 bis S-024).

Preisausweis in vier Kapiteln mit Zwischensummen: Inneneinheiten, Außeneinheiten (Komplett-Sets enthalten die
Inneneinheit), Zubehör, Inbetriebnahme/Service. Normalpositionen gehen in die Summe ein, Bedarfspositionen werden
bepreist, aber nicht summiert. Darunter Nettowert, Mehrwertsteuer und Endbetrag.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .. import parameter as P
from ..berechnung import raum_last
from ..modell import Projekt
from ..sprache import N_, T
from . import auswahl as A
from . import zubehoer as Z
from .katalog import Katalog

KAPITEL = [N_("Inneneinheiten"), N_("Außeneinheiten und Komplett-Sets"), N_("Zubehör und Montagematerial"),
           N_("Inbetriebnahme / Service")]


@dataclass
class Posten:
    name: str
    bestellnr: str
    menge: int
    einzelpreis: float | None
    bedarf: bool = False  # Bedarfsposition: bepreist, aber nicht in der Summe (S-022)

    @property
    def summe(self) -> float | None:
        return None if self.einzelpreis is None else self.einzelpreis * self.menge


@dataclass
class Kapitel:
    nr: int
    titel: str
    posten: list[Posten] = field(default_factory=list)

    @property
    def zwischensumme(self) -> float | None:
        normal = [x for x in self.posten if not x.bedarf]
        if any(x.einzelpreis is None for x in normal):
            return None
        return sum(x.summe or 0 for x in normal)


@dataclass
class Preisausweis:
    kapitel: list[Kapitel]
    mwst_satz: float = P.MWST_SATZ

    @property
    def vollstaendig(self) -> bool:
        return all(k.zwischensumme is not None for k in self.kapitel)

    @property
    def netto(self) -> float | None:
        return round(sum(k.zwischensumme for k in self.kapitel), 2) if self.vollstaendig else None

    @property
    def mwst(self) -> float | None:
        return None if self.netto is None else round(self.netto * self.mwst_satz, 2)

    @property
    def brutto(self) -> float | None:
        return None if self.netto is None else self.netto + self.mwst

    @property
    def bedarf_summe(self) -> float:
        return sum(x.summe or 0 for k in self.kapitel for x in k.posten if x.bedarf)


def _hinzu(liste: list[Posten], name: str, nr: str, menge: int, preis: float | None, bedarf: bool = False) -> None:
    for x in liste:
        if x.bestellnr == nr and x.bedarf == bedarf:
            x.menge += menge
            return
    liste.append(Posten(name, nr, menge, preis, bedarf))


def erstellen(projekt: Projekt, konzept: A.Konzept, kat: Katalog) -> Preisausweis:
    innen, aussen, zubehoer, service = (Kapitel(i + 1, t) for i, t in enumerate(KAPITEL))
    for t in konzept.teilsysteme:
        if t.set:
            _hinzu(aussen.posten, t.set.typ, t.set.bestellnr, 1, t.set.preis)
            continue
        if t.aussen:
            _hinzu(aussen.posten, t.aussen.typ, t.aussen.bestellnr, 1, t.aussen.preis)
        for _, u in t.innen:
            _hinzu(innen.posten, u.typ, u.bestellnr, 1, u.preis)
    for z in Z.gewaehlt(projekt, konzept, kat):
        _hinzu(zubehoer.posten, z.name, z.bestellnr, z.menge, z.einzelpreis)
    for x in A.optionale_leistungen(konzept, kat):
        _hinzu(service.posten, x.name, x.artikel, x.menge, x.einzelpreis, bedarf=not projekt.inbetriebnahme_einrechnen)
    return Preisausweis([innen, aussen, zubehoer, service])


# ---------------------------------------------------------------------- Gesamtstatus (S-005)
STATUS = {
    "ok": N_("Konfiguration technisch plausibel"),
    "hinweise": N_("Konfiguration mit Hinweisen"),
    "unvollstaendig": N_("Konfiguration unvollständig"),
    "unzulaessig": N_("Konfiguration technisch nicht zulässig"),
}


@dataclass
class Status:
    stufe: str  # ok | hinweise | unvollstaendig | unzulaessig
    gruende: list[str] = field(default_factory=list)

    @property
    def titel(self) -> str:
        return T(STATUS[self.stufe])


def gesamtstatus(projekt: Projekt, konzept: A.Konzept | None, kat: Katalog,
                 ungeprueft: int = 0) -> Status:
    """Eindeutiger Gesamtstatus der Konfiguration mit verständlichen Gründen."""
    if not projekt.raeume:
        return Status("unvollstaendig", [T("Noch keine Räume erfasst.")])
    if konzept is None or not konzept.gedeckt:
        return Status("unzulaessig", [T("Für diese Räume gibt es mit dem gewählten System keine zulässige "
                                        "Gerätekombination im Sortiment.")])
    gruende_unvollst: list[str] = []
    if not erstellen(projekt, konzept, kat).vollstaendig:
        gruende_unvollst.append(T("Für mindestens einen Artikel ist kein Preis hinterlegt („auf Anfrage“)."))
    if any((r.flaeche or 0) <= 0 or (r.hoehe or 0) <= 0 for r in projekt.raeume):
        gruende_unvollst.append(T("Mindestens ein Raum hat keine gültige Fläche oder Höhe."))
    if gruende_unvollst:
        return Status("unvollstaendig", gruende_unvollst)
    gruende: list[str] = []
    if ungeprueft:
        gruende.append(T("{n} Räume noch nicht geprüft (Raum öffnen, Werte kontrollieren).", n=ungeprueft))
    if not projekt.aufstellung:
        gruende.append(T("Aufstellort der Außeneinheit noch offen – Konsolen und Montagehinweise fehlen."))
    if konzept.lieferhinweise:
        gruende.append(T("Lieferhinweise zu {n} Artikel(n) beachten.", n=len(konzept.lieferhinweise)))
    if konzept.hinweise:
        gruende.append(T("{n} Hinweise zur Geräteauswahl.", n=len(konzept.hinweise)))
    if any(r.personen >= 10 and r.lueftung == "fenster" for r in projekt.raeume):
        gruende.append(T("Räume mit vielen Personen ohne Lüftungsanlage – Frischluft gesondert planen."))
    if any(raum_last(r, projekt.einstellungen).cool <= 0 and raum_last(r, projekt.einstellungen).heat <= 0
           for r in projekt.raeume):
        gruende.append(T("Mindestens ein Raum ohne Last – Eingaben prüfen."))
    return Status("hinweise" if gruende else "ok", gruende)
