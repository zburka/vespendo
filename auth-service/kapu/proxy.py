"""Whitelistes továbbítás az n8n webhookokhoz: a kliens csak a felsorolt végpontokat érheti el,
az n8n felé a háztartást és a személyt a kapu (nem a kliens) jelöli ki."""
import httpx

from .beallitasok import Beallitasok
from .biztonsag import HibaKod

# végpont -> (megengedett metódusok, banki-e, API tokennel is hívható-e)
VEGPONTOK: dict[str, tuple[frozenset, bool, bool]] = {
    "adatok": (frozenset({"GET"}), False, False),
    "tranzakciok": (frozenset({"GET"}), False, False),
    "havi-osszesito": (frozenset({"GET"}), False, False),
    "banki-import": (frozenset({"POST"}), False, False),
    "banki-fajl-elemzes": (frozenset({"POST"}), False, False),
    "banki-fajl-gyors-import": (frozenset({"POST"}), False, True),
    "kategoria-modositas": (frozenset({"POST"}), False, False),
    "tranzakcio-felvetel": (frozenset({"POST"}), False, False),
    "tranzakcio-modositas": (frozenset({"POST"}), False, False),
    "tranzakcio-torles": (frozenset({"POST"}), False, False),
    "nyugta-feltoltes": (frozenset({"POST"}), False, False),
    "keret-mentes": (frozenset({"POST"}), False, False),
    "cel-mentes": (frozenset({"POST"}), False, False),
    "cel-torles": (frozenset({"POST"}), False, False),
    "elofizetes-mentes": (frozenset({"POST"}), False, False),
    "elofizetes-torles": (frozenset({"POST"}), False, False),
    "szemely-mentes": (frozenset({"POST"}), False, False),
    "bank-osszekotes": (frozenset({"POST"}), True, False),
    "bank-szinkron": (frozenset({"POST"}), True, False),
    "bank-allapot": (frozenset({"GET"}), True, False),
}

# a kliens ezeket soha nem állíthatja be
TILTOTT_FEJLEC = {"x-haztartas", "x-felhasznalo", "x-szemely", "x-app-key", "authorization", "host", "cookie"}
ATENGEDETT_FEJLEC = ("content-type", "accept")


class Tovabbito:
    def __init__(self, cfg: Beallitasok, kliens: httpx.Client | None = None):
        self.cfg = cfg
        self.http = kliens or httpx.Client(timeout=300)

    def ellenoriz(self, nev: str, metodus: str, ctx: dict) -> None:
        v = VEGPONTOK.get(nev)
        if not v:
            raise HibaKod("Ismeretlen végpont.", 404)
        if metodus not in v[0]:
            raise HibaKod("A metódus nem engedélyezett.", 405)
        if v[1] and not ctx["bank"]:
            raise HibaKod("A bankösszekötés ennél a háztartásnál nincs engedélyezve.", 403)
        if ctx["api_token"] and not v[2]:
            raise HibaKod("Az API token ehhez a művelethez nem használható.", 403)

    def tovabbit(self, nev: str, metodus: str, ctx: dict, parameterek: list[tuple[str, str]], torzs: bytes,
                 fejlecek: dict) -> httpx.Response:
        self.ellenoriz(nev, metodus, ctx)
        fej = {k: v for k, v in fejlecek.items() if k.lower() in ATENGEDETT_FEJLEC}
        fej.update({"X-App-Key": self.cfg.n8n_belso_kulcs, "X-Haztartas": ctx["haztartas"],
                    "X-Felhasznalo": str(ctx["felhasznalo_id"]), "X-Szemely": ctx["szemely"]})
        # a kliens a háztartásra utaló paramétert sem küldhet
        params = [(k, v) for k, v in parameterek if k.lower() not in {"haztartas", "szemely_kulcs_kapu"}]
        try:
            return self.http.request(metodus, f"{self.cfg.n8n_url}/webhook/{self.cfg.n8n_ut_elotag}{nev}",
                                     params=params, content=torzs, headers=fej)
        except httpx.HTTPError:
            raise HibaKod("A háttérszolgáltatás nem érhető el.", 502)
