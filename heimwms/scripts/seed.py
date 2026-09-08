"""Seed the database with sample data for GUI testing.

Idempotent-ish: only seeds when there are no locations yet, so running it
repeatedly (or on an already-populated DB) won't create duplicates.

Usage:
    python -m scripts.seed
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.db import get_engine, init_db
from app.models import Location
from app.routers.items import ItemCreate, create_item
from app.routers.locations import LocationCreate, create_location
from app.scan import ScanState, handle_scan


def main() -> None:
    init_db()
    engine = get_engine()
    with Session(engine) as session:
        existing = session.exec(select(Location)).first()
        if existing is not None:
            print("[seed] Datenbank enthält bereits Daten – überspringe Seeding.")
            return

        # --- Lagerorte ---
        keller = create_location(session, LocationCreate(name="Keller", description="Kellerraum"))
        create_location(session, LocationCreate(name="Keller Regal A", parent_code=keller.code))
        dachboden = create_location(session, LocationCreate(name="Dachboden"))
        garage = create_location(session, LocationCreate(name="Garage"))
        print(f"[seed] Lagerorte angelegt: {keller.code}, Regal A, {dachboden.code}, {garage.code}")

        # --- Artikel/Kartons mit optionalen Inhaltslisten ---
        from app.routers.items import ContentLine

        def mk(title, typ, contents):
            return create_item(
                session,
                ItemCreate(
                    title=title,
                    type=typ,
                    contents=[ContentLine(text=t, quantity=q) for t, q in contents],
                ),
            )

        i1 = mk("Bücher – Romane", "box", [("Taschenbücher", 20), ("Hardcover", 8)])
        i2 = mk("Winterkleidung", "box", [("Jacken", 4), ("Handschuhe", 6)])
        i3 = mk("Werkzeug – Elektro", "tool", [("Bohrmaschine", 1), ("Bits-Set", 1)])
        i4 = mk("Weihnachtsdeko", "box", [("Lichterketten", 3)])
        i5 = mk("Konserven-Vorrat", "food", [("Tomaten", 12), ("Bohnen", 8)])
        print(f"[seed] Artikel angelegt: {i1.code}, {i2.code}, {i3.code}, {i4.code}, {i5.code}")

        # --- Ein paar davon direkt einlagern (STORE-Workflow) ---
        def store(location_code, item_codes):
            state = ScanState()
            handle_scan(session, state, "CMD:STORE")
            handle_scan(session, state, location_code)
            for code in item_codes:
                handle_scan(session, state, code)

        store(keller.code, [i1.code, i2.code])
        store(dachboden.code, [i4.code])
        store(garage.code, [i3.code])
        # i5 (Konserven) bleibt bewusst ohne Lagerort, um "Ohne Lagerort" zu zeigen.
        print("[seed] Beispiel-Einlagerungen erstellt. i5 bleibt ohne Lagerort.")
        print("[seed] Fertig.")


if __name__ == "__main__":
    main()
