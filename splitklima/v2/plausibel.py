"""Plausibilitätsprüfung der Raumdaten (Lastenheft v0.7, F-028).

Warnungen lassen die Berechnung zu; Fehler (technisch unmögliche Eingaben, z. B. mehr Fenster als Wand) machen die
Konfiguration „unvollständig“. Grenzen stehen in ``parameter.PLAUSI``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import parameter as P
from ..berechnung import raum_last
from ..modell import Einstellungen, Raum
from ..sprache import T, zahl


@dataclass
class Meldung:
    stufe: str  # "warnung" | "fehler"
    text: str


def pruefen(r: Raum, e: Einstellungen) -> list[Meldung]:
    g = P.PLAUSI
    out: list[Meldung] = []
    A = r.flaeche or 0.0
    for w in r.waende:
        brutto = (w.laenge or 0) * (r.hoehe or 0)
        if (w.fenster or 0) > brutto + 1e-6:
            out.append(Meldung("fehler", T("Fensterfläche {f} m² nach {r} ist größer als die Wandfläche ({w} m²).",
                                           f=zahl(w.fenster, 1), r=w.ausrichtung, w=zahl(brutto, 1))))
    fenster = sum(w.fenster or 0 for w in r.waende) + sum(gr.flaeche or 0 for gr in r.fenstergruppen)
    if r.waende and A >= g["flaeche_fensterpruefung"] and fenster < g["fensteranteil_min"] * A:
        out.append(Meldung("warnung", T("Nur {f} m² Fenster bei {a} m² Grundfläche ({p} %) – üblich sind 10–25 %. "
                                        "Fensterflächen in der Wandtabelle prüfen.",
                                        f=zahl(fenster, 1), a=zahl(A, 1), p=zahl(100 * fenster / A, 0))))
    if not r.waende and not r.dach and r.lage != "inside":
        out.append(Meldung("warnung", T("Keine Außenflächen erfasst – nur innere Lasten. Lage im Gebäude prüfen.")))
    if A > g["flaeche_gross"]:
        out.append(Meldung("warnung", T("Ungewöhnlich großer Raum ({a} m²) – Fläche prüfen.", a=zahl(A, 0))))
    if A > 0 and e.betriebsart != "heat":
        spez = raum_last(r, e).cool * 1000 / A
        gewerbe = r.raumart in P.RAUMARTEN_GEWERBE
        minimum = g["kuehllast_min_gewerbe"] if gewerbe else g["kuehllast_min_wohnen"]
        if spez < minimum:
            out.append(Meldung("warnung", T("Spezifische Kühllast nur {x} W/m² – für „{art}“ ungewöhnlich niedrig "
                                            "(üblich ab etwa {m} W/m²). Fensterflächen, Nutzung und Personen prüfen.",
                                            x=zahl(spez, 0), art=T(r.raumart), m=zahl(minimum, 0))))
        elif spez > g["kuehllast_max"]:
            out.append(Meldung("warnung", T("Spezifische Kühllast {x} W/m² – ungewöhnlich hoch. Eingaben prüfen.",
                                            x=zahl(spez, 0))))
    return out
