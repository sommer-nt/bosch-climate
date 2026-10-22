"""Fotos von Plänen (Kamera iPad/iPhone, Webcam am PC) für die Grundriss-Erkennung aufbereiten.

Handyfotos haben 12–48 Megapixel und speichern die Drehung oft nur als EXIF-Angabe. Vor dem Senden an
die Erkennung werden sie richtig gedreht, auf eine sinnvolle Größe verkleinert (Linien und Maßzahlen
bleiben lesbar, die Datei wird klein) und im Kontrast leicht angehoben.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import io
from dataclasses import dataclass, field

from PIL import Image, ImageFilter, ImageOps

from ..sprache import T

MAX_KANTE = 2400  # px – reicht für Maßketten, spart Token und bleibt unter den Bildgrenzen der API
BILD_MIME = {"image/jpeg", "image/png", "image/webp"}
MAX_WEBCAM_BYTES = 15_000_000  # Data-URL einer Webcam-Aufnahme (4K-JPEG ≈ 2–4 MB)


class FotoFehler(ValueError):
    """Bild konnte nicht gelesen werden."""


def aufbereiten(daten: bytes, drehung: int = 0, max_kante: int = MAX_KANTE) -> bytes:
    """Foto richtig drehen (EXIF + zusätzliche Drehung im Uhrzeigersinn), verkleinern, Kontrast anheben.
    Ergebnis: JPEG-Bytes."""
    try:
        with Image.open(io.BytesIO(daten)) as roh:
            bild = ImageOps.exif_transpose(roh)
            bild = bild.convert("RGB")
    except Exception as fehler:  # noqa: BLE001 – beschädigte oder unbekannte Bilddatei
        raise FotoFehler(T("Das Foto konnte nicht gelesen werden – bitte als JPG oder PNG aufnehmen.")) from fehler
    if drehung % 360:
        bild = bild.rotate(-(drehung % 360), expand=True)  # PIL dreht gegen den Uhrzeigersinn
    bild.thumbnail((max_kante, max_kante), Image.LANCZOS)
    bild = ImageOps.autocontrast(bild, cutoff=1)  # Papier heller, Linien dunkler
    bild = bild.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))
    puffer = io.BytesIO()
    bild.save(puffer, format="JPEG", quality=88, optimize=True)
    return puffer.getvalue()


def vorschau(daten: bytes, drehung: int = 0, kante: int = 320) -> bytes:
    """Kleines Vorschaubild (JPEG) in derselben Ausrichtung wie für die Erkennung."""
    return aufbereiten(daten, drehung, max_kante=kante)


@dataclass
class WebcamFoto:
    """Aufnahme der PC-Webcam – verhält sich für die Erkennung wie eine hochgeladene Datei."""

    daten: bytes
    name: str = "webcam.jpg"
    file_id: str = field(default="")

    def __post_init__(self) -> None:
        self.file_id = self.file_id or "webcam-" + hashlib.sha1(self.daten).hexdigest()[:12]

    def getvalue(self) -> bytes:
        return self.daten


def aus_data_url(url: str) -> bytes:
    """``data:image/jpeg;base64,…`` aus dem Browser prüfen und als Bildbytes liefern."""
    if not isinstance(url, str) or len(url) > MAX_WEBCAM_BYTES:
        raise FotoFehler(T("Die Webcam-Aufnahme ist zu groß oder ungültig."))
    kopf, _, inhalt = url.partition(",")
    if not (kopf.startswith("data:image/") and kopf.endswith(";base64")) or kopf[5:-7] not in BILD_MIME:
        raise FotoFehler(T("Die Webcam-Aufnahme hat kein unterstütztes Bildformat."))
    try:
        daten = base64.b64decode(inhalt, validate=True)
    except (binascii.Error, ValueError) as fehler:
        raise FotoFehler(T("Die Webcam-Aufnahme ist beschädigt.")) from fehler
    try:
        with Image.open(io.BytesIO(daten)) as bild:
            bild.verify()
    except Exception as fehler:  # noqa: BLE001
        raise FotoFehler(T("Die Webcam-Aufnahme konnte nicht gelesen werden.")) from fehler
    return daten
