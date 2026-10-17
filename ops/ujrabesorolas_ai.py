"""Az `Egyéb` kategóriás kiadások újrabesorolása Claude Haikuval, és a besorolt kereskedők tárolása szabályként
(így a következő importnál ugyanaz a kereskedő már AI nélkül, 0 tokennel kerül a helyére)."""
import collections, json, re, sys
from common import AKTUALIS
from n8nlib import *
from prompts import BESOROLAS_SYSTEM

IDS_ = json.load(open(AKTUALIS / 'ids.json'))['kategoriak']
T_ = {'Authorization': 'Token ' + ENV['BASEROW_VESPENDO_TOKEN']}
ROWS = f"{BASEROW}/api/database/rows/table/"
ANTH = {'x-api-key': ENV['ANTHROPIC_API_KEY'], 'anthropic-version': '2023-06-01'}

def lista(tabla):
    ki, url = [], f"{ROWS}{tabla}/?user_field_names=true&size=200"
    while url:
        st, d = hivas('GET', url, fejlec=T_); ki += d['results']; url = d.get('next')
    return ki

GENERIKUS = re.compile(r'^(vásárlás kártyával|áruvisszavét ellenértéke|azonnali fizetés.*|napközbeni átutalás.*|tranzakció.*)$', re.I)

def kulcs(szoveg):
    """Kereskedőnév-kulcs szabálynak (ugyanez a logika fut az n8n importban is)."""
    for r in [x.strip() for x in szoveg.split(', ') if x.strip()]:
        if GENERIKUS.match(r) or re.fullmatch(r'[\d\W]+', r) or re.search(r'\d+[,.]?\d*\s?EUR|\bEUR\b', r, re.I):
            continue
        r = re.sub(r'\s*-?apple\b.*$', '', r, flags=re.I)
        r = re.sub(r'\s+\d{3,}.*$', '', r)
        r = re.sub(r'\*+', ' ', r)
        r = re.sub(r'\s+', ' ', r).strip().lower()
        if len(r) >= 4:
            return r
    return None

def tiszta(szoveg):
    return re.sub(r'\s*-?APPLE\b', '', re.sub(r'^VÁSÁRLÁS KÁRTYÁVAL,\s*', '', szoveg, flags=re.I)).strip()[:140]

sorok = lista(T['tranzakciok'])
szabalyok = lista(T['szabalymotor'])
minta_lista = [str(r['minta']).lower() for r in szabalyok]
egyeb = [r for r in sorok if (r['tipus'] or {}).get('value') == 'kiadas' and (r['kategoria_id'] or [{}])[0].get('value') == 'Egyéb']
print('Egyéb kiadások:', len(egyeb))

valtozas, tanult, eloszlas, elter = [], {}, collections.Counter(), 0
from prompts import ertelmez

def kerdez(darab):
    bemenet = '\n'.join(f"{n}|{tiszta(r['kereskedo'])}|{int(float(r['osszeg']))}" for n, r in enumerate(darab))
    for _ in range(3):
        st, d = hivas('POST', 'https://api.anthropic.com/v1/messages', {'model': 'claude-haiku-5-5', 'max_tokens': 800,
            'thinking': {'type': 'disabled'}, 'system': BESOROLAS_SYSTEM, 'messages': [{'role': 'user', 'content': bemenet}]}, ANTH)
        if st != 200: raise SystemExit(f'Anthropic hiba: {st} {d}')
        ered = ertelmez(next(b['text'] for b in d['content'] if b['type'] == 'text'), len(darab))
        if ered is not None and len(ered) == len(darab):
            return ered
    raise SystemExit('A modell többször sem adott érvényes, teljes választ: leállok, semmit nem módosítok.')

for i in range(0, len(egyeb), 25):
    darab = egyeb[i:i + 25]
    elso, masodik = kerdez(darab), kerdez(darab)  # két független futás: csak az egyező besorolás számít
    for n, r in enumerate(darab):
        nev = elso[n]
        if nev != masodik[n]:
            elter += 1
            continue
        eloszlas[nev] += 1
        if nev == 'Egyéb' or nev not in IDS_: continue
        valtozas.append({'id': r['id'], 'kategoria_id': [IDS_[nev]], '_nev': tiszta(r['kereskedo']), '_kat': nev})
        k = kulcs(r['kereskedo'])
        if k and not any(m in k or k in m for m in minta_lista) and k not in tanult:
            tanult[k] = nev

print('a két futás eltért (kihagyva):', elter)
if '--lista' in sys.argv:
    for v in valtozas: print('  ', v['_nev'][:44].ljust(46), '->', v['_kat'])
valtozas = [{k: x for k, x in v.items() if not k.startswith('_')} for v in valtozas]
print('az AI besorolása:', dict(eloszlas))
print('átsorolandó tétel:', len(valtozas), '| új szabály (megtanult kereskedő):', len(tanult))
if '--alkalmaz' in sys.argv:
    for i in range(0, len(valtozas), 200):
        st, _ = hivas('PATCH', f"{ROWS}{T['tranzakciok']}/batch/?user_field_names=true", {'items': valtozas[i:i + 200]}, T_)
        print('tételek frissítve:', st)
    if tanult:
        st, _ = hivas('POST', f"{ROWS}{T['szabalymotor']}/batch/?user_field_names=true", {'items': [
            {'minta': k, 'kategoria_id': [IDS_[n]], 'alapertelmezett_tulajdonos': 'kozos'} for k, n in tanult.items()]}, T_)
        print('szabályok mentve:', st)
    print('megtanult kereskedők:', ', '.join(f"{k}→{n}" for k, n in list(tanult.items())[:40]))
