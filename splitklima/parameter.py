"""Berechnungsparameter (CALC-0.4) – 1:1 aus v6.9.1 übernommen.

Alle Werte sind Validierungsannahmen und fachlich freizugeben.
"""

from __future__ import annotations

TOOL_VERSION = "v6.9.1"
MODEL_VERSIONS = {
    "calculation": "CALC-0.4",
    "building": "BLD-0.1",
    "climate": "CLIM-0.1",
    "product": "PROD-0.1",
    "accessory": "ACC-0.1",
}

# Bau-/Dämmstandard → U-Wand [W/(m²K)]
USTD = {"old": {"w": 1.4}, "mid": {"w": 0.8}, "new": {"w": 0.35}}
USTD_LABEL = {"old": "Altbau", "mid": "Bestand modernisiert", "new": "Neubau / gut gedämmt"}

# Verglasung → U-Wert, g-Wert
GLAS = {"single": {"u": 5.2, "g": 0.78}, "double": {"u": 1.8, "g": 0.62}, "triple": {"u": 0.9, "g": 0.5}}
GLAS_LABEL = {"single": "Einfach", "double": "Zweifach", "triple": "Dreifach"}

# Solare Einstrahlung je Ausrichtung [W/m²]
SOL = {"N": 80, "O": 240, "S": 380, "W": 440, "NO": 130, "SO": 340, "SW": 410, "NW": 190}
SOL_DEFAULT = 250
DACHFENSTER_EINSTRAHLUNG = 430
AUSRICHTUNGEN = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]

# Sonnenschutz: Faktor Fenster (Schlüssel) und Wirkung auf Dachflächen
SONNENSCHUTZ_LABEL = {
    "1": "keine / unbekannt",
    "0.8": "Innenjalousie / Vorhang",
    "0.55": "Jalousie außen",
    "0.45": "Rollladen außen",
}
SHADE_ROOF = {"1": 1, "0.8": 1, "0.55": 0.85, "0.45": 0.8}  # Innenjalousie wirkt NICHT aufs Dach

# Solarlast Dach je Dachform [W/m²]
DACH_SOLAR = {"flat": 34, "saddle_south": 48, "saddle_north": 18, "saddle_eastwest": 34}
DACHFORM_LABEL = {
    "flat": "Flachdach",
    "saddle_south": "Satteldach Süd",
    "saddle_north": "Satteldach Nord",
    "saddle_eastwest": "Satteldach Ost/West",
}

# F-011 Baualtersklassen → U-Wand
AGE_CLASSES = {
    "bis1957": {"label": "bis 1957", "w": 1.6},
    "1958-1968": {"label": "1958–1968", "w": 1.4},
    "1969-1978": {"label": "1969–1978", "w": 1.2},
    "1979-1983": {"label": "1979–1983", "w": 0.9},
    "1984-2001": {"label": "1984–2001", "w": 0.6},
    "2002-heute": {"label": "2002 bis heute", "w": 0.35},
}

# B-010/B-015 Speichereffekt
STORAGE_CLASS = {
    "light": {"label": "leicht / Holzbau", "damp": 0.06},
    "mid": {"label": "massiv, geringe Dicke", "damp": 0.12},
    "heavy": {"label": "massiv, hohe Dicke", "damp": 0.18},
}
KUEHLBETRIEB_LABEL = {6: "bis 6 h (kurzer Betrieb)", 12: "ca. 12 h", 18: "ca. 18 h", 24: "Dauerbetrieb"}

# DIN EN 12831-1-nahe Zuschläge
WB_SURCHARGE = {
    "none": {"label": "ohne pauschalen Wärmebrückenzuschlag", "dU": 0.0},
    "standard": {"label": "pauschal ΔU_WB 0,05 W/(m²K)", "dU": 0.05},
    "high": {"label": "erhöht ΔU_WB 0,10 W/(m²K)", "dU": 0.10},
}
REHEAT_FACTOR = {
    "none": {"label": "keine Aufheizreserve", "f": 0.0},
    "standard": {"label": "Aufheizreserve +15 %", "f": 0.15},
    "high": {"label": "Aufheizreserve +30 %", "f": 0.30},
}

# F-012 nachträgliche Dämmung → resultierender U-Wand
RETROFIT = {
    "none": {"label": "keine", "u": None},
    "facade": {"label": "Fassadendämmung (U≈0,28)", "u": 0.28},
    "core": {"label": "Kerndämmung (U≈0,45)", "u": 0.45},
    "interior": {"label": "Innendämmung (U≈0,40)", "u": 0.40},
}

# Version 2: nachträgliche Fassadendämmung nach Sanierungsjahr (v1-Auswahl bleibt unverändert)
RETROFIT_ZUSATZ = {
    "facade_1990": {"label": "Fassadendämmung vor 1995, ca. 4–6 cm (U≈0,50)", "u": 0.50},
    "facade_2000": {"label": "Fassadendämmung 1995–2008, ca. 8–10 cm (U≈0,35)", "u": 0.35},
}
NACHDAEMMUNG_V2 = {
    "none": "keine",
    "facade_1990": RETROFIT_ZUSATZ["facade_1990"]["label"],
    "facade_2000": RETROFIT_ZUSATZ["facade_2000"]["label"],
    "facade": "Fassadendämmung ab 2009, ca. 12–16 cm (U≈0,28)",
    "core": RETROFIT["core"]["label"],
    "interior": RETROFIT["interior"]["label"],
}

# Vertikale Lage: U-Faktoren und Kühl-/Heiz-Gewichtung für Boden/Decke
VERTICAL = {
    "between_heated": {"floorU": 0, "floorC": 0, "floorH": 0, "ceilU": 0, "ceilC": 0, "ceilH": 0},
    "above_heated": {"floorU": 0, "floorC": 0, "floorH": 0, "ceilU": 0, "ceilC": 0, "ceilH": 0},
    "over_cellar": {"floorU": 0.65, "floorC": 0.18, "floorH": 0.45, "ceilU": 0, "ceilC": 0, "ceilH": 0},
    "over_unheated": {"floorU": 0.75, "floorC": 0.25, "floorH": 0.55, "ceilU": 0, "ceilC": 0, "ceilH": 0},
    "over_outdoor": {"floorU": 0.85, "floorC": 0.75, "floorH": 1, "ceilU": 0, "ceilC": 0, "ceilH": 0},
    "ground": {"floorU": 0.45, "floorC": 0.12, "floorH": 0.35, "ceilU": 0, "ceilC": 0, "ceilH": 0},
    "under_unheated_roof": {"floorU": 0, "floorC": 0, "floorH": 0, "ceilU": 0.55, "ceilC": 0.35, "ceilH": 0.55},
}
VERTICAL_LABEL = {
    "between_heated": "zwischen beheizten Geschossen",
    "above_heated": "über beheiztem Raum",
    "over_cellar": "über unbeheiztem Keller",
    "over_unheated": "über unbeheiztem Bereich",
    "over_outdoor": "über Außenluft / Durchfahrt",
    "ground": "erdberührt / Bodenplatte",
    "under_unheated_roof": "unter unbeheiztem Dachraum",
}

# Thermische Lage (Raummodus)
MODES = ["inside", "outside", "corner", "three", "attic", "attic_corner", "basement"]
MODE_LABEL = {
    "inside": "Innenliegend",
    "outside": "1 Außenwand",
    "corner": "2 Außenwände / Eckraum",
    "three": "3 Außenwände",
    "attic": "Dachgeschoss",
    "attic_corner": "DG-Eckraum",
    "basement": "Über Keller",
}
MODE_WALLS = {"inside": 0, "outside": 1, "corner": 2, "three": 3, "attic": 1, "attic_corner": 2, "basement": 1}

# Raumarten: Luftwechsel [1/h] und innere Grundlast [W] (+12 W/m²)
RAUMARTEN = ["Wohnzimmer", "Schlafzimmer", "Büro", "Küche", "Kinderzimmer", "Badezimmer"]
LUFTWECHSEL = {"Badezimmer": 0.7, "Küche": 0.7, "Schlafzimmer": 0.4}
LUFTWECHSEL_DEFAULT = 0.5
INTERN_W_M2 = 12
INTERN_GRUND = {"Küche": 320, "Badezimmer": 240, "Büro": 220, "Schlafzimmer": 120}
INTERN_GRUND_DEFAULT = 180

# Gewerbe (Version 2): Werkstatt, Halle/Lager, Verkaufsraum.
# VORLÄUFIGE ANNAHMEN für die überschlägige Auslegung – fachlich freizugeben.
# Wohn-Raumarten bleiben unverändert (v6.9.1), daher hier eigene Einträge.
RAUMARTEN_GEWERBE = ["Werkstatt", "Halle / Lager", "Verkaufsraum"]
LUFTWECHSEL.update({"Werkstatt": 0.5, "Halle / Lager": 0.3, "Verkaufsraum": 0.7})
INTERN_GRUND.update({"Werkstatt": 300, "Halle / Lager": 0, "Verkaufsraum": 300})
# Flächenbezogene innere Last [W/m²] (Beleuchtung, Maschinen, Personen); Standard 12 W/m²
INTERN_W_M2_RAUMART = {"Werkstatt": 20, "Halle / Lager": 6, "Verkaufsraum": 25}
GEWERBE_HINWEIS = ("Gewerbe-Raumarten: innere Lasten als überschlägige Auslegungsannahmen – Werkstatt 20 W/m² "
                   "(üblich 15–30 je nach Maschinen, Beleuchtung, Personen), Halle/Lager 6 W/m² (üblich 3–10), "
                   "Verkaufsraum 25 W/m² (üblich 20–30 je nach Personenverkehr, Beleuchtung, Schaufenstern, "
                   "Geräten). Diese Werte ersetzen keine detaillierte Kühllastberechnung nach VDI 2078 oder "
                   "DIN EN 16798. Maschinenabwärme, Tore und Hallenhöhe (Temperaturschichtung) gesondert prüfen.")

IG_BAUARTEN = ["auto", "Wandgerät", "Truhengerät", "Kassettengerät", "Kanalgerät"]

FORMELN = {
    "cooling": "Q_K = (Q_solar,Fenster + Q_solar,Dach + Q_transmission + Q_lueftung + Q_intern) - Q_speichereffekt",
    "heating": "Q_H = Q_transmission + Q_lueftung",
    "ventilation": "Q_L = 0.34 * n * V * ΔT",
    "volume": "V = A_Raum * h_Raum",
    "storage": "Q_speichereffekt = Q_brutto * Daempfung(Speicherklasse, Kuehlbetriebsdauer)",
}

HAFTUNGSHINWEISE = [
    "Heiz- und Kühllasten sind überschlägige Schätzwerte.",
    "Vereinfachte Kühllastabschätzung in Anlehnung an VDI 2078, keine vollständige VDI-2078-Fachberechnung.",
    "Vereinfachte Heizlastabschätzung in Anlehnung an DIN EN 12831-1, keine vollständige Norm-Heizlastberechnung.",
    "Die Konfiguration ersetzt keine Fachplanung.",
    "Schall-, Elektro-, Kältemittel-, Kondensat- und Genehmigungsanforderungen sind gesondert zu prüfen.",
    "Eine dargestellte Förderfähigkeit ist keine Förderzusage.",
]
HAFTUNG_LANGTEXT = (
    "Die angezeigten Heiz- und Kühllasten sind überschlägige Schätzwerte auf Basis vereinfachter "
    "Gebäude-, Klima- und Nutzungsannahmen. Die Berechnung erfolgt vereinfacht in Anlehnung an die "
    "Methodik der VDI 2078 bzw. DIN EN 12831-1, stellt jedoch keine vollständige normgerechte "
    "Fachberechnung dar. Sie ersetzt keine fachtechnische Planung oder Prüfung am Gebäude. Die "
    "endgültige Auswahl, Installation und Inbetriebnahme muss durch einen qualifizierten Fachbetrieb "
    "erfolgen. Schall-, Elektro-, Kältemittel-, Kondensat-, Brandschutz- und Genehmigungsanforderungen "
    "sind gesondert zu prüfen. Eine dargestellte Förderfähigkeit ist keine Förderzusage."
)
