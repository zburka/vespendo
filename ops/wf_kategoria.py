from n8nlib import *

BR = BASEROW + '/api/database/rows/table/'
ELOKESZIT = r"""
const b = $('Webhook').first().json.body || {};
const id = String(b.tranzakcio_id || '');
if (!/^\d+$/.test(id)) throw new Error('Érvénytelen tranzakcio_id');
const javitas = {};
if (b.uj_kategoria_id !== undefined && b.uj_kategoria_id !== null) {
  if (!/^\d+$/.test(String(b.uj_kategoria_id))) throw new Error('Érvénytelen uj_kategoria_id');
  javitas.kategoria_id = [Number(b.uj_kategoria_id)];
}
if (['kozos', 'ferj', 'feleseg'].includes(b.uj_tulajdonos)) javitas.tulajdonos = b.uj_tulajdonos;
if (!Object.keys(javitas).length) throw new Error('Nincs módosítandó mező');
return [{ json: { id, javitas, minta: String(b.kereskedo_minta || '').toLowerCase().trim(), kategoria: javitas.kategoria_id?.[0] ?? null } }];
"""
DONTES = r"""
const e = $('Előkészítés').first().json;
const letezo = ($input.first().json.results || [])[0];
return [{ json: { ...e, szabaly_id: letezo?.id ?? null, kell_szabaly: !!(e.minta && e.kategoria) } }];
"""
nodes = [
    webhook('Webhook', 'kategoria-modositas', 'POST', (0, 0)),
    code('Előkészítés', ELOKESZIT, (240, 0), hiba_ag=True),
    http('Tranzakció módosítása', 'PATCH', f"={BR}{T['tranzakciok']}/" + "{{ $json.id }}/?user_field_names=true", (480, 0),
         body='={{ JSON.stringify($json.javitas) }}', creds=cred_baserow(), hiba_ag=True),
    http('Meglévő szabály', 'GET', f"={BR}{T['szabalymotor']}/?user_field_names=true&size=1&filter__minta__equal=" + "{{ encodeURIComponent($('Előkészítés').first().json.minta) }}", (720, 0), creds=cred_baserow()),
    code('Döntés', DONTES, (960, 0)),
    if_('Kell szabály?', '={{ $json.kell_szabaly }}', '', {'type': 'boolean', 'operation': 'true', 'singleValue': True}, (1200, 0)),
    if_('Van már szabály?', '={{ $json.szabaly_id }}', '', {'type': 'string', 'operation': 'notEmpty', 'singleValue': True}, (1440, -120)),
    http('Szabály frissítése', 'PATCH', f"={BR}{T['szabalymotor']}/" + "{{ $json.szabaly_id }}/?user_field_names=true", (1680, -240),
         body='={{ JSON.stringify({ kategoria_id: [$json.kategoria] }) }}', creds=cred_baserow()),
    http('Szabály létrehozása', 'POST', f"{BR}{T['szabalymotor']}/?user_field_names=true", (1680, 0),
         body="={{ JSON.stringify({ minta: $json.minta, kategoria_id: [$json.kategoria], alapertelmezett_tulajdonos: 'kozos' }) }}", creds=cred_baserow()),
    respond('Válasz', "={{ { status: 'success' } }}", (1920, 0)),
    hiba_valasz((480, 240)),
]
k = {}
for a, b in [('Webhook', 'Előkészítés'), ('Előkészítés', 'Tranzakció módosítása'), ('Tranzakció módosítása', 'Meglévő szabály'),
             ('Meglévő szabály', 'Döntés'), ('Döntés', 'Kell szabály?')]: osszekot(k, a, b)
osszekot(k, 'Kell szabály?', 'Van már szabály?', 0); osszekot(k, 'Kell szabály?', 'Válasz', 1)
osszekot(k, 'Van már szabály?', 'Szabály frissítése', 0); osszekot(k, 'Van már szabály?', 'Szabály létrehozása', 1)
osszekot(k, 'Szabály frissítése', 'Válasz'); osszekot(k, 'Szabály létrehozása', 'Válasz')
osszekot(k, 'Előkészítés', 'Hiba válasz', 1); osszekot(k, 'Tranzakció módosítása', 'Hiba válasz', 1)
telepit('VeSpendo – Kategória módosítás', nodes, k)
