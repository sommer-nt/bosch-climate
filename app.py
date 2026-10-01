"""BOSCH Climate Split-Klima-Konfigurator – Python/Streamlit-Version von v6.9.1.

Start:  streamlit run app.py
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from splitklima import parameter as P
from splitklima.auswahl import ig_gewaehlt, ig_status, produkt_modus, raum_zuordnung
from splitklima.berechnung import raum_last
from splitklima.bewertung import (
    VALIDIERUNGSFAELLE, ZUBEHOER_KATEGORIEN, datenqualitaet, deckung_text, fmt_bereich, gesamtstatus,
    heizanwendung, schall_uebersicht, validiere, wende_validierungsfall_an, zubehoer,
)
from splitklima.bericht import pdf_bericht
from splitklima.export import (
    auswerten, berechnungsparameter, produktdaten, projektstand, pruefdaten_text, raum_annahmen,
    validierungs_snapshot,
)
from splitklima.modell import Einstellungen, Fenstergruppe, Projekt, Raum, Wand, neue_config_id
from splitklima.produkte import standard
from splitklima.standort import DEFAULT_ORT, ORTE, finde_ort, klimaregion

st.set_page_config(page_title="BOSCH Climate Split-Klima Konfigurator", page_icon="❄️", layout="wide")
st.markdown(
    "<style>.bosch{font-weight:700;font-size:1.6rem}.bosch b{color:#e20015}.bosch span{color:#005691}"
    ".ok{color:#2e7d32}.warn{color:#b26a00}.bad,.err,.orange{color:#c0161d}</style>",
    unsafe_allow_html=True,
)
PD = standard()
STATUSFARBE = {"ok": "🟢", "warn": "🟡", "orange": "🟠", "bad": "🔴", "err": "🔴"}


# ---------------------------------------------------------------- Zustand
def neu_laden(projekt: Projekt) -> None:
    st.session_state.projekt = projekt
    st.session_state.rev = st.session_state.get("rev", 0) + 1
    st.session_state.aktiv = 0


if "projekt" not in st.session_state:
    neu_laden(Projekt())
p: Projekt = st.session_state.projekt
e: Einstellungen = p.einstellungen
REV = st.session_state.rev


def k(name: str) -> str:
    """Widget-Schlüssel; ändert sich, wenn das Projekt ersetzt wird."""
    return f"{REV}:{name}"


def auswahl(label, optionen: dict, wert, key, **kw):
    if wert not in optionen:  # z. B. Wert aus geladenem Projekt, der nicht in der Liste steht
        optionen = optionen | {wert: str(wert)}
    keys = list(optionen)
    return st.selectbox(label, keys, index=keys.index(wert), format_func=optionen.get, key=k(key), **kw)


# ---------------------------------------------------------------- Kopf
kopf_l, kopf_r = st.columns([3, 2])
kopf_l.markdown('<div class="bosch"><b>BOSCH</b> <span>Climate</span> · Split-Klima Konfigurator '
                f'{P.TOOL_VERSION}</div>', unsafe_allow_html=True)
kopf_r.caption("Entwickelt von Daniel Sommer · HC/SDE3-PSD · Python-Version")

# ---------------------------------------------------------------- Seitenleiste
with st.sidebar:
    st.header("Projekt")
    p.name = st.text_input("Projektname", p.name, key=k("name"))
    ort_neu = st.text_input("Standort / PLZ oder Ort", p.ort, key=k("ort"),
                            help="Bekannte Orte: " + ", ".join(f"{z} {n}" for z, n in ORTE))
    p.expertenmodus = st.checkbox("Expertenmodus (Temperaturen manuell)", p.expertenmodus, key=k("expert"))
    treffer = finde_ort(ort_neu)
    if ort_neu != p.ort:
        p.ort = f"{treffer[0]} {treffer[1]}" if treffer else ort_neu
        if treffer:
            p.plz = treffer[0]
            if not p.expertenmodus:
                kr = klimaregion(p.plz)
                e.norm_aussen, e.sommer = kr.norm_aussen, kr.sommer
                st.session_state.rev += 1
                st.rerun()
    if treffer:
        kr = klimaregion(treffer[0])
        st.caption(f"PLZ {treffer[0]} · **{treffer[1]}** · Klimaregion {kr.name} · "
                   f"Norm-Außentemperatur {kr.norm_aussen:g} °C · Sommer {kr.sommer:g} °C"
                   + (" · Expertenmodus: Temperaturen manuell" if p.expertenmodus else ""))
    else:
        st.caption("Ort nicht in der Liste – Norm-Außentemperatur und Sommer-Auslegung bitte manuell prüfen.")
    c1, c2 = st.columns(2)
    p.bearbeiter = c1.text_input("Bearbeiter", p.bearbeiter, key=k("bearbeiter"))
    p.datum = c2.date_input("Datum", p.datum, key=k("datum"), format="DD.MM.YYYY")
    st.caption(f"Konfigurations-ID: `{p.config_id}`")
    if st.button("Auf Standard zurücksetzen", width="stretch"):
        # Auslegungsparameter, Expertenmodus und Standort auf Standard; Räume bleiben erhalten
        neu = Projekt(name=p.name, bearbeiter=p.bearbeiter, datum=p.datum, raeume=p.raeume,
                      config_id=p.config_id, ort=f"{DEFAULT_ORT[0]} {DEFAULT_ORT[1]}", plz=DEFAULT_ORT[0])
        kr = klimaregion(DEFAULT_ORT[0])
        neu.einstellungen.norm_aussen, neu.einstellungen.sommer = kr.norm_aussen, kr.sommer
        neu_laden(neu)
        st.rerun()

    st.header("System und Betriebsart")
    alt_system = e.systemart
    e.systemart = auswahl("Systemart", {"auto": "Automatisch", "single": "Single-Split", "multi": "Multi-Split"},
                          e.systemart, "systemart")
    e.betriebsart = auswahl("Betriebsart", {"both": "Heizen und Kühlen", "cool": "Nur Kühlen", "heat": "Nur Heizen"},
                            e.betriebsart, "betriebsart")
    if e.systemart != alt_system:  # applySystemRules
        if e.systemart == "single" and len(p.raeume) > 1:
            p.raeume = p.raeume[:1]
            st.session_state.aktiv = 0
        if e.systemart == "multi" and len(p.raeume) < 2:
            p.raeume.append(Raum(name=f"Raum {len(p.raeume) + 1}"))
        st.session_state.rev += 1
        st.rerun()

    st.header("Gebäude & Klima")
    e.daemmstandard = auswahl("Bau-/Dämmstandard", P.USTD_LABEL, e.daemmstandard, "daemm")
    e.verglasung = auswahl("Verglasung", P.GLAS_LABEL, e.verglasung, "glas")
    e.sonnenschutz = auswahl("Sonnenschutz", P.SONNENSCHUTZ_LABEL, e.sonnenschutz, "shade")
    c1, c2 = st.columns(2)
    e.norm_aussen = c1.number_input("Norm-Außentemp. (°C)", value=float(e.norm_aussen), step=1.0, key=k("heatOut"))
    e.sommer = c2.number_input("Sommer-Auslegung (°C)", value=float(e.sommer), step=1.0, key=k("summer"))
    e.kuehlbetrieb_h = auswahl("Tägliche Kühlbetriebsdauer · Speichereffekt", P.KUEHLBETRIEB_LABEL,
                               e.kuehlbetrieb_h, "coolHours")
    e.gleichzeitigkeit = auswahl("Gleichzeitigkeitsfaktor (P-004) · bedarfsseitig",
                                 {1.0: "100 % (Norm-Default)", 0.95: "95 %", 0.9: "90 %", 0.85: "85 %"},
                                 e.gleichzeitigkeit, "sim")
    e.waermebruecken = auswahl("Wärmebrückenzuschlag Heizlast (12831-1)",
                               {"none": "ohne Zuschlag", "standard": "pauschal ΔU 0,05", "high": "erhöht ΔU 0,10"},
                               e.waermebruecken, "wb")
    e.aufheizreserve = auswahl("Aufheizreserve Heizlast (12831-1)",
                               {"none": "keine Reserve", "standard": "+15 %", "high": "+30 %"},
                               e.aufheizreserve, "reheat")
    with st.expander("Erweiterte Annahmen (F-015)"):
        c1, c2 = st.columns(2)
        e.soll_kuehlen = c1.number_input("Kühl-Soll (°C)", 18.0, 28.0, float(e.soll_kuehlen), 0.5, key=k("coolSet"))
        e.soll_heizen = c2.number_input("Heiz-Soll (°C)", 16.0, 26.0, float(e.soll_heizen), 0.5, key=k("heatSet"))

    st.header(f"Validierung {P.TOOL_VERSION}")
    faelle = {"": "manuelle Eingabe"} | {key: f"{t['id']} {t['name']}" for key, t in VALIDIERUNGSFAELLE.items()}
    fall = st.selectbox("Referenzfall", list(faelle), index=list(faelle).index(p.validierungsfall),
                        format_func=faelle.get, key=k("fall"))
    if fall != p.validierungsfall:
        if fall:
            wende_validierungsfall_an(p, fall)
        else:
            p.validierungsfall = ""
        neu_laden(p)
        st.rerun()
    with st.expander("Prüfdaten"):
        st.code(pruefdaten_text(p, PD), language=None)

# ---------------------------------------------------------------- Berechnung
erg = auswerten(p, PD)
last, combos, chosen = erg.last, erg.kombinationen, erg.gewaehlt

# ---------------------------------------------------------------- Kennzahlen
m = st.columns(4)
m[0].metric("Räume", last.rooms)
m[1].metric("Kühllast", f"{last.cool:.2f} kW")
m[2].metric("Heizlast", f"{last.heat:.2f} kW")
m[3].metric("System", chosen.label if chosen else "–")
gs, hc, dq = gesamtstatus(p, chosen, PD), heizanwendung(last, chosen), datenqualitaet(p)
s = st.columns(3)
s[0].markdown(f"**Gesamtstatus**  \n{STATUSFARBE[gs.cls]} {gs.txt}")
s[1].markdown(f"**Heizanwendung (B-024)**  \n{STATUSFARBE[hc.cls]} {hc.label}  \n<small>{hc.note}</small>",
              unsafe_allow_html=True)
s[2].markdown(f"**Datenqualität (B-032)**  \n{STATUSFARBE[dq.cls]} {dq.txt} · {dq.individual}/{dq.total} "
              "individuelle Eingaben")
if last.sim_factor < 1:
    st.caption(f"Summe Raumlasten: K {last.raw_cool:.2f} · H {last.raw_heat:.2f} kW → Gleichzeitigkeit "
               f"{last.sim_factor * 100:.0f} % → dimensionierungsrelevant oben.")

v = validiere(p, last, chosen, PD)
if v:
    t = v.target
    with st.container(border=True):
        st.markdown(f"**Sollwert-Validierung: {t['id']} {t['name']}** – {STATUSFARBE[v.status]} {v.status_text}  \n"
                    f"{t['note']}  \nKühllast Ist {last.cool:.2f} kW · Soll {fmt_bereich(t['cool'])} · "
                    f"Heizlast Ist {last.heat:.2f} kW · Soll {fmt_bereich(t['heat'])} · Erwartet: "
                    f"{t.get('system', '-')} · Räume {t.get('rooms', '-')}")
        for x in v.issues:
            st.error(x)
        for x in v.warns:
            st.warning(x)

# ---------------------------------------------------------------- KI-Planerkennung
with st.expander("🔍 Räume aus Architektenplan übernehmen (KI)"):
    dateien = st.file_uploader("Grundrisse, Schnitte, Ansichten (PDF, PNG, JPG)",
                               type=["pdf", "png", "jpg", "jpeg", "webp"], accept_multiple_files=True)
    zusatz = st.text_area("Zusatzangaben (optional)",
                          placeholder="z. B. 'Plan-Oben zeigt nach Nordost', 'nur EG und OG klimatisieren'")
    if st.button("Pläne analysieren", type="primary", disabled=not dateien):
        from splitklima.ki_plan import PlanFehler, analysiere

        mime = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".webp": "image/webp"}
        with st.spinner("Claude liest die Pläne … (1–2 Minuten)"):
            try:
                a = analysiere([(f.getvalue(), mime[Path(f.name).suffix.lower()]) for f in dateien], zusatz)
                st.session_state.ki_ergebnis = a
            except PlanFehler as fehler:
                st.error(str(fehler))
    a = st.session_state.get("ki_ergebnis")
    if a:
        st.info(f"Nordrichtung: {a.nordrichtung}")
        for h in a.hinweise:
            st.warning(h)
        from splitklima.ki_plan import in_raeume

        vorschlag = in_raeume(a)
        st.dataframe(pd.DataFrame([{"Raum": r.name, "Art": r.raumart, "Fläche m²": r.flaeche,
                                    "Lage": P.MODE_LABEL[r.lage],
                                    "Außenwände": ", ".join(f"{w.ausrichtung} {w.laenge:g} m / {w.fenster:g} m² Fenster"
                                                             for w in r.waende)} for r in vorschlag]),
                     hide_index=True, width="stretch")
        if st.button(f"{len(vorschlag)} Räume übernehmen (ersetzt aktuelle Räume)"):
            p.raeume = vorschlag
            if len(vorschlag) > 1 and e.systemart == "single":
                e.systemart = "auto"
            p.validierungsfall = ""
            del st.session_state["ki_ergebnis"]
            neu_laden(p)
            st.rerun()

# ---------------------------------------------------------------- Räume
st.subheader("Räume")
aktiv = min(st.session_state.aktiv, len(p.raeume) - 1)
namen = [f"{i + 1}. {r.name}" for i, r in enumerate(p.raeume)]
c = st.columns([4, 1, 1, 1])
aktiv = c[0].radio("Aktiver Raum", range(len(p.raeume)), index=aktiv, format_func=lambda i: namen[i],
                   horizontal=True, key=k(f"aktiv{len(p.raeume)}"), label_visibility="collapsed")
st.session_state.aktiv = aktiv
if c[1].button("+ Raum", width="stretch", disabled=e.systemart == "single"):
    p.raeume.append(Raum(name=f"Raum {len(p.raeume) + 1}"))
    st.session_state.aktiv = len(p.raeume) - 1
    st.session_state.rev += 1
    st.rerun()
if c[2].button("Duplizieren", width="stretch", disabled=e.systemart == "single"):
    kopie = p.raeume[aktiv].model_copy(deep=True)
    kopie.name += " (Kopie)"
    p.raeume.insert(aktiv + 1, kopie)
    st.session_state.aktiv = aktiv + 1
    st.session_state.rev += 1
    st.rerun()
if c[3].button("Löschen", width="stretch", disabled=len(p.raeume) <= 1):
    p.raeume.pop(aktiv)
    st.session_state.aktiv = max(0, aktiv - 1)
    st.session_state.rev += 1
    st.rerun()

r: Raum = p.raeume[aktiv]
pre = f"r{aktiv}"
links, rechts = st.columns(2)
with links, st.container(border=True):
    st.markdown("**Raumeingabe**")
    c1, c2 = st.columns(2)
    r.name = c1.text_input("Raumname", r.name, key=k(pre + "name"))
    r.raumart = c2.selectbox("Raumart", P.RAUMARTEN, P.RAUMARTEN.index(r.raumart), key=k(pre + "art"))
    c1, c2 = st.columns(2)
    r.flaeche = c1.number_input("Raumfläche (m²)", 0.0, 1000.0, float(r.flaeche), 0.1, key=k(pre + "A"))
    r.hoehe = c2.number_input("Raumhöhe (m)", 0.0, 10.0, float(r.hoehe), 0.1, key=k(pre + "h"))
    r.baualter = auswahl("Baualtersklasse (F-011)",
                         {"": "aus Dämmstandard ableiten"} | {key: f"{v['label']} · U {v['w']}"
                                                              for key, v in P.AGE_CLASSES.items()},
                         r.baualter, pre + "age")
    c1, c2 = st.columns(2)
    with c1:
        r.speicher = auswahl("Speichermasse / Bauart (F-013)",
                             {key: v["label"] for key, v in P.STORAGE_CLASS.items()}, r.speicher, pre + "sto")
    with c2:
        r.daemmung = auswahl("Nachträgliche Dämmung (F-012)",
                             {key: v["label"] for key, v in P.RETROFIT.items()}, r.daemmung, pre + "ret")

with rechts, st.container(border=True):
    st.markdown("**Thermische Lage**")
    lage = st.radio("Lage", P.MODES, P.MODES.index(r.lage), format_func=P.MODE_LABEL.get, horizontal=True,
                    key=k(pre + "mode"), label_visibility="collapsed")
    if lage != r.lage:
        r.setze_lage(lage)
        st.session_state.rev += 1
        st.rerun()
    if r.dach:
        st.caption("Vertikale Lage: Dachgeschoss. Dachfläche wird separat erfasst; darunter vereinfacht beheizt.")
        c1, c2 = st.columns(2)
        with c1:
            r.dachform = auswahl("Dachform", P.DACHFORM_LABEL, r.dachform, pre + "roofKind")
        r.dachflaeche = c2.number_input("Dachfläche (m², 0 = Raumfläche)", 0.0, 1000.0, float(r.dachflaeche),
                                        0.5, key=k(pre + "roofA"))
    else:
        r.vertikal = auswahl("Vertikale Lage (unten / oben)", P.VERTICAL_LABEL, r.vertikal, pre + "vert")

with st.container(border=True):
    st.markdown("**Außenwände** – Fensterfläche wird von der Wand-Bruttofläche abgezogen; die Ausrichtung "
                "fließt in die solare Fensterlast ein.")
    if r.waende:
        wdf = st.data_editor(
            pd.DataFrame([w.model_dump() for w in r.waende]), hide_index=True, width="stretch",
            num_rows="fixed", key=k(pre + "walls"),
            column_config={
                "ausrichtung": st.column_config.SelectboxColumn("Ausrichtung", options=P.AUSRICHTUNGEN,
                                                                required=True),
                "laenge": st.column_config.NumberColumn("Länge (m)", min_value=0.0, step=0.1, required=True),
                "fenster": st.column_config.NumberColumn("Fensterfläche (m²)", min_value=0.0, step=0.1,
                                                         required=True),
            })
        r.waende = [Wand(**z) for z in wdf.to_dict("records")]
    else:
        st.caption("Innenliegender Raum: keine Außenwand.")
    st.markdown("**Zusätzliche Fenstergruppen (F-024)** – mehrere Fenster je Raum, Diagonalorientierungen oder "
                "Dachfenster (erhöhte Einstrahlung, kein Abzug von der Wandfläche).")
    gdf = st.data_editor(
        pd.DataFrame([g.model_dump() for g in r.fenstergruppen], columns=["ausrichtung", "flaeche", "dachfenster"]),
        hide_index=True, width="stretch", num_rows="dynamic", key=k(pre + "groups"),
        column_config={
            "ausrichtung": st.column_config.SelectboxColumn("Ausrichtung", options=P.AUSRICHTUNGEN, default="S"),
            "flaeche": st.column_config.NumberColumn("Fläche (m²)", min_value=0.0, step=0.1, default=1.5),
            "dachfenster": st.column_config.CheckboxColumn("Dachfenster", default=False),
        })
    r.fenstergruppen = [Fenstergruppe(ausrichtung=z["ausrichtung"] or "S", flaeche=z["flaeche"] or 0,
                                      dachfenster=bool(z["dachfenster"]))
                        for z in gdf.to_dict("records") if z.get("flaeche") is not None]

# Nach den Raumeingaben neu rechnen
erg = auswerten(p, PD)
last, combos, chosen = erg.last, erg.kombinationen, erg.gewaehlt

# ---------------------------------------------------------------- Inneneinheiten
st.subheader("Inneneinheiten je Raum")
st.caption("Automatische Vorauswahl: kleinste passende Inneneinheit. 100–130 % passend, 130–180 % prüfen, "
           "über 180 % stark überdimensioniert.")
spalten = st.columns(min(3, len(p.raeume)))
for i, rr in enumerate(p.raeume):
    with spalten[i % len(spalten)], st.container(border=True):
        l = raum_last(rr, e)
        u = ig_gewaehlt(rr, p, PD)
        stt = ig_status(rr, u, p)
        st.markdown(f"**{i + 1}. {rr.name}** – {STATUSFARBE[stt.cls]} {stt.txt}  \n"
                    f"<small>{rr.raumart} · Kühlen {l.cool:.2f} kW · Heizen {l.heat:.2f} kW</small>",
                    unsafe_allow_html=True)
        bauart = st.selectbox("Bauart", P.IG_BAUARTEN, P.IG_BAUARTEN.index(rr.ig_bauart),
                              format_func=lambda x: "automatisch" if x == "auto" else x, key=k(f"igt{i}"))
        if bauart != rr.ig_bauart:
            rr.ig_bauart, rr.ig_id, rr.ig_manuell = bauart, None, False
            st.session_state.rev += 1
            st.rerun()
        opts = [""] + [x.id for x in PD.innen if rr.ig_bauart == "auto" or x.type == rr.ig_bauart]
        lbl = {"": "automatisch wählen"} | {
            x.id: f"{x.name} · {x.cool:.1f} kW · {ig_status(rr, x, p).txt}" for x in PD.innen}
        wahl = st.selectbox("Inneneinheit", opts, opts.index(rr.ig_id) if rr.ig_manuell and rr.ig_id in opts else 0,
                            format_func=lbl.get, key=k(f"igid{i}"))
        rr.ig_id, rr.ig_manuell = (wahl or None), bool(wahl)
        u = ig_gewaehlt(rr, p, PD)
        st.caption(f"{u.name} · {u.type} · {ig_status(rr, u, p).detail} · Schalldruck {u.sound} dB(A)" if u
                   else "Bitte größere Bauart oder Gerätedaten ergänzen.")

erg = auswerten(p, PD)
last, combos, chosen = erg.last, erg.kombinationen, erg.gewaehlt

# ---------------------------------------------------------------- Geräteauswahl
st.subheader("Geräteauswahl")
st.caption("Single-Split-Familien aktiv." if produkt_modus(p, last) == "single" else
           "Multi-Split-Außeneinheiten aktiv. Auto-Modus kann bei mehr als 5 Räumen mehrere Außeneinheiten "
           "kombinieren.")
if not combos:
    st.error("Keine passende Außengerätelösung gefunden. Prüfe Raumanzahl, Systemart oder Auto-Modus.")
else:
    ids = [co.id for co in combos]
    gew = st.radio("Wirtschaftliche Systemalternativen", ids, index=ids.index(chosen.id),
                   format_func=lambda i: next(
                       f"{co.label} · {co.t.cool:.1f}/{co.t.heat:.1f} kW · Anschlüsse {last.rooms}/{co.t.ports}"
                       f"{' · wirtschaftlichste' if j == 0 else ''}" for j, co in enumerate(combos) if co.id == i),
                   key=k("combo"))
    if gew != chosen.id:
        p.gewaehltes_system = gew
        st.rerun()
    d0 = chosen.items[0]
    with st.container(border=True):
        st.markdown(f"### {chosen.label}\n{d0.line}  \n<small>{d0.meta_zeile()}</small>", unsafe_allow_html=True)
        for z in raum_zuordnung(p, chosen):
            st.markdown(f"**System {z.system}** · {z.outdoor.name}: {', '.join(x.name for x in z.rooms)} "
                        f"({len(z.rooms)}/{z.outdoor.ports} Anschlüsse)")

    st.subheader("Kennlinien / Auslegungsdiagnose")
    cp = chosen.t.cool / max(0.01, last.cool) * 100
    hp = chosen.t.heat / max(0.01, last.heat) * 100
    c1, c2, c3 = st.columns(3)
    c1.metric("Kühl-Deckung", f"{cp:.0f} %")
    c2.metric("Heiz-Deckung", f"{hp:.0f} %")
    c3.metric("Anschlussbelegung", f"{last.rooms}/{chosen.t.ports}")
    for name, pct, lst, ger in (("Kühlen", cp, last.cool, chosen.t.cool), ("Heizen", hp, last.heat, chosen.t.heat)):
        st.progress(min(1.0, pct / max(220, cp, hp)), text=f"{name}: {pct:.0f} % · Last {lst:.2f} kW · "
                                                            f"Gerät {ger:.2f} kW")
        st.caption(deckung_text(pct, name))

    t1, t2, t3 = st.tabs(["Schallbewertung", "Zubehörkonfiguration", "Produktdaten Professional"])
    with t1:
        st.dataframe(pd.DataFrame([{"Bereich": z.bereich, "Raum/System": z.bezug, "Gerät": z.geraet,
                                    "Schall": z.schall, "Bewertung": f"{STATUSFARBE[z.cls]} {z.bewertung}",
                                    "Abhilfe / Hinweis": z.hinweis}
                                   for z in schall_uebersicht(p, chosen, last, PD)]),
                     hide_index=True, width="stretch")
    with t2:
        for kat, liste in zubehoer(p, chosen, PD).items():
            if liste:
                st.markdown(f"**{ZUBEHOER_KATEGORIEN[kat]}**")
                st.dataframe(pd.DataFrame([{"Zubehör": z.name, "Art.-Nr.": z.article, "Menge": z.qty,
                                            "Hinweis": z.note} for z in liste]),
                             hide_index=True, width="stretch")
    with t3:
        st.caption("Validierungsstand: Produktdetails sind als Datenqualität „teilweise“ gekennzeichnet. Vor "
                   "Freigabe gegen finale Bosch-Datenblätter/PIM prüfen.")
        st.dataframe(pd.DataFrame([{"Gerät": d.name, "Art.-Nr.": d.article, "Effizienz K/H": f"{d.seer}/{d.scop}",
                                    "Kältemittel": d.refrigerant, "Schall außen": d.soundOutdoor,
                                    "Abmessungen": d.dimensions, "Gewicht": d.weight, "Elektrik": d.powerSupply,
                                    "Betrieb Kühlen": d.opCool, "Betrieb Heizen": d.opHeat,
                                    "Füllung": d.refrigerantCharge, "CO₂-Äq.": d.co2eq,
                                    "Qualität": d.dataQuality} for d in chosen.items]),
                     hide_index=True, width="stretch")

# ---------------------------------------------------------------- Detail & Annahmen
st.subheader("Detailergebnis")
c = raum_last(r, e)
u = ig_gewaehlt(r, p, PD)
zeilen = {
    "Aktiver Raum": r.name,
    "Thermische Lage": P.MODE_LABEL[r.lage],
    "Inneneinheit": f"{u.name} · {ig_status(r, u, p).txt}" if u else "-",
    "Kühllast brutto → netto": f"{c.cool_gross:.2f} kW − Speichereffekt {c.storage_effect:.2f} kW "
                               f"({c.damp * 100:.0f} %) = {c.cool:.2f} kW",
    "Heizlast (12831-1-nah)": f"Transmission {c.heat_trans:.2f} kW + Lüftung {c.heat_vent:.2f} kW"
                              + (f" + Aufheizreserve {c.heat_reheat:.2f} kW" if c.heat_reheat > 0 else "")
                              + f" = {c.heat:.2f} kW",
    "Spezifische Last": f"Kühlen {c.cool * 1000 / (r.flaeche or 1):.0f} W/m² · "
                        f"Heizen {c.heat * 1000 / (r.flaeche or 1):.0f} W/m²",
}
if r.raumart in ("Küche", "Badezimmer"):
    zeilen["Feuchtelast-Hinweis"] = (f"{r.raumart}: erhöhter Feuchteanfall. Latente Lasten werden nicht "
                                     "berechnet – Entfeuchtungsbedarf gesondert prüfen (B-016).")
st.table(pd.DataFrame(zeilen.items(), columns=["", "Wert"]).set_index(""))
if c.wall_gross > 0 and c.win > c.wall_gross:
    st.error("Fensterfläche ist größer als die Außenwandfläche – Eingaben prüfen.")

with st.expander("Berechnungsparameter (CALC-0.4)"):
    st.markdown(" ".join(f"`{v}`" for v in P.MODEL_VERSIONS.values()))
    st.markdown(f"**Rechenansatz:**  \n`{P.FORMELN['cooling']}`  \n`{P.FORMELN['heating']}`  \n"
                f"`{P.FORMELN['ventilation']}`")
    st.dataframe(pd.DataFrame([raum_annahmen(x, p) for x in p.raeume]), hide_index=True, width="stretch")
    st.caption("Alle Werte sind Validierungsannahmen und noch nicht final fachlich freigegeben.")

# ---------------------------------------------------------------- Export & Haftung
st.subheader("Export")
dl = st.columns(5)
stempel = p.config_id
dl[0].download_button("Projekt speichern", p.model_dump_json(indent=2), f"Split_Klima_{stempel}.skk.json",
                      "application/json", width="stretch",
                      help="Vollständiger Projektstand zum späteren Weiterarbeiten")
dl[1].download_button("Projekt-JSON (PJ-0.1)", json.dumps(projektstand(p, PD), ensure_ascii=False, indent=2),
                      f"Split_Klima_Projekt_{stempel}_v6_9_1.json", "application/json", width="stretch")
dl[2].download_button("Produktdaten-JSON", json.dumps(produktdaten(PD, p), ensure_ascii=False, indent=2),
                      "Split_Klima_Produktdaten_DM_0_1_v6_9_1.json", "application/json", width="stretch")
dl[3].download_button("Validierungs-Snapshot", json.dumps(validierungs_snapshot(p, PD), ensure_ascii=False,
                                                          indent=2),
                      f"Split_Klima_Validierung_{stempel}_v6_9_1.json", "application/json", width="stretch")
dl[4].download_button("Berechnungsparameter", json.dumps(berechnungsparameter(p), ensure_ascii=False, indent=2),
                      "Split_Klima_Berechnungsparameter_CALC_0_4_v6_9_1.json", "application/json",
                      width="stretch")
geladen = st.file_uploader("Gespeichertes Projekt laden (.skk.json)", type="json", key=f"laden{REV}")
if geladen:
    try:
        neu_laden(Projekt.model_validate_json(geladen.getvalue()))
        st.rerun()
    except ValueError as fehler:
        st.error(f"Datei ist kein gespeichertes Projekt: {fehler}")

with st.container(border=True):
    st.markdown("**Haftung & Exportfreigabe**")
    ok = all([st.checkbox(t, key=k(f"ack{i}")) for i, t in enumerate(P.HAFTUNGSHINWEISE)])
    if not ok:
        st.caption("PDF-Export gesperrt: Bitte alle Hinweise bestätigen.")
    else:
        st.session_state.setdefault(k("ack_zeit"), datetime.now().strftime("%d.%m.%Y %H:%M"))
        st.download_button("PDF erzeugen (A4 Querformat)", pdf_bericht(p, PD, st.session_state[k("ack_zeit")]),
                           f"Split_Klima_Bericht_{stempel}.pdf", "application/pdf", type="primary")

if st.sidebar.button("Neues Projekt", width="stretch"):
    neu_laden(Projekt(config_id=neue_config_id()))
    st.rerun()
st.caption(f"Entwickelt von Daniel Sommer · HC/SDE3-PSD · SplitConfigCore {P.TOOL_VERSION} (Python)")
