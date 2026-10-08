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
from splitklima.v2 import speichern as SP
from splitklima.v2 import zubehoer as Z
from splitklima.v2.katalog import FARBEN, standard

WURZEL = Path(__file__).parent.parent
BEISPIEL = WURZEL / "splitklima" / "daten" / "beispiel_planerkennung.json"
KAT = standard()


def beispielprojekt() -> Projekt:
    p = Projekt()
    p.raeume = in_raeume(KiPlanAnalyse.model_validate_json(BEISPIEL.read_text("utf-8")))
    return p


def test_katalog_gesamtsortiment():
    # Gesamtkatalog 03/2026 (26/6/29) + Ergänzungskatalog 09/2026 (26 Large-Split, CL5000M 53/3, 4× 1C)
    assert (len(KAT.sets), len(KAT.aussen), len(KAT.innen)) == (52, 7, 33)
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
        geraete = [u for t in k.teilsysteme for r, u in ([(x, t.set) for x in t.raeume] if t.set else t.innen)
                   if r is p.raeume[0]]
        assert geraete and geraete[0].bauart == "Deckenkassette", k.key


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
    # Speichern gibt es mehrfach: Desktop-Navigation, Smartphone-Schrittleiste, „Neu beginnen“-Abfrage
    assert {d.label for d in at.get("download_button")} == {"Angebotsübersicht (PDF)", "Speichern (JSON)",
                                                            "Vorher speichern (JSON)"}
    for seite in ("system", "gebaeude", "raeume"):
        at.session_state.v2_seite = seite
        at.run()
        assert not at.exception, seite


@pytest.mark.parametrize("farbe", ["rot", "anthrazit", "silber", "schwarz"])
def test_wunschfarbe_wird_empfohlen(farbe):
    """Eine Wunschfarbe, die es gibt, steht in der Empfehlung – auch wenn Weiß günstiger wäre."""
    p = beispielprojekt()
    raum = next(r for r in p.raeume if raum_last(r, p.einstellungen).cool < 3.4)  # passt in jede Farbserie
    raum.farbe = farbe
    for wunsch in ("auto", "multi"):
        liste = A.konzepte(p, KAT, wunsch)
        empf = next(k for k in liste if k.empfohlen)
        assert A.farbabweichungen(empf) == 0, (wunsch, empf.geraete_text)
        for k in liste:
            _pruefe_konzept(k, p)
        geraete = [u for t in empf.teilsysteme for r, u in ([(x, t.set) for x in t.raeume] if t.set else t.innen)
                   if r is raum]
        assert geraete[0].farbe == farbe


def test_rot_nur_als_set_im_multi_konzept():
    p = beispielprojekt()
    p.raeume[0].farbe = "rot"
    k = next(k for k in A.konzepte(p, KAT, "multi") if k.key == "multi_gesamt")
    eigenes = [t for t in k.teilsysteme if t.raeume == [p.raeume[0]]]
    assert eigenes and eigenes[0].set.farbe == "rot" and "8000i" in eigenes[0].set.linie
    assert sum(len(t.raeume) for t in k.teilsysteme) == len(p.raeume)


def test_farbe_bei_kassette_ignoriert():
    p = beispielprojekt()
    p.raeume[0].farbe = "rot"
    p.raeume[0].ig_bauart = "Deckenkassette"
    for k in A.konzepte(p, KAT):
        assert A.farbabweichungen(k) == 0 and not any("Wunschfarbe" in h for h in k.hinweise)


# ---------------------------------------------------------------- Gewerbe, Zonen, Gerätelinie
from splitklima import parameter as P  # noqa: E402


def _halle(art="Werkstatt", flaeche=200.0, hoehe=6.0) -> Projekt:
    r = Raum(name=art, raumart=art, flaeche=flaeche, hoehe=hoehe, lage="corner",
             waende=[Wand(ausrichtung="S", laenge=20, fenster=12), Wand(ausrichtung="W", laenge=10, fenster=4)])
    return Projekt(raeume=[r])


def test_gewerbe_raumarten_im_rechenkern():
    p = _halle()
    werkstatt = raum_last(p.raeume[0], p.einstellungen)
    p.raeume[0].raumart = "Halle / Lager"
    lager = raum_last(p.raeume[0], p.einstellungen)
    assert werkstatt.cool > lager.cool  # mehr innere Last in der Werkstatt
    assert set(P.RAUMARTEN_GEWERBE) <= set(P.LUFTWECHSEL) and len(P.RAUMARTEN) == 6  # v1-Liste unverändert


@pytest.mark.parametrize("art,flaeche,hoehe", [("Werkstatt", 200, 6.0), ("Halle / Lager", 400, 10.0),
                                               ("Verkaufsraum", 120, 3.0)])
def test_grosse_raeume_werden_in_zonen_geteilt(art, flaeche, hoehe):
    p = _halle(art, flaeche, hoehe)
    bed = A.bedarfe(p, KAT)
    assert len(bed) > 1
    assert abs(sum(b.raum.flaeche for b in bed) - flaeche) < 1e-6
    assert all(b.raum.name.startswith(f"{art} · Zone ") for b in bed)
    liste = A.konzepte(p, KAT)
    assert any(k.gedeckt for k in liste)
    for k in liste:
        _pruefe_konzept(k, p)
        if k.gedeckt and k.key != "large":  # Large-Split teilt mit größeren Geräten seltener auf
            assert k.innengeraete == len(bed)


def test_kleine_raeume_bleiben_ganz():
    p = beispielprojekt()
    assert len(A.bedarfe(p, KAT)) == len(p.raeume)


def test_gruppen_beachten_last_der_aussengeraete():
    bed = [A.Bedarf(Raum(name=f"R{i}"), 5.0, 5.0) for i in range(6)]
    for g in A.gruppen(bed, max_groesse=5, max_kuehl=12.3, max_heiz=12.3):
        assert sum(b.kuehl for b in g) <= 12.3 and len(g) <= 5


@pytest.mark.parametrize("linie", ["7000i", "8000i", "3200i"])
def test_geraetelinie_wird_empfohlen(linie):
    p = beispielprojekt()
    p.geraetelinie = linie
    liste = A.konzepte(p, KAT)
    empf = next(k for k in liste if k.empfohlen)
    assert A.linienabweichungen(empf, linie) == 0, empf.geraete_text
    for k in liste:
        _pruefe_konzept(k, p)
    if linie == "8000i":  # gibt es nur als Set
        assert empf.key == "single"


def test_oberflaeche_geraetelinie_und_hoehe(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    next(b for b in at.button if b.label == "Climate 7000i").click().run()
    assert at.session_state.v2_projekt.geraetelinie == "7000i"
    next(b for b in at.button if b.label == "Beispielhaus laden").click().run()
    next(b for b in at.button if b.label == "Küche bearbeiten").click().run()
    next(b for b in at.button if b.label == "Werkstatt").click().run()
    hoehe = next(n for n in at.number_input if n.label == "Raumhöhe")
    hoehe.set_value(9.5).run()
    assert not at.exception
    r = at.session_state.v2_projekt.raeume[at.session_state.v2_raum]
    assert (r.raumart, r.hoehe) == ("Werkstatt", 9.5)
    at.session_state.v2_seite = "ergebnis"
    at.run()
    assert not at.exception
    assert any("CL7000" in c.value for c in at.caption)


# ---------------------------------------------------------------- Ergänzungskatalog 09/2026
import json  # noqa: E402

from splitklima.v2 import katalog as KATMOD  # noqa: E402


def test_ergaenzung_daten_vollstaendig():
    erg = json.loads(KATMOD.ERGAENZUNG_JSON.read_text(encoding="utf-8"))
    assert len(erg["sets"]) == 26 and len(erg["preise"]) > 100
    for s in erg["sets"]:
        assert s["preis"] > 0 and len(s["bestellnr"]) == 10 and s["kuehl"] and s["heiz"], s["typ"]
        assert s["bauart"] in ("Deckenkassette", "Truhe/Decke", "Konsole"), s["typ"]
        assert s["anzahl_ie"] == (4 if "Double" in s["typ"] else 3 if "Triple" in s["typ"]
                                  else 2 if "Twin" in s["typ"] else 1)
        assert s["phasen"] in (1, 3)
    # Stichproben gegen den Katalog (S. 38, 44, 64)
    preise = {s["typ"]: s["preis"] for s in erg["sets"]}
    assert preise["CL5001iL-Set 26 4CC"] == 2136.40
    assert preise["CL5001iL-Set 160 4C-3"] == 6250.0
    assert preise["CL5001iL-Set 53 4CC Twin"] == 3464.60


def test_ergaenzung_preise_und_lieferstatus_uebernommen():
    basis = json.loads(KATMOD.KATALOG_JSON.read_text(encoding="utf-8"))
    alt = {a["typ"]: a["preis"] for a in basis["sets"]}
    neu = {a.typ: a.preis for a in KAT.sets}
    assert alt["CL3200i-Set 26 WE"] == 1351.0 and neu["CL3200i-Set 26 WE"] == 1378.02  # UVP 09/2026
    assert neu["CL3000i-Set 26 WE"] == alt["CL3000i-Set 26 WE"]  # nicht im Ergänzungskatalog → 03/2026
    assert all(a.verfuegbar for a in KAT.innen if a.typ.startswith("CL5001iU 4CC"))
    assert "CL5000M 53/3 E" in KAT.kombinationen
    assert all("CL5000M 53/3 E" in u.aussen_kompatibel for u in KAT.innen if "CL5000M 53/2 E" in u.aussen_kompatibel)


@pytest.mark.parametrize("art,flaeche,hoehe,bauart", [("Halle / Lager", 800, 8.0, "Truhe/Decke"),
                                                      ("Verkaufsraum", 120, 3.0, "Deckenkassette"),
                                                      ("Werkstatt", 200, 6.0, "auto")])
def test_large_split_fuer_hallen(art, flaeche, hoehe, bauart):
    p = _halle(art, flaeche, hoehe)
    p.raeume[0].ig_bauart = bauart
    liste = A.konzepte(p, KAT)
    large = next(k for k in liste if k.key == "large")
    assert large.gedeckt
    for k in liste:
        _pruefe_konzept(k, p)
    for t in large.teilsysteme:
        assert t.set.linie == "Climate 5000i L"
        if bauart != "auto":
            assert t.set.bauart == bauart
        if t.set.phasen == 3:
            assert any("400 V" in h for h in t.hinweise)
    assert large.innengeraete == sum(t.set.anzahl_ie for t in large.teilsysteme)


def test_wohnhaus_ohne_large_split():
    """Ohne Bauartwunsch ist für normale Wohnräume kein Large-Split nötig."""
    assert all(k.key != "large" for k in A.konzepte(beispielprojekt(), KAT))


# ---------------------------------------------------------------- Flachdach
def test_flachdach_erhoeht_kuehllast():
    p = beispielprojekt()
    r = Raum(name="Halle", raumart="Halle / Lager", flaeche=120, hoehe=6, lage="three",
             waende=[Wand(ausrichtung=a, laenge=10, fenster=2) for a in ("S", "W", "O")])
    ohne = raum_last(r, p.einstellungen).cool
    r.dach, r.dachform = True, "flat"
    flach = raum_last(r, p.einstellungen).cool
    r.dachform = "saddle_north"
    nord = raum_last(r, p.einstellungen).cool
    assert flach > nord > ohne


@pytest.mark.parametrize("aufstellung, konsole", [("flachdach", "Bodenkonsole"),
                                                  ("boden", "Bodenkonsole"),
                                                  ("wand", "Kleine Wandkonsole")])
def test_aufstellung_konsole_und_hinweise(aufstellung, konsole):
    p = beispielprojekt()
    p.aufstellung = aufstellung
    k = next(k for k in A.konzepte(p, KAT) if k.empfohlen)
    zub = {z.name: z.menge for z in Z.gewaehlt(p, k, KAT)}
    assert zub[konsole] == k.aussengeraete
    assert not {"Dämpfungssockel-Set 450 mm", "Dämpfungssockel-Set 600 mm"} & set(zub)  # nur als Alternative
    hinweise = A.aufstellungshinweise(p, k)
    assert hinweise and (aufstellung != "flachdach" or any("Dachabdichtung" in h for h in hinweise))
    assert pdf_angebot_v2(p, k, KAT)[:4] == b"%PDF"


def test_ohne_aufstellung_keine_konsole():
    p = beispielprojekt()
    k = next(k for k in A.konzepte(p, KAT) if k.empfohlen)
    namen = {x.name for x in Z.gewaehlt(p, k, KAT)}
    assert not namen & {"Bodenkonsole", "Kleine Wandkonsole"} and not A.aufstellungshinweise(p, k)


def test_oberflaeche_flachdach(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    next(b for b in at.button if b.label == "Flachdach").click().run()
    assert at.session_state.v2_projekt.aufstellung == "flachdach"
    next(b for b in at.button if b.label == "Beispielhaus laden").click().run()
    next(b for b in at.button if b.label == "Küche bearbeiten").click().run()
    next(b for b in at.button if b.label == "Flachdach").click().run()
    p = at.session_state.v2_projekt
    r = p.raeume[at.session_state.v2_raum]
    assert (r.dach, r.dachform) == (True, "flat")
    next(b for b in at.button if b.label == "3 Außenwände").click().run()  # Lagewechsel behält das Dach
    r = at.session_state.v2_projekt.raeume[at.session_state.v2_raum]
    assert r.dach and r.lage == "three"
    next(b for b in at.button if b.label == "Geschoss darüber").click().run()
    assert not at.session_state.v2_projekt.raeume[at.session_state.v2_raum].dach
    at.session_state.v2_seite = "ergebnis"
    at.run()
    assert not at.exception
    assert any("Flachdach" in m.value for m in at.markdown)


# ---------------------------------------------------------------- Farbwunsch über Leistungsgrenze/Linie
def _geraete_im_raum(k, name):
    return [u for t in k.teilsysteme for r, u in ([(x, t.set) for x in t.raeume] if t.set else t.innen)
            if r.name == name or r.name.startswith(f"{name} · Zone ")]


@pytest.mark.parametrize("linie", ["", "3200i", "8000i"])
@pytest.mark.parametrize("wunsch", ["auto", "multi"])
@pytest.mark.parametrize("flaeche", [38.4, 55, 70])
def test_schwarz_wird_immer_schwarz(flaeche, wunsch, linie):
    p = beispielprojekt()
    p.geraetelinie = linie
    r = p.raeume[0]
    r.flaeche, r.farbe = flaeche, "schwarz"
    k = next(k for k in A.konzepte(p, KAT, wunsch) if k.empfohlen)
    geraete = _geraete_im_raum(k, r.name)
    assert geraete and all(u.farbe == "schwarz" for u in geraete), [u.typ for u in geraete]
    assert A.farbabweichungen(k) == 0
    if raum_last(r, p.einstellungen).cool > A.farbgrenze(r, KAT)[0]:
        assert len(geraete) > 1 and any("je Gerät" in h for h in k.hinweise)


# ---------------------------------------------------------------- Zubehör
def test_zubehoer_vorschlag_vollstaendig():
    p = beispielprojekt()
    p.aufstellung, p.leitungslaenge, p.app_steuerung, p.boerdelfrei = "wand", 8, True, True
    k = next(k for k in A.konzepte(p, KAT, "single"))
    zub = {z.bestellnr: z for z in Z.gewaehlt(p, k, KAT)}
    ies = k.innengeraete
    rohre = sum(z.menge for nr, z in zub.items() if nr in {n for d in Z.ROHRE.values() for n in d.values()})
    assert rohre == ies  # 8 m → je Innengerät ein 10-m-Paket
    assert zub[Z.ROHRE['3/8"'][10]].menge + zub.get(Z.ROHRE['1/2"'][10], Z.ZubehoerZeile("", "", "", 0, 0, 0)).menge == ies
    assert zub[Z.NR_KABEL_KLEIN].menge == 2 * ies  # 8 m Kabel → 2 × 5,5 m
    assert zub[Z.NR_SPIRALSCHLAUCH].menge >= 1
    assert zub[Z.NR_WANDKONSOLE].menge == k.aussengeraete
    assert zub[Z.KLEMMRING['1/4"']].menge == 2 * ies
    assert Z.NR_G10_4 in zub or Z.NR_G10_3 in zub
    assert Z.summe(list(zub.values())) > 0
    # ersetzte Artikel werden nicht mehr angeboten
    alle = {z.bestellnr for z in Z.tabelle(p, k, KAT)[0]}
    assert not alle & set(Z.ERSETZT) and "7733704064" in alle and "7738347186" in alle


def test_zubehoer_manuelle_mengen_und_7000i():
    p = beispielprojekt()
    p.geraetelinie = "7000i"
    k = next(k for k in A.konzepte(p, KAT, "single"))
    zub = {z.bestellnr: z.menge for z in Z.gewaehlt(p, k, KAT)}
    assert zub[Z.NR_MSG1] == len(k.teilsysteme)  # BEG-Förderung
    p.app_steuerung = True
    assert not {Z.NR_G10_3, Z.NR_G10_4} & {z.bestellnr for z in Z.gewaehlt(p, k, KAT)}  # WLAN integriert
    p.zubehoer_mengen = {Z.NR_MSG1: 0, Z.NR_PUMPE_WAND: 2}
    zub = {z.bestellnr: z.menge for z in Z.gewaehlt(p, k, KAT)}
    assert Z.NR_MSG1 not in zub and zub[Z.NR_PUMPE_WAND] == 2


def test_rohrpakete_wenige_stuecke():
    assert Z.rohr_pakete(5, KAT, '3/8"') == [5]
    assert Z.rohr_pakete(12, KAT, '3/8"') == [20]
    assert sum(Z.rohr_pakete(35, KAT, '1/2"')) >= 35
    assert Z.rohrklasse(3.5) == '3/8"' and Z.rohrklasse(5.3) == '1/2"' and Z.rohrklasse(14) is None


def test_bopa_paket_hinweis():
    p = beispielprojekt()
    p.aufstellung = "wand"
    k = next(k for k in A.konzepte(p, KAT, "single"))
    _, hinweise = Z.tabelle(p, k, KAT)
    assert any("BOPA CL322" in h for h in hinweise)


def test_pdf_mit_zubehoer():
    p = beispielprojekt()
    p.aufstellung = "flachdach"
    k = next(k for k in A.konzepte(p, KAT) if k.empfohlen)
    assert pdf_angebot_v2(p, k, KAT)[:4] == b"%PDF"


# ---------------------------------------------------------------- Speichern / Laden
def test_konfiguration_json_rundreise():
    p = beispielprojekt()
    p.name, p.aufstellung, p.geraetelinie = "Haus Müller", "flachdach", "7000i"
    p.raeume[0].farbe, p.raeume[0].dach, p.raeume[0].dachform = "schwarz", True, "flat"
    p.zubehoer_mengen = {Z.NR_PUMPE_WAND: 3}
    text = SP.exportieren(p, {"konzept": "single", "seite": "ergebnis"})
    q, auswahl = SP.importieren(text.encode())
    assert q.model_dump() == p.model_dump() and auswahl["konzept"] == "single"
    assert SP.dateiname(p).startswith("Klima_Haus_Müller_") and SP.dateiname(p).endswith(".json")


@pytest.mark.parametrize("daten, meldung", [
    (b"kein json", "Kein gültiges JSON"),
    (b'{"a": 1}', "keine gespeicherte Konfiguration"),
    (b'{"format": "bosch-climate-konfiguration", "version": 99, "projekt": {}}', "neueren"),
    (b'{"format": "bosch-climate-konfiguration", "version": 1, "projekt": {"raeume": [{"flaeche": "x"}]}}',
     "ungültige Werte"),
])
def test_konfiguration_fehlerhafte_datei(daten, meldung):
    with pytest.raises(SP.LadeFehler, match=meldung):
        SP.importieren(daten)


def test_oberflaeche_speichern_laden_und_zubehoer(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    next(b for b in at.button if b.label == "Beispielhaus laden").click().run()
    p = at.session_state.v2_projekt
    p.name = "Gespeichert"
    text = SP.exportieren(p, {"seite": "ergebnis", "erledigt": ["system", "gebaeude", "raeume"]})
    at.session_state.v2_projekt = Projekt(raeume=[])
    at.run()
    at.session_state.v2_import = b"kaputt"  # wie über den Upload-Dialog
    at.run()
    assert "Kein gültiges JSON" in at.session_state.v2_import_fehler
    at.session_state.v2_import = text.encode()
    at.run()
    assert not at.exception
    assert at.session_state.v2_projekt.name == "Gespeichert" and at.session_state.v2_seite == "ergebnis"
    assert len(at.session_state.v2_projekt.raeume) == len(p.raeume)
    assert any(t.label == "App-Steuerung (WLAN)" for t in at.toggle)


def test_oberflaeche_zubehoer_ohne_vorschlag(monkeypatch):
    """Large-Split über 7 kW ohne Aufstellort: kein Zubehörvorschlag → Hinweis statt Absturz."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    p = at.session_state.v2_projekt
    p.raeume = [Raum(name="Halle", raumart="Halle / Lager", flaeche=200, hoehe=6, lage="three",
                     ig_bauart="Deckenkassette", waende=[Wand(ausrichtung=a, laenge=14, fenster=4) for a in "SWO"])]
    k = next(k for k in A.konzepte(p, KAT) if k.key == "large")
    assert not [z for z in Z.tabelle(p, k, KAT)[0] if z.vorschlag]
    at.session_state.v2_konzept = "large"
    at.session_state.v2_seite = "ergebnis"
    at.run()
    assert not at.exception
    assert any("keinen automatischen Zubehörvorschlag" in i.value for i in at.info)
    next(t for t in at.toggle if t.label == "Alle Zubehörartikel zeigen").set_value(True).run()
    assert not at.exception


# ---------------------------------------------------------------- Wandlängen aus der Grundfläche
def test_wandlaengen_aus_grundflaeche():
    r = Raum(flaeche=200, lage="outside", waende=[Wand(laenge=4)], waende_auto=True)
    r.wandlaengen_schaetzen()
    assert [w.laenge for w in r.waende] == [14.1]
    r.setze_lage("three")
    r.wandlaengen_schaetzen()
    assert [w.laenge for w in r.waende] == [14.1, 14.1, 14.1]


def test_oberflaeche_wandlaengen_folgen_der_flaeche(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    at.session_state.v2_seite = "raeume"
    at.run()
    next(b for b in at.button if b.label == "Raum hinzufügen").click().run()
    next(n for n in at.number_input if n.label == "Grundfläche").set_value(200.0).run()
    r = at.session_state.v2_projekt.raeume[-1]
    assert r.waende_auto and [w.laenge for w in r.waende] == [14.1]
    next(b for b in at.button if b.label == "3 Außenwände").click().run()
    r = at.session_state.v2_projekt.raeume[-1]
    assert [w.laenge for w in r.waende] == [14.1, 14.1, 14.1]
    assert any("Wandlängen aus der Grundfläche geschätzt" in c.value for c in at.caption)
    # von Hand gesetzte Längen (z. B. Beispielhaus, KI-Plan) werden nicht überschrieben
    p = at.session_state.v2_projekt
    r.waende_auto, r.waende[0].laenge = False, 25.0
    next(n for n in at.number_input if n.label == "Grundfläche").set_value(300.0).run()
    assert at.session_state.v2_projekt.raeume[-1].waende[0].laenge == 25.0
    assert not at.exception and p is at.session_state.v2_projekt


# ---------------------------------------------------------------- Freigabe-Punkte 10/2026
def test_auslaufartikel_standardmaessig_ausgeblendet():
    auslauf = {a.typ for a in KAT.auslaufartikel}
    assert {"CL3000i-Set 26 WE", "CL3000iU W 20 E", "CLC8001i-Set 35 E"} <= auslauf
    assert not any(a.auslauf for a in (*KAT.sets, *KAT.innen) if "3200i" in a.linie or "7000i" in a.linie)
    ohne = KAT.ohne_auslauf()
    p = beispielprojekt()
    for k in A.konzepte(p, ohne):
        assert not [a.typ for t in k.teilsysteme for a in t.artikel() if a.auslauf]
    assert KAT.artikel("CL3000i-Set 26 WE").lieferhinweis.startswith("Auslaufartikel")


def test_oberflaeche_auslaufartikel_schalter(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    next(b for b in at.button if b.label == "Beispielhaus laden").click().run()
    at.session_state.v2_seite = "ergebnis"
    at.run()
    assert not any("CL3000i" in c.value for c in at.caption)
    at.session_state.v2_seite = "system"
    at.run()
    next(t for t in at.toggle if t.label == "Auslaufartikel anzeigen").set_value(True).run()
    assert at.session_state.v2_projekt.auslaufartikel
    at.session_state.v2_seite = "ergebnis"
    at.run()
    assert not at.exception


def test_katalogfehler_und_hinweistexte():
    a = KAT.artikel("CL5000iM 1C 53 E")
    assert a.datenfehler.startswith("Katalogfehler") and a.kuehl_min is None and a.kuehl_max is None
    assert "Q4/2026" in Z.G10_3_HINWEIS and "Q2/2026" not in Z.G10_3_HINWEIS
    p = beispielprojekt()
    p.aufstellung = "flachdach"
    k = next(k for k in A.konzepte(p, KAT) if k.empfohlen)
    assert A.aufstellungshinweise(p, k)[-1] == A.MONTAGE_HINWEIS
    assert "VDI 2078" in P_GEWERBE_HINWEIS()


def P_GEWERBE_HINWEIS():
    from splitklima import parameter
    return parameter.GEWERBE_HINWEIS


def test_oberflaeche_planung_zuruecksetzen(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    next(b for b in at.button if b.label == "Beispielhaus laden").click().run()
    p = at.session_state.v2_projekt
    p.aufstellung, p.zubehoer_mengen = "flachdach", {Z.NR_PUMPE_WAND: 2}
    at.session_state.v2_seite = "ergebnis"
    at.run()
    assert len(at.session_state.v2_projekt.raeume) == 7
    next(b for b in at.button if b.key == "reset-ja-nav").click().run()
    assert not at.exception
    q = at.session_state.v2_projekt
    assert q.raeume == [] and q.aufstellung == "" and q.zubehoer_mengen == {}
    assert at.session_state.v2_seite == "system" and q.config_id != p.config_id


def test_oberflaeche_entwicklerhinweis(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    assert any("Entwickelt von Daniel Sommer (HC/SDE3-PSD)" in m.value for m in at.markdown)


# ---------------------------------------------------------------- Planungs-Assistent
from splitklima.v2 import assistent as AS  # noqa: E402


def _werkzeuge(p=None):
    p = p or beispielprojekt()
    return p, AS._Werkzeuge(p, KAT, {})


def test_assistent_plan_drehen_dreht_alle_raeume():
    p, w = _werkzeuge()
    vorher = [[x.ausrichtung for x in r.waende] for r in p.raeume]
    _, fehler = w.ausfuehren("plan_drehen", {"grad_im_uhrzeigersinn": 180})
    assert not fehler
    gegenueber = {"N": "S", "S": "N", "O": "W", "W": "O", "NO": "SW", "SW": "NO", "SO": "NW", "NW": "SO"}
    assert [[x.ausrichtung for x in r.waende] for r in p.raeume] == [[gegenueber[a] for a in r] for r in vorher]
    assert w.log and "180°" in w.log[0]


def test_assistent_raum_aendern_und_grenzen():
    p, w = _werkzeuge()
    text, fehler = w.ausfuehren("raum_aendern", {"raum": "Küche", "flaeche": 20, "farbe": "schwarz"})
    assert not fehler and p.raeume[1].flaeche == 20 and p.raeume[1].farbe == "schwarz"
    assert "neuer_stand" in text
    _, fehler = w.ausfuehren("raum_aendern", {"raum": "Küche", "flaeche": 900})
    assert fehler and p.raeume[1].flaeche == 20  # Grenzwert 500 m² → abgelehnt, nichts geändert
    _, fehler = w.ausfuehren("raum_aendern", {"raum": "Kind", "hoehe": 3})
    assert fehler  # „Kind“ passt auf Kind 1 und Kind 2 → nicht eindeutig
    _, fehler = w.ausfuehren("raum_aendern", {"raum": "2", "raumart": "Sauna"})
    assert fehler and p.raeume[1].raumart == "Küche"


def test_assistent_daemmung_baujahr_und_loesung():
    p, w = _werkzeuge()
    heiz_vorher = gebaeude_last(p).heat
    assert not w.ausfuehren("projekt_einstellungen", {"baujahr": 1958})[1]
    assert p.einstellungen.daemmstandard == "old"
    heiz_alt = gebaeude_last(p).heat
    assert not w.ausfuehren("daemmung_setzen", {"art": "facade_1990"})[1]
    assert all(r.daemmung == "facade_1990" for r in p.raeume) and p.nachdaemmung == "facade_1990"
    assert gebaeude_last(p).heat < heiz_alt and heiz_alt > heiz_vorher
    assert not w.ausfuehren("loesung_waehlen", {"konzept": "single"})[1]
    assert w.zustand["konzept"] == "single"
    assert w.ausfuehren("loesung_waehlen", {"konzept": "gibtsnicht"})[1]


def test_assistent_raum_hinzufuegen_und_entfernen():
    p, w = _werkzeuge()
    assert not w.ausfuehren("raum_hinzufuegen", {"name": "Werkstatt", "raumart": "Werkstatt", "flaeche": 200,
                                                  "lage": "three"})[1]
    r = p.raeume[-1]
    assert r.name == "Werkstatt" and [x.laenge for x in r.waende] == [14.1, 14.1, 14.1]
    assert not w.ausfuehren("raum_entfernen", {"raum": "Werkstatt"})[1]
    assert all(x.name != "Werkstatt" for x in p.raeume)


def _mock_client(antworten, anfragen):
    import json as _json

    import anthropic
    import httpx2

    def handler(req):
        anfragen.append(_json.loads(req.content))
        a = antworten[len(anfragen) - 1]
        return httpx2.Response(200, json={"id": f"msg_{len(anfragen)}", "type": "message", "role": "assistant",
                                          "model": AS.MODELL, "content": a[0], "stop_reason": a[1],
                                          "stop_sequence": None, "usage": {"input_tokens": 1, "output_tokens": 1}})
    return anthropic.Anthropic(api_key="test", http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))


def test_assistent_dialog_mit_werkzeugen():
    anfragen = []
    client = _mock_client([
        ([{"type": "tool_use", "id": "a", "name": "raum_aendern", "input": {"raum": "1", "flaeche": 9999}}],
         "tool_use"),
        ([{"type": "tool_use", "id": "b", "name": "plan_drehen", "input": {"grad_im_uhrzeigersinn": 180}}],
         "tool_use"),
        ([{"type": "text", "text": "Plan gedreht."}], "end_turn"),
    ], anfragen)
    p = beispielprojekt()
    verlauf = []
    a = AS.antworten(verlauf, "Wohnzimmer liegt im Norden", p, KAT, {}, client=client)
    assert a.text == "Plan gedreht." and len(a.aenderungen) == 1
    assert a.nachher["kuehllast_kw"] < a.vorher["kuehllast_kw"]
    erste = anfragen[0]
    assert erste["model"] == "claude-opus-5-5" and erste["fallbacks"] == "default"
    assert erste["output_config"] == {"effort": "medium"} and erste["system"] == AS.SYSTEM
    assert {t["name"] for t in erste["tools"]} >= {"plan_drehen", "raum_aendern", "daemmung_setzen"}
    fehler_ergebnis = anfragen[1]["messages"][-1]["content"][0]
    assert fehler_ergebnis["is_error"] and "außerhalb" in fehler_ergebnis["content"]
    assert [m["role"] for m in anfragen[2]["messages"]] == ["user", "assistant", "user", "assistant", "user"]
    # Werkzeuge erlauben keinen Zugriff auf Code, Dateien oder Server
    assert not {t["name"] for t in AS.TOOLS} & {"bash", "datei", "code", "shell"}


def test_oberflaeche_assistent_chat_und_rueckgaengig(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.delenv("APP_PASSWORT", raising=False)

    def fake(verlauf, text, p, kat, zustand, client=None):
        vorher = AS.kurzstatus(p, kat)
        p.raeume[0].flaeche = 60.0
        return AS.Antwort("Wohnzimmer auf 60 m² vergrößert.", ["Wohnen/Essen: Fläche 60 m²"], vorher,
                          AS.kurzstatus(p, kat))

    monkeypatch.setattr(AS, "antworten", fake)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    next(b for b in at.button if b.label == "Beispielhaus laden").click().run()
    flaeche = at.session_state.v2_projekt.raeume[0].flaeche
    next(b for b in at.button if b.label == "Planungs-Assistent").click().run()
    assert at.session_state.v2_chat_offen and not at.exception
    at.chat_input[0].set_value("Wohnzimmer 60 m²").run()
    assert at.session_state.v2_projekt.raeume[0].flaeche == 60.0
    assert any("60 m² vergrößert" in m.value for m in at.markdown)
    next(b for b in at.button if b.label == "Rückgängig").click().run()
    assert at.session_state.v2_projekt.raeume[0].flaeche == flaeche
    assert not at.exception
