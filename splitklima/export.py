"""JSON-Exporte (Schemata wie v6.9.1) und Prüfdaten-Text."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from . import parameter as P
from .auswahl import Kombination, gewaehlte_kombination, ig_gewaehlt, ig_status, kombinationen
from .berechnung import GebaeudeLast, gebaeude_last, raum_last
from .bewertung import validiere
from .modell import Projekt, Raum
from .produkte import Produktdaten


@dataclass
class Ergebnis:
    """Alles, was Oberfläche und Exporte zum aktuellen Projektstand brauchen."""

    last: GebaeudeLast
    kombinationen: list[Kombination]
    gewaehlt: Kombination | None


def auswerten(projekt: Projekt, pd: Produktdaten) -> Ergebnis:
    last = gebaeude_last(projekt)
    combos = kombinationen(projekt, last, pd)
    return Ergebnis(last, combos, gewaehlte_kombination(projekt, combos))


def _jetzt() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def berechnungsparameter(projekt: Projekt) -> dict:
    e = projekt.einstellungen
    return {
        "schema": "SplitKlimaCalculationParameters", "schemaVersion": "CALC-PARAM-0.1",
        "toolVersion": P.TOOL_VERSION, "modelVersions": P.MODEL_VERSIONS,
        "temperatures": {"coolSetpoint": e.soll_kuehlen_wirksam, "heatSetpoint": e.soll_heizen_wirksam,
                         "summerDesign": e.sommer, "winterDesign": e.norm_aussen},
        "buildingClasses": P.USTD, "glazing": P.GLAS, "solarOrientation": P.SOL, "roofSolar": P.DACH_SOLAR,
        "ventilation": {"default": P.LUFTWECHSEL_DEFAULT, **P.LUFTWECHSEL},
        "internalLoads": {"areaSpecific_W_m2": P.INTERN_W_M2, "Wohnzimmer": P.INTERN_GRUND_DEFAULT,
                          **P.INTERN_GRUND},
        "verticalBoundary": {"between_heated": "keine zusätzliche Transmission",
                             "over_cellar": "vereinfachter Boden gegen unbeheizt",
                             "above_unheated": "vereinfachte Decke gegen unbeheizt"},
        "formulas": P.FORMELN,
        "storageClasses": {k: {"label": v["label"], "baseDamping": v["damp"]} for k, v in P.STORAGE_CLASS.items()},
        "ageClasses": {k: {"label": v["label"], "uWall": v["w"]} for k, v in P.AGE_CLASSES.items()},
        "shadeRoof": P.SHADE_ROOF,
    }


def raum_annahmen(raum: Raum, projekt: Projekt) -> dict:
    e = projekt.einstellungen
    c = raum_last(raum, e)
    return {
        "room": raum.name, "type": raum.raumart, "area": raum.flaeche, "height": raum.hoehe,
        "volume": raum.flaeche * raum.hoehe,
        "ageClass": P.AGE_CLASSES[raum.baualter]["label"] if raum.baualter in P.AGE_CLASSES else "aus Dämmstandard",
        "uWall": c.u_wall, "uWindow": c.u_win, "gValue": c.g_val, "airChange": c.n,
        "storageClass": P.STORAGE_CLASS[raum.speicher]["label"], "coolHours": e.kuehlbetrieb_h,
        "storageDamping": f"{c.damp * 100:.0f} %", "storageEffect": round(c.storage_effect, 3),
        "coolGross": round(c.cool_gross, 3), "wallGross": c.wall_gross, "windowArea": c.win,
        "roofArea": c.roof_a, "summerDesign": e.sommer, "winterDesign": e.norm_aussen,
        "coolSetpoint": e.soll_kuehlen_wirksam, "heatSetpoint": e.soll_heizen_wirksam,
    }


def produktdaten(pd: Produktdaten, projekt: Projekt) -> dict:
    return {
        "schema": "SplitKlimaConfigData", "schemaVersion": "DM-0.1", "toolVersion": P.TOOL_VERSION,
        "generatedAt": _jetzt(),
        "outdoorUnits": [{
            "id": d.id, "name": d.name, "line": d.line, "system": d.system, "cool": d.cool, "heat": d.heat,
            "ports": d.ports, "article": d.article, "seer": d.seer, "scop": d.scop, "refrigerant": d.refrigerant,
            "soundOutdoor": d.soundOutdoor, "dimensions": d.dimensions, "weight": d.weight,
            "powerSupply": d.powerSupply, "operatingLimits": {"cool": d.opCool, "heat": d.opHeat},
            "refrigerantCharge": d.refrigerantCharge, "co2Equivalent": d.co2eq,
            "dataQuality": d.dataQuality or "offen",
        } for d in pd.aussen],
        "indoorUnits": [{"id": u.id, "name": u.name, "type": u.type, "cool": u.cool, "heat": u.heat,
                         "sound": u.sound} for u in pd.innen],
        "calculationParameters": berechnungsparameter(projekt),
        "defaults": {"building": P.USTD, "glass": P.GLAS, "solarOrientation": P.SOL,
                     "validationCases": ["sleep-small", "living-standard", "attic-west", "multi2", "multi5"]},
    }


def projektstand(projekt: Projekt, pd: Produktdaten) -> dict:
    """Projekt-Export im Schema ``SplitKlimaProject`` PJ-0.1 (wie v6.9.1)."""
    e = projekt.einstellungen
    erg = auswerten(projekt, pd)
    ch = erg.gewaehlt
    raeume = []
    for i, r in enumerate(projekt.raeume, 1):
        c = raum_last(r, e)
        u = ig_gewaehlt(r, projekt, pd)
        raeume.append({
            "index": i, "name": r.name, "type": r.raumart, "area": r.flaeche, "height": r.hoehe, "mode": r.lage,
            "walls": [{"ori": w.ausrichtung, "len": w.laenge, "win": w.fenster} for w in r.waende],
            "roof": r.dach, "roofKind": r.dachform, "roofArea": r.dachflaeche,
            "loads": {"cool": round(c.cool, 3), "heat": round(c.heat, 3),
                      "specificCool": round(c.cool * 1000 / (r.flaeche or 1)),
                      "specificHeat": round(c.heat * 1000 / (r.flaeche or 1))},
            "assumptions": raum_annahmen(r, projekt),
            "indoor": ({"id": u.id, "name": u.name, "type": u.type, "cool": u.cool, "heat": u.heat,
                        "status": ig_status(r, u, projekt).txt} if u else None),
        })
    return {
        "schema": "SplitKlimaProject", "schemaVersion": "PJ-0.1", "toolVersion": P.TOOL_VERSION,
        "modelVersions": P.MODEL_VERSIONS, "configId": projekt.config_id, "createdAt": _jetzt(),
        "project": {"name": projekt.name, "place": projekt.ort, "planner": projekt.bearbeiter,
                    "date": projekt.datum.isoformat()},
        "settings": {"systemKind": e.systemart, "operationMode": e.betriebsart, "building": e.daemmstandard,
                     "glass": e.verglasung, "shade": e.sonnenschutz, "heatOut": e.norm_aussen, "summer": e.sommer},
        "loads": {"cool": round(erg.last.cool, 3), "heat": round(erg.last.heat, 3), "rooms": erg.last.rooms},
        "selectedSystem": ({"id": ch.id, "label": ch.label, "cool": ch.t.cool, "heat": ch.t.heat,
                            "ports": ch.t.ports, "items": [d.id for d in ch.items]} if ch else None),
        "rooms": raeume,
    }


def pruefdaten_text(projekt: Projekt, pd: Produktdaten) -> str:
    erg = auswerten(projekt, pd)
    ch = erg.kombinationen[0] if erg.kombinationen else None
    zeilen = [
        f"Konfigurations-ID: {projekt.config_id}", f"Fall: {projekt.validierungsfall or 'manuell'}",
        f"Räume: {len(projekt.raeume)}", f"Kühlen: {erg.last.cool:.2f} kW", f"Heizen: {erg.last.heat:.2f} kW",
        f"System: {ch.label if ch else '-'}",
    ]
    for i, r in enumerate(projekt.raeume, 1):
        c = raum_last(r, projekt.einstellungen)
        u = ig_gewaehlt(r, projekt, pd)
        zeilen.append(f"Raum {i}: {r.name}; {r.flaeche:g} m²; K {c.cool:.2f} kW; H {c.heat:.2f} kW; "
                      f"IG {u.name if u else '-'}")
    v = validiere(projekt, erg.last, ch, pd)
    if v:
        zeilen.append(f"Validierungsstatus: {v.status_text}")
        if v.issues:
            zeilen.append("Fehler: " + " | ".join(v.issues))
        if v.warns:
            zeilen.append("Prüfen: " + " | ".join(v.warns))
    return "\n".join(zeilen)


def validierungs_snapshot(projekt: Projekt, pd: Produktdaten) -> dict:
    erg = auswerten(projekt, pd)
    ch = erg.kombinationen[0] if erg.kombinationen else None
    v = validiere(projekt, erg.last, ch, pd)
    return {
        "schema": "SplitKlimaValidationSnapshot", "schemaVersion": "VAL-0.1", "toolVersion": P.TOOL_VERSION,
        "configId": projekt.config_id, "caseId": projekt.validierungsfall or "manual",
        "summary": pruefdaten_text(projekt, pd),
        "validation": ({"key": v.key, "target": v.target, "issues": v.issues, "warns": v.warns,
                        "status": v.status} if v else None),
        "project": projektstand(projekt, pd),
    }
