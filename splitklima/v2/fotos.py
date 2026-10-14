"""Fotos von Plänen (Kamera iPad/iPhone) für die Grundriss-Erkennung aufbereiten.

Handyfotos haben 12–48 Megapixel und speichern die Drehung oft nur als EXIF-Angabe. Vor dem Senden an
die Erkennung werden sie richtig gedreht, auf eine sinnvolle Größe verkleinert (Linien und Maßzahlen
bleiben lesbar, die Datei wird klein) und im Kontrast leicht angehoben.
"""

from __future__ import annotations

import io

from PIL import Image, ImageFilter, ImageOps

MAX_KANTE = 2400  # px – reicht für Maßketten, spart Token und bleibt unter den Bildgrenzen der API
BILD_MIME = {"image/jpeg", "image/png", "image/webp"}


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
        raise FotoFehler("Das Foto konnte nicht gelesen werden – bitte als JPG oder PNG aufnehmen.") from fehler
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
