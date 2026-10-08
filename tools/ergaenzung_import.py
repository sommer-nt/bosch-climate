"""Ergänzungskatalog Klima-, Lüftungs- und Wärmepumpen-Sortiment 09/2026 → splitklima/daten/katalog_ergaenzung.json

Aufruf:  python tools/ergaenzung_import.py <Ergänzungskatalog.pdf>
Benötigt (nur für dieses Werkzeug): pip install pymupdf

Das PDF enthält Schriften ohne Zeichentabelle (ToUnicode). Der Text wird deshalb über die
Glyph-Nummern der Schrift „BoschSans“ zurückgewonnen (Zuordnung GLYPHEN unten, an Stichproben
geprüft). Übernommen werden:
  * Large-Split-Sets Climate 5000i L (Single, Twin, Triple, Double Twin) mit Preis und Kenndaten
  * neue Multi-Split-Geräte (CL5000M 53/3 E, CL5000iM 1C …) mit Kenndaten
  * Preise (UVP 09/2026) aller Artikel per Bestellnummer
  * Produktbilder der Large-Split-Familien
"""

from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
ZIEL = WURZEL / "splitklima" / "daten" / "katalog_ergaenzung.json"
BILDER = WURZEL / "splitklima" / "daten" / "bilder"

# Glyph-Nummer → Zeichen für die Schriften „BoschSans“ / „BoschSans,Bold“ (Identity-H ohne ToUnicode)
GLYPHEN = {1: " ", 32: "Ä", 129: "Ø", 171: "Ü", 246: "ä", 345: "ö", 381: "ß", 391: "ü", 512: ",", 514: ":",
           515: ".", 517: "-", 524: '"', 525: '"', 529: '"', 534: "/", 536: "|", 538: "–", 543: "(", 544: ")",
           545: "[", 546: "]", 561: "€", 616: "²", 617: "³", 645: "1/4", 663: "+", 668: "=", 674: "→", 687: "°"}
GLYPHEN.update({2 + i: c for i, c in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ")})
GLYPHEN.update({216 + i: chr(ord("a") + i) for i in range(26)})
GLYPHEN.update({578 + i: str(i) for i in range(10)})

# Kombinationen der neuen Außeneinheit CL5000M 53/3 E (Katalog S. 111, Kombinationsübersicht)
KOMBI_53_3 = [
    (3.5,), (5.3,),
    (2, 2), (2, 2.6), (2, 3.5), (2, 5.3), (2.6, 2.6), (2.6, 3.5), (2.6, 5.3), (3.5, 3.5), (3.5, 5.3),
    (2, 2, 2), (2, 2, 2.6), (2, 2, 3.5), (2, 2.6, 2.6), (2, 2.6, 3.5), (2, 3.5, 3.5), (2.6, 2.6, 2.6),
    (2.6, 2.6, 3.5), (2.6, 3.5, 3.5), (3.5, 3.5, 3.5),
]

BAUART_CODE = {"4CC": "Deckenkassette", "4C": "Deckenkassette", "1C": "Deckenkassette", "CF": "Truhe/Decke",
               "CNE": "Konsole"}
BILD_SEITEN = {  # Kapitel-Titelseite → Bildname (größtes Produktbild der Seite)
    36: "set_5000il_4cc", 42: "set_5000il_4c", 48: "set_5000il_cf", 56: "set_5000il_cne",
    62: "set_5000il_4cc_twin", 68: "set_5000il_4c_twin", 74: "set_5000il_cf_twin",
    80: "set_5000il_4cc_triple", 86: "set_5000il_4cc_double",
}
# Ersatz für die unscharfen Bilder aus dem Gesamtkatalog 03/2026 (dort nur ~150 px eingebettet):
# Bildname → (Seite, xref) des hochaufgelösten Produktbilds im Ergänzungskatalog
BILD_ERSATZ = {
    "set_8000i_weiss": (4, 16), "ie_8000i_anthrazit": (4, 13), "ie_8000i_silber": (4, 14), "ie_8000i_rot": (4, 15),
    "set_7000i_weiss": (12, 629), "ie_7000i_schwarz": (12, 632), "ie_7000i_silber": (12, 627),
    "set_6000ip": (20, 95), "set_3200i": (28, 136), "ae_5000m": (92, 402), "ie_konsole_5000i": (92, 400),
    "ie_wand_3200i": (92, 401), "ie_kassette_5000i": (92, 631), "ae_7000m": (114, 497),
}
# Noch schärfer aus dem Gesamtkatalog 03/2026 (Acrobat-Fassung "_edit"): Bildname → (Seite, xref)
BILD_GESAMT = {
    "ae_5000m": (1, 23872), "ie_konsole_5000i": (1, 23878), "ie_wand_3200i": (1, 23879),
    "ie_kassette_5000i": (1, 23880), "set_7000i_weiss": (1, 23874), "ie_7000i_weiss": (50, 247),
}
# Innengerät aus dem scharfen Set ausschneiden (kein eigenes hochaufgelöstes Einzelbild im Katalog)
IE_AUS_SET = {"ie_8000i_weiss": "set_8000i_weiss"}
# Zubehörbilder: Name → (Katalog "erg"/"gesamt", Seite, xref) – Zuordnung über die Tabellenzeile im Katalog
ZUBEHOER_BILDER = {
    "kabel": ("erg", 129, 584), "regler": ("erg", 129, 585), "sockel_450": ("erg", 129, 586),
    "sockel_600": ("erg", 129, 587), "wandkonsole": ("erg", 129, 588), "spiralschlauch": ("erg", 129, 589),
    "doppelrohr": ("erg", 130, 593), "klemmring": ("erg", 130, 594), "pumpe_mini": ("erg", 131, 598),
    "pumpe_kanal": ("erg", 131, 599), "pumpe_einbau": ("erg", 131, 600),
    "msg1": ("gesamt", 17, 78), "mcr": ("gesamt", 17, 358), "g10_3": ("gesamt", 27, 379),
    "g10_4": ("gesamt", 27, 378), "g10_clc": ("gesamt", 40, 192), "adapter": ("gesamt", 32, 387),
    "bodenkonsole": ("gesamt", 63, 300),
}
# Farbvarianten der Sets: im Katalog nur in Weiß hochaufgelöst → weißes Set + farbiges Innengerät
SET_FARBEN = {
    "set_8000i_anthrazit": ("set_8000i_weiss", "ie_8000i_anthrazit"), "set_8000i_silber": ("set_8000i_weiss", "ie_8000i_silber"),
    "set_8000i_rot": ("set_8000i_weiss", "ie_8000i_rot"),
    "set_7000i_schwarz": ("set_7000i_weiss", "ie_7000i_schwarz"), "set_7000i_silber": ("set_7000i_weiss", "ie_7000i_silber"),
}
# Neues Zubehör im Ergänzungskatalog 09/2026 (Texte S. 55, 129–134; Preise aus der Preistabelle)
ZUBEHOER_NEU = [
    ("Allgemein", "Kabelregler CRC R-3", "7733704064",
     "Kabelgebundener Raumregler, Wochenprogramm, Betriebsmodi, Temperaturbegrenzung; Wandgeräte: MC R nötig "
     "(Nachfolger CRC R-1)", "Climate Split-Klimageräte", 129),
    ("Allgemein", "Dämpfungssockel-Set 450 mm", "7738347185",
     "Schallentkoppelte Aufstellung der Außeneinheit auf festem Untergrund, UV-beständiger Recycling-Gummi "
     "mit Aluschiene, 450×160×90 mm, max. 260 kg je Sockel", "Climate Außeneinheiten", 129),
    ("Allgemein", "Dämpfungssockel-Set 600 mm", "7738347186",
     "Schallentkoppelte Aufstellung großer Außeneinheiten, 600×160×90 mm, max. 470 kg je Sockel",
     "CL7000M 79/3, CL5000M 105/4, CL5000M 125/5", 129),
    ("Allgemein", "Kondensatpumpe Geräteeinbau", "7738346711",
     "Einbau in die Inneneinheit, max. 35 l/h, Förderhöhe 10 m (Nachfolger 7738336975)", "Climate Geräteserie (R32)",
     131),
    ("Gerätespezifisch", "G 10 CLC-1 Gateway-Anschluss", "7733704066",
     "Verbindet CL5000iL CF mit Internet-Gateway G 10-4 und optional Kabelregler CRC R", "CL5000iL CF", 55),
    ("Paket", "Basispaket BOPA CL701 (Bodenkonsole)", "7739625892",
     "CL7000i-Set 26 E + Spiralschlauch 30 m, Doppelrohr 1/4\"+3/8\" 5 m, 4 Klemmringverschraubungen, "
     "Kommunikationskabel 5,5 m, Bodenkonsole", "CL7000i-Set 26 E", 133),
    ("Paket", "Basispaket BOPA CL702 (Wandkonsole)", "7739624113",
     "CL7000i-Set 26 E + Spiralschlauch 30 m, Doppelrohr 1/4\"+3/8\" 5 m, 4 Klemmringverschraubungen, "
     "Kommunikationskabel 5,5 m, Wandkonsole", "CL7000i-Set 26 E", 133),
    ("Paket", "Basispaket BOPA CL321 (Bodenkonsole)", "7739625891",
     "CL3200i-Set 26 WE + Spiralschlauch 30 m, Doppelrohr 1/4\"+3/8\" 5 m, 4 Klemmringverschraubungen, "
     "Kommunikationskabel 5,5 m, Bodenkonsole", "CL3200i-Set 26 WE", 134),
    ("Paket", "Basispaket BOPA CL322 (Wandkonsole)", "7739625457",
     "CL3200i-Set 26 WE + Spiralschlauch 30 m, Doppelrohr 1/4\"+3/8\" 5 m, 4 Klemmringverschraubungen, "
     "Kommunikationskabel 5,5 m, Wandkonsole", "CL3200i-Set 26 WE", 134),
]
TYP_RE = re.compile(r"^CLC?\d{4}[A-Za-z]*(?:-Set)?\s+[\w ./-]+$")
PREIS_RE = re.compile(r"(\d{10})\s*\|\s*([\d.]+,(?:\d\d|––|--))")


# ---------------------------------------------------------------- Text
def seiten_text(doc) -> list[list[str]]:
    """Je Seite die Zeilen (Zellen mit „ | “ getrennt, links → rechts)."""
    out = []
    for page in doc:
        zeilen = collections.defaultdict(list)
        for sp in page.get_texttrace():
            if not sp["chars"]:
                continue
            if sp["font"].split("+")[-1] in ("BoschSans", "BoschSans,Bold"):
                t = "".join(GLYPHEN.get(c[1], "?") for c in sp["chars"])
            else:
                t = "".join(chr(c[0]) for c in sp["chars"])
            y = round(sp["chars"][0][3][1] / 3) * 3
            zeilen[y].append((sp["chars"][0][3][0], t.strip()))
        out.append([" | ".join(t for _, t in sorted(zeilen[y]) if t) for y in sorted(zeilen)])
    return out


def zahl(s: str) -> float | None:
    s = (s or "").strip().replace(".", "").replace(",", ".").replace("––", "00").replace("–", "")
    try:
        return float(s)
    except ValueError:
        return None


def schluessel(typ: str) -> str:
    t = typ.upper().replace(" ", "")
    t = t.replace("CL5001IL", "CL5001L").replace("CL500I1L", "CL5001L").replace("DOUBLETWIN", "DOUBLE")
    return t.replace("-3", "")  # „105 CF-3“ (Preistabelle) = „105 CF“ (Datenblatt)


# ---------------------------------------------------------------- Preise
def preise(seiten: list[list[str]]) -> tuple[dict[str, float], list[dict]]:
    """Alle Bestellnummern mit Preis + Produkteinträge (Typ, Beschreibung, Bestell-Nr., Preis, Seite)."""
    alle: dict[str, float] = {}
    produkte = []
    for nr, zeilen in enumerate(seiten, start=1):
        im_bereich = False
        typen, beschr, paare = [], [], []
        for z in zeilen:
            if re.search(r"Typ \| (Beschreibung|Bezeichnung) \| Bestell-Nr\.", z) or "Anlagenschema | Typ" in z:
                im_bereich = True
                continue
            if not im_bereich:
                continue
            if z.startswith("Unverbindliche Preisempfehlung"):
                im_bereich = False
                for i, (bnr, preis) in enumerate(paare):
                    if i < len(typen):
                        produkte.append({"typ": typen[i], "beschreibung": beschr[i] if i < len(beschr) else "",
                                         "bestellnr": bnr, "preis": preis, "seite": nr})
                typen, beschr, paare = [], [], []
                continue
            for m in PREIS_RE.finditer(z):
                alle[m.group(1)] = zahl(m.group(2))
                paare.append((m.group(1), zahl(m.group(2))))
            for zelle in (c.strip() for c in z.split("|")):
                if TYP_RE.match(zelle):
                    typen.append(re.sub(r"\s+", " ", zelle))
                elif re.match(r"(Single-Split-Klimagerät|Wandhängende|Deckenkassette|Konsolengerät|"
                              r"Multi-Split|1-Wege|Außeneinheit)", zelle):
                    beschr.append(zelle)
    return alle, produkte


# ---------------------------------------------------------------- Technische Daten
FELDER = {
    "Nennkühlleistung": "kuehl", "Min. Kühlleistung": "kuehl_min", "Max. Kühlleistung": "kuehl_max",
    "Nennheizleistung": "heiz", "Min. Heizleistung": "heiz_min", "Max. Heizleistung": "heiz_max",
    "Arbeitszahl im Kühlbetrieb": "seer", "SCOP/A mittleres Klima": "scop",
    "Schallleistungspegel im Freien im Kühlbetrieb": "schall_aussen",
    "Phasenzahl des Stromanschlusses": "phasen", "Anschlussspannung": "spannung",
    "Max. zulässiger Abstand zwischen Innen- und Außeneinheit": "max_abstand",
    "Art der Inneneinheit": "art_innen",
    # Bezeichnungen auf den Seiten der Multi-Split-Inneneinheiten
    "Kühlleistung": "kuehl", "Kühlleistung (min.)": "kuehl_min", "Kühlleistung (max.)": "kuehl_max",
    "Heizleistung": "heiz", "Heizleistung (min.)": "heiz_min", "Heizleistung (max.)": "heiz_max",
}


def technische_daten(seiten: list[list[str]]) -> dict[str, dict]:
    daten: dict[str, dict] = collections.defaultdict(dict)
    for zeilen in seiten:
        spalten: list[str] = []
        label_offen = None
        for z in zeilen:
            zellen = [c.strip() for c in z.split("|")]
            if zellen and all(TYP_RE.match(c) for c in zellen):
                spalten = [schluessel(c) for c in zellen]  # Kopfzeile einer Datentabelle
                label_offen = None
                continue
            if not spalten:
                continue
            # Zeilen wie „Max. zulässiger Abstand …“ stehen manchmal ohne Werte, die Werte folgen
            label = zellen[0]
            if label in FELDER and len(zellen) == 1:
                label_offen = label
                continue
            if label_offen and len(zellen) >= len(spalten):
                zellen = [label_offen] + zellen
                label_offen = None
            label = zellen[0]
            if label not in FELDER:
                continue
            werte = zellen[-len(spalten):]
            for typ, w in zip(spalten, werte):
                feld = FELDER[label]
                if feld in daten[typ]:
                    continue  # erste Angabe gilt (Kombination vor Außen-/Inneneinheit)
                if feld == "phasen":
                    daten[typ][feld] = 3 if w.startswith("3") else 1
                elif feld == "art_innen":
                    daten[typ][feld] = w
                else:
                    v = zahl(w)
                    if v is not None:
                        daten[typ][feld] = v
    return daten


# ---------------------------------------------------------------- Aufbereitung
def large_split(produkte: list[dict], tech: dict[str, dict]) -> tuple[list[dict], list[str]]:
    sets, hinweise = [], []
    for p in produkte:
        if not re.match(r"CL5001i?L-Set", p["typ"]):
            continue
        typ = p["typ"].strip()
        if typ.endswith("Double"):
            typ += " Twin"
        anzahl = 4 if "Double" in typ else 3 if "Triple" in typ else 2 if "Twin" in typ else 1
        code = re.search(r"\b(4CC|4C|CF|CNE)\b", typ.replace("-3", " "))
        t = tech.get(schluessel(typ), {})
        if not t:
            hinweise.append(f"{typ}: keine technischen Daten gefunden (S. {p['seite']}).")
        d = {
            "typ": typ, "bestellnr": p["bestellnr"], "preis": p["preis"], "seite": p["seite"],
            "linie": "Climate 5000i L", "lieferstatus": "lieferbar (Ergänzungskatalog 09/2026)", "verfuegbar": True,
            "beschreibung": p["beschreibung"], "bauart": BAUART_CODE.get(code.group(1), "") if code else "",
            "bauart_code": code.group(1) if code else "", "anzahl_ie": anzahl, "farbe": "weiß",
            "aussen_typ": typ, "innen_typ": typ, "datenquelle": "Ergänzungskatalog 09/2026",
        }
        for feld in ("kuehl", "kuehl_min", "kuehl_max", "heiz", "heiz_min", "heiz_max", "seer", "scop",
                     "schall_aussen", "phasen", "max_abstand"):
            if feld in t:
                d[feld] = t[feld]
        if "kuehl" not in d:  # Notfall: Leistung aus der Typbezeichnung („140“ → 14 kW)
            m = re.search(r"Set (\d+)", typ)
            d["kuehl"] = int(m.group(1)) / 10 if m else None
            hinweise.append(f"{typ}: Kühlleistung aus der Typbezeichnung abgeleitet.")
        if "heiz" not in d:
            hinweise.append(f"{typ}: keine Heizleistung – wird für Heizbetrieb nicht empfohlen.")
        sets.append(d)
    return sets, hinweise


def multi_neu(produkte: list[dict], tech: dict[str, dict]) -> tuple[list[dict], list[dict], list[dict]]:
    aussen, innen = [], []
    for p in produkte:
        typ = p["typ"].strip()
        t = tech.get(schluessel(typ), {})
        if typ == "CL5000M 53/3 E":
            aussen.append({"typ": typ, "bestellnr": p["bestellnr"], "preis": p["preis"], "seite": p["seite"],
                           "linie": "Climate 5000 M", "lieferstatus": "lieferbar (Ergänzungskatalog 09/2026)",
                           "verfuegbar": True, "anschluesse": 3, "min_ie": 1,
                           "datenquelle": "Ergänzungskatalog 09/2026",
                           **{k: t[k] for k in ("kuehl", "heiz", "seer", "scop", "schall_aussen") if k in t}})
        m = re.match(r"CL5000iM 1C (\d+) E", typ)
        if m:
            klasse = {"26": 2.6, "35": 3.5, "53": 5.3, "70": 7.0}[m.group(1)]
            innen.append({"typ": typ, "bestellnr": p["bestellnr"], "preis": p["preis"], "seite": p["seite"],
                          "linie": "Climate 5000i M", "lieferstatus": "lieferbar (Ergänzungskatalog 09/2026)",
                          "verfuegbar": True, "bauart": "Deckenkassette", "farbe": "weiß", "klasse": klasse,
                          "beschreibung": p["beschreibung"] or "1-Wege-Deckenkassette",
                          "aussen_kompatibel": ["CL5000M 53/2 E", "CL5000M 53/3 E", "CL5000M 79/3 E",
                                                "CL5000M 105/4 E", "CL5000M 125/5 E"],
                          "datenquelle": "Ergänzungskatalog 09/2026",
                          **{k: t[k] for k in ("kuehl", "kuehl_min", "kuehl_max", "heiz", "heiz_min", "heiz_max")
                             if k in t}})
    kombis = [{"aussen": "CL5000M 53/3 E", "klassen": sorted(k, reverse=True), "seite": 111} for k in KOMBI_53_3]
    return aussen, innen, kombis


def bilder(doc) -> dict[str, str]:
    from PIL import Image
    import io

    BILDER.mkdir(parents=True, exist_ok=True)
    out = {}
    for seite, name in BILD_SEITEN.items():
        page = doc[seite - 1]
        # größtes Produktbild; die schmale Randleiste (85 × 1757 px) ausschließen
        kandidaten = [(im[2] * im[3], im[0]) for im in page.get_images(full=True)
                      if im[2] * im[3] > 50000 and 0.4 < im[2] / im[3] < 2.5]
        if not kandidaten:
            continue
        _, xref = max(kandidaten)
        roh = doc.extract_image(xref)
        bild = Image.open(io.BytesIO(roh["image"])).convert("RGB")
        bild.save(BILDER / f"{name}.png", optimize=True)
        out[name] = f"S. {seite}"
    return out


def _bild_weiss(doc, xref):
    """Eingebettetes Bild inkl. Transparenzmaske auf weißem Grund, Ränder beschnitten."""
    import pymupdf
    from PIL import Image, ImageChops

    pix = pymupdf.Pixmap(doc, xref)
    smask = doc.extract_image(xref).get("smask")
    if smask:
        pix = pymupdf.Pixmap(pix, pymupdf.Pixmap(doc, smask))
    if pix.colorspace and pix.colorspace.n != 3:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    modus = "RGBA" if pix.alpha else "RGB"
    bild = Image.frombytes(modus, (pix.width, pix.height), pix.samples)
    if modus == "RGBA":
        grund = Image.new("RGB", bild.size, "white")
        grund.paste(bild, mask=bild.split()[3])
        bild = grund
    box = ImageChops.difference(bild, Image.new("RGB", bild.size, "white")).point(lambda v: 255 if v > 12 else 0).getbbox()
    if box:
        rand = 4
        bild = bild.crop((max(box[0] - rand, 0), max(box[1] - rand, 0),
                          min(box[2] + rand, bild.width), min(box[3] + rand, bild.height)))
    return bild


def bilder_ersetzen(doc, tabelle: dict | None = None) -> dict[str, str]:
    """Ältere, unscharfe Produktbilder durch die hochaufgelösten Originale ersetzen."""
    out = {}
    for name, (seite, xref) in (BILD_ERSATZ if tabelle is None else tabelle).items():
        try:
            bild = _bild_weiss(doc, xref)
        except Exception as fehler:  # noqa: BLE001 – fehlendes Bild ist kein Abbruchgrund
            print(f" ! {name}: {fehler}")
            continue
        if bild.width * bild.height < 15000:
            continue
        bild.save(BILDER / f"{name}.png", optimize=True)
        out[name] = f"S. {seite}"
    return out


def _innengeraet_bereich(bild):
    """Bereich des Innengeräts im Set-Bild: oberster Block bis zur ersten breiten Weißlücke."""
    from PIL import Image, ImageChops

    maske = ImageChops.difference(bild, Image.new("RGB", bild.size, "white")).convert("L").point(
        lambda v: 255 if v > 12 else 0)
    leer = [maske.crop((0, y, bild.width, y + 1)).getbbox() is None for y in range(bild.height)]
    start = None
    for y, frei in enumerate(leer):
        if frei and start is None:
            start = y
        elif not frei and start is not None:
            if y - start >= 10:
                return maske.crop((0, 0, bild.width, start)).getbbox()
            start = None
    return None


def ie_aus_set() -> dict[str, str]:
    from PIL import Image

    out = {}
    for name, basis in IE_AUS_SET.items():
        if not (BILDER / f"{basis}.png").exists():
            continue
        bild = Image.open(BILDER / f"{basis}.png").convert("RGB")
        box = _innengeraet_bereich(bild)
        if box:
            rand = 4
            bild.crop((max(box[0] - rand, 0), max(box[1] - rand, 0), min(box[2] + rand, bild.width),
                       min(box[3] + rand, bild.height))).save(BILDER / f"{name}.png", optimize=True)
            out[name] = f"ausgeschnitten aus {basis}"
    return out


def set_farbvarianten() -> dict[str, str]:
    """Farbige Sets aus dem scharfen weißen Set und dem farbigen Innengerät zusammensetzen."""
    from PIL import Image

    out = {}
    for name, (basis, ie) in SET_FARBEN.items():
        if not (BILDER / f"{basis}.png").exists() or not (BILDER / f"{ie}.png").exists():
            continue
        bild = Image.open(BILDER / f"{basis}.png").convert("RGB")
        box = _innengeraet_bereich(bild)
        if not box:
            continue
        geraet = Image.open(BILDER / f"{ie}.png").convert("RGB")
        breite = box[2] - box[0]
        geraet = geraet.resize((breite, round(geraet.height * breite / geraet.width)), Image.LANCZOS)
        hoehe = box[3] - box[1]
        if geraet.height > hoehe + 20:  # passt nicht in die Lücke → Variante nicht erzeugen
            continue
        bild.paste((255, 255, 255), box)
        bild.paste(geraet, (box[0], box[1] + max(hoehe - geraet.height, 0) // 2))
        bild.save(BILDER / f"{name}.png", optimize=True)
        out[name] = f"zusammengesetzt aus {basis} + {ie}"
    return out


def zubehoer_neu(alle_preise: dict[str, float], hinweise: list[str]) -> list[dict]:
    out = []
    for kat, name, nr, text, passend, seite in ZUBEHOER_NEU:
        if nr not in alle_preise:
            hinweise.append(f"Zubehör {name} ({nr}): kein Preis im Ergänzungskatalog gefunden.")
            continue
        out.append({"kategorie": kat, "name": name, "bestellnr": nr, "beschreibung": text, "preis": alle_preise[nr],
                    "passend": passend, "seite": seite})
    return out


def zubehoer_bilder(doc, gesamt: str | None) -> dict[str, str]:
    """Zubehörbilder als kleine PNG (max. 200 px) nach splitklima/daten/bilder/zubehoer/."""
    import pymupdf

    ziel = BILDER / "zubehoer"
    ziel.mkdir(parents=True, exist_ok=True)
    quellen = {"erg": doc, "gesamt": pymupdf.open(gesamt) if gesamt else None}
    out = {}
    for name, (quelle, seite, xref) in ZUBEHOER_BILDER.items():
        if quellen[quelle] is None:
            continue
        try:
            bild = _bild_weiss(quellen[quelle], xref)
        except Exception as fehler:  # noqa: BLE001
            print(f" ! Zubehörbild {name}: {fehler}")
            continue
        bild.thumbnail((200, 200))
        bild.save(ziel / f"{name}.png", optimize=True)
        out[name] = f"{quelle} S. {seite}"
    return out


def _gesamt_bilder(gesamt: str | None) -> dict[str, str]:
    if not gesamt:
        return {}
    import pymupdf

    return {k: f"Gesamtkatalog {v}" for k, v in bilder_ersetzen(pymupdf.open(gesamt), BILD_GESAMT).items()}


def main(pdf: str, gesamt: str | None = None) -> None:
    import pymupdf

    doc = pymupdf.open(pdf)
    seiten = seiten_text(doc)
    alle_preise, produkte = preise(seiten)
    tech = technische_daten(seiten)
    sets, hinweise = large_split(produkte, tech)
    aussen, innen, kombis = multi_neu(produkte, tech)
    for d in (*sets, *aussen, *innen):
        if "kuehl" not in d:
            hinweise.append(f"{d['typ']}: keine technischen Daten gefunden.")
        elif d.get("heiz") is None and "heiz" not in [h for h in hinweise if d["typ"] in h]:
            hinweise.append(f"{d['typ']}: Mangels belastbarer Heizleistungsdaten wird das Gerät ausschließlich "
                            "für Kühlanwendungen berücksichtigt.")
        for art in ("kuehl", "heiz"):  # Datenblatt-Plausibilität: min ≤ nenn ≤ max
            lo, nenn, hi = d.get(f"{art}_min"), d.get(art), d.get(f"{art}_max")
            if None not in (lo, nenn, hi) and not lo <= nenn <= hi:
                # physikalisch unmöglich → Katalogfehler: Min./Max. verwerfen, nur Nennwert verwenden
                d[f"{art}_min"] = d[f"{art}_max"] = None
                d["datenfehler"] = (f"Katalogfehler ({'Kühl' if art == 'kuehl' else 'Heiz'}leistung min {lo:g} / "
                                    f"nenn {nenn:g} / max {hi:g} kW) – nur Nennleistung verwendet")
                hinweise.append(f"{d['typ']}: Datensatz als Katalogfehler markiert ({art} min {lo:g} / nenn {nenn:g} "
                                f"/ max {hi:g} kW) – Min./Max.-Werte werden nicht für automatische "
                                "Plausibilitätsprüfungen verwendet, nur der Nennwert.")
    erg = {
        "quelle": "Bosch Ergänzungskatalog Klima-, Lüftungs- und Wärmepumpen-Sortiment 09/2026",
        "preisbasis": "Unverbindliche Preisempfehlung netto, zzgl. MwSt., Montage und Material (09/2026)",
        "sets": sets, "aussen": aussen, "innen": innen, "kombinationen": kombis,
        "zubehoer": zubehoer_neu(alle_preise, hinweise),
        "preise": alle_preise, "bilder": {**bilder(doc), **bilder_ersetzen(doc), **_gesamt_bilder(gesamt), **ie_aus_set(),
                   **set_farbvarianten(),
                   **{f"zubehoer/{k}": v for k, v in zubehoer_bilder(doc, gesamt).items()}}, "pruefhinweise": hinweise,
    }
    ZIEL.write_text(json.dumps(erg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(sets)} Large-Split-Sets, {len(aussen)} Außen-, {len(innen)} Inneneinheiten neu, "
          f"{len(alle_preise)} Preise, {len(erg['bilder'])} Bilder → {ZIEL.relative_to(WURZEL)}")
    for h in hinweise:
        print(" -", h)


if __name__ == "__main__":
    # Aufruf: ergaenzung_import.py Ergaenzungskatalog.pdf [Gesamtkatalog_edit.pdf]
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
