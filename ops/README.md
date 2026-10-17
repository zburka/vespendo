# Üzemeltetési scriptek (Baserow és n8n)

Kódként leírt infrastruktúra: a VeSpendo Baserow-sémát és az n8n workflow-kat ezek hozzák létre, újrafuttathatók
(idempotensek). A titkokat a `/root/.vespendo.env` fájl tartalmazza (`VESPENDO_ENV` környezeti változóval
felülírható), ez soha nem kerül a repóba.

Szükséges kulcsok: `BASEROW_URL`, `BASEROW_EMAIL`, `BASEROW_PASSWORD`, `N8N_URL`, `N8N_API_KEY`, `PARSER_API_KEY`,
`VESPENDO_APP_KEY` (és a script által létrehozott `BASEROW_VESPENDO_TOKEN`).

```bash
python3 baserow_setup.py        # munkaterület, adatbázis, 6 tábla, induló adatok, saját token
python3 wf_fajl_elemzes.py      # POST /webhook/banki-fajl-elemzes  (-> vespendo-parser konténer)
python3 wf_import.py            # POST /webhook/banki-import
python3 wf_adatok.py            # GET  /webhook/adatok, GET /webhook/tranzakciok?honap=
python3 wf_havi.py              # GET  /webhook/havi-osszesito?honap=
python3 wf_kategoria.py         # POST /webhook/kategoria-modositas
python3 wf_nyugta.py            # POST /webhook/nyugta-feltoltes  (AI hitelesítő nélkül 503-at ad)
python3 wf_gyors_import.py      # POST /webhook/banki-fajl-gyors-import  (elemzés + import egy hívásban, iOS Parancsok)
python3 wf_keretek.py           # POST /webhook/keret-mentes, /cel-mentes, /cel-torles
python3 wf_felvetel.py          # POST /webhook/tranzakcio-felvetel (kézi tétel)
python3 wf_szerkesztok.py       # POST /webhook/elofizetes-mentes, /elofizetes-torles, /tranzakcio-modositas, /tranzakcio-torles, /szemely-mentes
```

A webhookok `X-App-Key` fejlécet várnak. A Haiku / Sonnet lépések akkor épülnek be, ha az n8n-ben létezik a
`VeSpendo Anthropic (x-api-key)` hitelesítő (és szerepel az `n8n_cred.json`-ban), majd a workflow scriptek újra lefutnak.
A parser konténer: `docker run -d --name vespendo-parser --network cloudoptima-net -e PARSER_API_KEY=... vespendo-parser`.

## Az app és a kulcs
Az app alapból az élő szerverhez (`https://n8n.cloudoptima.hu`) csatlakozik. Első indításkor bekéri az alkalmazás kulcsát
(`VESPENDO_APP_KEY`), és a telefon biztonságos tárolójába menti (iOS Keychain), nincs szükség `.env` fájlra.
Hibás kulcsnál újra bekéri. Szerver nélküli fejlesztéshez: `EXPO_PUBLIC_MOCK=1`.

## Besorolás és tanulás
Az ismeretlen kereskedőket a Claude Haiku sorolja be (`prompts.py`: közös utasítás, sorszám-kulcsos JSON válasz, teljességi
ellenőrzéssel: hiányos válasz nem csúsztat el besorolást). Amit egyszer besorolt, azt szabályként tárolja a `szabalymotor`
táblában, így a következő importnál ugyanaz a kereskedő már 0 tokennel kerül a helyére. Hibás besorolást az appban
kategóriamódosítással lehet helyesbíteni (ez a szabályt is javítja).

```bash
python3 ujrabesorolas.py --alkalmaz       # banki költségek / nem munkabér bevételek (szabály alapú)
python3 ujrabesorolas_ai.py --lista       # az Egyéb kiadások újrabesorolása AI-val, előnézet (két futás egyezése kell)
python3 ujrabesorolas_ai.py --alkalmaz    # ugyanez, alkalmazva, a megtanult kereskedőkkel
```

## Személyek
A tételek `tulajdonos` mezője a személy **kulcsát** tárolja (szöveg), a `szemelyek` tábla adja a nevét és az aktív állapotát.
A „Közös” is egy személy (`kozos`). Átnevezés: a `szemelyek` tábla `nev` mezője (vagy az appban a Beállítások fülön), a
tételek nem változnak. Új személy a `szemely-mentes` végponttal (az app Beállítások → Új személy) vagy a Baserow-ban vehető fel.
Az import a tulajdonost mindig a feltöltőre állítja (a szabályok alapértelmezett tulajdonosa üres, hacsak nem adtad meg).
