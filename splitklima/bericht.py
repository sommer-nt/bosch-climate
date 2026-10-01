"""PDF-Konfigurationsbericht (A4 quer) – entspricht dem Druckbericht von v6.9.1."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

from . import parameter as P
from .auswahl import ig_gewaehlt, ig_status, raum_zuordnung
from .berechnung import raum_last
from .bewertung import ZUBEHOER_KATEGORIEN, fmt_bereich, schall_uebersicht, validiere, zubehoer
from .export import auswerten, raum_annahmen
from .modell import Projekt
from .produkte import Produktdaten

BOSCH_ROT = (226, 0, 21)
BOSCH_BLAU = (0, 86, 145)
GRAU = (90, 98, 108)

SCHRIFTEN = [  # (normal, fett) – erste vorhandene wird genutzt
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
]
ERSATZ = {"₂": "2", "→": "->", "≈": "~", "Δ": "d", "–": "-", "−": "-", "“": '"', "„": '"', "×": "x"}


class _Bericht(FPDF):
    def __init__(self, config_id: str):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.config_id = config_id
        self.unicode = False
        for normal, fett in SCHRIFTEN:
            if Path(normal).exists() and Path(fett).exists():
                self.add_font("Text", "", normal)
                self.add_font("Text", "B", fett)
                self.unicode = True
                break
        self.schrift = "Text" if self.unicode else "Helvetica"
        self.set_auto_page_break(True, margin=14)
        self.set_margins(12, 12, 12)

    def t(self, s) -> str:
        s = str(s)
        if not self.unicode:
            for a, b in ERSATZ.items():
                s = s.replace(a, b)
            s = s.encode("latin-1", "replace").decode("latin-1")
        else:
            for a in ("₂", "→"):
                s = s.replace(a, ERSATZ[a])
        return s

    def header(self):
        self.set_font(self.schrift, "B", 15)
        self.set_text_color(*BOSCH_ROT)
        self.cell(0, 8, "BOSCH", new_x="END")
        self.set_text_color(*BOSCH_BLAU)
        self.cell(0, 8, self.t("  Climate · Split-Klima Konfigurationsbericht"), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BOSCH_ROT)
        self.set_line_width(0.6)
        self.line(12, self.get_y(), self.w - 12, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-10)
        self.set_font(self.schrift, "", 7)
        self.set_text_color(*GRAU)
        self.cell(0, 5, self.t(f"SplitConfigCore {P.TOOL_VERSION} · Konfigurations-ID {self.config_id} · "
                               f"Seite {self.page_no()}/{{nb}}"), align="C")

    def abschnitt(self, titel: str):
        if self.get_y() > self.h - 40:
            self.add_page()
        self.ln(2)
        self.set_font(self.schrift, "B", 11)
        self.set_text_color(*BOSCH_BLAU)
        self.cell(0, 7, self.t(titel), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def text(self, s: str, groesse: float = 8.5):
        self.set_font(self.schrift, "", groesse)
        self.multi_cell(0, 4.4, self.t(s), align="L", new_x="LMARGIN", new_y="NEXT")

    def tabelle(self, kopf: list[str], zeilen: list[list], breiten: list[float] | None = None):
        self.set_font(self.schrift, "", 7.5)
        self.set_fill_color(240, 244, 248)
        self.set_draw_color(0, 0, 0)
        kopfstil = FontFace(emphasis="BOLD", color=(255, 255, 255), fill_color=BOSCH_BLAU)
        with self.table(col_widths=breiten, headings_style=kopfstil, line_height=4.6,
                        text_align="LEFT", first_row_as_headings=True,
                        cell_fill_color=(240, 244, 248), cell_fill_mode="ROWS") as tab:
            tab.row([self.t(k) for k in kopf])
            for z in zeilen:
                tab.row([self.t(x) for x in z])
        self.ln(1)


def pdf_bericht(projekt: Projekt, pd: Produktdaten, bestaetigt_am: str = "") -> bytes:
    erg = auswerten(projekt, pd)
    last, ch = erg.last, erg.gewaehlt
    reco = ch.label if ch else "-"
    pdf = _Bericht(projekt.config_id)
    pdf.add_page()

    pdf.text(f"Projekt: {projekt.name} · Standort: {projekt.ort} · Bearbeiter: {projekt.bearbeiter or '-'} · "
             f"Datum: {projekt.datum.strftime('%d.%m.%Y')}\n"
             f"Konfigurations-ID: {projekt.config_id} · Version: SplitConfigCore {P.TOOL_VERSION} · "
             f"Disclaimer bestätigt: {'Ja' if bestaetigt_am else 'Nein'} · Bestätigt am: {bestaetigt_am or '-'}")
    pdf.ln(1)
    pdf.tabelle(["Räume", "Kühlen", "Heizen", "System"],
                [[last.rooms, f"{last.cool:.2f} kW", f"{last.heat:.2f} kW", reco]], [20, 30, 30, 193])

    pdf.abschnitt("Sollwert-Validierung")
    v = validiere(projekt, last, ch, pd)
    if v:
        t = v.target
        pdf.text(f"{t['id']} {t['name']} · Status: {v.status_text}\n"
                 f"Kühllast Ist/Soll: {last.cool:.2f} kW / {fmt_bereich(t['cool'])} · "
                 f"Heizlast Ist/Soll: {last.heat:.2f} kW / {fmt_bereich(t['heat'])}\n"
                 + ("\n".join(v.issues + v.warns) or "Keine Abweichungen erkannt."))
    else:
        pdf.text("Kein Referenzfall aktiv.")

    pdf.abschnitt("Berechnungsparameter und Annahmen")
    e = projekt.einstellungen
    pdf.text(f"Bau-/Dämmstandard: {P.USTD_LABEL[e.daemmstandard]} (U-Wand {P.USTD[e.daemmstandard]['w']}) · "
             f"Verglasung: {P.GLAS_LABEL[e.verglasung]} (U {P.GLAS[e.verglasung]['u']}, g {P.GLAS[e.verglasung]['g']}) · "
             f"Sonnenschutz: {P.SONNENSCHUTZ_LABEL[e.sonnenschutz]} · Auslegung {e.sommer:g} / {e.norm_aussen:g} °C · "
             f"Soll {e.soll_kuehlen_wirksam:g} / {e.soll_heizen_wirksam:g} °C · Gleichzeitigkeit "
             f"{e.gleichzeitigkeit_wirksam * 100:.0f} %\n"
             f"Kühlen: {P.FORMELN['cooling']}\nHeizen: {P.FORMELN['heating']}")
    pdf.tabelle(
        ["Raum", "Art", "Volumen", "Baualter", "U-Wand", "U-Fenster", "g", "n", "Speicher", "Dämpfung",
         "Brutto", "Fenster", "Dach"],
        [[a["room"], a["type"], f"{a['volume']:.1f} m³", a["ageClass"], f"{a['uWall']:g}", f"{a['uWindow']:g}",
          f"{a['gValue']:g}", f"{a['airChange']:g}", a["storageClass"], a["storageDamping"],
          f"{a['coolGross']:.2f} kW", f"{a['windowArea']:.1f} m²", f"{a['roofArea']:.1f} m²"]
         for a in (raum_annahmen(r, projekt) for r in projekt.raeume)],
        [30, 24, 19, 28, 15, 17, 10, 10, 36, 18, 22, 21, 23],
    )

    if ch:
        pdf.abschnitt("Auslegungscharakteristik")
        for name, l, g in (("Kühlen", last.cool, ch.t.cool), ("Heizen", last.heat, ch.t.heat)):
            pct = g / max(0.01, l) * 100
            _balken(pdf, name, pct, f"Last {l:.2f} kW · Gerät {g:.2f} kW")
        pdf.text("Zielbereich 100-130 %, Prüfbereich 130-180 %, kritisch unter 100 % oder stark über 180 %.", 7.5)

    pdf.abschnitt("Raumübersicht mit Inneneinheiten")
    zeilen = []
    for i, r in enumerate(projekt.raeume, 1):
        l = raum_last(r, e)
        u = ig_gewaehlt(r, projekt, pd)
        zeilen.append([i, r.name, r.raumart, f"{l.cool:.2f}", f"{l.heat:.2f}", u.name if u else "-",
                       u.type if u else "-", ig_status(r, u, projekt).txt])
    pdf.tabelle(["#", "Raum", "Art", "Kühlen kW", "Heizen kW", "Inneneinheit", "Bauart", "Status"], zeilen,
                [8, 40, 28, 20, 20, 50, 32, 75])

    if ch:
        pdf.abschnitt("Energie- und Gerätedaten")
        pdf.tabelle(["Gerät", "Art.-Nr.", "Effizienz K/H", "Kältemittel", "Schall außen"],
                    [[d.name, d.article or "-", f"{d.seer or '-'} / {d.scop or '-'}", d.refrigerant or "-",
                      f"{d.soundOutdoor or '-'} dB(A)"] for d in ch.items])
        pdf.abschnitt("Produktdaten Professional")
        pdf.tabelle(["Gerät", "Art.-Nr.", "Abmessungen", "Gewicht", "Elektrik", "Kühlen", "Heizen",
                     "Kältemittel", "Qualität"],
                    [[d.name, d.article or "-", d.dimensions or "noch offen", d.weight or "noch offen",
                      d.powerSupply or "noch offen", d.opCool or "noch offen", d.opHeat or "noch offen",
                      d.refrigerantCharge or "noch offen", d.dataQuality or "offen"] for d in ch.items])
        pdf.text("Produktdetails sind im Validierungsstand und müssen vor Freigabe gegen finale Bosch-Daten "
                 "geprüft werden.", 7.5)
        pdf.abschnitt("Raum-/Systemzuordnung")
        pdf.tabelle(["System", "Außengerät", "Zugeordnete Räume", "Belegung"],
                    [[f"System {z.system}", z.outdoor.name, ", ".join(r.name for r in z.rooms),
                      f"{len(z.rooms)}/{z.outdoor.ports}"] for z in raum_zuordnung(projekt, ch)])

    pdf.abschnitt("Schallbewertung")
    pdf.tabelle(["Bereich", "Raum/System", "Gerät", "Schall", "Bewertung", "Abhilfe / Hinweis"],
                [[s.bereich, s.bezug, s.geraet, s.schall, s.bewertung, s.hinweis]
                 for s in schall_uebersicht(projekt, ch, last, pd)], [22, 32, 45, 22, 38, 114])

    pdf.abschnitt("Zubehörkonfiguration")
    pdf.tabelle(["Kategorie", "Zubehör", "Art.-Nr.", "Menge", "Hinweis"],
                [[ZUBEHOER_KATEGORIEN[k], z.name, z.article, z.qty, z.note]
                 for k, liste in zubehoer(projekt, ch, pd).items() for z in liste], [40, 80, 30, 15, 108])

    pdf.abschnitt("Haftungs- und Nutzungshinweise")
    pdf.text(P.HAFTUNG_LANGTEXT, 8)
    return bytes(pdf.output())


def _balken(pdf: _Bericht, name: str, pct: float, info: str) -> None:
    x0, breite, hoehe = 40, 180, 5
    skala = breite / max(220, pct)
    y = pdf.get_y() + 1
    pdf.set_font(pdf.schrift, "B", 8)
    pdf.set_xy(12, y)
    pdf.cell(26, hoehe, pdf.t(name))
    pdf.set_fill_color(235, 238, 242)
    pdf.rect(x0, y, breite, hoehe, "F")
    farbe = (192, 22, 29) if pct < 100 else (46, 125, 50) if pct <= 130 else (178, 106, 0)
    pdf.set_fill_color(*farbe)
    pdf.rect(x0, y, max(1.5, min(breite, pct * skala)), hoehe, "F")
    pdf.set_draw_color(*GRAU)
    pdf.set_line_width(0.2)
    for marke in (100, 130, 180):
        pdf.line(x0 + marke * skala, y - 0.8, x0 + marke * skala, y + hoehe + 0.8)
    pdf.set_xy(x0 + breite + 3, y)
    pdf.set_font(pdf.schrift, "", 8)
    pdf.cell(0, hoehe, pdf.t(f"{pct:.0f} % · {info}"))
    pdf.set_fill_color(255, 255, 255)
    pdf.set_y(y + hoehe + 2)
