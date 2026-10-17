"""Fájlból nyers sorok kinyerése: CSV, XLSX, PDF (táblázatos és szöveges)."""
import csv
import io
import re
from datetime import date, datetime

from . import cells


class ParseHiba(Exception):
    """Érthető, felhasználónak megjeleníthető hiba."""


Sorok = list[list[object]]


def kinyer(adat: bytes, fajlnev: str) -> Sorok:
    nev = (fajlnev or "").lower()
    if adat[:4] == b"%PDF" or nev.endswith(".pdf"):
        return _pdf(adat)
    if adat[:2] == b"PK" or nev.endswith(".xlsx"):
        return _xlsx(adat)
    if nev.endswith(".xls"):
        raise ParseHiba("A régi .xls formátum nem támogatott, mentsd el .xlsx vagy .csv fájlként.")
    return _csv(adat)


def _dekodol(adat: bytes) -> str:
    try:
        return adat.decode("utf-8-sig")
    except UnicodeDecodeError:
        return adat.decode("cp1250", errors="replace")


def _csv(adat: bytes) -> Sorok:
    szoveg = _dekodol(adat)
    sorok = [s for s in szoveg.splitlines() if s.strip()]
    if not sorok:
        raise ParseHiba("A fájl üres.")
    minta = sorok[:50]
    elvalaszto = max(";,\t|", key=lambda d: sum(s.count(d) for s in minta))
    return [list(r) for r in csv.reader(io.StringIO("\n".join(sorok)), delimiter=elvalaszto)]


def _xlsx(adat: bytes) -> Sorok:
    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(adat), read_only=True, data_only=True)
    except Exception as e:  # sérült vagy jelszavas fájl
        raise ParseHiba("Az XLSX fájl nem olvasható (sérült vagy jelszóval védett).") from e
    sorok: Sorok = []
    for lap in wb.worksheets:
        for sor in lap.iter_rows(values_only=True):
            if any(not cells.ures(c) for c in sor):
                sorok.append(["" if c is None else c for c in sor])
    return sorok


# --- PDF -------------------------------------------------------------------------------------

# erős összegminta: előjeles, ezres tagolású vagy tizedes
_OSSZEG = r"[+-]?\d{1,3}(?:[  .]\d{3})+(?:,\d{1,2})?|[+-]?\d+[.,]\d{1,2}|[+-]\d+"
_PENZNEM = r"(?:\s*(?:HUF|Ft|EUR|USD))?"
_VEGE = re.compile(rf"((?:\s+(?:{_OSSZEG}){_PENZNEM})+)\s*$", re.IGNORECASE)
_SZAMOK = re.compile(_OSSZEG)


def _pdf(adat: bytes) -> Sorok:
    import pdfplumber

    try:
        pdf = pdfplumber.open(io.BytesIO(adat))
    except Exception as e:
        raise ParseHiba("A PDF nem olvasható (sérült vagy jelszóval védett).") from e

    tablazat: Sorok = []
    sorok_szovegbol: list[str] = []
    szoveg_van = False
    with pdf:
        for oldal in pdf.pages:
            for t in oldal.extract_tables():
                for sor in t:
                    tisztitott = [(c or "").replace("\n", " ").strip() for c in sor]
                    if any(tisztitott):
                        tablazat.append(tisztitott)
            szoveg = oldal.extract_text() or ""
            szoveg_van = szoveg_van or bool(szoveg.strip())
            sorok_szovegbol.extend(_sorok_szavakbol(oldal))

    if not szoveg_van:
        raise ParseHiba("A PDF képként tartalmaz szöveget (szkennelt), ez nem támogatott.")
    # táblázatos mód, ha a táblák tartalmaznak dátumot; egyébként soronkénti szövegelemzés
    if sum(1 for r in tablazat if any(cells.datum(c) for c in r)) >= 3:
        return tablazat
    return _szoveges_sorok(sorok_szovegbol)


def _szoveges_sorok(sorok: list[str]) -> Sorok:
    """[dátum, leírás, szám1, szám2, ...] sorok; a dátum nélküli sorok az előző leírásához fűződnek."""
    eredmeny: Sorok = []
    for nyers in sorok:
        sor = nyers.replace(" ", " ")
        m = cells.DATUM_SOR_ELEJE.match(sor)
        if not m:
            if eredmeny and sor.strip() and not _VEGE.search(sor):
                eredmeny[-1][1] = f"{eredmeny[-1][1]} {sor.strip()}".strip()
            continue
        maradek = sor[m.end():]
        szamok: list[str] = []
        v = _VEGE.search(maradek)
        if v:
            szamok = [x.strip() for x in _SZAMOK.findall(v.group(1))]
            maradek = maradek[: v.start()]
        eredmeny.append([m.group(1), maradek.strip(), *szamok])
    return eredmeny


def _sorok_szavakbol(oldal) -> list[str]:
    """Szavak pozíciójából sorok; a nagy vízszintes hézag tabulátor (oszlophatár), így az
    egymás melletti számok ('20 000    480 000') nem olvadnak össze."""
    szavak = oldal.extract_words(extra_attrs=["size"], keep_blank_chars=False)
    sorok: list[list[dict]] = []
    for sz in sorted(szavak, key=lambda w: (round(w["top"]), w["x0"])):
        if sorok and abs(sorok[-1][0]["top"] - sz["top"]) <= 3:
            sorok[-1].append(sz)
        else:
            sorok.append([sz])
    kimenet = []
    for sor in sorok:
        sor.sort(key=lambda w: w["x0"])
        szoveg = sor[0]["text"]
        for elozo, w in zip(sor, sor[1:]):
            hezag = w["x0"] - elozo["x1"]
            szoveg += ("\t" if hezag > 0.45 * w["size"] else " ") + w["text"]
        kimenet.append(szoveg)
    return kimenet
