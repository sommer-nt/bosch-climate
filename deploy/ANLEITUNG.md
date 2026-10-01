# Betrieb auf eigenem Server: klima.sommer-nt.de

Die App läuft als Docker-Container, davor **Caddy** als Webserver. Caddy holt das
HTTPS-Zertifikat (Let's Encrypt) automatisch und erneuert es selbst.

## Voraussetzungen

- Ein Server mit öffentlicher IP-Adresse (z. B. Hetzner/IONOS, Ubuntu) und Docker inkl. `docker compose`
- Ports **80 und 443** sind am Server bzw. in der Firewall offen
- Zugriff auf die DNS-Einstellungen von `sommer-nt.de`

## 1. DNS-Eintrag anlegen

Beim Anbieter der Domain `sommer-nt.de` einen **A-Record** anlegen:

| Typ | Name | Wert |
|---|---|---|
| A | `klima` | IP-Adresse des Servers |

Prüfen (nach einigen Minuten): `ping klima.sommer-nt.de` zeigt die Server-IP.

## 2. Code auf den Server holen

```bash
git clone -b claude/stoic-allen-jg56ti https://github.com/sommer-nt/bosch-climate.git
cd bosch-climate/deploy
```

Ist das Repository privat, fragt Git nach Benutzername und Passwort. Als Passwort ein
GitHub-Token verwenden (GitHub → Settings → Developer settings → Personal access tokens,
Berechtigung „Contents: Read“ für `bosch-climate`).

## 3. Zugangsdaten eintragen

```bash
cp .env.beispiel .env
nano .env
```

```
DOMAIN=klima.sommer-nt.de
ANTHROPIC_API_KEY=sk-ant-...
APP_PASSWORT=ein-sicheres-passwort
```

## 4. Starten

```bash
docker compose up -d --build
```

Nach 1–2 Minuten ist die App unter **https://klima.sommer-nt.de** erreichbar
(zuerst die Passwortseite).

## Im Betrieb

| Aufgabe | Befehl (im Ordner `deploy`) |
|---|---|
| Neue Version einspielen | `git pull && docker compose up -d --build` |
| Logs ansehen | `docker compose logs -f app` |
| Zertifikat/Caddy-Logs | `docker compose logs -f caddy` |
| Stoppen | `docker compose down` |
| Status | `docker compose ps` |

## Nur lokal testen (ohne Domain, z. B. Docker Desktop)

```bash
cd bosch-climate
docker build -t splitklima .
docker run --rm -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... -e APP_PASSWORT=test splitklima
```

Dann im Browser: http://localhost:8501

## Fehlersuche

- **Kein Zertifikat / Seite nicht erreichbar:** DNS-Eintrag prüfen, Ports 80/443 offen?
  `docker compose logs caddy` zeigt den Grund.
- **„Kein API-Schlüssel gefunden“:** `ANTHROPIC_API_KEY` in `.env` prüfen, danach
  `docker compose up -d` (Container wird mit neuen Werten neu gestartet).
