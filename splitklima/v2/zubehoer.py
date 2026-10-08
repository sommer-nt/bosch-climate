"""Zubehör und Montagematerial der Version 2: Vorschlag aus dem gewählten Konzept, Mengen änderbar.

Grundlage: „Allgemeines Zubehör“ und gerätespezifisches Zubehör aus Gesamtkatalog 03/2026 und
Ergänzungskatalog 09/2026 (Preise 09/2026, sonst 03/2026). Der Vorschlag ist eine Planungshilfe –
Leitungslängen, Kondensatführung und Aufstellung bestimmt der Fachbetrieb vor Ort.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from pathlib import Path

from ..modell import Projekt
from ..preise import fmt_eur
from .auswahl import Konzept, ist_large
from .katalog import Artikel, Katalog

# Kältemittelleitungen (Doppelrohr-Pakete) nach Gasleitung: Länge in m → Bestell-Nr.
ROHRE = {
    '3/8"': {5: "8750501319", 10: "7733701500", 20: "7733701501"},  # 1/4" + 3/8": 2,5 und 3,5 kW
    '1/2"': {5: "7739838151", 10: "7733701502", 20: "7733701503"},  # 1/4" + 1/2": 5,3 kW
    '5/8"': {5: "7739838153", 10: "8738206697", 20: "7748000688"},  # 3/8" + 5/8": 7 kW
}
KLEMMRING = {'1/4"': "7738345078", '3/8"': "7738345079", '1/2"': "7738345080", '5/8"': "7738345081"}
NR_KABEL_KLEIN, NR_KABEL_GROSS = "7733701741", "7733704678"  # Kommunikationskabel 5,5 m (≤ 5,3 kW / 7 kW)
NR_SPIRALSCHLAUCH = "7738345076"  # Kondensat Ø 16 mm, Rolle 30 m
NR_PUMPE_WAND, NR_PUMPE_EINBAU = "7738345075", "7738346711"
NR_G10_3, NR_G10_4, NR_G10_CLC, NR_G10_CLC1 = "7736606771", "7733703987", "7733701951", "7733704066"
NR_MSG1 = "7733702555"
NR_WANDKONSOLE, NR_BODENKONSOLE = "7747222358", "7716161065"
NR_SOCKEL_450, NR_SOCKEL_600 = "7738347185", "7738347186"
SOCKEL_600_FUER = ("CL7000M 79/3", "CL5000M 105/4", "CL5000M 125/5")
ALTERNATIVE = {  # Hinweistext für Artikel, die nicht automatisch vorgeschlagen werden
    NR_SOCKEL_450: "Alternative zur Bodenkonsole: direkt auf Betonfundament, schallentkoppelt",
    NR_SOCKEL_600: "Alternative zur Bodenkonsole für CL7000M 79/3, CL5000M 105/4 und 125/5 auf Betonfundament",
    NR_PUMPE_WAND: "Optional: Kondensatpumpe unter wandhängenden Innengeräten",
    "7738345958": "Optional: Alternative zur Silent+ mini – Pumpe mit 800 mm Kabelkanal für Wandgeräte",
    NR_PUMPE_EINBAU: "Optional: Einbaupumpe für Konsolen und Truhen",
    NR_WANDKONSOLE: "Optional: Wandmontage der Außeneinheit",
    NR_BODENKONSOLE: "Optional: Boden- oder Flachdachaufstellung der Außeneinheit",
    "7733704064": "Optional: Kabelregler; Wandgeräte benötigen zusätzlich das Verbindungsmodul MC R",
    "7733701597": "Optional: potentialfreier Kontakt, externes Ein/Aus, Alarm (3000i, 3200i, 7000i)",
}
# im Ergänzungskatalog 09/2026 ersetzt → nicht mehr anbieten
ERSETZT = {"7733701903": "7733704064", "7738336975": "7738346711"}
# Basispakete (Set + Montagematerial + Konsole): Set-Typ → {Aufstellung: Bestell-Nr.}
BOPA = {"CL7000i-Set 26 E": {"boden": "7739625892", "wand": "7739624113"},
        "CL3200i-Set 26 WE": {"boden": "7739625891", "wand": "7739625457"}}

G10_3_HINWEIS = ("G 10-3 laut aktuellem Katalog bis Q4/2026 verfügbar. Nachfolgeprodukt für die verbleibenden "
                 "Gerätefamilien derzeit nicht eindeutig dokumentiert.")
VORKALKULATION = ("Zubehörmengen dienen als automatische Vorkalkulation und müssen projektbezogen geprüft werden.")

GATEWAYS = {NR_G10_3, NR_G10_4, NR_G10_CLC, NR_G10_CLC1}
BOPA_NRS = {nr for d in BOPA.values() for nr in d.values()}
# Produktbild je Bestell-Nr. (daten/bilder/zubehoer/<name>.png, aus den Katalogen exportiert)
BILD = {
    **{nr: "doppelrohr" for d in ROHRE.values() for nr in d.values()},
    **{nr: "klemmring" for nr in KLEMMRING.values()},
    **{nr: "adapter" for nr in ("7733703606", "7733703603", "7733703604", "7733703607", "7733703605")},
    NR_KABEL_KLEIN: "kabel", NR_KABEL_GROSS: "kabel", "7733701597": "mcr", "7733704064": "regler",
    NR_SPIRALSCHLAUCH: "spiralschlauch", NR_PUMPE_WAND: "pumpe_mini", NR_PUMPE_EINBAU: "pumpe_einbau",
    "7738345958": "pumpe_kanal", NR_G10_3: "g10_3", NR_G10_4: "g10_4", NR_G10_CLC: "g10_clc", NR_G10_CLC1: "g10_clc",
    NR_MSG1: "msg1", NR_WANDKONSOLE: "wandkonsole", NR_BODENKONSOLE: "bodenkonsole",
    NR_SOCKEL_450: "sockel_450", NR_SOCKEL_600: "sockel_600",
}
BILD_ORDNER = Path(__file__).resolve().parent.parent / "daten" / "bilder" / "zubehoer"


def bild(bestellnr: str) -> Path | None:
    """Produktbild eines Zubehörartikels (Basispakete: Bild des Sets)."""
    if bestellnr in BOPA_NRS:
        name = "../set_7000i_weiss" if bestellnr in BOPA["CL7000i-Set 26 E"].values() else "../set_3200i"
    else:
        name = BILD.get(bestellnr)
    pfad = BILD_ORDNER / f"{name}.png" if name else None
    return pfad if pfad and pfad.exists() else None


GRUPPEN = ["Aufstellung Außeneinheit", "Kältemittelleitung", "Elektrik und Kommunikation", "Kondensat",
           "Steuerung und App", "Förderung", "Adapter und Verschraubungen", "Pakete"]
GRUPPE = {
    NR_WANDKONSOLE: 0, NR_BODENKONSOLE: 0, NR_SOCKEL_450: 0, NR_SOCKEL_600: 0,
    **{nr: 1 for d in ROHRE.values() for nr in d.values()},
    NR_KABEL_KLEIN: 2, NR_KABEL_GROSS: 2, "7733701597": 2,
    NR_SPIRALSCHLAUCH: 3, NR_PUMPE_WAND: 3, NR_PUMPE_EINBAU: 3, "7738345958": 3,
    NR_G10_3: 4, NR_G10_4: 4, NR_G10_CLC: 4, NR_G10_CLC1: 4, "7733704064": 4,
    NR_MSG1: 5,
    **{nr: 6 for nr in KLEMMRING.values()},
    **{nr: 6 for nr in ("7733703606", "7733703603", "7733703604", "7733703607", "7733703605")},
    **{nr: 7 for d in BOPA.values() for nr in d.values()},
}


@dataclass
class ZubehoerZeile:
    gruppe: str
    bestellnr: str
    name: str
    einzelpreis: float | None
    vorschlag: int
    menge: int
    grund: str = ""
    gesperrt: str = ""  # Grund, warum der Artikel für dieses Konzept nicht in Frage kommt (z. B. WLAN integriert)

    @property
    def summe(self) -> float | None:
        return None if self.einzelpreis is None else self.einzelpreis * self.menge


@dataclass
class _Ie:
    raum: str
    geraet: Artikel
    kuehl: float
    bauart: str  # Wandgerät | Deckenkassette | Konsole | Truhe/Decke


def _innengeraete(k: Konzept) -> list[_Ie]:
    out = []
    for t in k.teilsysteme:
        if t.set:
            n = max(t.set.anzahl_ie, 1)
            bauart = t.set.bauart or {"CF": "Truhe/Decke", "CNE": "Konsole"}.get(t.set.bauart_code or "",
                                                                                   "Deckenkassette" if ist_large(t.set) else "Wandgerät")
            for r in t.raeume:
                out += [_Ie(r.name, t.set, (t.set.kuehl or 0) / n, bauart) for _ in range(n)]
        else:
            out += [_Ie(r.name, u, u.kuehl or 0, u.bauart or "Wandgerät") for r, u in t.innen if u]
    return out


def _aussengeraete(k: Konzept) -> list[Artikel]:
    return [t.set if t.set else t.aussen for t in k.teilsysteme if t.set or t.aussen]


def rohrklasse(kw: float) -> str | None:
    """Gasleitung nach Nennleistung (Doppelrohr-Pakete des Katalogs nur bis 7 kW)."""
    if kw <= 3.6:
        return '3/8"'
    if kw <= 5.5:
        return '1/2"'
    if kw <= 7.5:
        return '5/8"'
    return None


def rohr_pakete(laenge: float, kat: Katalog, klasse: str) -> list[int]:
    """Paketlängen 5/10/20 m, die die Leitungslänge abdecken: möglichst wenige Stücke (jede Verbindungsstelle
    ist eine zusätzliche Lötstelle bzw. Verschraubung), bei gleicher Stückzahl die günstigste."""
    preise = {l: (kat.zubehoer_nr(nr).preis if kat.zubehoer_nr(nr) else None) or math.inf
              for l, nr in ROHRE[klasse].items()}
    beste: tuple[float, list[int]] = (math.inf, [5])
    for n in range(1, 5):
        for combo in itertools.combinations_with_replacement(sorted(preise), n):
            if sum(combo) >= laenge:
                preis = sum(preise[l] for l in combo)
                if beste[0] == math.inf or (len(combo), preis) < (len(beste[1]), beste[0]):
                    beste = (preis, list(combo))
    return beste[1]


def _gateway(ie: _Ie) -> list[tuple[str, str]]:
    a, typ = ie.geraet, ie.geraet.typ
    if "7000i" in a.linie or "8000i" in a.linie:
        return []  # WLAN integriert
    if a.linie == "Climate 5000i L":
        extra = [(NR_G10_CLC1, "CF-Gerät: Gateway-Anschluss nötig")] if ie.bauart == "Truhe/Decke" else []
        return [(NR_G10_4, "")] + extra
    if typ.startswith("CL5000iM 4CC"):
        return [(NR_G10_3, G10_3_HINWEIS),
                (NR_G10_CLC, "Kassette CL5000iM 4CC: Gateway-Anschluss nötig")]
    if "3000i" in a.linie:
        return [(NR_G10_3, G10_3_HINWEIS)]
    return [(NR_G10_4, "")]


def vorschlag(projekt: Projekt, konzept: Konzept, kat: Katalog) -> tuple[dict[str, int], dict[str, str], list[str]]:
    """Vorgeschlagene Mengen je Bestell-Nr., Begründung je Bestell-Nr. und Planungshinweise."""
    mengen: dict[str, int] = {}
    grund: dict[str, list[str]] = {}
    hinweise: list[str] = []

    def add(nr: str, n: int, text: str = "") -> None:
        if n <= 0 or not kat.zubehoer_nr(nr):
            return
        mengen[nr] = mengen.get(nr, 0) + n
        if text and text not in grund.setdefault(nr, []):
            grund[nr].append(text)

    ies, aes = _innengeraete(konzept), _aussengeraete(konzept)
    laenge = max(projekt.leitungslaenge, 1.0)

    # Aufstellung der Außeneinheit
    for ae in aes:
        if projekt.aufstellung == "wand":
            add(NR_WANDKONSOLE, 1, "Aufstellort Fassade/Wand: 1 je Außeneinheit")
        elif projekt.aufstellung == "flachdach":
            add(NR_BODENKONSOLE, 1, "Aufstellort Flachdach: 1 je Außeneinheit, aufgeständert über Schnee/Wasser")
        elif projekt.aufstellung == "boden":
            add(NR_BODENKONSOLE, 1, "Aufstellort Boden: 1 je Außeneinheit")

    # Kältemittelleitung, Kommunikationskabel, Klemmringverschraubungen je Innengerät
    ohne_rohr = []
    for ie in ies:
        klasse = rohrklasse(ie.kuehl)
        if klasse is None:
            ohne_rohr.append(ie.raum)
        else:
            for l in rohr_pakete(laenge, kat, klasse):
                add(ROHRE[klasse][l], 1, f"Grundausstattung: Kältemittelleitung {laenge:g} m je Innengerät")
            if projekt.boerdelfrei:
                fluessig = '3/8"' if klasse == '5/8"' else '1/4"'
                add(KLEMMRING[fluessig], 2, "Bördelfrei gewählt: 2 je Leitung und Seite")
                add(KLEMMRING[klasse], 2, "Bördelfrei gewählt: 2 je Leitung und Seite")
        if ie.kuehl <= 5.5:
            add(NR_KABEL_KLEIN, math.ceil(laenge / 5.5), "Grundausstattung: Steuerleitung je Innengerät (5,5 m je Kabel)")
        elif ie.kuehl <= 7.5:
            add(NR_KABEL_GROSS, math.ceil(laenge / 5.5), "Grundausstattung: Steuerleitung 2,5 mm² für 7-kW-Geräte")
    if ohne_rohr:
        hinweise.append("Kältemittelleitung für Geräte über 7 kW (" + ", ".join(sorted(set(ohne_rohr)))
                        + ") nicht als Paket im Katalog – Kupferrohr und Kabel bauseits nach Montageanleitung.")

    # Kondensat: Wandgeräte/Konsolen mit 16-mm-Ablauf; Kassetten haben eine integrierte Pumpe
    mit_schlauch = [ie for ie in ies if ie.bauart in ("Wandgerät", "Konsole")]
    if mit_schlauch:
        add(NR_SPIRALSCHLAUCH, math.ceil(len(mit_schlauch) * 3 / 30), "Grundausstattung: Kondensatablauf Ø 16 mm (Rolle 30 m)")
    if projekt.kondensatpumpe:
        for ie in ies:
            if ie.bauart == "Wandgerät":
                add(NR_PUMPE_WAND, 1, "Kondensatpumpe gewählt: unter dem Wandgerät")
            elif ie.bauart in ("Konsole", "Truhe/Decke"):
                add(NR_PUMPE_EINBAU, 1, "Kondensatpumpe gewählt: Einbau in Konsole/Truhe")

    # App-Steuerung (WLAN)
    if projekt.app_steuerung:
        for ie in ies:
            for nr, text in _gateway(ie):
                add(nr, 1, "App-Steuerung gewählt" + (f" – {text}" if text else ""))

    # BEG-Förderung: Climate 7000i nur mit Smart-Grid-Modul MSG-1
    add(NR_MSG1, sum(1 for t in konzept.teilsysteme if t.set and t.set.linie == "Climate 7000i"),
        "BEG-Förderung: netzdienliche Schnittstelle je Climate 7000i Set")

    # Basispakete: Set + Montagematerial + Konsole unter einer Bestell-Nr.
    raeume: dict[str, list[str]] = {}
    for t in konzept.teilsysteme:
        if t.set and BOPA.get(t.set.typ, {}).get(projekt.aufstellung):
            raeume.setdefault(t.set.typ, []).append(t.bezeichnung)
    for typ, namen in raeume.items():
        z = kat.zubehoer_nr(BOPA[typ][projekt.aufstellung])
        s = next(a for a in kat.sets if a.typ == typ)
        if not (z and z.preis and s.preis):
            continue
        teile = [ROHRE['3/8"'][5], NR_KABEL_KLEIN, NR_SPIRALSCHLAUCH,
                 NR_WANDKONSOLE if projekt.aufstellung == "wand" else NR_BODENKONSOLE]
        einzeln = s.preis + sum((kat.zubehoer_nr(nr).preis or 0) for nr in teile if kat.zubehoer_nr(nr)) + 2 * sum(
            (kat.zubehoer_nr(KLEMMRING[g]).preis or 0) for g in ('1/4"', '3/8"'))
        vergleich = (f"{fmt_eur(einzeln - z.preis)} günstiger als einzeln" if einzeln - z.preis > 5
                     else "preisgleich zu den Einzelteilen, aber nur eine Bestellposition")
        hinweise.append(f"{typ} ({', '.join(namen)}): auch als {z.name}, Bestell-Nr. {z.bestellnr}, {fmt_eur(z.preis)} "
                        f"je Raum – Set mit 5 m Leitung, Kabel, Kondensatschlauch, Klemmringen und Konsole; "
                        f"{vergleich}.")
    return mengen, {nr: "; ".join(t) for nr, t in grund.items()}, hinweise


def _optional(passend: str | None) -> str:
    if not passend or passend in ("–", "Split-Klimageräte", "Climate Außeneinheiten"):
        return "Optional"
    if "kW" in passend:
        return f"Optional: für Geräte mit {passend}"
    return f"Optional: passend für {passend}"


def gateway_bedarf(konzept: Konzept) -> tuple[set[str], int, int]:
    """Benötigte Gateway-Artikel, Zahl der Innengeräte mit bzw. ohne integriertes WLAN."""
    bedarf: set[str] = set()
    mit_wlan = ohne_wlan = 0
    for ie in _innengeraete(konzept):
        nrs = [nr for nr, _ in _gateway(ie)]
        bedarf |= set(nrs)
        mit_wlan += not nrs
        ohne_wlan += bool(nrs)
    return bedarf, mit_wlan, ohne_wlan


def wlan_uebersicht(konzept: Konzept, kat: Katalog | None = None) -> list[str]:
    """Je Geräteserie: WLAN integriert oder welches Gateway nötig ist (für den App-Schalter)."""
    namen = {NR_G10_3: "G 10-3", NR_G10_4: "G 10-4", NR_G10_CLC: "G 10 CLC", NR_G10_CLC1: "G 10 CLC-1"}
    zeilen: dict[str, str] = {}
    for ie in _innengeraete(konzept):
        serie = ie.geraet.linie + (f" {ie.bauart}" if ie.bauart != "Wandgerät" else "")
        nrs = [nr for nr, _ in _gateway(ie)]
        zeilen[serie] = ("WLAN integriert" if not nrs
                         else "kein WLAN eingebaut → " + " + ".join(namen[nr] for nr in nrs))
    return [f"{s}: {t}" for s, t in zeilen.items()]


def _sperrgrund(nr: str, konzept: Konzept, bedarf: set[str], ohne_wlan: int, bopa: set[str]) -> str:
    if nr in GATEWAYS and nr not in bedarf:
        return ("WLAN bei allen Innengeräten integriert (Climate 7000i / Class 8000i)" if not ohne_wlan
                else "passt nicht zu den gewählten Innengeräten")
    if nr == NR_MSG1 and not any(t.set and t.set.linie == "Climate 7000i" for t in konzept.teilsysteme):
        return "nur für Climate 7000i Single-Split"
    if nr in BOPA_NRS and nr not in bopa:
        return "nur für CL7000i-Set 26 E bzw. CL3200i-Set 26 WE"
    return ""


def tabelle(projekt: Projekt, konzept: Konzept, kat: Katalog) -> tuple[list[ZubehoerZeile], list[str]]:
    """Alle anbietbaren Zubehörartikel mit Vorschlag und gewählter Menge (manuelle Mengen haben Vorrang).
    Artikel, die zum Konzept nicht passen (z. B. WLAN-Gateway bei integriertem WLAN), sind gesperrt (Menge 0)."""
    mengen, grund, hinweise = vorschlag(projekt, konzept, kat)
    bedarf, _, ohne_wlan = gateway_bedarf(konzept)
    bopa = {nr for t in konzept.teilsysteme if t.set for nr in BOPA.get(t.set.typ, {}).values()}
    zeilen = []
    for z in kat.zubehoer:
        if z.kategorie == "Dienstleistung" or z.bestellnr in ERSETZT or z.bestellnr not in GRUPPE:
            continue
        v = mengen.get(z.bestellnr, 0)
        sperre = _sperrgrund(z.bestellnr, konzept, bedarf, ohne_wlan, bopa)
        menge = 0 if sperre else projekt.zubehoer_mengen.get(z.bestellnr, v)
        zeilen.append(ZubehoerZeile(GRUPPEN[GRUPPE[z.bestellnr]], z.bestellnr, z.name, z.preis, v, max(int(menge), 0),
                                    grund.get(z.bestellnr, ALTERNATIVE.get(z.bestellnr, _optional(z.passend))), sperre))
    zeilen.sort(key=lambda x: (GRUPPEN.index(x.gruppe), -x.vorschlag, x.name))
    return zeilen, hinweise


def gewaehlt(projekt: Projekt, konzept: Konzept, kat: Katalog) -> list[ZubehoerZeile]:
    return [z for z in tabelle(projekt, konzept, kat)[0] if z.menge > 0]


def summe(zeilen: list[ZubehoerZeile]) -> float | None:
    if any(z.einzelpreis is None for z in zeilen if z.menge):
        return None
    return sum(z.summe or 0 for z in zeilen)

