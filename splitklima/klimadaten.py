"""Klimadaten je PLZ nach DIN/TS 12831-1: prüfen, speichern und von der BWP-Klimakarte laden.

Die Klimakarte des Bundesverbands Wärmepumpe (https://www.waermepumpe.de/werkzeuge/klimakarte/)
zeigt die PLZ-genauen Werte der DIN/TS 12831-1. Sie lädt dazu eine SVG-Karte nach, in der jede
PLZ-Fläche ihre Werte als Attribute trägt:

    <polygon zip="72622" place="Nürtingen" dot="-12.4" aat="9.1" alt="291" zone="11" …>

``dot`` = Norm-Außentemperatur, ``aat`` = Jahresmitteltemperatur, ``alt`` = Höhe, ``zone`` = Klimazone.
Die Adresse der Karte steht im HTML der Seite (``bwpClimatezones_Load``). Diese Daten werden
gelesen, streng geprüft und als ``daten/normaussentemperatur_plz.csv`` gespeichert – nur wenn alles
stimmt; sonst bleibt die bisherige Tabelle unverändert.
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

from . import klima_plz as KP

BWP_KARTE_URL = KP.KLIMAKARTE_URL
# Physikalisch mögliche Werte in Deutschland – inkl. Hochgebirge (PLZ 82475 Zugspitze: θm,e ≈ 0 °C)
THETA_E_BEREICH = (-30.0, 2.0)
THETA_M_BEREICH = (-8.0, 14.0)
MIN_PLZ = 1000  # weniger PLZ → offensichtlich keine vollständige Tabelle
UA = "Mozilla/5.0 (Split-Klima-Konfigurator; Klimadaten DIN/TS 12831-1)"


@dataclass(frozen=True)
class Datensatz:
    plz: str
    theta_e: float
    theta_m: float | None = None
    ort: str = ""
    hoehe: float | None = None
    zone: str = ""


def zahl(x) -> float | None:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace("−", "-").replace("–", "-").replace("°C", "").replace("m", "").replace(" ", "")
    if not s:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


# ---------------------------------------------------------------- prüfen und speichern
def pruefen(zeilen: Iterable[dict]) -> tuple[dict[str, Datensatz], list[str]]:
    """Zeilen (dict mit plz, theta_e, theta_m, ort, hoehe, zone, nr) → geprüfte Datensätze + Fehlerliste."""
    werte: dict[str, Datensatz] = {}
    fehler: list[str] = []
    for z in zeilen:
        nr = z.get("nr", "?")
        roh = z.get("plz")
        plz = KP.plz_normalisieren(roh)
        te, tm = zahl(z.get("theta_e")), zahl(z.get("theta_m"))
        if plz is None:
            fehler.append(f"Zeile {nr}: ungültige PLZ „{roh}“")
            continue
        if te is None or not THETA_E_BEREICH[0] <= te <= THETA_E_BEREICH[1]:
            fehler.append(f"Zeile {nr}: PLZ {plz} – Norm-Außentemperatur „{z.get('theta_e')}“ fehlt oder unplausibel")
            continue
        if tm is not None and not THETA_M_BEREICH[0] <= tm <= THETA_M_BEREICH[1]:
            fehler.append(f"Zeile {nr}: PLZ {plz} – Jahresmitteltemperatur {tm} unplausibel")
            continue
        d = Datensatz(plz, te, tm, html.unescape(str(z.get("ort") or "")).strip(), zahl(z.get("hoehe")),
                      str(z.get("zone") or "").strip())
        alt = werte.get(plz)
        if alt and (alt.theta_e, alt.theta_m) != (d.theta_e, d.theta_m):
            fehler.append(f"Zeile {nr}: PLZ {plz} doppelt mit abweichenden Werten "
                          f"({alt.theta_e}/{alt.theta_m} und {d.theta_e}/{d.theta_m})")
            continue
        werte.setdefault(plz, d)
    if werte and len(werte) < MIN_PLZ:
        fehler.append(f"Nur {len(werte)} PLZ – das ist nicht die vollständige Tabelle (mindestens {MIN_PLZ}).")
    if not werte:
        fehler.append("Keine Klimadaten gefunden.")
    return werte, fehler


def bericht(werte: dict[str, Datensatz]) -> list[str]:
    vz = KP.verzeichnis()
    treffer = set(werte) & set(vz)
    zeilen = [f"{len(werte)} PLZ gelesen; Abdeckung des PLZ-Verzeichnisses: {len(treffer)} von {len(vz)} "
              f"({100 * len(treffer) / len(vz):.1f} %)."]
    for p in ("72622", "70173", "80331", "10115", "20095", "50667", "01067"):
        if p in werte:
            d = werte[p]
            zeilen.append(f"Stichprobe {p} {d.ort or (vz[p].ort if p in vz else '')}: θe = {d.theta_e:g} °C"
                          + (f", θm,e = {d.theta_m:g} °C" if d.theta_m is not None else ""))
    return zeilen


def schreiben(werte: dict[str, Datensatz], ziel: Path = KP.NORMTABELLE_CSV, quelle: str = "") -> None:
    """Atomar schreiben (erst Temp-Datei, dann umbenennen) und Zwischenspeicher leeren."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ziel.parent, prefix=".klima_", suffix=".csv")
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["plz", "theta_e", "theta_m", "ort", "hoehe", "klimazone", "quelle"])
        q = quelle or f"Import {date.today():%d.%m.%Y}"
        for p in sorted(werte):
            d = werte[p]
            w.writerow([p, f"{d.theta_e:g}", "" if d.theta_m is None else f"{d.theta_m:g}", d.ort,
                        "" if d.hoehe is None else f"{d.hoehe:g}", d.zone, q])
    os.replace(tmp, ziel)
    KP.normtabelle.cache_clear()
    KP.normtabelle_zusatz.cache_clear()


# ---------------------------------------------------------------- BWP-Klimakarte
def _http_get(url: str, timeout: float) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 – feste https-Adresse
        roh = r.read()
        kod = r.headers.get_content_charset() or "utf-8"
    return roh.decode(kod, errors="replace")


def _entschaerfen(s: str) -> str:
    """JS-/HTML-Maskierungen in einer URL oder einem Datenblock auflösen."""
    s = s.replace("\\/", "/").replace('\\"', '"').replace("\\u0026", "&")
    return html.unescape(s)


def bwp_datenquellen(seite: str, basis: str = BWP_KARTE_URL) -> dict[str, str]:
    """Adressen aus dem HTML der Klimakarte: Load (SVG), Info (JSON), AdditionalData."""
    out = {}
    for name in ("Load", "Info", "AdditionalData"):
        m = re.search(rf"bwpClimatezones_{name}\s*=\s*(['\"])(.*?)\1", seite)
        if m:
            out[name] = urljoin(basis, _entschaerfen(m.group(2)))
    return out


_POLYGON = re.compile(r"<polygon\b([^>]*)>", re.I)
_ATTR = re.compile(r"([\w:-]+)\s*=\s*(\"([^\"]*)\"|'([^']*)')")


def parse_polygone(svg: str) -> list[dict]:
    """SVG der Klimakarte → Zeilen für ``pruefen`` (eine je Fläche, Mehrfachflächen je PLZ möglich)."""
    if '\\"' in svg:
        svg = _entschaerfen(svg)
    zeilen = []
    for nr, m in enumerate(_POLYGON.finditer(svg), start=1):
        a = {k.lower(): v1 or v2 for k, _, v1, v2 in _ATTR.findall(m.group(1))}
        if "zip" not in a:
            continue
        zeilen.append({"nr": nr, "plz": a.get("zip"), "theta_e": a.get("dot"), "theta_m": a.get("aat"),
                       "ort": a.get("place", ""), "hoehe": a.get("alt"), "zone": a.get("zone", "")})
    return zeilen


def von_bwp_laden(ziel: Path = KP.NORMTABELLE_CSV, timeout: float = 60.0,
                  get=None) -> tuple[bool, list[str]]:
    """Klimadaten von der BWP-Klimakarte laden, prüfen und speichern. → (erfolgreich, Meldungen)."""
    get = get or _http_get
    meldungen: list[str] = []
    try:
        seite = get(BWP_KARTE_URL, timeout)
        quellen = bwp_datenquellen(seite)
        if "Load" not in quellen:
            return False, ["Die Klimakarte hat ihren Aufbau geändert – Datenadresse nicht gefunden."]
        erwartet = None
        if "Info" in quellen:
            try:
                erwartet = int(json.loads(get(quellen["Info"], timeout)).get("count"))
            except (ValueError, TypeError, AttributeError, OSError):
                erwartet = None
        svg = get(quellen["Load"], timeout)
    except OSError as e:  # Netzwerk, Zeitüberschreitung, HTTP-Fehler
        return False, [f"Die BWP-Klimakarte ist nicht erreichbar ({e})."]

    zeilen = parse_polygone(svg)
    if erwartet:
        meldungen.append(f"Karte meldet {erwartet} Gebiete, gelesen: {len(zeilen)} Flächen.")
    werte, fehler = pruefen(zeilen)
    if fehler:
        return False, meldungen + [f"{len(fehler)} Fehler – Klimadaten nicht übernommen:", *fehler[:10]]
    schreiben(werte, ziel, f"BWP-Klimakarte (DIN/TS 12831-1), geladen am {date.today():%d.%m.%Y}")
    return True, meldungen + bericht(werte)


def aus_datei(pfad: Path, ziel: Path = KP.NORMTABELLE_CSV) -> tuple[bool, list[str]]:
    """Tabelle aus Excel/CSV (z. B. Export der Klimakarte) übernehmen. → (erfolgreich, Meldungen)."""
    zeilen = tabellenzeilen(pfad)
    if zeilen is None:
        return False, ["Keine Kopfzeile mit „PLZ“ und „Norm-Außentemperatur“ gefunden."]
    werte, fehler = pruefen(zeilen)
    if fehler:
        return False, [f"{len(fehler)} Fehler – nichts übernommen:", *fehler[:25]]
    schreiben(werte, ziel, f"Import {pfad.name}, {date.today():%d.%m.%Y}")
    return True, bericht(werte)


# ---------------------------------------------------------------- Excel/CSV lesen
def _rohzeilen(pfad: Path) -> list[list]:
    if pfad.suffix.lower() in (".xlsx", ".xlsm"):
        import openpyxl

        wb = openpyxl.load_workbook(pfad, read_only=True, data_only=True)
        erste = []
        for ws in wb.worksheets:  # erstes Blatt mit erkennbarer Kopfzeile gewinnt
            zeilen = [list(z) for z in ws.iter_rows(values_only=True)]
            if _spalten(zeilen) is not None:
                return zeilen
            erste = erste or zeilen
        return erste
    roh = pfad.read_bytes()
    for kod in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = roh.decode(kod)
            break
        except UnicodeDecodeError:
            continue
    try:
        dialekt = csv.Sniffer().sniff(text[:4000], delimiters=";,\t")
    except csv.Error:
        class dialekt(csv.excel):
            delimiter = ";"
    return [list(z) for z in csv.reader(text.splitlines(), dialekt)]


def _spalten(zeilen: list[list]) -> dict[str, int] | None:
    """Spalten an der Überschrift erkennen → {feld: index, 'kopf': zeile}."""
    for i, z in enumerate(zeilen[:30]):
        kopf = [re.sub(r"\s+", " ", str(c or "")).strip().lower() for c in z]

        def such(bed):
            return next((j for j, k in enumerate(kopf) if bed(k)), None)

        sp = {
            "plz": such(lambda k: k in ("plz", "postleitzahl", "zip") or k.startswith("plz")),
            "theta_e": such(lambda k: ("norm" in k and "au" in k) or k in ("θe", "theta_e", "te", "dot")),
            "theta_m": such(lambda k: "mittel" in k or k in ("θm,e", "θme", "theta_m", "tm", "aat")),
            "ort": such(lambda k: k in ("ort", "place", "gemeinde", "name")),
            "hoehe": such(lambda k: k.startswith("höhe") or k.startswith("hoehe") or k in ("alt", "altitude")),
            "zone": such(lambda k: "zone" in k),
        }
        if sp["plz"] is not None and sp["theta_e"] is not None:
            return {**{k: v for k, v in sp.items() if v is not None}, "kopf": i}
    return None


def tabellenzeilen(pfad: Path) -> list[dict] | None:
    zeilen = _rohzeilen(pfad)
    sp = _spalten(zeilen)
    if sp is None:
        return None
    out = []
    for nr, z in enumerate(zeilen[sp["kopf"] + 1:], start=sp["kopf"] + 2):
        if not any(c not in (None, "") for c in z):
            continue
        out.append({"nr": nr, **{k: (z[j] if j < len(z) else None) for k, j in sp.items() if k != "kopf"}})
    return out
