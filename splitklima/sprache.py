"""Sprache der Oberfläche (Version 2): Deutsch (Standard) oder Englisch.

Texte stehen im Quelltext auf Deutsch und werden über ``T("…")`` übersetzt – fehlt eine Übersetzung,
bleibt der deutsche Text stehen. Platzhalter wie ``{n}`` werden nach der Übersetzung eingesetzt.
``N_("…")`` markiert Texte in Konstanten (Übersetzung erst bei der Anzeige mit ``T(wert)``).

Fachlich bleibt alles deutsch: PLZ, Orte, Klimadaten (DIN/TS 12831-1), Normen, Katalog, Preise in Euro.
Die Sprache kommt aus der Streamlit-Sitzung (``v2_sprache``); Tests und Berichte können sie mit
``sprache("en")`` erzwingen. Ohne beides (z. B. Version 1) gilt Deutsch.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

SPRACHEN = {"de": "Deutsch", "en": "English"}
SITZUNG_SCHLUESSEL = "v2_sprache"
_ERZWUNGEN: ContextVar[str | None] = ContextVar("sprache", default=None)


def aktuell() -> str:
    s = _ERZWUNGEN.get()
    if s:
        return s
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        if get_script_run_ctx(suppress_warning=True) is None:
            return "de"
        import streamlit as st

        s = st.session_state.get(SITZUNG_SCHLUESSEL, "de")
    except Exception:  # noqa: BLE001 – ohne Streamlit-Laufzeit
        return "de"
    return s if s in SPRACHEN else "de"


def englisch() -> bool:
    return aktuell() == "en"


@contextmanager
def sprache(s: str):
    """Sprache für einen Block erzwingen (Tests, Berichte)."""
    marke = _ERZWUNGEN.set(s)
    try:
        yield
    finally:
        _ERZWUNGEN.reset(marke)


def N_(text: str) -> str:
    """Nur Markierung: Text wird erst bei der Anzeige mit ``T`` übersetzt."""
    return text


def T(text: str, **werte) -> str:
    """Text in der aktuellen Sprache; ``werte`` füllen Platzhalter ``{name}``."""
    if text and aktuell() == "en":
        from .sprache_en import EN

        text = EN.get(text, text)
    return text.format(**werte) if werte else text


def zahl(x: float, nachkomma: int = 1) -> str:
    """Zahl mit Dezimalkomma (Deutsch) bzw. -punkt (Englisch)."""
    s = f"{x:.{nachkomma}f}"
    return s if englisch() else s.replace(".", ",")


def euro(betrag: float | None, cent: bool = False) -> str:
    """Eurobetrag: Deutsch „1.234 €“, Englisch „€1,234“."""
    if betrag is None:
        return T("auf Anfrage")
    s = f"{betrag:,.{2 if cent else 0}f}"
    if englisch():
        return f"€{s}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") + " €"


_QUELLE_EN = [  # Herkunft der Norm-Außentemperatur (klima_plz.py) → Englisch
    (r"^Richtwert Klimaregion (.+) \(v6\.9\.1\) – bitte prüfen$",
     r"Guide value for climate region \1 (v6.9.1) – please check"),
    (r"^Standardwert \(keine ortsgenaue Angabe\) – bitte prüfen$",
     "Default value (no location-specific data) – please check"),
    (r"^DIN/TS 12831-1, Wert der Nachbar-PLZ (\d+) \((.+) km\)$",
     r"DIN/TS 12831-1, value of neighbouring postcode \1 (\2 km)"),
]


def klimaquelle(text: str) -> str:
    """Herkunft der Norm-Außentemperatur anzeigen – Ortsnamen und Normbezug bleiben deutsch."""
    if not text or not englisch():
        return text
    import re

    for muster, ersatz in _QUELLE_EN:
        if re.match(muster, text):
            return re.sub(muster, ersatz, text)
    return T(text)
