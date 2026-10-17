"""Cellaértékek felismerése: dátum és összeg, bank- és nyelvfüggetlenül."""
import re
from datetime import date, datetime

DATUM_MINTAK = [
    (re.compile(r"^\s*(\d{4})[.\-/ ]+(\d{1,2})[.\-/ ]+(\d{1,2})\.?\s*(?:\d{1,2}:\d{2}(?::\d{2})?)?\s*$"), "ymd"),
    (re.compile(r"^\s*(\d{1,2})[.\-/ ]+(\d{1,2})[.\-/ ]+(\d{4})\.?\s*(?:\d{1,2}:\d{2}(?::\d{2})?)?\s*$"), "dmy"),
]
# sor eleji dátum a PDF szöveges módjához
DATUM_SOR_ELEJE = re.compile(
    r"^\s*(\d{4}[.\-/ ]+\d{1,2}[.\-/ ]+\d{1,2}\.?|\d{1,2}[.\-/]\d{1,2}[.\-/]\d{4}\.?"
    r"|\d{2}[.\-/]\d{2}[.\-/]\d{2}\.?)(?=\s|$)"
)
PENZNEM = re.compile(r"(?i)\b(huf|ft|eur|usd|chf|gbp)\b|[€$£]")
SZAM = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")


def datum(cella) -> str | None:
    if isinstance(cella, datetime):
        return cella.date().isoformat()
    if isinstance(cella, date):
        return cella.isoformat()
    if not isinstance(cella, str):
        return None
    for minta, sorrend in DATUM_MINTAK:
        m = minta.match(cella)
        if not m:
            continue
        a, b, c = (int(x) for x in m.groups())
        ev, ho, nap = (a, b, c) if sorrend == "ymd" else (c, b, a)
        try:
            return date(ev, ho, nap).isoformat()
        except ValueError:
            return None
    return None


def osszeg(cella) -> float | None:
    if isinstance(cella, bool):
        return None
    if isinstance(cella, (int, float)):
        return float(cella)
    if not isinstance(cella, str) or datum(cella) is not None:
        return None
    s = PENZNEM.sub("", cella).replace(" ", " ").strip()
    if not s:
        return None
    negativ = False
    if s.startswith("(") and s.endswith(")"):
        negativ, s = True, s[1:-1].strip()
    if s.endswith("-") and not s.startswith("-"):
        negativ, s = True, s[:-1].strip()
    s = re.sub(r"(?<=[+-])\s+", "", s)
    s = s.replace(" ", "")
    if not s or re.search(r"[^\d.,+-]", s):
        return None
    elojel = -1.0 if s.startswith("-") else 1.0
    s = s.lstrip("+-")
    if not re.fullmatch(r"\d[\d.,]*", s):
        return None
    if "," in s and "." in s:
        tizedes = "," if s.rfind(",") > s.rfind(".") else "."
        ezres = "." if tizedes == "," else ","
        s = s.replace(ezres, "").replace(tizedes, ".")
    elif "," in s or "." in s:
        jel = "," if "," in s else "."
        if re.fullmatch(rf"\d{{1,3}}(\{jel}\d{{3}})+", s):  # 1.234 / 1,234.567 -> ezres tagolás
            s = s.replace(jel, "")
        elif s.count(jel) == 1:
            s = s.replace(jel, ".")
        else:
            return None
    try:
        ertek = float(s) * elojel
    except ValueError:
        return None
    return -ertek if negativ else ertek


def ures(cella) -> bool:
    return cella is None or (isinstance(cella, str) and not cella.strip())
