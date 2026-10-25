# Betrieb auf eigenem Server: climate.sommer-nt.de

Die App läuft als Docker-Container und ist nur lokal auf **127.0.0.1:8503** erreichbar.
nginx leitet `climate.sommer-nt.de` dorthin, certbot holt das HTTPS-Zertifikat.

## Einrichten (einmalig)

**1. DNS:** Eintrag `climate` → Server (A-Record auf die IP bzw. CNAME auf den DynDNS-Namen).
Prüfen: `dig +short climate.sommer-nt.de` zeigt die Server-IP.

**2. Code holen und starten**
```bash
git clone https://github.com/sommer-nt/bosch-climate.git ~/bosch-climate-v2
cd ~/bosch-climate-v2/deploy
cp .env.beispiel .env && nano .env        # API-Schlüssel, Passwort
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

Fertig: **https://climate.sommer-nt.de** (zuerst die Passwortseite).

Wichtig in der nginx-Konfiguration sind die WebSocket-Zeilen (`Upgrade`/`Connection`) – ohne sie bleibt
die Seite weiß – sowie `client_max_body_size 50M` für große Pläne.

## Im Betrieb

| Aufgabe | Befehl (im Ordner `~/bosch-climate-v2/deploy`) |
|---|---|
| Neue Version einspielen | `git pull && docker compose -p climate -f docker-compose.v2.yml up -d --build` |
| Nach Änderung der `.env` | `docker compose -p climate -f docker-compose.v2.yml up -d --force-recreate` |
| Logs ansehen | `docker compose -p climate -f docker-compose.v2.yml logs -f app` |
| Status | `docker compose -p climate -f docker-compose.v2.yml ps` |
| Stoppen | `docker compose -p climate -f docker-compose.v2.yml down` |

## Nur lokal testen (ohne Domain)

```bash
docker build -t climate .
docker run --rm -p 8501:8501 -e ANTHROPIC_API_KEY=sk-ant-... -e APP_PASSWORT=test climate \
  streamlit run app_v2.py --server.address=0.0.0.0
```

Dann im Browser: http://localhost:8501 (englisch: http://localhost:8501/?lang=en)

## Fehlersuche

- **Seite weiß / lädt endlos:** WebSocket-Zeilen in der nginx-Konfiguration prüfen, danach
  `sudo nginx -t && sudo systemctl reload nginx`.
- **502 Bad Gateway:** Container läuft nicht → Status und Logs (siehe oben).
- **Kein Zertifikat:** DNS-Eintrag prüfen, Port 80 offen?
- **„Kein gültiger API-Schlüssel“:** `ANTHROPIC_API_KEY` in `.env` prüfen, danach `up -d --force-recreate`.
