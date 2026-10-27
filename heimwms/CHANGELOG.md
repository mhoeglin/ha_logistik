# Changelog

## 0.3.2

- Artikel-Foto: Das Foto-Feld öffnet auf dem Smartphone jetzt direkt die
  (Rück-)Kamera (`capture="environment"`), statt den Galerie-/Dateidialog. Am
  Desktop-Browser bleibt der normale Dateidialog erhalten.

## 0.3.1

- Artikel: **Löschen**-Funktion. Button in der Artikel-Tabelle und auf der
  Detailseite (mit Sicherheitsabfrage) sowie REST-Endpunkt
  `DELETE /api/items/{code}`. Beim Löschen werden auch die Inhaltsliste, die
  Fotos (inkl. der Bilddateien), aktive/alte Platzierungen und die
  Bewegungshistorie des Artikels entfernt.

## 0.3.0

- Artikel-Typen überarbeitet: **Karton, Kiste, Werkzeug, Lebensmittel,
  Material** (statt der bisherigen englischen Werte box/food/tool/other). Die
  Auswahl und Anzeige erfolgt mit deutschen Bezeichnungen. Bestehende
  Datenbanken werden beim Start automatisch migriert (box→Karton,
  food→Lebensmittel, tool→Werkzeug, other→Material); alte Werte werden auch
  bei der Eingabe weiterhin akzeptiert und zugeordnet.

## 0.2.0

- Fix: Nach dem Anlegen eines Lagerorts bzw. Artikels führte die Weiterleitung
  hinter Home-Assistant-Ingress zu „404: Not Found". Die POST-Handler leiten
  jetzt mit dem `X-Ingress-Path`-Präfix um (konsistent mit der Startseite).
- Lagerorte: **Bearbeiten**- und **Löschen**-Funktion direkt in der Tabelle.
  Bearbeiten über eigene Seite (Name, Beschreibung, übergeordneter Ort);
  Löschen mit Sicherheitsabfrage. Schutzregeln: ein Ort mit Unter-Orten oder
  noch eingelagerten Artikeln kann nicht gelöscht werden; Zyklen bei der
  Übergeordnet-Zuordnung werden verhindert. Dazu REST-Endpunkte
  `PUT`/`DELETE /api/locations/{code}`.
- Scan: **Auslagern** (CMD:REMOVE), **Umzug** (CMD:MOVE), **Ausleihen**
  (CMD:LEND) und **Zurückgeben** (CMD:RETURN) sind jetzt in der Oberfläche
  nutzbar (zuvor nur „geplant"). Umzug kann auch durch erneutes Einlagern am
  neuen Ort erfolgen. Artikel tragen einen Status (eingelagert/ausgelagert/
  ausgeliehen/entsorgt); Einlagern in einen als Senke markierten Ort
  (z.B. Mülleimer) entsorgt den Artikel.

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
