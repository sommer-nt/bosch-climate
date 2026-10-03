"""Norm-Außentemperatur über die PLZ: Prüfung, Suche, offizielle Tabelle, Import, Oberfläche."""

import csv
import importlib.util
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from splitklima import klima_plz as KP

WURZEL = Path(__file__).parent.parent
_spec = importlib.util.spec_from_file_location("normtemperatur_import", WURZEL / "tools" / "normtemperatur_import.py")
IMP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(IMP)


@pytest.mark.parametrize("eingabe,erwartet", [
    ("72622", "72622"), (" 72622 ", "72622"), ("D-72622", "72622"), ("1067", "01067"), (1067, "01067"),
    ("01001", "01001"), ("00000", None), ("99999", None), ("7262a", None), ("", None), (None, None), ("123", None),
])
def test_plz_normalisieren(eingabe, erwartet):
    assert KP.plz_normalisieren(eingabe) == erwartet


def test_verzeichnis_ganz_deutschland():
    vz = KP.verzeichnis()
    assert len(vz) > 8000
    assert vz["72622"].ort == "Nürtingen" and vz["72622"].bundesland == "Baden-Württemberg"
    assert vz["01067"].ort == "Dresden" and vz["20095"].ort == "Hamburg"
    assert all(len(p) == 5 and p.isdigit() for p in vz)
    assert all(47.2 < e.lat < 55.1 and 5.8 < e.lon < 15.1 for e in vz.values())


@pytest.mark.parametrize("eingabe,plz", [
    ("72622", "72622"), ("72622 Nürtingen", "72622"), ("Nürtingen", "72622"), ("nuertingen", "72622"),
    ("D 72622", "72622"), ("1067", "01067"), ("München", "80331"),
])
def test_suche_eindeutig(eingabe, plz):
    assert KP.suche(eingabe)[0].plz == plz


def test_suche_mehrdeutig_und_unbekannt():
    assert len(KP.suche("Hamburg")) > 1
    assert KP.suche("12345") == [] and KP.suche("Atlantis") == [] and KP.suche("") == []


TAB = {"72622": (-12.4, 9.1), "80331": (-14.6, 9.4)}


def test_offizieller_wert_exakt():
    w = KP.norm_aussentemperatur("72622", TAB)
    assert (w.theta_e, w.theta_m, w.status, w.offiziell) == (-12.4, 9.1, "din", True)
    assert w.ort == "Nürtingen" and w.quelle == "DIN/TS 12831-1"


def test_nachbar_plz_nur_in_der_naehe():
    w = KP.norm_aussentemperatur("72631", TAB)  # Aichtal, ca. 6 km von Nürtingen
    assert w.status == "nachbar" and w.theta_e == -12.4 and "72622" in w.quelle
    w = KP.norm_aussentemperatur("10115", TAB)  # Berlin: kein Tabellenwert in 15 km → Richtwert
    assert w.status == "richtwert" and not w.offiziell and "prüfen" in w.quelle


def test_ohne_tabelle_richtwert_gekennzeichnet():
    w = KP.norm_aussentemperatur("80331", {})
    assert (w.theta_e, w.status) == (-16, "richtwert") and "Bayern" in w.quelle
    w = KP.norm_aussentemperatur("50667", {})  # außerhalb der v6.9.1-Regionen
    assert w.status == "richtwert" and "Standardwert" in w.quelle
    assert KP.norm_aussentemperatur("12345", {}) is None
    assert KP.norm_aussentemperatur("abc", {}) is None


# ---------------------------------------------------------------- Import der offiziellen Tabelle
def _excel(pfad: Path, zeilen: list[list]) -> Path:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["DIN/TS 12831-1 – Klimadaten"])
    ws.append([])
    ws.append(["PLZ", "Ort", "Norm-Außentemperatur in °C", "Jahresmitteltemperatur in °C"])
    for z in zeilen:
        ws.append(z)
    wb.save(pfad)
    return pfad


def _testzeilen(n: int = 1200) -> list[list]:
    plz = sorted(KP.verzeichnis())[:n]
    # Excel speichert PLZ als Zahl → führende Null fehlt; Werte teils mit Dezimalkomma
    return [[int(p), "Ort", "-12,4" if i % 2 else -13.1, 8.9] for i, p in enumerate(plz)]


def test_import_excel_ok(tmp_path):
    ziel = tmp_path / "tab.csv"
    assert IMP.importiere(_excel(tmp_path / "t.xlsx", _testzeilen()), ziel) == 0
    tab = KP.lade_normtabelle(ziel)
    assert len(tab) == 1200
    erste = sorted(KP.verzeichnis())[0]
    assert erste.startswith("0") and erste in tab  # führende Null ergänzt
    assert set(tab.values()) == {(-13.1, 8.9), (-12.4, 8.9)}


def test_import_csv_semikolon(tmp_path):
    quelle = tmp_path / "t.csv"
    with quelle.open("w", encoding="cp1252", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["Postleitzahl", "Norm-Außentemperatur", "Jahresmittel"])
        for z in _testzeilen():
            w.writerow([z[0], str(z[2]).replace(".", ","), "8,9"])
    ziel = tmp_path / "tab.csv"
    assert IMP.importiere(quelle, ziel) == 0
    assert len(KP.lade_normtabelle(ziel)) == 1200


@pytest.mark.parametrize("fehler", ["bereich", "doppelt", "plz", "zu_wenig"])
def test_import_bricht_bei_fehlern_ab(tmp_path, fehler):
    zeilen = _testzeilen()
    if fehler == "bereich":
        zeilen[5][2] = 12.0  # positive Norm-Außentemperatur
    elif fehler == "doppelt":
        zeilen.append([zeilen[0][0], "Ort", -9.0, 8.9])
    elif fehler == "plz":
        zeilen[7][0] = "ABCDE"
    else:
        zeilen = zeilen[:50]
    ziel = tmp_path / "tab.csv"
    assert IMP.importiere(_excel(tmp_path / "t.xlsx", zeilen), ziel) == 1
    assert not ziel.exists()


# ---------------------------------------------------------------- Oberfläche
def _app(monkeypatch, tabelle):
    monkeypatch.setenv("KLIMADATEN_AUTO", "0")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("APP_PASSWORT", raising=False)
    monkeypatch.setattr(KP, "normtabelle", lambda: tabelle)
    at = AppTest.from_file(str(WURZEL / "app_v2.py"), default_timeout=60).run()
    at.session_state.v2_seite = "gebaeude"
    at.run()
    assert not at.exception
    return at


def _ort(at):
    return next(t for t in at.text_input if t.label == "PLZ oder Ort")


def test_oberflaeche_plz_mit_offizieller_tabelle(monkeypatch):
    at = _app(monkeypatch, TAB)
    p = at.session_state.v2_projekt
    assert p.einstellungen.norm_aussen == -12.4 and p.klima_quelle == "DIN/TS 12831-1"  # Start: Nürtingen
    _ort(at).set_value("80331").run()
    p = at.session_state.v2_projekt
    assert (p.plz, p.ort, p.einstellungen.norm_aussen) == ("80331", "80331 München", -14.6)
    _ort(at).set_value("72631").run()
    assert at.session_state.v2_projekt.einstellungen.norm_aussen == -12.4
    assert "Nachbar-PLZ 72622" in at.session_state.v2_projekt.klima_quelle


def test_oberflaeche_mehrdeutig_unbekannt_manuell(monkeypatch):
    at = _app(monkeypatch, {})
    _ort(at).set_value("Hamburg").run()
    assert at.selectbox and at.session_state.v2_projekt.plz == "72622"  # erst nach Auswahl übernehmen
    at.selectbox[0].set_value(KP.verzeichnis()["20095"]).run()
    assert at.session_state.v2_projekt.plz == "20095"
    _ort(at).set_value("99999").run()
    assert at.error and at.session_state.v2_projekt.plz == "20095"
    at.toggle[0].set_value(True).run()
    feld = next(n for n in at.number_input if n.label == "Norm-Außentemperatur")
    feld.set_value(-13.5).run()
    p = at.session_state.v2_projekt
    assert p.einstellungen.norm_aussen == -13.5 and p.norm_aussen_manuell and p.klima_quelle == "manuell eingegeben"
    at.toggle[0].set_value(False).run()
    p = at.session_state.v2_projekt
    assert not p.norm_aussen_manuell and p.klima_quelle.startswith("Standardwert")


# ---------------------------------------------------------------- BWP-Klimakarte (simuliert)
from splitklima import klimadaten as KD  # noqa: E402

SEITE = ('<html><script>var bwpClimatezones_Info = "\\/werkzeuge\\/klimakarte?type=7289322&amp;'
         'tx_bwpclimatezones_map%5Baction%5D=info";\n var bwpClimatezones_Load = '
         "'/werkzeuge/klimakarte?type=7289322&amp;tx_bwpclimatezones_map%5Baction%5D=load';</script></html>")


def _svg(n: int = 1200, kaputt: bool = False) -> str:
    plz = sorted(KP.verzeichnis())[:n]
    flaechen = []
    for i, p in enumerate(plz):
        dot = "15.0" if kaputt and i == 3 else f"-{10 + i % 50 / 10:.1f}"
        flaechen.append(f'<polygon points="1,2 3,4" zip="{p}" place="Ort &amp; Co {i}" dot="{dot}" aat="9.{i % 9}" '
                        f'alt="{200 + i}" zone="{1 + i % 15}" dotcolor="#fff"/>')
    flaechen.append(flaechen[0].replace('points="1,2 3,4"', 'points="9,9 8,8"'))  # PLZ aus zwei Flächen
    return "\n".join(flaechen)


def _get(svg: str):
    def get(url, timeout):
        if url == KD.BWP_KARTE_URL:
            return SEITE
        if "action%5D=info" in url:
            return '{"count": "1201"}'
        assert url == "https://www.waermepumpe.de/werkzeuge/klimakarte?type=7289322&tx_bwpclimatezones_map%5Baction%5D=load"
        return svg
    return get


def test_bwp_adressen_aus_seite():
    q = KD.bwp_datenquellen(SEITE)
    assert q["Load"].endswith("type=7289322&tx_bwpclimatezones_map%5Baction%5D=load")
    assert q["Info"].startswith("https://www.waermepumpe.de/werkzeuge/klimakarte?")


def test_bwp_laden_ok(tmp_path):
    ziel = tmp_path / "tab.csv"
    ok, meldungen = KD.von_bwp_laden(ziel, get=_get(_svg()))
    assert ok, meldungen
    tab = KP.lade_normtabelle(ziel)
    erste = sorted(KP.verzeichnis())[0]
    assert len(tab) == 1200 and tab[erste] == (-10.0, 9.0)
    zeile = next(z for z in KP._zeilen_normtabelle(ziel) if z["plz"] == erste)
    assert zeile["ort"] == "Ort & Co 0" and zeile["hoehe"] == "200" and zeile["klimazone"] == "1"
    assert zeile["quelle"].startswith("BWP-Klimakarte (DIN/TS 12831-1)")


def test_bwp_maskierte_antwort(tmp_path):
    svg = _svg().replace('"', '\\"')  # z. B. als JSON-String ausgeliefert
    assert KD.von_bwp_laden(tmp_path / "t.csv", get=_get(svg))[0]


def test_bwp_fehler_lassen_tabelle_unveraendert(tmp_path):
    ziel = tmp_path / "tab.csv"
    ziel.write_text("plz;theta_e;theta_m\n72622;-12.4;9.1\n", encoding="utf-8")

    def offline(url, timeout):
        raise OSError("Netzwerk nicht erreichbar")

    for get in (offline, _get(_svg(kaputt=True)), _get(_svg(n=20)), lambda u, t: "<html>umgebaut</html>"):
        ok, meldungen = KD.von_bwp_laden(ziel, get=get)
        assert not ok and meldungen
        assert KP.lade_normtabelle(ziel) == {"72622": (-12.4, 9.1)}


def test_export_der_klimakarte_als_csv(tmp_path):
    """Format des Konsolen-Exports: PLZ;Ort;Norm-Außentemperatur;Jahresmitteltemperatur;Höhe;Klimazone"""
    quelle = tmp_path / "bwp_klimadaten_plz.csv"
    zeilen = ["PLZ;Ort;Norm-Außentemperatur;Jahresmitteltemperatur;Höhe;Klimazone"]
    zeilen += [f"{p};Ort {i};-12.{i % 10};9.1;{300 + i};{1 + i % 15}"
               for i, p in enumerate(sorted(KP.verzeichnis())[:1500])]
    quelle.write_text("﻿" + "\n".join(zeilen), encoding="utf-8")
    ok, _ = KD.aus_datei(quelle, tmp_path / "tab.csv")
    assert ok and len(KP.lade_normtabelle(tmp_path / "tab.csv")) == 1500


def test_oberflaeche_laden_knopf(monkeypatch):
    import ui_v2

    tabelle = {}
    monkeypatch.setenv("KLIMADATEN_AUTO", "0")
    monkeypatch.setattr(KD, "von_bwp_laden", lambda timeout=45: (tabelle.update(TAB), (True, ["Test"]))[1])
    ui_v2.klimadaten_start.clear()
    at = _app(monkeypatch, tabelle)
    assert at.session_state.v2_projekt.klima_quelle.startswith("Richtwert")
    next(b for b in at.button if b.label == "BWP-Klimakarte laden").click().run()
    assert not at.exception
    p = at.session_state.v2_projekt
    assert p.einstellungen.norm_aussen == -12.4 and p.klima_quelle == "DIN/TS 12831-1"
    ui_v2.klimadaten_start.clear()
