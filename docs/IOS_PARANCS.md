# Banki kivonat importálása a megosztás menüből (iPhone, Parancsok app)

Fizetős Apple Developer fiók nélkül is működik. A banki appból a **Megosztás → VeSpendo** elküldi a PDF-et a VeSpendo szervernek,
az egy hívásban elemzi és importálja (duplikációk automatikusan kimaradnak), és értesítést kapsz az eredményről.

## Beállítás (egyszer, kb. 5 perc)

1. **Parancsok** app → **+** (új parancs) → név: `VeSpendo`.
2. Jobb felül az **(i)** → kapcsold be a **Megjelenítés a megosztási lapon** opciót → fogadott típusok: csak **PDF-ek**
   (és szükség esetén **Táblázatok**).
3. Adj hozzá két műveletet ebben a sorrendben:

   **a) URL tartalmának lekérése**
   - URL: `https://vespendo.cloudoptima.hu/api/v/banki-fajl-gyors-import`
     (a tételek tulajdonosa alapból a fiókodhoz kötött személy; másik személyhez hozzáfűzhető a `?feltolto=<személy kulcsa>`)
   - Metódus: **POST**
   - Fejlécek: `Authorization` = `Bearer vsp_…` (API token: VeSpendo Beállítások → **API tokenek** → Új token; a token csak
     létrehozáskor látható, és csak a banki fájl feltöltésére jó; bármikor törölhető)
   - Kérés törzse: **Fájl**, és a fájl legyen a **Parancs bemenete** (Shortcut Input).
     **Fontos:** a törzs típusa „Fájl” legyen, ne „Szöveg” vagy „JSON”. Ha a bemenetet szövegként használod, a Parancsok
     a PDF szövegét küldi el, és az import hibát ad.

   **b) Szótár értékének lekérése** → kulcs: `uzenet`, majd **Értesítés megjelenítése** a kapott értékkel.
   Siker és hiba esetén is az `uzenet` mezőben jön a válasz.

## Használat
Bankoldalon a letöltött PDF → **Megosztás** → **VeSpendo**. Pár másodperc múlva az értesítés megmondja, hány új tétel jött be
(például „12 új tétel, 79 már rögzítve volt”). A tételek a VeSpendo appban húzással frissíthetők.

## Megjegyzések
- A PDF a saját szervereden dolgozódik fel (nincs külső szolgáltatás; az ismeretlen kereskedők besorolásához a
  leírás rövid szövege a Claude Haikunak megy, a teljes fájl nem).
- Ha az értesítés hibát mutat („jelszóval védett”, „képként tartalmaz szöveget”), a PDF-et a bank egyéb módon védi
  vagy szkennelt; ilyenkor CSV/XLSX exportot kell használni.
- Az appban a **+ → Banki fájl tallózása** is megmarad (előnézettel), ha ellenőrizni szeretnéd import előtt.
