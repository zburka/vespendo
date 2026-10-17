"""A Haiku besorolás közös utasítása (n8n import workflow és az egyszeri újrabesorolás is ezt használja)."""
KATEGORIAK = ['Élelmiszer', 'Étterem', 'Rezsi', 'Szórakozás', 'Ruházat', 'Közlekedés', 'Egészség', 'Előfizetés', 'Banki költségek',
              'Törlesztés', 'Gazdaság', 'Egyéb']
BEVETEL_KATEGORIAK = ['Fizetés', 'Egyéb bevétel']

BESOROLAS_SYSTEM = (
    'Magyar banki tételeket sorolsz be kategóriába a kereskedő neve alapján. Kategóriák: ' + ', '.join(KATEGORIAK) + '. '
    'Útmutató: Élelmiszer = élelmiszerbolt, pékség, hentes, zöldséges, piac, online bevásárlás, drogéria; '
    'Étterem = étterem, gyorsétterem, kávézó, bár, pizzéria, ételrendelés, cukrászda; '
    'Közlekedés = üzemanyag, parkolás, taxi, tömegközlekedés, autópálya; Rezsi = áram, gáz, víz, internet, telefon; '
    'Szórakozás = mozi, játék, sport, hobbi, szabadidő; Ruházat = ruha, cipő, sportbolt; '
    'Egészség = patika, gyógyszertár, orvos, fogorvos, optika, gyógyászati termék; '
    'Előfizetés = rendszeres online vagy szoftver előfizetés (streaming, zene, Apple/Google szolgáltatások, felhő, edzőterem bérlet); '
    'Banki költségek = bankdíjak, tranzakciós költségek; Törlesztés = hitel, kölcsön, részlet törlesztése; '
    'Gazdaság = állattartás és gazdálkodás (takarmány, állateledel, állatorvos, termény, gazdabolt, szerszám), kert és növények; '
    'Bemenet soronként: sorszám|leírás|összeg. Válaszolj KIZÁRÓLAG egy JSON objektummal, amelynek kulcsa a sorszám (szövegként), értéke a kategória neve, '
    'és MINDEN bemeneti sorszám szerepel benne, pl. {"0":"Élelmiszer","1":"Egyéb"}.'
)


BEVETEL_SYSTEM = (
    'Magyar banki jóváírásokat sorolsz be kategóriába. Kategóriák: ' + ', '.join(BEVETEL_KATEGORIAK) + '. '
    'Fizetés = munkabér, jövedelem; '
    'Egyéb bevétel = minden más (visszatérítés, idegentől kapott pénz, utánvét). '
    'Bemenet soronként: sorszám|leírás|összeg. Válaszolj KIZÁRÓLAG egy JSON objektummal, amelynek kulcsa a sorszám (szövegként), értéke a kategória neve, '
    'és MINDEN bemeneti sorszám szerepel benne, pl. {"0":"Fizetés","1":"Egyéb bevétel"}.'
)

import json as _json, re as _re

def ertelmez(szoveg, db, megengedett=None):
    """A modell válaszát {sorszám: kategória} szótárrá alakítja; hibás vagy hiányos válasz esetén None."""
    try:
        d = _json.loads(_re.sub(r'```json|```', '', szoveg).strip())
    except ValueError:
        return None
    if not isinstance(d, dict) or any(str(i) not in d for i in range(db)):
        return None
    megengedett = megengedett or KATEGORIAK
    return {i: d[str(i)] for i in range(db) if d[str(i)] in megengedett}
