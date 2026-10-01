"""Assistent, Preise und wirtschaftliche Empfehlung."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from splitklima.anlagenvorschlag import anlagenkonzepte
from splitklima.bericht import pdf_angebot
from splitklima.ki_plan import KiPlanAnalyse, in_raeume
from splitklima.modell import Projekt, Raum, Wand
from splitklima.preise import Position, aus_json, fmt_eur, gesamtpreis, standard as preise
from splitklima.produkte import standard

WURZEL = Path(__file__).parent.parent
BEISPIEL = WURZEL / "splitklima" / "daten" / "beispiel_planerkennung.json"


def beispielprojekt() -> Projekt:
    p = Projekt()
    p.raeume = in_raeume(KiPlanAnalyse.model_validate_json(BEISPIEL.read_text("utf-8")))
    return p


def test_preisliste_vollstaendig():
    """Jedes Gerät aus den Produktdaten hat einen Preis."""
    pl, pd = preise(), standard()
    assert {d.id for d in pd.aussen} <= set(pl.aussen)
    assert {u.id for u in pd.innen} <= set(pl.innen)


def test_gesamtpreis_und_format():
    pos = [Position("aussen", "a", "A", "1", 1, 1000.0), Position("innen", "b", "B", "2", 3, 450.0)]
    assert gesamtpreis(pos) == 2350
    assert gesamtpreis(pos + [Position("zubehoer", "c", "C", "3", 1, None)]) is None
    assert fmt_eur(12345.4) == "12.345 €" and fmt_eur(None) == "auf Anfrage"


def test_empfehlung_ist_guenstigstes_vollstaendiges_konzept():
    pd, pl = standard(), preise()
    konzepte = anlagenkonzepte(beispielprojekt(), pd, pl)
    vollstaendig = [k for k in konzepte if k.vollstaendig(pd)]
    empf = [k for k in konzepte if k.empfohlen]
    assert len(empf) == 1
    assert empf[0].preis(pd, pl) == min(k.preis(pd, pl) for k in vollstaendig)


def test_stueckliste_enthaelt_alle_geraete():
    pd, pl = standard(), preise()
    p = beispielprojekt()
    for k in anlagenkonzepte(p, pd, pl):
        liste = k.stueckliste(pd, pl)
        assert sum(x.menge for x in liste if x.art == "innen") == len(p.raeume)
        assert sum(x.menge for x in liste if x.art == "aussen") == k.aussengeraete
        assert k.preis(pd, pl) == sum(x.summe for x in liste)


@pytest.mark.parametrize("wunsch,erwartet", [
    ("auto", {"multi_gesamt", "multi_geschoss", "single"}),
    ("multi", {"multi_gesamt", "multi_geschoss"}),
    ("single", {"single"}),
])
def test_systemwunsch(wunsch, erwartet):
    assert {k.key for k in anlagenkonzepte(beispielprojekt(), standard(), preise(), wunsch)} == erwartet


def test_multi_wunsch_mit_einem_raum_faellt_auf_single_zurueck():
    p = Projekt(raeume=[Raum(name="Wohnen", lage="outside", waende=[Wand(ausrichtung="S", laenge=5, fenster=3)])])
    assert [k.key for k in anlagenkonzepte(p, standard(), preise(), "multi")] == ["single"]


def test_ohne_freigabe_als_platzhalter_markiert():
    assert preise().freigegeben is False
    pl = aus_json('{"freigegeben": true, "aussengeraete": {"x": 1}}')
    assert pl.freigegeben and pl.preis("aussen", "x") == 1 and pl.preis("innen", "y") is None


def test_pdf_angebot():
    pd, pl = standard(), preise()
    p = beispielprojekt()
    k = next(k for k in anlagenkonzepte(p, pd, pl) if k.empfohlen)
    pdf = pdf_angebot(p, k, pd, pl, "01.10.2026 12:00")
    assert pdf.startswith(b"%PDF") and len(pdf) > 5_000


def _knopf(at, text):
    return next(b for b in at.button if b.label.strip().startswith(text))


def test_assistent_durchlauf():
    at = AppTest.from_file(str(WURZEL / "app.py"), default_timeout=90).run()
    assert not at.exception and len(at.sidebar.text_input) == 0  # Assistent ohne Seitenleiste
    next(n for n in at.number_input if n.label == "Baujahr").set_value(1972).run()
    _knopf(at, "Weiter zu den Räumen").click().run()
    _knopf(at, "Beispielhaus laden").click().run()
    p = at.session_state["projekt"]
    assert len(p.raeume) == 7 and p.baujahr == 1972 and all(r.baualter == "1969-1978" for r in p.raeume)
    assert not at.warning  # keine gelben Meldungen nach dem Hochladen
    _knopf(at, "Ergebnis anzeigen").click().run()
    assert not at.exception
    assert "Gerätepreis" in [m.label for m in at.metric]
    next(c for c in at.checkbox if c.label.startswith("Ich habe")).check().run()
    assert [d.label for d in at.get("download_button")] == ["📄 Angebotsübersicht (PDF)"]
    _knopf(at, "Details in der Expertenansicht").click().run()
    assert at.session_state["ansicht"] == "Expertenansicht" and len(at.sidebar.text_input) > 0
