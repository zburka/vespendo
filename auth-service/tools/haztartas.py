"""Háztartás létrehozása parancssorból (pl. a meglévő adatokhoz tartozó család). Használat (a konténerben):
python tools/haztartas.py hz_csalad "Család" [--bank]   -> kiírja a meghívókódot; az első csatlakozó lesz az admin."""
import sys
from datetime import datetime, timezone

from kapu import biztonsag as b
from kapu.beallitasok import Beallitasok
from kapu.db import Adatbazis

azon, nev, bank = sys.argv[1], sys.argv[2], "--bank" in sys.argv
db = Adatbazis(Beallitasok.kornyezetbol().db_utvonal)
with db.kapcsolat() as c:
    van = c.execute("select meghivokod from haztartasok where id=?", (azon,)).fetchone()
    if van:
        print("már létezik, meghívókód:", van["meghivokod"])
    else:
        kod = b.meghivokod()
        c.execute("insert into haztartasok(id, nev, meghivokod, bank_engedelyezett, letrehozva) values(?,?,?,?,?)",
                  (azon, nev, kod, int(bank), datetime.now(timezone.utc).isoformat(timespec="seconds")))
        print("létrehozva, meghívókód:", kod)
