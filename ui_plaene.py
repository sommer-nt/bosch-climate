"""Seite „Pläne & Anlagenvorschlag“: Architektenpläne → Räume → infrage kommende Anlagen."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
import streamlit as st

from splitklima import parameter as P
from splitklima.anlagenvorschlag import anlagenkonzepte
from splitklima.auswahl import ig_gewaehlt, ig_status
from splitklima.berechnung import raum_last
from splitklima.ki_plan import (
    KEIN_SCHLUESSEL, KiPlanAnalyse, PlanFehler, analysiere, baualter_aus_baujahr, in_raeume,
    schluessel_vorhanden,
)
from splitklima.modell import Projekt, Raum
from splitklima.produkte import Produktdaten

MIME = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp"}
MAX_MB = 30  # Anfragegrenze der Claude API: 32 MB
BEISPIEL = Path(__file__).parent / "splitklima" / "daten" / "beispiel_planerkennung.json"
STATUSFARBE = {"ok": "🟢", "warn": "🟡", "orange": "🟠", "bad": "🔴", "err": "🔴"}


def _neues_ergebnis(analyse: KiPlanAnalyse) -> None:
    st.session_state.ki_analyse = analyse
    st.session_state.ki_version = st.session_state.get("ki_version", 0) + 1


def seite_plaene(p: Projekt, prod: Produktdaten, uebernehmen: Callable[[list[Raum], str], None]) -> None:
    # ------------------------------------------------------------ 1. Hochladen
    st.subheader("① Architektenpläne und Grundrisse hochladen")
    links, rechts = st.columns([3, 2])
    with links:
        dateien = st.file_uploader(
            "Grundrisse aller Geschosse, Schnitte, Ansichten, Lageplan (PDF, PNG, JPG)",
            type=["pdf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True, key="plan_upload")
        zusatz = st.text_area(
            "Zusatzangaben für die KI (optional)",
            placeholder="z. B. 'Plan-Oben zeigt nach Nordost', 'Baujahr 1975, Fenster 2010 erneuert', "
                        "'Keller nicht klimatisieren', 'Fensterhöhe überall 1,40 m'")
    with rechts:
        groesse = sum(len(f.getvalue()) for f in dateien or []) / 1e6
        if dateien:
            st.caption(f"{len(dateien)} Datei(en) · {groesse:.1f} MB")
        zu_gross = groesse > MAX_MB
        if zu_gross:
            st.error(f"Zusammen größer als {MAX_MB} MB – bitte Geschosse einzeln hochladen oder Auflösung reduzieren.")
        if st.button("🔍 Pläne mit KI analysieren", type="primary", width="stretch",
                     disabled=not dateien or zu_gross):
            with st.spinner("Claude liest die Pläne … (je nach Umfang 1–3 Minuten)"):
                try:
                    _neues_ergebnis(analysiere(
                        [(f.getvalue(), MIME[Path(f.name).suffix.lower()]) for f in dateien], zusatz))
                except PlanFehler as e:
                    st.error(str(e))
        if st.button("Beispielergebnis laden (ohne KI)", width="stretch",
                     help="Zeigt den Ablauf mit einem Beispiel-Einfamilienhaus, ohne API-Schlüssel."):
            _neues_ergebnis(KiPlanAnalyse.model_validate_json(BEISPIEL.read_text("utf-8")))
        if schluessel_vorhanden():
            st.caption("✅ API-Schlüssel gefunden. Pläne werden zur Auswertung an die Claude API übertragen.")
        else:
            st.warning(KEIN_SCHLUESSEL, icon="🔑")
    bilder = [f for f in dateien or [] if not f.name.lower().endswith(".pdf")]
    if bilder:
        with st.expander("Vorschau"):
            st.image([f.getvalue() for f in bilder], caption=[f.name for f in bilder], width=320)

    analyse: KiPlanAnalyse | None = st.session_state.get("ki_analyse")
    if analyse is None:
        st.info("Nach der Analyse erscheinen hier die erkannten Räume und die infrage kommenden Anlagen. "
                "Ohne Pläne kannst du direkt unter „② Konfiguration“ Räume manuell eingeben.")
        return

    # ------------------------------------------------------------ 2. Räume prüfen
    st.subheader("② Erkannte Räume prüfen")
    st.caption(f"Nordrichtung: {analyse.nordrichtung}")
    for h in analyse.hinweise:
        st.warning(h, icon="⚠️")

    erkannt = in_raeume(analyse)
    ver = st.session_state.get("ki_version", 0)
    tabelle = pd.DataFrame([{
        "klimatisieren": True, "geschoss": r.geschoss, "name": r.name, "raumart": r.raumart, "flaeche": r.flaeche,
        "hoehe": r.hoehe, "lage": P.MODE_LABEL[r.lage],
        "waende": ", ".join(f"{w.ausrichtung} {w.laenge:g} m ({w.fenster:g} m² Fenster)" for w in r.waende) or "–",
        "dachfenster": sum(g.flaeche for g in r.fenstergruppen if g.dachfenster),
    } for r in erkannt])
    bearbeitet = st.data_editor(
        tabelle, hide_index=True, width="stretch", num_rows="fixed", key=f"ki_tabelle{ver}",
        disabled=["lage", "waende", "dachfenster"],
        column_config={
            "klimatisieren": st.column_config.CheckboxColumn("❄️", help="Raum klimatisieren?"),
            "geschoss": st.column_config.TextColumn("Geschoss"),
            "name": st.column_config.TextColumn("Raum"),
            "raumart": st.column_config.SelectboxColumn("Raumart", options=P.RAUMARTEN, required=True),
            "flaeche": st.column_config.NumberColumn("Fläche m²", min_value=0.0, format="%.1f"),
            "hoehe": st.column_config.NumberColumn("Höhe m", min_value=1.8, format="%.2f"),
            "lage": st.column_config.TextColumn("Thermische Lage"),
            "waende": st.column_config.TextColumn("Außenwände", width="large"),
            "dachfenster": st.column_config.NumberColumn("Dachfenster m²", format="%.1f"),
        })
    st.caption("Wände, Fenster und Lage lassen sich nach der Übernahme im Konfigurator je Raum feinjustieren.")

    c1, c2 = st.columns([1, 2])
    baujahr = c1.number_input("Baujahr (0 = unbekannt)", 0, 2100, int(analyse.baujahr or 0), key=f"ki_bj{ver}")
    klasse = baualter_aus_baujahr(baujahr)
    baualter_setzen = c2.checkbox(
        f"Baualtersklasse „{P.AGE_CLASSES[klasse]['label']}“ für alle Räume verwenden" if klasse
        else "Baualtersklasse aus Baujahr ableiten", value=bool(klasse), disabled=not klasse, key=f"ki_bjset{ver}")

    raeume: list[Raum] = []
    for r, z in zip(erkannt, bearbeitet.to_dict("records")):
        if not z["klimatisieren"]:
            continue
        neu = r.model_copy(deep=True)
        neu.geschoss = (z["geschoss"] or "").strip().upper()
        neu.name = z["name"] or r.name
        neu.raumart = z["raumart"] or r.raumart
        neu.flaeche = float(z["flaeche"] or 0)
        neu.hoehe = float(z["hoehe"] or 2.5)
        if baualter_setzen and klasse:
            neu.baualter = klasse
        raeume.append(neu)
    if not raeume:
        st.info("Keine Räume zum Klimatisieren ausgewählt.")
        return

    # ------------------------------------------------------------ 3. Anlagenvorschlag
    st.subheader("③ Infrage kommende Anlagen")
    st.caption("Berechnet mit den Gebäude- und Klimaeinstellungen aus der Seitenleiste "
               f"({P.USTD_LABEL[p.einstellungen.daemmstandard]}, {P.GLAS_LABEL[p.einstellungen.verglasung]}, "
               f"Sonnenschutz {P.SONNENSCHUTZ_LABEL[p.einstellungen.sonnenschutz]}, "
               f"{p.einstellungen.sommer:g} / {p.einstellungen.norm_aussen:g} °C).")
    basis = p.model_copy(deep=True)
    basis.raeume = raeume
    basis.gewaehltes_system = None
    basis.validierungsfall = ""

    zeilen = []
    lasten = [raum_last(r, basis.einstellungen) for r in raeume]
    for r, l in zip(raeume, lasten):
        u = ig_gewaehlt(r, basis, prod)
        s = ig_status(r, u, basis)
        zeilen.append({"Geschoss": r.geschoss, "Raum": r.name, "Kühllast kW": round(l.cool, 2),
                       "Heizlast kW": round(l.heat, 2), "W/m² Kühlen": round(l.cool * 1000 / (r.flaeche or 1)),
                       "Inneneinheit": f"{u.name} ({u.type})" if u else "–", "Status": f"{STATUSFARBE[s.cls]} {s.txt}"})
    m = st.columns(3)
    m[0].metric("Räume", len(raeume))
    m[1].metric("Kühllast (Summe Räume)", f"{sum(l.cool for l in lasten):.2f} kW")
    m[2].metric("Heizlast (Summe Räume)", f"{sum(l.heat for l in lasten):.2f} kW")
    st.markdown("**Inneneinheiten je Raum**")
    st.dataframe(pd.DataFrame(zeilen), hide_index=True, width="stretch")

    konzepte = anlagenkonzepte(basis, prod)
    st.caption("⭐ Empfehlung: vollständige Deckung mit den wenigsten Außengeräten, bei Gleichstand die geringere "
               "Leistungsreserve. Alle Konzepte sind technisch möglich, sofern keine Fehlermeldung erscheint.")
    for kz in konzepte:
        with st.container(border=True):
            kopf = f"### {'⭐ ' if kz.empfohlen else ''}{kz.name}" + (" – Empfehlung" if kz.empfohlen else "")
            st.markdown(kopf)
            st.caption(kz.beschreibung)
            if not kz.gedeckt:
                st.error("Nicht für alle Räume eine passende Außengerätelösung im Sortiment.")
            c = st.columns(3)
            c[0].metric("Außengeräte", kz.aussengeraete if kz.gedeckt else "–")
            c[1].metric("Inneneinheiten", len(raeume))
            c[2].metric("Lautestes Außengerät", f"{kz.schall_max:g} dB(A)" if kz.schall_max else "–")
            st.dataframe(pd.DataFrame([{
                "System": t.bezeichnung,
                "Räume": ", ".join(r.name for r in t.raeume),
                "Außengerät(e)": t.kombination.label if t.kombination else "keine passende Lösung",
                "Kühlen Last / Gerät": f"{t.last_kuehlen:.2f} / {t.kombination.t.cool:.1f} kW" if t.kombination
                else f"{t.last_kuehlen:.2f} kW",
                "Deckung K / H": f"{t.deckung_kuehlen:.0f} % / {t.deckung_heizen:.0f} %" if t.kombination else "–",
                "Anschlüsse": f"{len(t.raeume)}/{t.kombination.t.ports}" if t.kombination else "–",
                "Schall außen": f"{t.schall_max:g} dB(A)" if t.schall_max else "–",
            } for t in kz.teilsysteme]), hide_index=True, width="stretch")
            if kz.key == "multi_gesamt":
                if st.button("Alle Räume in den Konfigurator übernehmen", key=f"ueb_{kz.key}{ver}",
                             type="primary" if kz.empfohlen else "secondary"):
                    uebernehmen(raeume, "auto")
            else:
                with st.expander("Teilsystem im Konfigurator ausarbeiten (inkl. PDF-Bericht)"):
                    for i, t in enumerate(kz.teilsysteme):
                        if st.button(f"{t.bezeichnung}: {', '.join(r.name for r in t.raeume)}",
                                     key=f"ueb_{kz.key}{i}{ver}", disabled=not t.gedeckt):
                            uebernehmen(t.raeume, "single" if len(t.raeume) == 1 else "auto")

    if analyse.aufstellorte_aussengeraet:
        st.markdown("**Mögliche Aufstellorte für Außengeräte (aus dem Plan)**")
        for a in analyse.aufstellorte_aussengeraet:
            st.markdown(f"- **{a.ort}** – {a.begruendung}")
    st.caption("Vorschlag auf Basis der Nennleistungen. Schall, Leitungslängen, Kondensat, Elektro und "
               "Aufstellanforderungen sind projektbezogen zu prüfen.")
