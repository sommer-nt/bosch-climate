"""Version 2: Katalog, Geräteauswahl nach Katalogregeln, Bilder, PDF und Oberfläche."""

import itertools
import random
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from splitklima.berechnung import gebaeude_last, raum_last
from splitklima.ki_plan import KiPlanAnalyse, in_raeume
from splitklima.modell import Projekt, Raum, Wand
from splitklima.v2 import auswahl as A
from splitklima.v2.angebot import pdf_angebot_v2
from splitklima.v2.bilder import bild
from splitklima.v2.katalog import FARBEN, standard

WURZEL = Path(__file__).parent.parent
BEISPIEL = WURZEL / "splitklima" / "daten" / "beispiel_planerkennung.json"
KAT = standard()


def beispielprojekt() -> Projekt:
    p = Projekt()
    p.raeume = in_raeume(KiPlanAnalyse.model_validate_json(BEISPIEL.read_text("utf-8")))
    return p


def test_katalog_gesamtsortiment():
    assert (len(KAT.sets), len(KAT.aussen), len(KAT.innen)) == (26, 6, 29)
    assert KAT.preise_freigegeben
    for a in (*KAT.sets, *KAT.aussen, *KAT.innen):
        assert a.preis and a.preis > 0, a.typ
        assert a.bestellnr, a.typ
        assert bild(a) is not None, f"kein Bild für {a.typ}"
    for ae in KAT.aussen:
        assert KAT.kombinationen.get(ae.typ), f"keine Kombinationen für {ae.typ}"
        assert ae.anschluesse and ae.min_ie <= ae.anschluesse


def _pruefe_konzept(k: A.Konzept, p: Projekt) -> None:
    """Jede vorgeschlagene Anlage hält die Katalogregeln ein und deckt die Lasten aus dem Rechenkern."""
    kuehl_rel, heiz_rel = A._relevant(p)
    for t in k.teilsysteme:
        if not t.gedeckt:
            continue
        if t.set:
            (r,) = t.raeume
            l = raum_last(r, p.einstellungen)
            if kuehl_rel:
                assert t.set.kuehl >= l.cool - 1e-9
            if heiz_rel:
                assert t.set.heiz is not None and t.set.heiz >= l.heat - 1e-9
            continue
        ae = t.aussen
        n = len(t.innen)
        assert ae.min_ie <= n <= ae.anschluesse
        klassen = tuple(sorted((u.klasse for _, u in t.innen), reverse=True))
        assert klassen in KAT.kombinationen[ae.typ], (ae.typ, klassen)
        for _, u in t.innen:
            assert ae.typ in u.aussen_kompatibel
        teil = p.model_copy(deep=True)
        teil.raeume = [r.model_copy(deep=True) for r in t.raeume]
        last = gebaeude_last(teil)
        if kuehl_rel:
            assert ae.kuehl >= last.cool - 1e-9
        if heiz_rel:
            assert ae.heiz >= last.heat - 1e-9


@pytest.mark.parametrize("wunsch,betrieb", list(itertools.product(["auto", "multi", "single"], ["both", "cool", "heat"])))
def test_beispielhaus_konzepte_regelkonform(wunsch, betrieb):
    p = beispielprojekt()
    p.einstellungen.betriebsart = betrieb
    liste = A.konzepte(p, KAT, wunsch)
    assert liste and any(k.gedeckt for k in liste)
    assert sum(k.empfohlen for k in liste) == 1
    empf = next(k for k in liste if k.empfohlen)
    assert empf.preis == min(k.preis for k in liste if k.gedeckt)
    for k in liste:
        _pruefe_konzept(k, p)


def test_zufallsprojekte_regelkonform():
    """Viele zufällige Häuser: nie eine unzulässige Kombination oder Unterdeckung."""
    rnd = random.Random(26)
    for _ in range(60):
        p = Projekt(raeume=[])
        p.einstellungen.betriebsart = rnd.choice(["both", "cool", "heat"])
        for j in range(rnd.randint(1, 8)):
            r = Raum(name=f"R{j}", geschoss=rnd.choice(["EG", "OG"]), flaeche=rnd.uniform(8, 45),
                     lage=rnd.choice(["outside", "corner"]), raumart=rnd.choice(["Wohnzimmer", "Schlafzimmer", "Büro"]),
                     waende=[Wand(ausrichtung=rnd.choice(["N", "O", "S", "W"]), laenge=4, fenster=rnd.uniform(0, 4))])
            r.ig_bauart = rnd.choice(["auto", "auto", "Wandgerät", "Deckenkassette", "Konsole"])
            r.farbe = rnd.choice(["", "", *FARBEN])
            p.raeume.append(r)
        for k in A.konzepte(p, KAT, rnd.choice(["auto", "multi", "single"])):
            _pruefe_konzept(k, p)


def test_farb_und_bauartwunsch():
    p = beispielprojekt()
    for r in p.raeume:
        r.farbe = "silber"
    single = next(k for k in A.konzepte(p, KAT, "single"))
    assert all(t.set.farbe == "silber" for t in single.teilsysteme if t.set)
    p = beispielprojekt()
    p.raeume[0].ig_bauart = "Deckenkassette"
    for k in A.konzepte(p, KAT):
        assert k.gedeckt
        geraete = [u for t in k.teilsysteme for r, u in t.innen if r is p.raeume[0]]
        assert geraete and geraete[0].bauart == "Deckenkassette"


def test_optionale_leistungen_und_pdf():
    p = beispielprojekt()
    k = next(k for k in A.konzepte(p, KAT) if k.empfohlen)
    opt = {x.name: x.menge for x in A.optionale_leistungen(k, KAT)}
    assert opt["Inbetriebnahme Außeneinheit bis 18 kW"] == k.aussengeraete
    assert opt["Inbetriebnahme je Inneneinheit"] == len(p.raeume)
    pdf = pdf_angebot_v2(p, k, KAT, "01.10.2026 10:00")
    assert pdf[:4] == b"%PDF" and len(pdf) > 20_000  # mit Produktbildern


def test_oberflaeche_v2_durchlauf(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    assert not at.exception

    def klick(label):
        next(b for b in at.button if b.label == label).click()
        at.run()
        assert not at.exception, at.exception

    klick("Multi-Split")
    assert at.session_state.v2_projekt.systemwunsch == "multi"
    klick("Beste Lösung")
    klick("Beispielhaus laden")
    assert at.session_state.v2_seite == "raeume" and len(at.session_state.v2_projekt.raeume) == 7
    klick("Küche bearbeiten")
    klick("Konsole")
    assert at.session_state.v2_projekt.raeume[at.session_state.v2_raum].ig_bauart == "Konsole"
    at.session_state.v2_seite = "ergebnis"
    at.run()
    assert not at.exception
    assert any("preis" in m.value and "€" in m.value for m in at.markdown)
    at.checkbox[0].check().run()
    assert [d.label for d in at.get("download_button")] == ["Angebotsübersicht (PDF)"]
    for seite in ("system", "gebaeude", "raeume"):
        at.session_state.v2_seite = seite
        at.run()
        assert not at.exception, seite
