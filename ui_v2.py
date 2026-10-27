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
from splitklima.sprache import SITZUNG_SCHLUESSEL as SITZUNG, N_, T, englisch, klimaquelle
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
from splitklima.v2 import fotos as FO
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

SCHRITTE = [("system", N_("System"), ":material/hub:"), ("gebaeude", N_("Gebäude"), ":material/home:"),
            ("raeume", N_("Räume"), ":material/meeting_room:"), ("ergebnis", N_("Ergebnis"), ":material/task_alt:")]
SYSTEME = [("auto", N_("Beste Lösung"), N_("Wir vergleichen alle Varianten und empfehlen die wirtschaftlichste.")),
           ("multi", "Multi-Split", N_("Eine Außeneinheit versorgt mehrere Räume.")),
           ("single", "Single-Split", N_("Jeder Raum bekommt ein eigenes Set."))]
BETRIEB = [("both", N_("Kühlen & Heizen"), N_("Ganzjährig nutzen – im Sommer kühlen, in der Übergangszeit heizen.")),
           ("cool", N_("Nur Kühlen"), N_("Angenehme Temperaturen an heißen Tagen.")),
           ("heat", N_("Nur Heizen"), N_("Effizient heizen mit Luft-Luft-Wärmepumpe."))]
VERGLASUNG = [("double", N_("Zweifach"), "", "double"), ("triple", N_("Dreifach"), "", "triple"),
              ("single", N_("Einfach"), "", "single_glas")]
SONNENSCHUTZ = [("0.45", N_("Außen"), N_("Rollladen, Raffstore"), "0.45"),
                ("0.8", N_("Innen"), N_("Vorhang, Plissee"), "0.8"), ("1", N_("Keiner"), "", "1")]
LAGE = [("outside", N_("1 Außen&shy;wand")), ("corner", N_("Eckraum")), ("three", N_("3 Außen&shy;wände")),
        ("inside", N_("Innen&shy;liegend")), ("attic", N_("Dach&shy;geschoss")), ("attic_corner", N_("DG-Eck&shy;raum")),
        ("basement", N_("Über Keller"))]
DG_LAGEN = ("attic", "attic_corner")
ENTWICKLER = N_("Entwickelt von Daniel Sommer (HC/SDE3-PSD)")
ASSISTENT_AKTIV = os.environ.get("ASSISTENT", "1") != "0"  # ASSISTENT=0 blendet den Chat aus
BEISPIELE = [N_("Der Plan hat keinen Nordpfeil – das Wohnzimmer liegt im Norden."),
             N_("Das Haus ist von 1958, die Fassade wurde 1990 gedämmt."),
             N_("Geht es günstiger? Die Farbe ist mir egal.")]
RAUMART_KURZ = {"Wohnzimmer": N_("Wohnen"), "Schlafzimmer": N_("Schlafen"), "Büro": N_("Büro"), "Küche": N_("Küche"),
                "Kinderzimmer": N_("Kinder"), "Badezimmer": N_("Bad"), "Werkstatt": N_("Werkstatt"),
                "Halle / Lager": N_("Halle / Lager"), "Verkaufsraum": "Laden", "Seminar / Schulung": N_("Seminar")}
RAUMART_KURZ_EN = {"Verkaufsraum": "Shop"}  # „Laden“ ist sonst mehrdeutig (Knopf „Laden“ = Load)
RAUMARTEN_ALLE = [*P.RAUMARTEN, *P.RAUMARTEN_GEWERBE]
LINIEN_BILD = {"3200i": "set_3200i", "7000i": "set_7000i_weiss", "8000i": "set_8000i_weiss"}
BAUART = [("", N_("Keine Präferenz"), "egal"), ("Wandgerät", N_("Wandgerät"), "Wandgerät"),
          ("Deckenkassette", N_("Decken&shy;kassette"), "Deckenkassette"), ("Konsole", N_("Konsole"), "Konsole"),
          ("Truhe/Decke", N_("Truhe / Decke"), "Truhe/Decke")]
DACHFORMEN = [("flat", N_("Flachdach"), "dach_flach"), ("saddle_south", N_("Sattel&shy;dach Süd"), "dach_sued"),
              ("saddle_north", N_("Sattel&shy;dach Nord"), "dach_nord"),
              ("saddle_eastwest", N_("Sattel&shy;dach Ost/West"), "dach_ow")]
AUFSTELLUNG_UNTERTITEL = {"": N_("Entscheiden wir später."), "wand": N_("Wandkonsole an der Fassade."),
                          "boden": N_("Bodenkonsole vor dem Haus, z. B. Garten oder Terrasse."),
                          "flachdach": N_("Bodenkonsole auf dem Flachdach, ohne Dachdurchdringung.")}
RICHTUNG_EN = {"NO": "NE", "O": "E", "SO": "SE"}  # Himmelsrichtungen in der englischen Oberfläche
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
/* ---------- Plan fotografieren: Upload-Feld als großer Kamera-Knopf */
.st-key-kamera [data-testid="stFileUploaderDropzone"] {{background:#eef5fb; border:1.5px dashed #7fa9cc}}
.st-key-kamera [data-testid="stFileUploaderDropzoneInstructions"] {{display:none}}
.st-key-kamera button:not([data-testid="stBaseButton-minimal"]) {{font-size:0 !important;
    background:{BLAU} !important; color:white !important; border:none !important; padding:.55rem 1.1rem !important;
    border-radius:.5rem !important; width:auto !important; height:auto !important}}
.st-key-kamera button:not([data-testid="stBaseButton-minimal"]) * {{font-size:0 !important}}
.st-key-kamera button:not([data-testid="stBaseButton-minimal"])::after {{content:var(--kamera-text);
    font-size:.95rem; font-weight:600; color:white; white-space:nowrap}}
.st-key-kamera [data-testid="stFileChips"] > button:not([data-testid="stBaseButton-minimal"])::after {{
    content:var(--kamera-weiter)}}
/* Gerätekamera nur auf Touch-Geräten, Webcam nur am PC (Maus/Trackpad) */
@media (hover:hover) and (pointer:fine) {{ .st-key-kamera {{display:none !important}} }}
@media (hover:none), (pointer:coarse) {{ .st-key-webcam {{display:none !important}} }}
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
.auslauf-liste {{font-size:.82rem; color:#5c6773; background:#f7f9fa; border:1px solid #e3e8ed; border-radius:.5rem;
                 padding:.5rem .8rem; margin:.2rem 0 .6rem}}
.auslauf-liste.an {{background:#fff8e6; border-color:#f0d58c; color:#5c4a12}}
.auslauf-liste ul {{margin:.3rem 0 0 1rem; padding:0}} .auslauf-liste li {{margin:0}}
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
    """Zahl für die Anzeige – Dezimalkomma (Deutsch) bzw. -punkt (Englisch)."""
    if float(x).is_integer() and nachkomma <= 1:
        return f"{x:.0f}"
    s = f"{x:.{nachkomma}f}"
    return s if englisch() else s.replace(".", ",")


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
        titel, sub = T(titel), T(sub)
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
    for key in ("v2_ki_info", "v2_konzept", "v2_ack_zeit", "v2_webcam_fotos"):
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
            st.markdown(f'<div class="hero-ki">{svg("ki", 64)}<div><h3>{T("Grundriss hochladen – fertig.")}</h3>'
                        '<div>' + T("Die KI erkennt Räume, Flächen, Fenster und die Himmelsrichtung und füllt die "
                                    "Konfiguration für Sie aus. Sie prüfen nur noch kurz.") + '</div></div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown("**" + T("Grundrisse hochladen – Räume automatisch erkennen") + "**")
        dateien = st.file_uploader(T("Pläne"), type=["pdf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                                   label_visibility="collapsed", key="v2_upload")
        fotos = kamera_bereich()
        dateien = [*(dateien or []), *fotos]
        ki_bereit = schluessel_vorhanden()
        c1, c2, c3 = st.columns([2, 2, 2])
        with c3.popover(T("Zusatzangaben"), width="stretch"):
            zusatz = st.text_area(T("Hinweise für die Erkennung"), key="v2_zusatz",
                                  placeholder=T("z. B. Plan-Oben zeigt nach Nordost; Keller nicht klimatisieren"))
        try:
            eingaben = ki_eingaben(dateien)
            fehler_foto = ""
        except FO.FotoFehler as fehler:
            eingaben, fehler_foto = [], str(fehler)
        groesse = sum(len(d) for d, _ in eingaben) / 1e6
        if c1.button(T("Räume erkennen"), type="primary", width="stretch", icon=":material/auto_awesome:",
                     disabled=not eingaben or not ki_bereit or groesse > MAX_MB):
            with st.spinner(T("Die Pläne werden gelesen … das dauert 1–2 Minuten.")):
                try:
                    ki_uebernehmen(p, analysiere(eingaben, zusatz, sprache="en" if englisch() else "de"))
                except PlanFehler as fehler:
                    st.error(str(fehler))
        if fehler_foto:
            st.error(fehler_foto)
        if c2.button(T("Beispielhaus laden"), width="stretch", icon=":material/home_work:"):
            ki_uebernehmen(p, beispiel_analyse())
        if groesse > MAX_MB:
            st.error(T("Zusammen {mb} MB – bitte höchstens {max} MB bzw. Geschosse einzeln hochladen.",
                       mb=f"{groesse:.0f}", max=MAX_MB))
        elif not ki_bereit:
            st.caption(T("Automatische Erkennung ist hier nicht eingerichtet (API-Schlüssel fehlt) – "
                         "„Beispielhaus laden“ zeigt, wie es funktioniert."))
        else:
            st.caption(T("PDF, PNG, JPG oder Foto · alle Geschosse auf einmal möglich · Fotos werden vorher gedreht, "
                         "verkleinert und kontrastverstärkt · die Pläne werden zur Auswertung an die Claude API "
                         "übertragen."))


KAMERA_JS = """<script>
(() => {
  // „Plan fotografieren“: öffnet auf Tablet/Smartphone direkt die Rückkamera (volle Auflösung)
  const setzen = () => document.querySelectorAll('.st-key-kamera input[type=file]').forEach(i => {
    if (i.getAttribute('capture') !== 'environment') { i.setAttribute('capture', 'environment');
      i.setAttribute('accept', 'image/*'); }
  });
  setzen();
  if (!window.__kameraBeobachter) {
    window.__kameraBeobachter = new MutationObserver(setzen);
    window.__kameraBeobachter.observe(document.body, {childList: true, subtree: true});
  }
})();
</script>"""


WEBCAM_HTML = """
<div class="wc">
  <button class="start" type="button">🖥️&nbsp; Plan in die Webcam halten</button>
  <div class="live" hidden>
    <div class="rahmen"><video playsinline muted autoplay></video><div class="ecke"></div>
      <div class="zahl"></div><div class="blitz"></div></div>
    <div class="knoepfe">
      <button class="ausloesen haupt" type="button">📸&nbsp; Aufnehmen <small>(Leertaste)</small></button>
      <button class="timer" type="button">⏱️&nbsp; Selbstauslöser 3 s</button>
      <select class="cams" title="Kamera wählen" hidden></select>
      <button class="aus" type="button">Kamera aus</button>
    </div>
    <div class="info"></div>
  </div>
  <div class="fehler" hidden></div>
</div>"""

WEBCAM_CSS = """
.wc {font-family: var(--st-font, "Source Sans Pro", sans-serif); font-size:.95rem}
button {font:inherit; font-weight:600; border-radius:.5rem; padding:.5rem 1rem; cursor:pointer;
  border:1px solid #c5d3df; background:white; color:#1f2b37}
button:hover {border-color:#005691; color:#005691}
.start, .haupt {background:#005691; color:white; border-color:#005691}
.start:hover, .haupt:hover {filter:brightness(1.1); color:white}
small {font-weight:400; opacity:.8}
.rahmen {position:relative; margin-top:.6rem; max-width:720px; border-radius:.6rem; overflow:hidden;
  background:#0b1620; aspect-ratio:16/9}
video {width:100%; height:100%; object-fit:contain; display:block}
.ecke {position:absolute; inset:7%; border:2px dashed rgba(255,255,255,.65); border-radius:.4rem;
  pointer-events:none}
.zahl {position:absolute; inset:0; display:flex; align-items:center; justify-content:center;
  font-size:6rem; font-weight:700; color:white; text-shadow:0 2px 12px rgba(0,0,0,.6); pointer-events:none}
.blitz {position:absolute; inset:0; background:white; opacity:0; pointer-events:none; transition:opacity .35s}
.blitz.an {opacity:.85; transition:none}
.knoepfe {display:flex; flex-wrap:wrap; gap:.5rem; margin-top:.6rem; align-items:center}
select {font:inherit; padding:.45rem .5rem; border-radius:.5rem; border:1px solid #c5d3df; max-width:16rem}
.info {font-size:.82rem; color:#5c6773; margin-top:.4rem}
.info.warn {color:#a15c00}
.fehler {margin-top:.5rem; padding:.6rem .8rem; border-radius:.5rem; background:#fdecea; color:#8a1c12;
  font-size:.88rem}
"""

WEBCAM_JS = """
export default function (component) {
  const { parentElement, setTriggerValue } = component;
  const $ = (s) => parentElement.querySelector(s);
  // Beschriftungen in der Sprache der Oberfläche (kommen bei jedem Lauf aus Python)
  const L = component.data || {};
  for (const [sel, k] of [[".start", "start"], [".ausloesen", "ausloesen"], [".timer", "timer"], [".aus", "aus"]]) {
    const el = $(sel);
    if (el && L[k]) el.innerHTML = L[k];
  }
  if ($(".cams") && L.kamera_waehlen) $(".cams").title = L.kamera_waehlen;
  // Bei jedem Streamlit-Lauf wird die Funktion erneut aufgerufen – Kamera und Knöpfe nur einmal einrichten
  if (parentElement.__wc) { parentElement.__wc.L = L; return parentElement.__wc.aufraeumen; }
  const txt = (k, ersatz = {}) => {
    let s = (parentElement.__wc && parentElement.__wc.L[k]) || L[k] || k;
    for (const [n, v] of Object.entries(ersatz)) s = s.replaceAll("{" + n + "}", v);
    return s;
  };
  const video = $("video"), live = $(".live"), start = $(".start"), info = $(".info"), fehler = $(".fehler");
  const cams = $(".cams"), zahl = $(".zahl"), blitz = $(".blitz");
  let strom = null, zaehler = null;

  const meldung = (text) => { fehler.textContent = text; fehler.hidden = !text; };
  const stoppen = () => {
    if (zaehler) { clearInterval(zaehler); zaehler = null; zahl.textContent = ""; }
    if (strom) { strom.getTracks().forEach((t) => t.stop()); strom = null; }
    video.srcObject = null; live.hidden = true; start.hidden = false;
  };

  async function starten(geraet) {
    meldung("");
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      meldung(txt("kein_zugriff"));
      return;
    }
    if (strom) { strom.getTracks().forEach((t) => t.stop()); strom = null; }
    const video_wunsch = { width: { ideal: 3840 }, height: { ideal: 2160 } };  // höchste Auflösung der Webcam
    if (geraet) video_wunsch.deviceId = { exact: geraet };
    try {
      strom = await navigator.mediaDevices.getUserMedia({ video: video_wunsch, audio: false });
    } catch (e) {
      const text = { NotAllowedError: txt("abgelehnt"), NotFoundError: txt("keine_webcam"),
                     NotReadableError: txt("belegt") };
      meldung(text[e.name] || (txt("startfehler") + " " + e.message));
      return;
    }
    const spur = strom.getVideoTracks()[0];
    try {  // Autofokus, wo die Webcam es kann
      const kann = spur.getCapabilities ? spur.getCapabilities() : {};
      if (kann.focusMode && kann.focusMode.includes("continuous"))
        await spur.applyConstraints({ advanced: [{ focusMode: "continuous" }] });
    } catch (e) { /* egal */ }
    video.srcObject = strom;
    live.hidden = false; start.hidden = true;
    try { await video.play(); } catch (e) { /* autoplay */ }
    const st = spur.getSettings();
    const mp = ((st.width || 0) * (st.height || 0) / 1e6).toFixed(1);
    if ((st.width || 0) < 1280) {
      info.className = "info warn";
      info.textContent = txt("niedrig", { w: st.width, h: st.height });
    } else {
      info.className = "info";
      info.textContent = txt("info", { w: st.width, h: st.height, mp });
    }
    try {
      const geraete = (await navigator.mediaDevices.enumerateDevices()).filter((d) => d.kind === "videoinput");
      cams.hidden = geraete.length < 2;
      cams.innerHTML = "";
      geraete.forEach((d, i) => {
        const o = document.createElement("option");
        o.value = d.deviceId; o.textContent = d.label || txt("kamera_n", { n: i + 1 });
        if (d.deviceId === st.deviceId) o.selected = true;
        cams.appendChild(o);
      });
    } catch (e) { cams.hidden = true; }
  }

  function aufnehmen() {
    if (!strom || !video.videoWidth) return;
    const MAX = 3200;  // reicht für Maßketten; Python verkleinert danach ohnehin auf 2400 px
    const f = Math.min(1, MAX / Math.max(video.videoWidth, video.videoHeight));
    const c = document.createElement("canvas");
    c.width = Math.round(video.videoWidth * f); c.height = Math.round(video.videoHeight * f);
    c.getContext("2d").drawImage(video, 0, 0, c.width, c.height);
    blitz.classList.add("an"); setTimeout(() => blitz.classList.remove("an"), 60);
    setTriggerValue("foto", c.toDataURL("image/jpeg", 0.92));
  }

  function selbstausloeser() {
    if (!strom || zaehler) return;
    let n = 3; zahl.textContent = n;
    zaehler = setInterval(() => {
      n -= 1;
      if (n > 0) { zahl.textContent = n; return; }
      clearInterval(zaehler); zaehler = null; zahl.textContent = ""; aufnehmen();
    }, 1000);
  }

  const taste = (e) => {
    if (!strom || e.code !== "Space" || e.repeat) return;
    const ziel = e.composedPath ? e.composedPath()[0] : e.target;
    if (ziel && /^(INPUT|TEXTAREA|SELECT)$/.test(ziel.tagName || "")) return;
    if (ziel && ziel.isContentEditable) return;
    e.preventDefault(); aufnehmen();
  };

  start.onclick = () => starten();
  $(".ausloesen").onclick = aufnehmen;
  $(".timer").onclick = selbstausloeser;
  $(".aus").onclick = stoppen;
  cams.onchange = () => starten(cams.value);
  document.addEventListener("keydown", taste);
  const aufraeumen = () => { document.removeEventListener("keydown", taste); stoppen(); delete parentElement.__wc; };
  parentElement.__wc = { aufraeumen, L };
  return aufraeumen;
}
"""

_WEBCAM: dict = {}


def _webcam_komponente():
    """Webcam-Komponente einmal je Streamlit-Laufzeit registrieren."""
    from streamlit.components.v2 import get_bidi_component_manager
    manager = get_bidi_component_manager()
    if _WEBCAM.get("manager") is not manager:
        _WEBCAM["manager"] = manager
        _WEBCAM["render"] = st.components.v2.component("bosch_webcam", html=WEBCAM_HTML, css=WEBCAM_CSS,
                                                       js=WEBCAM_JS)
    return _WEBCAM["render"]


def _webcam_texte() -> dict:
    return {
        "start": "🖥️&nbsp; " + T("Plan in die Webcam halten"),
        "ausloesen": "📸&nbsp; " + T("Aufnehmen") + " <small>(" + T("Leertaste") + ")</small>",
        "timer": "⏱️&nbsp; " + T("Selbstauslöser 3 s"), "aus": T("Kamera aus"), "kamera_waehlen": T("Kamera wählen"),
        "kein_zugriff": T("Der Browser erlaubt hier keinen Kamerazugriff (nur über https). Alternativ ein Foto über "
                          "„Pläne hochladen“ hinzufügen."),
        "abgelehnt": T("Kamerazugriff wurde abgelehnt – bitte in der Adressleiste erlauben und erneut starten."),
        "keine_webcam": T("Keine Webcam gefunden. Alternativ ein Foto über „Pläne hochladen“ hinzufügen."),
        "belegt": T("Die Webcam wird gerade von einem anderen Programm benutzt (z. B. Teams) – dort schließen und "
                    "erneut starten."),
        "startfehler": T("Webcam konnte nicht gestartet werden:"),
        "niedrig": T("Webcam liefert nur {w}×{h} – Plan nah an die Kamera halten oder besser mit dem Handy "
                     "fotografieren und hochladen."),
        "info": T("Webcam: {w}×{h} ({mp} MP) · Plan formatfüllend in den Rahmen halten, ruhig halten, gutes Licht · "
                  "ein Foto je Geschoss."),
        "kamera_n": T("Kamera {n}"),
    }


def webcam_bereich() -> None:
    """PC: Plan in die Webcam halten – Live-Bild, Aufnehmen (Leertaste) oder Selbstauslöser."""
    with st.container(key="webcam"):
        ergebnis = _webcam_komponente()(key="v2_webcam", data=_webcam_texte(), on_foto_change=lambda: None)
        roh = ergebnis.get("foto") if hasattr(ergebnis, "get") else getattr(ergebnis, "foto", None)
    if not roh:
        return
    try:
        foto = FO.WebcamFoto(FO.aus_data_url(roh))
    except FO.FotoFehler as fehler:
        st.error(str(fehler))
        return
    liste = _ss().setdefault("v2_webcam_fotos", [])
    if all(f.file_id != foto.file_id for f in liste):
        foto.name = f"webcam-{len(liste) + 1}.jpg"
        liste.append(foto)
        st.toast(T("Webcam-Foto übernommen – für das nächste Geschoss einfach erneut aufnehmen."))


def kamera_bereich() -> list:
    """Fotos aufnehmen: Tablet/Smartphone über die Gerätekamera, PC über die Webcam.
    Zeigt Vorschau mit Drehen; liefert die aufgenommenen Fotos."""
    with st.container(key="kamera"):
        fotos = st.file_uploader(T("Plan fotografieren"), type=["jpg", "jpeg", "png", "webp"],
                                 accept_multiple_files=True, label_visibility="collapsed", key="v2_kamera")
        st.html(KAMERA_JS, unsafe_allow_javascript=True)
        st.html(f'<style>:root {{--kamera-text:"📷  {T("Plan fotografieren")}"; '
                f'--kamera-weiter:"📷  {T("Weiteres Foto")}"}}</style>')
        st.caption(T("Tipp: Plan flach hinlegen, von oben fotografieren, ganzes Blatt im Bild, gutes Licht – "
                     "Maßketten müssen lesbar sein. Ein Foto je Geschoss; jedes neue Foto wird ergänzt."))
    webcam_bereich()
    webcam_fotos = _ss().get("v2_webcam_fotos", [])
    alle_bilder = [f for f in [*(_ss().get("v2_upload") or []), *(fotos or []), *webcam_fotos]
                   if Path(f.name).suffix.lower() != ".pdf"]
    if alle_bilder:
        drehung = _ss().setdefault("v2_drehung", {})
        spalten = st.columns(min(len(alle_bilder), 4))
        for i, f in enumerate(alle_bilder):
            with spalten[i % len(spalten)]:
                try:
                    st.image(FO.vorschau(f.getvalue(), drehung.get(f.file_id, 0)), width="stretch")
                except FO.FotoFehler:
                    st.caption(T("{name}: nicht lesbar", name=f.name))
                    continue
                k1, k2 = st.columns(2) if isinstance(f, FO.WebcamFoto) else (st.container(), None)
                if k1.button(T("Drehen"), icon=":material/rotate_right:", key=f"dreh-{f.file_id}", type="tertiary"):
                    drehung[f.file_id] = (drehung.get(f.file_id, 0) + 90) % 360
                    st.rerun()
                if k2 is not None and k2.button(T("Entfernen"), icon=":material/delete:", key=f"weg-{f.file_id}",
                                                type="tertiary"):
                    _ss().v2_webcam_fotos = [w for w in webcam_fotos if w.file_id != f.file_id]
                    st.rerun()
    return [*(fotos or []), *webcam_fotos]


def ki_eingaben(dateien: list) -> list[tuple[bytes, str]]:
    """Dateien für die Erkennung: PDFs unverändert, Fotos/Bilder aufbereitet (Drehung, Größe, Kontrast)."""
    drehung = _ss().get("v2_drehung", {})
    out = []
    for f in dateien:
        endung = Path(f.name).suffix.lower()
        if endung == ".pdf":
            out.append((f.getvalue(), MIME[".pdf"]))
        else:
            out.append((FO.aufbereiten(f.getvalue(), drehung.get(f.file_id, 0)), "image/jpeg"))
    return out


def beispiel_analyse() -> KiPlanAnalyse:
    """Beispielhaus – in der englischen Oberfläche mit englischen Raumnamen und Hinweisen."""
    analyse = KiPlanAnalyse.model_validate_json(BEISPIEL.read_text("utf-8"))
    if englisch():
        for r in analyse.raeume:
            r.name = T(r.name)
        analyse.hinweise = [T(h) for h in analyse.hinweise]
        analyse.nordrichtung = T(analyse.nordrichtung)
        for a in analyse.aufstellorte_aussengeraet:
            a.ort, a.begruendung = T(a.ort), T(a.begruendung)
    return analyse


def ki_uebernehmen(p: Projekt, analyse: KiPlanAnalyse) -> None:
    p.raeume = in_raeume(analyse) or p.raeume
    if analyse.baujahr and not _ss().get("v2_baujahr_manuell"):
        p.baujahr = analyse.baujahr
    baujahr_anwenden(p)
    _ss().v2_ki_info = {
        "hinweise": [T("Nordrichtung: {r}", r=analyse.nordrichtung), *analyse.hinweise],
        "aufstellorte": [(a.ort, a.begruendung) for a in analyse.aufstellorte_aussengeraet],
    }
    _ss().v2_toast = T("{n} Räume erkannt – bitte kurz durchsehen.", n=len(p.raeume))
    _ss().v2_geprueft = set()
    _ss().v2_rev += 1
    _ss().pop("v2_konzept", None)
    gehe("raeume", erledigt="system")


# ====================================================================== Seiten
def _auslauf_liste(kat: Katalog, an: bool) -> str:
    """Welche Artikel der Schalter „Auslaufartikel“ betrifft – gruppiert nach Serie."""
    gruppen: dict[str, list[str]] = {}
    for a in kat.auslaufartikel:
        art = "Set" if a.aussen_typ else T("Multi-Innengerät")
        gruppen.setdefault(f"{a.linie} – {art}", []).append(
            a.typ + (f" ({T(a.farbe)})" if a.farbe not in ("", "weiß") else ""))
    zeilen = "".join(f"<li><b>{g}</b>: {', '.join(t)}</li>" for g, t in gruppen.items())
    kopf = (T("{n} Auslaufartikel werden bei der Auswahl berücksichtigt (Preise Stand 03/2026):",
              n=len(kat.auslaufartikel))
            if an else T("{n} Artikel sind ausgeblendet, weil sie im Ergänzungskatalog 09/2026 fehlen – mit dem "
                         "Schalter für Altprojekte wieder zulassen:", n=len(kat.auslaufartikel)))
    return f'<div class="auslauf-liste{" an" if an else ""}">{kopf}<ul>{zeilen}</ul></div>'


def seite_system(p: Projekt, kat: Katalog | None = None) -> None:
    ki_bereich(p, gross=True)
    st.write("")
    st.markdown("#### " + T("Welches System wünschen Sie?"))
    karten("sys", [(v, t, s, v) for v, t, s in SYSTEME], p.systemwunsch,
           lambda v: setattr(p, "systemwunsch", v))
    st.markdown("#### " + T("Was soll die Anlage leisten?"))
    karten("ba", [(v, t, s, v) for v, t, s in BETRIEB], p.einstellungen.betriebsart,
           lambda v: setattr(p.einstellungen, "betriebsart", v))
    st.markdown("#### " + T("Bevorzugte Gerätelinie"))

    def linien_ikon(v: str) -> str:
        if v not in LINIEN_BILD:
            return svg("auto", 56)
        pfad = Path(__file__).parent / "splitklima" / "daten" / "bilder" / f"{LINIEN_BILD[v]}.png"
        return f'<img src="data:image/png;base64,{_b64(pfad)}" style="height:56px">'

    untertitel = {"": N_("Wir wählen die günstigste passende Lösung."), "3200i": N_("Solide Wandgeräte, günstig."),
                  "7000i": N_("Leise, BEG-förderfähig mit MSG-1, auch silber/schwarz."),
                  "8000i": N_("Design-Linie, anthrazit/silber/rot – nur als Set.")}
    karten("linie", [(v, t, untertitel[v], linien_ikon(v)) for v, t in A.GERAETELINIEN.items()], p.geraetelinie,
           lambda v: (setattr(p, "geraetelinie", v), _ss().pop("v2_konzept", None)), spalten=4, klein=True)
    auslauf = st.toggle(T("Auslaufartikel anzeigen"), p.auslaufartikel, key=_k("auslauf"),
                        help=T("Geräte, die im Ergänzungskatalog 09/2026 nicht mehr enthalten sind: "
                               "Climate 3000i (Sets und Multi-Inneneinheiten) und CLC8001i-Set 35. "
                               "Für Altprojekte; Preise Stand 03/2026."))
    if auslauf != p.auslaufartikel:
        p.auslaufartikel = auslauf
        _ss().pop("v2_konzept", None)
        st.rerun()
    if kat is not None and kat.auslaufartikel:
        st.markdown(_auslauf_liste(kat, p.auslaufartikel), unsafe_allow_html=True)
    st.markdown("#### " + T("Wo steht die Außeneinheit?"))
    karten("aufst", [(v, t, AUFSTELLUNG_UNTERTITEL[v], f"ae_{v}" if v else "egal") for v, t in A.AUFSTELLUNG.items()],
           p.aufstellung, lambda v: setattr(p, "aufstellung", v), spalten=4, klein=True)
    _weiter_zurueck(None, ("gebaeude", N_("Weiter zum Gebäude")), "system")


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
    s = f"{x:.1f}"
    return f"{s if englisch() else s.replace('.', ',')} °C".replace("-", "−")


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
            st.caption(T("Die PLZ-genauen Werte der DIN/TS 12831-1 werden gerade von der BWP-Klimakarte geladen …"))
        warten()
        return
    if zustand["status"] == "fehler":
        st.caption(T("Automatisches Laden der BWP-Klimakarte nicht möglich:") + " " + (zustand["meldungen"] or ["–"])[0])
    else:
        st.caption(T("Die PLZ-genauen Werte der DIN/TS 12831-1 sind noch nicht hinterlegt."))
    c1, c2 = st.columns(2)
    if c1.button(T("BWP-Klimakarte laden"), icon=":material/cloud_download:", key="klima_laden",
                 width="stretch"):
        with st.spinner(T("Klimakarte wird geladen und geprüft …")):
            ok, meldungen = KD.von_bwp_laden(timeout=45)
        zustand.update(status="ok" if ok else "fehler", meldungen=meldungen)
        _ss().v2_klima_meldung = (ok, meldungen)
        st.rerun()
    with c2.popover(T("Tabelle hochladen"), icon=":material/upload_file:", width="stretch"):
        st.caption(T("Excel oder CSV mit den Spalten PLZ, Norm-Außentemperatur und optional Jahresmitteltemperatur "
                     "(z. B. Export der Klimakarte)."))
        datei = st.file_uploader(T("Klimadaten"), type=["csv", "xlsx", "txt"], label_visibility="collapsed",
                                 key="klima_upload")
        if datei is not None and st.button(T("Übernehmen"), type="primary", key="klima_upload_ok"):
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
            st.markdown(f'<div style="font-size:.85rem;color:#5c6773">{T("Norm-Außentemperatur θe")}</div>'
                        f'<div class="preis">{grad(e.norm_aussen)}</div>', unsafe_allow_html=True)
            if p.norm_aussen_manuell:
                quelle = T("manuell eingegeben") + (T(" (PLZ-Wert: {w})", w=grad(wert.theta_e)) if wert else "")
            else:
                quelle = klimaquelle(p.klima_quelle or (wert.quelle if wert else ""))
            st.caption(f"{p.ort} · {quelle}")
            if wert and not p.norm_aussen_manuell:
                details = []
                if wert.theta_m is not None:
                    details.append(T("Jahresmittel θm,e {t}", t=grad(wert.theta_m)))
                if wert.hoehe is not None:
                    details.append(T("Höhe {h} m", h=f"{wert.hoehe:.0f}"))
                if wert.klimazone:
                    details.append(T("Klimazone {z}", z=wert.klimazone))
                if details:
                    st.caption(" · ".join(details))
            if msg := _ss().pop("v2_klima_meldung", None):
                ok, meldungen = msg
                (st.success if ok else st.error)((T("Klimadaten übernommen.") + " " if ok else "") + " ".join(meldungen[:3]))
            if wert and wert.status == "richtwert" and not p.norm_aussen_manuell:
                _klimadaten_laden_ui()
        with c2:
            manuell = st.toggle(T("Wert anpassen"), p.norm_aussen_manuell, key=_k("ta_manuell"))
            if manuell:
                neu = zahl(st, T("Norm-Außentemperatur"), "°C", e.norm_aussen, -25.0, 0.0, 0.1, "ta_wert")
                if not p.norm_aussen_manuell or neu != e.norm_aussen:
                    e.norm_aussen, p.norm_aussen_manuell = round(neu, 1), True
                    p.klima_quelle = "manuell eingegeben"
            elif p.norm_aussen_manuell:  # zurück auf den PLZ-Wert
                eintrag = KP.eintrag(p.plz)
                if eintrag:
                    standort_setzen(p, eintrag)
                    st.rerun()
            st.caption(T("Sommer-Auslegung {t} °C", t=de(e.sommer)))


def seite_gebaeude(p: Projekt) -> None:
    e = p.einstellungen
    st.markdown("#### " + T("Wo steht das Gebäude?"))
    c1, c2 = st.columns(2)
    p.name = c1.text_input(T("Projektname"), p.name, key=_k("name"))
    eingabe = c2.text_input(T("PLZ oder Ort"), p.ort, key=_k("ort"), placeholder=T("z. B. 72622 oder Nürtingen"))
    if eingabe.strip() != p.ort:
        treffer = KP.suche(eingabe)
        if len(treffer) == 1:
            standort_setzen(p, treffer[0])
            st.rerun()
        elif treffer:
            wahl = c2.selectbox(T("Bitte auswählen"), [None, *treffer], format_func=lambda t: t.text if t else "–",
                                key=_k(f"ortwahl_{eingabe}"))
            if wahl:
                standort_setzen(p, wahl)
                st.rerun()
        else:
            c2.error(T("Diese PLZ bzw. diesen Ort gibt es in Deutschland nicht – bitte prüfen."))
    _klima_karte(p)

    st.markdown("#### " + T("Baujahr"))
    c1, _ = st.columns([1, 2])
    bj = c1.number_input(T("Baujahr"), 1850, datetime.now().year, int(p.baujahr or 1995), step=1, key=_k("bj"),
                         label_visibility="collapsed")
    if bj != p.baujahr:
        p.baujahr = int(bj)
        _ss().v2_baujahr_manuell = True
        baujahr_anwenden(p)
    st.caption(T({"old": "Altbau vor 1979 – wenig Dämmung", "mid": "Baujahr 1979–2001 – mittlerer Dämmstandard",
                  "new": "ab 2002 – guter Dämmstandard (EnEV/GEG)"}[e.daemmstandard]))
    c1, _ = st.columns([2, 1])
    optionen = list(P.NACHDAEMMUNG_V2)
    nach = c1.selectbox(T("Außenwände nachträglich gedämmt"), optionen,
                        index=optionen.index(p.nachdaemmung) if p.nachdaemmung in optionen else 0,
                        format_func=lambda v: T(P.NACHDAEMMUNG_V2[v]), key=_k("nachdaemmung"),
                        help=T("Sanierung nach dem Baujahr, z. B. Haus von 1958 mit Fassadendämmung 1990. "
                               "Gilt für alle Räume; einzelne Räume kann der Planungs-Assistent abweichend setzen."))
    if nach != p.nachdaemmung:
        p.nachdaemmung = nach
        for r in p.raeume:
            r.daemmung = nach

    st.markdown("#### " + T("Fenster"))
    karten("glas", VERGLASUNG, e.verglasung, lambda v: setattr(e, "verglasung", v), klein=True, groesse=44)
    if e.sonnenschutz == "0.55":
        e.sonnenschutz = "0.45"
    st.markdown("#### " + T("Sonnenschutz"))
    karten("shade", SONNENSCHUTZ, e.sonnenschutz, lambda v: setattr(e, "sonnenschutz", v), klein=True, groesse=44)
    _weiter_zurueck(("system", N_("System")), ("raeume", N_("Weiter zu den Räumen")), "gebaeude")


def _raum_neu(p: Projekt) -> None:
    neu = Raum(name=T("Raum {n}", n=len(p.raeume) + 1), lage="outside", waende=[Wand(ausrichtung="S", laenge=4, fenster=2)],
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
    kopf_l.markdown("#### " + T("Ihre Räume ({n})", n=len(p.raeume)))
    if info and info["hinweise"]:
        with kopf_r.popover(T("Hinweise zur Erkennung ({n})", n=len(info["hinweise"])), width="stretch",
                            icon=":material/info:"):
            for h in info["hinweise"]:
                st.markdown(f"- {h}")

    if not p.raeume:
        st.caption(T("Noch keine Räume – Grundriss hochladen oder Räume von Hand anlegen."))
    spalten = st.columns(3)
    geprueft = _ss().v2_geprueft
    for i, r in enumerate(p.raeume):
        l = raum_last(r, p.einstellungen)
        status = T("✓ geprüft") if i in geprueft else T("bitte prüfen")
        with spalten[i % 3].container(border=True, key=f"karte-raum-{i}"):
            st.markdown(
                f'<div class="karte klein"><div>{svg(r.raumart, 44)}</div>'
                f'<div class="titel">{r.name}</div><div class="sub">{r.geschoss or "–"} · {de(r.flaeche)} m² · '
                f'{de(l.cool, 2)} kW {T("Kühlen")}'
                + (f' · {T("{n} Pers.", n=r.personen)}' if r.personen else "")
                + f'</div><div class="sub">{status}</div></div>', unsafe_allow_html=True)
            if st.button(T("{name} bearbeiten", name=r.name), key=f"kbtn-{_k('raum')}-{i}"):
                gehe("raum", raum=i)
    if st.button(T("Raum hinzufügen"), icon=":material/add:"):
        _raum_neu(p)
    _weiter_zurueck(("gebaeude", N_("Gebäude")), ("ergebnis", N_("Zum Ergebnis")) if p.raeume else None, "raeume")


def personen_bereich(p: Projekt, r: Raum, i: int) -> None:
    """Personen gleichzeitig im Raum (z. B. Seminar, Forum, Schulung): Wärme je Person und Frischluft."""
    c1, c2, c3 = st.columns([1, 1.5, 1.5], vertical_alignment="bottom")
    r.personen = int(c1.number_input(
        T("Personen gleichzeitig"), 0, 2000, int(r.personen or 0), 1, key=_k(f"rpers{i}"),
        help=T("Personen, die sich in der Spitzenzeit gleichzeitig im Raum aufhalten. 0 = übliche Nutzung "
               "(in der Grundlast enthalten). Je Person 120 W sitzend bzw. 150 W stehend/aktiv, inkl. Feuchte "
               "(VDI 2078).")))
    if not r.personen:
        return
    r.taetigkeit = c2.selectbox(T("Tätigkeit"), list(P.PERSON_W), index=list(P.PERSON_W).index(r.taetigkeit),
                                format_func=lambda v: T(P.PERSON_LABEL[v]), key=_k(f"rtaet{i}"),
                                help=T("Sitzend: Schulung, Seminar, Besprechung. Stehend/aktiv: Empfang, Ausstellung, "
                                       "Veranstaltung mit Bewegung."))
    r.lueftung = c3.selectbox(T("Frischluft"), list(P.LUEFTUNG_LABEL), index=list(P.LUEFTUNG_LABEL).index(r.lueftung),
                              format_func=lambda v: T(P.LUEFTUNG_LABEL[v]), key=_k(f"rlueft{i}"),
                              help=T("Fensterlüftung: 30 m³/h Außenluft je Person kommen ungekühlt herein und werden "
                                     "in der Kühllast mitgerechnet. Lüftungsanlage mit Wärmerückgewinnung (WRG): "
                                     "nur ein Restanteil von etwa 25 % zählt."))
    l = raum_last(r, p.einstellungen)
    st.caption(T("Personen: +{w} kW Wärme · Außenluft {q} m³/h ({je} m³/h je Person).", w=de(l.personen_w / 1000, 1),
                 q=f"{l.luft_m3h:,.0f}".replace(",", "." if not englisch() else ","), je=P.AUSSENLUFT_JE_PERSON))
    if r.lueftung == "fenster" and r.personen >= 10:
        st.info(T("Split-Klimageräte kühlen nur die Raumluft und liefern keine Frischluft. Bei {n} Personen wird "
                  "eine Lüftungsanlage mit Wärmerückgewinnung empfohlen. Die Kühllast enthält hier die Außenluft der "
                  "Fensterlüftung; im Winter erhöht sie zusätzlich die Heizlast (in der Heizlast nicht enthalten).",
                  n=r.personen), icon=":material/air:")


def seite_raum(p: Projekt, i: int, kat: Katalog | None = None) -> None:
    if not p.raeume:
        gehe("raeume")
    i = min(i, len(p.raeume) - 1)
    r = p.raeume[i]
    _ss().v2_geprueft.add(i)

    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    c1.caption(T("RAUM {i} VON {n}", i=i + 1, n=len(p.raeume)))
    r.name = c1.text_input(T("Raumname"), r.name, key=_k(f"rn{i}"))
    r.geschoss = c2.text_input(T("Geschoss"), r.geschoss, key=_k(f"rg{i}"), placeholder=T("EG, OG, DG …"))

    st.markdown("##### " + T("Nutzung"))
    def raumart_setzen(v: str) -> None:
        r.raumart = v
        if v == "Seminar / Schulung" and not r.personen:
            r.personen = r.personen_vorschlag()
            _ss().v2_rev += 1

    karten(f"ra{i}", [(v, RAUMART_KURZ_EN.get(v, RAUMART_KURZ[v]) if englisch() else RAUMART_KURZ[v], "", v)
                      for v in RAUMARTEN_ALLE], r.raumart, raumart_setzen, spalten=5, klein=True, groesse=40)
    if r.raumart in P.RAUMARTEN_GEWERBE and r.raumart != "Seminar / Schulung":
        st.caption(T(P.GEWERBE_HINWEIS))
    personen_bereich(p, r, i)

    st.markdown("##### " + T("Größe"))
    c1, c2, _ = st.columns([1, 1, 1])
    flaeche = zahl(c1, T("Grundfläche"), "m²", r.flaeche or 1, 1.0, 500.0, 0.5, f"rf{i}")
    if flaeche != r.flaeche:
        r.flaeche = flaeche
        if r.waende_auto:
            r.wandlaengen_schaetzen()
    r.hoehe = zahl(c2, T("Raumhöhe"), "m", r.hoehe or 2.5, 1.8, 10.0, 0.05, f"rh{i}", "%.2f")

    st.markdown("##### " + T("Lage im Gebäude"))

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
                "ausrichtung": st.column_config.SelectboxColumn(
                    T("Außenwand zeigt nach"), options=P.AUSRICHTUNGEN, required=True,
                    format_func=lambda v: RICHTUNG_EN.get(v, v) if englisch() else v),
                "laenge": st.column_config.NumberColumn(T("Wandlänge (m)"), min_value=0.0, step=0.1, required=True,
                                                        format="%.1f m"),
                "fenster": st.column_config.NumberColumn(T("Fensterfläche (m²)"), min_value=0.0, step=0.1,
                                                         required=True, format="%.1f m²"),
            })
        neu_waende = [Wand(**z) for z in wdf.to_dict("records")]
        if r.waende_auto and [w.laenge for w in neu_waende] != [w.laenge for w in r.waende]:
            r.waende_auto = False  # Länge von Hand geändert → nicht mehr automatisch nachführen
        r.waende = neu_waende
        if r.waende_auto:
            st.caption(T("Wandlängen aus der Grundfläche geschätzt (≈ √{a} m² = {l} m) – bitte an den Grundriss "
                         "anpassen. Nach einer Änderung bleiben Ihre Werte stehen.",
                         a=de(r.flaeche), l=de(r.waende[0].laenge)))
        elif st.button(T("Wandlängen aus Grundfläche schätzen"), icon=":material/straighten:", type="tertiary",
                       key=_k(f"wschaetz{i}")):
            r.waende_auto = True
            r.wandlaengen_schaetzen()
            _ss().v2_rev += 1
            st.rerun()
    else:
        st.caption(T("Innenliegender Raum – keine Außenwände."))

    st.markdown("##### " + T("Dach über dem Raum"))
    dg = r.lage in DG_LAGEN

    def dach_setzen(v: str) -> None:
        r.dach = bool(v) or dg
        if v:
            r.dachform = v
        _ss().v2_rev += 1

    dach_optionen = ([] if dg else [("", N_("Geschoss darüber"), "dach_nein")]) + DACHFORMEN
    karten(f"dach{i}", [(v, t, "", s) for v, t, s in dach_optionen], r.dachform if r.dach else "", dach_setzen,
           spalten=5, klein=True, groesse=40)
    if r.dach and r.dachform == "flat":
        st.caption(T("Flachdach: Die Dachfläche ist den ganzen Tag besonnt – die Kühllast steigt deutlich "
                     "(Dachfläche = Grundfläche). Lichtkuppeln unten als Dachfenster eintragen."))
    if r.dach:
        df = sum(g.flaeche for g in r.fenstergruppen if g.dachfenster)
        c1, _ = st.columns([1, 2])
        neu = zahl(c1, T("Dachfenster / Lichtkuppeln"), "m²", df, 0.0, 50.0, 0.1, f"rdf{i}")
        if neu != df:
            r.fenstergruppen = [g for g in r.fenstergruppen if not g.dachfenster]
            if neu > 0:
                r.fenstergruppen.append(Fenstergruppe(ausrichtung="S", flaeche=neu, dachfenster=True))

    st.markdown("##### " + T("Gerätewunsch"))
    wunsch = A.bauart_wunsch(r)
    karten(f"bau{i}", [(v, t, "", s) for v, t, s in BAUART], wunsch,
           lambda v: setattr(r, "ig_bauart", v or "auto"), spalten=5, klein=True, groesse=44)
    if wunsch in ("", "Wandgerät"):
        st.markdown("##### " + T("Farbe der Inneneinheit"))
        farben = [("", N_("Keine Präferenz"), "", '<span class="farbpunkt" style="background:linear-gradient('
                   '135deg,#f4f5f6 50%,#c3c8cd 50%)"></span>')]
        farben += [(f, f.capitalize(), "", f'<span class="farbpunkt" style="background:{FARBCODE[f]}"></span>')
                   for f in FARBEN]
        karten(f"farbe{i}", farben, r.farbe, lambda v: setattr(r, "farbe", v), spalten=6, klein=True)
        if r.farbe and r.farbe != "weiß":
            st.caption(T("Farbige Inneneinheiten gibt es in den Serien Climate 7000i (silber, schwarz) und "
                         "Climate Class 8000i (anthrazit, silber, rot)."))
            grenze = A.farbgrenze(r, kat) if kat else None
            last = raum_last(r, p.einstellungen)
            if grenze and last.cool > grenze[0]:
                st.info(T("„{farbe}“ gibt es bis {max} kW je Gerät. Dieser Raum braucht {last} kW – wir planen "
                          "deshalb mehrere Geräte in {farbe_klein}. Für ein einzelnes Gerät „Keine Präferenz“ wählen.",
                          farbe=T(r.farbe.capitalize()), max=de(grenze[0]), last=de(last.cool, 2),
                          farbe_klein=T(r.farbe)), icon=":material/palette:")
    elif wunsch == "Truhe/Decke":
        st.caption(T("Ceiling/Floor-Truhengeräte (Climate 5000i L) – unter der Decke oder am Boden, 5,3 bis 16 kW, "
                     "auch als Twin."))
    elif wunsch:
        st.caption(T("{bauart}n: als Large-Split-Set (Climate 5000i L) oder als Multi-Split-Inneneinheit.",
                     bauart=T(wunsch)))

    st.write("")
    c1, c2, c3 = st.container(key="wz-raum").columns([1, 1.3, 1.7])
    if c3.button(T("Raum entfernen"), icon=":material/delete:", type="tertiary"):
        p.raeume.pop(i)
        _ss().v2_geprueft = {j if j < i else j - 1 for j in _ss().v2_geprueft if j != i}
        _ss().v2_rev += 1
        gehe("raeume")
    zurueck = ("raum", i - 1) if i > 0 else ("raeume", None)
    weiter = ("raum", i + 1) if i < len(p.raeume) - 1 else ("ergebnis", None)
    if c1.button(T("Zurück"), icon=":material/arrow_back:", width="stretch"):
        gehe(zurueck[0], raum=zurueck[1])
    if c2.button(T("Nächster Raum") if weiter[0] == "raum" else T("Zum Ergebnis"), type="primary", width="stretch",
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
                art += T(" mit {n} Innengeräten", n=t.set.anzahl_ie)
            st.markdown(f"**{T(t.bezeichnung)}** · {art}")
            st.caption(T("{typ} · Kühlen {k} kW · Heizen {h} kW", typ=haupt.typ if haupt else "–",
                         k=de(t.leistung_kuehl, 1), h=de(t.leistung_heiz, 1)))
            geraete = [(r, t.set) for r in t.raeume] if t.set else t.innen
            for r, u in geraete:
                farbe = f" · {T(u.farbe)}" if u.farbe and u.farbe != "weiß" else ""
                st.markdown(f"<span style='font-size:.88rem'>▸ {r.name}: {u.typ if t.aussen else T('Inneneinheit')}"
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
    """Betrag mit Cent (Deutsch 1.970,64 €, Englisch €1,970.64)."""
    from splitklima.sprache import euro

    return euro(betrag, cent=True)


def _zubehoer_bild(nr: str) -> str | None:
    pfad = Z.bild(nr)
    return _bild_uri(str(pfad)) if pfad else None


def zubehoer_bereich(p: Projekt, k: A.Konzept, kat: Katalog) -> None:
    """Zubehör und Montagematerial: Vorschlag aus dem Konzept, Mengen frei änderbar.
    Das Fenster bleibt offen, bis es selbst zugeklappt wird (fester Schlüssel statt wechselndem Titel)."""
    zeilen, _ = Z.tabelle(p, k, kat)
    summe = Z.summe(zeilen)
    bedarf, mit_wlan, ohne_wlan = Z.gateway_bedarf(k)
    with st.expander(T("Zubehör und Montagematerial"), icon=":material/handyman:", key="zubehoer-fenster"):
        st.markdown("**" + T("Summe Zubehör: {s}", s=fmt_eur(summe)) + "**")
        c1, _ = st.columns([1, 1])
        laenge = zahl(c1, T("Leitungslänge je Innengerät"), "m", p.leitungslaenge, 1.0, 50.0, 1.0, "zlaenge", "%.0f")
        c2, c3, c4 = st.columns(3)
        if bedarf:
            app = c2.toggle(T("App-Steuerung (WLAN)"), p.app_steuerung, key=_k("zapp"),
                            help=T("Internet-Gateways für Innengeräte ohne integriertes WLAN")
                                 + (T(" ({n} von {gesamt} Geräten).", n=ohne_wlan, gesamt=mit_wlan + ohne_wlan)
                                    if mit_wlan else "."))
        else:
            c2.toggle(T("App-Steuerung (WLAN)"), True, key=_k("zapp_fest"), disabled=True,
                      help=T("WLAN ist bei allen Innengeräten integriert (Climate 7000i / Class 8000i) – "
                             "kein Gateway nötig."))
            app = p.app_steuerung
        boerdel = c3.toggle(T("Bördelfrei (Klemmring)"), p.boerdelfrei, key=_k("zboerdel"),
                            help=T("SAE-Klemmringverschraubungen, 2 je Leitung und Seite."))
        pumpe = c4.toggle(T("Kondensatpumpe"), p.kondensatpumpe, key=_k("zpumpe"),
                          help=T("Wenn das Kondensat nicht mit Gefälle abgeleitet werden kann. Kassetten haben eine "
                                 "integrierte Pumpe."))
        if not bedarf:
            c2.caption(T("WLAN integriert"))
        if (laenge, app, boerdel, pumpe) != (p.leitungslaenge, p.app_steuerung, p.boerdelfrei, p.kondensatpumpe):
            p.leitungslaenge, p.app_steuerung, p.boerdelfrei, p.kondensatpumpe = laenge, app, boerdel, pumpe
            st.rerun()
        st.caption(T("WLAN") + ": " + " · ".join(Z.wlan_uebersicht(k)))
        alle = st.toggle(T("Alle Zubehörartikel zeigen"), key=_k("zalle"),
                         help=T("Auch Artikel, die nicht automatisch vorgeschlagen werden – Menge mit + erhöhen."))
        sichtbar = [z for z in zeilen if not z.gesperrt and (alle or z.vorschlag or z.menge)]
        if not sichtbar:
            st.info(T("Für diese Lösung gibt es keinen automatischen Zubehörvorschlag – z. B. Large-Split über 7 kW "
                      "(Kältemittelleitung bauseits) ohne gewählten Aufstellort. Über „Alle Zubehörartikel zeigen“ "
                      "können Sie Artikel manuell ergänzen."), icon=":material/info:")
        neu = dict(p.zubehoer_mengen)
        gruppe = None
        for z in sichtbar:
            if z.gruppe != gruppe:
                gruppe = z.gruppe
                st.markdown(f'<div class="zub-gruppe">{T(gruppe)}</div>', unsafe_allow_html=True)
            manuell = z.bestellnr in p.zubehoer_mengen
            with st.container(key=f"zubrow-{z.bestellnr}"):
                c1, c2, c3, c4 = st.columns([0.9, 4.2, 1.5, 1.2], vertical_alignment="center")
                uri = _zubehoer_bild(z.bestellnr)
                c1.markdown(f'<img class="zub-bild" src="{uri}">' if uri else "", unsafe_allow_html=True)
                warum = z.grund + (T(" · Menge von Hand geändert") if manuell else "")
                c2.markdown(f'<div class="zub-name">{T(z.name)}</div><div class="zub-info">{z.bestellnr} · '
                            f'{T("{p} je Stück", p=fmt_eur2(z.einzelpreis))}</div><div class="zub-warum">{warum}</div>',
                            unsafe_allow_html=True)
                menge = c3.number_input(T("Menge"), 0, 999, int(z.menge), 1, label_visibility="collapsed",
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
        # Nicht wählbare Artikel nur in der Gesamtansicht zeigen – sonst wirken sie wie eine Auswahl
        gesperrt = [z for z in zeilen if z.gesperrt] if alle else []
        for titel, auswahl in ((T("Nicht erforderlich – WLAN integriert"), [z for z in gesperrt if z.wlan_integriert]),
                               (T("Passt nicht zu den gewählten Geräten"),
                                [z for z in gesperrt if not z.wlan_integriert])):
            if auswahl:
                st.markdown(f'<div class="zub-gesperrt-titel">{titel} – {T("nicht wählbar")}</div>',
                            unsafe_allow_html=True)
                st.markdown("".join(
                    '<div class="zub-gesperrt">'
                    + (f'<img src="{_zubehoer_bild(z.bestellnr)}">' if _zubehoer_bild(z.bestellnr) else "<span></span>")
                    + f'<span><b>{T(z.name)}</b> · {z.bestellnr}</span><span>{z.gesperrt}</span></div>'
                    for z in auswahl), unsafe_allow_html=True)
        geraete = k.preis
        st.markdown("**" + T("Summe Zubehör: {s}", s=fmt_eur(summe)) + "**" + (
            " · " + T("Geräte + Zubehör: **{s}**", s=fmt_eur(geraete + summe))
            if geraete is not None and summe is not None else ""))
        c1, c2 = st.columns([2, 1], vertical_alignment="center")
        c1.caption(T(Z.VORKALKULATION) + " " + T("Vorschlag aus Konzept, Aufstellort und Leitungslänge – Mengen mit "
                                                 "+/− anpassen.") + f" {T(kat.preisbasis)}.")
        if p.zubehoer_mengen and c2.button(T("Vorschlag wiederherstellen"), icon=":material/restart_alt:",
                                           type="tertiary"):
            p.zubehoer_mengen = {}
            _ss().v2_rev += 1
            st.rerun()


def _chat_senden(p: Projekt, kat: Katalog, text: str) -> None:
    ss = _ss()
    ss.v2_chat.append({"rolle": "user", "text": text})
    if ss.v2_chat_zaehler >= AS.MAX_NACHRICHTEN:
        ss.v2_chat.append({"rolle": "assistant", "text": T("Für diese Sitzung ist das Nachrichtenlimit erreicht – "
                                                           "bitte die Seite neu laden.")})
        return
    ss.v2_chat_zaehler += 1
    sicherung = (p.model_dump_json(), ss.get("v2_konzept"))
    zustand = {"konzept": ss.get("v2_konzept")}
    try:
        antwort = AS.antworten(ss.v2_chat_api, text, p, kat, zustand, sprache="en" if englisch() else "de")
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
    for feld, name, einheit in (("kuehllast_kw", T("Kühllast"), " kW"), ("heizlast_kw", T("Heizlast"), " kW")):
        a, b = vorher.get(feld), nachher.get(feld)
        if a is not None and b is not None and a != b:
            teile.append(f"{name} {de(a, 2)} → {de(b, 2)}{einheit}")
    if vorher.get("preis") != nachher.get("preis") and nachher.get("preis"):
        teile.append(T("Preis {a} → {b}", a=vorher.get("preis", "–"), b=nachher["preis"]))
    if vorher.get("loesung") != nachher.get("loesung") and nachher.get("loesung"):
        teile.append(T("Lösung: {l}", l=nachher["loesung"]))
    return " · ".join(teile)


def planungs_assistent(p: Projekt, kat: Katalog) -> None:
    """Chat-Blase unten rechts: Änderungen an der Planung per Text (nur die eigene Sitzung)."""
    ss = _ss()
    for key, start in (("v2_chat", []), ("v2_chat_api", []), ("v2_chat_zaehler", 0), ("v2_chat_offen", False)):
        if key not in ss:
            ss[key] = start if not isinstance(start, list) else list(start)
    if not ss.v2_chat_offen:
        with st.container(key="chatfab"):
            if st.button(T("Planungs-Assistent"), icon=":material/forum:", key="chat-oeffnen"):
                ss.v2_chat_offen = True
                st.rerun()
        return
    with st.container(key="chatpanel"):
        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        c1.markdown(f'<div class="chat-titel">{T("Planungs-Assistent")} <span class="v2-badge">Beta</span></div>',
                    unsafe_allow_html=True)
        if c2.button("", icon=":material/close:", key="chat-schliessen", help=T("Schließen")):
            ss.v2_chat_offen = False
            st.rerun()
        bereit = schluessel_vorhanden()
        verlauf = st.container(height=360, key="chatverlauf", border=False)
        with verlauf:
            with st.chat_message("assistant", avatar=":material/support_agent:"):
                st.markdown(T("Hallo! Beschreiben Sie einfach, was an der Planung anders sein soll – ich passe sie an "
                              "und zeige, was sich ändert."))
            letzte = max((i for i, e in enumerate(ss.v2_chat) if e.get("sicherung")), default=-1)
            for i, eintrag in enumerate(ss.v2_chat):
                with st.chat_message(eintrag["rolle"],
                                     avatar=":material/person:" if eintrag["rolle"] == "user"
                                     else ":material/support_agent:"):
                    st.markdown(eintrag["text"])
                    if eintrag.get("aenderungen"):
                        st.caption(T("Geändert:") + " " + " · ".join(eintrag["aenderungen"]))
                        vergleich = _vergleich(eintrag.get("vorher", {}), eintrag.get("nachher", {}))
                        if vergleich:
                            st.caption(vergleich)
                    if eintrag.get("rueckgaengig"):
                        st.caption("↩ " + T("Rückgängig gemacht."))
                    elif i == letzte and st.button(T("Rückgängig"), icon=":material/undo:", key=f"chat-undo-{i}",
                                                   type="tertiary"):
                        _chat_rueckgaengig(eintrag)
                        st.rerun()
            if not ss.v2_chat and bereit:
                for j, beispiel in enumerate(T(b) for b in BEISPIELE):
                    if st.button(beispiel, key=f"chat-bsp-{j}", type="secondary", width="stretch"):
                        with st.spinner(T("Der Assistent arbeitet …")):
                            _chat_senden(p, kat, beispiel)
                        st.rerun()
        if not bereit:
            st.info(T("Der Assistent ist auf diesem Server noch nicht eingerichtet (API-Schlüssel fehlt)."),
                    icon=":material/key_off:")
            return
        text = st.chat_input(T("Was soll anders sein?"), key="chat-eingabe", max_chars=1500)
        if text:
            with st.spinner(T("Der Assistent arbeitet …")):
                _chat_senden(p, kat, text)
            st.rerun()
        st.caption(T("Ändert nur Ihre Planung in dieser Sitzung. Eingaben werden zur Auswertung an die Claude API "
                     "übertragen – keine personenbezogenen Kundendaten eingeben."))


def seite_ergebnis(p: Projekt, kat: Katalog) -> None:
    liste = _konzepte(p, kat)
    gewaehlt = _gewaehlt(liste)
    if gewaehlt is None:
        st.error(T("Für diese Räume gibt es mit dem gewählten System keine passende Lösung im Sortiment. "
                   "Bitte ein anderes System oder eine andere Bauart wählen oder große Räume aufteilen."))
        for k in liste:
            for h in k.hinweise:
                st.caption(h)
        _weiter_zurueck(("raeume", N_("Räume")), None, "ergebnis")
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
            st.markdown(f'<span class="empf">{T("UNSERE EMPFEHLUNG")}</span>' if gewaehlt is empfohlen
                        else f'<span class="empf" style="background:#5c6773">{T("IHRE AUSWAHL")}</span>',
                        unsafe_allow_html=True)
            st.markdown(f"## {gewaehlt.name}")
            st.markdown(gewaehlt.beschreibung)
            st.caption(gewaehlt.geraete_text)
        with c2:
            st.markdown(f'<div class="preis">{fmt_eur(preis)}</div>', unsafe_allow_html=True)
            st.caption(T("Gerätepreis") + f" · {T(kat.preisbasis)}")
            if gewaehlt is not empfohlen:
                st.caption(T("Empfohlen wäre: {name} ({preis})", name=empfohlen.name, preis=fmt_eur(empfohlen.preis)))
        if bilder:
            for sp, pf in zip(st.container(key="konzeptbilder").columns(len(bilder) + 1), bilder):
                sp.image(str(pf), width=min(BILD_MAX, Image.open(pf).width))
        m = st.container(key="kennzahlen").columns(4)
        m[0].metric(T("Außengeräte"), gewaehlt.aussengeraete)
        m[1].metric(T("Innengeräte"), gewaehlt.innengeraete)
        m[2].metric(T("Kühlleistung"), f"{de(gewaehlt.leistung_kuehl)} kW", help=T("Summe Nennleistung Außengeräte"))
        m[3].metric(T("Kühllast Gebäude"), f"{de(last.cool)} kW", help=T("Rechenkern CALC-0.4, mit Gleichzeitigkeit"))

    # ------------------------------------------------------------ Alternativen
    andere = [k for k in moeglich if k is not gewaehlt]
    if andere:
        st.markdown("##### " + T("Alternativen"))
        spalten = st.columns(len(andere))
        for sp, k in zip(spalten, andere):
            with sp.container(border=True):
                pk = k.preis
                diff = (pk - preis) if (pk is not None and preis is not None) else None
                st.markdown(f"**{k.name}**" + ("  ·  " + T("Empfehlung") if k.empfohlen else ""))
                st.caption((T("{n} Außengerät", n=k.aussengeraete) if k.aussengeraete == 1
                            else T("{n} Außengeräte", n=k.aussengeraete)) + f" · {fmt_eur(pk)}"
                           + (f" ({'+' if diff >= 0 else '−'}{fmt_eur(abs(diff))})" if diff else ""))
                if st.button(T("Auswählen"), key=f"wahl_{k.key}", width="stretch"):
                    _ss().v2_konzept = k.key
                    _ss().v2_oben = True
                    st.rerun()

    st.markdown("##### " + T("Ihre Geräte"))
    sp = st.columns(2)
    for j, t in enumerate(gewaehlt.teilsysteme):
        with sp[j % 2]:
            _teilsystem_karte(t, p)

    # ------------------------------------------------------------ Details (eingeklappt)
    with st.expander(T("Stückliste mit Preisen"), icon=":material/receipt_long:"):
        st.dataframe(pdx.DataFrame([{
            T("Artikel"): x.name, T("Bestell-Nr."): x.artikel, T("Menge"): x.menge,
            T("Einzelpreis"): fmt_eur(x.einzelpreis), T("Summe"): fmt_eur(x.summe)} for x in gewaehlt.stueckliste()]),
            hide_index=True, width="stretch")
        st.markdown("**" + T("Summe Geräte: {s}", s=fmt_eur(preis)) + "**")
        st.caption(f"{T(kat.preisbasis)} · {T(kat.quelle)}")
    zubehoer_bereich(p, gewaehlt, kat)
    optional = A.optionale_leistungen(gewaehlt, kat)
    if optional:
        with st.expander(T("Optional: Inbetriebnahme durch den Bosch-Kundendienst"), icon=":material/build:"):
            st.dataframe(pdx.DataFrame([{
                T("Leistung"): T(x.name), T("Bestell-Nr."): x.artikel, T("Menge"): x.menge,
                T("Einzelpreis"): fmt_eur(x.einzelpreis), T("Summe"): fmt_eur(x.summe)} for x in optional]),
                hide_index=True, width="stretch")
            st.markdown(T("**Summe optional: {s}** – nicht im Gerätepreis enthalten.",
                          s=fmt_eur(gesamtpreis(optional))))
    with st.expander(T("Räume und Lasten"), icon=":material/thermostat:"):
        zeilen = []
        for b in A.bedarfe(p):
            zeilen.append({T("Raum"): f"{b.raum.geschoss} {b.raum.name}".strip(), T("Fläche m²"): b.raum.flaeche,
                           **({T("Personen"): b.raum.personen} if any(r.personen for r in p.raeume) else {}),
                           T("Kühllast kW"): round(b.kuehl, 2), T("Heizlast kW"): round(b.heiz, 2)})
        st.dataframe(pdx.DataFrame(zeilen), hide_index=True, width="stretch")
        st.caption(T("Gebäude gesamt: Kühlen {k} kW · Heizen {h} kW (Rechenkern CALC-0.4, in Anlehnung an "
                     "VDI 2078 / DIN EN 12831-1)", k=de(last.cool, 2), h=de(last.heat, 2)))
    hinweise = (gewaehlt.lieferhinweise + gewaehlt.hinweise + A.aufstellungshinweise(p, gewaehlt)
                + Z.tabelle(p, gewaehlt, kat)[1])
    if hinweise:
        with st.expander(T("Hinweise ({n})", n=len(hinweise)), icon=":material/info:"):
            for h in hinweise:
                st.markdown(f"- {h}")
    info = _ss().get("v2_ki_info")
    if info and info["aufstellorte"]:
        with st.expander(T("Mögliche Aufstellorte für Außengeräte"), icon=":material/location_on:"):
            for ort, grund in info["aufstellorte"]:
                st.markdown(f"- **{ort}** – {grund}")

    # ------------------------------------------------------------ Abschluss
    st.write("")
    with st.container(border=True):
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        with c1:
            ok = st.checkbox(T("Ich habe die Hinweise zur überschlägigen Auslegung gelesen."), key=_k("ack"))
            with st.popover(T("Hinweise anzeigen")):
                for h in P.HAFTUNGSHINWEISE:
                    st.markdown(f"- {T(h)}")
        with c2:
            if ok:
                _ss().setdefault("v2_ack_zeit", datetime.now().strftime("%d.%m.%Y %H:%M"))
                st.download_button(T("Angebotsübersicht (PDF)"), width="stretch", type="primary",
                                   icon=":material/picture_as_pdf:",
                                   data=pdf_angebot_v2(p, gewaehlt, kat, _ss().v2_ack_zeit),
                                   file_name=(f"Split_AC_Quote_{p.config_id}.pdf" if englisch()
                                              else f"Split_Klima_Angebot_{p.config_id}.pdf"),
                                   mime="application/pdf")
            else:
                st.button(T("Angebotsübersicht (PDF)"), width="stretch", disabled=True,
                          icon=":material/picture_as_pdf:", help=T("Bitte zuerst die Hinweise bestätigen."))
    c1, c2, _ = st.columns([1, 1, 2])
    if c1.button(T("Zurück"), icon=":material/arrow_back:", width="stretch"):
        gehe("raeume")
    with c2:
        planung_zuruecksetzen(p, "ende")


def _weiter_zurueck(zurueck: tuple[str, str] | None, weiter: tuple[str, str] | None, hier: str) -> None:
    st.write("")
    c1, c2, _ = st.container(key=f"wz-{hier}").columns([1, 1.6, 1])
    if zurueck and c1.button(T("Zurück"), icon=":material/arrow_back:", width="stretch", key=f"zur_{hier}"):
        gehe(zurueck[0])
    if weiter and c2.button(T(weiter[1]), type="primary", icon=":material/arrow_forward:", width="stretch",
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
        st.markdown(f'<div class="fortschritt">{T("Fortschritt {n} %", n=round(anteil * 100))}</div>',
                    unsafe_allow_html=True)
        st.progress(anteil)
        for key, titel, icon in SCHRITTE:
            aktiv = seite == key or (key == "raeume" and seite == "raum")
            haken = "  ✓" if key in erledigt else ""
            if st.button(f"{T(titel)}{haken}", key=f"nav-{key}", icon=icon, width="stretch",
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
            if sp.button(T(titel), key=f"mnav-{key}", width="stretch", type="primary" if aktiv else "secondary",
                         disabled=key == "ergebnis" and not p.raeume):
                gehe(key)
        with spalten[4].popover("", icon=":material/save:", width="stretch"):
            st.markdown("**" + T("Konfiguration") + "**")
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
            f'<div class="mp-info">{T("Kühllast {k} kW · {ag} AG / {ig} IG", k=de(last.cool, 2), ag=k.aussengeraete, ig=k.innengeraete)}</div>'
            f'</div><div class="mp-preis">{fmt_eur(k.preis)}</div></div>')


def konfiguration_speichern_laden(p: Projekt, mobil: bool = False) -> None:
    """Aktuelle Konfiguration als JSON herunterladen bzw. eine gespeicherte wieder laden."""
    auswahl = {"konzept": _ss().get("v2_konzept"), "seite": _ss().v2_seite, "raum": _ss().get("v2_raum", 0),
               "erledigt": sorted(_ss().v2_erledigt), "geprueft": sorted(_ss().v2_geprueft)}
    endung = "-m" if mobil else ""
    with st.container(border=not mobil):
        if not mobil:
            st.markdown("**" + T("Konfiguration") + "**")
        st.download_button(T("Speichern (JSON)"), SP.exportieren(p, auswahl), file_name=SP.dateiname(p),
                           mime="application/json", icon=":material/download:", width="stretch",
                           key=f"konfig-speichern{endung}")
        with st.popover(T("Laden"), icon=":material/upload:", width="stretch"):
            datei = st.file_uploader(T("Gespeicherte Konfiguration (.json)"), type=["json"], key=f"konfig-laden{endung}")
            if datei is not None and _ss().get("v2_geladen") != datei.file_id:
                _ss().v2_geladen = datei.file_id
                _ss().v2_import = datei.getvalue()
                st.rerun()
            if fehler := _ss().get("v2_import_fehler"):
                st.error(fehler)
            st.caption(T("Lädt Räume, Einstellungen, Gerätewünsche und Zubehörmengen. Die aktuelle Konfiguration "
                         "wird ersetzt – vorher speichern."))
        planung_zuruecksetzen(p, "m" if mobil else "nav")


def planung_zuruecksetzen(p: Projekt, ort: str) -> None:
    """„Neu beginnen“ mit Sicherheitsabfrage – löscht Räume, Einstellungen und Zubehörmengen."""
    with st.popover(T("Neu beginnen"), icon=":material/restart_alt:", width="stretch"):
        st.markdown("**" + T("Planung zurücksetzen?") + "**")
        st.caption(T("Alle Räume, Einstellungen, Gerätewünsche und Zubehörmengen werden gelöscht. "
                     "Wer die aktuelle Planung behalten möchte, speichert sie vorher als JSON."))
        if p.raeume:
            st.download_button(T("Vorher speichern (JSON)"), SP.exportieren(p), file_name=SP.dateiname(p),
                               mime="application/json", icon=":material/download:", width="stretch",
                               key=f"reset-speichern-{ort}")
        if st.button(T("Ja, alles zurücksetzen"), type="primary", icon=":material/delete_sweep:", width="stretch",
                     key=f"reset-ja-{ort}"):
            neues_projekt()
            _ss().v2_import_fehler = ""
            _ss().v2_toast = T("Neue Planung gestartet.")
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
        _ss().v2_import_fehler = T("Laden nicht möglich:") + f" {fehler}"
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
    _ss().v2_toast = T("Konfiguration „{name}“ geladen ({n} Räume).", name=projekt.name, n=n)


def zusammenfassung(p: Projekt, kat: Katalog) -> None:
    e = p.einstellungen
    with st.container(border=True, key="zusammenfassung"):
        st.markdown("**" + T("Ihre Konfiguration") + "**")
        gewaehlt = _gewaehlt(_konzepte(p, kat)) if p.raeume else None
        if gewaehlt:
            bilder = _konzept_bilder(gewaehlt, 2)
            if bilder:
                _bild_mittig(bilder[0], 260)
            st.markdown(f"**{gewaehlt.name}**")
            st.caption(gewaehlt.geraete_text)
            st.markdown(f'<div class="preis">{fmt_eur(gewaehlt.preis)}</div>', unsafe_allow_html=True)
            st.caption(T("Gerätepreis, UVP netto"))
        elif p.raeume:
            st.caption(T("Noch keine passende Gerätekombination – Räume oder Gerätewunsch anpassen."))
        else:
            st.markdown(f'<div style="color:{BLAU};text-align:center">{svg("haus", 72)}</div>',
                        unsafe_allow_html=True)
            st.caption(T("Sobald Räume erfasst sind, sehen Sie hier live den Vorschlag mit Preis."))

        zeilen = [("System", T(dict((v, t) for v, t, _ in SYSTEME)[p.systemwunsch])),
                  ("Betrieb", T(dict((v, t) for v, t, _ in BETRIEB)[e.betriebsart])),
                  *([("Gerätelinie", T(A.GERAETELINIEN[p.geraetelinie]))] if p.geraetelinie else []),
                  *([("Außeneinheit", T(A.AUFSTELLUNG[p.aufstellung]))] if p.aufstellung else []),
                  ("Standort", p.ort), ("Norm-Außentemp.", grad(e.norm_aussen)),
                  ("Baujahr", str(p.baujahr or "–"))]
        if p.raeume:
            last = gebaeude_last(p)
            zeilen += [("Räume", f"{len(p.raeume)} · {de(sum(r.flaeche for r in p.raeume))} m²"),
                       ("Kühllast", f"{de(last.cool, 2)} kW"), ("Heizlast", f"{de(last.heat, 2)} kW")]
        st.markdown("".join(f'<div class="zs-zeile"><span>{T(a)}</span><span>{b}</span></div>' for a, b in zeilen)
                    + '<div style="height:.6rem"></div>',
                    unsafe_allow_html=True)

        if _ss().v2_seite == "raum" and p.raeume:
            r = p.raeume[min(_ss().v2_raum, len(p.raeume) - 1)]
            l = raum_last(r, e)
            st.write("")
            st.markdown(f"**{r.name}** – " + T("live berechnet"))
            c1, c2 = st.columns(2)
            c1.metric(T("Kühllast"), f"{de(l.cool, 2)} kW")
            c2.metric(T("Heizlast"), f"{de(l.heat, 2)} kW")
            if gewaehlt:
                treffer = [(u, bool(t.set)) for t in gewaehlt.teilsysteme
                           for rr, u in ([(x, t.set) for x in t.raeume] if t.set else t.innen)
                           if u is not None and (rr is r or rr.name.startswith(f"{r.name} · Zone "))]
                if treffer:
                    u, ist_set = treffer[0]
                    if pf := (bild_innen_set(u) if ist_set else bild(u)):
                        _bild_mittig(pf, 220)
                    typen = list(dict.fromkeys(x.typ for x, _ in treffer))
                    st.caption(T("Vorschlag:") + " " + (T("{n} Geräte – ", n=len(treffer)) if len(treffer) > 1 else "")
                               + ", ".join(typen))


# ====================================================================== Sprache
def sprache_vorbereiten() -> None:
    """Sprache beim ersten Aufruf aus der Adresse übernehmen (``?lang=en``), sonst Deutsch."""
    if SITZUNG not in _ss():
        _ss()[SITZUNG] = "en" if st.query_params.get("lang", "").lower().startswith("en") else "de"


def _sprache_gewechselt() -> None:
    wahl = _ss().get("v2_sprachwahl")
    if not wahl:  # erneuter Klick auf die aktive Sprache hebt die Auswahl auf – Sprache bleibt
        return
    neu = "en" if "EN" in wahl else "de"
    _ss()[SITZUNG] = neu
    if neu == "en":
        st.query_params["lang"] = "en"
    else:
        st.query_params.pop("lang", None)


def sprache_umschalter() -> None:
    """Umschalter DE | EN oben rechts. Fachlich bleibt alles deutsch (PLZ, Orte, Normen, Katalog, Euro)."""
    sprache_vorbereiten()
    optionen = ["🇩🇪 DE", "🇬🇧 EN"]
    _ss()["v2_sprachwahl"] = optionen[1] if _ss()[SITZUNG] == "en" else optionen[0]
    st.segmented_control("Sprache / Language", optionen, key="v2_sprachwahl", on_change=_sprache_gewechselt,
                         label_visibility="collapsed", width="stretch")


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

    kat_voll = kat
    if not p.auslaufartikel:  # Standard: nur Artikel des aktuellen Katalogs 09/2026
        kat = kat.ohne_auslauf()
    links, mitte, rechts = st.columns([1.05, 3, 1.35], gap="medium")
    seite = _ss().v2_seite
    with mitte:
        mobil_navigation(p)
        if seite == "system":
            seite_system(p, kat_voll)
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
    st.markdown(f'<div class="entwickler">{T(ENTWICKLER)}</div>', unsafe_allow_html=True)
    if ASSISTENT_AKTIV:
        planungs_assistent(p, kat)
