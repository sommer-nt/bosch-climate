import json

import httpx2
import anthropic

from splitklima.bericht import pdf_bericht
from splitklima.bewertung import wende_validierungsfall_an
from splitklima.export import produktdaten, projektstand, pruefdaten_text, validierungs_snapshot
from splitklima.ki_plan import KiPlanAnalyse, analysiere, in_raeume
from splitklima.modell import Projekt, Raum
from splitklima.produkte import standard
from splitklima.standort import finde_ort, klimaregion


def test_standort():
    assert finde_ort("nuertingen") == ("72622", "Nürtingen")
    assert finde_ort("80331") == ("80331", "München")
    assert finde_ort("Esslingen") == ("73728", "Esslingen am Neckar")
    assert finde_ort("Hamburg") is None
    assert klimaregion("80331").norm_aussen == -16
    assert klimaregion("50667").name == "Baden-Württemberg"  # außerhalb der Tabelle → erste Region


def test_setze_lage_wie_html():
    r = Raum()
    r.setze_lage("three")
    assert [w.ausrichtung for w in r.waende] == ["S", "W", "O"]
    r.setze_lage("attic")
    assert r.dach and r.vertikal == "above_heated" and len(r.waende) == 1
    r.setze_lage("basement")
    assert not r.dach and r.vertikal == "over_cellar"


def test_projekt_speichern_und_laden():
    p = Projekt()
    wende_validierungsfall_an(p, "multi5")
    kopie = Projekt.model_validate_json(p.model_dump_json())
    assert kopie == p


def test_exporte():
    pd = standard()
    p = Projekt()
    wende_validierungsfall_an(p, "multi2")
    pj = projektstand(p, pd)
    assert pj["schema"] == "SplitKlimaProject" and len(pj["rooms"]) == 2
    assert pj["selectedSystem"]["items"] == ["cl7000m-53-2"]
    assert len(produktdaten(pd, p)["outdoorUnits"]) == 13
    snap = validierungs_snapshot(p, pd)
    assert snap["validation"]["status"] == "ok"
    json.dumps(snap)  # muss serialisierbar sein
    assert "Validierungsstatus: Bestanden" in pruefdaten_text(p, pd)


def test_pdf_bericht():
    p = Projekt()
    wende_validierungsfall_an(p, "multi5")
    pdf = pdf_bericht(p, standard(), "01.10.2026 12:00")
    assert pdf.startswith(b"%PDF") and len(pdf) > 10_000


KI_ANTWORT = {
    "raeume": [
        {"name": "Wohnen", "geschoss": "EG", "raumart": "Wohnzimmer", "flaeche_m2": 31.4, "raumhoehe_m": 2.6,
         "aussenwaende": [{"ausrichtung": "S", "laenge_m": 6.1, "fensterflaeche_m2": 5.2},
                          {"ausrichtung": "W", "laenge_m": 5.0, "fensterflaeche_m2": 2.0}],
         "unter_dach": False, "dachform": "flat", "dachfenster_m2": 0, "ueber_unbeheizt": "erdreich",
         "unter_unbeheiztem_dachraum": False},
        {"name": "Schlafen", "geschoss": "DG", "raumart": "Schlafzimmer", "flaeche_m2": 15.0, "raumhoehe_m": 2.4,
         "aussenwaende": [{"ausrichtung": "W", "laenge_m": 4.0, "fensterflaeche_m2": 1.2}],
         "unter_dach": True, "dachform": "saddle_south", "dachfenster_m2": 0.9, "ueber_unbeheizt": "nein",
         "unter_unbeheiztem_dachraum": False},
    ],
    "nordrichtung": "Nordpfeil",
    "hinweise": ["Fensterhöhen angenommen."],
}


def test_ki_in_raeume():
    raeume = in_raeume(KiPlanAnalyse.model_validate(KI_ANTWORT))
    wohnen, schlafen = raeume
    assert wohnen.name == "EG Wohnen" and wohnen.lage == "corner" and wohnen.vertikal == "ground"
    assert schlafen.lage == "attic" and schlafen.dach and schlafen.dachform == "saddle_south"
    assert schlafen.fenstergruppen[0].dachfenster and schlafen.fenstergruppen[0].flaeche == 0.9


def test_ki_anfrage_aufbau():
    """Prüft die Anfrage an die Claude API mit einem simulierten Server."""
    gesehen = {}

    def server(req):
        gesehen["body"] = json.loads(req.content)
        gesehen["beta"] = req.headers.get("anthropic-beta")
        return httpx2.Response(200, json={
            "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
            "content": [{"type": "text", "text": json.dumps(KI_ANTWORT)}], "stop_reason": "end_turn",
            "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}})

    client = anthropic.Anthropic(api_key="test", http_client=httpx2.Client(transport=httpx2.MockTransport(server)))
    a = analysiere([(b"%PDF-1.4", "application/pdf")], "Oben ist Norden", client=client)
    assert len(a.raeume) == 2
    body = gesehen["body"]
    assert body["model"] == "claude-opus-5-5" and body["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in gesehen["beta"]
    assert [b["type"] for b in body["messages"][0]["content"]] == ["document", "text"]
    assert "Oben ist Norden" in body["messages"][0]["content"][1]["text"]
