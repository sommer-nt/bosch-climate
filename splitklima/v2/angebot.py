"""PDF-Angebotsübersicht der Version 2 – mit Produktbildern und Katalogpreisen."""

from __future__ import annotations

from .. import parameter as P
from ..berechnung import raum_last
from ..bericht import BOSCH_BLAU, BOSCH_ROT, GRAU, _Bericht
from ..modell import Projekt
from ..preise import fmt_eur, gesamtpreis
from ..sprache import N_, T, englisch, klimaquelle
from .auswahl import AUFSTELLUNG, Konzept, aufstellungshinweise, optionale_leistungen
from .bilder import bild
from .katalog import Katalog

BETRIEB = {"both": N_("Kühlen und Heizen"), "cool": N_("nur Kühlen"), "heat": N_("nur Heizen")}


class _Angebot(_Bericht):
    def header(self):
        self.set_font(self.schrift, "B", 15)
        self.set_text_color(*BOSCH_ROT)
        self.cell(0, 8, "BOSCH", new_x="END")
        self.set_text_color(*BOSCH_BLAU)
        self.cell(0, 8, self.t("  " + T("Climate · Split-Klima Angebotsübersicht")), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BOSCH_ROT)
        self.set_line_width(0.6)
        self.line(12, self.get_y(), self.w - 12, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-10)
        self.set_font(self.schrift, "", 7)
        self.set_text_color(*GRAU)
        self.cell(0, 5, self.t(T("SplitConfigCore {v} · Konfigurations-ID {id} · Seite {s}/{{nb}}",
                                 v=P.TOOL_VERSION, id=self.config_id, s=self.page_no())), align="C")


def _bilderzeile(pdf: _Angebot, pfade: list, hoehe: float = 26) -> None:
    """Produktbilder nebeneinander (Höhe fest, Breite proportional)."""
    from PIL import Image

    x, y = pdf.l_margin, pdf.get_y()
    if y + hoehe > pdf.h - 20:
        pdf.add_page()
        y = pdf.get_y()
    for pfad in pfade:
        with Image.open(pfad) as im:
            breite = hoehe * im.width / im.height
        if x + breite > pdf.w - pdf.r_margin:
            break
        pdf.image(str(pfad), x=x, y=y, h=hoehe)
        x += breite + 4
    pdf.set_y(y + hoehe + 2)


def pdf_angebot_v2(projekt: Projekt, konzept: Konzept, kat: Katalog, bestaetigt_am: str = "") -> bytes:
    pdf = _Angebot(projekt.config_id)
    pdf.add_page()
    e = projekt.einstellungen
    datum = projekt.datum.strftime("%Y-%m-%d" if englisch() else "%d.%m.%Y")
    pdf.text(T("Projekt: {name} · Standort: {ort} · Datum: {datum} · Baujahr: {bj} · Betrieb: {betrieb} · ",
               name=projekt.name, ort=projekt.ort, datum=datum, bj=projekt.baujahr or "-",
               betrieb=T(BETRIEB[e.betriebsart]))
             + (T("Aufstellung Außeneinheit: {a} · ", a=T(AUFSTELLUNG[projekt.aufstellung]))
                if projekt.aufstellung else "")
             + T("Konfigurations-ID: {id}", id=projekt.config_id))

    preis = konzept.preis
    pdf.abschnitt(T("Empfohlene Lösung: {name}", name=konzept.name))
    pdf.set_font(pdf.schrift, "B", 13)
    pdf.set_text_color(*BOSCH_BLAU)
    pdf.cell(0, 7, pdf.t(T("Gerätepreis {preis}", preis=fmt_eur(preis))), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.text(f"{konzept.geraete_text}\n{T(kat.preisbasis)} · " + T("Stand {q}", q=T(kat.quelle)), 8)

    # Bilder: je Gerätetyp einmal
    pfade = []
    for t in konzept.teilsysteme:
        for a in t.artikel():
            pf = bild(a)
            if pf and pf not in pfade:
                pfade.append(pf)
    _bilderzeile(pdf, pfade[:6])

    pdf.abschnitt(T("Systeme"))
    pdf.tabelle([T("System"), T("Räume"), T("Geräte"), T("Last Kühlen"), T("Leistung Kühlen"), T("Last Heizen"),
                 T("Leistung Heizen")],
                [[T(t.bezeichnung), ", ".join(r.name for r in t.raeume), t.geraete_text,
                  f"{t.last_kuehl:.2f} kW", f"{t.leistung_kuehl:.2f} kW", f"{t.last_heiz:.2f} kW",
                  f"{t.leistung_heiz:.2f} kW"] for t in konzept.teilsysteme],
                [28, 62, 93, 22, 22, 22, 24])

    pdf.abschnitt(T("Räume und Inneneinheiten"))
    zeilen = []
    for t in konzept.teilsysteme:
        geraete = [(r, t.set) for r in t.raeume] if t.set else t.innen
        for r, u in geraete:
            b = raum_last(r, e)
            flaeche = f"{r.flaeche:.1f} m²"
            nutzung = T(r.raumart) + (T(" · {n} Pers.", n=r.personen) if r.personen else "")
            zeilen.append([f"{r.geschoss} {r.name}".strip(), nutzung,
                           flaeche if englisch() else flaeche.replace(".", ","),
                           f"{b.cool:.2f} kW", f"{b.heat:.2f} kW",
                           u.typ if u else "-", T(u.bauart or "Wandgerät") if u else "-",
                           T(u.farbe or "-") if u else "-"])
    pdf.tabelle([T("Raum"), T("Nutzung"), T("Fläche"), T("Kühllast"), T("Heizlast"), T("Gerät"), T("Bauart"),
                 T("Farbe")], zeilen, [48, 28, 20, 22, 22, 63, 35, 35])

    kopf = [T("Artikel"), T("Bestell-Nr."), T("Menge"), T("Einzelpreis"), T("Summe")]
    pdf.abschnitt(T("Stückliste Geräte"))
    liste = konzept.stueckliste()
    pdf.tabelle(kopf,
                [[x.name, x.artikel, x.menge, fmt_eur(x.einzelpreis), fmt_eur(x.summe)] for x in liste]
                + [[T("Summe Geräte"), "", "", "", fmt_eur(preis)]], [110, 45, 20, 49, 49])

    from . import zubehoer as Z

    zub_zeilen, zub_hinweise = Z.tabelle(projekt, konzept, kat)
    zub = [z for z in zub_zeilen if z.menge]
    if zub:
        zsumme = Z.summe(zub)
        pdf.abschnitt(T("Zubehör und Montagematerial"))
        pdf.tabelle(kopf,
                    [[T(z.name), z.bestellnr, z.menge, fmt_eur(z.einzelpreis), fmt_eur(z.summe)] for z in zub]
                    + [[T("Summe Zubehör"), "", "", "", fmt_eur(zsumme)]]
                    + ([[T("Geräte + Zubehör"), "", "", "", fmt_eur(preis + zsumme)]]
                       if preis is not None and zsumme is not None else []), [110, 45, 20, 49, 49])
        pdf.text(T("Leitungslänge je Innengerät {l} m.", l=f"{projekt.leitungslaenge:g}") + f" {T(Z.VORKALKULATION)}", 8)

    optional = optionale_leistungen(konzept, kat)
    if optional:
        pdf.abschnitt(T("Optional: Inbetriebnahme durch den Bosch-Kundendienst und Zubehör"))
        pdf.tabelle([T("Leistung"), *kopf[1:]],
                    [[T(x.name), x.artikel, x.menge, fmt_eur(x.einzelpreis), fmt_eur(x.summe)] for x in optional]
                    + [[T("Summe optional"), "", "", "", fmt_eur(gesamtpreis(optional))]], [110, 45, 20, 49, 49])

    hinweise = konzept.lieferhinweise + konzept.hinweise + aufstellungshinweise(projekt, konzept) + zub_hinweise
    if hinweise:
        pdf.abschnitt(T("Hinweise zu Lieferbarkeit, Auswahl und Aufstellung"))
        pdf.text("\n".join(f"- {h}" for h in hinweise), 8)

    pdf.abschnitt(T("Auslegungsgrundlagen"))
    pdf.text(T("{daemm} · {glas}verglasung · Sonnenschutz: {schutz} · Auslegung Sommer {sommer} °C · "
               "Norm-Außentemperatur {ta} °C ({quelle}) · Soll {soll_k} / {soll_h} °C. ",
               daemm=T(P.USTD_LABEL[e.daemmstandard]), glas=T(P.GLAS_LABEL[e.verglasung]),
               schutz=T(P.SONNENSCHUTZ_LABEL[e.sonnenschutz]), sommer=f"{e.sommer:g}", ta=f"{e.norm_aussen:g}",
               quelle=klimaquelle(projekt.klima_quelle) or T("Standardwert"), soll_k=f"{e.soll_kuehlen_wirksam:g}",
               soll_h=f"{e.soll_heizen_wirksam:g}")
             + T("Kühllast in Anlehnung an VDI 2078, Heizlast in Anlehnung an DIN EN 12831-1 (Rechenkern CALC-0.4). "
                 "Geräteauswahl nach den zulässigen Kombinationen des Bosch-Katalogs."), 8)
    pdf.abschnitt(T("Hinweise"))
    pdf.set_text_color(*GRAU)
    pdf.text(T(P.HAFTUNG_LANGTEXT) + (T(" Hinweise bestätigt am {zeit}.", zeit=bestaetigt_am) if bestaetigt_am else ""),
             8)
    return bytes(pdf.output())

