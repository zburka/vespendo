"""Kétháztartásos izolációs teszt az éles n8n-en (h- előtagú workflow-k): két ideiglenes háztartást hoz létre,
próbál átlátni / belenyúlni a másikéba, majd mindent töröl. Használat: python3 teszt_haztartas.py"""
import json, sys, uuid
from pathlib import Path
from common import ENV, hivas
from n8nlib import UT_ELOTAG, N8N, IDS

sys.path.insert(0, str(Path(__file__).parent.parent / 'auth-service'))
from kapu.baserow import BaserowKliens
from kapu.beallitasok import Beallitasok

cfg = Beallitasok(baserow_url=ENV['BASEROW_URL'], baserow_token=ENV['BASEROW_VESPENDO_TOKEN'], baserow_tablak=IDS['tablak'])
br = BaserowKliens(cfg)
A, B = 'hz_teszta' + uuid.uuid4().hex[:6], 'hz_tesztb' + uuid.uuid4().hex[:6]
eredmeny = []


def ellenoriz(nev, ok, reszlet=''):
    ok = bool(ok); eredmeny.append(ok)
    print(('PASS ' if ok else 'FAIL ') + nev + ('' if ok else f'  -> {reszlet}'))


def h(hz, metodus, ut, body=None, szemely='anna'):
    fej = {'X-App-Key': ENV['VESPENDO_APP_KEY'], 'X-Szemely': szemely}
    if hz: fej['X-Haztartas'] = hz
    return hivas(metodus, f'{N8N}/webhook/{UT_ELOTAG}{ut}', body, fej)


def siker(r):
    return r[0] == 200 and isinstance(r[1], dict) and r[1].get('status') in ('success', None) and 'uzenet' not in r[1]


try:
    br.haztartas_letrehozas(A, 'Anna'); br.haztartas_letrehozas(B, 'Bela')
    ad_a, ad_b = h(A, 'GET', 'adatok')[1], h(B, 'GET', 'adatok')[1]
    ids_a = {k['id'] for k in ad_a['kategoriak']}; ids_b = {k['id'] for k in ad_b['kategoriak']}
    ellenoriz('adatok: saját kategóriák, átfedés nélkül', len(ids_a) == 16 and len(ids_b) == 16 and not ids_a & ids_b)
    ellenoriz('adatok: csak a saját személyek', {x['kulcs'] for x in ad_a['szemelyek']} == {'kozos', 'anna'})
    ellenoriz('adatok: a családi háztartás adata nem látszik', not any(k['nev'] == 'Zoltán' for k in ad_a['szemelyek']) and len(ad_a['szabalyok']) < 100)
    r = h(None, 'GET', 'adatok')
    ellenoriz('adatok háztartás-fejléc nélkül: nem ad adatot', not (isinstance(r[1], dict) and 'kategoriak' in r[1]), r)
    r = h("hz_x' OR '1", 'GET', 'adatok')
    ellenoriz('adatok hamis háztartás-azonosítóval: nem ad adatot', not (isinstance(r[1], dict) and 'kategoriak' in r[1]), r)

    kat_a = sorted(ids_a, key=int)[0]; kat_b = sorted(ids_b, key=int)[0]
    felv = lambda hz, kat, nev: h(hz, 'POST', 'tranzakcio-felvetel', {'kereskedo': nev, 'osszeg': 1234, 'datum': '2026-10-01', 'kategoria_id': kat, 'tulajdonos': 'anna'})
    ra = felv(A, kat_a, 'A-tetel'); ellenoriz('felvétel saját kategóriával', siker(ra) and ra[1].get('id'), ra)
    ellenoriz('felvétel másik háztartás kategóriájával elutasítva', not siker(felv(A, kat_b, 'A-csalas')))
    tr_a = ra[1]['id']
    lista_a = h(A, 'GET', 'tranzakciok')[1]['tranzakciok']; lista_b = h(B, 'GET', 'tranzakciok')[1]['tranzakciok']
    ellenoriz('tranzakciók: A látja a sajátját', any(t['id'] == tr_a for t in lista_a) and not any(t['kereskedo'] == 'A-csalas' for t in lista_a))
    ellenoriz('tranzakciók: B nem látja A tételét', not any(t['id'] == tr_a for t in lista_b) and lista_b == [])
    ellenoriz('havi összesítő: B-nél üres', h(B, 'GET', 'havi-osszesito?honap=2026-10')[1].get('osszes_kiadas') == 0)

    ellenoriz('módosítás idegen tételen elutasítva', not siker(h(B, 'POST', 'tranzakcio-modositas', {'id': tr_a, 'kereskedo': 'HACK'})))
    ellenoriz('kategória-módosítás idegen tételen elutasítva', not siker(h(B, 'POST', 'kategoria-modositas', {'tranzakcio_id': tr_a, 'uj_kategoria_id': kat_b, 'kereskedo_minta': 'a-tetel'})))
    ellenoriz('kategória-módosítás saját tételen idegen kategóriával elutasítva', not siker(h(A, 'POST', 'kategoria-modositas', {'tranzakcio_id': tr_a, 'uj_kategoria_id': kat_b})))
    ellenoriz('törlés idegen tételen elutasítva', not siker(h(B, 'POST', 'tranzakcio-torles', {'id': tr_a})))
    still = [t for t in h(A, 'GET', 'tranzakciok')[1]['tranzakciok'] if t['id'] == tr_a]
    ellenoriz('az idegen próbálkozások után a tétel változatlan', len(still) == 1 and still[0]['kereskedo'] == 'A-tetel' and still[0]['kategoria_id'] == kat_a)
    ellenoriz('B szabályai nem kaptak A-s szabályt', not any(x['minta'] == 'a-tetel' for x in h(B, 'GET', 'adatok')[1]['szabalyok']))

    rc = h(A, 'POST', 'cel-mentes', {'cel_neve': 'Nyaralas', 'celosszeg': 100000, 'aktualis_osszeg': 0}); cel = rc[1].get('id')
    ellenoriz('cél létrehozása', siker(rc) and cel, rc)
    ellenoriz('cél módosítása idegenből elutasítva', not siker(h(B, 'POST', 'cel-mentes', {'id': cel, 'cel_neve': 'HACK', 'celosszeg': 1, 'aktualis_osszeg': 0})))
    ellenoriz('cél törlése idegenből elutasítva', not siker(h(B, 'POST', 'cel-torles', {'id': cel})))
    ellenoriz('B nem látja A célját', h(B, 'GET', 'adatok')[1]['celok'] == [])
    re_ = h(A, 'POST', 'elofizetes-mentes', {'megnevezes': 'Netflix', 'varhato_osszeg': 4000, 'esedekesseg_napja': 5, 'kategoria_id': kat_a}); ef = re_[1].get('id')
    ellenoriz('előfizetés létrehozása', siker(re_) and ef, re_)
    ellenoriz('előfizetés idegen kategóriával elutasítva', not siker(h(A, 'POST', 'elofizetes-mentes', {'megnevezes': 'X', 'varhato_osszeg': 1, 'esedekesseg_napja': 1, 'kategoria_id': kat_b})))
    ellenoriz('előfizetés törlése idegenből elutasítva', not siker(h(B, 'POST', 'elofizetes-torles', {'id': ef})))
    ellenoriz('keret idegen kategóriára elutasítva', not siker(h(B, 'POST', 'keret-mentes', {'kategoria_id': kat_a, 'nev': 'x', 'havi_keret': 1})))
    ellenoriz('keret saját kategóriára', siker(h(A, 'POST', 'keret-mentes', {'kategoria_id': kat_a, 'nev': 'x', 'havi_keret': 5000})))

    ellenoriz('új személy csak a saját háztartásban', siker(h(A, 'POST', 'szemely-mentes', {'nev': 'Gyerek'})) and {x['kulcs'] for x in h(B, 'GET', 'adatok')[1]['szemelyek']} == {'kozos', 'bela'})
    ellenoriz('idegen személy átnevezése elutasítva', not siker(h(B, 'POST', 'szemely-mentes', {'kulcs': 'anna', 'nev': 'HACK'})))

    imp = {'feltolto': 'anna', 'tranzakciok': [{'datum': '2026-10-02', 'osszeg': 5000, 'irany': 'kiadas', 'kereskedo_nyers': 'LIDL Budapest', 'kozlemeny': 'Vásárlás kártyával'}]}
    ri = h(A, 'POST', 'banki-import', imp)
    ellenoriz('import A-nak', ri[0] == 200 and ri[1].get('status') == 'success' and ri[1]['data']['uj'] == 1, ri)
    ellenoriz('import: a háztartás saját kategóriájába sorol (szabály: lidl → Élelmiszer)', any(t['kereskedo'].startswith('LIDL') and t['kategoria_id'] in ids_a for t in h(A, 'GET', 'tranzakciok')[1]['tranzakciok']))
    rb = h(B, 'POST', 'banki-import', imp)
    ellenoriz('ugyanaz az import B-nek nem duplikátum (külön háztartás)', rb[1]['data']['uj'] == 1 and rb[1]['data']['duplikalt'] == 0, rb)
    ellenoriz('B tételei B kategóriáit használják', all(t['kategoria_id'] in ids_b for t in h(B, 'GET', 'tranzakciok')[1]['tranzakciok']))
    ra2 = h(A, 'POST', 'banki-import', imp)
    ellenoriz('újraimport A-nak: duplikáció-védelem működik', ra2[1]['data']['uj'] == 0 and ra2[1]['data']['duplikalt'] == 1, ra2)
    ellenoriz('bank-állapot: az új háztartásnak nincs kapcsolata', h(A, 'GET', 'bank-allapot')[1].get('kapcsolatok') == [])
    ellenoriz('bank-összekötés idegen személyre elutasítva', not siker(h(A, 'POST', 'bank-osszekotes', {'szemely': 'bela'})))
finally:
    for hz in (A, B):
        br.haztartas_torles(hz)
    marad = sum(len(br.sorok(t, hz)) for hz in (A, B) for t in IDS['tablak'])
    print('takarítás után maradt sor:', marad)
print(f'{sum(eredmeny)}/{len(eredmeny)} sikeres')
sys.exit(0 if all(eredmeny) and not marad else 1)
