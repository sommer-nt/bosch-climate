"""Schneidet Produktbilder aus dem Katalog-PDF (Gesamtkatalog 03/2026) aus.

Aufruf:  python tools/katalog_bilder.py <Katalog.pdf>
Benötigt pdftoppm (poppler-utils) und Pillow. Ergebnis: splitklima/daten/bilder/*.png

Koordinaten: Pixel bei 200 dpi (Seite 1700×2200), PDF-Seite = Katalogseite − 3000.
Gerendert wird mit 400 dpi, damit die Bilder scharf bleiben.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ZIEL = Path(__file__).resolve().parent.parent / "splitklima" / "daten" / "bilder"
DPI, BASIS = 400, 200

# name: (pdf-seite, (x0, y0, x1, y1) bei 200 dpi)
AUSSCHNITTE = {
    "set_8000i_weiss": (6, (230, 530, 438, 690)),
    "set_8000i_anthrazit": (6, (232, 696, 438, 852)),
    "set_8000i_silber": (6, (230, 855, 438, 1014)),
    "set_8000i_rot": (6, (230, 1017, 438, 1177)),
    "ie_8000i_weiss": (6, (236, 530, 380, 582)),
    "ie_8000i_anthrazit": (6, (236, 693, 380, 745)),
    "ie_8000i_silber": (6, (236, 855, 380, 907)),
    "ie_8000i_rot": (6, (236, 1017, 380, 1070)),
    "set_7000i_weiss": (14, (224, 600, 435, 800)),
    "set_7000i_silber": (14, (224, 804, 435, 964)),
    "set_7000i_schwarz": (14, (224, 969, 435, 1129)),
    "set_6000ip": (19, (374, 612, 704, 1100)),
    "set_3200i": (24, (224, 558, 435, 724)),
    "set_3000i": (24, (224, 900, 435, 1068)),
    "ae_5000m": (32, (232, 452, 432, 588)),
    "ie_konsole_5000i": (35, (176, 420, 371, 569)),
    "ie_kassette_5001iu": (37, (176, 514, 366, 692)),
    "ie_kassette_5000i": (40, (240, 522, 435, 708)),
    "ie_wand_3200i": (42, (232, 452, 432, 548)),
    "ie_wand_3000i": (42, (232, 772, 432, 860)),
    "ae_7000m": (52, (237, 420, 435, 572)),
    "ie_7000i_weiss": (55, (179, 473, 368, 537)),
    "ie_7000i_schwarz": (55, (179, 540, 368, 609)),
    "ie_7000i_silber": (55, (179, 612, 368, 679)),
}


def zuschneiden(bild: Image.Image, rand: int = 12) -> Image.Image:
    """Entfernt weißen Rand und Tabellenlinien (Zeilen/Spalten, die fast komplett dunkel sind)."""
    a = np.asarray(bild.convert("RGB")).astype(int)
    tinte = a.min(axis=2) < 232

    def gueltig(anteil: np.ndarray) -> np.ndarray:
        # Tabellenlinien = dünne (≤ 4 px), fast durchgehend dunkle Streifen; dunkle Geräte bleiben erhalten
        ok = anteil > 0.002
        voll = anteil > 0.92
        i = 0
        while i < len(voll):
            if voll[i]:
                j = i
                while j < len(voll) and voll[j]:
                    j += 1
                if j - i <= 4:
                    ok[i:j] = False
                i = j
            else:
                i += 1
        return np.where(ok)[0]

    ok_z = gueltig(tinte.mean(axis=1))
    ok_s = gueltig(tinte.mean(axis=0))
    if not len(ok_z) or not len(ok_s):
        return bild
    box = (ok_s.min(), ok_z.min(), ok_s.max() + 1, ok_z.max() + 1)
    teil = bild.crop(box)
    out = Image.new("RGB", (teil.width + 2 * rand, teil.height + 2 * rand), "white")
    out.paste(teil, (rand, rand))
    return out


def main(pdf: str) -> None:
    ZIEL.mkdir(parents=True, exist_ok=True)
    f = DPI / BASIS
    with tempfile.TemporaryDirectory() as tmp:
        seiten: dict[int, Image.Image] = {}
        for name, (seite, box) in AUSSCHNITTE.items():
            if seite not in seiten:
                stamm = Path(tmp) / f"s{seite}"
                subprocess.run(["pdftoppm", "-f", str(seite), "-l", str(seite), "-r", str(DPI), "-png",
                                "-singlefile", pdf, str(stamm)], check=True)
                seiten[seite] = Image.open(f"{stamm}.png").convert("RGB")
            teil = seiten[seite].crop(tuple(int(v * f) for v in box))
            zuschneiden(teil).save(ZIEL / f"{name}.png", optimize=True)
            print(name)


if __name__ == "__main__":
    main(sys.argv[1])
