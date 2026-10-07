"""Projekt-, Einstellungs- und Raummodell.

Interne Schlüsselwerte (z. B. ``mid``, ``corner``, ``saddle_south``) sind
identisch mit v6.9.1, damit Projekt-JSON-Dateien kompatibel bleiben.
"""

from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from .parameter import MODE_WALLS

Ausrichtung = Literal["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
Raumart = Literal["Wohnzimmer", "Schlafzimmer", "Büro", "Küche", "Kinderzimmer", "Badezimmer",
                  "Werkstatt", "Halle / Lager", "Verkaufsraum"]  # die letzten drei: Version 2 (Gewerbe)
Lage = Literal["inside", "outside", "corner", "three", "attic", "attic_corner", "basement"]
Dachform = Literal["flat", "saddle_south", "saddle_north", "saddle_eastwest"]
Vertikal = Literal[
    "between_heated", "above_heated", "over_cellar", "over_unheated",
    "over_outdoor", "ground", "under_unheated_roof",
]


class Wand(BaseModel):
    ausrichtung: Ausrichtung = "S"
    laenge: float = 4.0  # m
    fenster: float = 0.0  # Fensterfläche m²


class Fenstergruppe(BaseModel):
    ausrichtung: Ausrichtung = "S"
    flaeche: float = 1.5  # m²
    dachfenster: bool = False


class Raum(BaseModel):
    name: str = "Wohnzimmer"
    geschoss: str = ""  # z. B. EG, OG, DG – nur für Anlagenvorschlag/Anzeige
    raumart: Raumart = "Wohnzimmer"
    flaeche: float = 22.0
    hoehe: float = 2.5
    lage: Lage = "corner"
    waende: list[Wand] = Field(
        default_factory=lambda: [Wand(ausrichtung="S", laenge=4, fenster=3),
                                 Wand(ausrichtung="W", laenge=5, fenster=1)]
    )
    dach: bool = False
    dachform: Dachform = "flat"
    dachflaeche: float = 0.0  # 0 = Raumfläche
    vertikal: Vertikal = "between_heated"
    baualter: str = ""  # "" = aus Dämmstandard ableiten
    speicher: Literal["light", "mid", "heavy"] = "mid"
    daemmung: Literal["none", "facade", "core", "interior"] = "none"
    fenstergruppen: list[Fenstergruppe] = Field(default_factory=list)
    ig_bauart: str = "auto"
    ig_id: str | None = None
    ig_manuell: bool = False
    farbe: str = ""  # Version 2: Farbwunsch Inneneinheit ("" = keine Präferenz)

    def setze_lage(self, lage: Lage) -> None:
        """Wie ``setMode`` in v6.9.1: passt Dach, vertikale Lage und Wandanzahl an."""
        self.lage = lage
        self.dach = lage in ("attic", "attic_corner")
        if lage == "basement":
            self.vertikal = "over_cellar"
        if self.dach:
            self.vertikal = "above_heated"
        n = MODE_WALLS[lage]
        vorschlag = ["S", "W", "O"]
        while len(self.waende) < n:
            i = len(self.waende)
            self.waende.append(Wand(ausrichtung=vorschlag[i] if i < 3 else "N", laenge=4, fenster=0))
        del self.waende[n:]


class Einstellungen(BaseModel):
    systemart: Literal["auto", "single", "multi"] = "auto"
    betriebsart: Literal["both", "cool", "heat"] = "both"
    daemmstandard: Literal["old", "mid", "new"] = "mid"
    verglasung: Literal["single", "double", "triple"] = "double"
    sonnenschutz: Literal["1", "0.8", "0.55", "0.45"] = "1"
    norm_aussen: float = -12.0  # °C
    sommer: float = 33.0  # °C
    kuehlbetrieb_h: int = 12
    gleichzeitigkeit: float = 1.0
    waermebruecken: Literal["none", "standard", "high"] = "standard"
    aufheizreserve: Literal["none", "standard", "high"] = "none"
    soll_kuehlen: float = 24.0
    soll_heizen: float = 20.0

    # Plausibilitätsgrenzen wie v6.9.1 (außerhalb → Standardwert)
    @property
    def soll_kuehlen_wirksam(self) -> float:
        return self.soll_kuehlen if 18 <= self.soll_kuehlen <= 28 else 24.0

    @property
    def soll_heizen_wirksam(self) -> float:
        return self.soll_heizen if 16 <= self.soll_heizen <= 26 else 20.0

    @property
    def gleichzeitigkeit_wirksam(self) -> float:
        return self.gleichzeitigkeit if 0 < self.gleichzeitigkeit <= 1 else 1.0


def neue_config_id() -> str:
    d = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"SKK-{d}-{secrets.token_hex(3).upper()}"


class Projekt(BaseModel):
    name: str = "Musterprojekt"
    ort: str = "72622 Nürtingen"
    plz: str = "72622"
    bearbeiter: str = ""
    datum: date = Field(default_factory=date.today)
    config_id: str = Field(default_factory=neue_config_id)
    expertenmodus: bool = False
    einstellungen: Einstellungen = Field(default_factory=Einstellungen)
    raeume: list[Raum] = Field(default_factory=lambda: [Raum()])
    gewaehltes_system: str | None = None
    validierungsfall: str = ""
    # Assistent
    systemwunsch: Literal["auto", "single", "multi"] = "auto"
    baujahr: int | None = None
    # Version 2: Herkunft der Norm-Außentemperatur (DIN/TS 12831-1, Nachbar-PLZ, Richtwert, manuell)
    klima_quelle: str = ""
    norm_aussen_manuell: bool = False
    geraetelinie: str = ""  # Version 2: Wunsch-Gerätelinie, z. B. "7000i" ("" = wirtschaftlichste)
    aufstellung: Literal["", "wand", "boden", "flachdach"] = ""  # Version 2: Aufstellort der Außeneinheit(en)
    # Version 2: Zubehör und Montagematerial
    leitungslaenge: float = 5.0  # m Kältemittelleitung je Innengerät
    app_steuerung: bool = False  # WLAN-Gateways, wo nicht integriert
    boerdelfrei: bool = False  # SAE-Klemmringverschraubungen statt Bördeln
    kondensatpumpe: bool = False  # Kondensat ohne natürliches Gefälle
    zubehoer_mengen: dict[str, int] = Field(default_factory=dict)  # manuelle Mengen je Bestell-Nr.
