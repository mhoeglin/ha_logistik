# Heim-WMS – Home Assistant Add-on

Persönliche Lagerverwaltung als lokales HA-Add-on: Lagerorte und Kartons/Artikel
anlegen, Etiketten (QR + Code128) drucken und per Barcode-Scan einlagern.

## Installation

1. Dieses Verzeichnis liegt unter `das Repository (Ordner heimwms)` auf dem HA-Host
   (Ordner „addons" der lokalen Add-ons).
2. In Home Assistant: **Einstellungen → Add-ons → Add-on Store**.
3. Oben rechts **⋮ → Repositories aktualisieren** bzw. Store neu laden.
4. Unter **Local add-ons** erscheint **Heim-WMS** → anklicken → **Installieren**.
5. Nach dem Build **Starten**. Über **In Seitenleiste anzeigen** ist die
   Web-UI direkt per Ingress erreichbar (keine Portfreigabe nötig).

## Konfiguration

| Option           | Default | Bedeutung                                            |
|------------------|---------|------------------------------------------------------|
| `seed_demo_data` | `false` | Beim Start Beispieldaten anlegen (nur wenn DB leer). |

Zum Testen der GUI: `seed_demo_data` auf `true` setzen, Add-on starten. Es
werden 4 Lagerorte und 5 Kartons angelegt, einige davon bereits eingelagert.
Danach kann die Option wieder auf `false` gestellt werden (erneutes Seeding
wird ohnehin übersprungen, solange bereits Daten vorhanden sind).

## Daten / Persistenz

Alle Daten (SQLite-DB + Foto-Uploads) liegen im vom Supervisor verwalteten
`/data`-Verzeichnis des Add-ons und überleben Neustarts und Updates.

## Zugriff

- **Ingress** (empfohlen): über die HA-Seitenleiste, authentifiziert durch HA.
- **Direkt**: optional auf Host-Port `8099` (siehe `ports` in `config.yaml`).

## Scanner

Bluetooth-/USB-Barcodescanner im HID-/Keyboard-Wedge-Modus an ein Handy/Tablet
koppeln, im HA-Frontend die Heim-WMS-Seite **Scan** öffnen. Ablauf Einlagern:
`CMD:STORE` scannen → Lagerort scannen → Artikel nacheinander scannen.
