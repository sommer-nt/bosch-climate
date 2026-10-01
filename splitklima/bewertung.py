"""Bewertungen: Gesamtstatus, Heizanwendung, Datenqualität, Schall, Zubehör, Validierung."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .auswahl import (
    Kombination, aktuelle_inneneinheiten, ig_gewaehlt, ig_status, produkt_modus, raum_zuordnung,
)
from .berechnung import GebaeudeLast, raum_last
from .modell import Projekt, Raum, Wand
from .produkte import Aussengeraet, Produktdaten


# ---------------------------------------------------------------- Status
@dataclass
class Status:
    cls: str
    txt: str
    issues: int = 0
    warns: int = 0


def gesamtstatus(projekt: Projekt, combo: Kombination | None, pd: Produktdaten) -> Status:
    issues = warns = 0
    for r in projekt.raeume:
        u = ig_gewaehlt(r, projekt, pd)
        st = ig_status(r, u, projekt)
        if u is None or st.cls == "bad":
            issues += 1
        if st.cls in ("warn", "orange"):
            warns += 1
        c = raum_last(r, projekt.einstellungen)
        if c.wall_gross > 0 and c.win > c.wall_gross:
            issues += 1
    if combo is None:
        issues += 1
    if issues:
        return Status("bad", "Technisch nicht zulässig", issues, warns)
    if warns:
        return Status("warn", "Konfiguration mit Hinweisen", issues, warns)
    return Status("ok", "Konfiguration technisch plausibel", issues, warns)


@dataclass
class Klasse:
    cls: str
    label: str
    note: str


def heizanwendung(last: GebaeudeLast, combo: Kombination | None) -> Klasse:
    """B-024: Hauptheizung wird konservativ nicht vergeben (fehlende Tieftemperatur-Kennlinien)."""
    if combo is None or not last.heat:
        return Klasse("warn", "nicht bewertet", "Kein System oder keine Heizlast.")
    cov = combo.t.heat / last.heat
    if cov >= 1:
        return Klasse("warn", "Ergänzungsheizung",
                      "Nennleistung deckt die Heizlast rechnerisch. Eignung als Hauptheizung nicht "
                      "bewertet (fehlende Leistungsdaten bei Norm-Außentemperatur).")
    if cov >= 0.6:
        return Klasse("warn", "Übergangsheizung",
                      "Deckt einen Teil der Heizlast (Übergangszeit). Keine Hauptheizungs-Eignung.")
    return Klasse("err", "Heizung unterdimensioniert", "Nennleistung unter Heizlast.")


@dataclass
class Datenqualitaet:
    ratio: float
    cls: str
    txt: str
    individual: int
    total: int


def datenqualitaet(projekt: Projekt) -> Datenqualitaet:
    """B-032: Anteil individueller Eingaben gegenüber Standardwerten."""
    individual = total = 0
    for r in projekt.raeume:
        total += 5
        individual += (r.flaeche > 0 and r.flaeche != 22)
        individual += (r.hoehe > 0 and r.hoehe != 2.5)
        individual += bool(r.baualter)
        individual += (r.speicher != "mid")
        individual += (r.daemmung != "none")
    ratio = individual / total if total else 0.0
    cls, txt = ("ok", "hoch") if ratio >= 0.5 else ("warn", "mittel") if ratio >= 0.2 else ("err", "niedrig")
    return Datenqualitaet(ratio, cls, txt, individual, total)


def deckung_text(p: float, modus: str) -> str:
    if not math.isfinite(p):
        return "Keine Bewertung möglich."
    if p < 100:
        return (f"{modus}: Unterdeckung. Die verfügbare Geräteleistung liegt unter der berechneten Last; "
                "größere Geräteklasse, zusätzliche Inneneinheit oder anderes System prüfen.")
    if p <= 130:
        return (f"{modus}: Zielbereich. Die verfügbare Leistung deckt die Last mit moderater Reserve ab; "
                "dies ist für die überschlägige Vorauswahl der bevorzugte Bereich.")
    if p <= 180:
        return (f"{modus}: Reserve prüfen. Die Leistung ist deutlich größer als die Last; Komfort, "
                "Taktverhalten, Mindestleistung und Schall sollten fachlich geprüft werden.")
    return (f"{modus}: sehr hohe Reserve. Die Leistung ist stark über der Last; eine kleinere "
            "Geräteklasse, andere Raumaufteilung oder alternatives System sollte geprüft werden.")


# ---------------------------------------------------------------- Schall
def schall_bewertung(d: Aussengeraet) -> tuple[str, str]:
    s = d.soundOutdoor or 0
    if s <= 55:
        return "ok", "unauffällig"
    if s <= 60:
        return "warn", "Aufstellort prüfen"
    return "bad", "akustisch kritisch prüfen"


def leisere_alternative(d: Aussengeraet, last: GebaeudeLast, pd: Produktdaten) -> Aussengeraet | None:
    kand = [
        x for x in pd.aussen
        if x.system == d.system and x.id != d.id
        and (x.soundOutdoor or 99) < (d.soundOutdoor or 99)
        and x.ports >= last.rooms and x.cool >= last.cool and x.heat >= last.heat
    ]
    kand.sort(key=lambda x: ((x.soundOutdoor or 99), x.cool))
    return kand[0] if kand else None


@dataclass
class SchallZeile:
    bereich: str
    bezug: str
    geraet: str
    schall: str
    cls: str
    bewertung: str
    hinweis: str


def schall_uebersicht(projekt: Projekt, combo: Kombination | None, last: GebaeudeLast,
                      pd: Produktdaten) -> list[SchallZeile]:
    if combo is None:
        return []
    zeilen = []
    for i, d in enumerate(combo.items, 1):
        cls, txt = schall_bewertung(d)
        if cls == "ok":
            hinweis = "Aufstellung trotzdem projektbezogen prüfen."
        else:
            q = leisere_alternative(d, last, pd)
            hinweis = (f"Leisere Alternative prüfen: {q.name} ({q.soundOutdoor} dB(A)). " if q
                       else "Leisere Systemaufteilung oder kleineren Gerätetyp prüfen. ")
            hinweis += "Zusätzlich Schwingungsentkopplung, Aufstellort und Abschirmung prüfen."
        zeilen.append(SchallZeile("Außengerät", f"System {i}", d.name,
                                  f"{d.soundOutdoor or '-'} dB(A)", cls, txt, hinweis))
    for r in projekt.raeume:
        u = ig_gewaehlt(r, projekt, pd)
        if u:
            zeilen.append(SchallZeile("Raum", r.name, u.name, f"{u.sound or '-'} dB(A)", "ok",
                                      "akustisch geeignet", f"{u.sound or '-'} dB(A) im niedrigen Bereich."))
    return zeilen


# ---------------------------------------------------------------- Zubehör
@dataclass
class Zubehoer:
    id: str
    name: str
    article: str
    note: str
    qty: int = 1


def zubehoer(projekt: Projekt, combo: Kombination | None, pd: Produktdaten) -> dict[str, list[Zubehoer]]:
    inds = aktuelle_inneneinheiten(projekt, pd)
    outs = combo.items if combo else []
    cats: dict[str, list[Zubehoer]] = {"pflicht": [], "bedingt": [], "empfohlen": [], "optional": []}

    def add(cat, id_, name, article, note, qty=1):
        if not any(z.id == id_ for z in cats[cat]):
            cats[cat].append(Zubehoer(id_, name, article, note, qty))

    kassetten = sum(1 for u in inds if "Kassette" in u.type)
    if kassetten:
        add("pflicht", "g10-clc", "G 10 CLC Gateway-Anschluss Deckenkassette", "7733701951",
            "für Deckenkassetten-Anbindung berücksichtigen", kassetten)
    if any(o.system == "multi" for o in outs):
        add("bedingt", "adapter-38-14", 'Multi-Split Adapter 3/8" auf 1/4"', "7733703606",
            "bei abweichendem Rohranschluss prüfen")
        add("bedingt", "adapter-14-38", 'Multi-Split Adapter 1/4" auf 3/8"', "7733703603",
            "bei abweichendem Rohranschluss prüfen")
    add("empfohlen", "g10-3", "G 10-3 Internet-Gateway WLAN", "7736606771", "komfortable App-/Gateway-Anbindung")
    n = len(outs) or 1
    add("optional", "wandkonsole", "Wandkonsole Außengerät", "projektabhängig", "bei Fassadenmontage prüfen", n)
    add("optional", "bodenkonsole", "Bodenkonsole Außengerät", "projektabhängig",
        "bei Boden-/Flachdachaufstellung prüfen", n)
    add("optional", "schwingung", "Schwingungsdämpfer", "projektabhängig", "zur Körperschallentkopplung empfohlen", n)
    if any(o.refrigerant == "R290" for o in outs):
        add("bedingt", "r290", "R290-Aufstell- und Sicherheitsprüfung", "projektabhängig",
            "Mindestabstände und Aufstellanforderungen prüfen")
    return cats


ZUBEHOER_KATEGORIEN = {"pflicht": "Pflichtzubehör", "bedingt": "Bedingtes Zubehör",
                       "empfohlen": "Empfohlenes Zubehör", "optional": "Optionales Zubehör"}


# ---------------------------------------------------------------- Validierung
VALIDIERUNGSFAELLE = {
    "sleep-small": {"id": "V-101", "name": "Schlafzimmer klein", "cool": (0.35, 1.10), "heat": (0.25, 1.00),
                    "rooms": 1, "system": "single", "indoorMax": 2.6,
                    "note": "Niedrige Raumlast, kleinste passende Inneneinheit, keine harte Warnung."},
    "living-standard": {"id": "V-102", "name": "Wohnzimmer Standard", "cool": (1.40, 3.80), "heat": (0.90, 3.20),
                        "rooms": 1, "system": "single", "indoorMin": 2.0, "indoorMax": 5.3,
                        "note": "Mittlere Last, üblicherweise Geräteklasse 2,6 bis 3,5 kW, abhängig von "
                                "Sonnenschutz und Gebäude."},
    "attic-west": {"id": "V-103", "name": "Dachgeschoss Süd/West", "cool": (2.20, 6.20), "heat": (1.20, 4.50),
                   "rooms": 1, "system": "single", "indoorMin": 3.5,
                   "note": "Erhöhte Kühllast durch Dach/Solaranteil. Sonnenschutz muss Ergebnis sichtbar "
                           "beeinflussen."},
    "multi2": {"id": "V-202", "name": "Multi-Split zwei Räume", "cool": (1.80, 5.50), "heat": (1.10, 4.50),
               "rooms": 2, "system": "multi",
               "note": "Ein Außengerät, zwei Innengeräte, Raum-/Systemzuordnung sichtbar."},
    "multi5": {"id": "V-203", "name": "Multi-Split fünf Räume", "cool": (3.80, 11.50), "heat": (2.40, 9.50),
               "rooms": 5, "system": "multi",
               "note": "Alle Räume genau einmal zugeordnet, Anschlussbelegung plausibel."},
}


def wende_validierungsfall_an(projekt: Projekt, fall: str) -> None:
    """Setzt Räume und Systemart wie ``applyValidationCase`` in v6.9.1."""
    projekt.validierungsfall = fall
    if fall == "sleep-small":
        r = Raum(name="Schlafzimmer", raumart="Schlafzimmer", flaeche=12, hoehe=2.5, lage="outside",
                 waende=[Wand(ausrichtung="N", laenge=4, fenster=1.5)])
        projekt.raeume = [r]
        projekt.einstellungen.systemart = "single"
    elif fall == "living-standard":
        r = Raum(name="Wohnzimmer", flaeche=30, hoehe=2.5, lage="outside",
                 waende=[Wand(ausrichtung="S", laenge=6, fenster=6)])
        projekt.raeume = [r]
        projekt.einstellungen.systemart = "single"
    elif fall == "attic-west":
        r = Raum(name="Dachgeschoss", flaeche=35, hoehe=2.5, lage="attic_corner", dach=True, dachflaeche=35,
                 dachform="saddle_eastwest",
                 waende=[Wand(ausrichtung="W", laenge=5, fenster=8), Wand(ausrichtung="S", laenge=4, fenster=0)])
        projekt.raeume = [r]
        projekt.einstellungen.systemart = "single"
    elif fall == "multi2":
        projekt.raeume = [
            Raum(name="Wohnzimmer", flaeche=28, waende=[Wand(ausrichtung="S", laenge=6, fenster=5)]),
            Raum(name="Schlafzimmer", raumart="Schlafzimmer", flaeche=14,
                 waende=[Wand(ausrichtung="N", laenge=4, fenster=1.5)]),
        ]
        projekt.einstellungen.systemart = "multi"
    elif fall == "multi5":
        arten = ["Wohnzimmer", "Schlafzimmer", "Büro", "Kinderzimmer", "Küche"]
        projekt.raeume = [
            Raum(name=a, raumart=a, flaeche=[30, 14, 16, 18, 12][i],
                 waende=[Wand(ausrichtung=["S", "N", "O", "W", "S"][i], laenge=4 + i * 0.3,
                              fenster=[6, 1.5, 2, 2.5, 1.5][i])])
            for i, a in enumerate(arten)
        ]
        projekt.einstellungen.systemart = "multi"
    projekt.gewaehltes_system = None


@dataclass
class Validierung:
    key: str
    target: dict
    issues: list[str] = field(default_factory=list)
    warns: list[str] = field(default_factory=list)
    status: str = "ok"

    @property
    def status_text(self) -> str:
        return {"ok": "Bestanden", "warn": "Prüfen"}.get(self.status, "Außerhalb Soll")


def fmt_bereich(b) -> str:
    return f"{b[0]:.2f} - {b[1]:.2f} kW" if b else "-"


def validiere(projekt: Projekt, last: GebaeudeLast, combo: Kombination | None,
              pd: Produktdaten) -> Validierung | None:
    t = VALIDIERUNGSFAELLE.get(projekt.validierungsfall)
    if not t:
        return None
    v = Validierung(projekt.validierungsfall, t)
    if t.get("rooms") and last.rooms != t["rooms"]:
        v.issues.append(f"Raumanzahl {last.rooms}, erwartet {t['rooms']}.")
    if t.get("system") and produkt_modus(projekt, last) != t["system"]:
        v.issues.append(f"Systemart {produkt_modus(projekt, last)}, erwartet {t['system']}.")
    if not (t["cool"][0] <= last.cool <= t["cool"][1]):
        v.issues.append(f"Kühllast {last.cool:.2f} kW außerhalb Soll {fmt_bereich(t['cool'])}.")
    if not (t["heat"][0] <= last.heat <= t["heat"][1]):
        v.issues.append(f"Heizlast {last.heat:.2f} kW außerhalb Soll {fmt_bereich(t['heat'])}.")
    if combo is None:
        v.issues.append("Keine passende Außengeräte-/Systemlösung gefunden.")
    inds = aktuelle_inneneinheiten(projekt, pd)
    if t.get("indoorMin") and any(u.cool < t["indoorMin"] for u in inds):
        v.warns.append(f"Mindestens eine Inneneinheit kleiner als erwartete {t['indoorMin']:.1f} kW-Klasse.")
    if t.get("indoorMax") and any(u.cool > t["indoorMax"] for u in inds):
        v.warns.append(f"Mindestens eine Inneneinheit größer als erwartete {t['indoorMax']:.1f} kW-Klasse.")
    zugeordnet = sum(len(z.rooms) for z in raum_zuordnung(projekt, combo))
    if combo and zugeordnet != len(projekt.raeume):
        v.issues.append(f"Raum-/Systemzuordnung unvollständig ({zugeordnet}/{len(projekt.raeume)}).")
    v.status = "bad" if v.issues else "warn" if v.warns else "ok"
    return v
