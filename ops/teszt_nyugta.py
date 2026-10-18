"""A nyugta szerinti kategória-bontás és a banki tétellel párosítás éles próbája (két sorrend), ideiglenes háztartásokban.
Kell: Pillow (a nyugtaképet előállítja). Használat: /tmp/pv/bin/python teszt_nyugta.py"""
import base64, io, sys, uuid
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from common import ENV
from n8nlib import IDS
from belso import h

sys.path.insert(0, str(Path(__file__).parent.parent / 'auth-service'))
from kapu.baserow import BaserowKliens
from kapu.beallitasok import Beallitasok

br = BaserowKliens(Beallitasok(baserow_url=ENV['BASEROW_URL'], baserow_token=ENV['BASEROW_VESPENDO_TOKEN'], baserow_tablak=IDS['tablak']))
ma = date.today().isoformat()
SOROK = [('BANAN 1 kg', 799), ('KENYER 1 kg', 699), ('TEJ 2,8% 1 l', 459), ('FERFI POLO M', 4990), ('MOSOGATOSZER 1 l', 1190)]
OSSZEG = sum(x[1] for x in SOROK)
eredmeny = []


def ok(nev, feltetel, reszlet=''):
    eredmeny.append(bool(feltetel))
    print(('PASS ' if feltetel else 'FAIL ') + nev + ('' if feltetel else f'  -> {reszlet}'))


def nyugta_kep():
    kep = Image.new('RGB', (700, 120 + 60 * (len(SOROK) + 4)), 'white')
    d = ImageDraw.Draw(kep)
    f = ImageFont.load_default(size=30)
    y = 20
    for sor in ['TESCO HIPERMARKET', f'Datum: {ma}', '------------------------------']:
        d.text((30, y), sor, fill='black', font=f); y += 50
    for nev, ar in SOROK:
        d.text((30, y), f'{nev}', fill='black', font=f); d.text((520, y), f'{ar} Ft', fill='black', font=f); y += 50
    d.text((30, y), '------------------------------', fill='black', font=f); y += 50
    d.text((30, y), f'VEGOSSZEG: {OSSZEG} Ft', fill='black', font=f); y += 50
    d.text((30, y), 'Fizetes: Bankkartya', fill='black', font=f)
    b = io.BytesIO(); kep.save(b, 'PNG')
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()


def tetelek(hz):
    ad = h(hz, 'GET', 'adatok')[1]
    kn = {k['id']: k['nev'] for k in ad['kategoriak']}
    return [(t['kereskedo'], t['osszeg'], kn.get(t['kategoria_id']), t['allapot'], t['forras']) for t in h(hz, 'GET', 'tranzakciok')[1]['tranzakciok']]


A, B = 'hz_teszta' + uuid.uuid4().hex[:6], 'hz_tesztb' + uuid.uuid4().hex[:6]
BANK = {'feltolto': 'anna', 'tranzakciok': [{'datum': ma, 'osszeg': OSSZEG, 'irany': 'kiadas', 'kereskedo_nyers': 'TESCO 44031', 'kozlemeny': 'Vásárlás kártyával'}]}
try:
    br.haztartas_letrehozas(A, 'Anna'); br.haztartas_letrehozas(B, 'Bela')
    kep = nyugta_kep()
    # 1) előbb a nyugta, aztán a bank
    r = h(A, 'POST', 'nyugta-feltoltes', {'kep_base64': kep, 'feltolto': 'anna'})
    ok('nyugta feltöltése sikeres', r[0] == 200 and r[1].get('status') == 'success', r)
    d = r[1].get('data', {})
    print('  bontás:', d.get('bontott_tetelek'))
    ok('több kategóriára bontva, az összeg a végösszeg', len(d.get('bontott_tetelek', [])) >= 2 and abs(sum(x['osszeg'] for x in d['bontott_tetelek']) - OSSZEG) < 0.01 and d.get('osszeg') == OSSZEG, d)
    nevek = {x['kategoria'] for x in d.get('bontott_tetelek', [])}
    ok('élelmiszer, ruházat és háztartás külön', {'Élelmiszer', 'Ruházat'} <= nevek, nevek)
    sorok = tetelek(A)
    ok('a sorok várakozó állapotban, összegük a végösszeg', len(sorok) >= 2 and all(s[3] == 'banki_egyeztetesre_var' for s in sorok) and abs(sum(s[1] for s in sorok) - OSSZEG) < 0.01, sorok)
    ri = h(A, 'POST', 'banki-import', BANK)
    ok('a banki tétel párosul a nyugta-csoporttal (nincs új sor)', ri[1].get('data', {}).get('egyeztetve') == 1 and ri[1]['data']['uj'] == 0, ri)
    sorok = tetelek(A)
    ok('minden sor lezárt, összeg változatlan', all(s[3] == 'lezart' for s in sorok) and abs(sum(s[1] for s in sorok) - OSSZEG) < 0.01, sorok)
    ok('újraimport: duplikáció-védelem', h(A, 'POST', 'banki-import', BANK)[1]['data']['duplikalt'] == 1)
    # 2) előbb a bank, aztán a nyugta
    ri = h(B, 'POST', 'banki-import', BANK)
    ok('bank tétel előbb (szabály: Tesco → Élelmiszer)', ri[1]['data']['uj'] == 1, ri)
    rn = h(B, 'POST', 'nyugta-feltoltes', {'kep_base64': kep, 'feltolto': 'bela'})
    ok('nyugta a már meglévő banki tételhez párosul', rn[1].get('data', {}).get('parositva') is True, rn)
    sorok = tetelek(B)
    print('  sorok:', sorok)
    ok('a banki tétel felbontva, az összeg változatlan', len(sorok) >= 2 and abs(sum(s[1] for s in sorok) - OSSZEG) < 0.01 and all(s[3] == 'lezart' and s[4] == 'bank_import' for s in sorok), sorok)
    ok('újraimport után sem keletkezik duplikátum', h(B, 'POST', 'banki-import', BANK)[1]['data']['uj'] == 0 and len(tetelek(B)) == len(sorok))
finally:
    for hz in (A, B):
        br.haztartas_torles(hz)
    marad = sum(len(br.sorok(t, hz)) for hz in (A, B) for t in IDS['tablak'])
    print('takarítás után maradt sor:', marad)
print(f'{sum(eredmeny)}/{len(eredmeny)} sikeres')
sys.exit(0 if all(eredmeny) and not marad else 1)
