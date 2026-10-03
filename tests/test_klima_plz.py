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
