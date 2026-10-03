"""Oberfläche Version 2 – geführte Konfiguration im Stil eines Produktkonfigurators.

Links: Navigationsbaum mit Fortschritt · Mitte: Auswahlkarten mit Piktogrammen ·
rechts: Live-Zusammenfassung mit Produktbild, Lasten und Preis.
Gerechnet wird mit dem unveränderten Rechenkern (``splitklima.berechnung``), die
Geräteauswahl kommt aus ``splitklima.v2.auswahl`` (Gesamtsortiment aus dem Katalog).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pdx
from PIL import Image
import streamlit as st

from splitklima import parameter as P
from splitklima.berechnung import gebaeude_last, raum_last
from splitklima.ki_plan import (
    KiPlanAnalyse, PlanFehler, analysiere, baualter_aus_baujahr, in_raeume, schluessel_vorhanden,
)
from splitklima.modell import Fenstergruppe, Projekt, Raum, Wand
from splitklima.preise import fmt_eur, gesamtpreis
from splitklima.standort import finde_ort, klimaregion
from splitklima.v2 import auswahl as A
from splitklima.v2.angebot import pdf_angebot_v2
from splitklima.v2.bilder import bild, bild_innen_set
from splitklima.v2.katalog import FARBEN, Katalog
from splitklima.v2.piktogramme import svg

BEISPIEL = Path(__file__).parent / "splitklima" / "daten" / "beispiel_planerkennung.json"
MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp"}
MAX_MB = 30
BILD_MAX = 300  # px – Katalogbilder nicht stärker vergrößern (Quelle nur ~150 px breit)
BLAU = "#005691"

SCHRITTE = [("system", "System", ":material/hub:"), ("gebaeude", "Gebäude", ":material/home:"),
            ("raeume", "Räume", ":material/meeting_room:"), ("ergebnis", "Ergebnis", ":material/task_alt:")]
SYSTEME = [("auto", "Beste Lösung", "Wir vergleichen alle Varianten und empfehlen die wirtschaftlichste."),
           ("multi", "Multi-Split", "Eine Außeneinheit versorgt mehrere Räume."),
           ("single", "Single-Split", "Jeder Raum bekommt ein eigenes Set.")]
BETRIEB = [("both", "Kühlen & Heizen", "Ganzjährig nutzen – im Sommer kühlen, in der Übergangszeit heizen."),
           ("cool", "Nur Kühlen", "Angenehme Temperaturen an heißen Tagen."),
           ("heat", "Nur Heizen", "Effizient heizen mit Luft-Luft-Wärmepumpe.")]
VERGLASUNG = [("double", "Zweifach", "", "double"), ("triple", "Dreifach", "", "triple"),
              ("single", "Einfach", "", "single_glas")]
SONNENSCHUTZ = [("0.45", "Außen", "Rollladen, Raffstore", "0.45"), ("0.8", "Innen", "Vorhang, Plissee", "0.8"),
                ("1", "Keiner", "", "1")]
LAGE = [("outside", "1 Außen&shy;wand"), ("corner", "Eckraum"), ("three", "3 Außen&shy;wände"),
        ("inside", "Innen&shy;liegend"), ("attic", "Dach&shy;geschoss"), ("attic_corner", "DG-Eck&shy;raum"),
        ("basement", "Über Keller")]
RAUMART_KURZ = {"Wohnzimmer": "Wohnen", "Schlafzimmer": "Schlafen", "Büro": "Büro", "Küche": "Küche",
                "Kinderzimmer": "Kinder", "Badezimmer": "Bad"}
BAUART = [("", "Keine Präferenz", "egal"), ("Wandgerät", "Wandgerät", "Wandgerät"),
          ("Deckenkassette", "Deckenkassette", "Deckenkassette"), ("Konsole", "Konsole", "Konsole")]
FARBCODE = {"weiß": "#f4f5f6", "silber": "#c3c8cd", "schwarz": "#1d1f22", "anthrazit": "#41464d", "rot": "#c8102e"}

CSS = f"""
<style>
.block-container {{padding-top: 3.2rem; max-width: 1500px}}
/* kein blinkender Textcursor in normalem Text (nur in Eingabefeldern) */
body, .stApp {{caret-color: transparent}}
input, textarea, [contenteditable="true"] {{caret-color: auto !important}}
.stApp img {{image-rendering: auto}}
div[class*="st-key-zusammenfassung"], div[class*="st-key-ergebnis-karte"] {{overflow:hidden}}
.marke {{font-weight:700; font-size:1.45rem}} .marke b {{color:#e20015}} .marke span {{color:{BLAU}}}
.v2-badge {{display:inline-block; margin-left:.6rem; padding:.1rem .55rem; border-radius:1rem;
           background:#e8f1f8; color:{BLAU}; font-size:.75rem; font-weight:600; vertical-align:middle}}
/* Auswahlkarten: ganze Karte klickbar, gewählte Karte blau umrandet */
div[class*="st-key-karte-"] {{position:relative; transition:border-color .15s, box-shadow .15s; cursor:pointer;
                              border-radius:.6rem}}
div[class*="st-key-karte-"]:hover {{border-color:#7fa9cc !important; box-shadow:0 2px 10px rgba(0,86,145,.12)}}
div[class*="st-key-karte-"]:has(.karte.an) {{border:2px solid {BLAU} !important; background:#f2f7fb}}
div[class*="st-key-kbtn-"] {{position:absolute !important; inset:0 !important; width:100% !important;
                             height:100% !important; z-index:3; margin:0 !important}}
div[class*="st-key-kbtn-"] * {{width:100% !important; height:100% !important; max-width:none !important}}
div[class*="st-key-kbtn-"] button {{opacity:0; cursor:pointer}}
.karte {{text-align:center; color:{BLAU}; padding:.2rem 0}}
.karte .titel {{color:#1d2834; font-weight:600; margin-top:.25rem}}
.karte .sub {{color:#5c6773; font-size:.8rem; line-height:1.25; margin-top:.15rem}}
.karte.klein .titel {{font-size:.85rem; font-weight:500; overflow-wrap:normal; word-break:normal; hyphens:manual}}
.karte .haken {{position:absolute; top:.35rem; right:.5rem; color:{BLAU}; font-weight:700}}
.farbpunkt {{display:inline-block; width:38px; height:38px; border-radius:50%; border:1px solid #9aa4ad}}
.einheit {{color:#5c6773; padding-bottom:.85rem}}
/* Navigation links */
div[class*="st-key-nav"] button {{justify-content:flex-start}}
div[class*="st-key-nav"] button > div {{justify-content:flex-start; width:100%}}
div[class*="st-key-nav"] button > div > span {{justify-content:flex-start}}
div[class*="st-key-navr-"] button {{padding-left:2.3rem; min-height:2rem}}
div[class*="st-key-navr-"] button p {{font-size:.86rem}}
.fortschritt {{font-size:.8rem; color:#5c6773; margin-bottom:.2rem}}
.zs-zeile {{display:flex; justify-content:space-between; font-size:.88rem; padding:.12rem 0;
            border-bottom:1px solid #eef1f4}}
.zs-zeile span:first-child {{color:#5c6773}}
.preis {{font-size:1.9rem; font-weight:700; color:{BLAU}; line-height:1.1}}
.empf {{display:inline-block; background:{BLAU}; color:white; border-radius:1rem; padding:.1rem .6rem;
        font-size:.75rem; font-weight:600; letter-spacing:.03em}}
.hero-ki {{display:flex; gap:1rem; align-items:center; color:{BLAU}}}
.hero-ki > div:last-child {{color:#3a4652}}
.hero-ki h3 {{margin:0; color:#1d2834}}
.raumkopf {{display:flex; gap:.8rem; align-items:center; color:{BLAU}}}
.raumkopf .name {{font-weight:600; color:#1d2834}}
.raumkopf .info {{font-size:.8rem; color:#5c6773}}
</style>
"""


# ====================================================================== Hilfen
def de(x: float, nachkomma: int = 1) -> str:
    if float(x).is_integer() and nachkomma <= 1:
        return f"{x:.0f}"
    return f"{x:.{nachkomma}f}".replace(".", ",")


def _ss():
    return st.session_state


def _k(name: str) -> str:
    """Widget-Schlüssel; ändert sich, wenn das Projekt ersetzt wird."""
    return f"r{_ss().v2_rev}_{name}"


def gehe(seite: str, raum: int | None = None, erledigt: str | None = None) -> None:
    if erledigt:
        _ss().v2_erledigt.add(erledigt)
    _ss().v2_seite = seite
    if raum is not None:
        _ss().v2_raum = raum
    _ss().v2_oben = True
    st.rerun()


def _nach_oben() -> None:
    """Nach einem Seitenwechsel an den Seitenanfang springen – direkt im Dokument, ohne iframe
    (ein 1-px-iframe zeigte unter Windows einen Mini-Scrollbalken über der Zusammenfassung)."""
    if _ss().pop("v2_oben", False):
        _ss().v2_sprung = _ss().get("v2_sprung", 0) + 1  # neuer Inhalt → Skript läuft erneut
        st.html(f"<script>/* {_ss().v2_sprung} */ for (const s of ['[data-testid=\"stMain\"]', "
                "'[data-testid=\"stAppViewContainer\"]']) { const el = document.querySelector(s); "
                "if (el) el.scrollTo(0, 0); } window.scrollTo(0, 0);</script>", unsafe_allow_javascript=True)


def karten(key: str, optionen: list[tuple], wert, setzen, spalten: int = 3, klein: bool = False,
           groesse: int = 56) -> None:
    """Auswahlkarten mit Piktogramm. optionen: (wert, titel, untertitel, symbol | html)."""
    cols = st.columns(spalten)
    geklickt = None
    for i, (v, titel, sub, symbol) in enumerate(optionen):
        an = v == wert
        ikon = symbol if symbol.startswith("<") else svg(symbol, groesse)
        with cols[i % spalten].container(border=True, key=f"karte-{key}-{i}"):
            st.markdown(
                f'<div class="karte{" klein" if klein else ""}{" an" if an else ""}">'
                f'{"<span class=haken>✓</span>" if an else ""}<div>{ikon}</div><div class="titel">{titel}</div>'
                f'{f"<div class=sub>{sub}</div>" if sub else ""}</div>', unsafe_allow_html=True)
            if st.button(titel.replace("&shy;", ""), key=f"kbtn-{_k(key)}-{i}"):
                geklickt = v
    if geklickt is not None and geklickt != wert:
        setzen(geklickt)
        st.rerun()


def zahl(spalte, label: str, einheit: str, wert: float, mn: float, mx: float, schritt: float, key: str,
         fmt: str = "%.1f") -> float:
    """Zahlenfeld mit Einheit rechts daneben."""
    c1, c2 = spalte.columns([5, 1], vertical_alignment="bottom", gap="small")
    v = c1.number_input(label, mn, mx, float(min(max(wert, mn), mx)), schritt, format=fmt, key=_k(key))
    c2.markdown(f'<div class="einheit">{einheit}</div>', unsafe_allow_html=True)
    return float(v)


def _daemmstandard(baujahr: int) -> str:
    return "old" if baujahr < 1979 else "mid" if baujahr < 2002 else "new"


def baujahr_anwenden(p: Projekt) -> None:
    if not p.baujahr:
        return
    p.einstellungen.daemmstandard = _daemmstandard(p.baujahr)
    klasse = baualter_aus_baujahr(p.baujahr)
    for r in p.raeume:
        r.baualter = klasse


def neues_projekt(p: Projekt | None = None) -> None:
    p = p or Projekt(raeume=[])
    if p.baujahr is None:
        p.baujahr = 1995
    baujahr_anwenden(p)
    _ss().v2_projekt = p
    _ss().v2_rev = _ss().get("v2_rev", 0) + 1
    _ss().v2_geprueft = set()
    _ss().v2_erledigt = set()
    _ss().v2_seite = "system"
    _ss().v2_raum = 0
    for key in ("v2_ki_info", "v2_konzept", "v2_ack_zeit"):
        _ss().pop(key, None)


def _konzepte(p: Projekt, kat: Katalog) -> list[A.Konzept]:
    return A.konzepte(p, kat, p.systemwunsch) if p.raeume else []


def _gewaehlt(liste: list[A.Konzept]) -> A.Konzept | None:
    moeglich = [k for k in liste if k.gedeckt]
    if not moeglich:
        return None
    empf = next((k for k in moeglich if k.empfohlen), moeglich[0])
    return next((k for k in moeglich if k.key == _ss().get("v2_konzept")), empf)


def _bild_mittig(pfad: Path, max_breite: int) -> None:
    """Produktbild zentriert und höchstens etwa doppelt so groß wie die Vorlage."""
    breite = min(max_breite, Image.open(pfad).width)
    st.markdown(f'<div style="text-align:center"><img src="data:image/png;base64,{_b64(pfad)}" '
                f'style="width:{breite}px;max-width:100%"></div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _b64(pfad: Path) -> str:
    import base64
    return base64.b64encode(Path(pfad).read_bytes()).decode()


def _konzept_bilder(k: A.Konzept, max_anzahl: int = 3) -> list[Path]:
    pfade: list[Path] = []
    for t in k.teilsysteme:
        for a in t.artikel():
            pf = bild(a)
            if pf and pf not in pfade:
                pfade.append(pf)
    return pfade[:max_anzahl]


# ====================================================================== KI (das Herzstück)
def ki_bereich(p: Projekt, gross: bool) -> None:
    with st.container(border=True, key="ki-bereich"):
        if gross:
            st.markdown(f'<div class="hero-ki">{svg("ki", 64)}<div><h3>Grundriss hochladen – fertig.</h3>'
                        '<div>Die KI erkennt Räume, Flächen, Fenster und die Himmelsrichtung und füllt die '
                        'Konfiguration für Sie aus. Sie prüfen nur noch kurz.</div></div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown("**Grundrisse hochladen – Räume automatisch erkennen**")
        dateien = st.file_uploader("Pläne", type=["pdf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                                   label_visibility="collapsed", key="v2_upload")
        ki_bereit = schluessel_vorhanden()
        c1, c2, c3 = st.columns([2, 2, 2])
        with c3.popover("Zusatzangaben", width="stretch"):
            zusatz = st.text_area("Hinweise für die Erkennung", key="v2_zusatz",
                                  placeholder="z. B. Plan-Oben zeigt nach Nordost; Keller nicht klimatisieren")
        groesse = sum(len(f.getvalue()) for f in dateien or []) / 1e6
        if c1.button("Räume erkennen", type="primary", width="stretch", icon=":material/auto_awesome:",
                     disabled=not dateien or not ki_bereit or groesse > MAX_MB):
            with st.spinner("Die Pläne werden gelesen … das dauert 1–2 Minuten."):
                try:
                    ki_uebernehmen(p, analysiere(
                        [(f.getvalue(), MIME[Path(f.name).suffix.lower()]) for f in dateien], zusatz))
                except PlanFehler as fehler:
                    st.error(str(fehler))
        if c2.button("Beispielhaus laden", width="stretch", icon=":material/home_work:"):
            ki_uebernehmen(p, KiPlanAnalyse.model_validate_json(BEISPIEL.read_text("utf-8")))
        if groesse > MAX_MB:
            st.error(f"Zusammen {groesse:.0f} MB – bitte höchstens {MAX_MB} MB bzw. Geschosse einzeln hochladen.")
        elif not ki_bereit:
            st.caption("Automatische Erkennung ist hier nicht eingerichtet (API-Schlüssel fehlt) – "
                       "„Beispielhaus laden“ zeigt, wie es funktioniert.")
        else:
            st.caption("PDF, PNG oder JPG · alle Geschosse auf einmal möglich · die Pläne werden zur Auswertung "
                       "an die Claude API übertragen.")


def ki_uebernehmen(p: Projekt, analyse: KiPlanAnalyse) -> None:
    p.raeume = in_raeume(analyse) or p.raeume
    if analyse.baujahr and not _ss().get("v2_baujahr_manuell"):
        p.baujahr = analyse.baujahr
    baujahr_anwenden(p)
    _ss().v2_ki_info = {
        "hinweise": [f"Nordrichtung: {analyse.nordrichtung}", *analyse.hinweise],
        "aufstellorte": [(a.ort, a.begruendung) for a in analyse.aufstellorte_aussengeraet],
    }
    _ss().v2_toast = f"{len(p.raeume)} Räume erkannt – bitte kurz durchsehen."
    _ss().v2_geprueft = set()
    _ss().v2_rev += 1
    _ss().pop("v2_konzept", None)
    gehe("raeume", erledigt="system")


# ====================================================================== Seiten
def seite_system(p: Projekt) -> None:
    ki_bereich(p, gross=True)
    st.write("")
    st.markdown("#### Welches System wünschen Sie?")
    karten("sys", [(v, t, s, v) for v, t, s in SYSTEME], p.systemwunsch,
           lambda v: setattr(p, "systemwunsch", v))
    st.markdown("#### Was soll die Anlage leisten?")
    karten("ba", [(v, t, s, v) for v, t, s in BETRIEB], p.einstellungen.betriebsart,
           lambda v: setattr(p.einstellungen, "betriebsart", v))
    _weiter_zurueck(None, ("gebaeude", "Weiter zum Gebäude"), "system")


def seite_gebaeude(p: Projekt) -> None:
    e = p.einstellungen
    st.markdown("#### Wo steht das Gebäude?")
    c1, c2 = st.columns(2)
    p.name = c1.text_input("Projektname", p.name, key=_k("name"))
    ort = c2.text_input("PLZ oder Ort", p.ort, key=_k("ort"))
    treffer = finde_ort(ort)
    if ort != p.ort:
        p.ort = f"{treffer[0]} {treffer[1]}" if treffer else ort
        if treffer:
            p.plz = treffer[0]
            kr = klimaregion(p.plz)
            e.norm_aussen, e.sommer = kr.norm_aussen, kr.sommer
    kr = klimaregion(p.plz)
    c2.caption(f"Klimaregion {kr.name} · Auslegung Sommer {de(e.sommer)} °C · Winter {de(e.norm_aussen)} °C")

    st.markdown("#### Baujahr")
    c1, _ = st.columns([1, 2])
    bj = c1.number_input("Baujahr", 1850, datetime.now().year, int(p.baujahr or 1995), step=1, key=_k("bj"),
                         label_visibility="collapsed")
    if bj != p.baujahr:
        p.baujahr = int(bj)
        _ss().v2_baujahr_manuell = True
        baujahr_anwenden(p)
    st.caption({"old": "Altbau vor 1979 – wenig Dämmung", "mid": "Baujahr 1979–2001 – mittlerer Dämmstandard",
                "new": "ab 2002 – guter Dämmstandard (EnEV/GEG)"}[e.daemmstandard])

    st.markdown("#### Fenster")
    karten("glas", VERGLASUNG, e.verglasung, lambda v: setattr(e, "verglasung", v), klein=True, groesse=44)
    if e.sonnenschutz == "0.55":
        e.sonnenschutz = "0.45"
    st.markdown("#### Sonnenschutz")
    karten("shade", SONNENSCHUTZ, e.sonnenschutz, lambda v: setattr(e, "sonnenschutz", v), klein=True, groesse=44)
    _weiter_zurueck(("system", "System"), ("raeume", "Weiter zu den Räumen"), "gebaeude")


def _raum_neu(p: Projekt) -> None:
    neu = Raum(name=f"Raum {len(p.raeume) + 1}", lage="outside", waende=[Wand(ausrichtung="S", laenge=4, fenster=2)],
               geschoss=p.raeume[-1].geschoss if p.raeume else "EG")
    neu.baualter = baualter_aus_baujahr(p.baujahr) if p.baujahr else ""
    p.raeume.append(neu)
    _ss().v2_rev += 1
    gehe("raum", raum=len(p.raeume) - 1)


def seite_raeume(p: Projekt) -> None:
    if msg := _ss().pop("v2_toast", None):
        st.toast(msg, icon="✅")
    ki_bereich(p, gross=not p.raeume)
    info = _ss().get("v2_ki_info")
    st.write("")
    kopf_l, kopf_r = st.columns([3, 2], vertical_alignment="bottom")
    kopf_l.markdown(f"#### Ihre Räume ({len(p.raeume)})")
    if info and info["hinweise"]:
        with kopf_r.popover(f"Hinweise zur Erkennung ({len(info['hinweise'])})", width="stretch",
                            icon=":material/info:"):
            for h in info["hinweise"]:
                st.markdown(f"- {h}")

    if not p.raeume:
        st.caption("Noch keine Räume – Grundriss hochladen oder Räume von Hand anlegen.")
    spalten = st.columns(3)
    geprueft = _ss().v2_geprueft
    for i, r in enumerate(p.raeume):
        l = raum_last(r, p.einstellungen)
        status = "✓ geprüft" if i in geprueft else "bitte prüfen"
        with spalten[i % 3].container(border=True, key=f"karte-raum-{i}"):
            st.markdown(
                f'<div class="karte klein"><div>{svg(r.raumart, 44)}</div>'
                f'<div class="titel">{r.name}</div><div class="sub">{r.geschoss or "–"} · {de(r.flaeche)} m² · '
                f'{de(l.cool, 2)} kW Kühlen</div><div class="sub">{status}</div></div>', unsafe_allow_html=True)
            if st.button(f"{r.name} bearbeiten", key=f"kbtn-{_k('raum')}-{i}"):
                gehe("raum", raum=i)
    if st.button("Raum hinzufügen", icon=":material/add:"):
        _raum_neu(p)
    _weiter_zurueck(("gebaeude", "Gebäude"), ("ergebnis", "Zum Ergebnis") if p.raeume else None, "raeume")


def seite_raum(p: Projekt, i: int) -> None:
    if not p.raeume:
        gehe("raeume")
    i = min(i, len(p.raeume) - 1)
    r = p.raeume[i]
    _ss().v2_geprueft.add(i)

    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    c1.caption(f"RAUM {i + 1} VON {len(p.raeume)}")
    r.name = c1.text_input("Raumname", r.name, key=_k(f"rn{i}"))
    r.geschoss = c2.text_input("Geschoss", r.geschoss, key=_k(f"rg{i}"), placeholder="EG, OG, DG …")

    st.markdown("##### Nutzung")
    karten(f"ra{i}", [(v, RAUMART_KURZ[v], "", v) for v in P.RAUMARTEN], r.raumart, lambda v: setattr(r, "raumart", v),
           spalten=6, klein=True, groesse=40)

    st.markdown("##### Größe")
    c1, c2, _ = st.columns([1, 1, 1])
    r.flaeche = zahl(c1, "Grundfläche", "m²", r.flaeche or 1, 1.0, 500.0, 0.5, f"rf{i}")
    r.hoehe = zahl(c2, "Raumhöhe", "m", r.hoehe or 2.5, 1.8, 6.0, 0.05, f"rh{i}", "%.2f")

    st.markdown("##### Lage im Gebäude")

    def lage_setzen(v: str) -> None:
        r.setze_lage(v)
        _ss().v2_rev += 1

    karten(f"lage{i}", [(v, t, "", v) for v, t in LAGE], r.lage, lage_setzen, spalten=7, klein=True, groesse=40)
    if r.waende:
        wdf = st.data_editor(
            pdx.DataFrame([w.model_dump() for w in r.waende]), hide_index=True, width="stretch",
            num_rows="fixed", key=_k(f"rw{i}"),
            column_config={
                "ausrichtung": st.column_config.SelectboxColumn("Außenwand zeigt nach", options=P.AUSRICHTUNGEN,
                                                                required=True),
                "laenge": st.column_config.NumberColumn("Wandlänge (m)", min_value=0.0, step=0.1, required=True,
                                                        format="%.1f m"),
                "fenster": st.column_config.NumberColumn("Fensterfläche (m²)", min_value=0.0, step=0.1,
                                                         required=True, format="%.1f m²"),
            })
        r.waende = [Wand(**z) for z in wdf.to_dict("records")]
    else:
        st.caption("Innenliegender Raum – keine Außenwände.")
    if r.dach:
        df = sum(g.flaeche for g in r.fenstergruppen if g.dachfenster)
        c1, _ = st.columns([1, 2])
        neu = zahl(c1, "Dachfenster", "m²", df, 0.0, 50.0, 0.1, f"rdf{i}")
        if neu != df:
            r.fenstergruppen = [g for g in r.fenstergruppen if not g.dachfenster]
            if neu > 0:
                r.fenstergruppen.append(Fenstergruppe(ausrichtung="S", flaeche=neu, dachfenster=True))

    st.markdown("##### Gerätewunsch")
    wunsch = A.bauart_wunsch(r)
    karten(f"bau{i}", [(v, t, "", s) for v, t, s in BAUART], wunsch,
           lambda v: setattr(r, "ig_bauart", v or "auto"), spalten=4, klein=True, groesse=44)
    if wunsch in ("", "Wandgerät"):
        st.markdown("##### Farbe der Inneneinheit")
        farben = [("", "Keine Präferenz", "", '<span class="farbpunkt" style="background:linear-gradient('
                   '135deg,#f4f5f6 50%,#c3c8cd 50%)"></span>')]
        farben += [(f, f.capitalize(), "", f'<span class="farbpunkt" style="background:{FARBCODE[f]}"></span>')
                   for f in FARBEN]
        karten(f"farbe{i}", farben, r.farbe, lambda v: setattr(r, "farbe", v), spalten=6, klein=True)
        if r.farbe and r.farbe != "weiß":
            st.caption("Farbige Inneneinheiten gibt es in den Serien Climate 7000i (silber, schwarz) und "
                       "Climate Class 8000i (anthrazit, silber, rot).")
    elif wunsch:
        st.caption(f"{wunsch}n werden als Multi-Split-Inneneinheit eingesetzt (auch 1:1 an einer Außeneinheit).")

    st.write("")
    c1, c2, c3 = st.columns([1, 1, 2])
    if c3.button("Raum entfernen", icon=":material/delete:", type="tertiary"):
        p.raeume.pop(i)
        _ss().v2_geprueft = {j if j < i else j - 1 for j in _ss().v2_geprueft if j != i}
        _ss().v2_rev += 1
        gehe("raeume")
    zurueck = ("raum", i - 1) if i > 0 else ("raeume", None)
    weiter = ("raum", i + 1) if i < len(p.raeume) - 1 else ("ergebnis", None)
    if c1.button("Zurück", icon=":material/arrow_back:", width="stretch"):
        gehe(zurueck[0], raum=zurueck[1])
    if c2.button("Nächster Raum" if weiter[0] == "raum" else "Zum Ergebnis", type="primary", width="stretch",
                 icon=":material/arrow_forward:"):
        gehe(weiter[0], raum=weiter[1], erledigt="raeume" if weiter[0] == "ergebnis" else None)


def _teilsystem_karte(t: A.Teilsystem, p: Projekt) -> None:
    with st.container(border=True):
        c1, c2 = st.columns([1, 2], vertical_alignment="center")
        haupt = t.set or t.aussen
        if (pf := bild(haupt)) is not None:
            c1.image(str(pf), width=min(BILD_MAX, Image.open(pf).width))
        with c2:
            st.markdown(f"**{t.bezeichnung}** · {'Single-Split-Set' if t.set else 'Multi-Split'}")
            st.caption(f"{haupt.typ if haupt else '–'} · Kühlen {de(t.leistung_kuehl, 1)} kW · "
                       f"Heizen {de(t.leistung_heiz, 1)} kW")
            geraete = [(r, t.set) for r in t.raeume] if t.set else t.innen
            for r, u in geraete:
                farbe = f" · {u.farbe}" if u.farbe and u.farbe != "weiß" else ""
                st.markdown(f"<span style='font-size:.88rem'>▸ {r.name}: {u.typ if t.aussen else 'Inneneinheit'}"
                            f"{farbe}</span>", unsafe_allow_html=True)


def seite_ergebnis(p: Projekt, kat: Katalog) -> None:
    liste = _konzepte(p, kat)
    gewaehlt = _gewaehlt(liste)
    if gewaehlt is None:
        st.error("Für diese Räume gibt es mit dem gewählten System keine passende Lösung im Sortiment. "
                 "Bitte ein anderes System oder eine andere Bauart wählen oder große Räume aufteilen.")
        for k in liste:
            for h in k.hinweise:
                st.caption(h)
        _weiter_zurueck(("raeume", "Räume"), None, "ergebnis")
        return
    moeglich = [k for k in liste if k.gedeckt]
    empfohlen = next((k for k in moeglich if k.empfohlen), moeglich[0])
    preis = gewaehlt.preis
    last = gebaeude_last(p)

    # ------------------------------------------------------------ Ergebnis-Karte
    with st.container(border=True, key="ergebnis-karte"):
        bilder = _konzept_bilder(gewaehlt)
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        with c1:
            st.markdown('<span class="empf">UNSERE EMPFEHLUNG</span>' if gewaehlt is empfohlen
                        else '<span class="empf" style="background:#5c6773">IHRE AUSWAHL</span>',
                        unsafe_allow_html=True)
            st.markdown(f"## {gewaehlt.name}")
            st.markdown(gewaehlt.beschreibung)
            st.caption(gewaehlt.geraete_text)
        with c2:
            st.markdown(f'<div class="preis">{fmt_eur(preis)}</div>', unsafe_allow_html=True)
            st.caption(f"Gerätepreis · {kat.preisbasis}")
            if gewaehlt is not empfohlen:
                st.caption(f"Empfohlen wäre: {empfohlen.name} ({fmt_eur(empfohlen.preis)})")
        if bilder:
            for sp, pf in zip(st.columns(len(bilder) + 1), bilder):
                sp.image(str(pf), width=min(BILD_MAX, Image.open(pf).width))
        m = st.columns(4)
        m[0].metric("Außengeräte", gewaehlt.aussengeraete)
        m[1].metric("Innengeräte", gewaehlt.innengeraete)
        m[2].metric("Kühlleistung", f"{de(gewaehlt.leistung_kuehl)} kW", help="Summe Nennleistung Außengeräte")
        m[3].metric("Kühllast Gebäude", f"{de(last.cool)} kW", help="Rechenkern CALC-0.4, mit Gleichzeitigkeit")

    # ------------------------------------------------------------ Alternativen
    andere = [k for k in moeglich if k is not gewaehlt]
    if andere:
        st.markdown("##### Alternativen")
        spalten = st.columns(len(andere))
        for sp, k in zip(spalten, andere):
            with sp.container(border=True):
                pk = k.preis
                diff = (pk - preis) if (pk is not None and preis is not None) else None
                st.markdown(f"**{k.name}**" + ("  ·  Empfehlung" if k.empfohlen else ""))
                st.caption(f"{k.aussengeraete} Außengerät{'e' if k.aussengeraete != 1 else ''} · {fmt_eur(pk)}"
                           + (f" ({'+' if diff >= 0 else '−'}{fmt_eur(abs(diff))})" if diff else ""))
                if st.button("Auswählen", key=f"wahl_{k.key}", width="stretch"):
                    _ss().v2_konzept = k.key
                    _ss().v2_oben = True
                    st.rerun()

    st.markdown("##### Ihre Geräte")
    sp = st.columns(2)
    for j, t in enumerate(gewaehlt.teilsysteme):
        with sp[j % 2]:
            _teilsystem_karte(t, p)

    # ------------------------------------------------------------ Details (eingeklappt)
    with st.expander("Stückliste mit Preisen", icon=":material/receipt_long:"):
        st.dataframe(pdx.DataFrame([{
            "Artikel": x.name, "Bestell-Nr.": x.artikel, "Menge": x.menge, "Einzelpreis": fmt_eur(x.einzelpreis),
            "Summe": fmt_eur(x.summe)} for x in gewaehlt.stueckliste()]), hide_index=True, width="stretch")
        st.markdown(f"**Summe Geräte: {fmt_eur(preis)}**")
        st.caption(f"{kat.preisbasis} · {kat.quelle}")
    optional = A.optionale_leistungen(gewaehlt, kat)
    if optional:
        with st.expander("Optional: Inbetriebnahme durch den Bosch-Kundendienst", icon=":material/build:"):
            st.dataframe(pdx.DataFrame([{
                "Leistung": x.name, "Bestell-Nr.": x.artikel, "Menge": x.menge,
                "Einzelpreis": fmt_eur(x.einzelpreis), "Summe": fmt_eur(x.summe)} for x in optional]),
                hide_index=True, width="stretch")
            st.markdown(f"**Summe optional: {fmt_eur(gesamtpreis(optional))}** – nicht im Gerätepreis enthalten.")
    with st.expander("Räume und Lasten", icon=":material/thermostat:"):
        zeilen = []
        for b in A.bedarfe(p):
            zeilen.append({"Raum": f"{b.raum.geschoss} {b.raum.name}".strip(), "Fläche m²": b.raum.flaeche,
                           "Kühllast kW": round(b.kuehl, 2), "Heizlast kW": round(b.heiz, 2)})
        st.dataframe(pdx.DataFrame(zeilen), hide_index=True, width="stretch")
        st.caption(f"Gebäude gesamt: Kühlen {de(last.cool, 2)} kW · Heizen {de(last.heat, 2)} kW "
                   "(Rechenkern CALC-0.4, in Anlehnung an VDI 2078 / DIN EN 12831-1)")
    hinweise = gewaehlt.lieferhinweise + gewaehlt.hinweise
    if hinweise:
        with st.expander(f"Hinweise ({len(hinweise)})", icon=":material/info:"):
            for h in hinweise:
                st.markdown(f"- {h}")
    info = _ss().get("v2_ki_info")
    if info and info["aufstellorte"]:
        with st.expander("Mögliche Aufstellorte für Außengeräte", icon=":material/location_on:"):
            for ort, grund in info["aufstellorte"]:
                st.markdown(f"- **{ort}** – {grund}")

    # ------------------------------------------------------------ Abschluss
    st.write("")
    with st.container(border=True):
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        with c1:
            ok = st.checkbox("Ich habe die Hinweise zur überschlägigen Auslegung gelesen.", key=_k("ack"))
            with st.popover("Hinweise anzeigen"):
                for h in P.HAFTUNGSHINWEISE:
                    st.markdown(f"- {h}")
        with c2:
            if ok:
                _ss().setdefault("v2_ack_zeit", datetime.now().strftime("%d.%m.%Y %H:%M"))
                st.download_button("Angebotsübersicht (PDF)", width="stretch", type="primary",
                                   icon=":material/picture_as_pdf:",
                                   data=pdf_angebot_v2(p, gewaehlt, kat, _ss().v2_ack_zeit),
                                   file_name=f"Split_Klima_Angebot_{p.config_id}.pdf", mime="application/pdf")
            else:
                st.button("Angebotsübersicht (PDF)", width="stretch", disabled=True, icon=":material/picture_as_pdf:",
                          help="Bitte zuerst die Hinweise bestätigen.")
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button("Zurück", icon=":material/arrow_back:", width="stretch"):
        gehe("raeume")
    if c2.button("Neues Projekt", icon=":material/restart_alt:", width="stretch"):
        neues_projekt()
        st.rerun()


def _weiter_zurueck(zurueck: tuple[str, str] | None, weiter: tuple[str, str] | None, hier: str) -> None:
    st.write("")
    c1, c2, _ = st.columns([1, 1.4, 1.6])
    if zurueck and c1.button("Zurück", icon=":material/arrow_back:", width="stretch", key=f"zur_{hier}"):
        gehe(zurueck[0])
    if weiter and c2.button(weiter[1], type="primary", icon=":material/arrow_forward:", width="stretch",
                            key=f"weiter_{hier}"):
        gehe(weiter[0], erledigt=hier)


# ====================================================================== Navigation und Zusammenfassung
def navigation(p: Projekt) -> None:
    seite = _ss().v2_seite
    erledigt = _ss().v2_erledigt
    geprueft = _ss().v2_geprueft
    teile = 3 + len(p.raeume)
    fertig = len(erledigt & {"system", "gebaeude", "raeume"}) + len(geprueft & set(range(len(p.raeume))))
    anteil = fertig / teile if teile else 0
    with st.container(border=True):
        st.markdown(f'<div class="fortschritt">Fortschritt {round(anteil * 100)} %</div>', unsafe_allow_html=True)
        st.progress(anteil)
        for key, titel, icon in SCHRITTE:
            aktiv = seite == key or (key == "raeume" and seite == "raum")
            haken = "  ✓" if key in erledigt else ""
            if st.button(f"{titel}{haken}", key=f"nav-{key}", icon=icon, width="stretch",
                         type="primary" if aktiv else "tertiary",
                         disabled=key == "ergebnis" and not p.raeume):
                gehe(key)
            if key == "raeume":
                for i, r in enumerate(p.raeume):
                    zeichen = "✓" if i in geprueft else "○"
                    if st.button(f"{zeichen}  {r.name}", key=f"navr-{i}", width="stretch",
                                 type="secondary" if seite == "raum" and _ss().v2_raum == i else "tertiary"):
                        gehe("raum", raum=i)


def zusammenfassung(p: Projekt, kat: Katalog) -> None:
    e = p.einstellungen
    with st.container(border=True, key="zusammenfassung"):
        st.markdown("**Ihre Konfiguration**")
        gewaehlt = _gewaehlt(_konzepte(p, kat)) if p.raeume else None
        if gewaehlt:
            bilder = _konzept_bilder(gewaehlt, 2)
            if bilder:
                _bild_mittig(bilder[0], 260)
            st.markdown(f"**{gewaehlt.name}**")
            st.caption(gewaehlt.geraete_text)
            st.markdown(f'<div class="preis">{fmt_eur(gewaehlt.preis)}</div>', unsafe_allow_html=True)
            st.caption("Gerätepreis, UVP netto")
        elif p.raeume:
            st.caption("Noch keine passende Gerätekombination – Räume oder Gerätewunsch anpassen.")
        else:
            st.markdown(f'<div style="color:{BLAU};text-align:center">{svg("haus", 72)}</div>',
                        unsafe_allow_html=True)
            st.caption("Sobald Räume erfasst sind, sehen Sie hier live den Vorschlag mit Preis.")

        zeilen = [("System", dict((v, t) for v, t, _ in SYSTEME)[p.systemwunsch]),
                  ("Betrieb", dict((v, t) for v, t, _ in BETRIEB)[e.betriebsart]),
                  ("Standort", p.ort), ("Baujahr", str(p.baujahr or "–"))]
        if p.raeume:
            last = gebaeude_last(p)
            zeilen += [("Räume", f"{len(p.raeume)} · {de(sum(r.flaeche for r in p.raeume))} m²"),
                       ("Kühllast", f"{de(last.cool, 2)} kW"), ("Heizlast", f"{de(last.heat, 2)} kW")]
        st.markdown("".join(f'<div class="zs-zeile"><span>{a}</span><span>{b}</span></div>' for a, b in zeilen)
                    + '<div style="height:.6rem"></div>',
                    unsafe_allow_html=True)

        if _ss().v2_seite == "raum" and p.raeume:
            r = p.raeume[min(_ss().v2_raum, len(p.raeume) - 1)]
            l = raum_last(r, e)
            st.write("")
            st.markdown(f"**{r.name}** – live berechnet")
            c1, c2 = st.columns(2)
            c1.metric("Kühllast", f"{de(l.cool, 2)} kW")
            c2.metric("Heizlast", f"{de(l.heat, 2)} kW")
            if gewaehlt:
                for t in gewaehlt.teilsysteme:
                    for rr, u in ([(x, t.set) for x in t.raeume] if t.set else t.innen):
                        if rr is r and u is not None:
                            pf = bild_innen_set(u) if t.set else bild(u)
                            if pf:
                                _bild_mittig(pf, 220)
                            st.caption(f"Vorschlag: {u.typ}")


# ====================================================================== Einstieg
def app_v2(kat: Katalog) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    if "v2_projekt" not in _ss():
        neues_projekt()
    p: Projekt = _ss().v2_projekt
    _nach_oben()

    links, mitte, rechts = st.columns([1.05, 3, 1.35], gap="medium")
    seite = _ss().v2_seite
    with mitte:
        if seite == "system":
            seite_system(p)
        elif seite == "gebaeude":
            seite_gebaeude(p)
        elif seite == "raeume":
            seite_raeume(p)
        elif seite == "raum":
            seite_raum(p, _ss().v2_raum)
        else:
            seite_ergebnis(p, kat)
    with links:
        navigation(p)
    with rechts:
        zusammenfassung(p, kat)
