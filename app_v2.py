"""BOSCH Climate Split-Klima-Konfigurator – Version 2 (Gesamtsortiment, geführte Konfiguration).

Start:  streamlit run app_v2.py
Läuft parallel zur Version 1 (app.py); Rechenkern und KI-Planerkennung sind dieselben.
"""

from __future__ import annotations

import hmac
import os

import streamlit as st

from splitklima import parameter as P
from splitklima.v2.katalog import standard as katalog_standard
from ui_v2 import app_v2

st.set_page_config(page_title="BOSCH Climate Split-Klima Konfigurator 2", page_icon="❄️", layout="wide")


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
    st.markdown("### 🔒 BOSCH Climate Split-Klima Konfigurator")
    eingabe = st.text_input("Passwort", type="password")
    if eingabe:
        if hmac.compare_digest(eingabe, str(_passwort)):
            st.session_state.angemeldet = True
            st.rerun()
        st.error("Passwort falsch.")
    st.stop()

KATALOG = katalog_standard()
st.markdown(f'<div class="marke"><b>BOSCH</b> <span>Climate</span> · Split-Klima Konfigurator'
            f'<span class="v2-badge">Version 2 · Testumgebung</span></div>'
            f'<div style="color:#5c6773;font-size:.8rem;margin-bottom:.6rem">Gesamtsortiment {KATALOG.quelle} · '
            f'Rechenkern {P.TOOL_VERSION}</div>', unsafe_allow_html=True)
app_v2(KATALOG)
