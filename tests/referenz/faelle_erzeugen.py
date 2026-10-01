"""Erzeugt Testfälle (JS-Format) für den Abgleich Python ↔ HTML v6.9.1.

Aufruf (aus dem Repo-Wurzelverzeichnis):
    python tests/referenz/faelle_erzeugen.py
    node tests/referenz/js_referenz.mjs Split_Klima_Konfigurator_v6_9_1_Aktuell_Sommer.html \
        tests/referenz/faelle.json tests/referenz/erwartet.json
"""

import json
import random
from pathlib import Path

HIER = Path(__file__).parent
ORI = ["N", "NO", "O", "SO", "S", "SW", "W", "NW"]
ARTEN = ["Wohnzimmer", "Schlafzimmer", "Büro", "Küche", "Kinderzimmer", "Badezimmer"]
MODES = {"inside": 0, "outside": 1, "corner": 2, "three": 3, "attic": 1, "attic_corner": 2, "basement": 1}
VERT = ["between_heated", "above_heated", "over_cellar", "over_unheated", "over_outdoor", "ground",
        "under_unheated_roof"]
AGE = ["", "bis1957", "1958-1968", "1969-1978", "1979-1983", "1984-2001", "2002-heute"]
STANDARD = {"systemKind": "auto", "operationMode": "both", "building": "mid", "glass": "double", "shade": "1",
            "heatOut": -12, "summer": 33, "coolHours": 12, "simFactor": 1, "wbClass": "standard",
            "reheatClass": "none", "coolSet": 24, "heatSet": 20}


def zufallsraum(rng: random.Random, i: int) -> dict:
    mode = rng.choice(list(MODES))
    roof = mode in ("attic", "attic_corner")
    walls = [{"ori": rng.choice(ORI), "len": round(rng.uniform(2.5, 8), 1), "win": round(rng.uniform(0, 6), 1)}
             for _ in range(MODES[mode])]
    groups = [{"ori": rng.choice(ORI), "area": round(rng.uniform(0.5, 3), 1), "roofWindow": rng.random() < 0.4}
              for _ in range(rng.choice([0, 0, 1, 2]))]
    manual = rng.random() < 0.15
    return {
        "name": f"Raum {i + 1}", "type": rng.choice(ARTEN), "area": round(rng.uniform(8, 45), 1),
        "height": rng.choice([2.4, 2.5, 2.6, 2.75, 3.0]), "mode": mode, "walls": walls, "roof": roof,
        "roofKind": rng.choice(["flat", "saddle_south", "saddle_north", "saddle_eastwest"]),
        "roofArea": rng.choice([0, round(rng.uniform(10, 50), 1)]),
        "vertical": "above_heated" if roof else ("over_cellar" if mode == "basement" else rng.choice(VERT)),
        "ageClass": rng.choice(AGE), "storage": rng.choice(["light", "mid", "heavy"]),
        "retrofit": rng.choice(["none", "none", "facade", "core", "interior"]), "windowGroups": groups,
        "indoorType": rng.choice(["auto", "auto", "auto", "Wandgerät", "Truhengerät", "Kassettengerät",
                                  "Kanalgerät"]),
        "indoorId": rng.choice(["w20", "w26", "w35", "w53", "cn35", "cc53", "d70"]) if manual else None,
        "indoorManual": manual,
    }


def zufallseinstellungen(rng: random.Random) -> dict:
    return {
        "systemKind": rng.choice(["auto", "auto", "single", "multi"]),
        "operationMode": rng.choice(["both", "both", "cool", "heat"]),
        "building": rng.choice(["old", "mid", "new"]), "glass": rng.choice(["single", "double", "triple"]),
        "shade": rng.choice(["1", "0.8", "0.55", "0.45"]), "heatOut": rng.choice([-16, -14, -12, -10, -8]),
        "summer": rng.choice([30, 31, 32, 33, 35]), "coolHours": rng.choice([6, 12, 18, 24]),
        "simFactor": rng.choice([1, 0.95, 0.9, 0.85]), "wbClass": rng.choice(["none", "standard", "high"]),
        "reheatClass": rng.choice(["none", "standard", "high"]), "coolSet": rng.choice([22, 24, 26, 30]),
        "heatSet": rng.choice([18, 20, 22, 30]),
    }


def main() -> None:
    rng = random.Random(6_9_1)
    faelle = [{"name": f"Validierung {k}", "settings": dict(STANDARD), "applyCase": k}
              for k in ["sleep-small", "living-standard", "attic-west", "multi2", "multi5"]]
    for i in range(150):
        n = rng.choice([1, 1, 1, 2, 3, 4, 5, 6, 8])
        faelle.append({
            "name": f"Zufall {i + 1}", "settings": zufallseinstellungen(rng),
            "rooms": [zufallsraum(rng, j) for j in range(n)],
            "validationCase": rng.choice(["", "", "sleep-small", "living-standard", "attic-west", "multi2",
                                          "multi5"]),
        })
    (HIER / "faelle.json").write_text(json.dumps(faelle, ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"{len(faelle)} Fälle geschrieben.")


if __name__ == "__main__":
    main()
