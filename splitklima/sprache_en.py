"""Englische Texte der Version 2 (Schlüssel = deutscher Originaltext, Platzhalter wie im Original).

Fachlich bleibt alles deutsch: PLZ, Orte, Klimadaten, Normen (DIN/VDI), Bestellnummern, Euro-Preise.
Fehlt ein Eintrag, zeigt die App den deutschen Text (Test ``test_englisch_vollstaendig`` prüft das).
"""

EN: dict[str, str] = {
    # ------------------------------------------------------------------ Kopf, Navigation, allgemein
    "BOSCH Climate Split-Klima Konfigurator 2": "BOSCH Climate Split AC Configurator 2",
    "Split-Klima Konfigurator": "Split AC Configurator",
    "Version 2 · Testumgebung": "Version 2 · Test environment",
    "Gesamtsortiment {q} · Rechenkern {v}": "Full range: {q} · calculation core {v}",
    "Passwort": "Password",
    "Passwort falsch.": "Wrong password.",
    "Entwickelt von Daniel Sommer (HC/SDE3-PSD)": "Developed by Daniel Sommer (HC/SDE3-PSD)",
    "System": "System",
    "Gebäude": "Building",
    "Räume": "Rooms",
    "Ergebnis": "Result",
    "Fortschritt {n} %": "Progress {n}%",
    "Konfiguration": "Configuration",
    "Speichern (JSON)": "Save (JSON)",
    "Laden": "Load",
    "Gespeicherte Konfiguration (.json)": "Saved configuration (.json)",
    "Lädt Räume, Einstellungen, Gerätewünsche und Zubehörmengen. Die aktuelle Konfiguration wird ersetzt – "
    "vorher speichern.": "Loads rooms, settings, unit preferences and accessory quantities. The current "
                          "configuration will be replaced – save it first.",
    "Laden nicht möglich:": "Could not load:",
    "Konfiguration „{name}“ geladen ({n} Räume).": "Configuration “{name}” loaded ({n} rooms).",
    "Neu beginnen": "Start over",
    "Planung zurücksetzen?": "Reset planning?",
    "Alle Räume, Einstellungen, Gerätewünsche und Zubehörmengen werden gelöscht. Wer die aktuelle Planung "
    "behalten möchte, speichert sie vorher als JSON.": "All rooms, settings, unit preferences and accessory "
                                                       "quantities will be deleted. To keep the current planning, "
                                                       "save it as JSON first.",
    "Vorher speichern (JSON)": "Save first (JSON)",
    "Ja, alles zurücksetzen": "Yes, reset everything",
    "Neue Planung gestartet.": "New planning started.",
    "Zurück": "Back",
    "Weiter zum Gebäude": "Continue to building",
    "Weiter zu den Räumen": "Continue to rooms",
    "Zum Ergebnis": "To the result",
    "Nächster Raum": "Next room",
    "Übernehmen": "Apply",
    "Bitte auswählen": "Please select",
    "Schließen": "Close",
    "Hinweise": "Notes",
    "Hinweise ({n})": "Notes ({n})",
    "keine": "none",
    "auf Anfrage": "on request",
    "kein": "none",
    "Optional": "Optional",

    # ------------------------------------------------------------------ Grundriss-Erkennung, Kamera, Webcam
    "Grundriss hochladen – fertig.": "Upload a floor plan – done.",
    "Die KI erkennt Räume, Flächen, Fenster und die Himmelsrichtung und füllt die Konfiguration für Sie aus. "
    "Sie prüfen nur noch kurz.": "The AI detects rooms, areas, windows and orientation and fills in the "
                                 "configuration for you. You just check it briefly.",
    "Grundrisse hochladen – Räume automatisch erkennen": "Upload floor plans – detect rooms automatically",
    "Pläne": "Plans",
    "Zusatzangaben": "Additional details",
    "Hinweise für die Erkennung": "Notes for the recognition",
    "z. B. Plan-Oben zeigt nach Nordost; Keller nicht klimatisieren": "e.g. top of plan faces north-east; "
                                                                      "do not air-condition the basement",
    "Räume erkennen": "Detect rooms",
    "Die Pläne werden gelesen … das dauert 1–2 Minuten.": "Reading the plans … this takes 1–2 minutes.",
    "Beispielhaus laden": "Load example house",
    "Zusammen {mb} MB – bitte höchstens {max} MB bzw. Geschosse einzeln hochladen.":
        "{mb} MB in total – please upload at most {max} MB or one floor at a time.",
    "Automatische Erkennung ist hier nicht eingerichtet (API-Schlüssel fehlt) – „Beispielhaus laden“ zeigt, "
    "wie es funktioniert.": "Automatic recognition is not set up here (API key missing) – “Load example house” "
                            "shows how it works.",
    "PDF, PNG, JPG oder Foto · alle Geschosse auf einmal möglich · Fotos werden vorher gedreht, verkleinert und "
    "kontrastverstärkt · die Pläne werden zur Auswertung an die Claude API übertragen.":
        "PDF, PNG, JPG or photo · all floors at once · photos are rotated, downscaled and contrast-enhanced first "
        "· plans are sent to the Claude API for analysis.",
    "Plan fotografieren": "Photograph plan",
    "Weiteres Foto": "Another photo",
    "Tipp: Plan flach hinlegen, von oben fotografieren, ganzes Blatt im Bild, gutes Licht – Maßketten müssen "
    "lesbar sein. Ein Foto je Geschoss; jedes neue Foto wird ergänzt.":
        "Tip: lay the plan flat, shoot from above, whole sheet in frame, good light – dimensions must be "
        "legible. One photo per floor; each new photo is added.",
    "{name}: nicht lesbar": "{name}: not readable",
    "Drehen": "Rotate",
    "Entfernen": "Remove",
    "Plan in die Webcam halten": "Hold plan up to webcam",
    "Aufnehmen": "Capture",
    "Leertaste": "space bar",
    "Selbstauslöser 3 s": "Self-timer 3 s",
    "Kamera aus": "Camera off",
    "Kamera wählen": "Choose camera",
    "Kamera {n}": "Camera {n}",
    "Der Browser erlaubt hier keinen Kamerazugriff (nur über https). Alternativ ein Foto über „Pläne hochladen“ "
    "hinzufügen.": "The browser does not allow camera access here (https only). Alternatively add a photo via "
                   "the plan upload.",
    "Kamerazugriff wurde abgelehnt – bitte in der Adressleiste erlauben und erneut starten.":
        "Camera access was denied – please allow it in the address bar and start again.",
    "Keine Webcam gefunden. Alternativ ein Foto über „Pläne hochladen“ hinzufügen.":
        "No webcam found. Alternatively add a photo via the plan upload.",
    "Die Webcam wird gerade von einem anderen Programm benutzt (z. B. Teams) – dort schließen und erneut starten.":
        "The webcam is in use by another program (e.g. Teams) – close it there and start again.",
    "Webcam konnte nicht gestartet werden:": "Webcam could not be started:",
    "Webcam liefert nur {w}×{h} – Plan nah an die Kamera halten oder besser mit dem Handy fotografieren und "
    "hochladen.": "Webcam only delivers {w}×{h} – hold the plan close to the camera or, better, photograph it "
                  "with a phone and upload it.",
    "Webcam: {w}×{h} ({mp} MP) · Plan formatfüllend in den Rahmen halten, ruhig halten, gutes Licht · ein Foto je "
    "Geschoss.": "Webcam: {w}×{h} ({mp} MP) · fill the frame with the plan, hold it still, good light · one photo "
                 "per floor.",
    "Webcam-Foto übernommen – für das nächste Geschoss einfach erneut aufnehmen.":
        "Webcam photo added – for the next floor simply capture again.",
    "Nordrichtung: {r}": "North direction: {r}",
    "{n} Räume erkannt – bitte kurz durchsehen.": "{n} rooms detected – please review them briefly.",
    "Das Foto konnte nicht gelesen werden – bitte als JPG oder PNG aufnehmen.":
        "The photo could not be read – please take it as JPG or PNG.",
    "Die Webcam-Aufnahme ist zu groß oder ungültig.": "The webcam capture is too large or invalid.",
    "Die Webcam-Aufnahme hat kein unterstütztes Bildformat.": "The webcam capture has no supported image format.",
    "Die Webcam-Aufnahme ist beschädigt.": "The webcam capture is corrupted.",
    "Die Webcam-Aufnahme konnte nicht gelesen werden.": "The webcam capture could not be read.",
    "Kein API-Schlüssel gefunden. In Streamlit Cloud unter ⋮ → Settings → Secrets eintragen:  "
    'ANTHROPIC_API_KEY = "sk-ant-..."  (lokal: Datei .streamlit/secrets.toml). Nach dem Speichern ca. 1 Minute '
    "warten und die App neu laden.": "No API key found. In Streamlit Cloud add it under ⋮ → Settings → Secrets:  "
                                     'ANTHROPIC_API_KEY = "sk-ant-..."  (locally: file .streamlit/secrets.toml). '
                                     "After saving, wait about 1 minute and reload the app.",
    "Kein gültiger API-Schlüssel (ANTHROPIC_API_KEY).": "No valid API key (ANTHROPIC_API_KEY).",
    "Rate-Limit erreicht – bitte kurz warten.": "Rate limit reached – please wait a moment.",
    "Anfrage abgelehnt (Datei zu groß?):": "Request rejected (file too large?):",
    "Keine Verbindung zur Claude API.": "No connection to the Claude API.",
    "Die Analyse wurde vom Modell abgelehnt.": "The analysis was declined by the model.",
    "Plan zu umfangreich – bitte einzelne Geschosse hochladen.": "Plan too extensive – please upload single floors.",
    "Antwort konnte nicht gelesen werden.": "The response could not be read.",

    # ------------------------------------------------------------------ Seite System
    "Welches System wünschen Sie?": "Which system would you like?",
    "Beste Lösung": "Best solution",
    "Wir vergleichen alle Varianten und empfehlen die wirtschaftlichste.":
        "We compare all variants and recommend the most economical one.",
    "Eine Außeneinheit versorgt mehrere Räume.": "One outdoor unit serves several rooms.",
    "Jeder Raum bekommt ein eigenes Set.": "Each room gets its own set.",
    "Was soll die Anlage leisten?": "What should the system do?",
    "Kühlen & Heizen": "Cooling & heating",
    "Ganzjährig nutzen – im Sommer kühlen, in der Übergangszeit heizen.":
        "Year-round use – cool in summer, heat in spring and autumn.",
    "Nur Kühlen": "Cooling only",
    "Angenehme Temperaturen an heißen Tagen.": "Comfortable temperatures on hot days.",
    "Nur Heizen": "Heating only",
    "Effizient heizen mit Luft-Luft-Wärmepumpe.": "Efficient heating with an air-to-air heat pump.",
    "Bevorzugte Gerätelinie": "Preferred product line",
    "Wirtschaftlichste Lösung": "Most economical solution",
    "Wir wählen die günstigste passende Lösung.": "We choose the lowest-priced suitable solution.",
    "Solide Wandgeräte, günstig.": "Solid wall-mounted units, good value.",
    "Leise, BEG-förderfähig mit MSG-1, auch silber/schwarz.":
        "Quiet, eligible for BEG funding with MSG-1, also silver/black.",
    "Design-Linie, anthrazit/silber/rot – nur als Set.": "Design line, anthracite/silver/red – set only.",
    "Auslaufartikel anzeigen": "Show discontinued items",
    "Geräte, die im Ergänzungskatalog 09/2026 nicht mehr enthalten sind: Climate 3000i (Sets und "
    "Multi-Inneneinheiten) und CLC8001i-Set 35. Für Altprojekte; Preise Stand 03/2026.":
        "Units no longer listed in the supplementary catalogue 09/2026: Climate 3000i (sets and multi-split "
        "indoor units) and CLC8001i-Set 35. For older projects; prices as of 03/2026.",
    "{n} Auslaufartikel werden bei der Auswahl berücksichtigt (Preise Stand 03/2026):":
        "{n} discontinued items are included in the selection (prices as of 03/2026):",
    "{n} Artikel sind ausgeblendet, weil sie im Ergänzungskatalog 09/2026 fehlen – mit dem Schalter für "
    "Altprojekte wieder zulassen:": "{n} items are hidden because they are missing from the supplementary "
                                    "catalogue 09/2026 – re-enable them with the switch for older projects:",
    "Multi-Innengerät": "Multi-split indoor unit",
    "Wo steht die Außeneinheit?": "Where is the outdoor unit installed?",
    "Noch offen": "Not decided yet",
    "Fassade / Wand": "Facade / wall",
    "Boden / Terrasse": "Ground / terrace",
    "Flachdach": "Flat roof",
    "Entscheiden wir später.": "We'll decide later.",
    "Wandkonsole an der Fassade.": "Wall bracket on the facade.",
    "Bodenkonsole vor dem Haus, z. B. Garten oder Terrasse.": "Floor stand in front of the house, e.g. garden or "
                                                              "terrace.",
    "Bodenkonsole auf dem Flachdach, ohne Dachdurchdringung.": "Floor stand on the flat roof, without roof "
                                                               "penetration.",

    # ------------------------------------------------------------------ Seite Gebäude
    "Wo steht das Gebäude?": "Where is the building?",
    "Projektname": "Project name",
    "PLZ oder Ort": "Postcode or town (Germany)",
    "z. B. 72622 oder Nürtingen": "e.g. 72622 or Nürtingen",
    "Diese PLZ bzw. diesen Ort gibt es in Deutschland nicht – bitte prüfen.":
        "This postcode or town does not exist in Germany – please check.",
    "Norm-Außentemperatur θe": "Design outdoor temperature θe",
    "Norm-Außentemperatur": "Design outdoor temperature",
    "manuell eingegeben": "entered manually",
    " (PLZ-Wert: {w})": " (postcode value: {w})",
    "Jahresmittel θm,e {t}": "Annual mean θm,e {t}",
    "Höhe {h} m": "Altitude {h} m",
    "Klimazone {z}": "Climate zone {z}",
    "Klimadaten übernommen.": "Climate data applied.",
    "Wert anpassen": "Adjust value",
    "Sommer-Auslegung {t} °C": "Summer design {t} °C",
    "Die PLZ-genauen Werte der DIN/TS 12831-1 werden gerade von der BWP-Klimakarte geladen …":
        "The postcode-specific values of DIN/TS 12831-1 are being loaded from the BWP climate map …",
    "Automatisches Laden der BWP-Klimakarte nicht möglich:": "Automatic loading of the BWP climate map failed:",
    "Die PLZ-genauen Werte der DIN/TS 12831-1 sind noch nicht hinterlegt.":
        "The postcode-specific values of DIN/TS 12831-1 are not stored yet.",
    "BWP-Klimakarte laden": "Load BWP climate map",
    "Klimakarte wird geladen und geprüft …": "Loading and checking climate map …",
    "Tabelle hochladen": "Upload table",
    "Excel oder CSV mit den Spalten PLZ, Norm-Außentemperatur und optional Jahresmitteltemperatur (z. B. Export "
    "der Klimakarte).": "Excel or CSV with the columns PLZ (postcode), design outdoor temperature and optionally "
                        "annual mean temperature (e.g. export of the climate map).",
    "Klimadaten": "Climate data",
    "Baujahr": "Year of construction",
    "Altbau vor 1979 – wenig Dämmung": "Old building before 1979 – little insulation",
    "Baujahr 1979–2001 – mittlerer Dämmstandard": "Built 1979–2001 – medium insulation standard",
    "ab 2002 – guter Dämmstandard (EnEV/GEG)": "From 2002 – good insulation standard (EnEV/GEG)",
    "Außenwände nachträglich gedämmt": "Exterior walls insulated later",
    "Sanierung nach dem Baujahr, z. B. Haus von 1958 mit Fassadendämmung 1990. Gilt für alle Räume; einzelne "
    "Räume kann der Planungs-Assistent abweichend setzen.": "Renovation after construction, e.g. house from 1958 "
                                                            "with facade insulation in 1990. Applies to all rooms; "
                                                            "the planning assistant can set individual rooms "
                                                            "differently.",
    "Fassadendämmung vor 1995, ca. 4–6 cm (U≈0,50)": "Facade insulation before 1995, approx. 4–6 cm (U≈0.50)",
    "Fassadendämmung 1995–2008, ca. 8–10 cm (U≈0,35)": "Facade insulation 1995–2008, approx. 8–10 cm (U≈0.35)",
    "Fassadendämmung ab 2009, ca. 12–16 cm (U≈0,28)": "Facade insulation from 2009, approx. 12–16 cm (U≈0.28)",
    "Kerndämmung (U≈0,45)": "Cavity wall insulation (U≈0.45)",
    "Innendämmung (U≈0,40)": "Interior insulation (U≈0.40)",
    "Fenster": "Windows",
    "Zweifach": "Double",
    "Dreifach": "Triple",
    "Einfach": "Single",
    "Sonnenschutz": "Sun protection",
    "Außen": "External",
    "Rollladen, Raffstore": "Roller shutter, external blinds",
    "Innen": "Internal",
    "Vorhang, Plissee": "Curtain, pleated blind",
    "Keiner": "None",

    # ------------------------------------------------------------------ Räume
    "Ihre Räume ({n})": "Your rooms ({n})",
    "Hinweise zur Erkennung ({n})": "Recognition notes ({n})",
    "Noch keine Räume – Grundriss hochladen oder Räume von Hand anlegen.":
        "No rooms yet – upload a floor plan or add rooms manually.",
    "✓ geprüft": "✓ checked",
    "bitte prüfen": "please check",
    "Kühlen": "cooling",
    "{name} bearbeiten": "Edit {name}",
    "Raum hinzufügen": "Add room",
    "Raum {n}": "Room {n}",
    "RAUM {i} VON {n}": "ROOM {i} OF {n}",
    "Raumname": "Room name",
    "Geschoss": "Floor",
    "EG, OG, DG …": "EG, OG, DG … (ground, upper, attic)",
    "Nutzung": "Use",
    "Wohnen": "Living",
    "Schlafen": "Bedroom",
    "Büro": "Office",
    "Küche": "Kitchen",
    "Kinder": "Children",
    "Bad": "Bathroom",
    "Werkstatt": "Workshop",
    "Halle / Lager": "Hall / storage",
    "Größe": "Size",
    "Grundfläche": "Floor area",
    "Raumhöhe": "Room height",
    "Lage im Gebäude": "Position in the building",
    "1 Außen&shy;wand": "1 exterior wall",
    "Eckraum": "Corner room",
    "3 Außen&shy;wände": "3 exterior walls",
    "Innen&shy;liegend": "Interior",
    "Dach&shy;geschoss": "Attic floor",
    "DG-Eck&shy;raum": "Attic corner",
    "Über Keller": "Above basement",
    "Außenwand zeigt nach": "Exterior wall faces",
    "Wandlänge (m)": "Wall length (m)",
    "Fensterfläche (m²)": "Window area (m²)",
    "Wandlängen aus der Grundfläche geschätzt (≈ √{a} m² = {l} m) – bitte an den Grundriss anpassen. Nach einer "
    "Änderung bleiben Ihre Werte stehen.": "Wall lengths estimated from the floor area (≈ √{a} m² = {l} m) – "
                                          "please adjust to the floor plan. Once changed, your values are kept.",
    "Wandlängen aus Grundfläche schätzen": "Estimate wall lengths from floor area",
    "Innenliegender Raum – keine Außenwände.": "Interior room – no exterior walls.",
    "Dach über dem Raum": "Roof above the room",
    "Geschoss darüber": "Floor above",
    "Sattel&shy;dach Süd": "Gable roof south",
    "Sattel&shy;dach Nord": "Gable roof north",
    "Sattel&shy;dach Ost/West": "Gable roof east/west",
    "Flachdach: Die Dachfläche ist den ganzen Tag besonnt – die Kühllast steigt deutlich (Dachfläche = "
    "Grundfläche). Lichtkuppeln unten als Dachfenster eintragen.": "Flat roof: the roof is in the sun all day – "
                                                                   "the cooling load rises considerably (roof area "
                                                                   "= floor area). Enter skylight domes below as "
                                                                   "roof windows.",
    "Dachfenster / Lichtkuppeln": "Roof windows / skylights",
    "Gerätewunsch": "Unit preference",
    "Keine Präferenz": "No preference",
    "Wandgerät": "Wall-mounted unit",
    "Decken&shy;kassette": "Ceiling cassette",
    "Deckenkassette": "Ceiling cassette",
    "Konsole": "Console",
    "Truhe / Decke": "Floor / ceiling",
    "Truhe/Decke": "Floor/ceiling unit",
    "Farbe der Inneneinheit": "Indoor unit colour",
    "Farbige Inneneinheiten gibt es in den Serien Climate 7000i (silber, schwarz) und Climate Class 8000i "
    "(anthrazit, silber, rot).": "Coloured indoor units are available in the Climate 7000i (silver, black) and "
                                 "Climate Class 8000i (anthracite, silver, red) series.",
    "„{farbe}“ gibt es bis {max} kW je Gerät. Dieser Raum braucht {last} kW – wir planen deshalb mehrere Geräte "
    "in {farbe_klein}. Für ein einzelnes Gerät „Keine Präferenz“ wählen.":
        "“{farbe}” is available up to {max} kW per unit. This room needs {last} kW – so we plan several units in "
        "{farbe_klein}. For a single unit choose “No preference”.",
    "Ceiling/Floor-Truhengeräte (Climate 5000i L) – unter der Decke oder am Boden, 5,3 bis 16 kW, auch als Twin.":
        "Ceiling/floor units (Climate 5000i L) – under the ceiling or on the floor, 5.3 to 16 kW, also as twin.",
    "{bauart}n: als Large-Split-Set (Climate 5000i L) oder als Multi-Split-Inneneinheit.":
        "{bauart}: as a Large-Split set (Climate 5000i L) or as a multi-split indoor unit.",
    "Raum entfernen": "Remove room",
    # Raumarten (Werte bleiben deutsch, Anzeige übersetzt)
    "Wohnzimmer": "Living room",
    "Schlafzimmer": "Bedroom",
    "Kinderzimmer": "Children's room",
    "Badezimmer": "Bathroom",
    "Verkaufsraum": "Sales room",
    # Farben
    "weiß": "white", "silber": "silver", "schwarz": "black", "anthrazit": "anthracite", "rot": "red",
    "Weiß": "White", "Silber": "Silver", "Schwarz": "Black", "Anthrazit": "Anthracite", "Rot": "Red",
    "Gewerbe-Raumarten: innere Lasten als überschlägige Auslegungsannahmen – Werkstatt 20 W/m² (üblich 15–30 je "
    "nach Maschinen, Beleuchtung, Personen), Halle/Lager 6 W/m² (üblich 3–10), Verkaufsraum 25 W/m² (üblich 20–30 "
    "je nach Personenverkehr, Beleuchtung, Schaufenstern, Geräten). Diese Werte ersetzen keine detaillierte "
    "Kühllastberechnung nach VDI 2078 oder DIN EN 16798. Maschinenabwärme, Tore und Hallenhöhe "
    "(Temperaturschichtung) gesondert prüfen.":
        "Commercial room types: internal loads are rough design assumptions – workshop 20 W/m² (typically 15–30 "
        "depending on machines, lighting, people), hall/storage 6 W/m² (typically 3–10), sales room 25 W/m² "
        "(typically 20–30 depending on footfall, lighting, shop windows, equipment). These values do not replace "
        "a detailed cooling load calculation to VDI 2078 or DIN EN 16798. Check machine waste heat, doors and hall "
        "height (temperature stratification) separately.",

    # ------------------------------------------------------------------ Zusammenfassung rechts, Kennzahlen
    "Ihre Konfiguration": "Your configuration",
    "Gerätepreis, UVP netto": "Unit price, RRP net",
    "Noch keine passende Gerätekombination – Räume oder Gerätewunsch anpassen.":
        "No suitable unit combination yet – adjust rooms or unit preference.",
    "Sobald Räume erfasst sind, sehen Sie hier live den Vorschlag mit Preis.":
        "As soon as rooms are entered, you see the live proposal with price here.",
    "Betrieb": "Operation",
    "Gerätelinie": "Product line",
    "Außeneinheit": "Outdoor unit",
    "Standort": "Location",
    "Norm-Außentemp.": "Design outdoor temp.",
    "Kühllast": "Cooling load",
    "Heizlast": "Heating load",
    "live berechnet": "calculated live",
    "Vorschlag:": "Proposal:",
    "{n} Geräte – ": "{n} units – ",
    "Kühllast {k} kW · {ag} AG / {ig} IG": "Cooling load {k} kW · {ag} ODU / {ig} IDU",

    # ------------------------------------------------------------------ Ergebnis
    "Für diese Räume gibt es mit dem gewählten System keine passende Lösung im Sortiment. Bitte ein anderes "
    "System oder eine andere Bauart wählen oder große Räume aufteilen.":
        "There is no suitable solution in the range for these rooms with the selected system. Please choose "
        "another system or unit type, or split large rooms.",
    "UNSERE EMPFEHLUNG": "OUR RECOMMENDATION",
    "IHRE AUSWAHL": "YOUR CHOICE",
    "Gerätepreis": "Unit price",
    "Empfohlen wäre: {name} ({preis})": "Recommended would be: {name} ({preis})",
    "Außengeräte": "Outdoor units",
    "Innengeräte": "Indoor units",
    "Kühlleistung": "Cooling capacity",
    "Summe Nennleistung Außengeräte": "Total rated capacity of outdoor units",
    "Kühllast Gebäude": "Building cooling load",
    "Rechenkern CALC-0.4, mit Gleichzeitigkeit": "Calculation core CALC-0.4, with diversity factor",
    "Alternativen": "Alternatives",
    "Empfehlung": "Recommendation",
    "{n} Außengerät": "{n} outdoor unit",
    "{n} Außengeräte": "{n} outdoor units",
    "Auswählen": "Select",
    "Ihre Geräte": "Your units",
    " mit {n} Innengeräten": " with {n} indoor units",
    "{typ} · Kühlen {k} kW · Heizen {h} kW": "{typ} · cooling {k} kW · heating {h} kW",
    "Inneneinheit": "Indoor unit",
    "Stückliste mit Preisen": "Parts list with prices",
    "Artikel": "Item",
    "Bestell-Nr.": "Order no.",
    "Menge": "Qty",
    "Einzelpreis": "Unit price",
    "Summe": "Total",
    "Summe Geräte: {s}": "Total units: {s}",
    "Optional: Inbetriebnahme durch den Bosch-Kundendienst": "Optional: commissioning by Bosch customer service",
    "Leistung": "Service",
    "**Summe optional: {s}** – nicht im Gerätepreis enthalten.": "**Total optional: {s}** – not included in the "
                                                                 "unit price.",
    "Räume und Lasten": "Rooms and loads",
    "Raum": "Room",
    "Fläche m²": "Area m²",
    "Kühllast kW": "Cooling load kW",
    "Heizlast kW": "Heating load kW",
    "Gebäude gesamt: Kühlen {k} kW · Heizen {h} kW (Rechenkern CALC-0.4, in Anlehnung an VDI 2078 / DIN EN "
    "12831-1)": "Building total: cooling {k} kW · heating {h} kW (calculation core CALC-0.4, based on VDI 2078 / "
               "DIN EN 12831-1)",
    "Mögliche Aufstellorte für Außengeräte": "Possible locations for outdoor units",
    "Ich habe die Hinweise zur überschlägigen Auslegung gelesen.": "I have read the notes on the approximate "
                                                                   "sizing.",
    "Hinweise anzeigen": "Show notes",
    "Angebotsübersicht (PDF)": "Quotation summary (PDF)",
    "Bitte zuerst die Hinweise bestätigen.": "Please confirm the notes first.",
    "Heiz- und Kühllasten sind überschlägige Schätzwerte.": "Heating and cooling loads are rough estimates.",
    "Vereinfachte Kühllastabschätzung in Anlehnung an VDI 2078, keine vollständige VDI-2078-Fachberechnung.":
        "Simplified cooling load estimate based on VDI 2078, not a complete VDI 2078 calculation.",
    "Vereinfachte Heizlastabschätzung in Anlehnung an DIN EN 12831-1, keine vollständige "
    "Norm-Heizlastberechnung.": "Simplified heating load estimate based on DIN EN 12831-1, not a complete "
                                "standard heating load calculation.",
    "Die Konfiguration ersetzt keine Fachplanung.": "The configuration does not replace professional planning.",
    "Schall-, Elektro-, Kältemittel-, Kondensat- und Genehmigungsanforderungen sind gesondert zu prüfen.":
        "Noise, electrical, refrigerant, condensate and permit requirements must be checked separately.",
    "Eine dargestellte Förderfähigkeit ist keine Förderzusage.": "Eligibility for funding shown is no funding "
                                                                 "commitment.",

    # ------------------------------------------------------------------ Zubehör
    "Zubehör und Montagematerial": "Accessories and installation material",
    "Summe Zubehör: {s}": "Total accessories: {s}",
    "Leitungslänge je Innengerät": "Pipe length per indoor unit",
    "App-Steuerung (WLAN)": "App control (Wi-Fi)",
    "Internet-Gateways für Innengeräte ohne integriertes WLAN": "Internet gateways for indoor units without "
                                                                "built-in Wi-Fi",
    " ({n} von {gesamt} Geräten).": " ({n} of {gesamt} units).",
    "WLAN ist bei allen Innengeräten integriert (Climate 7000i / Class 8000i) – kein Gateway nötig.":
        "Wi-Fi is built into all indoor units (Climate 7000i / Class 8000i) – no gateway needed.",
    "Bördelfrei (Klemmring)": "Flare-free (compression)",
    "SAE-Klemmringverschraubungen, 2 je Leitung und Seite.": "SAE compression fittings, 2 per pipe and side.",
    "Kondensatpumpe": "Condensate pump",
    "Wenn das Kondensat nicht mit Gefälle abgeleitet werden kann. Kassetten haben eine integrierte Pumpe.":
        "If the condensate cannot be drained by gravity. Cassettes have a built-in pump.",
    "WLAN integriert": "Wi-Fi built in",
    "WLAN": "Wi-Fi",
    "kein WLAN eingebaut →": "no built-in Wi-Fi →",
    " (alternativ {g})": " (alternatively {g})",
    "Alle Zubehörartikel zeigen": "Show all accessories",
    "Auch Artikel, die nicht automatisch vorgeschlagen werden – Menge mit + erhöhen.":
        "Also items that are not proposed automatically – increase the quantity with +.",
    "Für diese Lösung gibt es keinen automatischen Zubehörvorschlag – z. B. Large-Split über 7 kW "
    "(Kältemittelleitung bauseits) ohne gewählten Aufstellort. Über „Alle Zubehörartikel zeigen“ können Sie "
    "Artikel manuell ergänzen.": "There is no automatic accessory proposal for this solution – e.g. Large-Split "
                                 "above 7 kW (refrigerant piping on site) without a selected location. Use “Show "
                                 "all accessories” to add items manually.",
    " · Menge von Hand geändert": " · quantity changed manually",
    "{p} je Stück": "{p} each",
    "Nicht erforderlich – WLAN integriert": "Not required – Wi-Fi built in",
    "Passt nicht zu den gewählten Geräten": "Does not fit the selected units",
    "nicht wählbar": "not selectable",
    "Geräte + Zubehör: **{s}**": "Units + accessories: **{s}**",
    "Vorschlag aus Konzept, Aufstellort und Leitungslänge – Mengen mit +/− anpassen.":
        "Proposal based on concept, location and pipe length – adjust quantities with +/−.",
    "Vorschlag wiederherstellen": "Restore proposal",
    "Zubehörmengen dienen als automatische Vorkalkulation und müssen projektbezogen geprüft werden.":
        "Accessory quantities are an automatic preliminary calculation and must be checked for each project.",
    "Aufstellung Außeneinheit": "Outdoor unit installation",
    "Kältemittelleitung": "Refrigerant piping",
    "Elektrik und Kommunikation": "Electrical and communication",
    "Kondensat": "Condensate",
    "Steuerung und App": "Controls and app",
    "Förderung": "Funding",
    "Adapter und Verschraubungen": "Adapters and fittings",
    "Pakete": "Packages",
    "Alternative zur Bodenkonsole: direkt auf Betonfundament, schallentkoppelt":
        "Alternative to the floor stand: directly on a concrete base, vibration-isolated",
    "Alternative zur Bodenkonsole für CL7000M 79/3, CL5000M 105/4 und 125/5 auf Betonfundament":
        "Alternative to the floor stand for CL7000M 79/3, CL5000M 105/4 and 125/5 on a concrete base",
    "Optional: Kondensatpumpe unter wandhängenden Innengeräten": "Optional: condensate pump below wall-mounted "
                                                                 "indoor units",
    "Optional: Alternative zum G 10-4 – laut aktuellem Katalog bis Q4/2026 verfügbar":
        "Optional: alternative to the G 10-4 – available until Q4/2026 according to the current catalogue",
    "Optional: Internet-Gateway für die App-Steuerung": "Optional: internet gateway for app control",
    "Optional: Gateway-Anschluss für Deckenkassetten, zusammen mit G 10-3":
        "Optional: gateway connection for ceiling cassettes, together with G 10-3",
    "Optional: Alternative zur Silent+ mini – Pumpe mit 800 mm Kabelkanal für Wandgeräte":
        "Optional: alternative to the Silent+ mini – pump with 800 mm trunking for wall-mounted units",
    "Optional: Einbaupumpe für Konsolen und Truhen": "Optional: built-in pump for consoles and floor units",
    "Optional: Wandmontage der Außeneinheit": "Optional: wall mounting of the outdoor unit",
    "Optional: Boden- oder Flachdachaufstellung der Außeneinheit": "Optional: ground or flat-roof installation of "
                                                                   "the outdoor unit",
    "Optional: Kabelregler; Wandgeräte benötigen zusätzlich das Verbindungsmodul MC R":
        "Optional: wired controller; wall-mounted units additionally need the MC R connection module",
    "Optional: potentialfreier Kontakt, externes Ein/Aus, Alarm (3000i, 3200i, 7000i)":
        "Optional: volt-free contact, external on/off, alarm (3000i, 3200i, 7000i)",
    "Optional: passend für {p}": "Optional: suitable for {p}",
    "Optional: für Geräte mit {p}": "Optional: for units with {p}",
    "G 10-3 laut aktuellem Katalog bis Q4/2026 verfügbar. Nachfolgeprodukt für die verbleibenden Gerätefamilien "
    "derzeit nicht eindeutig dokumentiert.": "G 10-3 available until Q4/2026 according to the current catalogue. "
                                             "A successor for the remaining unit families is currently not clearly "
                                             "documented.",
    "CF-Gerät: Gateway-Anschluss nötig": "CF unit: gateway connection required",
    "Kassette CL5000iM 4CC: Gateway-Anschluss nötig": "Cassette CL5000iM 4CC: gateway connection required",
    "Aufstellort Fassade/Wand: 1 je Außeneinheit": "Location facade/wall: 1 per outdoor unit",
    "Aufstellort Flachdach: 1 je Außeneinheit, aufgeständert über Schnee/Wasser":
        "Location flat roof: 1 per outdoor unit, raised above snow/water",
    "Aufstellort Boden: 1 je Außeneinheit": "Location ground: 1 per outdoor unit",
    "Grundausstattung: Kältemittelleitung {l} m je Innengerät": "Basic equipment: refrigerant pipe {l} m per "
                                                                "indoor unit",
    "Bördelfrei gewählt: 2 je Leitung und Seite": "Flare-free selected: 2 per pipe and side",
    "Grundausstattung: Steuerleitung je Innengerät (5,5 m je Kabel)": "Basic equipment: control cable per indoor "
                                                                      "unit (5.5 m per cable)",
    "Grundausstattung: Steuerleitung 2,5 mm² für 7-kW-Geräte": "Basic equipment: control cable 2.5 mm² for 7 kW "
                                                               "units",
    "Kältemittelleitung für Geräte über 7 kW ({raeume}) nicht als Paket im Katalog – Kupferrohr und Kabel "
    "bauseits nach Montageanleitung.": "Refrigerant piping for units above 7 kW ({raeume}) is not available as a "
                                       "package in the catalogue – copper pipe and cable on site according to "
                                       "the installation instructions.",
    "Grundausstattung: Kondensatablauf Ø 16 mm (Rolle 30 m)": "Basic equipment: condensate drain Ø 16 mm "
                                                              "(30 m roll)",
    "Kondensatpumpe gewählt: unter dem Wandgerät": "Condensate pump selected: below the wall-mounted unit",
    "Kondensatpumpe gewählt: Einbau in Konsole/Truhe": "Condensate pump selected: built into console/floor unit",
    "App-Steuerung gewählt": "App control selected",
    "BEG-Förderung: netzdienliche Schnittstelle je Climate 7000i Set": "BEG funding: grid-supportive interface "
                                                                       "per Climate 7000i set",
    "{betrag} günstiger als einzeln": "{betrag} cheaper than individually",
    "preisgleich zu den Einzelteilen, aber nur eine Bestellposition": "same price as the individual parts, but "
                                                                      "only one order line",
    "{typ} ({raeume}): auch als {name}, Bestell-Nr. {nr}, {preis} je Raum – Set mit 5 m Leitung, Kabel, "
    "Kondensatschlauch, Klemmringen und Konsole; {vergleich}.": "{typ} ({raeume}): also available as {name}, "
                                                               "order no. {nr}, {preis} per room – set with 5 m "
                                                               "pipe, cable, condensate hose, compression fittings "
                                                               "and bracket; {vergleich}.",
    "WLAN bei allen Innengeräten integriert (Climate 7000i / Class 8000i)": "Wi-Fi built into all indoor units "
                                                                            "(Climate 7000i / Class 8000i)",
    "passt nicht zu den gewählten Innengeräten": "does not fit the selected indoor units",
    "nur für Climate 7000i Single-Split": "only for Climate 7000i single-split",
    "nur für CL7000i-Set 26 E bzw. CL3200i-Set 26 WE": "only for CL7000i-Set 26 E or CL3200i-Set 26 WE",
    # Zubehör-Artikel (Katalogbezeichnungen)
    "Smart Grid Modul MSG-1": "Smart Grid module MSG-1",
    "Internet-Gateway G 10-3": "Internet gateway G 10-3",
    "Internet-Gateway G 10-4": "Internet gateway G 10-4",
    "Climate 5000 M, Climate 7000 M": "Climate 5000 M, Climate 7000 M",
    "Climate 7000i Single": "Climate 7000i single-split",
    "Verbindungsmodul MC R": "Connection module MC R",
    "G 10 CLC Gateway-Anschluss": "G 10 CLC gateway connection",
    "G 10 CLC-1 Gateway-Anschluss": "G 10 CLC-1 gateway connection",
    'Multi-Split-Adapter 3/8" (ODU) auf 1/4" (IDU)': 'Multi-split adapter 3/8" (ODU) to 1/4" (IDU)',
    'Multi-Split-Adapter 1/4" (ODU) auf 3/8" (IDU)': 'Multi-split adapter 1/4" (ODU) to 3/8" (IDU)',
    'Multi-Split-Adapter 3/8" (ODU) auf 1/2" (IDU)': 'Multi-split adapter 3/8" (ODU) to 1/2" (IDU)',
    'Multi-Split-Adapter 1/2" (ODU) auf 3/8" (IDU)': 'Multi-split adapter 1/2" (ODU) to 3/8" (IDU)',
    'Multi-Split-Adapter 1/2" (ODU) auf 5/8" (IDU)': 'Multi-split adapter 1/2" (ODU) to 5/8" (IDU)',
    "Kommunikationskabel ≤ 5,3 kW": "Communication cable ≤ 5.3 kW",
    "Kommunikationskabel 7 kW": "Communication cable 7 kW",
    "Kabelregler CRC R-1": "Wired controller CRC R-1",
    "Kabelregler CRC R-3": "Wired controller CRC R-3",
    "Bodenkonsole": "Floor stand",
    "Kleine Wandkonsole": "Small wall bracket",
    "Spiralschlauch Ø 16 mm": "Spiral hose Ø 16 mm",
    'Doppelrohr 1/4" + 3/8", 5 m': 'Twin pipe 1/4" + 3/8", 5 m',
    'Doppelrohr 1/4" + 3/8", 10 m': 'Twin pipe 1/4" + 3/8", 10 m',
    'Doppelrohr 1/4" + 3/8", 20 m': 'Twin pipe 1/4" + 3/8", 20 m',
    'Doppelrohr 1/4" + 1/2", 5 m': 'Twin pipe 1/4" + 1/2", 5 m',
    'Doppelrohr 1/4" + 1/2", 10 m': 'Twin pipe 1/4" + 1/2", 10 m',
    'Doppelrohr 1/4" + 1/2", 20 m': 'Twin pipe 1/4" + 1/2", 20 m',
    'Doppelrohr 3/8" + 5/8", 5 m': 'Twin pipe 3/8" + 5/8", 5 m',
    'Kälteleitung 3/8" + 5/8", 10 m': 'Refrigerant pipe 3/8" + 5/8", 10 m',
    'Kälteleitung 3/8" + 5/8", 20 m': 'Refrigerant pipe 3/8" + 5/8", 20 m',
    'SAE-Klemmringverschraubung 1/4"': 'SAE compression fitting 1/4"',
    'SAE-Klemmringverschraubung 3/8"': 'SAE compression fitting 3/8"',
    'SAE-Klemmringverschraubung 1/2"': 'SAE compression fitting 1/2"',
    'SAE-Klemmringverschraubung 5/8"': 'SAE compression fitting 5/8"',
    "Kondensatpumpe Geräteeinbau": "Condensate pump, built-in",
    "Kondensatpumpe Silent+ mini": "Condensate pump Silent+ mini",
    "Kondensatpumpe inkl. Kanal": "Condensate pump incl. trunking",
    "Auftragspauschale": "Order flat fee",
    "Inbetriebnahme Außeneinheit bis 18 kW": "Commissioning outdoor unit up to 18 kW",
    "Inbetriebnahme je Inneneinheit": "Commissioning per indoor unit",
    "Zusätzlicher Anschluss kältetechnische Rohrverbindungen": "Additional connection of refrigerant pipe joints",
    "Service-Pauschale Kältemittel R32": "Service flat fee refrigerant R32",
    "Dämpfungssockel-Set 450 mm": "Damping base set 450 mm",
    "Dämpfungssockel-Set 600 mm": "Damping base set 600 mm",
    "Basispaket BOPA CL701 (Bodenkonsole)": "Basic package BOPA CL701 (floor stand)",
    "Basispaket BOPA CL702 (Wandkonsole)": "Basic package BOPA CL702 (wall bracket)",
    "Basispaket BOPA CL321 (Bodenkonsole)": "Basic package BOPA CL321 (floor stand)",
    "Basispaket BOPA CL322 (Wandkonsole)": "Basic package BOPA CL322 (wall bracket)",
    # „passend für“-Angaben aus dem Katalog
    "2,5 und 3,5 kW": "2.5 and 3.5 kW",
    "5,3 kW": "5.3 kW",
    "Climate Geräteserie": "Climate product series",
    "Climate Geräteserie (R32)": "Climate product series (R32)",
    "Climate Split-Klimageräte": "Climate split air conditioners",
    "Inneneinheiten mit 16 mm Kondensatablauf": "indoor units with 16 mm condensate drain",
    "wandhängende Inneneinheiten": "wall-mounted indoor units",

    # ------------------------------------------------------------------ Geräteauswahl (Konzepte, Hinweise)
    "Ein Multi-Split-System": "One multi-split system",
    "Alle Räume an möglichst wenigen Außeneinheiten. Wenige Geräte an der Fassade, längere Kältemittelleitungen.":
        "All rooms on as few outdoor units as possible. Few units on the facade, longer refrigerant pipes.",
    "Multi-Split je Geschoss": "Multi-split per floor",
    "Je Geschoss ein eigenes System mit kurzen Leitungswegen; ein einzelner Raum auf einer Etage erhält ein "
    "Single-Split-Set.": "A separate system per floor with short pipe runs; a single room on a floor gets a "
                         "single-split set.",
    "Single-Split je Raum": "Single-split per room",
    "Jeder Raum erhält ein eigenes Set aus Außen- und Inneneinheit – unabhängig und effizient, aber mehr "
    "Außengeräte.": "Each room gets its own set of outdoor and indoor unit – independent and efficient, but more "
                    "outdoor units.",
    "Die gewünschte Farbe gibt es nur als Single-Split-Set – deshalb erhält jeder Raum ein eigenes Set.":
        "The requested colour is only available as a single-split set – so each room gets its own set.",
    "Large-Split für große Räume": "Large-Split for large rooms",
    "Leistungsstarke Einzelanlagen bis 16 kW mit Decken-, Truhen- oder Konsolengeräten – auch als Twin/Triple mit "
    "mehreren Innengeräten an einer Außeneinheit. Weniger Geräte, ideal für Werkstatt, Halle und Laden.":
        "Powerful single systems up to 16 kW with ceiling, floor or console units – also as twin/triple with "
        "several indoor units on one outdoor unit. Fewer units, ideal for workshops, halls and shops.",
    "Räume mit Wunschfarbe erhalten ein eigenes Set in dieser Farbe.": "Rooms with a requested colour get their own "
                                                                       "set in that colour.",
    "keine passende Lösung": "no suitable solution",
    " als {bauart}": " as {bauart}",
    "{raum}: Kein Single-Split-Set{art} deckt {k} kW Kühl-/{h} kW Heizlast.":
        "{raum}: no single-split set{art} covers {k} kW cooling / {h} kW heating load.",
    "{raum}: {linie} deckt die Last nicht – andere Gerätelinie gewählt.":
        "{raum}: {linie} does not cover the load – another product line selected.",
    "{raum}: „{farbe}“ gibt es nicht als {linie} – {neu} gewählt.":
        "{raum}: “{farbe}” is not available as {linie} – {neu} selected.",
    "{raum}: Farbe „{farbe}“ in passender Größe nicht verfügbar – Standardfarbe gewählt.":
        "{raum}: colour “{farbe}” not available in a suitable size – standard colour selected.",
    "{raum}: Nur mit noch nicht lieferbarem Gerät lösbar.": "{raum}: only possible with a unit not yet available.",
    "{raum}: {typ} benötigt einen Drehstromanschluss (400 V).": "{raum}: {typ} requires a three-phase supply "
                                                                "(400 V).",
    "{raum}: {n} Innengeräte an einer Außeneinheit ({typ}).": "{raum}: {n} indoor units on one outdoor unit "
                                                              "({typ}).",
    "{linie} als Multi-Split hier nicht möglich – andere Gerätelinie gewählt.":
        "{linie} not possible as multi-split here – another product line selected.",
    "{raum}: Wunschfarbe nicht verfügbar – Standardfarbe gewählt.": "{raum}: requested colour not available – "
                                                                    "standard colour selected.",
    "Enthält noch nicht lieferbare Geräte.": "Contains units that are not yet available.",
    "Keine zulässige Multi-Split-Kombination für {n} Räume ({k} kW Kühl-/{h} kW Heizlast).":
        "No permissible multi-split combination for {n} rooms ({k} kW cooling / {h} kW heating load).",
    "{raum}: „{farbe}“ gibt es bis {max} kW je Gerät – der Raum erhält {n} Geräte in dieser Farbe. Für ein "
    "einzelnes Gerät die Farbe auf „Keine Präferenz“ stellen.": "{raum}: “{farbe}” is available up to {max} kW per "
                                                               "unit – the room gets {n} units in this colour. For "
                                                               "a single unit set the colour to “No preference”.",
    "Auslaufartikel – nicht mehr im Ergänzungskatalog 09/2026 (Preis 03/2026)":
        "Discontinued item – no longer in the supplementary catalogue 09/2026 (price 03/2026)",
    "verfügbar ab Q3/2026": "available from Q3/2026",
    "nur solange Vorrat reicht": "only while stocks last",
    "verfügbar bis Q3/2026": "available until Q3/2026",
    "Katalogfehler (Kühlleistung min 5.8 / nenn 5.2 / max 4.7 kW) – nur Nennleistung verwendet":
        "Catalogue error (cooling capacity min 5.8 / rated 5.2 / max 4.7 kW) – rated capacity used only",
    "Wandmontage: Tragfähigkeit der Wand und Körperschall zu angrenzenden Schlafräumen prüfen.":
        "Wall mounting: check the load-bearing capacity of the wall and structure-borne noise to adjacent bedrooms.",
    "Bodenaufstellung vor dem Haus: Bodenkonsole mit Schwingungsdämpfern auf ebenem, tragfähigem Untergrund, "
    "Kondensat- und Abtauwasser frostsicher ableiten. Alternative auf Betonfundament: Dämpfungssockel-Set.":
        "Ground installation in front of the house: floor stand with vibration dampers on a level, load-bearing "
        "surface; drain condensate and defrost water frost-free. Alternative on a concrete base: damping base set.",
    "Flachdach: Außeneinheit auf Bodenkonsole mit Schwingungsdämpfern, auf Bautenschutzmatte bzw. "
    "Lastverteilplatten – die Dachabdichtung nicht durchdringen; Dachlast und Windsog prüfen lassen.":
        "Flat roof: outdoor unit on a floor stand with vibration dampers, on a protection mat or load distribution "
        "plates – do not penetrate the roof membrane; have roof load and wind suction checked.",
    "Flachdach: Kondensat- und Abtauwasser zum Dachablauf führen, Vereisung der Dachfläche vermeiden; "
    "Mindestabstände zur Attika und zu Lichtkuppeln nach Montageanleitung einhalten.":
        "Flat roof: route condensate and defrost water to the roof drain, avoid icing of the roof surface; keep "
        "minimum distances to the parapet and skylights according to the installation instructions.",
    "Flachdach: Leitungsführung durch die Dachhaut nur über Dachdurchführung oder Fassade; maximale Leitungslänge "
    "und Höhendifferenz der Außeneinheit beachten.": "Flat roof: route pipes through the roof only via a roof "
                                                     "penetration or the facade; observe the maximum pipe length "
                                                     "and height difference of the outdoor unit.",
    "Flachdach: sicheren Zugang für Wartung einplanen (Absturzsicherung nach DGUV/ASR A2.1).":
        "Flat roof: plan safe access for maintenance (fall protection according to DGUV/ASR A2.1).",
    "Large-Split-Außeneinheiten: Traglast von Konsole bzw. Sockel gegen das Gerätegewicht prüfen.":
        "Large-Split outdoor units: check the load capacity of the stand or base against the unit weight.",
    "Montagehinweise beruhen auf allgemeinen Fachregeln und dienen der überschlägigen Planung. Maßgeblich sind die "
    "jeweils gültigen Montageanleitungen des Herstellers.": "Installation notes are based on general technical "
                                                           "rules and serve for preliminary planning. The "
                                                           "manufacturer's current installation instructions are "
                                                           "authoritative.",

    # ------------------------------------------------------------------ Katalog
    "Gesamtkatalog 03/2026 + Ergänzungskatalog 09/2026": "Main catalogue 03/2026 + supplementary catalogue 09/2026",
    "Unverbindliche Preisempfehlung netto, zzgl. MwSt., Montage und Material (09/2026); Artikel ohne Eintrag im "
    "Ergänzungskatalog: Stand 03/2026": "Recommended retail price, net, plus VAT, installation and material "
                                        "(09/2026); items not in the supplementary catalogue: as of 03/2026",

    # ------------------------------------------------------------------ PDF-Angebot
    "Climate · Split-Klima Angebotsübersicht": "Climate · Split AC quotation summary",
    "SplitConfigCore {v} · Konfigurations-ID {id} · Seite {s}/{{nb}}":
        "SplitConfigCore {v} · Configuration ID {id} · Page {s}/{{nb}}",
    "Projekt: {name} · Standort: {ort} · Datum: {datum} · Baujahr: {bj} · Betrieb: {betrieb} · ":
        "Project: {name} · Location: {ort} · Date: {datum} · Year built: {bj} · Operation: {betrieb} · ",
    "Aufstellung Außeneinheit: {a} · ": "Outdoor unit location: {a} · ",
    "Konfigurations-ID: {id}": "Configuration ID: {id}",
    "Empfohlene Lösung: {name}": "Recommended solution: {name}",
    "Gerätepreis {preis}": "Unit price {preis}",
    "Stand {q}": "Source: {q}",
    "Kühlen und Heizen": "Cooling and heating",
    "nur Kühlen": "cooling only",
    "nur Heizen": "heating only",
    "Systeme": "Systems",
    "Geräte": "Units",
    "Last Kühlen": "Cooling load",
    "Leistung Kühlen": "Cooling capacity",
    "Last Heizen": "Heating load",
    "Leistung Heizen": "Heating capacity",
    "Räume und Inneneinheiten": "Rooms and indoor units",
    "Fläche": "Area",
    "Gerät": "Unit",
    "Bauart": "Type",
    "Farbe": "Colour",
    "Stückliste Geräte": "Parts list units",
    "Summe Geräte": "Total units",
    "Summe Zubehör": "Total accessories",
    "Geräte + Zubehör": "Units + accessories",
    "Leitungslänge je Innengerät {l} m.": "Pipe length per indoor unit {l} m.",
    "Optional: Inbetriebnahme durch den Bosch-Kundendienst und Zubehör":
        "Optional: commissioning by Bosch customer service and accessories",
    "Summe optional": "Total optional",
    "Hinweise zu Lieferbarkeit, Auswahl und Aufstellung": "Notes on availability, selection and installation",
    "Auslegungsgrundlagen": "Design basis",
    "{daemm} · {glas}verglasung · Sonnenschutz: {schutz} · Auslegung Sommer {sommer} °C · Norm-Außentemperatur "
    "{ta} °C ({quelle}) · Soll {soll_k} / {soll_h} °C. ": "{daemm} · {glas} glazing · sun protection: {schutz} · "
                                                         "summer design {sommer} °C · design outdoor temperature "
                                                         "{ta} °C ({quelle}) · set point {soll_k} / {soll_h} °C. ",
    "Kühllast in Anlehnung an VDI 2078, Heizlast in Anlehnung an DIN EN 12831-1 (Rechenkern CALC-0.4). "
    "Geräteauswahl nach den zulässigen Kombinationen des Bosch-Katalogs.":
        "Cooling load based on VDI 2078, heating load based on DIN EN 12831-1 (calculation core CALC-0.4). Unit "
        "selection according to the permissible combinations of the Bosch catalogue.",
    " Hinweise bestätigt am {zeit}.": " Notes confirmed on {zeit}.",
    "Standardwert": "default value",
    "Altbau": "Old building",
    "Bestand modernisiert": "Existing building, modernised",
    "Neubau / gut gedämmt": "New building / well insulated",
    "keine / unbekannt": "none / unknown",
    "Innenjalousie / Vorhang": "Interior blind / curtain",
    "Jalousie außen": "External blind",
    "Rollladen außen": "External roller shutter",
    "Die angezeigten Heiz- und Kühllasten sind überschlägige Schätzwerte auf Basis vereinfachter Gebäude-, Klima- "
    "und Nutzungsannahmen. Die Berechnung erfolgt vereinfacht in Anlehnung an die Methodik der VDI 2078 bzw. DIN "
    "EN 12831-1, stellt jedoch keine vollständige normgerechte Fachberechnung dar. Sie ersetzt keine "
    "fachtechnische Planung oder Prüfung am Gebäude. Die endgültige Auswahl, Installation und Inbetriebnahme muss "
    "durch einen qualifizierten Fachbetrieb erfolgen. Schall-, Elektro-, Kältemittel-, Kondensat-, Brandschutz- "
    "und Genehmigungsanforderungen sind gesondert zu prüfen. Eine dargestellte Förderfähigkeit ist keine "
    "Förderzusage.": "The heating and cooling loads shown are rough estimates based on simplified building, "
                     "climate and usage assumptions. The calculation is simplified and based on the methodology of "
                     "VDI 2078 and DIN EN 12831-1, but is not a complete calculation in accordance with the "
                     "standards. It does not replace professional planning or inspection of the building. Final "
                     "selection, installation and commissioning must be carried out by a qualified specialist "
                     "contractor. Noise, electrical, refrigerant, condensate, fire protection and permit "
                     "requirements must be checked separately. Eligibility for funding shown is no funding "
                     "commitment.",

    # ------------------------------------------------------------------ Planungs-Assistent
    "Planungs-Assistent": "Planning assistant",
    "Hallo! Beschreiben Sie einfach, was an der Planung anders sein soll – ich passe sie an und zeige, was sich "
    "ändert.": "Hello! Just describe what should be different in the planning – I'll adjust it and show what "
               "changes.",
    "Der Plan hat keinen Nordpfeil – das Wohnzimmer liegt im Norden.": "The plan has no north arrow – the living "
                                                                       "room faces north.",
    "Das Haus ist von 1958, die Fassade wurde 1990 gedämmt.": "The house is from 1958, the facade was insulated in "
                                                              "1990.",
    "Geht es günstiger? Die Farbe ist mir egal.": "Can it be cheaper? I don't mind the colour.",
    "Was soll anders sein?": "What should be different?",
    "Der Assistent arbeitet …": "The assistant is working …",
    "Der Assistent ist auf diesem Server noch nicht eingerichtet (API-Schlüssel fehlt).":
        "The assistant is not set up on this server yet (API key missing).",
    "Ändert nur Ihre Planung in dieser Sitzung. Eingaben werden zur Auswertung an die Claude API übertragen – "
    "keine personenbezogenen Kundendaten eingeben.": "Only changes your planning in this session. Input is sent to "
                                                     "the Claude API for processing – do not enter personal "
                                                     "customer data.",
    "Für diese Sitzung ist das Nachrichtenlimit erreicht – bitte die Seite neu laden.":
        "The message limit for this session has been reached – please reload the page.",
    "Geändert:": "Changed:",
    "Rückgängig": "Undo",
    "Rückgängig gemacht.": "Undone.",
    "Preis {a} → {b}": "Price {a} → {b}",
    "Lösung: {l}": "Solution: {l}",
    "Lage {l}": "position {l}",
    "Fläche {a} m²": "area {a} m²",
    "Dach {d}": "roof {d}",
    "Dachfenster {a} m²": "roof windows {a} m²",
    "Farbe {f}": "colour {f}",
    "Gerätewunsch {g}": "unit preference {g}",
    "Außenwände": "exterior walls",
    "{r} {l} m/Fenster {f} m²": "{r} {l} m/windows {f} m²",
    "{raum}: Fenster {r} {a} → {b} m²": "{raum}: windows {r} {a} → {b} m²",
    "Raum „{name}“ angelegt ({art}, {a} m²)": "Room “{name}” added ({art}, {a} m²)",
    "Raum „{name}“ entfernt": "Room “{name}” removed",
    "Grundriss um {g}° im Uhrzeigersinn gedreht ({n} Räume)": "Floor plan rotated {g}° clockwise ({n} rooms)",
    "Nachträgliche Dämmung: {art} ({raeume})": "Retrofit insulation: {art} ({raeume})",
    "alle Räume": "all rooms",
    "Projekt:": "Project:",
    "Projektname {n}": "project name {n}",
    "Standort {ort} (Norm-Außentemperatur {t} °C)": "location {ort} (design outdoor temperature {t} °C)",
    "Baujahr {bj} ({d})": "year built {bj} ({d})",
    "Leitungslänge {l} m": "pipe length {l} m",
    "keine Änderung": "no change",
    "Lösung: Empfehlung": "Solution: recommendation",
    "Lösung gewählt: {name}": "Solution selected: {name}",
    "Der Assistent ist nicht eingerichtet (API-Schlüssel fehlt).": "The assistant is not set up (API key missing).",
    "Zu viele Anfragen – bitte kurz warten und erneut senden.": "Too many requests – please wait a moment and send "
                                                                "again.",
    "Claude API meldet einen Fehler ({code}).": "The Claude API reports an error ({code}).",
    "Dazu kann ich leider nichts beitragen.": "Unfortunately I can't help with that.",
    "(Antwort gekürzt.)": "(Answer shortened.)",
    "Ich habe die Bearbeitung nach mehreren Schritten angehalten – bitte genauer beschreiben.":
        "I stopped after several steps – please describe it more precisely.",
    "Erledigt.": "Done.",
    # Lagen und Dachformen (Rechenkern-Labels)
    "Innenliegend": "Interior",
    "1 Außenwand": "1 exterior wall",
    "2 Außenwände / Eckraum": "2 exterior walls / corner room",
    "3 Außenwände": "3 exterior walls",
    "Dachgeschoss": "Attic floor",
    "DG-Eckraum": "Attic corner room",
    "Satteldach Süd": "Gable roof south",
    "Satteldach Nord": "Gable roof north",
    "Satteldach Ost/West": "Gable roof east/west",

    # ------------------------------------------------------------------ Beispielhaus (Raumnamen, Hinweise)
    "Wohnen/Essen": "Living/dining",
    "Arbeiten": "Study",
    "Kind 1": "Child 1",
    "Kind 2": "Child 2",
    "Studio": "Studio",
    "Beispielergebnis zum Ausprobieren – keine echte Planerkennung.": "Example result to try out – no real plan "
                                                                      "recognition.",
    "Fensterhöhen im OG mit 1,35 m angenommen (keine Ansicht vorhanden).": "Window heights on the upper floor "
                                                                           "assumed at 1.35 m (no elevation "
                                                                           "available).",
    "Terrasse Westseite (EG)": "Terrace, west side (ground floor)",
    "Direkt am Wohnzimmer, kurzer Leitungsweg, gut zugänglich.": "Right next to the living room, short pipe run, "
                                                                 "easily accessible.",
    "Fassade Ostseite neben Küche": "East facade next to the kitchen",
    "Abseits der Schlafräume, kurze Leitung zu Küche und Arbeiten.": "Away from the bedrooms, short pipe to "
                                                                     "kitchen and study.",
    "Beispieldaten – Nordpfeil im Lageplan (Plan-Oben = Norden)": "Example data – north arrow in the site plan "
                                                                  "(top of plan = north)",

    # ------------------------------------------------------------------ Personen (Seminar, Forum, Schulung)
    "Seminar / Schulung": "Seminar / training",
    "Seminar": "Seminar",
    "Personen gleichzeitig": "People at the same time",
    "Personen, die sich in der Spitzenzeit gleichzeitig im Raum aufhalten. 0 = übliche Nutzung (in der Grundlast "
    "enthalten). Je Person 120 W sitzend bzw. 150 W stehend/aktiv, inkl. Feuchte (VDI 2078).":
        "People present in the room at the same time at peak. 0 = normal use (included in the base load). 120 W "
        "per person seated or 150 W standing/active, including moisture (VDI 2078).",
    "Tätigkeit": "Activity",
    "Sitzend · 120 W/Person": "Seated · 120 W/person",
    "Stehend, aktiv · 150 W/Person": "Standing, active · 150 W/person",
    "Sitzend: Schulung, Seminar, Besprechung. Stehend/aktiv: Empfang, Ausstellung, Veranstaltung mit Bewegung.":
        "Seated: training, seminar, meeting. Standing/active: reception, exhibition, events with movement.",
    "Fensterlüftung: 30 m³/h Außenluft je Person kommen ungekühlt herein und werden in der Kühllast mitgerechnet. "
    "Lüftungsanlage mit Wärmerückgewinnung (WRG): nur ein Restanteil von etwa 25 % zählt.":
        "Window ventilation: 30 m³/h of uncooled outdoor air per person enters and is included in the cooling "
        "load. Ventilation system with heat recovery (HR): only a residual share of about 25 % counts.",
    "Frischluft": "Fresh air",
    "Fensterlüftung": "Window ventilation",
    "Lüftungsanlage mit WRG": "Ventilation system with HR",
    "Personen: +{w} kW Wärme · Außenluft {q} m³/h ({je} m³/h je Person).":
        "People: +{w} kW heat · outdoor air {q} m³/h ({je} m³/h per person).",
    "Split-Klimageräte kühlen nur die Raumluft und liefern keine Frischluft. Bei {n} Personen wird eine "
    "Lüftungsanlage mit Wärmerückgewinnung empfohlen. Die Kühllast enthält hier die Außenluft der Fensterlüftung; "
    "im Winter erhöht sie zusätzlich die Heizlast (in der Heizlast nicht enthalten).":
        "Split air conditioners only cool the room air and do not supply fresh air. With {n} people, a "
        "ventilation system with heat recovery is recommended. The cooling load here includes the outdoor air of "
        "window ventilation; in winter it also increases the heating load (not included in the heating load).",
    "Personen": "People",
    "{n} Pers.": "{n} people",
    " · {n} Pers.": " · {n} people",
    "{n} Personen": "{n} people",

    # ------------------------------------------------------------------ Laden/Speichern
    "Datei ist zu groß für eine Konfiguration.": "The file is too large for a configuration.",
    "Datei ist keine Textdatei (UTF-8).": "The file is not a text file (UTF-8).",
    "Kein gültiges JSON (Zeile {n}).": "Not valid JSON (line {n}).",
    "Das ist keine gespeicherte Konfiguration dieses Programms.": "This is not a configuration saved by this "
                                                                  "program.",
    "Die Datei stammt aus einer neueren Programmversion – bitte Programm aktualisieren.":
        "The file comes from a newer program version – please update the program.",
    "Konfiguration enthält ungültige Werte (Feld „{feld}“).": "The configuration contains invalid values (field "
                                                              "“{feld}”).",
}
