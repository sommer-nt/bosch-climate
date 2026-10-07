"""Geräteauswahl Version 2: echte Bosch-Sets, Kombinationsregeln und Preise aus dem Katalog.

Die Heiz- und Kühllasten kommen unverändert aus dem Rechenkern (``berechnung.py``).
Hier wird nur entschieden, welche Geräte die Lasten wirtschaftlich decken:

* Single-Split: je Raum das günstigste Set, das die Raumlast deckt.
* Multi-Split: Außeneinheit + Inneneinheiten nach der Positivliste der zulässigen
  Kombinationen (Leistungsklassen) aus dem Katalog; die Außeneinheit muss die Gebäudelast
  der Gruppe (mit Gleichzeitigkeit) decken.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import permutations

from ..berechnung import gebaeude_last, raum_last
from ..modell import Projekt, Raum
from ..preise import Position, gesamtpreis, stueckliste_zusammenfassen
from .katalog import Artikel, Katalog

# Bauart-Werte aus v1 auf v2 abbilden
BAUART_ALIAS = {"Kassettengerät": "Deckenkassette", "Truhengerät": "Konsole", "auto": "", "": ""}
NR_INBETRIEBNAHME_AE = "8737804256"
NR_INBETRIEBNAHME_IE = "8737804260"
NR_AUFTRAGSPAUSCHALE = "7739607426"
NR_MSG1 = "7733702555"

MONTAGE_HINWEIS = ("Montagehinweise beruhen auf allgemeinen Fachregeln und dienen der überschlägigen Planung. "
                   "Maßgeblich sind die jeweils gültigen Montageanleitungen des Herstellers.")
# Aufstellort der Außeneinheit → Montagehinweise (Konsolen/Sockel: zubehoer.py)
AUFSTELLUNG = {"": "Noch offen", "wand": "Fassade / Wand", "boden": "Boden / Terrasse", "flachdach": "Flachdach"}
AUFSTELLUNG_HINWEISE = {
    "wand": ["Wandmontage: Tragfähigkeit der Wand und Körperschall zu angrenzenden Schlafräumen prüfen."],
    "boden": ["Bodenaufstellung vor dem Haus: Bodenkonsole mit Schwingungsdämpfern auf ebenem, tragfähigem Untergrund, "
              "Kondensat- und Abtauwasser frostsicher ableiten. Alternative auf Betonfundament: Dämpfungssockel-Set."],
    "flachdach": [
        "Flachdach: Außeneinheit auf Bodenkonsole mit Schwingungsdämpfern, auf Bautenschutzmatte bzw. "
        "Lastverteilplatten – die Dachabdichtung nicht durchdringen; Dachlast und Windsog prüfen lassen.",
        "Flachdach: Kondensat- und Abtauwasser zum Dachablauf führen, Vereisung der Dachfläche vermeiden; "
        "Mindestabstände zur Attika und zu Lichtkuppeln nach Montageanleitung einhalten.",
        "Flachdach: Leitungsführung durch die Dachhaut nur über Dachdurchführung oder Fassade; "
        "maximale Leitungslänge und Höhendifferenz der Außeneinheit beachten.",
        "Flachdach: sicheren Zugang für Wartung einplanen (Absturzsicherung nach DGUV/ASR A2.1).",
    ],
}


def bauart_wunsch(raum: Raum) -> str:
    return BAUART_ALIAS.get(raum.ig_bauart, raum.ig_bauart)


def farbwunsch(raum: Raum) -> str:
    """Farbwunsch gilt nur für Wandgeräte (Kassetten und Konsolen gibt es nur in Weiß)."""
    return raum.farbe if bauart_wunsch(raum) in ("", "Wandgerät") else ""


def farbgrenze(raum: Raum, kat: Katalog) -> tuple[float, float] | None:
    """Größte Kühl-/Heizleistung eines Wandgeräts bzw. Sets in der Wunschfarbe (None = keine Farbe/nicht im
    Sortiment). Beispiel: schwarz/silber gibt es nur als Climate 7000i bis 3,4 kW."""
    farbe = farbwunsch(raum)
    if not farbe:
        return None
    geraete = [a for a in (*kat.innen, *kat.sets) if a.farbe == farbe and a.verfuegbar]
    if not geraete:
        return None
    return max((a.kuehl or 0) for a in geraete), max((a.heiz or 0) for a in geraete)


@dataclass
class Bedarf:
    raum: Raum
    kuehl: float
    heiz: float


# Gerätelinien, die der Anwender bevorzugen kann ("" = wirtschaftlichste Lösung)
GERAETELINIEN = {
    "": "Wirtschaftlichste Lösung",
    "3200i": "Climate 3200i",
    "7000i": "Climate 7000i",
    "8000i": "Climate Class 8000i",
}
MAX_ZONEN = 12


def linie_passt(a: Artikel, linie: str) -> bool:
    """Passt der Artikel zur Wunsch-Gerätelinie? Kassetten/Konsolen gibt es nur als 5000i – immer erlaubt."""
    if not linie:
        return True
    if a.aussen_typ:  # komplettes Set: muss zur Linie gehören
        return linie in a.linie
    if a.bauart in ("Deckenkassette", "Konsole", "Truhe/Decke"):  # Multi-Inneneinheiten nur als 5000i
        return True
    if a.anschluesse:  # Multi-Außeneinheit
        return {"7000i": "7000 M", "3200i": "5000 M"}.get(linie, "§") in a.linie
    return linie in a.linie


def _teilraum(r: Raum, k: int, i: int) -> Raum:
    """Raum in k gleich große Zonen teilen (Fläche, Wände, Fenster, Dach anteilig)."""
    t = r.model_copy(deep=True)
    t.name = f"{r.name} · Zone {i}/{k}"
    t.flaeche = r.flaeche / k
    t.dachflaeche = (r.dachflaeche or 0) / k
    for w in t.waende:
        w.laenge, w.fenster = w.laenge / k, w.fenster / k
    for g in t.fenstergruppen:
        g.flaeche = g.flaeche / k
    return t


LARGE_SPLIT = "Climate 5000i L"


def ist_large(a: Artikel) -> bool:
    return a.linie == LARGE_SPLIT


def set_bauart(s: Artikel) -> str:
    return s.bauart or "Wandgerät"


def _max_einheit(r: Raum, kat: Katalog, linie: str, mit_large: bool = True) -> tuple[float, float]:
    """Größte Kühl-/Heizleistung, die ein einzelnes Gerät/Set in diesem Raum haben kann (Bauartwunsch, Linie)."""
    wunsch = bauart_wunsch(r)
    geraete = [u for u in kat.innen if not wunsch or u.bauart == wunsch]
    geraete += [s for s in kat.sets if (not wunsch or set_bauart(s) == wunsch) and (mit_large or not ist_large(s))]
    passend = [u for u in geraete if linie_passt(u, linie)] or geraete
    if not passend:
        return 0.0, 0.0
    return (max((u.kuehl or 0) for u in passend), max((u.heiz or 0) for u in passend))


def bedarfe(projekt: Projekt, kat: Katalog | None = None, mit_large: bool = False) -> list[Bedarf]:
    """Lasten je Raum aus dem Rechenkern. Mit Katalog: Räume, die kein einzelnes Gerät decken kann
    (z. B. Werkstatt, Halle), werden in Zonen mit je einem Innengerät aufgeteilt."""
    e = projekt.einstellungen
    kuehl_rel, heiz_rel = _relevant(projekt)
    out = []
    for r in projekt.raeume:
        l = raum_last(r, e)
        if kat is None:
            out.append(Bedarf(r, l.cool, l.heat))
            continue
        k_max, h_max = _max_einheit(r, kat, projekt.geraetelinie, mit_large)
        grenze = farbgrenze(r, kat)
        if grenze:  # Farbwunsch: lieber zwei Geräte in Wunschfarbe als eins in Weiß
            k_max, h_max = min(k_max, grenze[0]) or k_max, min(h_max, grenze[1]) or h_max
        if k_max <= 0:
            out.append(Bedarf(r, l.cool, l.heat))
            continue
        k = 1
        while k < MAX_ZONEN:
            teil = l if k == 1 else raum_last(_teilraum(r, k, 1), e)
            if not ((kuehl_rel and teil.cool > k_max) or (heiz_rel and teil.heat > h_max)):
                break
            k += 1
        if k == 1:
            out.append(Bedarf(r, l.cool, l.heat))
        else:
            for i in range(1, k + 1):
                t = _teilraum(r, k, i)
                lt = raum_last(t, e)
                out.append(Bedarf(t, lt.cool, lt.heat))
    return out


def _relevant(projekt: Projekt) -> tuple[bool, bool]:
    ba = projekt.einstellungen.betriebsart
    return ba in ("both", "cool"), ba in ("both", "heat")


@dataclass
class Teilsystem:
    bezeichnung: str
    art: str  # "single" | "multi"
    raeume: list[Raum]
    last_kuehl: float
    last_heiz: float
    set: Artikel | None = None
    aussen: Artikel | None = None
    innen: list[tuple[Raum, Artikel]] = field(default_factory=list)
    hinweise: list[str] = field(default_factory=list)

    @property
    def gedeckt(self) -> bool:
        return self.set is not None or (self.aussen is not None and len(self.innen) == len(self.raeume))

    @property
    def leistung_kuehl(self) -> float:
        g = self.set or self.aussen
        return (g.kuehl or 0.0) if g else 0.0

    @property
    def leistung_heiz(self) -> float:
        g = self.set or self.aussen
        return (g.heiz or 0.0) if g else 0.0

    @property
    def geraete_text(self) -> str:
        if self.set:
            return self.set.typ
        if self.aussen:
            return f"{self.aussen.typ} + " + ", ".join(u.typ for _, u in self.innen)
        return "keine passende Lösung"

    @property
    def schall_aussen(self) -> float | None:
        g = self.set or self.aussen
        return g.schall_aussen if g else None

    def positionen(self) -> list[Position]:
        if self.set:
            return [Position("set", self.set.bestellnr, self.set.typ, self.set.bestellnr, 1, self.set.preis)]
        pos = []
        if self.aussen:
            pos.append(Position("aussen", self.aussen.bestellnr, self.aussen.typ, self.aussen.bestellnr, 1,
                                self.aussen.preis))
        for _, u in self.innen:
            pos.append(Position("innen", u.bestellnr, u.typ, u.bestellnr, 1, u.preis))
        return pos

    def artikel(self) -> list[Artikel]:
        if self.set:
            return [self.set]
        return ([self.aussen] if self.aussen else []) + [u for _, u in self.innen]


# ---------------------------------------------------------------- Single-Split
def single_set(b: Bedarf, kat: Katalog, projekt: Projekt, mit_large: bool = False
               ) -> tuple[Artikel | None, list[str]]:
    """Günstigstes Set für einen Raum (Bauartwunsch beachtet; Large-Split nur, wenn erlaubt)."""
    kuehl_rel, heiz_rel = _relevant(projekt)
    wunsch = bauart_wunsch(b.raum)

    def deckt(s: Artikel) -> bool:
        if kuehl_rel and (s.kuehl is None or s.kuehl < b.kuehl):
            return False
        if heiz_rel and (s.heiz is None or s.heiz < b.heiz):
            return False
        return True

    alle = [s for s in kat.sets if deckt(s) and (not wunsch or set_bauart(s) == wunsch)
            and (mit_large or not ist_large(s))]
    if not alle:
        art = f" als {wunsch}" if wunsch else ""
        return None, [f"{b.raum.name}: Kein Single-Split-Set{art} deckt {b.kuehl:.2f} kW Kühl-/"
                      f"{b.heiz:.2f} kW Heizlast."]
    linie = projekt.geraetelinie
    kandidaten = [s for s in alle if linie_passt(s, linie)]
    linien_hinweis = []
    if linie and not kandidaten and alle:
        kandidaten = alle
        linien_hinweis = [f"{b.raum.name}: {GERAETELINIEN.get(linie, linie)} deckt die Last nicht – "
                          "andere Gerätelinie gewählt."]
    farbe = farbwunsch(b.raum)
    if linie and farbe and not any(s.farbe == farbe and s.verfuegbar for s in kandidaten):
        farbig = [s for s in alle if s.farbe == farbe and s.verfuegbar]
        if farbig:  # Farbwunsch des Raums geht vor der bevorzugten Gerätelinie
            kandidaten = farbig
            linien_hinweis = [f"{b.raum.name}: „{farbe}“ gibt es nicht als {GERAETELINIEN.get(linie, linie)} – "
                              f"{farbig[0].linie} gewählt."]
    stufen = [
        ([s for s in kandidaten if s.verfuegbar and (not farbe or s.farbe == farbe)], None),
        ([s for s in kandidaten if s.verfuegbar], f"{b.raum.name}: Farbe „{farbe}“ in passender Größe nicht "
                                                  "verfügbar – Standardfarbe gewählt."),
        (kandidaten, f"{b.raum.name}: Nur mit noch nicht lieferbarem Gerät lösbar."),
    ]
    for liste, hinweis in stufen:
        if liste:
            best = min(liste, key=lambda s: (s.preis or math.inf, s.kuehl or 0))
            notizen = [hinweis] if hinweis and (farbe or "lieferbar" in hinweis) else []
            if best.phasen == 3:
                notizen.append(f"{b.raum.name}: {best.typ} benötigt einen Drehstromanschluss (400 V).")
            if best.anzahl_ie > 1:
                notizen.append(f"{b.raum.name}: {best.anzahl_ie} Innengeräte an einer Außeneinheit "
                               f"({best.typ}).")
            return best, linien_hinweis + notizen
    return None, [f"{b.raum.name}: Kein Single-Split-Set deckt {b.kuehl:.2f} kW Kühl-/"
                  f"{b.heiz:.2f} kW Heizlast."]


def single_system(b: Bedarf, kat: Katalog, projekt: Projekt, bezeichnung: str | None = None,
                  mit_large: bool = False) -> Teilsystem:
    s, notizen = single_set(b, kat, projekt, mit_large)
    wunsch = bauart_wunsch(b.raum)
    if s is None and wunsch and wunsch != "Wandgerät":
        # kein passendes Set dieser Bauart – Kassette/Konsole als 1:1-System mit Multi-Außeneinheit
        ts = multi_system([b], kat, projekt, bezeichnung or b.raum.name)
        if ts.gedeckt:
            return ts
    return Teilsystem(bezeichnung or b.raum.name, "single", [b.raum], b.kuehl, b.heiz, set=s, hinweise=notizen)


# ---------------------------------------------------------------- Multi-Split
def _innen_optionen(b: Bedarf, ae: Artikel, kat: Katalog, projekt: Projekt, nur_verfuegbar: bool,
                    farbe_streng: bool, linie: str = "") -> list[Artikel]:
    _, heiz_rel = _relevant(projekt)
    nur_heizen = projekt.einstellungen.betriebsart == "heat"
    wunsch = bauart_wunsch(b.raum)
    out = []
    for u in kat.innen:
        if ae.typ not in u.aussen_kompatibel:
            continue
        if nur_verfuegbar and not u.verfuegbar:
            continue
        if not linie_passt(u, linie):
            continue
        if wunsch and u.bauart != wunsch:
            continue
        if farbe_streng and farbwunsch(b.raum) and u.farbe != farbwunsch(b.raum):
            continue
        # Inneneinheit nach Kühllast (bzw. Heizlast bei „nur Heizen“) – wie in v6.9.1
        wert, bedarf = (u.heiz, b.heiz) if nur_heizen else (u.kuehl, b.kuehl)
        if wert is None or wert < bedarf:
            continue
        if heiz_rel and u.heiz is None:
            continue
        out.append(u)
    return out


def _gruppenlast(raeume: list[Raum], projekt: Projekt) -> tuple[float, float]:
    teil = projekt.model_copy(deep=True)
    teil.raeume = [r.model_copy(deep=True) for r in raeume]
    last = gebaeude_last(teil)
    return last.cool, last.heat


def multi_system(gruppe: list[Bedarf], kat: Katalog, projekt: Projekt, bezeichnung: str) -> Teilsystem:
    """Günstigste zulässige Kombination aus Außeneinheit und Inneneinheiten für eine Raumgruppe."""
    kuehl_rel, heiz_rel = _relevant(projekt)
    n = len(gruppe)
    last_k, last_h = _gruppenlast([b.raum for b in gruppe], projekt)
    ts = Teilsystem(bezeichnung, "multi", [b.raum for b in gruppe], last_k, last_h)

    linien = [projekt.geraetelinie, ""] if projekt.geraetelinie else [""]
    for linie in linien:
        for nur_verfuegbar in (True, False):
            bestes = None
            for ae in kat.aussen:
                if nur_verfuegbar and not ae.verfuegbar:
                    continue
                if not linie_passt(ae, linie):
                    continue
                if not (ae.min_ie <= n <= (ae.anschluesse or 0)):
                    continue
                if kuehl_rel and (ae.kuehl or 0) < last_k:
                    continue
                if heiz_rel and (ae.heiz or 0) < last_h:
                    continue
                optionen = []
                farbe_gelockert = []
                for b in gruppe:
                    opt = _innen_optionen(b, ae, kat, projekt, nur_verfuegbar, farbe_streng=True, linie=linie)
                    if not opt and farbwunsch(b.raum):
                        opt = _innen_optionen(b, ae, kat, projekt, nur_verfuegbar, farbe_streng=False, linie=linie)
                        farbe_gelockert.append(b.raum.name)
                    optionen.append(opt)
                if any(not o for o in optionen):
                    continue
                for kombi in kat.kombinationen.get(ae.typ, ()):
                    if len(kombi) != n:
                        continue
                    for perm in set(permutations(kombi)):
                        wahl = []
                        for opt, klasse in zip(optionen, perm):
                            passend = [u for u in opt if u.klasse == klasse]
                            if not passend:
                                break
                            wahl.append(min(passend, key=lambda u: u.preis or math.inf))
                        else:
                            preis = (ae.preis or 0) + sum(u.preis or 0 for u in wahl)
                            schluessel = (len(farbe_gelockert), preis, ae.kuehl or 0)
                            if bestes is None or schluessel < bestes[0]:
                                bestes = (schluessel, ae, wahl, list(farbe_gelockert))
            if bestes:
                _, ae, wahl, gelockert = bestes
                ts.aussen = ae
                ts.innen = [(b.raum, u) for b, u in zip(gruppe, wahl)]
                if linie != projekt.geraetelinie:
                    ts.hinweise.append(f"{GERAETELINIEN.get(projekt.geraetelinie, projekt.geraetelinie)} "
                                       "als Multi-Split hier nicht möglich – andere Gerätelinie gewählt.")
                ts.hinweise += [f"{name}: Wunschfarbe nicht verfügbar – Standardfarbe gewählt."
                                for name in gelockert]
                if not nur_verfuegbar:
                    ts.hinweise.append("Enthält noch nicht lieferbare Geräte.")
                return ts
    ts.hinweise.append(f"Keine zulässige Multi-Split-Kombination für {n} Räume "
                       f"({last_k:.2f} kW Kühl-/{last_h:.2f} kW Heizlast).")
    return ts


def gruppen(bed: list[Bedarf], max_groesse: int = 5, max_kuehl: float = math.inf,
            max_heiz: float = math.inf) -> list[list[Bedarf]]:
    """Teilt Räume (nach Geschoss geordnet) in möglichst wenige, gleich große Gruppen mit höchstens
    ``max_groesse`` Innengeräten, deren Summenlast eine Außeneinheit noch decken kann."""
    geordnet = sorted(bed, key=lambda b: b.raum.geschoss)
    n = len(geordnet)
    for k in range(max(1, math.ceil(n / max_groesse)), n + 1):
        groesse = math.ceil(n / k)
        teile = [geordnet[i:i + groesse] for i in range(0, n, groesse)]
        if all(sum(b.kuehl for b in t) <= max_kuehl and sum(b.heiz for b in t) <= max_heiz for t in teile):
            return teile
    return [[b] for b in geordnet]


# ---------------------------------------------------------------- Konzepte
@dataclass
class Konzept:
    key: str
    name: str
    beschreibung: str
    teilsysteme: list[Teilsystem] = field(default_factory=list)
    empfohlen: bool = False
    zusatzhinweise: list[str] = field(default_factory=list)

    @property
    def gedeckt(self) -> bool:
        return bool(self.teilsysteme) and all(t.gedeckt for t in self.teilsysteme)

    @property
    def aussengeraete(self) -> int:
        return sum(1 for t in self.teilsysteme if t.gedeckt)

    @property
    def innengeraete(self) -> int:
        return sum((t.set.anzahl_ie if t.set else len(t.raeume)) for t in self.teilsysteme if t.gedeckt)

    def stueckliste(self) -> list[Position]:
        return stueckliste_zusammenfassen([p for t in self.teilsysteme for p in t.positionen()])

    @property
    def preis(self) -> float | None:
        return gesamtpreis(self.stueckliste()) if self.gedeckt else None

    @property
    def leistung_kuehl(self) -> float:
        return sum(t.leistung_kuehl for t in self.teilsysteme)

    @property
    def schall_max(self) -> float | None:
        werte = [t.schall_aussen for t in self.teilsysteme if t.schall_aussen]
        return max(werte) if werte else None

    @property
    def hinweise(self) -> list[str]:
        return self.zusatzhinweise + [h for t in self.teilsysteme for h in t.hinweise]

    @property
    def lieferhinweise(self) -> list[str]:
        return sorted({f"{a.typ}: {a.lieferhinweis}" for t in self.teilsysteme for a in t.artikel()
                       if a.lieferhinweis} | {f"{a.typ}: {a.datenfehler}" for t in self.teilsysteme
                                              for a in t.artikel() if a.datenfehler})

    @property
    def geraete_text(self) -> str:
        sets = [t.set.typ for t in self.teilsysteme if t.set]
        aes = [t.aussen.typ for t in self.teilsysteme if t.aussen]
        teile = []
        if aes:
            teile.append(" + ".join(aes))
        if sets:
            zaehl: dict[str, int] = {}
            for s in sets:
                zaehl[s] = zaehl.get(s, 0) + 1
            teile.append(" + ".join(f"{n}× {s}" if n > 1 else s for s, n in zaehl.items()))
        return " + ".join(teile) or "–"


def _geschosse(bed: list[Bedarf]) -> dict[str, list[Bedarf]]:
    g: dict[str, list[Bedarf]] = {}
    for b in bed:
        g.setdefault(b.raum.geschoss or "Gebäude", []).append(b)
    return g


def nur_als_set(b: Bedarf, kat: Katalog, linie: str = "") -> bool:
    """Wunschfarbe gibt es nur als Single-Split-Set (z. B. rot/anthrazit: Climate Class 8000i),
    nicht als Multi-Split-Inneneinheit → der Raum bekommt im Multi-Konzept ein eigenes Set."""
    farbe = farbwunsch(b.raum)
    if not farbe:
        return False
    if any(u.farbe == farbe and linie_passt(u, linie) for u in kat.innen):
        return False
    return any(s.farbe == farbe for s in kat.sets)


def _multi_teilsysteme(bed: list[Bedarf], kat: Katalog, projekt: Projekt, name: str,
                       mehrere: bool) -> list[Teilsystem]:
    out = []
    kuehl_rel, heiz_rel = _relevant(projekt)
    aes = [ae for ae in kat.aussen if linie_passt(ae, projekt.geraetelinie)] or list(kat.aussen)
    gs = gruppen(bed, max_groesse=max(ae.anschluesse or 1 for ae in aes), max_kuehl=max(ae.kuehl or 0 for ae in aes) if kuehl_rel else math.inf,
                 max_heiz=max(ae.heiz or 0 for ae in aes) if heiz_rel else math.inf)
    for j, g in enumerate(gs, 1):
        bez = name if len(gs) == 1 else (f"{name} ({j})" if mehrere else f"System {j}")
        out.append(single_system(g[0], kat, projekt, bez) if len(g) == 1 else multi_system(g, kat, projekt, bez))
    return out


def konzepte(projekt: Projekt, kat: Katalog, wunsch: str = "auto") -> list[Konzept]:
    bed = bedarfe(projekt, kat)
    if not bed:
        return []
    out: list[Konzept] = []
    multi_moeglich = len(bed) > 1
    # Räume, deren Wunschfarbe es nur als Set gibt, bekommen auch im Multi-Konzept ihr eigenes Set
    eigene_sets = [b for b in bed if nur_als_set(b, kat, projekt.geraetelinie)]
    rest = [b for b in bed if b not in eigene_sets]
    farb_sets = [single_system(b, kat, projekt) for b in eigene_sets]
    FARB_TEXT = " Räume mit Wunschfarbe erhalten ein eigenes Set in dieser Farbe."

    def gesamt(liste: list[Bedarf]) -> list[Teilsystem]:
        return _multi_teilsysteme(liste, kat, projekt, "Gebäude", mehrere=False) if liste else []

    def je_geschoss(liste: list[Bedarf]) -> list[Teilsystem]:
        return [t for name, g in _geschosse(liste).items() for t in _multi_teilsysteme(g, kat, projekt, name, True)]

    def farbtreu(k: Konzept, liste: list[Bedarf], bauen) -> Konzept:
        """Bleiben Farbwünsche im Multi-System offen (z. B. Farbgerät nur an kleinerer Außeneinheit),
        erhalten diese Räume ein eigenes Set in Wunschfarbe – sofern das die Farbwünsche erfüllt."""
        if not farbabweichungen(k):
            return k
        farbig = [b for b in liste if farbwunsch(b.raum)]
        neu = Konzept(k.key, k.name, k.beschreibung if FARB_TEXT in k.beschreibung else k.beschreibung + FARB_TEXT)
        neu.teilsysteme = bauen([b for b in liste if b not in farbig]) + farb_sets + [
            single_system(b, kat, projekt) for b in farbig]
        return neu if neu.gedeckt and farbabweichungen(neu) < farbabweichungen(k) else k

    if multi_moeglich and len(rest) > 1 and wunsch in ("auto", "multi"):
        k = Konzept("multi_gesamt", "Ein Multi-Split-System",
                    "Alle Räume an möglichst wenigen Außeneinheiten. Wenige Geräte an der Fassade, "
                    "längere Kältemittelleitungen.")
        k.teilsysteme = gesamt(rest) + farb_sets
        if farb_sets:
            k.beschreibung += FARB_TEXT
        out.append(farbtreu(k, rest, gesamt))

        etagen = _geschosse(rest)
        if len(etagen) > 1 and any(len(g) > 1 for g in etagen.values()):
            k = Konzept("multi_geschoss", "Multi-Split je Geschoss",
                        "Je Geschoss ein eigenes System mit kurzen Leitungswegen; ein einzelner Raum auf einer "
                        "Etage erhält ein Single-Split-Set.")
            k.teilsysteme = je_geschoss(rest) + farb_sets
            out.append(farbtreu(k, rest, je_geschoss))

    if wunsch in ("auto", "single") or not multi_moeglich or not out:
        k = Konzept("single", "Single-Split je Raum",
                    "Jeder Raum erhält ein eigenes Set aus Außen- und Inneneinheit – unabhängig und effizient, "
                    "aber mehr Außengeräte.")
        k.teilsysteme = [single_system(b, kat, projekt) for b in bed]
        if wunsch == "multi" and multi_moeglich:
            k.beschreibung = ("Die gewünschte Farbe gibt es nur als Single-Split-Set – deshalb erhält jeder Raum "
                              "ein eigenes Set.")
        out.append(k)

    # Large-Split (Ergänzungskatalog): große Räume mit wenigen leistungsstarken Anlagen bis 16 kW
    if wunsch in ("auto", "single") and any(ist_large(s) for s in kat.sets):
        bed_gross = bedarfe(projekt, kat, mit_large=True)
        teile = [single_system(b, kat, projekt, mit_large=True) for b in bed_gross]
        if any(t.set is not None and ist_large(t.set) for t in teile):
            k = Konzept("large", "Large-Split für große Räume",
                        "Leistungsstarke Einzelanlagen bis 16 kW mit Decken-, Truhen- oder Konsolengeräten – "
                        "auch als Twin/Triple mit mehreren Innengeräten an einer Außeneinheit. Weniger Geräte, "
                        "ideal für Werkstatt, Halle und Laden.")
            k.teilsysteme = teile
            out.append(k)

    geteilt = {}
    for b in bed:
        if " · Zone " in b.raum.name:
            geteilt[b.raum.name.split(" · Zone ")[0]] = b
    for r in projekt.raeume:
        grenze = farbgrenze(r, kat)
        if r.name in geteilt and grenze:
            n = sum(1 for b in bed if b.raum.name.startswith(f"{r.name} · Zone "))
            hinweis = (f"{r.name}: „{farbwunsch(r)}“ gibt es bis {grenze[0]:.1f} kW je Gerät – der Raum erhält "
                       f"{n} Geräte in dieser Farbe. Für ein einzelnes Gerät die Farbe auf „Keine Präferenz“ "
                       "stellen.").replace(".", ",", 1)
            for k in out:
                k.zusatzhinweise.append(hinweis)
    empfehlung_setzen(out, projekt.geraetelinie)
    return out


def farbabweichungen(k: Konzept) -> int:
    """Anzahl Räume, deren Wunschfarbe im Konzept nicht erfüllt ist."""
    n = 0
    for t in k.teilsysteme:
        geraete = [(r, t.set) for r in t.raeume] if t.set else t.innen
        n += sum(1 for r, u in geraete if farbwunsch(r) and u is not None and u.farbe != farbwunsch(r))
    return n


def linienabweichungen(k: Konzept, linie: str) -> int:
    """Anzahl Geräte, die nicht zur Wunsch-Gerätelinie gehören."""
    return sum(1 for t in k.teilsysteme for a in t.artikel() if not linie_passt(a, linie)) if linie else 0


def empfehlung_setzen(liste: list[Konzept], linie: str = "") -> None:
    """Erfüllte Farbwünsche und Wunsch-Gerätelinie zuerst, dann das wirtschaftlichste vollständige
    Konzept, bei Gleichstand weniger Außengeräte."""
    for k in liste:
        k.empfohlen = False
    kandidaten = [k for k in liste if k.gedeckt]
    if kandidaten:
        min(kandidaten, key=lambda k: (farbabweichungen(k), linienabweichungen(k, linie),
                                       k.preis if k.preis is not None else math.inf,
                                       k.aussengeraete)).empfohlen = True


# ---------------------------------------------------------------- Optionale Leistungen
def optionale_leistungen(konzept: Konzept, kat: Katalog) -> list[Position]:
    """Inbetriebnahme durch den Bosch-Kundendienst – nicht im Gerätepreis enthalten
    (Zubehör und Montagematerial: siehe ``zubehoer.py``)."""
    pos: list[Position] = []

    def add(nr: str, menge: int, art: str = "leistung"):
        z = kat.zubehoer_nr(nr)
        if z and menge:
            pos.append(Position(art, z.bestellnr, z.name, z.bestellnr, menge, z.preis))

    add(NR_AUFTRAGSPAUSCHALE, 1)
    add(NR_INBETRIEBNAHME_AE, konzept.aussengeraete)
    add(NR_INBETRIEBNAHME_IE, konzept.innengeraete)
    return pos


def aufstellungshinweise(projekt: Projekt, konzept: Konzept | None = None) -> list[str]:
    hinweise = list(AUFSTELLUNG_HINWEISE.get(projekt.aufstellung, []))
    if projekt.aufstellung in ("boden", "flachdach") and konzept and any(
            t.set and ist_large(t.set) for t in konzept.teilsysteme):
        hinweise.append("Large-Split-Außeneinheiten: Traglast von Konsole bzw. Sockel gegen das Gerätegewicht prüfen.")
    if hinweise:
        hinweise.append(MONTAGE_HINWEIS)
    return hinweise
