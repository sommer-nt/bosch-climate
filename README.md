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

## Version 2 (`app_v2.py`) – Gesamtsortiment

Läuft parallel zu Version 1 (eigener Container, z. B. climate.sommer-nt.de), mit demselben
Rechenkern und derselben KI-Planerkennung:

- **Geführte Konfiguration**: links Navigationsbaum mit Fortschritt (System → Gebäude → Räume
  je Raum → Ergebnis), Mitte Auswahlkarten mit eigenen Piktogrammen, rechts eine
  **Live-Zusammenfassung** mit Produktbild, Gebäudelasten und Preis.
- **KI-Upload** prominent auf der Startseite: Grundriss hochladen, Räume werden vorbefüllt.
- **Gesamtsortiment** aus der Produktdaten-Excel (26 Sets, 6 Multi-Außeneinheiten,
  29 Inneneinheiten) mit **freigegebenen Katalogpreisen** (UVP netto, März 2026).
- Auswahl nach den **zulässigen Kombinationen** des Katalogs, Bauart- und Farbwunsch je Raum,
  Lieferstatus; Empfehlung = günstigstes vollständiges Konzept.
- **Produktbilder** aus dem Gesamtkatalog, Angebots-PDF mit Bildern, Stückliste und optionaler
  Inbetriebnahme durch den Kundendienst.

```bash
streamlit run app_v2.py
```

### Ergänzungskatalog 09/2026 (Version 2)

`splitklima/daten/katalog_ergaenzung.json` ergänzt das Sortiment um die **Large-Split-Anlagen
Climate 5000i L** (2,6–16 kW; Kompakt-/Deckenkassette, Ceiling/Floor-Truhengerät, Konsole; auch Twin,
Triple, Double Twin), die **CL5000M 53/3 E**, die **Ein-Wege-Kassetten CL5000iM 1C** und aktualisiert alle
dort gelisteten **Preise (UVP 09/2026)** per Bestellnummer. In der Auswahl erscheint für große Räume bzw.
Kassetten-/Truhenwunsch das Konzept „Large-Split für große Räume“ (Hinweis bei 400-V-Drehstromgeräten).

```bash
pip install pymupdf
python tools/ergaenzung_import.py Ergaenzungskatalog_2026-09.pdf
```

Das PDF enthält Schriften ohne Zeichentabelle; das Werkzeug liest den Text über die Glyph-Nummern
(siehe Kopf von `tools/ergaenzung_import.py`) und meldet Datenblatt-Widersprüche als Prüfhinweise.

### Gewerbe, große Räume und Gerätelinie (Version 2)

- **Raumarten** zusätzlich *Werkstatt*, *Halle / Lager*, *Verkaufsraum* – Luftwechsel und innere Lasten
  sind vorläufige Annahmen (`splitklima/parameter.py`, fachlich freizugeben); die Wohn-Raumarten und
  damit alle Ergebnisse aus v6.9.1 bleiben unverändert.
- **Raumhöhe bis 10 m.**
- **Große Räume** (z. B. Werkstatt 200 m²), die kein einzelnes Gerät decken kann, werden automatisch in
  Zonen mit je einem Innengerät aufgeteilt; Multi-Split-Gruppen beachten die Leistung der Außeneinheit.
- **Bevorzugte Gerätelinie** (Climate 3200i, 7000i, Class 8000i): geht in der Empfehlung vor dem Preis;
  ist sie für einen Raum nicht möglich, wird eine andere Linie gewählt und darauf hingewiesen.

### Norm-Außentemperatur über die PLZ (Version 2)

Auf der Seite „Gebäude“ genügt die PLZ oder der Ort. Die App prüft die Eingabe gegen das
**PLZ-Verzeichnis für ganz Deutschland** (8.308 PLZ, `splitklima/daten/plz_verzeichnis.csv`,
Quelle [GeoNames](https://www.geonames.org), Lizenz CC BY 4.0) und ermittelt die
Norm-Außentemperatur θe nach **DIN/TS 12831-1**:

1. PLZ in der offiziellen Tabelle → Wert 1:1 (inkl. Jahresmitteltemperatur θm,e)
2. PLZ fehlt in der Tabelle → Wert der nächstgelegenen PLZ (höchstens 15 km), mit Angabe
3. ohne Tabelle → Richtwert der Klimaregion aus v6.9.1, deutlich als „bitte prüfen“ gekennzeichnet

Der Wert lässt sich jederzeit manuell anpassen; Herkunft und Wert stehen im Angebots-PDF.

**Woher die PLZ-Werte kommen:** Die App lädt sie beim ersten Start selbst von der
[Klimakarte des BWP](https://www.waermepumpe.de/werkzeuge/klimakarte/) (PLZ-genaue Werte der
DIN/TS 12831-1 mit Jahresmittel, Höhe und Klimazone), prüft sie streng und speichert sie als
`splitklima/daten/normaussentemperatur_plz.csv`. Klappt das nicht (z. B. ohne Internet), gibt es auf
der Seite „Gebäude“ den Knopf **„BWP-Klimakarte laden“** und **„Tabelle hochladen“** (Excel/CSV).
Abschalten: Umgebungsvariable `KLIMADATEN_AUTO=0`.

Per Kommandozeile:

```bash
python tools/normtemperatur_import.py --bwp            # von der BWP-Klimakarte laden
python tools/normtemperatur_import.py Tabelle.xlsx     # aus einer Datei (Excel oder CSV)
```

Geprüft werden PLZ (führende Nullen aus Excel werden ergänzt), Wertebereiche, widersprüchliche
Doppel-Einträge und Vollständigkeit; bei Fehlern bleibt die bisherige Tabelle unverändert.
Die Tabelle wird nicht eingecheckt (`.gitignore`), da die Werte aus der DIN/TS 12831-1 stammen.

Katalog aktualisieren (neue Excel nach `splitklima/daten/quellen/` legen):

```bash
python tools/katalog_import.py [Excel-Datei]   # → splitklima/daten/katalog.json (+ Prüfhinweise)
python tools/katalog_bilder.py Katalog.pdf   # Produktbilder → splitklima/daten/bilder/
```

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

## Eigener Server mit Docker (HTTPS)

`Dockerfile` + `deploy/docker-compose.yml` (App + Caddy mit automatischem HTTPS).
Schritt-für-Schritt: **[deploy/ANLEITUNG.md](deploy/ANLEITUNG.md)** – Kurzform:

```bash
cd deploy && cp .env.beispiel .env   # Domain, API-Schlüssel, Passwort eintragen
docker compose up -d --build
```

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
| `app_v2.py`, `ui_v2.py` | Version 2: Oberfläche mit Auswahlkarten, Navigation, Live-Zusammenfassung |
| `splitklima/v2/` | Version 2: Katalog, Geräteauswahl nach Katalogregeln, Bilder, Piktogramme, Angebots-PDF |
| `splitklima/klima_plz.py` | PLZ-Prüfung, Ortssuche, Norm-Außentemperatur nach DIN/TS 12831-1 |
| `splitklima/daten/plz_verzeichnis.csv` | Alle deutschen PLZ mit Ort, Bundesland, Koordinaten (GeoNames, CC BY 4.0) |
| `splitklima/daten/katalog.json` | Gesamtsortiment mit Preisen (erzeugt aus der Produktdaten-Excel) |

Die Produktdaten liegen jetzt als JSON vor (in v6.9.1 als „spätere JSON-Auslagerung“
vorbereitet) und können ohne Code-Änderung gepflegt werden.

## Tests

```bash
python -m pytest -q
```

`tests/test_v2.py` prüft Version 2: jede vorgeschlagene Anlage (Beispielhaus und 60 zufällige
Häuser) hält die zulässigen Kombinationen ein und deckt die Lasten aus dem Rechenkern.

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
