"""Abgleich Python ↔ HTML v6.9.1.

`tests/referenz/erwartet.json` wurde mit dem Original-JavaScript erzeugt
(siehe `tests/referenz/faelle_erzeugen.py`). Python muss für alle Fälle
dieselben Lasten, Geräte, Systeme und Bewertungen liefern.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from splitklima.auswahl import ig_gewaehlt, ig_status, kombinationen, produkt_modus, raum_zuordnung
from splitklima.berechnung import gebaeude_last, raum_last
from splitklima.bewertung import (
    datenqualitaet, gesamtstatus, heizanwendung, leisere_alternative, schall_bewertung, validiere,
    wende_validierungsfall_an, zubehoer,
)
from splitklima.modell import Einstellungen, Fenstergruppe, Projekt, Raum, Wand
from splitklima.produkte import standard

REF = Path(__file__).parent / "referenz"
FAELLE = json.loads((REF / "faelle.json").read_text("utf-8"))
ERWARTET = {e["name"]: e for e in json.loads((REF / "erwartet.json").read_text("utf-8"))}


def einstellungen_aus_js(s: dict) -> Einstellungen:
    return Einstellungen(
        systemart=s["systemKind"], betriebsart=s["operationMode"], daemmstandard=s["building"],
        verglasung=s["glass"], sonnenschutz=str(s["shade"]), norm_aussen=float(s["heatOut"]),
        sommer=float(s["summer"]), kuehlbetrieb_h=int(s["coolHours"]), gleichzeitigkeit=float(s["simFactor"]),
        waermebruecken=s["wbClass"], aufheizreserve=s["reheatClass"], soll_kuehlen=float(s["coolSet"]),
        soll_heizen=float(s["heatSet"]),
    )


def raum_aus_js(r: dict) -> Raum:
    return Raum(
        name=r["name"], raumart=r["type"], flaeche=r["area"], hoehe=r["height"], lage=r["mode"],
        waende=[Wand(ausrichtung=w["ori"], laenge=w["len"], fenster=w["win"]) for w in r["walls"]],
        dach=r["roof"], dachform=r["roofKind"], dachflaeche=r["roofArea"], vertikal=r["vertical"],
        baualter=r["ageClass"], speicher=r["storage"], daemmung=r["retrofit"],
        fenstergruppen=[Fenstergruppe(ausrichtung=g["ori"], flaeche=g["area"], dachfenster=g["roofWindow"])
                        for g in r["windowGroups"]],
        ig_bauart=r["indoorType"], ig_id=r["indoorId"], ig_manuell=r["indoorManual"],
    )


def projekt_aus_fall(f: dict) -> Projekt:
    p = Projekt(einstellungen=einstellungen_aus_js(f["settings"]))
    if f.get("applyCase"):
        wende_validierungsfall_an(p, f["applyCase"])
    else:
        p.raeume = [raum_aus_js(r) for r in f["rooms"]]
        p.validierungsfall = f.get("validationCase", "")
    return p


@pytest.mark.parametrize("fall", FAELLE, ids=[f["name"] for f in FAELLE])
def test_gleiches_ergebnis_wie_html(fall):
    exp = ERWARTET[fall["name"]]
    pd = standard()
    p = projekt_aus_fall(fall)
    e = p.einstellungen
    assert e.systemart == exp["settings"]["systemKind"]

    for r, er in zip(p.raeume, exp["rooms"], strict=True):
        l = raum_last(r, e)
        for py, js in [("cool", "cool"), ("cool_gross", "coolGross"), ("storage_effect", "storageEffect"),
                       ("heat", "heat"), ("heat_trans", "heatTrans"), ("heat_vent", "heatVent"),
                       ("heat_reheat", "heatReheat"), ("damp", "damp"), ("wall_gross", "wallGross"),
                       ("win", "win")]:
            assert getattr(l, py) == pytest.approx(er[js], rel=1e-12, abs=1e-12), (r.name, py)
        u = ig_gewaehlt(r, p, pd)
        assert (u.id if u else None) == er["indoorId"], r.name
        assert ig_status(r, u, p).txt == er["indoorStatus"], r.name

    last = gebaeude_last(p)
    assert last.cool == pytest.approx(exp["load"]["cool"], rel=1e-12, abs=1e-12)
    assert last.heat == pytest.approx(exp["load"]["heat"], rel=1e-12, abs=1e-12)
    assert produkt_modus(p, last) == exp["productMode"]

    combos = kombinationen(p, last, pd)
    assert [(c.id, c.label) for c in combos] == [(c["id"], c["label"]) for c in exp["combos"]]
    for c, ec in zip(combos, exp["combos"]):
        assert c.score == pytest.approx(ec["score"], rel=1e-9, abs=1e-9)
    chosen = combos[0] if combos else None

    assert [[z.system, z.outdoor.id, [r.name for r in z.rooms]] for z in raum_zuordnung(p, chosen)] \
        == exp["assignment"]
    assert gesamtstatus(p, chosen, pd).txt == exp["overall"]
    assert heizanwendung(last, chosen).label == exp["heatClass"]
    dq = datenqualitaet(p)
    assert [dq.individual, dq.total] == exp["dataQuality"]
    assert {k: [[z.id, z.qty] for z in v] for k, v in zubehoer(p, chosen, pd).items()} == exp["accessories"]
    if chosen:
        assert [schall_bewertung(d)[1] for d in chosen.items] == exp["sound"]
        assert [(q.id if (q := leisere_alternative(d, last, pd)) else None) for d in chosen.items] \
            == exp["quieter"]
    v = validiere(p, last, chosen, pd)
    if exp["validation"] is None:
        assert v is None
    else:
        assert (v.status, v.issues, v.warns) == (exp["validation"]["status"], exp["validation"]["issues"],
                                                 exp["validation"]["warns"])


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js nicht installiert")
def test_referenz_ist_aktuell(tmp_path):
    """Erzeugt die Referenz neu aus dem HTML und prüft, dass sie unverändert ist."""
    html = Path(__file__).parent.parent / "Split_Klima_Konfigurator_v6_9_1_Aktuell_Sommer.html"
    if not html.exists():
        pytest.skip("HTML-Original nicht vorhanden")
    ziel = tmp_path / "erwartet.json"
    subprocess.run(["node", str(REF / "js_referenz.mjs"), str(html), str(REF / "faelle.json"), str(ziel)],
                   check=True, capture_output=True)
    assert json.loads(ziel.read_text("utf-8")) == json.loads((REF / "erwartet.json").read_text("utf-8"))
