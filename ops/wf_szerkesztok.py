"""Előfizetések és tranzakciók szerkesztő végpontjai: elofizetes-mentes, elofizetes-torles, tranzakcio-modositas, tranzakcio-torles."""
from n8nlib import *

BR = BASEROW + '/api/database/rows/table/'
VAN = {'type': 'string', 'operation': 'notEmpty', 'singleValue': True}

# ---------- POST /webhook/elofizetes-mentes {id?, megnevezes, varhato_osszeg, esedekesseg_napja, kategoria_id}
EF_ELO = r"""
const b = $('Webhook').first().json.body || {};
const nev = String(b.megnevezes || '').trim();
if (!nev) throw new Error('A megnevezés kötelező');
const osszeg = Number(b.varhato_osszeg);
if (!isFinite(osszeg) || osszeg <= 0) throw new Error('Érvénytelen összeg');
const nap = Number(b.esedekesseg_napja);
if (!Number.isInteger(nap) || nap < 1 || nap > 31) throw new Error('Az esedékesség napja 1 és 31 közötti szám legyen');
const kat = String(b.kategoria_id || '');
if (!/^\d+$/.test(kat)) throw new Error('Érvénytelen kategória');
const id = b.id === undefined || b.id === null ? '' : String(b.id);
if (id && !/^\d+$/.test(id)) throw new Error('Érvénytelen id');
return [{ json: { id, sor: { megnevezes: nev.slice(0, 100), varhato_osszeg: osszeg, esedekesseg_napja: nap, kategoria_id: [Number(kat)] } } }];
"""
nodes = [
    webhook('Webhook', 'elofizetes-mentes', 'POST', (0, 0)),
    code('Előkészítés', EF_ELO, (240, 0), hiba_ag=True),
    if_('Van id?', '={{ $json.id }}', '', VAN, (480, 0)),
    http('Frissítés', 'PATCH', f"={BR}{T['elofizetesek']}/" + "{{ $json.id }}/?user_field_names=true", (720, -120),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    http('Létrehozás', 'POST', f"{BR}{T['elofizetesek']}/?user_field_names=true", (720, 120),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    respond('Válasz', "={{ { status: 'success', id: String($json.id) } }}", (960, 0)),
    hiba_valasz((480, 240)),
]
k = {}
osszekot(k, 'Webhook', 'Előkészítés'); osszekot(k, 'Előkészítés', 'Van id?')
osszekot(k, 'Van id?', 'Frissítés', 0); osszekot(k, 'Van id?', 'Létrehozás', 1)
osszekot(k, 'Frissítés', 'Válasz'); osszekot(k, 'Létrehozás', 'Válasz')
for n in ('Előkészítés', 'Frissítés', 'Létrehozás'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Előfizetés mentés', nodes, k)

def torles(nev, ut, tabla):
    ELO = r"""
const id = String(($('Webhook').first().json.body || {}).id || '');
if (!/^\d+$/.test(id)) throw new Error('Érvénytelen id');
return [{ json: { id } }];
"""
    nodes = [
        webhook('Webhook', ut, 'POST', (0, 0)),
        code('Előkészítés', ELO, (240, 0), hiba_ag=True),
        http('Törlés', 'DELETE', f"={BR}{T[tabla]}/" + "{{ $json.id }}/", (480, 0), creds=cred_baserow(), hiba_ag=True),
        respond('Válasz', "={{ { status: 'success' } }}", (720, 0)),
        hiba_valasz((480, 240)),
    ]
    k = {}
    osszekot(k, 'Webhook', 'Előkészítés'); osszekot(k, 'Előkészítés', 'Törlés'); osszekot(k, 'Törlés', 'Válasz')
    for n in ('Előkészítés', 'Törlés'): osszekot(k, n, 'Hiba válasz', 1)
    telepit(nev, nodes, k)

torles('VeSpendo – Előfizetés törlés', 'elofizetes-torles', 'elofizetesek')
torles('VeSpendo – Tranzakció törlés', 'tranzakcio-torles', 'tranzakciok')

# ---------- POST /webhook/tranzakcio-modositas {id, kereskedo?, osszeg?, datum?, megjegyzes?, fizetesi_mod?}
TR_ELO = r"""
const b = $('Webhook').first().json.body || {};
const id = String(b.id || '');
if (!/^\d+$/.test(id)) throw new Error('Érvénytelen id');
const sor = {};
if (b.kereskedo !== undefined) { const v = String(b.kereskedo).trim(); if (!v) throw new Error('A megnevezés nem lehet üres'); sor.kereskedo = v.slice(0, 200); }
if (b.osszeg !== undefined) { const v = Number(b.osszeg); if (!isFinite(v) || v <= 0) throw new Error('Az összeg legyen pozitív szám'); sor.osszeg = v; }
if (b.datum !== undefined) { if (!/^\d{4}-\d{2}-\d{2}$/.test(String(b.datum)) || isNaN(Date.parse(b.datum))) throw new Error('Érvénytelen dátum (ÉÉÉÉ-HH-NN)'); sor.datum = b.datum; }
if (b.megjegyzes !== undefined) sor.megjegyzes = String(b.megjegyzes).slice(0, 1000);
if (b.fizetesi_mod !== undefined) { if (!['kartya', 'keszpenz', 'atutalas'].includes(b.fizetesi_mod)) throw new Error('Érvénytelen fizetési mód'); sor.fizetesi_mod = b.fizetesi_mod; }
if (!Object.keys(sor).length) throw new Error('Nincs módosítandó mező');
return [{ json: { id, sor } }];
"""
nodes = [
    webhook('Webhook', 'tranzakcio-modositas', 'POST', (0, 0)),
    code('Előkészítés', TR_ELO, (240, 0), hiba_ag=True),
    http('Módosítás', 'PATCH', f"={BR}{T['tranzakciok']}/" + "{{ $json.id }}/?user_field_names=true", (480, 0),
         body='={{ JSON.stringify($json.sor) }}', creds=cred_baserow(), hiba_ag=True),
    respond('Válasz', "={{ { status: 'success' } }}", (720, 0)),
    hiba_valasz((480, 240)),
]
k = {}
osszekot(k, 'Webhook', 'Előkészítés'); osszekot(k, 'Előkészítés', 'Módosítás'); osszekot(k, 'Módosítás', 'Válasz')
for n in ('Előkészítés', 'Módosítás'): osszekot(k, n, 'Hiba válasz', 1)
telepit('VeSpendo – Tranzakció módosítás', nodes, k)
