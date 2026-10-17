"""Nyers sorokból egységes tranzakciólista, a tartalom (nem a fix szerkezet) alapján."""
import re
import unicodedata

from . import cells
from .extract import ParseHiba, Sorok

EGYENLEG = ("egyenleg", "zaro", "balance", "maradv")
TERHELES = ("terhel", "debit", "kiadas", "tartozas", "withdraw")
JOVAIRAS = ("jovair", "credit", "bevetel", "koveteles", "deposit")
OSSZEG = ("osszeg", "amount", "forgalom", "tetel")
NEM_OSSZEG = ("azonosit", "szamlaszam", "referen", "id", "kod", "szam")
DATUM_ELSO = ("konyvel", "booking", "teljesit", "datum", "date")
PARTNER = ("partner", "kedvezmenyezett", "megnevezes", "ellenfel", "nev", "payee", "merchant", "beneficiary")
KOZLEMENY = ("kozlemeny", "megjegyzes", "leiras", "description", "note", "narrative", "reference")


def _ascii(s: object) -> str:
    t = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def _kulcsszo(fejlec: str, kulcsok: tuple[str, ...]) -> bool:
    return any(k in fejlec for k in kulcsok)


def normalizal(sorok: Sorok) -> dict:
    if not sorok:
        raise ParseHiba("A fájlban nincs feldolgozható adat.")
    szeles = max(len(s) for s in sorok)
    sorok = [list(s) + [""] * (szeles - len(s)) for s in sorok]

    # 1. dátum oszlop: amelyikben a legtöbb dátumszerű cella van
    datum_db = [sum(cells.datum(s[c]) is not None for s in sorok) for c in range(szeles)]
    if max(datum_db) == 0:
        raise ParseHiba("Nem található dátumot tartalmazó oszlop a fájlban.")
    legjobb = max(datum_db)
    jeloltek = [c for c in range(szeles) if datum_db[c] >= 0.8 * legjobb]
    datum_oszlop = jeloltek[0]

    adat_sorok = [i for i, s in enumerate(sorok) if cells.datum(s[datum_oszlop]) is not None]
    elso = adat_sorok[0]
    fejlec = [""] * szeles
    for i in range(elso - 1, -1, -1):  # a legközelebbi nem üres sor az adatsorok fölött
        if any(not cells.ures(c) for c in sorok[i]):
            fejlec = [_ascii(c) for c in sorok[i]]
            break
    if len(jeloltek) > 1:
        elsodleges = [c for c in jeloltek if _kulcsszo(fejlec[c], DATUM_ELSO[:3])]
        datum_oszlop = (elsodleges or jeloltek)[0]
    adat = [sorok[i] for i in adat_sorok]

    # 2. összeg-jelölt oszlopok
    jeloltek_osszeg: list[int] = []
    for c in range(szeles):
        if c == datum_oszlop or _kulcsszo(fejlec[c], NEM_OSSZEG) and not _kulcsszo(fejlec[c], OSSZEG):
            continue
        nem_ures = [s[c] for s in adat if not cells.ures(s[c])]
        if len(nem_ures) < max(1, 0.2 * len(adat)):
            continue
        ertekek = [cells.osszeg(x) for x in nem_ures]
        if sum(v is not None for v in ertekek) < 0.9 * len(nem_ures):
            continue
        if any(v is not None and abs(v) >= 1e10 for v in ertekek):
            continue
        jeloltek_osszeg.append(c)
    if not jeloltek_osszeg:
        raise ParseHiba("Nem található összeg oszlop a fájlban.")

    def ertek(sor, c):
        return None if c is None else cells.osszeg(sor[c])

    # 3. oszlopszerepek: fejléc kulcsszavak, majd egyenleg-ellenőrzés
    szerep: dict[str, int | None] = {"egyenleg": None, "terheles": None, "jovairas": None, "osszeg": None}
    for c in jeloltek_osszeg:
        for nev, kulcsok in (("egyenleg", EGYENLEG), ("terheles", TERHELES), ("jovairas", JOVAIRAS), ("osszeg", OSSZEG)):
            if szerep[nev] is None and _kulcsszo(fejlec[c], kulcsok):
                szerep[nev] = c
                break
    iranyok_forras = "elojel"
    megbizhatosag_egyenleg = 0.0
    # 1: időrendben növekvő sorok, -1: legújabb elöl (a dátumokból, mert az egyenleg-különbség szimmetrikus)
    elso_datum, utolso_datum = cells.datum(adat[0][datum_oszlop]), cells.datum(adat[-1][datum_oszlop])
    sorrend = -1 if elso_datum and utolso_datum and elso_datum > utolso_datum else 1

    maradek = [c for c in jeloltek_osszeg if c not in szerep.values()]
    if szerep["egyenleg"] is None and len(jeloltek_osszeg) >= 2:
        legjobb_par = (0.0, None, None, 1)
        for a in jeloltek_osszeg:
            for b in jeloltek_osszeg:
                if a == b:
                    continue
                arany = _egyenleg_egyezes(adat, a, b, sorrend)
                if arany > legjobb_par[0]:
                    legjobb_par = (arany, a, b, sorrend)
        if legjobb_par[0] >= 0.6:
            megbizhatosag_egyenleg, a, b, sorrend = legjobb_par
            szerep["egyenleg"] = b
            if szerep["osszeg"] is None and szerep["terheles"] is None:
                szerep["osszeg"] = a
            maradek = [c for c in jeloltek_osszeg if c not in szerep.values()]
    elif szerep["egyenleg"] is not None:
        for c in jeloltek_osszeg:
            arany = _egyenleg_egyezes(adat, c, szerep["egyenleg"], sorrend)
            if arany >= 0.6 and c != szerep["egyenleg"]:
                megbizhatosag_egyenleg = arany
                if szerep["osszeg"] is None:
                    szerep["osszeg"] = c
                break
        maradek = [c for c in jeloltek_osszeg if c not in szerep.values()]

    figyelmeztetesek: list[str] = []
    if szerep["osszeg"] is None and szerep["terheles"] is None and szerep["jovairas"] is None:
        if maradek:
            szerep["osszeg"] = maradek[0]
            if len(maradek) > 1:
                figyelmeztetesek.append("Több lehetséges összegoszlop van, az elsőt használtuk.")
        elif szerep["egyenleg"] is not None:
            raise ParseHiba("Csak egyenleg oszlop található, tételösszeg nem.")
    elif szerep["terheles"] is not None and szerep["jovairas"] is None and maradek:
        szerep["jovairas"] = maradek[0]
    elif szerep["jovairas"] is not None and szerep["terheles"] is None and maradek:
        szerep["terheles"] = maradek[0]

    # két megosztott (egymást kiegészítő) oszlop fejléc nélkül: terhelés / jóváírás
    if szerep["osszeg"] is None and szerep["terheles"] is None and szerep["jovairas"] is None:
        raise ParseHiba("Az összeg oszlop nem azonosítható.")

    # 4. szöveges oszlopok
    kihagyott_oszlopok = {datum_oszlop, *(v for v in szerep.values() if v is not None), *jeloltek_osszeg}
    szoveg_oszlopok = []
    for c in range(szeles):
        if c in kihagyott_oszlopok:
            continue
        nem_ures = [str(s[c]).strip() for s in adat if not cells.ures(s[c])]
        if not nem_ures:
            continue
        atlag = sum(len(x) for x in nem_ures) / len(nem_ures)
        szoveg_oszlopok.append((c, atlag, len(nem_ures)))
    partner_c = next((c for c, _, _ in szoveg_oszlopok if _kulcsszo(fejlec[c], PARTNER)), None)
    kozlemeny_c = next(
        (c for c, _, _ in szoveg_oszlopok if _kulcsszo(fejlec[c], KOZLEMENY) and c != partner_c), None
    )
    szabad = sorted((x for x in szoveg_oszlopok if x[0] not in (partner_c, kozlemeny_c)), key=lambda x: -x[1])
    if partner_c is None and szabad:
        partner_c = szabad.pop(0)[0]
    if kozlemeny_c is None and szabad:
        kozlemeny_c = szabad.pop(0)[0]

    # 5. tranzakciók
    tranzakciok = []
    kihagyott = 0
    bizonytalan: list[int] = []  # tranzakciók indexei, amelyek iránya nem számolható ki
    for n, s in enumerate(adat):
        osszeg = ertek(s, szerep["osszeg"])
        terheles = ertek(s, szerep["terheles"])
        jovairas = ertek(s, szerep["jovairas"])
        elojeles: float | None
        if szerep["osszeg"] is not None and osszeg is not None:
            elojeles = osszeg
            if szerep["egyenleg"] is not None and megbizhatosag_egyenleg >= 0.6:
                elojeles, biztos = _egyenleg_elojel(adat, n, szerep, sorrend, osszeg)
                if not biztos:
                    bizonytalan.append(len(tranzakciok))
        elif terheles:
            elojeles = -abs(terheles)
        elif jovairas:
            elojeles = abs(jovairas)
        else:
            elojeles = None
        if elojeles is None or elojeles == 0:
            kihagyott += 1
            continue
        kozlemeny = _szoveg(s, kozlemeny_c)
        partner = _szoveg(s, partner_c) or kozlemeny
        tranzakciok.append(
            {
                "datum": cells.datum(s[datum_oszlop]),
                "osszeg": round(abs(elojeles), 2),
                "kereskedo_nyers": partner,
                "kozlemeny": kozlemeny,
                "irany": "kiadas" if elojeles < 0 else "bevetel",
            }
        )

    if not tranzakciok:
        raise ParseHiba("Nem sikerült tételeket kinyerni a fájlból.")

    if bizonytalan:
        biztos_kiadas = sum(t["irany"] == "kiadas" for i, t in enumerate(tranzakciok) if i not in bizonytalan)
        biztos_bevetel = len(tranzakciok) - len(bizonytalan) - biztos_kiadas
        irany = "kiadas" if biztos_kiadas >= biztos_bevetel else "bevetel"
        for i in bizonytalan:
            tranzakciok[i]["irany"] = irany
        figyelmeztetesek.append(
            "A legrégebbi tétel iránya nem számolható ki az egyenlegből, a leggyakoribb irányt "
            "használtuk. Ellenőrizd az előnézetet."
        )

    van_negativ = any(t["irany"] == "kiadas" for t in tranzakciok)
    van_pozitiv = any(t["irany"] == "bevetel" for t in tranzakciok)
    iranyjel_megbizhato = (
        megbizhatosag_egyenleg >= 0.8
        or (szerep["terheles"] is not None and szerep["jovairas"] is not None)
        or (van_negativ and van_pozitiv)
    )
    if not iranyjel_megbizhato and not van_negativ:
        figyelmeztetesek.append(
            "A tételek iránya nem állapítható meg biztosan (minden összeg pozitív). "
            "Ellenőrizd az előnézetet."
        )
    fejlec_talalat = sum(1 for k in ("osszeg", "terheles", "jovairas") if szerep[k] is not None and fejlec[szerep[k]])
    if megbizhatosag_egyenleg >= 0.8 or (fejlec_talalat and iranyjel_megbizhato):
        megbizhatosag = "magas"
    elif iranyjel_megbizhato:
        megbizhatosag = "kozepes"
    else:
        megbizhatosag = "alacsony"
    if kihagyott:
        figyelmeztetesek.append(f"{kihagyott} sor kimaradt (hiányzó összeg).")

    return {
        "tranzakciok": tranzakciok,
        "kihagyott": kihagyott,
        "megbizhatosag": megbizhatosag,
        "figyelmeztetesek": figyelmeztetesek,
    }


def _szoveg(sor, c) -> str:
    if c is None or cells.ures(sor[c]):
        return ""
    return re.sub(r"\s+", " ", str(sor[c])).strip()


def _egyenleg_egyezes(adat, a: int, b: int, sorrend: int) -> float:
    """Az `a` oszlop a tétel, a `b` az egyenleg? Az egyezési arány a régebbi szomszéd sorhoz képest."""
    vizsgalt = egyezik = 0
    for i in range(len(adat)):
        regebbi = i - 1 if sorrend == 1 else i + 1
        if not 0 <= regebbi < len(adat):
            continue
        x = cells.osszeg(adat[i][a])
        ez = cells.osszeg(adat[i][b])
        elozo = cells.osszeg(adat[regebbi][b])
        if x is None or ez is None or elozo is None:
            continue
        vizsgalt += 1
        if abs(abs(ez - elozo) - abs(x)) < 0.011:
            egyezik += 1
    return egyezik / vizsgalt if vizsgalt >= 2 else 0.0


def _egyenleg_elojel(adat, n: int, szerep, sorrend: int, osszeg: float) -> tuple[float, bool]:
    """Előjel az egyenleg változásából. Visszaadja (előjeles összeg, biztos-e az irány)."""
    b = szerep["egyenleg"]
    biztos_sajat = osszeg < 0
    ez = cells.osszeg(adat[n][b])
    szomszed_i = n - 1 if sorrend == 1 else n + 1  # a régebbi szomszéd
    if ez is None or not (0 <= szomszed_i < len(adat)):
        return osszeg, biztos_sajat  # a legrégebbi tételnek nincs előző egyenlege
    szomszed = cells.osszeg(adat[szomszed_i][b])
    if szomszed is None:
        return osszeg, biztos_sajat
    valtozas = ez - szomszed
    if abs(abs(valtozas) - abs(osszeg)) >= 0.011:
        return osszeg, biztos_sajat
    return (abs(osszeg) if valtozas > 0 else -abs(osszeg)), True
