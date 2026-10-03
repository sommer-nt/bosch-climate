# Betrieb auf eigenem Server: klima.sommer-nt.de

Zwei Varianten:

- **A) Vorhandener nginx** (Server mit nginx und weiteren Apps) → Abschnitt „Variante nginx“
- **B) Frischer Server** → Caddy als Webserver, holt das HTTPS-Zertifikat automatisch

---

## Variante nginx (vorhandener Server)

Die App läuft im Container und ist nur lokal auf **127.0.0.1:8502** erreichbar
(8501 bleibt für andere Apps frei). nginx leitet `klima.sommer-nt.de` dorthin.

**1. DNS:** A-Record `klima` → IP des Servers (siehe unten, Schritt 1).

**2. App starten**
```bash
git clone -b claude/stoic-allen-jg56ti https://github.com/sommer-nt/bosch-climate.git
cd bosch-climate/deploy
cp .env.beispiel .env && nano .env        # API-Schlüssel, Passwort; APP_PORT=8502
docker compose -f docker-compose.nginx.yml up -d --build
curl http://127.0.0.1:8502/_stcore/health  # → ok
```

**3. nginx einrichten**
```bash
sudo cp nginx-klima.sommer-nt.de.conf /etc/nginx/sites-available/klima.sommer-nt.de
sudo ln -s /etc/nginx/sites-available/klima.sommer-nt.de /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```
(Ohne `sites-available`: Datei nach `/etc/nginx/conf.d/klima.sommer-nt.de.conf` kopieren.)

**4. HTTPS-Zertifikat**
```bash
sudo certbot --nginx -d klima.sommer-nt.de
```

Fertig: **https://klima.sommer-nt.de**

Wichtig in der nginx-Konfiguration sind die WebSocket-Zeilen (`Upgrade`/`Connection`) –
ohne sie bleibt die Seite weiß – sowie `client_max_body_size 50M` für große Pläne.

Neue Version: `git pull && docker compose -f docker-compose.nginx.yml up -d --build`

---

## Version 2 parallel: climate.sommer-nt.de

Version 2 (Gesamtsortiment, Auswahlkarten, Produktbilder, Katalogpreise) läuft als **zweiter
Container** neben Version 1 – gleiches Repository, gleiche `.env`, eigener Port **8503** und
eigenes Compose-Projekt `climate`. Version 1 auf klima.sommer-nt.de bleibt unverändert.

**1. DNS:** CNAME `climate` → `danisox.ddns.net` (bzw. derselbe Eintrag wie bei `klima`).
Prüfen: `dig +short climate.sommer-nt.de` zeigt die Server-IP.

**2. Code holen und Version 2 starten**
```bash
cd ~/bosch-climate && git pull
cd deploy
docker compose -p climate -f docker-compose.v2.yml up -d --build
curl http://127.0.0.1:8503/_stcore/health   # → ok
```

**3. nginx und HTTPS**
```bash
sudo cp nginx-climate.sommer-nt.de.conf /etc/nginx/sites-available/climate.sommer-nt.de
sudo ln -s /etc/nginx/sites-available/climate.sommer-nt.de /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d climate.sommer-nt.de
```

Fertig: **https://climate.sommer-nt.de** (gleiches Passwort wie Version 1).

Neue Version 2: `cd ~/bosch-climate/deploy && git pull && docker compose -p climate -f docker-compose.v2.yml up -d --build`

---

## Variante Caddy (frischer Server)

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
