"""Baserow-elérés: új háztartás induló adatainak létrehozása és (hiba esetén) visszavonása."""
import re
from urllib.parse import urlparse
import unicodedata

import httpx

from .alapadatok import KATEGORIAK, SZABALYOK
from .beallitasok import Beallitasok
from .biztonsag import HibaKod


def szemely_kulcs(nev: str) -> str:
    """'Zoltán' -> 'zoltan' (ékezet nélküli, a szemelyek tábla kulcsa)."""
    ascii_ = unicodedata.normalize("NFD", nev).encode("ascii", "ignore").decode().lower()
    k = re.sub(r"[^a-z0-9]+", "_", ascii_).strip("_")[:24] or "szemely"
    return "szemely" if k == "kozos" else k


class BaserowKliens:
    def __init__(self, cfg: Beallitasok, kliens: httpx.Client | None = None):
        self.cfg = cfg
        self.http = kliens or httpx.Client(timeout=60, headers={"User-Agent": "vespendo-kapu"})

    def _kerj(self, metodus: str, ut: str, **kw):
        r = self.http.request(metodus, self.cfg.baserow_url + ut, headers={"Authorization": f"Token {self.cfg.baserow_token}"}, **kw)
        if r.status_code >= 400:
            raise HibaKod(f"Az adatbázis hibát jelzett ({r.status_code}).", 502)
        return r.json() if r.content else {}

    def sorok_letrehoz(self, tabla: str, sorok: list[dict]) -> list[dict]:
        tid = self.cfg.baserow_tablak[tabla]
        ki: list[dict] = []
        for i in range(0, len(sorok), 200):
            ki += self._kerj("POST", f"/api/database/rows/table/{tid}/batch/?user_field_names=true", json={"items": sorok[i:i + 200]})["items"]
        return ki

    def sor_modosit(self, tabla: str, sor_id: int, adat: dict) -> None:
        tid = self.cfg.baserow_tablak[tabla]
        self._kerj("PATCH", f"/api/database/rows/table/{tid}/{sor_id}/?user_field_names=true", json=adat)

    def sorok(self, tabla: str, haztartas: str) -> list[dict]:
        tid = self.cfg.baserow_tablak[tabla]
        ki, ut = [], f"/api/database/rows/table/{tid}/?user_field_names=true&size=200&filter__haztartas__equal={haztartas}"
        while ut:
            v = self._kerj("GET", ut)
            ki += v["results"]
            nxt = v.get("next")
            ut = (lambda u: u.path + "?" + u.query)(urlparse(nxt)) if nxt else None
        return ki

    def sorok_torol(self, tabla: str, ids: list[int]) -> None:
        tid = self.cfg.baserow_tablak[tabla]
        for i in range(0, len(ids), 200):
            self._kerj("POST", f"/api/database/rows/table/{tid}/batch-delete/", json={"items": ids[i:i + 200]})

    # --- háztartás életciklusa
    def haztartas_letrehozas(self, hz: str, szemely_nev: str) -> str:
        """Kategóriák, szabályok, 'Közös' és a létrehozó személye. Visszaadja a létrehozó személykulcsát."""
        try:
            kat = self.sorok_letrehoz("kategoriak", [{"haztartas": hz, "nev": n, "tipus": t, "ikon": i} for n, t, i in KATEGORIAK])
            kat_id = {r["nev"]: r["id"] for r in kat}
            self.sorok_letrehoz("szabalymotor", [{"haztartas": hz, "minta": m, "kategoria_id": [kat_id[k]]} for m, k in SZABALYOK])
            kulcs = szemely_kulcs(szemely_nev)
            self.sorok_letrehoz("szemelyek", [
                {"haztartas": hz, "kulcs": "kozos", "nev": "Közös", "aktiv": True},
                {"haztartas": hz, "kulcs": kulcs, "nev": szemely_nev[:50], "aktiv": True},
            ])
            return kulcs
        except Exception:
            self.haztartas_torles(hz)
            raise

    def haztartas_torles(self, hz: str) -> None:
        for tabla in ("szabalymotor", "szemelyek", "kategoriak", "tranzakciok", "koltsegkeretek", "elofizetesek",
                      "megtakaritasi_celok", "bankkapcsolatok"):
            try:
                self.sorok_torol(tabla, [r["id"] for r in self.sorok(tabla, hz)])
            except Exception:  # a visszavonás best-effort
                pass

    def szemely_letezik(self, hz: str, kulcs: str) -> bool:
        return any(r["kulcs"] == kulcs and r.get("aktiv") for r in self.sorok("szemelyek", hz))
