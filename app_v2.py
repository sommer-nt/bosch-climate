"""BOSCH Climate Split-Klima-Konfigurator – Version 2 (Gesamtsortiment, geführte Konfiguration).

Start:  streamlit run app_v2.py
Läuft parallel zur Version 1 (app.py); Rechenkern und KI-Planerkennung sind dieselben.
"""

from __future__ import annotations

import hmac
import os

import streamlit as st

from splitklima import parameter as P
from splitklima.sprache import SITZUNG_SCHLUESSEL, T
from splitklima.v2.katalog import standard as katalog_standard
from ui_v2 import app_v2, sprache_umschalter, sprache_vorbereiten

sprache_vorbereiten()  # Deutsch/Englisch aus Sitzung bzw. ?lang=en
st.set_page_config(page_title=T("BOSCH Climate Split-Klima Konfigurator 2"), page_icon="❄️", layout="wide")


def _secret(name: str) -> str | None:
    """Umgebungsvariable (Docker) oder Streamlit-Secret – unabhängig von Groß-/Kleinschreibung."""
    if os.environ.get(name, "").strip():
        return os.environ[name].strip()
    try:
        eintraege = st.secrets.to_dict()
    except Exception:  # keine Secrets vorhanden
        return None
    stapel = [eintraege]
    while stapel:
        d = stapel.pop()
        for key, wert in d.items():
            if isinstance(wert, dict):
                stapel.append(wert)
            elif key.strip().upper() == name and str(wert).strip():
                return str(wert).strip().strip('"').strip("“”„")
    return None


if not os.environ.get("ANTHROPIC_API_KEY", "").strip() and _secret("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = _secret("ANTHROPIC_API_KEY")

_passwort = _secret("APP_PASSWORT")
if _passwort and not st.session_state.get("angemeldet"):
    kopf, schalter = st.columns([5, 1], vertical_alignment="center")
    kopf.markdown("### 🔒 BOSCH Climate " + T("Split-Klima Konfigurator"))
    with schalter:
        sprache_umschalter()
    eingabe = st.text_input(T("Passwort"), type="password")
    if eingabe:
        if hmac.compare_digest(eingabe, str(_passwort)):
            st.session_state.angemeldet = True
            st.rerun()
        st.error(T("Passwort falsch."))
    st.stop()

KATALOG = katalog_standard()
kopf, schalter = st.columns([5, 1], vertical_alignment="center")
kopf.markdown(f'<div class="marke"><b>BOSCH</b> <span>Climate</span> · {T("Split-Klima Konfigurator")}'
              f'<span class="v2-badge">{T("Version 2 · Testumgebung")}</span></div>'
              f'<div style="color:#5c6773;font-size:.8rem;margin-bottom:.6rem">'
              f'{T("Gesamtsortiment {q} · Rechenkern {v}", q=T(KATALOG.quelle), v=P.TOOL_VERSION)}</div>',
              unsafe_allow_html=True)
with schalter:
    sprache_umschalter()
app_v2(KATALOG)
