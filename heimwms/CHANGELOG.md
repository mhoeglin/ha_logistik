# Changelog

## 0.1.4

- Fix: Nach dem Anlegen eines Lagerorts bzw. Artikels führte die Weiterleitung
  zu „404: Not Found" hinter Home-Assistant-Ingress. Die POST-Handler leiteten
  auf absolute Pfade (`/locations`, `/items/...`) ohne den Ingress-Prefix um.
  Die Redirects berücksichtigen jetzt den `X-Ingress-Path`-Header (konsistent
  mit der Startseiten-Weiterleitung).

## 0.1.3

- Neue Seite **Hilfe / Abläufe**: visuelle Prozess-Diagramme (Mermaid) für die
  Use Cases Einlagern, Auslagern, Umzug, Ausleihen/Zurückgeben sowie
  Wegwerfen (Senke/Mülleimer) und Neukauf (Quelle). Enthält auch ein
  Zustandsdiagramm eines Artikels. Mermaid ist lokal eingebettet (funktioniert
  offline über Ingress). Noch nicht implementierte Aktionen sind als „geplant"
  gekennzeichnet.

## 0.1.2

- `CHANGELOG.md` ergänzt (HA zeigt Änderungsnotizen beim Update statt
  „No changelog found").

## 0.1.1

- Robustes Seeding der Demo-Daten: Die Add-on-Option `seed_demo_data` wird
  jetzt zuverlässig als Umgebungsvariable (`HEIMWMS_SEED`) an die App
  durchgereicht; das eigentliche Seeding läuft im App-Lifespan und nur, wenn
  die Datenbank leer ist.

## 0.1.0

- Erste Version: FastAPI + SQLite Lagerverwaltung.
- Lagerorte und Artikel/Kartons anlegen (Codes `LOC:xxxxxx` / `ITM:xxxxxx`),
  optionale Inhaltsliste und optionales Foto pro Artikel.
- Etiketten als A4-PDF mit QR-Code + Code128 + Klartext; Kommando-Blatt
  (`CMD:STORE` u.a.).
- Scan-Workflow „Einlagern": Kommando → Lagerort → Artikel scannen.
- Übersicht „Was ist wo?", Standort/Historie eines Artikels, Suche.
- Home-Assistant-Add-on mit Ingress und persistentem `/data`-Volume.
