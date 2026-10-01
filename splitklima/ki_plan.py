"""KI-Planerkennung: Architektenpläne (PDF/Bild) → Räume für den Konfigurator.

Nutzt Claude (Vision + strukturierte Ausgabe). Benötigt ANTHROPIC_API_KEY
in der Umgebung (oder ein über ``ant auth login`` angemeldetes Profil).
Die erkannten Räume sind ein Vorschlag und müssen vom Nutzer geprüft werden.
"""

from __future__ import annotations

import base64
from typing import Literal

from pydantic import BaseModel, Field

from .modell import Fenstergruppe, Raum, Wand

MODELL = "claude-opus-5-5"
BILD_TYPEN = {"image/png", "image/jpeg", "image/webp", "image/gif"}

Ori = Literal["N", "NO", "O", "SO", "S", "SW", "W", "NW"]


class KiWand(BaseModel):
    ausrichtung: Ori = Field(description="Himmelsrichtung, in die die Außenwand zeigt")
    laenge_m: float = Field(description="Länge der Außenwand im Raum in Metern")
    fensterflaeche_m2: float = Field(description="Summe der Fensterflächen (inkl. Fenstertüren) in dieser Wand")


class KiRaum(BaseModel):
    name: str = Field(description="Raumbezeichnung wie im Plan")
    geschoss: str = Field(description="z. B. KG, EG, OG, DG")
    raumart: Literal["Wohnzimmer", "Schlafzimmer", "Büro", "Küche", "Kinderzimmer", "Badezimmer"] = Field(
        description="Nächstliegende Raumart (Essen/Wohnen → Wohnzimmer, Arbeiten → Büro, Gäste → Schlafzimmer)"
    )
    flaeche_m2: float
    raumhoehe_m: float = Field(description="Lichte Raumhöhe; 2.5 wenn unbekannt")
    aussenwaende: list[KiWand]
    unter_dach: bool = Field(description="True, wenn die Dachfläche direkt über dem Raum liegt (ausgebautes DG)")
    dachform: Literal["flat", "saddle_south", "saddle_north", "saddle_eastwest"] = Field(
        description="Nur bei unter_dach relevant: Flachdach bzw. Satteldach-Seite des Raums"
    )
    dachfenster_m2: float = Field(description="Fläche der Dachflächenfenster, sonst 0")
    ueber_unbeheizt: Literal["nein", "keller", "erdreich", "aussenluft"] = Field(
        description="Was liegt unter dem Raum, falls nicht beheizt"
    )
    unter_unbeheiztem_dachraum: bool = Field(description="True, wenn darüber ein unbeheizter Dachboden liegt")


class KiAufstellort(BaseModel):
    ort: str = Field(description="z. B. 'Terrasse Südseite', 'Flachdach Garage', 'Balkon OG West'")
    begruendung: str = Field(description="Warum geeignet (Zugänglichkeit, Leitungsweg, Abstand zu Nachbarn)")


class KiPlanAnalyse(BaseModel):
    raeume: list[KiRaum]
    baujahr: int | None = Field(description="Baujahr bzw. Planungsjahr laut Plankopf, sonst null")
    nordrichtung: str = Field(description="Wie die Nordrichtung bestimmt wurde")
    aufstellorte_aussengeraet: list[KiAufstellort] = Field(
        description="Bis zu 3 im Plan erkennbare, geeignete Aufstellorte für Außengeräte")
    hinweise: list[str] = Field(description="Annahmen und Unsicherheiten, die der Nutzer prüfen sollte")


SYSTEM_PROMPT = """\
Du bist ein erfahrener TGA-Planer (Kälte/Klima) und liest Architektenpläne \
(Grundrisse, Schnitte, Ansichten) deutscher Wohngebäude, um Split-Klimageräte \
auszulegen.

Erfasse alle Aufenthaltsräume (Wohnen, Schlafen, Kind, Arbeiten, Küche, Bad). \
Flure, Abstellräume, Technik und Treppenhäuser lässt du weg.

- Fläche: eingetragene m²-Angabe übernehmen, sonst aus Maßketten/Maßstab berechnen.
- Nordrichtung über den Nordpfeil; Angaben des Nutzers haben Vorrang. \
Ausrichtungen sind absolute Himmelsrichtungen der Fassade.
- Je Außenwand: Länge im Raum und Summe der Fensterflächen. Fensterhöhe aus \
Ansicht/Schnitt; ohne Angabe 1,35 m (Fenster) bzw. 2,10 m (Fenstertür).
- Baujahr: aus dem Plankopf (Bauantrag, Planungsdatum), sonst null.
- Aufstellorte für Außengeräte: nur Orte, die im Plan erkennbar sind (Terrasse, \
Balkon, Garten, Flachdach, Fassade); kurze Leitungswege zu den Räumen und \
Abstand zu Schlafräumen/Nachbargrenze bevorzugen.
- Jede Annahme mit spürbarem Einfluss gehört als kurzer Satz in 'hinweise'.
"""


def _block(daten: bytes, media_type: str) -> dict:
    b64 = base64.standard_b64encode(daten).decode("utf-8")
    if media_type == "application/pdf":
        return {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": b64}}
    if media_type in BILD_TYPEN:
        return {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}}
    raise ValueError(f"Nicht unterstützter Dateityp: {media_type}")


class PlanFehler(RuntimeError):
    pass


def analysiere(dateien: list[tuple[bytes, str]], zusatz: str = "", client=None) -> KiPlanAnalyse:
    import anthropic

    if not dateien:
        raise ValueError("Mindestens ein Plan erforderlich.")
    client = client or anthropic.Anthropic()
    inhalt = [_block(d, mt) for d, mt in dateien]
    text = "Erfasse die Räume aus den beigefügten Plänen."
    if zusatz.strip():
        text += f"\n\nAngaben des Nutzers:\n{zusatz.strip()}"
    inhalt.append({"type": "text", "text": text})
    try:
        antwort = client.beta.messages.parse(
            model=MODELL, max_tokens=16000, system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": inhalt}],
            output_config={"effort": "high"}, output_format=KiPlanAnalyse,
            # Bei Ablehnung durch Sicherheitsfilter auf empfohlenes Ersatzmodell ausweichen
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise PlanFehler("Kein gültiger API-Schlüssel (ANTHROPIC_API_KEY).") from e
    except anthropic.RateLimitError as e:
        raise PlanFehler("Rate-Limit erreicht – bitte kurz warten.") from e
    except anthropic.BadRequestError as e:
        raise PlanFehler(f"Anfrage abgelehnt (Datei zu groß?): {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise PlanFehler("Keine Verbindung zur Claude API.") from e
    if antwort.stop_reason == "refusal":
        raise PlanFehler("Die Analyse wurde vom Modell abgelehnt.")
    if antwort.stop_reason == "max_tokens":
        raise PlanFehler("Plan zu umfangreich – bitte einzelne Geschosse hochladen.")
    if antwort.parsed_output is None:
        raise PlanFehler("Antwort konnte nicht gelesen werden.")
    return antwort.parsed_output


def in_raeume(analyse: KiPlanAnalyse) -> list[Raum]:
    """Wandelt das KI-Ergebnis in Räume des Rechenkerns um."""
    raeume = []
    for k in analyse.raeume:
        waende = [Wand(ausrichtung=w.ausrichtung, laenge=round(w.laenge_m, 2), fenster=round(w.fensterflaeche_m2, 2))
                  for w in k.aussenwaende][:3]
        n = len(waende)
        if k.unter_dach:
            lage = "attic" if n <= 1 else "attic_corner"
            waende = waende[:2] or [Wand(ausrichtung="S", laenge=4, fenster=0)]
            if lage == "attic":
                waende = waende[:1]
        elif n == 0:
            lage = "inside"
        elif k.ueber_unbeheizt == "keller" and n == 1:
            lage = "basement"
        else:
            lage = {1: "outside", 2: "corner", 3: "three"}[n]
        vertikal = {"keller": "over_cellar", "erdreich": "ground", "aussenluft": "over_outdoor"}.get(
            k.ueber_unbeheizt, "between_heated")
        if k.unter_unbeheiztem_dachraum and not k.unter_dach:
            vertikal = "under_unheated_roof"
        if k.unter_dach:
            vertikal = "above_heated"
        raeume.append(Raum(
            name=k.name.strip(), geschoss=k.geschoss.strip().upper(), raumart=k.raumart, flaeche=round(k.flaeche_m2, 1),
            hoehe=round(k.raumhoehe_m or 2.5, 2), lage=lage, waende=waende, dach=k.unter_dach,
            dachform=k.dachform, dachflaeche=0.0, vertikal=vertikal,
            fenstergruppen=([Fenstergruppe(ausrichtung="S", flaeche=round(k.dachfenster_m2, 2), dachfenster=True)]
                            if k.dachfenster_m2 > 0 else []),
        ))
    return raeume


def baualter_aus_baujahr(baujahr: int | None) -> str:
    """Ordnet ein Baujahr der Baualtersklasse (F-011) zu; "" wenn unbekannt."""
    if not baujahr:
        return ""
    for grenze, klasse in ((1957, "bis1957"), (1968, "1958-1968"), (1978, "1969-1978"),
                           (1983, "1979-1983"), (2001, "1984-2001")):
        if baujahr <= grenze:
            return klasse
    return "2002-heute"
