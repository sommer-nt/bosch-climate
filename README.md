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
- **Neu: Assistent mit KI-Planerkennung, wirtschaftlichem Vorschlag und Preis** – siehe unten

## Assistent (Startseite)

Geführter Ablauf in drei Schritten – der Rechenkern bleibt unverändert:

1. **Projekt** – Ort (Klimadaten automatisch), kühlen/heizen, gewünschtes System
   (*Beste Lösung finden*, Multi-Split oder Single-Split), Baujahr, Fenster, Sonnenschutz.
2. **Räume** – Grundrisse hochladen (PDF, PNG, JPG): die KI (Claude) erkennt Räume, Flächen,
   Außenwände, Fenster, Dachlage und Baujahr. Oder Räume manuell anlegen. Jeder Raum ist eine
   kompakte, aufklappbare Zeile mit Kühlbedarf; Hinweise der Erkennung liegen eingeklappt
   hinter einem Info-Knopf.
3. **Ergebnis** – eine Empfehlung mit **Gerätepreis**, Anzahl Außen-/Innengeräte und
   Kühlleistung. Empfohlen wird das **wirtschaftlichste** Konzept, das alle Räume abdeckt
   (Vergleich: ein Multi-Split, Multi-Split je Geschoss, Single-Split je Raum). Alternativen
   mit Preisdifferenz, Stückliste, Räume/Geräte und Aufstellorte eingeklappt darunter.
   **Angebotsübersicht als PDF** nach Bestätigung der Hinweise.

Die bisherige Detailansicht (alle Parameter, Validierung, Exporte, PDF-Bericht) ist über
**„Expertenansicht“** oben rechts erreichbar.

### Preise

Preise stehen in `splitklima/daten/preise.json` (je Artikel-ID). **Die mitgelieferten Werte
sind Platzhalter.** Gültige Listenpreise eintragen und `"freigegeben": true` setzen – bis
dahin kennzeichnet die App den Preis als „Richtpreis aus Platzhalter-Preisliste“.

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
| `ui_assistent.py` | Assistent: Projekt → Räume → Ergebnis |
| `splitklima/ki_plan.py` | KI-Planerkennung (Claude) |
| `splitklima/anlagenvorschlag.py` | Vergleich der Anlagenkonzepte, wirtschaftliche Empfehlung |
| `splitklima/preise.py` | Preisliste, Stückliste, Gesamtpreis |
| `splitklima/daten/preise.json` | Preise je Artikel (Platzhalter – bitte pflegen) |
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
