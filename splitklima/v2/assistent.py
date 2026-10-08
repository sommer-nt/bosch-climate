"""Planungs-Assistent der Version 2: Änderungen an der Planung per Chat (Claude API mit Werkzeugen).

Sicherheitsprinzip: Der Assistent ändert ausschließlich die Planung der eigenen Sitzung – über
dieselben Felder, die auch per Klick änderbar sind. Es gibt kein Werkzeug für Programmcode, Dateien,
Server oder Katalogdaten. Jede Änderung wird wie eine Eingabe geprüft (pydantic-Modell, Grenzwerte).
Rechnung und Geräteauswahl macht weiterhin das Programm, nicht das Sprachmodell.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .. import klima_plz as KP
from .. import parameter as P
from ..berechnung import gebaeude_last, raum_last
from ..ki_plan import baualter_aus_baujahr
from ..modell import Fenstergruppe, Projekt, Raum, Wand
from ..preise import fmt_eur
from ..standort import klimaregion
from . import auswahl as A
from . import zubehoer as Z
from .katalog import BAUARTEN, FARBEN, Katalog

MODELL = "claude-opus-5-5"
MAX_RUNDEN = 10  # Werkzeug-Runden je Nachricht
MAX_NACHRICHTEN = 40  # je Sitzung (Kostenbremse)
RICHTUNGEN = P.AUSRICHTUNGEN  # N, NO, O, SO, S, SW, W, NW – im Uhrzeigersinn
DACH = {"kein": None, "flat": "flat", "saddle_south": "saddle_south", "saddle_north": "saddle_north",
        "saddle_eastwest": "saddle_eastwest"}
LAGEN = list(P.MODE_LABEL)
GRENZEN = {"flaeche": (1.0, 500.0), "hoehe": (1.8, 10.0), "laenge": (0.0, 200.0), "fenster": (0.0, 400.0),
           "dachfenster_m2": (0.0, 200.0), "leitungslaenge": (1.0, 50.0), "baujahr": (1800, 2030)}

SYSTEM = f"""Du bist der Planungs-Assistent im „Bosch Climate · Split-Klima Konfigurator“ (Version 2).
Fachbetriebe und Planer beschreiben dir auf Deutsch, was an ihrer Planung anders sein soll; du setzt es
mit deinen Werkzeugen um und erklärst kurz das Ergebnis.

Arbeitsweise
- Lies zuerst die Planung (planung_lesen), bevor du etwas änderst – Raumnummern und Werte stehen dort.
- Ändere nur über die Werkzeuge. Du rechnest keine Lasten und wählst keine Geräte selbst – das macht das
  Programm nach den Katalogregeln. Nach Änderungen meldet jedes Werkzeug den neuen Stand.
- Ist eine Angabe mehrdeutig und ändert sie das Ergebnis spürbar, frage kurz nach, statt zu raten.
  Kleine, offensichtliche Annahmen darfst du treffen – nenne sie dann.
- Antworte knapp: was geändert wurde (vorher → nachher), Auswirkung auf Kühllast/Heizlast und empfohlene
  Lösung mit Preis. Keine langen Erklärungen, keine Markdown-Tabellen.
- Erfinde keine Geräte, Preise oder Katalogdaten. Fragen zu Geräten beantwortest du aus ergebnis_lesen.

Himmelsrichtungen
- „Raum X liegt im Norden“ heißt: seine Außenwände zeigen nach Norden. Hat der Plan keinen Nordpfeil
  und liegt ein Raum anders als erkannt, ist meist der ganze Plan gedreht → plan_drehen (alle Räume,
  Dachfenster und Satteldach-Seiten drehen mit), nicht nur den einen Raum ändern.
- Drehwinkel: Richtung des Raums von der erkannten zur genannten im Uhrzeigersinn (z. B. S → N = 180°,
  S → W = 90°, S → O = 270°). Hat der Raum mehrere Außenwände und ist die Drehung nicht eindeutig, frage.

Bauphysik (überschlägig)
- Baujahr setzt die Grundwerte (Altbau/Bestand/Neubau). Eine spätere Fassadendämmung trägst du mit
  daemmung_setzen ein – passend zum Sanierungsjahr: vor 1995 facade_1990 (U≈0,50), 1995–2008 facade_2000
  (U≈0,35), ab 2009 facade (U≈0,28); Kerndämmung core, Innendämmung interior.
  Wurde nur das Dach oder die Kellerdecke gedämmt, sag, dass das Programm das nicht getrennt abbildet.
- Gewerbe-Lasten (Werkstatt 20 W/m², Halle/Lager 6 W/m², Verkaufsraum 25 W/m²) sind überschlägige
  Annahmen; sie ersetzen keine Kühllastberechnung nach VDI 2078 / DIN EN 16798.

Grenzen
- Du kannst die App selbst (Aussehen, Funktionen, Katalog, Preise) nicht ändern. Wünsche dazu nimmt der
  Entwickler entgegen: Daniel Sommer (HC/SDE3-PSD).
- Werte außerhalb der Grenzen lehnt das Programm ab: Fläche 1–500 m², Raumhöhe 1,8–10 m.
- Auswahlwerte: Raumarten {", ".join([*P.RAUMARTEN, *P.RAUMARTEN_GEWERBE])}; Lagen {", ".join(LAGEN)}
  ({"; ".join(f"{k} = {v}" for k, v in P.MODE_LABEL.items())}); Gerätewunsch {", ".join(BAUARTEN)} oder
  „keine“; Farben {", ".join(FARBEN)} oder „keine“; Gerätelinien {", ".join(f"{k or 'leer'} = {v}"
  for k, v in A.GERAETELINIEN.items())}; Aufstellung {", ".join(f"{k or 'leer'} = {v}"
  for k, v in A.AUFSTELLUNG.items())}.
"""


def _o(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


_RAUM = {"type": "string", "description": "Raumnummer (1, 2, …) oder Raumname"}
_WAND = _o({"ausrichtung": {"type": "string", "enum": RICHTUNGEN}, "laenge": {"type": "number"},
            "fenster": {"type": "number", "description": "Fensterfläche dieser Wand in m²"}},
           ["ausrichtung", "laenge", "fenster"])

TOOLS = [
    {"name": "planung_lesen", "description": "Aktuelle Planung: Projekt-Einstellungen, alle Räume mit Wänden, "
     "Lasten je Raum und die berechneten Lösungen. Vor jeder Änderung aufrufen.", "input_schema": _o({})},
    {"name": "ergebnis_lesen", "description": "Berechnete Lösungen (Konzepte) mit Geräten, Preisen, Hinweisen, "
     "Zubehörsumme. Für Fragen wie „warum so teuer“ oder „gibt es Günstigeres“.", "input_schema": _o({})},
    {"name": "raum_aendern", "description": "Eigenschaften eines Raums ändern. Nur angegebene Felder werden "
     "geändert.", "input_schema": _o({
         "raum": _RAUM, "name": {"type": "string"}, "geschoss": {"type": "string"},
         "raumart": {"type": "string", "enum": [*P.RAUMARTEN, *P.RAUMARTEN_GEWERBE]},
         "flaeche": {"type": "number", "description": "Grundfläche m²"},
         "hoehe": {"type": "number", "description": "Raumhöhe m"},
         "lage": {"type": "string", "enum": LAGEN, "description": "Ändert die Zahl der Außenwände"},
         "dach": {"type": "string", "enum": list(DACH), "description": "Dach direkt über dem Raum"},
         "dachfenster_m2": {"type": "number"},
         "farbe": {"type": "string", "enum": [*FARBEN, "keine"]},
         "geraetewunsch": {"type": "string", "enum": [*BAUARTEN, "keine"]}}, ["raum"])},
    {"name": "waende_setzen", "description": "Alle Außenwände eines Raums neu setzen (Ausrichtung, Länge, "
     "Fensterfläche). Leere Liste = innenliegender Raum.", "input_schema": _o({
         "raum": _RAUM, "waende": {"type": "array", "items": _WAND}}, ["raum", "waende"])},
    {"name": "fenster_setzen", "description": "Fensterfläche der Außenwand mit der angegebenen Ausrichtung "
     "setzen.", "input_schema": _o({"raum": _RAUM, "ausrichtung": {"type": "string", "enum": RICHTUNGEN},
                                     "fenster_m2": {"type": "number"}}, ["raum", "ausrichtung", "fenster_m2"])},
    {"name": "raum_hinzufuegen", "description": "Neuen Raum anlegen. Außenwände werden aus der Grundfläche "
     "geschätzt, wenn keine angegeben sind.", "input_schema": _o({
         "name": {"type": "string"}, "raumart": {"type": "string", "enum": [*P.RAUMARTEN, *P.RAUMARTEN_GEWERBE]},
         "flaeche": {"type": "number"}, "hoehe": {"type": "number"}, "geschoss": {"type": "string"},
         "lage": {"type": "string", "enum": LAGEN},
         "waende": {"type": "array", "items": _WAND}}, ["name", "raumart", "flaeche"])},
    {"name": "raum_entfernen", "description": "Raum aus der Planung entfernen.",
     "input_schema": _o({"raum": _RAUM}, ["raum"])},
    {"name": "plan_drehen", "description": "Den ganzen Grundriss drehen: alle Außenwände, Dachfenster und "
     "Satteldach-Seiten aller Räume. Für Pläne ohne oder mit falsch erkanntem Nordpfeil.",
     "input_schema": _o({"grad_im_uhrzeigersinn": {"type": "integer", "enum": [45, 90, 135, 180, 225, 270, 315]}},
                        ["grad_im_uhrzeigersinn"])},
    {"name": "daemmung_setzen", "description": "Nachträgliche Dämmung der Außenwände setzen – für alle Räume "
     "oder einzelne.", "input_schema": _o({
         "art": {"type": "string", "enum": list(P.NACHDAEMMUNG_V2)},
         "raeume": {"type": "array", "items": _RAUM, "description": "Leer = alle Räume"}}, ["art"])},
    {"name": "projekt_einstellungen", "description": "Projektweite Einstellungen. Nur angegebene Felder werden "
     "geändert.", "input_schema": _o({
         "projektname": {"type": "string"}, "plz": {"type": "string", "description": "Postleitzahl des Standorts"},
         "baujahr": {"type": "integer"},
         "systemwunsch": {"type": "string", "enum": ["auto", "multi", "single"]},
         "betriebsart": {"type": "string", "enum": ["both", "cool", "heat"]},
         "geraetelinie": {"type": "string", "enum": list(A.GERAETELINIEN)},
         "aufstellung": {"type": "string", "enum": list(A.AUFSTELLUNG)},
         "verglasung": {"type": "string", "enum": ["single", "double", "triple"]},
         "sonnenschutz": {"type": "string", "enum": ["1", "0.8", "0.45"],
                          "description": "1 = keiner, 0.8 = innen, 0.45 = außen"},
         "auslaufartikel": {"type": "boolean"}, "leitungslaenge": {"type": "number"},
         "app_steuerung": {"type": "boolean"}, "kondensatpumpe": {"type": "boolean"},
         "boerdelfrei": {"type": "boolean"}})},
    {"name": "loesung_waehlen", "description": "Eine der berechneten Lösungen auswählen (Schlüssel aus "
     "ergebnis_lesen, z. B. single, multi_gesamt, multi_geschoss, large) oder 'empfehlung'.",
     "input_schema": _o({"konzept": {"type": "string"}}, ["konzept"])},
]


class AssistentFehler(RuntimeError):
    """Für die Oberfläche verständliche Fehlermeldung."""


class _Ungueltig(ValueError):
    pass


@dataclass
class Antwort:
    text: str
    aenderungen: list[str] = field(default_factory=list)
    vorher: dict = field(default_factory=dict)
    nachher: dict = field(default_factory=dict)


# ---------------------------------------------------------------------- Hilfen
def _katalog(p: Projekt, kat: Katalog) -> Katalog:
    return kat if p.auslaufartikel else kat.ohne_auslauf()


def _konzepte(p: Projekt, kat: Katalog) -> list[A.Konzept]:
    return A.konzepte(p, _katalog(p, kat), p.systemwunsch) if p.raeume else []


def _gewaehlt(liste: list[A.Konzept], schluessel: str | None) -> A.Konzept | None:
    moeglich = [k for k in liste if k.gedeckt]
    if not moeglich:
        return None
    empf = next((k for k in moeglich if k.empfohlen), moeglich[0])
    return next((k for k in moeglich if k.key == schluessel), empf)


def kurzstatus(p: Projekt, kat: Katalog, schluessel: str | None = None) -> dict:
    if not p.raeume:
        return {"raeume": 0}
    last = gebaeude_last(p)
    k = _gewaehlt(_konzepte(p, kat), schluessel)
    return {"raeume": len(p.raeume), "kuehllast_kw": round(last.cool, 2), "heizlast_kw": round(last.heat, 2),
            "loesung": k.name if k else "keine passende Lösung", "geraete": k.geraete_text if k else "",
            "preis": fmt_eur(k.preis) if k else "–"}


def _zahl(name: str, wert) -> float:
    lo, hi = GRENZEN[name]
    try:
        x = float(wert)
    except (TypeError, ValueError) as e:
        raise _Ungueltig(f"{name}: keine Zahl") from e
    if not lo <= x <= hi:
        raise _Ungueltig(f"{name} {x:g} außerhalb des erlaubten Bereichs {lo:g}–{hi:g}")
    return x


def _raum_finden(p: Projekt, angabe: str) -> int:
    s = str(angabe).strip()
    if s.isdigit() and 1 <= int(s) <= len(p.raeume):
        return int(s) - 1
    treffer = [i for i, r in enumerate(p.raeume) if r.name.lower() == s.lower()]
    treffer = treffer or [i for i, r in enumerate(p.raeume) if s.lower() in r.name.lower()]
    if len(treffer) == 1:
        return treffer[0]
    namen = ", ".join(f"{i + 1} = {r.name}" for i, r in enumerate(p.raeume))
    raise _Ungueltig(f"Raum „{angabe}“ {'nicht eindeutig' if treffer else 'nicht gefunden'}. Räume: {namen}")


def _wand(d: dict) -> Wand:
    if d.get("ausrichtung") not in RICHTUNGEN:
        raise _Ungueltig(f"Ausrichtung muss eine von {', '.join(RICHTUNGEN)} sein")
    return Wand(ausrichtung=d["ausrichtung"], laenge=_zahl("laenge", d.get("laenge", 0)),
                fenster=_zahl("fenster", d.get("fenster", 0)))


def _drehen(richtung: str, grad: int) -> str:
    return RICHTUNGEN[(RICHTUNGEN.index(richtung) + grad // 45) % 8]


def _raum_info(i: int, r: Raum, p: Projekt) -> dict:
    l = raum_last(r, p.einstellungen)
    return {"nr": i + 1, "name": r.name, "geschoss": r.geschoss, "raumart": r.raumart, "flaeche_m2": r.flaeche,
            "hoehe_m": r.hoehe, "lage": r.lage,
            "waende": [{"ausrichtung": w.ausrichtung, "laenge": w.laenge, "fenster": w.fenster} for w in r.waende],
            "dach": r.dachform if r.dach else "kein",
            "dachfenster_m2": round(sum(g.flaeche for g in r.fenstergruppen if g.dachfenster), 2),
            "farbe": r.farbe or "keine", "geraetewunsch": A.bauart_wunsch(r) or "keine",
            "daemmung": r.daemmung, "kuehllast_kw": round(l.cool, 2), "heizlast_kw": round(l.heat, 2)}


def _ergebnis(p: Projekt, kat: Katalog, schluessel: str | None) -> dict:
    liste = _konzepte(p, kat)
    gew = _gewaehlt(liste, schluessel)
    out = []
    for k in liste:
        eintrag = {"schluessel": k.key, "name": k.name, "gedeckt": k.gedeckt, "empfohlen": k.empfohlen,
                   "gewaehlt": k is gew, "preis": fmt_eur(k.preis), "aussengeraete": k.aussengeraete,
                   "geraete": k.geraete_text, "hinweise": (k.lieferhinweise + k.hinweise)[:8]}
        if k is gew:
            zub = Z.gewaehlt(p, k, _katalog(p, kat))
            eintrag["zubehoer_summe"] = fmt_eur(Z.summe(zub))
            eintrag["aufstellungshinweise"] = A.aufstellungshinweise(p, k)
        out.append(eintrag)
    return {"konzepte": out}


# ---------------------------------------------------------------------- Werkzeuge
class _Werkzeuge:
    def __init__(self, p: Projekt, kat: Katalog, zustand: dict):
        self.p, self.kat, self.zustand = p, kat, zustand
        self.log: list[str] = []

    def _status(self) -> str:
        return json.dumps({"neuer_stand": kurzstatus(self.p, self.kat, self.zustand.get("konzept"))},
                          ensure_ascii=False)

    def ausfuehren(self, name: str, eingabe: dict) -> tuple[str, bool]:
        fn = getattr(self, f"t_{name}", None)
        if fn is None:
            return f"Unbekanntes Werkzeug {name}", True
        try:
            return fn(**(eingabe or {})), False
        except _Ungueltig as e:
            return f"Nicht übernommen: {e}", True
        except TypeError as e:
            return f"Ungültige Parameter: {e}", True
        except ValueError as e:  # pydantic-Prüfung
            return f"Nicht übernommen (ungültiger Wert): {str(e).splitlines()[0]}", True

    # --- lesen
    def t_planung_lesen(self) -> str:
        p, e = self.p, self.p.einstellungen
        return json.dumps({
            "projekt": {"name": p.name, "standort": p.ort, "plz": p.plz, "baujahr": p.baujahr,
                        "daemmstandard": P.USTD_LABEL[e.daemmstandard], "nachtraegliche_daemmung": p.nachdaemmung,
                        "norm_aussentemperatur": e.norm_aussen, "auslegung_sommer": e.sommer,
                        "systemwunsch": p.systemwunsch, "betriebsart": e.betriebsart,
                        "geraetelinie": p.geraetelinie, "aufstellung": p.aufstellung,
                        "verglasung": e.verglasung, "sonnenschutz": e.sonnenschutz,
                        "auslaufartikel": p.auslaufartikel, "leitungslaenge_m": p.leitungslaenge},
            "raeume": [_raum_info(i, r, p) for i, r in enumerate(p.raeume)],
            "stand": kurzstatus(p, self.kat, self.zustand.get("konzept"))}, ensure_ascii=False)

    def t_ergebnis_lesen(self) -> str:
        return json.dumps(_ergebnis(self.p, self.kat, self.zustand.get("konzept")), ensure_ascii=False)

    # --- Räume
    def t_raum_aendern(self, raum, **felder) -> str:
        i = _raum_finden(self.p, raum)
        r = self.p.raeume[i].model_copy(deep=True)
        alt_name = r.name
        teile = []
        if "lage" in felder:
            if felder["lage"] not in LAGEN:
                raise _Ungueltig(f"lage muss eine von {', '.join(LAGEN)} sein")
            hatte_dach = r.dach and r.lage not in ("attic", "attic_corner")
            r.setze_lage(felder["lage"])
            if hatte_dach and felder["lage"] not in ("attic", "attic_corner"):
                r.dach = True
            if r.waende_auto:
                r.wandlaengen_schaetzen()
            teile.append(f"Lage {P.MODE_LABEL[felder['lage']]}")
        for feld in ("name", "geschoss", "raumart"):
            if feld in felder:
                setattr(r, feld, felder[feld])
                teile.append(f"{feld} {felder[feld]}")
        if "flaeche" in felder:
            r.flaeche = _zahl("flaeche", felder["flaeche"])
            if r.waende_auto:
                r.wandlaengen_schaetzen()
            teile.append(f"Fläche {r.flaeche:g} m²")
        if "hoehe" in felder:
            r.hoehe = _zahl("hoehe", felder["hoehe"])
            teile.append(f"Höhe {r.hoehe:g} m")
        if "dach" in felder:
            if felder["dach"] not in DACH:
                raise _Ungueltig(f"dach muss eine von {', '.join(DACH)} sein")
            form = DACH[felder["dach"]]
            r.dach = bool(form) or r.lage in ("attic", "attic_corner")
            if form:
                r.dachform = form
            teile.append(f"Dach {P.DACHFORM_LABEL.get(form, 'kein') if form else 'kein'}")
        if "dachfenster_m2" in felder:
            fl = _zahl("dachfenster_m2", felder["dachfenster_m2"])
            r.fenstergruppen = [g for g in r.fenstergruppen if not g.dachfenster]
            if fl > 0:
                r.dach = True
                r.fenstergruppen.append(Fenstergruppe(ausrichtung="S", flaeche=fl, dachfenster=True))
            teile.append(f"Dachfenster {fl:g} m²")
        if "farbe" in felder:
            r.farbe = "" if felder["farbe"] == "keine" else felder["farbe"]
            teile.append(f"Farbe {felder['farbe']}")
        if "geraetewunsch" in felder:
            r.ig_bauart = "auto" if felder["geraetewunsch"] == "keine" else felder["geraetewunsch"]
            teile.append(f"Gerätewunsch {felder['geraetewunsch']}")
        self.p.raeume[i] = Raum.model_validate(r.model_dump())
        self.log.append(f"{alt_name}: " + ", ".join(teile))
        return self._status()

    def t_waende_setzen(self, raum, waende) -> str:
        i = _raum_finden(self.p, raum)
        r = self.p.raeume[i]
        neu = [_wand(w) for w in waende]
        r.waende, r.waende_auto = neu, False
        if not neu:
            r.lage = "inside"
        self.log.append(f"{r.name}: Außenwände " + (", ".join(f"{w.ausrichtung} {w.laenge:g} m/Fenster "
                                                              f"{w.fenster:g} m²" for w in neu) or "keine"))
        return self._status()

    def t_fenster_setzen(self, raum, ausrichtung, fenster_m2) -> str:
        i = _raum_finden(self.p, raum)
        r = self.p.raeume[i]
        wand = next((w for w in r.waende if w.ausrichtung == ausrichtung), None)
        if wand is None:
            raise _Ungueltig(f"{r.name} hat keine Außenwand nach {ausrichtung} "
                             f"(vorhanden: {', '.join(w.ausrichtung for w in r.waende) or 'keine'})")
        alt = wand.fenster
        wand.fenster = _zahl("fenster", fenster_m2)
        self.log.append(f"{r.name}: Fenster {ausrichtung} {alt:g} → {wand.fenster:g} m²")
        return self._status()

    def t_raum_hinzufuegen(self, name, raumart, flaeche, hoehe=2.5, geschoss="", lage="outside", waende=None) -> str:
        if lage not in LAGEN:
            raise _Ungueltig(f"lage muss eine von {', '.join(LAGEN)} sein")
        r = Raum(name=name, raumart=raumart, flaeche=_zahl("flaeche", flaeche), hoehe=_zahl("hoehe", hoehe),
                 geschoss=geschoss or (self.p.raeume[-1].geschoss if self.p.raeume else "EG"),
                 lage="outside", waende=[Wand(ausrichtung="S", laenge=4, fenster=2)], waende_auto=True,
                 daemmung=self.p.nachdaemmung if self.p.nachdaemmung in P.NACHDAEMMUNG_V2 else "none")
        r.baualter = baualter_aus_baujahr(self.p.baujahr) if self.p.baujahr else ""
        r.setze_lage(lage)
        if waende:
            r.waende, r.waende_auto = [_wand(w) for w in waende], False
        else:
            r.wandlaengen_schaetzen()
        self.p.raeume.append(Raum.model_validate(r.model_dump()))
        self.log.append(f"Raum „{name}“ angelegt ({raumart}, {r.flaeche:g} m²)")
        return self._status()

    def t_raum_entfernen(self, raum) -> str:
        i = _raum_finden(self.p, raum)
        r = self.p.raeume.pop(i)
        self.log.append(f"Raum „{r.name}“ entfernt")
        return self._status()

    def t_plan_drehen(self, grad_im_uhrzeigersinn) -> str:
        grad = int(grad_im_uhrzeigersinn)
        if grad % 45 or not 0 < grad < 360:
            raise _Ungueltig("Drehung nur in 45°-Schritten zwischen 45 und 315°")
        for r in self.p.raeume:
            for w in r.waende:
                w.ausrichtung = _drehen(w.ausrichtung, grad)
            for g in r.fenstergruppen:
                g.ausrichtung = _drehen(g.ausrichtung, grad)
            if r.dach and r.dachform.startswith("saddle"):
                if grad == 180:
                    r.dachform = {"saddle_south": "saddle_north", "saddle_north": "saddle_south"}.get(
                        r.dachform, r.dachform)
                elif grad in (90, 270):
                    r.dachform = {"saddle_south": "saddle_eastwest", "saddle_north": "saddle_eastwest",
                                  "saddle_eastwest": "saddle_south"}.get(r.dachform, r.dachform)
        self.log.append(f"Grundriss um {grad}° im Uhrzeigersinn gedreht ({len(self.p.raeume)} Räume)")
        return self._status()

    def t_daemmung_setzen(self, art, raeume=None) -> str:
        if art not in P.NACHDAEMMUNG_V2:
            raise _Ungueltig(f"art muss eine von {', '.join(P.NACHDAEMMUNG_V2)} sein")
        ziele = [_raum_finden(self.p, x) for x in raeume] if raeume else range(len(self.p.raeume))
        for i in ziele:
            self.p.raeume[i].daemmung = art
        if not raeume:
            self.p.nachdaemmung = art
        self.log.append(f"Nachträgliche Dämmung: {P.NACHDAEMMUNG_V2[art]} "
                        f"({'alle Räume' if not raeume else ', '.join(self.p.raeume[i].name for i in ziele)})")
        return self._status()

    def t_projekt_einstellungen(self, **felder) -> str:
        p, e = self.p.model_copy(deep=True), None
        e = p.einstellungen
        teile = []
        if "projektname" in felder:
            p.name = felder["projektname"]
            teile.append(f"Projektname {p.name}")
        if "plz" in felder:
            eintrag = KP.eintrag(str(felder["plz"]))
            if eintrag is None:
                raise _Ungueltig(f"PLZ {felder['plz']} nicht im Verzeichnis")
            p.plz, p.ort = eintrag.plz, eintrag.text
            wert = KP.norm_aussentemperatur(eintrag.plz)
            if wert is not None:
                e.norm_aussen, p.klima_quelle = round(wert.theta_e, 1), wert.quelle
            p.norm_aussen_manuell = False
            e.sommer = klimaregion(eintrag.plz).sommer
            teile.append(f"Standort {p.ort} (Norm-Außentemperatur {e.norm_aussen:g} °C)")
        if "baujahr" in felder:
            p.baujahr = int(_zahl("baujahr", felder["baujahr"]))
            e.daemmstandard = "old" if p.baujahr < 1979 else "mid" if p.baujahr < 2002 else "new"
            for r in p.raeume:
                r.baualter = baualter_aus_baujahr(p.baujahr)
            teile.append(f"Baujahr {p.baujahr} ({P.USTD_LABEL[e.daemmstandard]})")
        for feld in ("systemwunsch", "geraetelinie", "aufstellung", "auslaufartikel", "app_steuerung",
                     "kondensatpumpe", "boerdelfrei"):
            if feld in felder:
                setattr(p, feld, felder[feld])
                teile.append(f"{feld} {felder[feld]}")
        for feld in ("betriebsart", "verglasung", "sonnenschutz"):
            if feld in felder:
                setattr(e, feld, felder[feld])
                teile.append(f"{feld} {felder[feld]}")
        if "leitungslaenge" in felder:
            p.leitungslaenge = _zahl("leitungslaenge", felder["leitungslaenge"])
            teile.append(f"Leitungslänge {p.leitungslaenge:g} m")
        neu = Projekt.model_validate(p.model_dump())
        for k in Projekt.model_fields:
            setattr(self.p, k, getattr(neu, k))
        if {"systemwunsch", "geraetelinie", "auslaufartikel"} & set(felder):
            self.zustand.pop("konzept", None)
        self.log.append("Projekt: " + (", ".join(teile) or "keine Änderung"))
        return self._status()

    def t_loesung_waehlen(self, konzept) -> str:
        if konzept == "empfehlung":
            self.zustand.pop("konzept", None)
            self.log.append("Lösung: Empfehlung")
            return self._status()
        liste = [k for k in _konzepte(self.p, self.kat) if k.gedeckt]
        k = next((k for k in liste if k.key == konzept), None)
        if k is None:
            raise _Ungueltig(f"Lösung {konzept} nicht verfügbar; möglich: {', '.join(x.key for x in liste)}")
        self.zustand["konzept"] = k.key
        self.log.append(f"Lösung gewählt: {k.name}")
        return self._status()


# ---------------------------------------------------------------------- Dialog
def antworten(verlauf: list, eingabe: str, p: Projekt, kat: Katalog, zustand: dict, client=None) -> Antwort:
    """Eine Nutzernachricht verarbeiten. ``verlauf`` (API-Nachrichten) und ``p`` werden fortgeschrieben,
    ``zustand['konzept']`` ist die gewählte Lösung der Sitzung."""
    import anthropic

    if client is None:
        try:
            client = anthropic.Anthropic()
        except Exception as e:  # noqa: BLE001
            raise AssistentFehler("Der Assistent ist nicht eingerichtet (API-Schlüssel fehlt).") from e
    werkzeuge = _Werkzeuge(p, kat, zustand)
    vorher = kurzstatus(p, kat, zustand.get("konzept"))
    verlauf.append({"role": "user", "content": eingabe})
    texte: list[str] = []
    for _ in range(MAX_RUNDEN):
        try:
            antwort = client.beta.messages.create(
                model=MODELL, max_tokens=16000, system=SYSTEM, tools=TOOLS, messages=verlauf,
                cache_control={"type": "ephemeral"}, output_config={"effort": "medium"},
                betas=["server-side-fallback-2026-07-01"], fallbacks="default")
        except anthropic.AuthenticationError as e:
            raise AssistentFehler("Kein gültiger API-Schlüssel (ANTHROPIC_API_KEY).") from e
        except anthropic.RateLimitError as e:
            raise AssistentFehler("Zu viele Anfragen – bitte kurz warten und erneut senden.") from e
        except anthropic.APIConnectionError as e:
            raise AssistentFehler("Keine Verbindung zur Claude API.") from e
        except anthropic.APIStatusError as e:
            raise AssistentFehler(f"Claude API meldet einen Fehler ({e.status_code}).") from e
        verlauf.append({"role": "assistant", "content": antwort.content})
        texte += [b.text for b in antwort.content if getattr(b, "type", "") == "text" and b.text.strip()]
        if antwort.stop_reason == "refusal":
            texte.append("Dazu kann ich leider nichts beitragen.")
            break
        if antwort.stop_reason != "tool_use":
            if antwort.stop_reason == "max_tokens":
                texte.append("(Antwort gekürzt.)")
            break
        ergebnisse = []
        for b in antwort.content:
            if getattr(b, "type", "") == "tool_use":
                inhalt, fehler = werkzeuge.ausfuehren(b.name, b.input if isinstance(b.input, dict) else {})
                ergebnisse.append({"type": "tool_result", "tool_use_id": b.id, "content": inhalt,
                                   **({"is_error": True} if fehler else {})})
        verlauf.append({"role": "user", "content": ergebnisse})
    else:
        texte.append("Ich habe die Bearbeitung nach mehreren Schritten angehalten – bitte genauer beschreiben.")
    return Antwort("\n\n".join(texte) or "Erledigt.", werkzeuge.log, vorher,
                   kurzstatus(p, kat, zustand.get("konzept")))
