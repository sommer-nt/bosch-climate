"""PDF der Version 2: Auslegungsdokumentation mit Stückliste oder nur Stückliste (Lastenheft S-010),
jeweils mit Preisausweis in Kapiteln, Nettowert, Mehrwertsteuer und Endbetrag (S-020 bis S-024)."""

from __future__ import annotations

from .. import parameter as P
from ..berechnung import raum_last
from ..bericht import BOSCH_BLAU, BOSCH_ROT, GRAU, _Bericht
from ..modell import Projekt
from ..preise import fmt_eur
from ..sprache import euro
from ..sprache import N_, T, englisch, klimaquelle
from . import preisausweis as PA
from . import zubehoer as Z
from .auswahl import AUFSTELLUNG, Konzept, aufstellungshinweise
from .bilder import bild
from .katalog import Katalog

BETRIEB = {"both": N_("Kühlen und Heizen"), "cool": N_("nur Kühlen"), "heat": N_("nur Heizen")}


UMFANG = {"auslegung": N_("Auslegungsdokumentation mit Stückliste"), "stueckliste": N_("Nur Stückliste")}


class _Angebot(_Bericht):
    titel = N_("Climate · Split-Klima Angebotsübersicht")

    def header(self):
        self.set_font(self.schrift, "B", 15)
        self.set_text_color(*BOSCH_ROT)
        self.cell(0, 8, "BOSCH", new_x="END")
        self.set_text_color(*BOSCH_BLAU)
        self.cell(0, 8, self.t("  " + T(self.titel)), new_x="LMARGIN", new_y="NEXT")
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


def _preisausweis(pdf: _Angebot, pa: PA.Preisausweis) -> None:
    """Preisausweis in Kapiteln mit Zwischensummen; Bedarfspositionen bepreist, aber nicht summiert."""
    eur = lambda b: euro(b, cent=True)  # noqa: E731
    zeilen = []
    for kap in pa.kapitel:
        zeilen.append([str(kap.nr), T("Kapitel {n}: {t}", n=kap.nr, t=T(kap.titel)).upper(), "", "", "", ""])
        if not kap.posten:
            zeilen.append(["", T("In den Komplett-Sets (Kapitel 2) enthalten.") if kap.nr == 1
                           else T("keine Positionen"), "", "", "", ""])
        for j, x in enumerate(kap.posten, 1):
            name = T(x.name) + (" " + T("(Bedarfsposition, nicht in der Summe)") if x.bedarf else "")
            summe = eur(x.summe)
            zeilen.append([f"{kap.nr}.{j}", name, x.bestellnr, str(x.menge), eur(x.einzelpreis),
                           f"({summe})" if x.bedarf else summe])
        zeilen.append(["", T("Zwischensumme Kapitel {n}", n=kap.nr), "", "", "", eur(kap.zwischensumme)])
    zeilen += [["", T("Nettowert"), "", "", "", eur(pa.netto)],
               ["", T("zzgl. MwSt. {p} %", p=f"{pa.mwst_satz * 100:g}"), "", "", "", eur(pa.mwst)],
               ["", T("Endbetrag"), "", "", "", eur(pa.brutto)]]
    pdf.tabelle([T("Pos."), T("Artikel"), T("Bestell-Nr."), T("Menge"), T("Einzelpreis"), T("Summe")], zeilen,
                [14, 124, 34, 16, 42, 43])
    if pa.bedarf_summe:
        pdf.text(T("Bedarfspositionen (nicht in der Summe): {s}", s=eur(pa.bedarf_summe)), 8)


def pdf_angebot_v2(projekt: Projekt, konzept: Konzept, kat: Katalog, bestaetigt_am: str = "",
                   umfang: str = "auslegung") -> bytes:
    pdf = _Angebot(projekt.config_id)
    if umfang == "stueckliste":
        pdf.titel = N_("Climate · Split-Klima Stückliste")
    pdf.add_page()
    e = projekt.einstellungen
    datum = projekt.datum.strftime("%Y-%m-%d" if englisch() else "%d.%m.%Y")
    pdf.text(T("Projekt: {name} · Standort: {ort} · Datum: {datum} · Baujahr: {bj} · Betrieb: {betrieb} · ",
               name=projekt.name, ort=projekt.ort, datum=datum, bj=projekt.baujahr or "-",
               betrieb=T(BETRIEB[e.betriebsart]))
             + (T("Aufstellung Außeneinheit: {a} · ", a=T(AUFSTELLUNG[projekt.aufstellung]))
                if projekt.aufstellung else "")
             + T("Konfigurations-ID: {id}", id=projekt.config_id))

    pa = PA.erstellen(projekt, konzept, kat)
    zub_hinweise = Z.tabelle(projekt, konzept, kat)[1]

    if umfang == "stueckliste":
        pdf.abschnitt(T("Lösung: {name}", name=konzept.name))
        pdf.text(konzept.geraete_text, 8)
        pdf.abschnitt(T("Preisausweis"))
        _preisausweis(pdf, pa)
        pdf.text(f"{T(P.PREIS_HINWEIS)} {T(kat.preisbasis)}.", 8)
        pdf.abschnitt(T("Technische Hinweise"))
        aes = [t.set or t.aussen for t in konzept.teilsysteme if t.set or t.aussen]
        elektro = [T("{typ}: Elektrischer Anschluss {art}", typ=a.typ,
                     art=T("400 V, 3-phasig (Drehstrom)") if a.phasen == 3 else T("230 V, 1-phasig"))
                   for a in dict.fromkeys(aes)]
        hinweise = (elektro + [T("Absicherung und Leitungsquerschnitt laut Montageanleitung des Herstellers; eine "
                                 "elektrische Anschlussplanung erfolgt nicht.")]
                    + konzept.lieferhinweise + zub_hinweise)
        pdf.text("\n".join(f"- {h}" for h in hinweise), 8)
        pdf.text(T("Leitungslänge je Innengerät {l} m.", l=f"{projekt.leitungslaenge:g}") + f" {T(Z.VORKALKULATION)}", 8)
        pdf.abschnitt(T("Hinweise"))
        pdf.set_text_color(*GRAU)
        pdf.text(T(P.HAFTUNG_LANGTEXT) + (T(" Hinweise bestätigt am {zeit}.", zeit=bestaetigt_am)
                                          if bestaetigt_am else ""), 8)
        return bytes(pdf.output())

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

    pdf.abschnitt(T("Preisausweis"))
    _preisausweis(pdf, pa)
    pdf.text(f"{T(P.PREIS_HINWEIS)} {T(kat.preisbasis)}. "
             + T("Leitungslänge je Innengerät {l} m.", l=f"{projekt.leitungslaenge:g}") + f" {T(Z.VORKALKULATION)}", 8)

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
    angepasst = annahmen_abweichungen(projekt)
    pdf.text(T("Berechnungsannahmen: Kühl-Solltemperatur {k} °C · Heiz-Solltemperatur {h} °C · tägliche "
               "Kühlbetriebsdauer {d} h · Bauart: {b}.", k=f"{e.soll_kuehlen_wirksam:g}",
               h=f"{e.soll_heizen_wirksam:g}", d=e.kuehlbetrieb_h, b=T(P.SPEICHER_LABEL[projekt.speicher]))
             + (" " + T("Individuell angepasst: {liste}.", liste=", ".join(angepasst)) if angepasst
                else " " + T("Alle Annahmen auf Standardwerten.")), 8)
    pdf.text(T("Versionsstände: {v} · Katalog {k} · Klimadaten {q} · Berechnung vom {d}.",
               v=" · ".join(f"{k} {w}" for k, w in P.MODEL_VERSIONS.items()), k=T(kat.quelle),
               q=klimaquelle(projekt.klima_quelle) or T("Standardwert"), d=datum), 8)
    pdf.abschnitt(T("Hinweise"))
    pdf.set_text_color(*GRAU)
    pdf.text(T(P.HAFTUNG_LANGTEXT) + (T(" Hinweise bestätigt am {zeit}.", zeit=bestaetigt_am) if bestaetigt_am else ""),
             8)
    return bytes(pdf.output())


def annahmen_abweichungen(projekt: Projekt) -> list[str]:
    """Berechnungsannahmen, die vom Standard abweichen (als „individuell angepasst“ auszuweisen)."""
    e, std = projekt.einstellungen, P.ANNAHMEN_STANDARD
    out = []
    if e.soll_kuehlen_wirksam != std["soll_kuehlen"]:
        out.append(T("Kühl-Solltemperatur"))
    if e.soll_heizen_wirksam != std["soll_heizen"]:
        out.append(T("Heiz-Solltemperatur"))
    if e.kuehlbetrieb_h != std["kuehlbetrieb_h"]:
        out.append(T("Kühlbetriebsdauer"))
    if projekt.speicher != std["speicher"]:
        out.append(T("Bauart / Speichermasse"))
    return out
