"""Költségkeretek és megtakarítási célok szerkesztő végpontjai."""
from n8nlib import *

IGAZ = {'type': 'boolean', 'operation': 'true', 'singleValue': True}
VAN = {'type': 'string', 'operation': 'notEmpty', 'singleValue': True}

# ---------- POST /webhook/keret-mentes  {kategoria_id, nev, havi_keret, aktiv}
KERET_ELO = HZ_JS + r"""
const b = $('Webhook').first().json.body || {};
const kat = String(b.kategoria_id || '');
if (!/^\d+$/.test(kat)) throw new Error('Érvénytelen kategoria_id');
const keret = Number(b.havi_keret);
if (!isFinite(keret) || keret < 0) throw new Error('Érvénytelen havi_keret');
return [{ json: { kat: Number(kat), sor: { haztartas: HZ, nev: String(b.nev || '').slice(0, 100), kategoria_id: [Number(kat)], havi_keret: keret, aktiv: b.aktiv !== false } } }];
"""
KERET_DONT = r"""
const e = $('Előkészítés').first().json;
const letezo = ($input.first().json.results || [])[0];
return [{ json: { ...e, sor_id: letezo?.id ? String(letezo.id) : '' } }];
"""
kat_lek, kat_ell = tulajdon_ellenorzes('Kategória', 'kategoriak', '$json.kat', (480, 120))
nodes = [
    kat_lek, kat_ell,
    webhook('Webhook', 'keret-mentes', 'POST', (0, 0)),
    code('Előkészítés', KERET_ELO, (240, 0), hiba_ag=True),
    http('Meglévő keret', 'GET', f"={BR}{T['koltsegkeretek']}/?user_field_names=true&size=1{HZ_SZURO}&filter__kategoria_id__link_row_has=" + "{{ $json.kat }}",
         (480, 0), creds=cred_baserow(), hiba_ag=True),
    code('Döntés', KERET_DONT, (720, 0)),
    if_('Van már?', '={{ $json.sor_id }}', '', VAN, (960, 0)),
    http('Frissítés', 'PATCH', f"={BR}{T['koltsegkeretek']}/" + "{{ $json.sor_id }}/?user_field_names=true", (1200, -120),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    http('Létrehozás', 'POST', f"{BR}{T['koltsegkeretek']}/?user_field_names=true", (1200, 120),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    respond('Válasz', "={{ { status: 'success', id: String($json.id) } }}", (1440, 0)),
    hiba_valasz((480, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Kategória lekérés'), ('Kategória lekérés', 'Kategória ellenőrzés'),
             ('Kategória ellenőrzés', 'Meglévő keret'), ('Meglévő keret', 'Döntés'), ('Döntés', 'Van már?')]: osszekot(k, a, b)
osszekot(k, 'Van már?', 'Frissítés', 0); osszekot(k, 'Van már?', 'Létrehozás', 1)
osszekot(k, 'Frissítés', 'Válasz'); osszekot(k, 'Létrehozás', 'Válasz')
for n in ('Előkészítés', 'Kategória ellenőrzés', 'Meglévő keret', 'Frissítés', 'Létrehozás'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Keret mentés', nodes, k)

# ---------- POST /webhook/cel-mentes  {id?, cel_neve, celosszeg, aktualis_osszeg}
CEL_ELO = HZ_JS + r"""
const b = $('Webhook').first().json.body || {};
const nev = String(b.cel_neve || '').trim();
if (!nev) throw new Error('A cél neve kötelező');
const cel = Number(b.celosszeg), akt = Number(b.aktualis_osszeg ?? 0);
if (!isFinite(cel) || cel <= 0) throw new Error('Érvénytelen célösszeg');
if (!isFinite(akt) || akt < 0) throw new Error('Érvénytelen aktuális összeg');
const id = b.id === undefined || b.id === null ? '' : String(b.id);
if (id && !/^\d+$/.test(id)) throw new Error('Érvénytelen id');
return [{ json: { id, sor: { haztartas: HZ, cel_neve: nev.slice(0, 100), celosszeg: cel, aktualis_osszeg: akt } } }];
"""
cel_lek, cel_ell = tulajdon_ellenorzes('Cél', 'megtakaritasi_celok', '$json.id', (720, -240))
nodes = [
    cel_lek, cel_ell,
    webhook('Webhook', 'cel-mentes', 'POST', (0, 0)),
    code('Előkészítés', CEL_ELO, (240, 0), hiba_ag=True),
    if_('Van id?', '={{ $json.id }}', '', VAN, (480, 0)),
    http('Frissítés', 'PATCH', f"={BR}{T['megtakaritasi_celok']}/" + "{{ $json.id }}/?user_field_names=true", (720, -120),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    http('Létrehozás', 'POST', f"{BR}{T['megtakaritasi_celok']}/?user_field_names=true", (720, 120),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    respond('Válasz', "={{ { status: 'success', id: String($json.id) } }}", (960, 0)),
    hiba_valasz((480, 240)),
]
k = {}
osszekot(k, 'Webhook', 'Előkészítés'); osszekot(k, 'Előkészítés', 'Van id?')
osszekot(k, 'Van id?', 'Cél lekérés', 0); osszekot(k, 'Van id?', 'Létrehozás', 1)
osszekot(k, 'Cél lekérés', 'Cél ellenőrzés'); osszekot(k, 'Cél ellenőrzés', 'Frissítés')
osszekot(k, 'Frissítés', 'Válasz'); osszekot(k, 'Létrehozás', 'Válasz')
for n in ('Előkészítés', 'Cél ellenőrzés', 'Frissítés', 'Létrehozás'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Cél mentés', nodes, k)

# ---------- POST /webhook/cel-torles  {id}
TOR_ELO = HZ_JS + r"""
const id = String(($('Webhook').first().json.body || {}).id || '');
if (!/^\d+$/.test(id)) throw new Error('Érvénytelen id');
return [{ json: { id } }];
"""
cel_lek, cel_ell = tulajdon_ellenorzes('Cél', 'megtakaritasi_celok', '$json.id', (480, 120))
nodes = [
    cel_lek, cel_ell,
    webhook('Webhook', 'cel-torles', 'POST', (0, 0)),
    code('Előkészítés', TOR_ELO, (240, 0), hiba_ag=True),
    http('Törlés', 'DELETE', f"={BR}{T['megtakaritasi_celok']}/" + "{{ $json.id }}/", (480, 0), creds=cred_baserow(), hiba_ag=True),
    respond('Válasz', "={{ { status: 'success' } }}", (720, 0)),
    hiba_valasz((480, 240)),
]
k = {}
osszekot(k, 'Webhook', 'Előkészítés'); osszekot(k, 'Előkészítés', 'Cél lekérés'); osszekot(k, 'Cél lekérés', 'Cél ellenőrzés')
osszekot(k, 'Cél ellenőrzés', 'Törlés'); osszekot(k, 'Törlés', 'Válasz')
for n in ('Előkészítés', 'Cél ellenőrzés', 'Törlés'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Cél törlés', nodes, k)
