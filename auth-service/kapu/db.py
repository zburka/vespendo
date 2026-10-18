import sqlite3
from contextlib import contextmanager

SEMA = """
create table if not exists felhasznalok(
  id integer primary key autoincrement,
  email text not null unique,
  nev text not null,
  jelszo_hash text not null,
  aktiv integer not null default 1,
  letrehozva text not null
);
create table if not exists haztartasok(
  id text primary key,
  nev text not null,
  meghivokod text not null unique,
  bank_engedelyezett integer not null default 0,
  letrehozva text not null
);
-- egy felhasználó egy háztartásban van (v1)
create table if not exists tagsagok(
  felhasznalo_id integer primary key references felhasznalok(id) on delete cascade,
  haztartas_id text not null references haztartasok(id),
  szerep text not null check (szerep in ('admin','tag')),
  szemely_kulcs text
);
create table if not exists frissito_tokenek(
  id integer primary key autoincrement,
  felhasznalo_id integer not null references felhasznalok(id) on delete cascade,
  token_hash text not null unique,
  lejar integer not null,
  visszavonva integer not null default 0,
  eszkoz text,
  letrehozva text not null
);
create table if not exists api_tokenek(
  id integer primary key autoincrement,
  felhasznalo_id integer not null references felhasznalok(id) on delete cascade,
  nev text not null,
  token_hash text not null unique,
  letrehozva text not null,
  utolso text
);
create table if not exists probalkozasok(kulcs text not null, ido integer not null);
create index if not exists probalkozasok_kulcs on probalkozasok(kulcs, ido);
"""


class Adatbazis:
    def __init__(self, utvonal: str):
        self.utvonal = utvonal
        with self.kapcsolat() as c:
            c.execute("pragma journal_mode=wal")
            c.executescript(SEMA)
            # meglévő adatbázis: demó fiók jelölése (a demó belépés jelszó nélküli, csak ezzel a jelzéssel működik)
            if 'demo' not in [r[1] for r in c.execute('pragma table_info(felhasznalok)')]:
                c.execute('alter table felhasznalok add column demo integer not null default 0')

    @contextmanager
    def kapcsolat(self):
        c = sqlite3.connect(self.utvonal, timeout=30, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("pragma foreign_keys=on")
        try:
            yield c
        finally:
            c.close()
