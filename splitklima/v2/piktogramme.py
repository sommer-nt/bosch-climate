"""Eigene Linien-Piktogramme (SVG) für die Auswahlkarten der Version 2.

Bewusst eigene Zeichnungen im schlichten Linienstil – keine Kopie fremder Piktogramme oder Logos.
Alle Symbole: viewBox 0 0 64 64, Linienfarbe über ``currentColor``.
"""

from __future__ import annotations

_KOPF = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{g}" height="{g}" fill="none" '
         'stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">')

# Bausteine
_AUSSEN = '<rect x="{x}" y="{y}" width="20" height="16" rx="2"/><circle cx="{cx}" cy="{cy}" r="5"/>'
_INNEN = '<rect x="{x}" y="{y}" width="18" height="7" rx="2.5"/><path d="M{x2} {y2}h12"/>'


def _aussen(x: float, y: float) -> str:
    return _AUSSEN.format(x=x, y=y, cx=x + 8, cy=y + 8)


def _innen(x: float, y: float) -> str:
    return _INNEN.format(x=x, y=y, x2=x + 3, y2=y + 5)


_SCHNEE = ('<path d="M{x} {y1}v20M{x1} {ym}h20M{a1} {b1}l14 14M{a2} {b1}l-14 14"/>'
           '<path d="M{x} {y1}l-3 3M{x} {y1}l3 3M{x} {y2}l-3-3M{x} {y2}l3-3"/>')


def _schnee(cx: float, cy: float) -> str:
    return _SCHNEE.format(x=cx, y1=cy - 10, y2=cy + 10, x1=cx - 10, ym=cy, a1=cx - 7, b1=cy - 7, a2=cx + 7)


def _sonne(cx: float, cy: float) -> str:
    strahlen = "".join(
        f'<path d="M{cx + dx * 9:.1f} {cy + dy * 9:.1f}L{cx + dx * 13:.1f} {cy + dy * 13:.1f}"/>'
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (0.71, 0.71), (-0.71, 0.71), (0.71, -0.71), (-0.71, -0.71)))
    return f'<circle cx="{cx}" cy="{cy}" r="5.5"/>{strahlen}'


SYMBOLE: dict[str, str] = {
    # ---------------------------------------------------------- System
    "multi": _aussen(6, 40) + '<path d="M26 48h8M34 48V12M34 12h6M34 30h6M34 48h6"/>'
             + _innen(40, 8) + _innen(40, 26) + _innen(40, 44),
    "single": _aussen(6, 40) + '<path d="M26 48h10V20h4"/>' + _innen(40, 16),
    "auto": '<path d="M32 8v48M14 56h36M12 18h40"/><path d="M12 18l-7 16h14zM52 18l-7 16h14z"/>'
            '<path d="M5 34a7 4 0 0 0 14 0M45 34a7 4 0 0 0 14 0"/><circle cx="32" cy="8" r="2"/>',
    # ---------------------------------------------------------- Betriebsart
    "both": _schnee(20, 32) + _sonne(46, 32),
    "cool": f'<g transform="translate(32 32) scale(1.7) translate(-32 -32)" stroke-width="1.5">{_schnee(32, 32)}</g>',
    "heat": f'<g transform="translate(32 32) scale(1.6) translate(-32 -32)" stroke-width="1.6">{_sonne(32, 32)}</g>',
    # ---------------------------------------------------------- Raumart
    "Wohnzimmer": '<path d="M10 30v-6a4 4 0 0 1 4-4h36a4 4 0 0 1 4 4v6"/>'
                  '<path d="M8 30h8v8h32v-8h8v14H8z"/><path d="M12 44v5M52 44v5M16 38h32"/>',
    "Schlafzimmer": '<path d="M8 18v32M56 36v14M8 44h48M8 36h48v8"/><rect x="12" y="26" width="12" height="10" rx="3"/>'
                    '<path d="M28 36v-6a3 3 0 0 1 3-3h21a4 4 0 0 1 4 4v5"/>',
    "Büro": '<rect x="14" y="10" width="36" height="24" rx="2"/><path d="M28 34v8M36 34v8M24 42h16"/>'
            '<path d="M6 48h52M10 48v8M54 48v8"/>',
    "Küche": '<path d="M14 26h36v22a6 6 0 0 1-6 6H20a6 6 0 0 1-6-6z"/><path d="M8 30h6M50 30h6M12 26h40"/>'
             '<path d="M24 18c0-4 4-4 4-8M32 18c0-4 4-4 4-8M40 18c0-4 4-4 4-8"/>',
    "Kinderzimmer": '<circle cx="32" cy="36" r="14"/><circle cx="20" cy="18" r="6"/><circle cx="44" cy="18" r="6"/>'
                    '<circle cx="27" cy="33" r="1.5"/><circle cx="37" cy="33" r="1.5"/>'
                    '<path d="M28 41a6 4 0 0 0 8 0"/>',
    "Badezimmer": '<path d="M6 32h52v6a12 12 0 0 1-12 12H18A12 12 0 0 1 6 38z"/><path d="M18 50l-3 6M46 50l3 6"/>'
                  '<path d="M14 32V14a5 5 0 0 1 10 0"/><path d="M21 18h6"/>',
    "Werkstatt": '<path d="M8 54h48M12 54V30l20-12 20 12v24"/><path d="M24 54V40h16v14"/>'
                 '<path d="M44 12l8 8-4 4-8-8z"/><path d="M40 16L28 28"/><circle cx="26" cy="30" r="3"/>',
    "Halle / Lager": '<path d="M6 54h52M8 54V24L32 10l24 14v30"/><path d="M16 54V32h32v22"/>'
                     '<path d="M16 39h32M16 46h32M24 32v22M40 32v22"/>',
    "Verkaufsraum": '<path d="M10 26h44v28H10z"/><path d="M8 26l4-12h40l4 12"/>'
                    '<path d="M8 26c0 4 6 4 6 0c0 4 6 4 6 0c0 4 6 4 6 0c0 4 6 4 6 0c0 4 6 4 6 0c0 4 6 4 6 0c0 4 6 4 6 0'
                    'c0 4 6 4 6 0"/><path d="M18 54V38h10v16M34 38h12v8H34z"/>',
    # ---------------------------------------------------------- Bauart
    "Wandgerät": '<path d="M8 10v44"/><rect x="12" y="20" width="44" height="16" rx="4"/>'
                 '<path d="M18 30h32M22 42l-2 6M34 42v6M46 42l2 6"/>',
    "Deckenkassette": '<path d="M6 12h52"/><rect x="14" y="16" width="36" height="10" rx="2"/>'
                      '<path d="M20 26l-6 10M44 26l6 10M28 26v14M36 26v14"/><path d="M14 52h36" stroke-dasharray="3 4"/>',
    "Konsole": '<path d="M6 56h52"/><rect x="16" y="24" width="32" height="30" rx="3"/>'
               '<path d="M22 32h20M22 38h20M22 44h20M24 18l-2-6M32 18v-6M40 18l2-6"/>',
    "Truhe/Decke": '<path d="M6 10h52"/><path d="M14 10v4M50 10v4"/><rect x="10" y="14" width="44" height="12" rx="3"/>'
                   '<path d="M16 26l-4 8M48 26l4 8M32 26v8"/><path d="M6 56h52" stroke-dasharray="3 4"/>',
    "egal": '<rect x="10" y="12" width="20" height="10" rx="3"/><rect x="34" y="12" width="20" height="10" rx="3"/>'
            '<rect x="10" y="30" width="20" height="22" rx="3"/><path d="M38 40l5 5 9-11"/>',
    # ---------------------------------------------------------- Lage (Grundriss, Außenwände fett)
    "inside": '<rect x="14" y="14" width="36" height="36" stroke-dasharray="4 4"/><circle cx="32" cy="32" r="3"/>',
    "outside": '<rect x="14" y="14" width="36" height="36" stroke-dasharray="4 4"/><path d="M12 50h40" stroke-width="6"/>',
    "corner": '<rect x="14" y="14" width="36" height="36" stroke-dasharray="4 4"/>'
              '<path d="M12 14v38h40" stroke-width="6"/>',
    "three": '<rect x="14" y="14" width="36" height="36" stroke-dasharray="4 4"/>'
             '<path d="M12 12v40h40V12" stroke-width="6"/>',
    "attic": '<path d="M8 50h48M10 50L32 14l22 36" stroke-dasharray="4 4"/><path d="M32 14l22 36" stroke-width="6"/>',
    "attic_corner": '<path d="M8 50h48" stroke-dasharray="4 4"/><path d="M10 50L32 14l22 36" stroke-width="6"/>',
    "basement": '<path d="M8 28h48" stroke-width="2"/><rect x="14" y="30" width="36" height="22" stroke-dasharray="4 4"/>'
                '<path d="M8 30h48" stroke-width="6"/><path d="M14 12h36v16" />',
    # ---------------------------------------------------------- Dach
    "dach_ja": '<path d="M6 34L32 12l26 22"/><path d="M14 28v24h36V28"/><rect x="38" y="20" width="8" height="6"/>',
    "dach_nein": '<rect x="12" y="10" width="40" height="16"/><rect x="12" y="30" width="40" height="22" stroke-width="3.5"/>',
    # ---------------------------------------------------------- Sonnenschutz
    "0.45": '<rect x="12" y="10" width="40" height="44" rx="2"/><path d="M12 18h40M12 24h40M12 30h40M12 36h40"/>',
    "0.8": '<rect x="12" y="10" width="40" height="44" rx="2"/><path d="M16 10c-2 14 2 30 0 44M48 10c2 14-2 30 0 44"/>'
           '<path d="M22 10c-3 12 0 26-2 44M42 10c3 12 0 26 2 44"/>',
    "1": '<rect x="12" y="10" width="40" height="44" rx="2"/><path d="M32 10v44M12 32h40"/>' + _sonne(46, 18),
    # ---------------------------------------------------------- Verglasung
    "double": '<rect x="16" y="10" width="32" height="44" rx="2"/><path d="M28 14v36M36 14v36"/>',
    "triple": '<rect x="14" y="10" width="36" height="44" rx="2"/><path d="M24 14v36M32 14v36M40 14v36"/>',
    "single_glas": '<rect x="18" y="10" width="28" height="44" rx="2"/><path d="M32 14v36"/>',
    # ---------------------------------------------------------- Sonstiges
    "ki": '<path d="M10 8h28l10 10v38H10z"/><path d="M38 8v10h10"/><path d="M16 26h12v12H16zM28 32h12M34 26v18"/>'
          '<path d="M50 34l2 5 5 2-5 2-2 5-2-5-5-2 5-2z" fill="currentColor"/>',
    "haus": '<path d="M8 30L32 10l24 20"/><path d="M14 26v28h36V26"/><rect x="27" y="38" width="10" height="16"/>',
    "raum": '<rect x="10" y="10" width="44" height="44" rx="2"/><path d="M10 34h18M40 10v16"/>',
    "ergebnis": '<circle cx="32" cy="32" r="22"/><path d="M22 33l7 7 14-16"/>',
}


def svg(name: str, groesse: int = 56) -> str:
    """SVG-Markup eines Piktogramms (leerer String, wenn unbekannt)."""
    inhalt = SYMBOLE.get(name)
    return f"{_KOPF.format(g=groesse)}{inhalt}</svg>" if inhalt else ""
