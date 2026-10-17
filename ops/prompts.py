"""A Haiku besorolás közös utasítása (n8n import workflow és az egyszeri újrabesorolás is ezt használja)."""
KATEGORIAK = ['Élelmiszer', 'Étterem', 'Rezsi', 'Szórakozás', 'Ruházat', 'Közlekedés', 'Banki költségek', 'Egyéb']

BESOROLAS_SYSTEM = (
    'Magyar banki tételeket sorolsz be kategóriába a kereskedő neve alapján. Kategóriák: ' + ', '.join(KATEGORIAK) + '. '
    'Útmutató: Élelmiszer = élelmiszerbolt, pékség, hentes, zöldséges, piac, online bevásárlás, drogéria; '
    'Étterem = étterem, gyorsétterem, kávézó, bár, pizzéria, ételrendelés, cukrászda; '
    'Közlekedés = üzemanyag, parkolás, taxi, tömegközlekedés, autópálya; Rezsi = áram, gáz, víz, internet, telefon; '
    'Szórakozás = streaming, mozi, játék, sport, hobbi; Ruházat = ruha, cipő, sportbolt; '
    'Banki költségek = bankdíjak, tranzakciós költségek; Egyéb = ami nem illik sehova (pl. magánszemélyeknek utalás, hitel, törlesztés). '
    'Bemenet soronként: sorszám|leírás|összeg. Válaszolj KIZÁRÓLAG egy JSON objektummal, amelynek kulcsa a sorszám (szövegként), értéke a kategória neve, '
    'és MINDEN bemeneti sorszám szerepel benne, pl. {"0":"Élelmiszer","1":"Egyéb"}.'
)


import json as _json, re as _re

def ertelmez(szoveg, db):
    """A modell válaszát {sorszám: kategória} szótárrá alakítja; hibás vagy hiányos válasz esetén None."""
    try:
        d = _json.loads(_re.sub(r'```json|```', '', szoveg).strip())
    except ValueError:
        return None
    if not isinstance(d, dict) or any(str(i) not in d for i in range(db)):
        return None
    return {i: d[str(i)] for i in range(db) if d[str(i)] in KATEGORIAK}
