"""Bemutató (demó) háztartás feltöltése kitalált adatokkal: ~3 hónap tételei, keretek, előfizetések, célok, két személy.
Használat: python3 demo_adat.py <háztartás-azonosító>   (a háztartást előbb regisztrálni kell az appban; a script a meglévő adatait lecseréli).
Minden adat kitalált, determinisztikus (ugyanaz a futtatás ugyanazt adja)."""
import random, sys
from datetime import date, timedelta
from common import ENV, hivas
import json
from pathlib import Path

HZ = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
B = ENV['BASEROW_URL']
TOKEN = {'Authorization': 'Token ' + ENV['BASEROW_VESPENDO_TOKEN']}
T = json.load(open(Path(__file__).parent / 'ids.json'))['tablak']
rnd = random.Random(2026)


def api(m, ut, body=None):
    st, d = hivas(m, B + ut, body, TOKEN)
    if st >= 300:
        raise SystemExit(f'HIBA {m} {ut}: {st} {d}')
    return d


def sorok(tabla):
    ki, ut = [], f'/api/database/rows/table/{T[tabla]}/?user_field_names=true&size=200&filter__haztartas__equal={HZ}'
    while ut:
        d = api('GET', ut)
        ki += d['results']
        ut = (lambda u: u.path + '?' + u.query)(__import__('urllib.parse').parse.urlparse(d['next'])) if d.get('next') else None
    return ki


def torol(tabla):
    ids = [r['id'] for r in sorok(tabla)]
    for i in range(0, len(ids), 200):
        api('POST', f'/api/database/rows/table/{T[tabla]}/batch-delete/', {'items': ids[i:i + 200]})


def letrehoz(tabla, items):
    for i in range(0, len(items), 200):
        api('POST', f'/api/database/rows/table/{T[tabla]}/batch/?user_field_names=true', {'items': items[i:i + 200]})


kat = {r['nev']: r['id'] for r in sorok('kategoriak')}
if not kat:
    sys.exit('A háztartásnak nincsenek kategóriái: előbb regisztráld az appban.')
for t in ('tranzakciok', 'koltsegkeretek', 'elofizetesek', 'megtakaritasi_celok'):
    torol(t)

# személyek: Anna (a regisztrált fiók) és Péter
if not any(r['kulcs'] == 'peter' for r in sorok('szemelyek')):
    letrehoz('szemelyek', [{'haztartas': HZ, 'kulcs': 'peter', 'nev': 'Péter', 'aktiv': True}])

ma = date.today()
honapok = []
d = date(ma.year, ma.month, 1)
for _ in range(3):
    honapok.append(d)
    d = (d - timedelta(days=1)).replace(day=1)
honapok.reverse()

tetelek = []
szamlalo = 0


def tetel(datum, kereskedo, osszeg, kategoria, tipus='kiadas', tulajdonos='kozos', mod='kartya', forras='bank_import', megj=''):
    global szamlalo
    if datum > ma or datum < honapok[0]:
        return
    szamlalo += 1
    tetelek.append({
        'haztartas': HZ, 'datum': datum.isoformat(), 'osszeg': round(osszeg, 2), 'kereskedo': kereskedo, 'kategoria_id': [kat[kategoria]],
        'tipus': tipus, 'tulajdonos': tulajdonos, 'fizetesi_mod': mod, 'forras': forras, 'allapot': 'lezart', 'megjegyzes': megj,
        'import_kulcs': f'demo|{szamlalo}' if forras == 'bank_import' else '',
    })


def nap(h, n):
    return h.replace(day=min(n, 28))


for h in honapok:
    # bevételek, rendszeres kiadások
    tetel(nap(h, 5), 'Munkabér – Anna', 548000, 'Fizetés', 'bevetel_rendszeres', 'anna', 'atutalas')
    tetel(nap(h, 10), 'Munkabér – Péter', 497000, 'Fizetés', 'bevetel_rendszeres', 'peter', 'atutalas')
    tetel(nap(h, 15), 'Lakáshitel törlesztés', 112000, 'Törlesztés', 'kiadas', 'kozos', 'atutalas')
    tetel(nap(h, 2), 'Közös költség', 24500, 'Rezsi', 'kiadas', 'kozos', 'atutalas')
    tetel(nap(h, 20), 'MVM Next áram', rnd.randint(14000, 21000), 'Rezsi', 'kiadas', 'kozos', 'atutalas')
    tetel(nap(h, 22), 'MVM gáz', rnd.randint(9000, 26000), 'Rezsi', 'kiadas', 'kozos', 'atutalas')
    tetel(nap(h, 8), 'Telekom mobil', 9900, 'Előfizetés', 'kiadas', 'kozos', 'atutalas')
    tetel(nap(h, 12), 'Netflix', 4490, 'Előfizetés', 'kiadas', 'kozos', 'kartya')
    tetel(nap(h, 20), 'Spotify', 2490, 'Előfizetés', 'kiadas', 'anna', 'kartya')
    tetel(nap(h, 3), 'Apple iCloud', 890, 'Előfizetés', 'kiadas', 'peter', 'kartya')
    tetel(nap(h, 28), 'Számlavezetési díj', 990, 'Banki költségek', 'kiadas', 'kozos', 'atutalas')
    tetel(nap(h, 25), 'Belső átvezetés megtakarításra', 100000, 'Belső átvezetés', 'kiadas', 'kozos', 'atutalas')
    # élelmiszer
    for _ in range(rnd.randint(11, 14)):
        tetel(nap(h, rnd.randint(1, 28)), rnd.choice(['Lidl', 'Spar', 'Aldi', 'Tesco', 'Penny', 'Kifli.hu']), rnd.randint(3200, 17500),
              'Élelmiszer', 'kiadas', rnd.choice(['kozos', 'kozos', 'anna', 'peter']))
    # étterem / szórakozás / közlekedés / egészség / ruházat
    etterem = 7 if h == honapok[1] else rnd.randint(4, 5)   # a középső hónapban túllépik az éttermi keretet
    for _ in range(etterem):
        tetel(nap(h, rnd.randint(1, 28)), rnd.choice(['Pizza Hut', 'McDonalds', 'Gyros étterem', 'Kávézó', 'Sushi bár']),
              rnd.randint(3500, 11500) if h != honapok[1] else rnd.randint(6500, 9800), 'Étterem', 'kiadas', rnd.choice(['kozos', 'anna', 'peter']))
    for _ in range(rnd.randint(2, 3)):
        tetel(nap(h, rnd.randint(1, 28)), rnd.choice(['Cinema City', 'Szabadulószoba', 'Könyvesbolt', 'Játékbolt']), rnd.randint(2800, 9500),
              'Szórakozás', 'kiadas', rnd.choice(['kozos', 'anna', 'peter']))
    for n in (6, 19):
        tetel(nap(h, n + rnd.randint(0, 3)), rnd.choice(['MOL', 'OMV', 'Shell']), rnd.randint(14500, 21500), 'Közlekedés', 'kiadas', 'peter')
    tetel(nap(h, rnd.randint(1, 28)), 'BKK jegy', rnd.randint(3000, 9500), 'Közlekedés', 'kiadas', 'anna')
    tetel(nap(h, rnd.randint(1, 28)), 'Patika', rnd.randint(2500, 9800), 'Egészség', 'kiadas', rnd.choice(['kozos', 'anna']))
    if rnd.random() < 0.7:
        tetel(nap(h, rnd.randint(1, 28)), rnd.choice(['H&M', 'Zara', 'Decathlon', 'Pepco']), rnd.randint(7000, 24000), 'Ruházat', 'kiadas', rnd.choice(['anna', 'peter']))
    # készpénzes és nyugtás tételek
    tetel(nap(h, rnd.randint(1, 28)), 'Piac (készpénz)', rnd.randint(4500, 8800), 'Élelmiszer', 'kiadas', 'kozos', 'keszpenz', 'kezi', 'Heti piac')
    tetel(nap(h, rnd.randint(1, 28)), 'Dm drogéria', rnd.randint(4800, 12000), 'Egyéb', 'kiadas', 'anna', 'kartya', 'nyugta_foto')

# egyszeri bevétel és nagyobb tétel a középső hónapban
tetel(nap(honapok[1], 17), 'Béta Kft. számla (mellékmunka)', 85000, 'Egyéb bevétel', 'bevetel_egyszeri', 'peter', 'atutalas')
tetel(nap(honapok[1], 11), 'Szervíz – kocsi', 68500, 'Közlekedés', 'kiadas', 'peter', 'kartya')

letrehoz('tranzakciok', tetelek)
letrehoz('koltsegkeretek', [{'haztartas': HZ, 'nev': n, 'kategoria_id': [kat[n]], 'havi_keret': v, 'aktiv': True}
                           for n, v in (('Élelmiszer', 150000), ('Étterem', 40000), ('Szórakozás', 25000), ('Közlekedés', 80000), ('Ruházat', 30000))])
letrehoz('elofizetesek', [{'haztartas': HZ, 'megnevezes': n, 'varhato_osszeg': o, 'esedekesseg_napja': nap_, 'kategoria_id': [kat['Előfizetés']]}
                         for n, o, nap_ in (('Netflix', 4490, 12), ('Spotify', 2490, 20), ('Apple iCloud', 890, 3), ('Telekom mobil', 9900, 8))])
letrehoz('megtakaritasi_celok', [{'haztartas': HZ, 'cel_neve': 'Nyaralás (Horvátország)', 'celosszeg': 600000, 'aktualis_osszeg': 270000},
                                 {'haztartas': HZ, 'cel_neve': 'Biztonsági tartalék', 'celosszeg': 1500000, 'aktualis_osszeg': 640000}])
print(f'KÉSZ: {len(tetelek)} tétel, {honapok[0]} – {ma}')
