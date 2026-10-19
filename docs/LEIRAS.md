# VeSpendo: családi pénzügyi alkalmazás

A VeSpendo egy családi költségkövető alkalmazás. Összegyűjti a banki tételeket és a nyugtákat, automatikusan kategóriákba sorolja őket, és áttekinthetően mutatja, hova megy a pénz. Telefonról és böngészőből is használható (webalkalmazás, a főképernyőre kitehető), App Store nélkül.

## Mit tud

**Áttekintés (Dashboard)**
- Havi bevétel, kiadás és egyenleg, személyenkénti bontásban (pl. közös, saját).
- Kiadások kategóriánként; ahol van költségkeret, a sávon piros vonal jelzi a határt és a túllépést.
- Havi AI-összefoglaló: lezárt hónapról visszatekintés, a folyamatban lévő hónapról helyzetkép és tanács a hátralévő napokra.
- Készpénz-állapot és előfizetés-javaslatok a tranzakciókból.

**Tételek felvitele**
- **Banki összekötés** (OTP, Enable Banking): a tételek naponta automatikusan letöltődnek, a tranzakció típusával (pl. azonnali fizetés, kártyás vásárlás).
- **Banki kivonat feltöltése**: PDF, Excel vagy CSV, formátumtól függetlenül; iPhone-on a Megosztás menüből, egy lépésben is (API-tokennel).
- **Nyugta fényképezése**: az AI soronként elolvassa, kategóriákra bontja (élelmiszer, ruházat, háztartás stb.), és párosítja a banki tétellel, bármelyik érkezik előbb.
- **Kézi tétel**: készpénzes kiadásokhoz.
- Duplikáció-védelem: ugyanaz a tétel nem kerül be kétszer.

**Kategorizálás**
- Kereskedő-szabályok alapján, AI-token nélkül; az ismeretlen kereskedőket az AI sorolja be, és a szabályt megtanulja.
- Kategória átállításakor a rendszer a kereskedőre szabályt tanul.
- Saját kategóriák felvehetők, átnevezhetők, törölhetők (a tételek áthelyezésével); az AI a sajátokat is használja.
- A belső átvezetések (pl. megtakarításra) nem számítanak se kiadásnak, se bevételnek.

**Tervezés**
- Havi költségkeretek kategóriánként.
- Megtakarítási célok.
- Előfizetések nyilvántartása, esedékességgel.

**Háztartások és felhasználók**
- Belépés e-mail címmel és jelszóval. Egy háztartásban több felhasználó is lehet (pl. házaspár), meghívókóddal csatlakozva.
- Minden háztartás adata teljesen elkülönül a többiétől; az admin kezeli a tagokat és a meghívókódot.
- Személyek: a tételek tulajdonosa (közös, vagy személyenként).
- API-tokenek az iPhone Parancsokhoz (csak banki fájl feltöltésére jók).
- Bemutató (demó) mód kitalált adatokkal, jelszó nélkül.

## Hogyan épül fel

| Rész | Szerep |
|---|---|
| **App** (Expo / React Native, webes változattal) | felület, `src/` |
| **Belépési kapu** (`auth-service/`) | fiókok, háztartások, jogosultság; minden kérést ellenőriz, és csak engedélyezett végpontokat enged az n8n felé |
| **n8n** (`ops/wf_*.py`) | az üzleti folyamatok: import, nyugta, kategorizálás, összesítők, bankszinkron |
| **Baserow** | az adatok (tranzakciók, kategóriák, keretek, célok…), háztartásonként szűrve |
| **Fájlelemző** (`parser-service/`) | banki kivonatok (PDF/XLSX/CSV) feldolgozása AI nélkül |
| **Banki szolgáltatás** (`bank-service/`) | Enable Banking kapcsolat, több alkalmazással |
| **AI** (Anthropic) | nyugtaolvasás, ismeretlen kereskedők besorolása, havi összefoglaló |

## Biztonság és üzemeltetés
- Jelszavak Argon2-vel tárolva; rövid életű belépési token, megújítással és lopásvédelemmel; belépési kísérletek korlátozva.
- Háztartások között szigorú elkülönítés (automatikus teszttel ellenőrizve).
- Napi automatikus mentés (adatok, belépési adatbázis, workflow-k), visszaállítási szkripttel.
- A titkok nincsenek a kódtárban; a nyilvános csomagba nem kerülhetnek (a telepítés ellenőrzi).

## Ismert korlátok
- A banki hozzáférés kb. 6 havonta lejár, újra kell jóváhagyni.
- A kártyás tételeket a bank késve könyveli (akár több nap).
- Banki összekötéshez minden személynek a saját számláját kell hozzákötni az Enable Banking alkalmazásához.
- A mentés ugyanazon a szerveren van; érdemes időnként máshová másolni.

Részletes üzemeltetési leírás: `ops/README.md`. iPhone Parancs beállítása: `docs/IOS_PARANCS.md`.
