"""PDF-Angebotsübersicht der Version 2 – mit Produktbildern und Katalogpreisen."""

from __future__ import annotations

from .. import parameter as P
from ..berechnung import raum_last
from ..bericht import BOSCH_BLAU, BOSCH_ROT, GRAU, _Bericht
from ..modell import Projekt
from ..preise import fmt_eur, gesamtpreis
from .auswahl import AUFSTELLUNG, Konzept, aufstellungshinweise, optionale_leistungen
from .bilder import bild
from .katalog import Katalog

BETRIEB = {"both": "Kühlen und Heizen", "cool": "nur Kühlen", "heat": "nur Heizen"}


class _Angebot(_Bericht):
    def header(self):
        self.set_font(self.schrift, "B", 15)
        self.set_text_color(*BOSCH_ROT)
        self.cell(0, 8, "BOSCH", new_x="END")
        self.set_text_color(*BOSCH_BLAU)
        self.cell(0, 8, self.t("  Climate · Split-Klima Angebotsübersicht"), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BOSCH_ROT)
        self.set_line_width(0.6)
        self.line(12, self.get_y(), self.w - 12, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)


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
    pdf.text(f"Projekt: {projekt.name} · Standort: {projekt.ort} · Datum: {projekt.datum.strftime('%d.%m.%Y')} · "
             f"Baujahr: {projekt.baujahr or '-'} · Betrieb: {BETRIEB[e.betriebsart]} · "
             + (f"Aufstellung Außeneinheit: {AUFSTELLUNG[projekt.aufstellung]} · " if projekt.aufstellung else "") +
             f"Konfigurations-ID: {projekt.config_id}")

    preis = konzept.preis
    pdf.abschnitt(f"Empfohlene Lösung: {konzept.name}")
    pdf.set_font(pdf.schrift, "B", 13)
    pdf.set_text_color(*BOSCH_BLAU)
    pdf.cell(0, 7, pdf.t(f"Gerätepreis {fmt_eur(preis)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.text(f"{konzept.geraete_text}\n{kat.preisbasis} · Stand {kat.quelle}", 8)

    # Bilder: je Gerätetyp einmal
    pfade = []
    for t in konzept.teilsysteme:
        for a in t.artikel():
            pf = bild(a)
            if pf and pf not in pfade:
                pfade.append(pf)
    _bilderzeile(pdf, pfade[:6])

    pdf.abschnitt("Systeme")
    pdf.tabelle(["System", "Räume", "Geräte", "Last Kühlen", "Leistung Kühlen", "Last Heizen", "Leistung Heizen"],
                [[t.bezeichnung, ", ".join(r.name for r in t.raeume), t.geraete_text,
                  f"{t.last_kuehl:.2f} kW", f"{t.leistung_kuehl:.2f} kW", f"{t.last_heiz:.2f} kW",
                  f"{t.leistung_heiz:.2f} kW"] for t in konzept.teilsysteme],
                [28, 62, 93, 22, 22, 22, 24])

    pdf.abschnitt("Räume und Inneneinheiten")
    zeilen = []
    for t in konzept.teilsysteme:
        geraete = [(r, t.set) for r in t.raeume] if t.set else t.innen
        for r, u in geraete:
            b = raum_last(r, e)
            zeilen.append([f"{r.geschoss} {r.name}".strip(), r.raumart, f"{r.flaeche:.1f} m²".replace(".", ","),
                           f"{b.cool:.2f} kW", f"{b.heat:.2f} kW",
                           u.typ if u else "-", (u.bauart or "Wandgerät") if u else "-", (u.farbe or "-") if u else "-"])
    pdf.tabelle(["Raum", "Nutzung", "Fläche", "Kühllast", "Heizlast", "Gerät", "Bauart", "Farbe"], zeilen,
                [48, 28, 20, 22, 22, 63, 35, 35])

    pdf.abschnitt("Stückliste Geräte")
    liste = konzept.stueckliste()
    pdf.tabelle(["Artikel", "Bestell-Nr.", "Menge", "Einzelpreis", "Summe"],
                [[x.name, x.artikel, x.menge, fmt_eur(x.einzelpreis), fmt_eur(x.summe)] for x in liste]
                + [["Summe Geräte", "", "", "", fmt_eur(preis)]], [110, 45, 20, 49, 49])

    from . import zubehoer as Z

    zub_zeilen, zub_hinweise = Z.tabelle(projekt, konzept, kat)
    zub = [z for z in zub_zeilen if z.menge]
    if zub:
        zsumme = Z.summe(zub)
        pdf.abschnitt("Zubehör und Montagematerial")
        pdf.tabelle(["Artikel", "Bestell-Nr.", "Menge", "Einzelpreis", "Summe"],
                    [[z.name, z.bestellnr, z.menge, fmt_eur(z.einzelpreis), fmt_eur(z.summe)] for z in zub]
                    + [["Summe Zubehör", "", "", "", fmt_eur(zsumme)]]
                    + ([["Geräte + Zubehör", "", "", "", fmt_eur(preis + zsumme)]]
                       if preis is not None and zsumme is not None else []), [110, 45, 20, 49, 49])
        pdf.text(f"Leitungslänge je Innengerät {projekt.leitungslaenge:g} m. Vorschlag als Planungshilfe – "
                 "Mengen und Leitungswege bestimmt der Fachbetrieb vor Ort.", 8)

    optional = optionale_leistungen(konzept, kat)
    if optional:
        pdf.abschnitt("Optional: Inbetriebnahme durch den Bosch-Kundendienst und Zubehör")
        pdf.tabelle(["Leistung", "Bestell-Nr.", "Menge", "Einzelpreis", "Summe"],
                    [[x.name, x.artikel, x.menge, fmt_eur(x.einzelpreis), fmt_eur(x.summe)] for x in optional]
                    + [["Summe optional", "", "", "", fmt_eur(gesamtpreis(optional))]], [110, 45, 20, 49, 49])

    hinweise = konzept.lieferhinweise + konzept.hinweise + aufstellungshinweise(projekt, konzept) + zub_hinweise
    if hinweise:
        pdf.abschnitt("Hinweise zu Lieferbarkeit, Auswahl und Aufstellung")
        pdf.text("\n".join(f"- {h}" for h in hinweise), 8)

    pdf.abschnitt("Auslegungsgrundlagen")
    pdf.text(f"{P.USTD_LABEL[e.daemmstandard]} · {P.GLAS_LABEL[e.verglasung]}verglasung · Sonnenschutz: "
             f"{P.SONNENSCHUTZ_LABEL[e.sonnenschutz]} · Auslegung Sommer {e.sommer:g} °C · "
             f"Norm-Außentemperatur {e.norm_aussen:g} °C ({projekt.klima_quelle or 'Standardwert'}) · Soll {e.soll_kuehlen_wirksam:g} / {e.soll_heizen_wirksam:g} °C. "
             "Kühllast in Anlehnung an VDI 2078, Heizlast in Anlehnung an DIN EN 12831-1 (Rechenkern CALC-0.4). "
             "Geräteauswahl nach den zulässigen Kombinationen des Bosch-Katalogs.", 8)
    pdf.abschnitt("Hinweise")
    pdf.set_text_color(*GRAU)
    pdf.text(P.HAFTUNG_LANGTEXT + (f" Hinweise bestätigt am {bestaetigt_am}." if bestaetigt_am else ""), 8)
    return bytes(pdf.output())

