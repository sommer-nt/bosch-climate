# BOSCH Climate – Split-Klima-Konfigurator (Python)

Python-Version des Split-Klima-Konfigurators **v6.9.1**
(`Split_Klima_Konfigurator_v6_9_1_Aktuell_Sommer.html`).
Gleicher Rechenkern (CALC-0.4), gleiche Produktdaten (DM-0.1), gleiche Ergebnisse –
jetzt als Python-Paket mit Streamlit-Oberfläche.

## Funktionen

- **Heiz- und Kühllast je Raum** – Kühllast in Anlehnung an VDI 2078, Heizlast in
  Anlehnung an DIN EN 12831-1 (Wärmebrücken, Aufheizreserve, Speichereffekt,
  Baualtersklassen, nachträgliche Dämmung, Fenstergruppen/Dachfenster, vertikale Lage)
- **Standort → Klimaregion** (Norm-Außentemperatur, Sommer-Auslegung), Expertenmodus
- **Inneneinheiten je Raum** – automatische Vorauswahl (kleinste passende Einheit) oder manuell,
  Bewertung Passend / Überdimensionierung prüfen / Passt nicht
- **Außengeräte** – Single- und Multi-Split, wirtschaftliche Systemalternativen,
  im Auto-Modus Kombination mehrerer Außengeräte, Raum-/Systemzuordnung
- **Schallbewertung, Zubehörkonfiguration, Produktdaten Professional, Kennlinien**
- **Validierung** mit Referenzfällen V-101 … V-203, Gesamtstatus, Heizanwendung (B-024),
  Datenqualität (B-032)
- **Exporte** wie v6.9.1: Projekt-JSON (PJ-0.1), Produktdaten-JSON (DM-0.1),
  Validierungs-Snapshot, Berechnungsparameter; **PDF-Bericht A4 quer** nach Bestätigung
  der Haftungshinweise
- **Neu:** Projekt speichern/laden (`.skk.json`)
- **Neu: Pläne & Anlagenvorschlag (KI)** – siehe unten

## Pläne & Anlagenvorschlag (KI)

Erste Seite der App („① Pläne & Anlagenvorschlag“):

1. **Pläne hochladen** – Grundrisse aller Geschosse, Schnitte, Ansichten, Lageplan
   (PDF, PNG, JPG; zusammen max. 30 MB). Optional Zusatzangaben wie
   „Plan-Oben zeigt nach Nordost“.
2. **KI-Analyse (Claude)** – erkennt je Raum Geschoss, Bezeichnung, Raumart, Fläche,
   Raumhöhe, Außenwände mit Himmelsrichtung, Länge und Fensterfläche, Dachlage,
   Dachfenster und was darunter/darüber liegt; dazu Baujahr aus dem Plankopf und
   geeignete Aufstellorte für Außengeräte. Unsicherheiten werden als Hinweise angezeigt.
3. **Prüfen** – erkannte Räume in einer Tabelle korrigieren oder abwählen,
   Baujahr → Baualtersklasse übernehmen.
4. **Infrage kommende Anlagen** – mit dem Rechenkern werden drei Konzepte verglichen:
   *ein Multi-Split-System*, *Multi-Split je Geschoss*, *Single-Split je Raum* – jeweils mit
   Außen- und Inneneinheiten, Deckung, Anschlüssen und Schall. Das Konzept mit
   vollständiger Deckung und den wenigsten Außengeräten wird als Empfehlung markiert.
5. **Übernehmen** – alle Räume oder ein Teilsystem (z. B. nur das DG) in den
   Konfigurator übernehmen und dort im Detail ausarbeiten inkl. PDF-Bericht.

Ohne API-Schlüssel lässt sich der Ablauf mit „Beispielergebnis laden“ ausprobieren.

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

Für die KI-Planerkennung zusätzlich einen API-Schlüssel setzen:

```bash
export ANTHROPIC_API_KEY=sk-ant-...      # Windows: set ANTHROPIC_API_KEY=sk-ant-...
```

Alles andere funktioniert ohne Schlüssel und offline.

## Lokal starten per Doppelklick

- **Windows:** Repo als ZIP herunterladen (GitHub → Code → Download ZIP), entpacken,
  `start_windows.bat` doppelklicken. Voraussetzung: Python 3.11+ von python.org.
- **macOS/Linux:** `./start_mac_linux.sh`

Für die KI-Planerkennung `.streamlit/secrets.toml` nach Vorlage
`.streamlit/secrets.toml.beispiel` anlegen.

## Deployment auf Streamlit Community Cloud

1. <https://share.streamlit.io> → **Create app** → „Deploy a public app from GitHub“
2. Repository `sommer-nt/bosch-climate`, Branch (z. B. `main`), Main file `app.py`
3. **Advanced settings** → Python 3.12 und unter **Secrets** eintragen
   (Vorlage: `.streamlit/secrets.toml.beispiel`):
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   APP_PASSWORT = "..."      # optional, schützt die App mit einem Passwort
   ```
4. **Deploy**. `requirements.txt` und `packages.txt` (Schrift für den PDF-Bericht)
   werden automatisch installiert.

## Aufbau

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `splitklima/parameter.py` | Alle Berechnungsparameter (U-/g-Werte, Einstrahlung, Zuschläge …) |
| `splitklima/modell.py` | Projekt, Einstellungen, Raum, Wand, Fenstergruppe |
| `splitklima/berechnung.py` | Rechenkern: Kühl-/Heizlast je Raum und Gebäude |
| `splitklima/auswahl.py` | Inneneinheiten, Außengeräte-Kombinationen, Raumzuordnung |
| `splitklima/bewertung.py` | Status, Heizanwendung, Datenqualität, Schall, Zubehör, Validierung |
| `splitklima/standort.py` | Orte und Klimaregionen |
| `splitklima/export.py` | JSON-Exporte und Prüfdaten |
| `splitklima/bericht.py` | PDF-Bericht |
| `ui_plaene.py` | Seite „Pläne & Anlagenvorschlag“ |
| `splitklima/ki_plan.py` | KI-Planerkennung (Claude) |
| `splitklima/anlagenvorschlag.py` | Vergleich der Anlagenkonzepte und Empfehlung |
| `splitklima/daten/produkte.json` | Produktdaten Außen-/Inneneinheiten (aus v6.9.1 übernommen) |

Die Produktdaten liegen jetzt als JSON vor (in v6.9.1 als „spätere JSON-Auslagerung“
vorbereitet) und können ohne Code-Änderung gepflegt werden.

## Tests

```bash
python -m pytest -q
```

`tests/test_abgleich_html.py` rechnet **155 Fälle** (die 5 Validierungsfälle und 150
zufällige Projekte mit 1–8 Räumen und allen Einstellungen) und vergleicht Python mit dem
Original-JavaScript der HTML-Datei: Lasten, Inneneinheiten, Systemalternativen,
Zuordnung, Status, Zubehör, Schall und Validierung stimmen exakt überein.

Referenz neu erzeugen (benötigt Node.js), z. B. nach Änderungen an der HTML-Version:

```bash
python tests/referenz/faelle_erzeugen.py
node tests/referenz/js_referenz.mjs Split_Klima_Konfigurator_v6_9_1_Aktuell_Sommer.html \
     tests/referenz/faelle.json tests/referenz/erwartet.json
```

## Hinweis

Heiz- und Kühllasten sind überschlägige Schätzwerte. Alle Parameter sind
Validierungsannahmen und fachlich freizugeben. Die Konfiguration ersetzt keine Fachplanung.

Entwickelt von Daniel Sommer · HC/SDE3-PSD
