"""Geführter Assistent: ① Projekt → ② Räume → ③ Ergebnis.

Bewusst schlank: wenige Fragen, klare Schritte, am Ende ein wirtschaftlicher
Vorschlag mit Preis. Gerechnet wird mit dem unveränderten Rechenkern.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

import pandas as pdx
import streamlit as st
import streamlit.components.v1 as components

from splitklima import parameter as P
from splitklima.anlagenvorschlag import Konzept, anlagenkonzepte
from splitklima.auswahl import ig_gewaehlt, ig_status
from splitklima.berechnung import raum_last
from splitklima.bericht import pdf_angebot
from splitklima.ki_plan import (
    KiPlanAnalyse, PlanFehler, analysiere, baualter_aus_baujahr, in_raeume, schluessel_vorhanden,
)
from splitklima.modell import Fenstergruppe, Projekt, Raum, Wand
from splitklima.preise import Preisliste, fmt_eur
from splitklima.produkte import Produktdaten
from splitklima.standort import finde_ort, klimaregion

SCHRITTE = {1: "Projekt", 2: "Räume", 3: "Ergebnis"}
MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp"}
MAX_MB = 30
BEISPIEL = Path(__file__).parent / "splitklima" / "daten" / "beispiel_planerkennung.json"
SONNENSCHUTZ = {"0.45": "Rollläden / Außenjalousien", "0.8": "Innen (Vorhang, Plissee)", "1": "Keiner"}
VERGLASUNG = {"double": "Zweifach", "triple": "Dreifach", "single": "Einfach"}
SYSTEM = {"auto": "Beste Lösung finden", "multi": "Multi-Split", "single": "Single-Split"}
LAGE_KURZ = {
    "outside": "1 Außenwand", "corner": "Eckraum (2 Außenwände)", "three": "3 Außenwände",
    "attic": "Dachgeschoss", "attic_corner": "Dachgeschoss, Eckraum", "inside": "Innenliegend",
    "basement": "Über Keller",
}


def de(x: float, nachkomma: int = 1) -> str:
    """Zahl in deutscher Schreibweise (Komma), ohne überflüssige Nullen bei ganzen Zahlen."""
    if float(x).is_integer() and nachkomma <= 1:
        return f"{x:.0f}"
    return f"{x:.{nachkomma}f}".replace(".", ",")


def _gehe(schritt: int) -> None:
    st.session_state.schritt = schritt
    st.session_state.nach_oben = True
    st.rerun()


def _nach_oben() -> None:
    """Nach einem Schrittwechsel an den Seitenanfang springen."""
    if st.session_state.pop("nach_oben", False):
        components.html(
            "<script>for (const s of ['[data-testid=\"stMain\"]', '[data-testid=\"stAppViewContainer\"]',"
            " 'section.main']) { const el = window.parent.document.querySelector(s); if (el) el.scrollTo(0, 0); }"
            " window.parent.scrollTo(0, 0);</script>", height=0)


def _daemmstandard(baujahr: int) -> str:
    return "old" if baujahr < 1979 else "mid" if baujahr < 2002 else "new"


def baujahr_anwenden(p: Projekt) -> None:
    """Baujahr → Dämmstandard und Baualtersklasse aller Räume."""
    if not p.baujahr:
        return
    p.einstellungen.daemmstandard = _daemmstandard(p.baujahr)
    klasse = baualter_aus_baujahr(p.baujahr)
    for r in p.raeume:
        r.baualter = klasse


def _stepper(schritt: int, p: Projekt) -> None:
    spalten = st.columns(len(SCHRITTE))
    for (nr, titel), sp in zip(SCHRITTE.items(), spalten):
        zeichen = "✓" if nr < schritt else str(nr)
        if sp.button(f"{zeichen}  {titel}", key=f"stepper{nr}", width="stretch",
                     type="primary" if nr == schritt else "secondary", disabled=nr == 3 and not p.raeume):
            _gehe(nr)


# ====================================================================== Schritt 1
def _schritt_projekt(p: Projekt, k: Callable[[str], str]) -> None:
    e = p.einstellungen
    st.markdown("#### Wo und was soll klimatisiert werden?")
    c1, c2 = st.columns(2)
    p.name = c1.text_input("Projektname", p.name, key=k("a_name"))
    ort = c2.text_input("PLZ oder Ort", p.ort, key=k("a_ort"))
    treffer = finde_ort(ort)
    if ort != p.ort:
        p.ort = f"{treffer[0]} {treffer[1]}" if treffer else ort
        if treffer:
            p.plz = treffer[0]
            if not p.expertenmodus:
                kr = klimaregion(p.plz)
                e.norm_aussen, e.sommer = kr.norm_aussen, kr.sommer
    kr = klimaregion(p.plz)
    c2.caption(f"Klima: {kr.name} · Sommer {de(e.sommer)} °C · Winter {de(e.norm_aussen)} °C")

    c1, c2 = st.columns(2)
    with c1:
        e.betriebsart = st.radio("Die Anlage soll …", ["both", "cool"], ["both", "cool"].index(
            e.betriebsart if e.betriebsart in ("both", "cool") else "both"),
            format_func={"both": "kühlen und heizen", "cool": "nur kühlen"}.get, horizontal=True, key=k("a_ba"))
    with c2:
        p.systemwunsch = st.radio("Gewünschtes System", list(SYSTEM), list(SYSTEM).index(p.systemwunsch),
                                  format_func=SYSTEM.get, horizontal=True, key=k("a_sys"),
                                  help="„Beste Lösung finden“ vergleicht Single- und Multi-Split und empfiehlt "
                                       "die wirtschaftlichste.")

    st.markdown("#### Das Gebäude")
    c1, c2, c3 = st.columns(3)
    bj = c1.number_input("Baujahr", 1850, datetime.now().year, int(p.baujahr or 1990), step=1, key=k("a_bj"))
    if p.baujahr is None:  # Erstaufruf: Vorschlagswert übernehmen
        p.baujahr = int(bj)
        baujahr_anwenden(p)
    elif bj != p.baujahr:
        p.baujahr = int(bj)
        st.session_state.baujahr_manuell = True
        baujahr_anwenden(p)
    e.verglasung = c2.selectbox("Fenster", list(VERGLASUNG), list(VERGLASUNG).index(e.verglasung),
                                format_func=lambda v: f"{VERGLASUNG[v]}verglasung", key=k("a_glas"))
    if e.sonnenschutz == "0.55":  # „Jalousie außen“ aus der Expertenansicht zählt als außenliegend
        e.sonnenschutz = "0.45"
    e.sonnenschutz = c3.selectbox("Sonnenschutz", list(SONNENSCHUTZ), list(SONNENSCHUTZ).index(e.sonnenschutz),
                                  format_func=SONNENSCHUTZ.get, key=k("a_shade"))

    st.write("")
    if st.button("Weiter zu den Räumen  →", type="primary"):
        baujahr_anwenden(p)
        _gehe(2)


# ====================================================================== Schritt 2
def _ki_bereich(p: Projekt, neu_laden: Callable[[Projekt], None]) -> None:
    with st.container(border=True):
        st.markdown("**Grundrisse hochladen – die Räume werden automatisch erkannt**")
        dateien = st.file_uploader("Pläne", type=["pdf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True,
                                   label_visibility="collapsed", key="a_upload")
        ki_bereit = schluessel_vorhanden()
        c1, c2, c3 = st.columns([2, 2, 3])
        with c3.popover("Zusatzangaben", width="stretch"):
            zusatz = st.text_area("Hinweise für die Erkennung", key="a_zusatz",
                                  placeholder="z. B. Plan-Oben zeigt nach Nordost; Keller nicht klimatisieren")
        groesse = sum(len(f.getvalue()) for f in dateien or []) / 1e6
        if c1.button("Räume erkennen", type="primary", width="stretch",
                     disabled=not dateien or not ki_bereit or groesse > MAX_MB):
            with st.spinner("Die Pläne werden gelesen … das dauert 1–2 Minuten."):
                try:
                    _ki_uebernehmen(p, analysiere(
                        [(f.getvalue(), MIME[Path(f.name).suffix.lower()]) for f in dateien], zusatz), neu_laden)
                except PlanFehler as fehler:
                    st.error(str(fehler))
        if c2.button("Beispielhaus laden", width="stretch"):
            _ki_uebernehmen(p, KiPlanAnalyse.model_validate_json(BEISPIEL.read_text("utf-8")), neu_laden)
        if groesse > MAX_MB:
            st.error(f"Zusammen {groesse:.0f} MB – bitte höchstens {MAX_MB} MB bzw. Geschosse einzeln hochladen.")
        elif not ki_bereit:
            st.caption("Automatische Erkennung ist nicht eingerichtet (API-Schlüssel fehlt). "
                       "Räume einfach unten anlegen.")
        else:
            st.caption("PDF, PNG oder JPG · alle Geschosse auf einmal möglich · die Pläne werden zur Auswertung "
                       "an die Claude API übertragen.")


def _ki_uebernehmen(p: Projekt, analyse: KiPlanAnalyse, neu_laden: Callable[[Projekt], None]) -> None:
    p.raeume = in_raeume(analyse) or p.raeume
    if analyse.baujahr and not st.session_state.get("baujahr_manuell"):
        p.baujahr = analyse.baujahr
    baujahr_anwenden(p)
    p.validierungsfall = ""
    st.session_state.ki_info = {
        "hinweise": [f"Nordrichtung: {analyse.nordrichtung}", *analyse.hinweise],
        "aufstellorte": [(a.ort, a.begruendung) for a in analyse.aufstellorte_aussengeraet],
    }
    st.session_state.ki_toast = f"{len(p.raeume)} Räume erkannt – bitte kurz prüfen."
    neu_laden(p)
    st.session_state.schritt = 2
    st.session_state.nach_oben = True
    st.rerun()


def _raum_label(r: Raum, p: Projekt, pd: Produktdaten) -> str:
    l = raum_last(r, p.einstellungen)
    u = ig_gewaehlt(r, p, pd)
    zeichen = {"ok": "✅", "warn": "✅", "orange": "✅", "bad": "⚠️"}[ig_status(r, u, p).cls]
    geschoss = f"{r.geschoss} · " if r.geschoss else ""
    return f"{zeichen} {geschoss}{r.name} — {de(r.flaeche)} m² · Kühlbedarf {de(l.cool)} kW"


def _raum_bearbeiten(i: int, r: Raum, p: Projekt, k: Callable[[str], str]) -> None:
    c = st.columns([3, 1, 2, 1, 1])
    r.name = c[0].text_input("Raum", r.name, key=k(f"a_rn{i}"))
    r.geschoss = c[1].text_input("Geschoss", r.geschoss, key=k(f"a_rg{i}"), placeholder="EG")
    r.raumart = c[2].selectbox("Nutzung", P.RAUMARTEN, P.RAUMARTEN.index(r.raumart), key=k(f"a_ra{i}"))
    r.flaeche = c[3].number_input("Fläche m²", 1.0, 500.0, float(r.flaeche or 1), 0.5, key=k(f"a_rf{i}"))
    r.hoehe = c[4].number_input("Höhe m", 1.8, 6.0, float(r.hoehe or 2.5), 0.05, key=k(f"a_rh{i}"))

    c1, c2 = st.columns([1, 3])
    lage = c1.selectbox("Lage", list(LAGE_KURZ), list(LAGE_KURZ).index(r.lage), format_func=LAGE_KURZ.get,
                        key=k(f"a_rl{i}"))
    if lage != r.lage:
        r.setze_lage(lage)
        st.session_state.rev += 1
        st.rerun()
    with c2:
        if r.waende:
            wdf = st.data_editor(
                pdx.DataFrame([w.model_dump() for w in r.waende]), hide_index=True, width="stretch",
                num_rows="fixed", key=k(f"a_rw{i}"),
                column_config={
                    "ausrichtung": st.column_config.SelectboxColumn("Außenwand zeigt nach", options=P.AUSRICHTUNGEN,
                                                                    required=True),
                    "laenge": st.column_config.NumberColumn("Wandlänge m", min_value=0.0, step=0.1, required=True),
                    "fenster": st.column_config.NumberColumn("Fensterfläche m²", min_value=0.0, step=0.1,
                                                             required=True),
                })
            r.waende = [Wand(**z) for z in wdf.to_dict("records")]
        else:
            st.caption("Innenliegender Raum – keine Außenwände.")
    if r.dach:
        df = sum(g.flaeche for g in r.fenstergruppen if g.dachfenster)
        neu = st.number_input("Dachfenster m²", 0.0, 50.0, float(df), 0.1, key=k(f"a_rdf{i}"))
        if neu != df:
            r.fenstergruppen = [g for g in r.fenstergruppen if not g.dachfenster]
            if neu > 0:
                r.fenstergruppen.append(Fenstergruppe(ausrichtung="S", flaeche=neu, dachfenster=True))


def _schritt_raeume(p: Projekt, pd: Produktdaten, k: Callable[[str], str],
                    neu_laden: Callable[[Projekt], None]) -> None:
    if msg := st.session_state.pop("ki_toast", None):
        st.toast(msg, icon="✅")
    _ki_bereich(p, neu_laden)

    info = st.session_state.get("ki_info")
    kopf_l, kopf_r = st.columns([3, 2])
    kopf_l.markdown(f"#### Räume ({len(p.raeume)})")
    if info and info["hinweise"]:
        with kopf_r.popover(f"ℹ️ Hinweise zur Erkennung ({len(info['hinweise'])})", width="stretch"):
            for h in info["hinweise"]:
                st.markdown(f"- {h}")

    for i, r in enumerate(p.raeume):
        with st.expander(_raum_label(r, p, pd), expanded=len(p.raeume) == 1):
            _raum_bearbeiten(i, r, p, k)
            if len(p.raeume) > 1 and st.button("Raum entfernen", key=k(f"a_del{i}")):
                p.raeume.pop(i)
                st.session_state.rev += 1
                st.rerun()

    if st.button("+ Raum hinzufügen"):
        neu = Raum(name=f"Raum {len(p.raeume) + 1}", lage="outside",
                   waende=[Wand(ausrichtung="S", laenge=4, fenster=2)],
                   geschoss=p.raeume[-1].geschoss if p.raeume else "")
        neu.baualter = baualter_aus_baujahr(p.baujahr) if p.baujahr else ""
        p.raeume.append(neu)
        st.session_state.rev += 1
        st.rerun()

    st.write("")
    c1, c2, _ = st.columns([1, 2, 3])
    if c1.button("←  Zurück"):
        _gehe(1)
    if c2.button("Ergebnis anzeigen  →", type="primary", disabled=not p.raeume):
        _gehe(3)


# ====================================================================== Schritt 3
def _konzept_kurz(kz: Konzept) -> str:
    n_aussen = kz.aussengeraete
    return f"{n_aussen} Außengerät{'e' if n_aussen != 1 else ''}"


def _schritt_ergebnis(p: Projekt, pd: Produktdaten, preise: Preisliste, k: Callable[[str], str],
                      zur_expertenansicht: Callable[[], None], neu_starten: Callable[[], None]) -> None:
    konzepte = anlagenkonzepte(p, pd, preise, p.systemwunsch)
    moeglich = [kz for kz in konzepte if kz.gedeckt]
    if not moeglich:
        st.error("Für diese Räume gibt es mit dem gewählten System keine passende Lösung im Sortiment. "
                 "Bitte ein anderes System wählen oder große Räume aufteilen.")
        if st.button("←  Zurück zu den Räumen"):
            _gehe(2)
        return

    empfohlen = next((kz for kz in moeglich if kz.empfohlen), moeglich[0])
    gewaehlt_key = st.session_state.get("konzept_wahl", empfohlen.key)
    gewaehlt = next((kz for kz in moeglich if kz.key == gewaehlt_key), empfohlen)
    preis = gewaehlt.preis(pd, preise)
    lasten = [raum_last(r, p.einstellungen) for r in p.raeume]
    bedarf = sum(l.cool for l in lasten)
    leistung = sum(t.kombination.t.cool for t in gewaehlt.teilsysteme if t.kombination)

    # ---------------------------------------------------------- Ergebnis-Karte
    with st.container(border=True):
        c1, c2 = st.columns([3, 2])
        with c1:
            st.caption("⭐ UNSERE EMPFEHLUNG" if gewaehlt is empfohlen else "IHRE AUSWAHL")
            st.markdown(f"## {gewaehlt.name}")
            st.markdown(f"{gewaehlt.geraete_text}")
            grund = ("Wirtschaftlichste Lösung, die alle Räume abdeckt." if gewaehlt is empfohlen
                     else f"Empfohlen wäre: {empfohlen.name}.")
            st.caption(grund)
            if not gewaehlt.vollstaendig(pd):
                st.caption("⚠️ Für mindestens einen Raum gibt es keine passende Inneneinheit – siehe Details.")
        with c2:
            st.metric("Gerätepreis", fmt_eur(preis))
            st.caption(preise.preisbasis if preise.freigegeben
                       else "Richtpreis aus Platzhalter-Preisliste – noch nicht freigegeben.")
        m = st.columns(3)
        m[0].metric("Außengeräte", gewaehlt.aussengeraete)
        m[1].metric("Innengeräte", len(p.raeume))
        m[2].metric("Kühlleistung", f"{de(leistung)} kW")
        m[2].caption(f"Bedarf der Räume: {de(bedarf)} kW")

    # ---------------------------------------------------------- Alternativen
    andere = [kz for kz in moeglich if kz is not gewaehlt]
    if andere:
        st.markdown("##### Alternativen")
        spalten = st.columns(len(andere))
        for sp, kz in zip(spalten, andere):
            with sp, st.container(border=True):
                pk = kz.preis(pd, preise)
                diff = (pk - preis) if (pk is not None and preis is not None) else None
                st.markdown(f"**{kz.name}**" + ("  ⭐" if kz.empfohlen else ""))
                st.caption(f"{_konzept_kurz(kz)} · {fmt_eur(pk)}"
                           + (f" ({'+' if diff >= 0 else '−'}{fmt_eur(abs(diff))})" if diff else ""))
                if st.button("Auswählen", key=f"wahl_{kz.key}", width="stretch"):
                    st.session_state.konzept_wahl = kz.key
                    st.session_state.nach_oben = True
                    st.rerun()

    # ---------------------------------------------------------- Details (eingeklappt)
    with st.expander("Stückliste"):
        liste = gewaehlt.stueckliste(pd, preise)
        st.dataframe(pdx.DataFrame([{
            "Artikel": x.name, "Art.-Nr.": x.artikel, "Menge": x.menge, "Einzelpreis": fmt_eur(x.einzelpreis),
            "Summe": fmt_eur(x.summe)} for x in liste]), hide_index=True, width="stretch")
        st.markdown(f"**Summe: {fmt_eur(preis)}**")
    with st.expander("Räume und Geräte"):
        zeilen = []
        for t in gewaehlt.teilsysteme:
            for r in (t.projekt.raeume if t.projekt else t.raeume):
                l = raum_last(r, p.einstellungen)
                u = ig_gewaehlt(r, t.projekt or p, pd)
                zeilen.append({"System": t.bezeichnung, "Raum": f"{r.geschoss} {r.name}".strip(),
                               "Fläche m²": r.flaeche, "Kühlen kW": round(l.cool, 2), "Heizen kW": round(l.heat, 2),
                               "Inneneinheit": u.name if u else "– keine passende –",
                               "Außengerät": t.kombination.label if t.kombination else "–"})
        st.dataframe(pdx.DataFrame(zeilen), hide_index=True, width="stretch")
    info = st.session_state.get("ki_info")
    if info and info["aufstellorte"]:
        with st.expander("Mögliche Aufstellorte für Außengeräte"):
            for ort, grund in info["aufstellorte"]:
                st.markdown(f"- **{ort}** – {grund}")

    # ---------------------------------------------------------- Abschluss
    st.write("")
    with st.container(border=True):
        c1, c2 = st.columns([3, 2])
        with c1:
            ok = st.checkbox("Ich habe die Hinweise zur überschlägigen Auslegung gelesen.", key=k("a_ack"))
            with st.popover("Hinweise anzeigen"):
                for h in P.HAFTUNGSHINWEISE:
                    st.markdown(f"- {h}")
        with c2:
            if ok:
                st.session_state.setdefault(k("a_ack_zeit"), datetime.now().strftime("%d.%m.%Y %H:%M"))
                st.download_button("📄 Angebotsübersicht (PDF)", width="stretch", type="primary",
                                   data=pdf_angebot(p, gewaehlt, pd, preise, st.session_state[k("a_ack_zeit")]),
                                   file_name=f"Split_Klima_Vorschlag_{p.config_id}.pdf", mime="application/pdf")
            else:
                st.button("📄 Angebotsübersicht (PDF)", width="stretch", disabled=True,
                          help="Bitte zuerst die Hinweise bestätigen.")

    c1, c2, c3, _ = st.columns([1, 2, 2, 2])
    if c1.button("←  Räume"):
        _gehe(2)
    if c2.button("Details in der Expertenansicht"):
        zur_expertenansicht()
    if c3.button("Neues Projekt"):
        neu_starten()


# ====================================================================== Einstieg
def assistent(p: Projekt, pd: Produktdaten, preise: Preisliste, k: Callable[[str], str],
              neu_laden: Callable[[Projekt], None], zur_expertenansicht: Callable[[], None],
              neu_starten: Callable[[], None]) -> None:
    schritt = st.session_state.setdefault("schritt", 1)
    _nach_oben()
    _stepper(schritt, p)
    st.write("")
    if schritt == 1:
        _schritt_projekt(p, k)
    elif schritt == 2:
        _schritt_raeume(p, pd, k, neu_laden)
    else:
        _schritt_ergebnis(p, pd, preise, k, zur_expertenansicht, neu_starten)
