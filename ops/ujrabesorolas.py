"""Meglévő tételek átsorolása: banki költségek és nem munkabér jellegű bevételek (egyszeri, szabály alapú)."""
import re, sys
from n8nlib import *

from common import AKTUALIS
IDS_ = json.load(open(AKTUALIS / 'ids.json'))['kategoriak']
T_ = {'Authorization': 'Token ' + ENV['BASEROW_VESPENDO_TOKEN']}
URL = f"{BASEROW}/api/database/rows/table/{T['tranzakciok']}/"
BANK = re.compile(r'TRANZAKCIÓ KÖLTSÉGE|MEGB\.DÍJ|HAVIDÍJ|SZÁMLACSOMAG', re.I)
MUNKABER = re.compile(r'munkabér', re.I)
# átutalás típusú tétel: a leírás az átutalás fajtájával kezdődik (nem vásárlás)
ATUTALAS = re.compile(r'^(azonnali fizetés|napközbeni átutalás|átutalás|qvik fizetés|csoportos|beszedés)', re.I)

sorok, url = [], URL + '?user_field_names=true&size=200'
while url:
    st, d = hivas('GET', url, fejlec=T_); sorok += d['results']; url = d.get('next')

valtozas = []
for r in sorok:
    kat = (r['kategoria_id'] or [{}])[0].get('value')
    szoveg = f"{r['kereskedo']} {r.get('megjegyzes') or ''}"
    tipus = (r['tipus'] or {}).get('value')
    if tipus == 'kiadas' and kat == 'Egyéb' and BANK.search(szoveg):
        valtozas.append({'id': r['id'], 'kategoria_id': [IDS_['Banki költségek']]})
    elif tipus == 'kiadas' and kat == 'Egyéb' and ATUTALAS.match(r['kereskedo'].strip()):
        valtozas.append({'id': r['id'], 'kategoria_id': [IDS_['Átutalás']]})
    elif tipus != 'kiadas' and kat == 'Fizetés' and not MUNKABER.search(szoveg):
        valtozas.append({'id': r['id'], 'kategoria_id': [IDS_['Egyéb bevétel']]})
print('átsorolandó tételek:', len(valtozas))
if '--alkalmaz' in sys.argv and valtozas:
    st, d = hivas('PATCH', URL + 'batch/?user_field_names=true', {'items': valtozas}, T_)
    print('kész:', st)
