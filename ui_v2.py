"""Oberfläche Version 2 – geführte Konfiguration im Stil eines Produktkonfigurators.

Links: Navigationsbaum mit Fortschritt · Mitte: Auswahlkarten mit Piktogrammen ·
rechts: Live-Zusammenfassung mit Produktbild, Lasten und Preis.
Gerechnet wird mit dem unveränderten Rechenkern (``splitklima.berechnung``), die
Geräteauswahl kommt aus ``splitklima.v2.auswahl`` (Gesamtsortiment aus dem Katalog).
"""

from __future__ import annotations

import os
import tempfile
import threading
from datetime import datetime
from functools import lru_cache
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
from splitklima import klima_plz as KP
from splitklima import klimadaten as KD
from splitklima.standort import klimaregion
from splitklima.v2 import auswahl as A
from splitklima.v2.angebot import pdf_angebot_v2
from splitklima.v2.bilder import bild, bild_innen_set
from splitklima.v2 import assistent as AS
from splitklima.v2 import speichern as SP
from splitklima.v2 import zubehoer as Z
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
DG_LAGEN = ("attic", "attic_corner")
ENTWICKLER = "Entwickelt von Daniel Sommer (HC/SDE3-PSD)"
ASSISTENT_AKTIV = os.environ.get("ASSISTENT", "1") != "0"  # ASSISTENT=0 blendet den Chat aus
BEISPIELE = ["Der Plan hat keinen Nordpfeil – das Wohnzimmer liegt im Norden.",
             "Das Haus ist von 1958, die Fassade wurde 1990 gedämmt.",
             "Geht es günstiger? Die Farbe ist mir egal."]
RAUMART_KURZ = {"Wohnzimmer": "Wohnen", "Schlafzimmer": "Schlafen", "Büro": "Büro", "Küche": "Küche",
                "Kinderzimmer": "Kinder", "Badezimmer": "Bad", "Werkstatt": "Werkstatt",
                "Halle / Lager": "Halle / Lager", "Verkaufsraum": "Laden"}
RAUMARTEN_ALLE = [*P.RAUMARTEN, *P.RAUMARTEN_GEWERBE]
LINIEN_BILD = {"3200i": "set_3200i", "7000i": "set_7000i_weiss", "8000i": "set_8000i_weiss"}
BAUART = [("", "Keine Präferenz", "egal"), ("Wandgerät", "Wandgerät", "Wandgerät"),
          ("Deckenkassette", "Decken&shy;kassette", "Deckenkassette"), ("Konsole", "Konsole", "Konsole"),
          ("Truhe/Decke", "Truhe / Decke", "Truhe/Decke")]
DACHFORMEN = [("flat", "Flachdach", "dach_flach"), ("saddle_south", "Sattel&shy;dach Süd", "dach_sued"),
              ("saddle_north", "Sattel&shy;dach Nord", "dach_nord"),
              ("saddle_eastwest", "Sattel&shy;dach Ost/West", "dach_ow")]
AUFSTELLUNG_UNTERTITEL = {"": "Entscheiden wir später.", "wand": "Wandkonsole an der Fassade.",
                          "boden": "Bodenkonsole vor dem Haus, z. B. Garten oder Terrasse.",
                          "flachdach": "Bodenkonsole auf dem Flachdach, ohne Dachdurchdringung."}
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
/* Streamlit setzt -1rem unter Textblöcke – in Karten würde der Inhalt sonst über den Rand rutschen */
div[class*="st-key-karte-"] [data-testid="stMarkdownContainer"] {{margin-bottom:0 !important}}
.karte .sub, .karte .titel {{hyphens:manual; -webkit-hyphens:manual; overflow-wrap:normal; word-break:normal}}
.entwickler {{text-align:center; color:#8a949e; font-size:.78rem; padding:1.6rem 0 .4rem;
              border-top:1px solid #eef1f4; margin-top:1rem}}
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
.einheit {{white-space:nowrap}}
.zs-zeile {{gap:.6rem}} .zs-zeile span:last-child {{text-align:right}}
[data-testid="stMetricValue"] {{font-size:clamp(1.35rem, 2.3vw, 2.25rem) !important}}
[data-testid="stMetricValue"] > div {{overflow:visible !important; text-overflow:clip !important}}
/* ---------- Planungs-Assistent: Chat-Blase unten rechts */
.st-key-chatfab {{position:fixed !important; right:1.6rem; bottom:1.6rem; z-index:1002; width:auto !important}}
.st-key-chatfab button {{background:{BLAU} !important; color:white !important; border:none !important;
    border-radius:2rem !important; padding:.75rem 1.2rem !important; box-shadow:0 6px 20px rgba(0,86,145,.35)}}
.st-key-chatfab button:hover {{filter:brightness(1.1)}}
.st-key-chatpanel {{position:fixed !important; right:1.6rem; bottom:1.6rem; z-index:1002; width:400px !important;
    max-height:calc(100vh - 6rem); overflow-y:auto; background:white; border:1px solid #dfe3e8;
    border-radius:1rem; box-shadow:0 12px 40px rgba(0,0,0,.18); padding:.8rem 1rem .6rem}}
.st-key-chatpanel [data-testid="stChatMessage"] {{padding:.4rem .2rem}}
.st-key-chatpanel [data-testid="stChatMessage"] p {{font-size:.9rem}}
.chat-titel {{font-weight:700; color:{BLAU}}}
.zub-gruppe {{font-size:.78rem; font-weight:600; color:{BLAU}; text-transform:uppercase; letter-spacing:.04em;
               margin:.8rem 0 .1rem; padding-bottom:.2rem; border-bottom:1px solid #e3e8ed}}
div[class*="st-key-zubrow-"] {{border-bottom:1px solid #f0f2f5; padding:.15rem 0}}
.zub-bild {{width:56px; height:56px; object-fit:contain; border-radius:.3rem; background:white}}
.zub-name {{font-weight:600; font-size:.9rem; color:#1d2834}}
.zub-info {{font-size:.78rem; color:#5c6773}}
.zub-warum {{font-size:.78rem; color:{BLAU}}}
.zub-summe {{text-align:right; font-weight:600; font-size:.9rem; white-space:nowrap}}
.zub-gesperrt-titel {{font-size:.82rem; color:#8a949e; margin:.4rem 0 .2rem}}
.zub-gesperrt {{display:grid; grid-template-columns:44px 1fr auto; gap:.7rem; align-items:center; padding:.3rem .5rem;
               border:1px dashed #d5dbe1; border-radius:.4rem; margin-bottom:.3rem; color:#9aa4ad; font-size:.82rem;
               background:#fafbfc}}
.zub-gesperrt img {{width:40px; height:30px; object-fit:contain; filter:grayscale(1); opacity:.5}}
.zub-gesperrt b {{font-weight:600; color:#8a949e}}
.st-key-chatpanel > div > [data-testid="stHorizontalBlock"], .st-key-chatpanel [data-testid="stHorizontalBlock"] {{
    flex-wrap:nowrap !important}}
.st-key-chatpanel [data-testid="stColumn"] {{min-width:0 !important}}
body:has(.st-key-chatpanel) .mobilpreis {{display:none !important}}
/* ---------- Smartphone/Tablet: Schrittleiste und Preisleiste (Desktop ausgeblendet) */
.st-key-mobilnav, .mobilpreis {{display:none !important}}
@media (max-width: 1024px) {{
  .block-container {{padding-left:1rem; padding-right:1rem; padding-top:2.6rem}}
  .st-key-mobilnav {{display:flex !important}}
  /* linke Navigationsspalte ausblenden – ersetzt durch die Schrittleiste */
  [data-testid="stColumn"]:has(.st-key-navspalte) {{display:none !important}}
  .st-key-mobilnav [data-testid="stHorizontalBlock"] {{flex-wrap:nowrap !important; gap:.35rem !important}}
  .st-key-mobilnav [data-testid="stColumn"] {{min-width:0 !important}}
  .st-key-mobilnav button {{padding:.3rem .2rem !important; min-height:2.3rem}}
  .st-key-mobilnav button p {{font-size:.82rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis}}
  /* Auswahlkarten als umbrechendes Raster in Lesereihenfolge */
  [class*="st-key-kgrid-"] {{display:grid !important; gap:.6rem !important;
                              grid-template-columns:repeat(auto-fill, minmax(6.4rem, 1fr))}}
  [class*="st-key-kgrid-"]:has(.karte:not(.klein)) {{grid-template-columns:repeat(auto-fill, minmax(13rem, 1fr))}}
  [class*="st-key-kgrid-"] > [data-testid="stLayoutWrapper"],
  [class*="st-key-kgrid-"] [data-testid="stHorizontalBlock"] {{display:contents !important}}
  [class*="st-key-kgrid-"] [data-testid="stColumn"] {{min-width:0 !important; width:auto !important}}
  [class*="st-key-kgrid-"] [data-testid="stColumn"]:not(:has(.karte)) {{display:none !important}}
  /* Zahlenfeld + Einheit bleiben nebeneinander */
  [class*="st-key-zahl-"] [data-testid="stHorizontalBlock"] {{flex-wrap:nowrap !important}}
  [class*="st-key-zahl-"] [data-testid="stColumn"] {{min-width:0 !important}}
  [class*="st-key-wz-"] button p {{white-space:normal}}
  [data-testid="stMain"] [data-testid="stButton"] button p, [data-testid="stDownloadButton"] button p {{
      white-space:normal !important; overflow:visible !important; text-overflow:clip !important}}
  [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {{white-space:normal !important;
      overflow:visible !important; text-overflow:clip !important}}
  div[class*="st-key-zubrow-"] [data-testid="stHorizontalBlock"] {{flex-wrap:wrap !important}}
  div[class*="st-key-zubrow-"] [data-testid="stColumn"]:nth-child(1) {{min-width:60px !important; flex:0 0 60px !important}}
  div[class*="st-key-zubrow-"] [data-testid="stColumn"]:nth-child(2) {{min-width:0 !important; flex:1 1 calc(100% - 80px) !important}}
  div[class*="st-key-zubrow-"] [data-testid="stColumn"]:nth-child(3),
  div[class*="st-key-zubrow-"] [data-testid="stColumn"]:nth-child(4) {{min-width:0 !important; flex:1 1 40% !important}}
  [data-testid="stCheckbox"] label, [data-testid="stCheckbox"] label p {{white-space:normal !important;
      overflow:visible !important; text-overflow:clip !important}}
}}
@media (max-width: 640px) {{
  .block-container {{padding-bottom:5.5rem; padding-top:3.8rem}}
  .st-key-chatfab {{bottom:5.2rem; right:1rem}}
  .st-key-chatpanel {{left:0; right:0 !important; bottom:0 !important; width:auto !important; max-height:88vh;
                      border-radius:1rem 1rem 0 0}}
  .st-key-chatverlauf {{height:auto !important; max-height:52vh}}
  [data-testid="stImage"] img, [data-testid="stMarkdownContainer"] img:not(.karte img), .stHtml img {{
      max-height:140px; width:auto !important; max-width:100%; object-fit:contain}}
  .st-key-zusammenfassung img {{display:none}}  /* Preis steht in der festen Leiste unten */
  [class*="st-key-kgrid-"]:has(.karte.klein .sub) {{grid-template-columns:repeat(2, minmax(0, 1fr))}}
  .marke {{font-size:1.15rem}}
  /* große Karten: Symbol links, Text rechts */
  [class*="st-key-kgrid-"]:has(.karte:not(.klein)) {{grid-template-columns:1fr}}
  [class*="st-key-kgrid-"] {{grid-template-columns:repeat(3, minmax(0, 1fr))}}
  .karte:not(.klein) {{display:grid; grid-template-columns:auto 1fr; column-gap:.9rem; align-items:center;
                       text-align:left; padding:0}}
  .karte:not(.klein) > div:nth-of-type(1) {{grid-row:span 2}}
  .karte:not(.klein) > div:nth-of-type(1) svg, .karte:not(.klein) > div:nth-of-type(1) img {{height:42px !important;
                       width:auto !important}}
  .karte:not(.klein) .titel {{margin-top:0}}
  .karte.klein svg {{width:34px; height:34px}}
  .karte.klein .titel {{font-size:.78rem}}
  .farbpunkt {{width:30px; height:30px}}
  /* Kennzahlen und Produktbilder im Ergebnis: 2 je Zeile */
  .st-key-kennzahlen [data-testid="stColumn"], .st-key-konzeptbilder [data-testid="stColumn"] {{
      min-width:calc(50% - 1rem) !important}}
  .st-key-konzeptbilder [data-testid="stColumn"]:not(:has(img)) {{display:none}}
  [class*="st-key-wz-"]:not(.st-key-wz-raum) [data-testid="stHorizontalBlock"] {{flex-wrap:nowrap !important}}
  [class*="st-key-wz-"]:not(.st-key-wz-raum) [data-testid="stColumn"] {{min-width:0 !important}}
  [class*="st-key-wz-"] [data-testid="stColumn"]:last-child:not(:has(button)) {{display:none}}
  .st-key-wz-raum [data-testid="stColumn"] {{min-width:calc(50% - .5rem) !important}}
  .st-key-wz-raum [data-testid="stColumn"]:last-child {{min-width:100% !important}}
  /* feste Preisleiste unten */
  .mobilpreis {{display:flex !important; position:fixed; left:0; right:0; bottom:0; z-index:1000;
               justify-content:space-between; align-items:center; gap:.8rem; padding:.6rem 1rem;
               background:white; border-top:1px solid #dfe3e8; box-shadow:0 -4px 14px rgba(0,0,0,.08)}}
  .mp-name {{font-weight:600; font-size:.9rem; color:#1d2834}}
  .mp-info {{font-size:.75rem; color:#5c6773}}
  .mp-preis {{font-size:1.35rem; font-weight:700; color:{BLAU}; white-space:nowrap}}
}}
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
    geklickt = None
    raster = st.container(key=f"kgrid-{key}")  # Smartphone/Tablet: per CSS als umbrechendes Raster
    cols: list = []
    for i, (v, titel, sub, symbol) in enumerate(optionen):
        an = v == wert
        ikon = symbol if symbol.startswith("<") else svg(symbol, groesse)
        if i % spalten == 0:
            cols = raster.columns(spalten)
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
    c1, c2 = spalte.container(key=f"zahl-{key}").columns([5, 1], vertical_alignment="bottom", gap="small")
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


def neues_projekt(p: Projekt | None = None, geladen: bool = False) -> None:
    p = p or Projekt(raeume=[])
    if p.baujahr is None:
        p.baujahr = 1995
    if not geladen:  # gespeicherte Konfiguration: Dämmstandard/Baualter so lassen, wie gespeichert
        baujahr_anwenden(p)
    _ss().v2_projekt = p
    _ss().v2_rev = _ss().get("v2_rev", 0) + 1
    if not p.klima_quelle and (start := KP.eintrag(p.plz)):
        standort_setzen(p, start)
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
    st.markdown("#### Bevorzugte Gerätelinie")

    def linien_ikon(v: str) -> str:
        if v not in LINIEN_BILD:
            return svg("auto", 56)
        pfad = Path(__file__).parent / "splitklima" / "daten" / "bilder" / f"{LINIEN_BILD[v]}.png"
        return f'<img src="data:image/png;base64,{_b64(pfad)}" style="height:56px">'

    untertitel = {"": "Wir wählen die günstigste passende Lösung.", "3200i": "Solide Wandgeräte, günstig.",
                  "7000i": "Leise, BEG-förderfähig mit MSG-1, auch silber/schwarz.",
                  "8000i": "Design-Linie, anthrazit/silber/rot – nur als Set."}
    karten("linie", [(v, t, untertitel[v], linien_ikon(v)) for v, t in A.GERAETELINIEN.items()], p.geraetelinie,
           lambda v: (setattr(p, "geraetelinie", v), _ss().pop("v2_konzept", None)), spalten=4, klein=True)
    auslauf = st.toggle("Auslaufartikel anzeigen", p.auslaufartikel, key=_k("auslauf"),
                        help="Geräte, die im Ergänzungskatalog 09/2026 nicht mehr enthalten sind: "
                             "Climate 3000i (Sets und Multi-Inneneinheiten) und CLC8001i-Set 35. "
                             "Für Altprojekte; Preise Stand 03/2026.")
    if auslauf != p.auslaufartikel:
        p.auslaufartikel = auslauf
        _ss().pop("v2_konzept", None)
        st.rerun()
    st.markdown("#### Wo steht die Außeneinheit?")
    karten("aufst", [(v, t, AUFSTELLUNG_UNTERTITEL[v], f"ae_{v}" if v else "egal") for v, t in A.AUFSTELLUNG.items()],
           p.aufstellung, lambda v: setattr(p, "aufstellung", v), spalten=4, klein=True)
    _weiter_zurueck(None, ("gebaeude", "Weiter zum Gebäude"), "system")


def standort_setzen(p: Projekt, eintrag: KP.PlzEintrag) -> None:
    """Standort übernehmen und Norm-Außentemperatur aus der PLZ ermitteln (DIN/TS 12831-1)."""
    e = p.einstellungen
    p.plz, p.ort = eintrag.plz, eintrag.text
    wert = KP.norm_aussentemperatur(eintrag.plz)
    if wert is not None:
        e.norm_aussen = round(wert.theta_e, 1)
        p.klima_quelle = wert.quelle
    p.norm_aussen_manuell = False
    e.sommer = klimaregion(eintrag.plz).sommer
    _ss().v2_rev += 1


def grad(x: float) -> str:
    """Temperatur mit einer Nachkommastelle und echtem Minuszeichen, z. B. „−12,4 °C“."""
    return f"{x:.1f} °C".replace(".", ",").replace("-", "−")


@st.cache_resource(show_spinner=False)
def klimadaten_start() -> dict:
    """Beim ersten Aufruf der App: fehlt die PLZ-Tabelle, wird sie im Hintergrund von der
    BWP-Klimakarte geladen (einmal je Server-Prozess; abschaltbar mit KLIMADATEN_AUTO=0)."""
    zustand: dict = {"status": "vorhanden" if KP.tabelle_vorhanden() else "aus", "meldungen": []}
    if zustand["status"] == "aus" and os.environ.get("KLIMADATEN_AUTO", "1") != "0":
        zustand["status"] = "laeuft"

        def lauf() -> None:
            ok, meldungen = KD.von_bwp_laden(timeout=45)
            zustand.update(status="ok" if ok else "fehler", meldungen=meldungen)

        threading.Thread(target=lauf, daemon=True, name="klimadaten").start()
    return zustand


def klima_synchronisieren(p: Projekt) -> None:
    """Liegt (inzwischen) ein genauerer Wert für die PLZ vor, wird er übernommen – außer bei manueller Eingabe."""
    if p.norm_aussen_manuell:
        return
    wert = KP.norm_aussentemperatur(p.plz)
    if wert is not None and (wert.quelle != p.klima_quelle or round(wert.theta_e, 1) != p.einstellungen.norm_aussen):
        p.einstellungen.norm_aussen = round(wert.theta_e, 1)
        p.klima_quelle = wert.quelle


def _klimadaten_laden_ui() -> None:
    """Status des automatischen Ladens, Knopf „Jetzt laden“ und Datei-Upload als Rückfallebene."""
    zustand = klimadaten_start()
    if zustand["status"] == "laeuft":
        @st.fragment(run_every=3)
        def warten() -> None:
            if klimadaten_start()["status"] != "laeuft":
                st.rerun()
            st.caption("Die PLZ-genauen Werte der DIN/TS 12831-1 werden gerade von der BWP-Klimakarte geladen …")
        warten()
        return
    if zustand["status"] == "fehler":
        st.caption("Automatisches Laden der BWP-Klimakarte nicht möglich: " + (zustand["meldungen"] or ["–"])[0])
    else:
        st.caption("Die PLZ-genauen Werte der DIN/TS 12831-1 sind noch nicht hinterlegt.")
    c1, c2 = st.columns(2)
    if c1.button("BWP-Klimakarte laden", icon=":material/cloud_download:", key="klima_laden",
                 width="stretch"):
        with st.spinner("Klimakarte wird geladen und geprüft …"):
            ok, meldungen = KD.von_bwp_laden(timeout=45)
        zustand.update(status="ok" if ok else "fehler", meldungen=meldungen)
        _ss().v2_klima_meldung = (ok, meldungen)
        st.rerun()
    with c2.popover("Tabelle hochladen", icon=":material/upload_file:", width="stretch"):
        st.caption("Excel oder CSV mit den Spalten PLZ, Norm-Außentemperatur und optional Jahresmitteltemperatur "
                   "(z. B. Export der Klimakarte).")
        datei = st.file_uploader("Klimadaten", type=["csv", "xlsx", "txt"], label_visibility="collapsed",
                                 key="klima_upload")
        if datei is not None and st.button("Übernehmen", type="primary", key="klima_upload_ok"):
            endung = Path(datei.name).suffix.lower() if Path(datei.name).suffix.lower() in (".xlsx", ".csv") else ".csv"
            with tempfile.TemporaryDirectory() as tmp:
                pfad = Path(tmp) / f"klimadaten{endung}"
                pfad.write_bytes(datei.getvalue())
                ok, meldungen = KD.aus_datei(pfad)
            if ok:
                zustand.update(status="ok", meldungen=meldungen)
            _ss().v2_klima_meldung = (ok, meldungen)
            st.rerun()


def _klima_karte(p: Projekt) -> None:
    e = p.einstellungen
    wert = KP.norm_aussentemperatur(p.plz)
    with st.container(border=True, key="klima-karte"):
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        with c1:
            st.markdown(f'<div style="font-size:.85rem;color:#5c6773">Norm-Außentemperatur θe</div>'
                        f'<div class="preis">{grad(e.norm_aussen)}</div>', unsafe_allow_html=True)
            if p.norm_aussen_manuell:
                quelle = "manuell eingegeben" + (f" (PLZ-Wert: {grad(wert.theta_e)})" if wert else "")
            else:
                quelle = p.klima_quelle or (wert.quelle if wert else "")
            st.caption(f"{p.ort} · {quelle}")
            if wert and not p.norm_aussen_manuell:
                details = []
                if wert.theta_m is not None:
                    details.append(f"Jahresmittel θm,e {grad(wert.theta_m)}")
                if wert.hoehe is not None:
                    details.append(f"Höhe {wert.hoehe:.0f} m")
                if wert.klimazone:
                    details.append(f"Klimazone {wert.klimazone}")
                if details:
                    st.caption(" · ".join(details))
            if msg := _ss().pop("v2_klima_meldung", None):
                ok, meldungen = msg
                (st.success if ok else st.error)(("Klimadaten übernommen. " if ok else "") + " ".join(meldungen[:3]))
            if wert and wert.status == "richtwert" and not p.norm_aussen_manuell:
                _klimadaten_laden_ui()
        with c2:
            manuell = st.toggle("Wert anpassen", p.norm_aussen_manuell, key=_k("ta_manuell"))
            if manuell:
                neu = zahl(st, "Norm-Außentemperatur", "°C", e.norm_aussen, -25.0, 0.0, 0.1, "ta_wert")
                if not p.norm_aussen_manuell or neu != e.norm_aussen:
                    e.norm_aussen, p.norm_aussen_manuell = round(neu, 1), True
                    p.klima_quelle = "manuell eingegeben"
            elif p.norm_aussen_manuell:  # zurück auf den PLZ-Wert
                eintrag = KP.eintrag(p.plz)
                if eintrag:
                    standort_setzen(p, eintrag)
                    st.rerun()
            st.caption(f"Sommer-Auslegung {de(e.sommer)} °C")


def seite_gebaeude(p: Projekt) -> None:
    e = p.einstellungen
    st.markdown("#### Wo steht das Gebäude?")
    c1, c2 = st.columns(2)
    p.name = c1.text_input("Projektname", p.name, key=_k("name"))
    eingabe = c2.text_input("PLZ oder Ort", p.ort, key=_k("ort"), placeholder="z. B. 72622 oder Nürtingen")
    if eingabe.strip() != p.ort:
        treffer = KP.suche(eingabe)
        if len(treffer) == 1:
            standort_setzen(p, treffer[0])
            st.rerun()
        elif treffer:
            wahl = c2.selectbox("Bitte auswählen", [None, *treffer], format_func=lambda t: t.text if t else "–",
                                key=_k(f"ortwahl_{eingabe}"))
            if wahl:
                standort_setzen(p, wahl)
                st.rerun()
        else:
            c2.error("Diese PLZ bzw. diesen Ort gibt es in Deutschland nicht – bitte prüfen.")
    _klima_karte(p)

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
    c1, _ = st.columns([2, 1])
    optionen = list(P.NACHDAEMMUNG_V2)
    nach = c1.selectbox("Außenwände nachträglich gedämmt", optionen,
                        index=optionen.index(p.nachdaemmung) if p.nachdaemmung in optionen else 0,
                        format_func=P.NACHDAEMMUNG_V2.get, key=_k("nachdaemmung"),
                        help="Sanierung nach dem Baujahr, z. B. Haus von 1958 mit Fassadendämmung 1990. "
                             "Gilt für alle Räume; einzelne Räume kann der Planungs-Assistent abweichend setzen.")
    if nach != p.nachdaemmung:
        p.nachdaemmung = nach
        for r in p.raeume:
            r.daemmung = nach

    st.markdown("#### Fenster")
    karten("glas", VERGLASUNG, e.verglasung, lambda v: setattr(e, "verglasung", v), klein=True, groesse=44)
    if e.sonnenschutz == "0.55":
        e.sonnenschutz = "0.45"
    st.markdown("#### Sonnenschutz")
    karten("shade", SONNENSCHUTZ, e.sonnenschutz, lambda v: setattr(e, "sonnenschutz", v), klein=True, groesse=44)
    _weiter_zurueck(("system", "System"), ("raeume", "Weiter zu den Räumen"), "gebaeude")


def _raum_neu(p: Projekt) -> None:
    neu = Raum(name=f"Raum {len(p.raeume) + 1}", lage="outside", waende=[Wand(ausrichtung="S", laenge=4, fenster=2)],
               geschoss=p.raeume[-1].geschoss if p.raeume else "EG", waende_auto=True)
    neu.wandlaengen_schaetzen()
    neu.baualter = baualter_aus_baujahr(p.baujahr) if p.baujahr else ""
    neu.daemmung = p.nachdaemmung if p.nachdaemmung in P.NACHDAEMMUNG_V2 else "none"
    p.raeume.append(neu)
    _ss().v2_rev += 1
    gehe("raum", raum=len(p.raeume) - 1)


def seite_raeume(p: Projekt) -> None:
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


def seite_raum(p: Projekt, i: int, kat: Katalog | None = None) -> None:
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
    karten(f"ra{i}", [(v, RAUMART_KURZ[v], "", v) for v in RAUMARTEN_ALLE], r.raumart,
           lambda v: setattr(r, "raumart", v), spalten=5, klein=True, groesse=40)
    if r.raumart in P.RAUMARTEN_GEWERBE:
        st.caption(P.GEWERBE_HINWEIS)

    st.markdown("##### Größe")
    c1, c2, _ = st.columns([1, 1, 1])
    flaeche = zahl(c1, "Grundfläche", "m²", r.flaeche or 1, 1.0, 500.0, 0.5, f"rf{i}")
    if flaeche != r.flaeche:
        r.flaeche = flaeche
        if r.waende_auto:
            r.wandlaengen_schaetzen()
    r.hoehe = zahl(c2, "Raumhöhe", "m", r.hoehe or 2.5, 1.8, 10.0, 0.05, f"rh{i}", "%.2f")

    st.markdown("##### Lage im Gebäude")

    def lage_setzen(v: str) -> None:
        flachdach = r.dach and r.lage not in DG_LAGEN  # gewähltes Dach über Nicht-DG-Raum behalten
        r.setze_lage(v)
        if r.waende_auto:
            r.wandlaengen_schaetzen()
        if flachdach and v not in DG_LAGEN:
            r.dach = True
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
        neu_waende = [Wand(**z) for z in wdf.to_dict("records")]
        if r.waende_auto and [w.laenge for w in neu_waende] != [w.laenge for w in r.waende]:
            r.waende_auto = False  # Länge von Hand geändert → nicht mehr automatisch nachführen
        r.waende = neu_waende
        if r.waende_auto:
            st.caption(f"Wandlängen aus der Grundfläche geschätzt (≈ √{de(r.flaeche)} m² = {de(r.waende[0].laenge)} m) "
                       "– bitte an den Grundriss anpassen. Nach einer Änderung bleiben Ihre Werte stehen.")
        elif st.button("Wandlängen aus Grundfläche schätzen", icon=":material/straighten:", type="tertiary",
                       key=_k(f"wschaetz{i}")):
            r.waende_auto = True
            r.wandlaengen_schaetzen()
            _ss().v2_rev += 1
            st.rerun()
    else:
        st.caption("Innenliegender Raum – keine Außenwände.")

    st.markdown("##### Dach über dem Raum")
    dg = r.lage in DG_LAGEN

    def dach_setzen(v: str) -> None:
        r.dach = bool(v) or dg
        if v:
            r.dachform = v
        _ss().v2_rev += 1

    dach_optionen = ([] if dg else [("", "Geschoss darüber", "dach_nein")]) + DACHFORMEN
    karten(f"dach{i}", [(v, t, "", s) for v, t, s in dach_optionen], r.dachform if r.dach else "", dach_setzen,
           spalten=5, klein=True, groesse=40)
    if r.dach and r.dachform == "flat":
        st.caption("Flachdach: Die Dachfläche ist den ganzen Tag besonnt – die Kühllast steigt deutlich "
                   "(Dachfläche = Grundfläche). Lichtkuppeln unten als Dachfenster eintragen.")
    if r.dach:
        df = sum(g.flaeche for g in r.fenstergruppen if g.dachfenster)
        c1, _ = st.columns([1, 2])
        neu = zahl(c1, "Dachfenster / Lichtkuppeln", "m²", df, 0.0, 50.0, 0.1, f"rdf{i}")
        if neu != df:
            r.fenstergruppen = [g for g in r.fenstergruppen if not g.dachfenster]
            if neu > 0:
                r.fenstergruppen.append(Fenstergruppe(ausrichtung="S", flaeche=neu, dachfenster=True))

    st.markdown("##### Gerätewunsch")
    wunsch = A.bauart_wunsch(r)
    karten(f"bau{i}", [(v, t, "", s) for v, t, s in BAUART], wunsch,
           lambda v: setattr(r, "ig_bauart", v or "auto"), spalten=5, klein=True, groesse=44)
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
            grenze = A.farbgrenze(r, kat) if kat else None
            last = raum_last(r, p.einstellungen)
            if grenze and last.cool > grenze[0]:
                st.info(f"„{r.farbe.capitalize()}“ gibt es bis {de(grenze[0])} kW je Gerät. Dieser Raum braucht "
                        f"{de(last.cool, 2)} kW – wir planen deshalb mehrere Geräte in {r.farbe}. Für ein einzelnes "
                        "Gerät „Keine Präferenz“ wählen.", icon=":material/palette:")
    elif wunsch == "Truhe/Decke":
        st.caption("Ceiling/Floor-Truhengeräte (Climate 5000i L) – unter der Decke oder am Boden, 5,3 bis 16 kW, "
                   "auch als Twin.")
    elif wunsch:
        st.caption(f"{wunsch}n: als Large-Split-Set (Climate 5000i L) oder als Multi-Split-Inneneinheit.")

    st.write("")
    c1, c2, c3 = st.container(key="wz-raum").columns([1, 1.3, 1.7])
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
            art = ("Multi-Split" if not t.set else "Large-Split" if t.set.linie == A.LARGE_SPLIT
                   else "Single-Split-Set")
            if t.set and t.set.anzahl_ie > 1:
                art += f" mit {t.set.anzahl_ie} Innengeräten"
            st.markdown(f"**{t.bezeichnung}** · {art}")
            st.caption(f"{haupt.typ if haupt else '–'} · Kühlen {de(t.leistung_kuehl, 1)} kW · "
                       f"Heizen {de(t.leistung_heiz, 1)} kW")
            geraete = [(r, t.set) for r in t.raeume] if t.set else t.innen
            for r, u in geraete:
                farbe = f" · {u.farbe}" if u.farbe and u.farbe != "weiß" else ""
                st.markdown(f"<span style='font-size:.88rem'>▸ {r.name}: {u.typ if t.aussen else 'Inneneinheit'}"
                            f"{farbe}</span>", unsafe_allow_html=True)


@lru_cache(maxsize=128)
def _bild_uri(pfad: str, kante: int = 72) -> str:
    """Kleines Vorschaubild als data-URI (für Bildspalten in Tabellen)."""
    import base64
    import io

    with Image.open(pfad) as im:
        im = im.convert("RGB")
        im.thumbnail((kante - 6, kante - 6))
        feld = Image.new("RGB", (kante, kante), "white")  # quadratisch, nichts wird abgeschnitten
        feld.paste(im, ((kante - im.width) // 2, (kante - im.height) // 2))
        puffer = io.BytesIO()
        feld.save(puffer, format="PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(puffer.getvalue()).decode()


def fmt_eur2(betrag: float | None) -> str:
    """Betrag mit Cent, deutsch formatiert (z. B. 1.970,64 €)."""
    if betrag is None:
        return "auf Anfrage"
    return f"{betrag:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _zubehoer_bild(nr: str) -> str | None:
    pfad = Z.bild(nr)
    return _bild_uri(str(pfad)) if pfad else None


def zubehoer_bereich(p: Projekt, k: A.Konzept, kat: Katalog) -> None:
    """Zubehör und Montagematerial: Vorschlag aus dem Konzept, Mengen frei änderbar.
    Das Fenster bleibt offen, bis es selbst zugeklappt wird (fester Schlüssel statt wechselndem Titel)."""
    zeilen, _ = Z.tabelle(p, k, kat)
    summe = Z.summe(zeilen)
    bedarf, mit_wlan, ohne_wlan = Z.gateway_bedarf(k)
    with st.expander("Zubehör und Montagematerial", icon=":material/handyman:", key="zubehoer-fenster"):
        st.markdown(f"**Summe Zubehör: {fmt_eur(summe)}**")
        c1, _ = st.columns([1, 1])
        laenge = zahl(c1, "Leitungslänge je Innengerät", "m", p.leitungslaenge, 1.0, 50.0, 1.0, "zlaenge", "%.0f")
        c2, c3, c4 = st.columns(3)
        if bedarf:
            app = c2.toggle("App-Steuerung (WLAN)", p.app_steuerung, key=_k("zapp"),
                            help="Internet-Gateways für Innengeräte ohne integriertes WLAN"
                                 + (f" ({ohne_wlan} von {mit_wlan + ohne_wlan} Geräten)." if mit_wlan else "."))
        else:
            c2.toggle("App-Steuerung (WLAN)", True, key=_k("zapp_fest"), disabled=True,
                      help="WLAN ist bei allen Innengeräten integriert (Climate 7000i / Class 8000i) – "
                           "kein Gateway nötig.")
            app = p.app_steuerung
        boerdel = c3.toggle("Bördelfrei (Klemmring)", p.boerdelfrei, key=_k("zboerdel"),
                            help="SAE-Klemmringverschraubungen, 2 je Leitung und Seite.")
        pumpe = c4.toggle("Kondensatpumpe", p.kondensatpumpe, key=_k("zpumpe"),
                          help="Wenn das Kondensat nicht mit Gefälle abgeleitet werden kann. Kassetten haben eine "
                               "integrierte Pumpe.")
        if not bedarf:
            c2.caption("WLAN integriert")
        if (laenge, app, boerdel, pumpe) != (p.leitungslaenge, p.app_steuerung, p.boerdelfrei, p.kondensatpumpe):
            p.leitungslaenge, p.app_steuerung, p.boerdelfrei, p.kondensatpumpe = laenge, app, boerdel, pumpe
            st.rerun()
        st.caption("WLAN: " + " · ".join(Z.wlan_uebersicht(k)))
        alle = st.toggle("Alle Zubehörartikel zeigen", key=_k("zalle"),
                         help="Auch Artikel, die nicht automatisch vorgeschlagen werden – Menge mit + erhöhen.")
        sichtbar = [z for z in zeilen if not z.gesperrt and (alle or z.vorschlag or z.menge)]
        if not sichtbar:
            st.info("Für diese Lösung gibt es keinen automatischen Zubehörvorschlag – z. B. Large-Split über 7 kW "
                    "(Kältemittelleitung bauseits) ohne gewählten Aufstellort. Über „Alle Zubehörartikel zeigen“ "
                    "können Sie Artikel manuell ergänzen.", icon=":material/info:")
        neu = dict(p.zubehoer_mengen)
        gruppe = None
        for z in sichtbar:
            if z.gruppe != gruppe:
                gruppe = z.gruppe
                st.markdown(f'<div class="zub-gruppe">{gruppe}</div>', unsafe_allow_html=True)
            manuell = z.bestellnr in p.zubehoer_mengen
            with st.container(key=f"zubrow-{z.bestellnr}"):
                c1, c2, c3, c4 = st.columns([0.9, 4.2, 1.5, 1.2], vertical_alignment="center")
                uri = _zubehoer_bild(z.bestellnr)
                c1.markdown(f'<img class="zub-bild" src="{uri}">' if uri else "", unsafe_allow_html=True)
                warum = z.grund + (" · Menge von Hand geändert" if manuell else "")
                c2.markdown(f'<div class="zub-name">{z.name}</div><div class="zub-info">{z.bestellnr} · '
                            f'{fmt_eur2(z.einzelpreis)} je Stück</div><div class="zub-warum">{warum}</div>',
                            unsafe_allow_html=True)
                menge = c3.number_input("Menge", 0, 999, int(z.menge), 1, label_visibility="collapsed",
                                        key=_k(f"zm-{k.key}-{z.bestellnr}-{z.vorschlag}-{int(manuell)}"))
                c4.markdown(f'<div class="zub-summe">{fmt_eur2(z.einzelpreis * menge if z.einzelpreis else None)}'
                            '</div>', unsafe_allow_html=True)
            if int(menge) == z.vorschlag:
                neu.pop(z.bestellnr, None)
            else:
                neu[z.bestellnr] = int(menge)
        if neu != p.zubehoer_mengen:
            p.zubehoer_mengen = neu
            st.rerun()
        gesperrt = [z for z in zeilen if z.gesperrt and (alle or z.bestellnr in Z.GATEWAYS)]
        for titel, auswahl in (("Nicht erforderlich – WLAN integriert",
                                [z for z in gesperrt if z.gesperrt.startswith("WLAN")]),
                               ("Passt nicht zu den gewählten Geräten",
                                [z for z in gesperrt if not z.gesperrt.startswith("WLAN")])):
            if auswahl:
                st.markdown(f'<div class="zub-gesperrt-titel">{titel}</div>', unsafe_allow_html=True)
                st.markdown("".join(
                    '<div class="zub-gesperrt">'
                    + (f'<img src="{_zubehoer_bild(z.bestellnr)}">' if _zubehoer_bild(z.bestellnr) else "<span></span>")
                    + f'<span><b>{z.name}</b> · {z.bestellnr}</span><span>{z.gesperrt}</span></div>'
                    for z in auswahl), unsafe_allow_html=True)
        geraete = k.preis
        st.markdown(f"**Summe Zubehör: {fmt_eur(summe)}**" + (
            f" · Geräte + Zubehör: **{fmt_eur(geraete + summe)}**" if geraete is not None and summe is not None else ""))
        c1, c2 = st.columns([2, 1], vertical_alignment="center")
        c1.caption(f"{Z.VORKALKULATION} Vorschlag aus Konzept, Aufstellort und Leitungslänge – Mengen mit "
                   f"+/− anpassen. {kat.preisbasis}.")
        if p.zubehoer_mengen and c2.button("Vorschlag wiederherstellen", icon=":material/restart_alt:",
                                           type="tertiary"):
            p.zubehoer_mengen = {}
            _ss().v2_rev += 1
            st.rerun()


def _chat_senden(p: Projekt, kat: Katalog, text: str) -> None:
    ss = _ss()
    ss.v2_chat.append({"rolle": "user", "text": text})
    if ss.v2_chat_zaehler >= AS.MAX_NACHRICHTEN:
        ss.v2_chat.append({"rolle": "assistant", "text": "Für diese Sitzung ist das Nachrichtenlimit erreicht – "
                                                         "bitte die Seite neu laden."})
        return
    ss.v2_chat_zaehler += 1
    sicherung = (p.model_dump_json(), ss.get("v2_konzept"))
    zustand = {"konzept": ss.get("v2_konzept")}
    try:
        antwort = AS.antworten(ss.v2_chat_api, text, p, kat, zustand)
    except AS.AssistentFehler as fehler:
        ss.v2_chat.append({"rolle": "assistant", "text": str(fehler), "fehler": True})
        return
    if zustand.get("konzept"):
        ss.v2_konzept = zustand["konzept"]
    else:
        ss.pop("v2_konzept", None)
    if antwort.aenderungen:
        ss.v2_rev += 1  # Eingabefelder mit den neuen Werten neu aufbauen
    ss.v2_chat.append({"rolle": "assistant", "text": antwort.text, "aenderungen": antwort.aenderungen,
                       "vorher": antwort.vorher, "nachher": antwort.nachher,
                       "sicherung": sicherung if antwort.aenderungen else None})


def _chat_rueckgaengig(eintrag: dict) -> None:
    daten, konzept = eintrag["sicherung"]
    _ss().v2_projekt = Projekt.model_validate_json(daten)
    if konzept:
        _ss().v2_konzept = konzept
    else:
        _ss().pop("v2_konzept", None)
    eintrag["sicherung"] = None
    eintrag["rueckgaengig"] = True
    _ss().v2_rev += 1


def _vergleich(vorher: dict, nachher: dict) -> str:
    teile = []
    for feld, name, einheit in (("kuehllast_kw", "Kühllast", " kW"), ("heizlast_kw", "Heizlast", " kW")):
        a, b = vorher.get(feld), nachher.get(feld)
        if a is not None and b is not None and a != b:
            teile.append(f"{name} {de(a, 2)} → {de(b, 2)}{einheit}")
    if vorher.get("preis") != nachher.get("preis") and nachher.get("preis"):
        teile.append(f"Preis {vorher.get('preis', '–')} → {nachher['preis']}")
    if vorher.get("loesung") != nachher.get("loesung") and nachher.get("loesung"):
        teile.append(f"Lösung: {nachher['loesung']}")
    return " · ".join(teile)


def planungs_assistent(p: Projekt, kat: Katalog) -> None:
    """Chat-Blase unten rechts: Änderungen an der Planung per Text (nur die eigene Sitzung)."""
    ss = _ss()
    for key, start in (("v2_chat", []), ("v2_chat_api", []), ("v2_chat_zaehler", 0), ("v2_chat_offen", False)):
        if key not in ss:
            ss[key] = start if not isinstance(start, list) else list(start)
    if not ss.v2_chat_offen:
        with st.container(key="chatfab"):
            if st.button("Planungs-Assistent", icon=":material/forum:", key="chat-oeffnen"):
                ss.v2_chat_offen = True
                st.rerun()
        return
    with st.container(key="chatpanel"):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown('<div class="chat-titel">Planungs-Assistent <span class="v2-badge">Beta</span></div>',
                    unsafe_allow_html=True)
        if c2.button("", icon=":material/close:", key="chat-schliessen", help="Schließen"):
            ss.v2_chat_offen = False
            st.rerun()
        bereit = schluessel_vorhanden()
        verlauf = st.container(height=360, key="chatverlauf", border=False)
        with verlauf:
            with st.chat_message("assistant", avatar=":material/support_agent:"):
                st.markdown("Hallo! Beschreiben Sie einfach, was an der Planung anders sein soll – ich passe sie an "
                            "und zeige, was sich ändert.")
            letzte = max((i for i, e in enumerate(ss.v2_chat) if e.get("sicherung")), default=-1)
            for i, eintrag in enumerate(ss.v2_chat):
                with st.chat_message(eintrag["rolle"],
                                     avatar=":material/person:" if eintrag["rolle"] == "user"
                                     else ":material/support_agent:"):
                    st.markdown(eintrag["text"])
                    if eintrag.get("aenderungen"):
                        st.caption("Geändert: " + " · ".join(eintrag["aenderungen"]))
                        vergleich = _vergleich(eintrag.get("vorher", {}), eintrag.get("nachher", {}))
                        if vergleich:
                            st.caption(vergleich)
                    if eintrag.get("rueckgaengig"):
                        st.caption("↩ Rückgängig gemacht.")
                    elif i == letzte and st.button("Rückgängig", icon=":material/undo:", key=f"chat-undo-{i}",
                                                   type="tertiary"):
                        _chat_rueckgaengig(eintrag)
                        st.rerun()
            if not ss.v2_chat and bereit:
                for j, beispiel in enumerate(BEISPIELE):
                    if st.button(beispiel, key=f"chat-bsp-{j}", type="secondary", width="stretch"):
                        with st.spinner("Der Assistent arbeitet …"):
                            _chat_senden(p, kat, beispiel)
                        st.rerun()
        if not bereit:
            st.info("Der Assistent ist auf diesem Server noch nicht eingerichtet (API-Schlüssel fehlt).",
                    icon=":material/key_off:")
            return
        text = st.chat_input("Was soll anders sein?", key="chat-eingabe", max_chars=1500)
        if text:
            with st.spinner("Der Assistent arbeitet …"):
                _chat_senden(p, kat, text)
            st.rerun()
        st.caption("Ändert nur Ihre Planung in dieser Sitzung. Eingaben werden zur Auswertung an die Claude API "
                   "übertragen – keine personenbezogenen Kundendaten eingeben.")


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
            for sp, pf in zip(st.container(key="konzeptbilder").columns(len(bilder) + 1), bilder):
                sp.image(str(pf), width=min(BILD_MAX, Image.open(pf).width))
        m = st.container(key="kennzahlen").columns(4)
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
    zubehoer_bereich(p, gewaehlt, kat)
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
    hinweise = (gewaehlt.lieferhinweise + gewaehlt.hinweise + A.aufstellungshinweise(p, gewaehlt)
                + Z.tabelle(p, gewaehlt, kat)[1])
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
    with c2:
        planung_zuruecksetzen(p, "ende")


def _weiter_zurueck(zurueck: tuple[str, str] | None, weiter: tuple[str, str] | None, hier: str) -> None:
    st.write("")
    c1, c2, _ = st.container(key=f"wz-{hier}").columns([1, 1.6, 1])
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
    konfiguration_speichern_laden(p)


def mobil_navigation(p: Projekt) -> None:
    """Kompakte Schrittleiste für Smartphone/Tablet (per CSS nur dort sichtbar)."""
    seite = _ss().v2_seite
    with st.container(key="mobilnav", border=True):
        spalten = st.columns([1, 1, 1, 1, 0.55], gap="small")
        for sp, (key, titel, icon) in zip(spalten, SCHRITTE):
            aktiv = seite == key or (key == "raeume" and seite == "raum")
            if sp.button(titel, key=f"mnav-{key}", width="stretch", type="primary" if aktiv else "secondary",
                         disabled=key == "ergebnis" and not p.raeume):
                gehe(key)
        with spalten[4].popover("", icon=":material/save:", width="stretch"):
            st.markdown("**Konfiguration**")
            konfiguration_speichern_laden(p, mobil=True)


def mobil_preisleiste(p: Projekt, kat: Katalog) -> None:
    """Feste Preisleiste am unteren Rand (nur Smartphone)."""
    if not p.raeume:
        return
    k = _gewaehlt(_konzepte(p, kat))
    if not k:
        return
    last = gebaeude_last(p)
    st.html(f'<div class="mobilpreis"><div><div class="mp-name">{k.name}</div>'
            f'<div class="mp-info">Kühllast {de(last.cool, 2)} kW · {k.aussengeraete} AG / {k.innengeraete} IG</div>'
            f'</div><div class="mp-preis">{fmt_eur(k.preis)}</div></div>')


def konfiguration_speichern_laden(p: Projekt, mobil: bool = False) -> None:
    """Aktuelle Konfiguration als JSON herunterladen bzw. eine gespeicherte wieder laden."""
    auswahl = {"konzept": _ss().get("v2_konzept"), "seite": _ss().v2_seite, "raum": _ss().get("v2_raum", 0),
               "erledigt": sorted(_ss().v2_erledigt), "geprueft": sorted(_ss().v2_geprueft)}
    endung = "-m" if mobil else ""
    with st.container(border=not mobil):
        if not mobil:
            st.markdown("**Konfiguration**")
        st.download_button("Speichern (JSON)", SP.exportieren(p, auswahl), file_name=SP.dateiname(p),
                           mime="application/json", icon=":material/download:", width="stretch",
                           key=f"konfig-speichern{endung}")
        with st.popover("Laden", icon=":material/upload:", width="stretch"):
            datei = st.file_uploader("Gespeicherte Konfiguration (.json)", type=["json"], key=f"konfig-laden{endung}")
            if datei is not None and _ss().get("v2_geladen") != datei.file_id:
                _ss().v2_geladen = datei.file_id
                _ss().v2_import = datei.getvalue()
                st.rerun()
            if fehler := _ss().get("v2_import_fehler"):
                st.error(fehler)
            st.caption("Lädt Räume, Einstellungen, Gerätewünsche und Zubehörmengen. Die aktuelle Konfiguration "
                       "wird ersetzt – vorher speichern.")
        planung_zuruecksetzen(p, "m" if mobil else "nav")


def planung_zuruecksetzen(p: Projekt, ort: str) -> None:
    """„Neu beginnen“ mit Sicherheitsabfrage – löscht Räume, Einstellungen und Zubehörmengen."""
    with st.popover("Neu beginnen", icon=":material/restart_alt:", width="stretch"):
        st.markdown("**Planung zurücksetzen?**")
        st.caption("Alle Räume, Einstellungen, Gerätewünsche und Zubehörmengen werden gelöscht. "
                   "Wer die aktuelle Planung behalten möchte, speichert sie vorher als JSON.")
        if p.raeume:
            st.download_button("Vorher speichern (JSON)", SP.exportieren(p), file_name=SP.dateiname(p),
                               mime="application/json", icon=":material/download:", width="stretch",
                               key=f"reset-speichern-{ort}")
        if st.button("Ja, alles zurücksetzen", type="primary", icon=":material/delete_sweep:", width="stretch",
                     key=f"reset-ja-{ort}"):
            neues_projekt()
            _ss().v2_import_fehler = ""
            _ss().v2_toast = "Neue Planung gestartet."
            st.rerun()


def konfiguration_importieren() -> None:
    """Hochgeladene Konfiguration (``v2_import``) am Anfang des Laufs übernehmen."""
    daten = _ss().get("v2_import")
    if daten is None:
        return
    del _ss()["v2_import"]
    try:
        projekt, auswahl = SP.importieren(daten)
    except SP.LadeFehler as fehler:
        _ss().v2_import_fehler = f"Laden nicht möglich: {fehler}"
        return
    _ss().v2_import_fehler = ""
    konfiguration_uebernehmen(projekt, auswahl)


def konfiguration_uebernehmen(projekt: Projekt, auswahl: dict) -> None:
    neues_projekt(projekt, geladen=True)
    n = len(projekt.raeume)
    _ss().v2_erledigt = {s for s in auswahl.get("erledigt", []) if s in {k for k, _, _ in SCHRITTE}}
    _ss().v2_geprueft = {i for i in auswahl.get("geprueft", []) if isinstance(i, int) and 0 <= i < n}
    if auswahl.get("konzept"):
        _ss().v2_konzept = str(auswahl["konzept"])
    else:
        _ss().pop("v2_konzept", None)
    seite = auswahl.get("seite") if auswahl.get("seite") in {k for k, _, _ in SCHRITTE} | {"raum"} else "system"
    if seite in ("raum", "ergebnis") and not n:
        seite = "raeume"
    _ss().v2_seite = seite
    _ss().v2_raum = min(max(int(auswahl.get("raum") or 0), 0), max(n - 1, 0))
    _ss().v2_toast = f"Konfiguration „{projekt.name}“ geladen ({n} Räume)."


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
                  *([("Gerätelinie", A.GERAETELINIEN[p.geraetelinie])] if p.geraetelinie else []),
                  *([("Außeneinheit", A.AUFSTELLUNG[p.aufstellung])] if p.aufstellung else []),
                  ("Standort", p.ort), ("Norm-Außentemp.", grad(e.norm_aussen)),
                  ("Baujahr", str(p.baujahr or "–"))]
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
                treffer = [(u, bool(t.set)) for t in gewaehlt.teilsysteme
                           for rr, u in ([(x, t.set) for x in t.raeume] if t.set else t.innen)
                           if u is not None and (rr is r or rr.name.startswith(f"{r.name} · Zone "))]
                if treffer:
                    u, ist_set = treffer[0]
                    if pf := (bild_innen_set(u) if ist_set else bild(u)):
                        _bild_mittig(pf, 220)
                    typen = list(dict.fromkeys(x.typ for x, _ in treffer))
                    st.caption("Vorschlag: " + (f"{len(treffer)} Geräte – " if len(treffer) > 1 else "")
                               + ", ".join(typen))


# ====================================================================== Einstieg
def app_v2(kat: Katalog) -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    if "v2_projekt" not in _ss():
        neues_projekt()
    konfiguration_importieren()
    p: Projekt = _ss().v2_projekt
    klimadaten_start()
    klima_synchronisieren(p)
    _nach_oben()
    if msg := _ss().pop("v2_toast", None):
        st.toast(msg, icon="✅")

    if not p.auslaufartikel:  # Standard: nur Artikel des aktuellen Katalogs 09/2026
        kat = kat.ohne_auslauf()
    links, mitte, rechts = st.columns([1.05, 3, 1.35], gap="medium")
    seite = _ss().v2_seite
    with mitte:
        mobil_navigation(p)
        if seite == "system":
            seite_system(p)
        elif seite == "gebaeude":
            seite_gebaeude(p)
        elif seite == "raeume":
            seite_raeume(p)
        elif seite == "raum":
            seite_raum(p, _ss().v2_raum, kat)
        else:
            seite_ergebnis(p, kat)
        mobil_preisleiste(p, kat)
    with links, st.container(key="navspalte"):
        navigation(p)
    with rechts:
        zusammenfassung(p, kat)
    st.markdown(f'<div class="entwickler">{ENTWICKLER}</div>', unsafe_allow_html=True)
    if ASSISTENT_AKTIV:
        planungs_assistent(p, kat)
