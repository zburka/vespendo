"""Üzleti logika: regisztráció, belépés, tokenek, háztartás-kezelés."""
import re
import secrets
import time
import uuid
from datetime import datetime, timezone

from . import biztonsag as b
from .baserow import BaserowKliens
from .beallitasok import Beallitasok
from .biztonsag import HibaKod
from .db import Adatbazis

PROBA_ABLAK_MP = 15 * 60
PROBA_LIMIT = 5
REG_LIMIT_ORA = 10


def _most() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Kapu:
    def __init__(self, cfg: Beallitasok, db: Adatbazis, baserow: BaserowKliens):
        self.cfg, self.db, self.baserow = cfg, db, baserow

    # ------------------------------------------------------------ kérés-korlátozás
    def _korlat(self, c, kulcs: str, limit: int, ablak: int, uzenet: str):
        n = c.execute("select count(*) from probalkozasok where kulcs=? and ido>?", (kulcs, int(time.time()) - ablak)).fetchone()[0]
        if n >= limit:
            raise HibaKod(uzenet, 429)

    def _proba(self, c, kulcs: str):
        c.execute("insert into probalkozasok(kulcs, ido) values(?,?)", (kulcs, int(time.time())))
        c.execute("delete from probalkozasok where ido<?", (int(time.time()) - 24 * 3600,))

    # ------------------------------------------------------------ tokenek
    def _token_par(self, c, felh_id: int, haztartas: str, eszkoz: str = "") -> dict:
        frissito, kivonat = b.uj_token("vsr_")
        lejar = int(time.time()) + self.cfg.frissito_ttl_nap * 86400
        c.execute("insert into frissito_tokenek(felhasznalo_id, token_hash, lejar, eszkoz, letrehozva) values(?,?,?,?,?)",
                  (felh_id, kivonat, lejar, eszkoz[:80], _most()))
        return {"access_token": b.access_token(self.cfg.jwt_titok, felh_id, haztartas, self.cfg.access_ttl_mp),
                "frissito_token": frissito, "lejarat_mp": self.cfg.access_ttl_mp}

    # ------------------------------------------------------------ regisztráció és belépés
    def regisztracio(self, email: str, jelszo: str, nev: str, regisztracios_kod: str = "", meghivokod: str = "",
                     haztartas_nev: str = "", ip: str = "", eszkoz: str = "") -> dict:
        email = b.email_rendbe(email)
        nev = (nev or "").strip()
        if not (1 <= len(nev) <= 50):
            raise HibaKod("Add meg a nevedet (legfeljebb 50 karakter).")
        b.jelszo_szabaly(jelszo, email)
        meghivokod = (meghivokod or "").strip().upper()
        with self.db.kapcsolat() as c:
            self._korlat(c, f"reg:{ip}", REG_LIMIT_ORA, 3600, "Túl sok regisztrációs kísérlet, próbáld később.")
            self._proba(c, f"reg:{ip}")
            hz = None
            if meghivokod:
                hz = c.execute("select * from haztartasok where meghivokod=?", (meghivokod,)).fetchone()
                if not hz:
                    raise HibaKod("Érvénytelen meghívókód.", 404)
            elif self.cfg.regisztracios_kod and not secrets.compare_digest(regisztracios_kod or "", self.cfg.regisztracios_kod):
                raise HibaKod("Új háztartás létrehozásához a regisztrációs kód kell (kérd el attól, aki a VeSpendo-t üzemelteti).", 403)
            if c.execute("select 1 from felhasznalok where email=?", (email,)).fetchone():
                raise HibaKod("Ezzel az e-mail címmel már van fiók.", 409)

            uj_hz = None
            if not hz:
                hz_id = "hz_" + uuid.uuid4().hex[:12]
                hz_nev = (haztartas_nev or "").strip()[:60] or f"{nev} háztartása"
                kod = b.meghivokod()
                c.execute("insert into haztartasok(id, nev, meghivokod, letrehozva) values(?,?,?,?)", (hz_id, hz_nev, kod, _most()))
                uj_hz = hz_id
            hz_id = hz["id"] if hz else uj_hz
            try:
                cur = c.execute("insert into felhasznalok(email, nev, jelszo_hash, letrehozva) values(?,?,?,?)",
                                (email, nev, b.jelszo_hash(jelszo), _most()))
                felh_id = cur.lastrowid
                tagok = c.execute("select count(*) from tagsagok where haztartas_id=?", (hz_id,)).fetchone()[0]
                szerep = "admin" if tagok == 0 else "tag"
                szemely = None
                if uj_hz:  # az induló adatokat az új háztartáshoz a létrehozó nevével hozzuk létre
                    szemely = self.baserow.haztartas_letrehozas(hz_id, nev)
                c.execute("insert into tagsagok(felhasznalo_id, haztartas_id, szerep, szemely_kulcs) values(?,?,?,?)",
                          (felh_id, hz_id, szerep, szemely))
            except Exception:
                if uj_hz:
                    c.execute("delete from haztartasok where id=?", (uj_hz,))
                c.execute("delete from felhasznalok where email=?", (email,))
                raise
            tokenek = self._token_par(c, felh_id, hz_id, eszkoz)
        return {**tokenek, "en": self.en(felh_id)}

    def belepes(self, email: str, jelszo: str, ip: str = "", eszkoz: str = "") -> dict:
        email = (email or "").strip().lower()
        kulcs = f"bel:{email}:{ip}"
        with self.db.kapcsolat() as c:
            self._korlat(c, kulcs, PROBA_LIMIT, PROBA_ABLAK_MP, "Túl sok sikertelen belépés, próbáld 15 perc múlva.")
            f = c.execute("select * from felhasznalok where email=?", (email,)).fetchone()
            # azonos futási idő akkor is, ha nincs ilyen fiók (nem szivárog, hogy létezik-e)
            helyes = b.jelszo_helyes(f["jelszo_hash"] if f else b.jelszo_hash("nincs-ilyen-fiok"), jelszo or "")
            if not f or not helyes or not f["aktiv"]:
                self._proba(c, kulcs)
                raise HibaKod("Hibás e-mail cím vagy jelszó.", 401)
            tag = c.execute("select * from tagsagok where felhasznalo_id=?", (f["id"],)).fetchone()
            if not tag:
                raise HibaKod("A fiók nem tartozik háztartáshoz.", 403)
            c.execute("delete from probalkozasok where kulcs=?", (kulcs,))
            tokenek = self._token_par(c, f["id"], tag["haztartas_id"], eszkoz)
        return {**tokenek, "en": self.en(f["id"])}

    def frissites(self, frissito_token: str, eszkoz: str = "") -> dict:
        kivonat = b.hash_token(frissito_token or "")
        with self.db.kapcsolat() as c:
            t = c.execute("select * from frissito_tokenek where token_hash=?", (kivonat,)).fetchone()
            if not t:
                raise HibaKod("Érvénytelen belépés.", 401)
            if t["visszavonva"]:  # már felhasznált token újrahasználata: lopás gyanúja, minden munkamenetet lezárunk
                c.execute("update frissito_tokenek set visszavonva=1 where felhasznalo_id=?", (t["felhasznalo_id"],))
                raise HibaKod("A munkamenet érvénytelen, lépj be újra.", 401)
            if t["lejar"] < time.time():
                raise HibaKod("A munkamenet lejárt, lépj be újra.", 401)
            f = c.execute("select * from felhasznalok where id=? and aktiv=1", (t["felhasznalo_id"],)).fetchone()
            tag = c.execute("select * from tagsagok where felhasznalo_id=?", (t["felhasznalo_id"],)).fetchone()
            if not f or not tag:
                raise HibaKod("Érvénytelen belépés.", 401)
            c.execute("update frissito_tokenek set visszavonva=1 where id=?", (t["id"],))
            return self._token_par(c, f["id"], tag["haztartas_id"], eszkoz or t["eszkoz"] or "")

    def kilepes(self, frissito_token: str) -> None:
        with self.db.kapcsolat() as c:
            c.execute("update frissito_tokenek set visszavonva=1 where token_hash=?", (b.hash_token(frissito_token or ""),))

    # ------------------------------------------------------------ azonosítás kérésenként
    def kontextus(self, token: str) -> dict:
        """Access token (vagy 'vsp_' API token) -> aktuális felhasználó és háztartás, MINDIG az adatbázisból ellenőrizve."""
        with self.db.kapcsolat() as c:
            if token.startswith("vsp_"):
                a = c.execute("select * from api_tokenek where token_hash=?", (b.hash_token(token),)).fetchone()
                if not a:
                    raise HibaKod("Érvénytelen API token.", 401)
                c.execute("update api_tokenek set utolso=? where id=?", (_most(), a["id"]))
                felh_id, api = a["felhasznalo_id"], True
            else:
                felh_id, api = int(b.access_dekod(self.cfg.jwt_titok, token)["sub"]), False
            f = c.execute("select * from felhasznalok where id=? and aktiv=1", (felh_id,)).fetchone()
            tag = c.execute("select t.*, h.bank_engedelyezett from tagsagok t join haztartasok h on h.id=t.haztartas_id "
                            "where t.felhasznalo_id=?", (felh_id,)).fetchone()
            if not f or not tag:
                raise HibaKod("Érvénytelen belépés.", 401)
            return {"felhasznalo_id": felh_id, "haztartas": tag["haztartas_id"], "szerep": tag["szerep"],
                    "szemely": tag["szemely_kulcs"] or "", "bank": bool(tag["bank_engedelyezett"]), "api_token": api}

    # ------------------------------------------------------------ profil és háztartás
    def en(self, felh_id: int) -> dict:
        with self.db.kapcsolat() as c:
            f = c.execute("select * from felhasznalok where id=?", (felh_id,)).fetchone()
            t = c.execute("select * from tagsagok where felhasznalo_id=?", (felh_id,)).fetchone()
            h = c.execute("select * from haztartasok where id=?", (t["haztartas_id"],)).fetchone()
            tagok = [dict(r) for r in c.execute(
                "select f.id, f.nev, f.email, t.szerep, t.szemely_kulcs from tagsagok t join felhasznalok f on f.id=t.felhasznalo_id "
                "where t.haztartas_id=? and f.aktiv=1 order by f.id", (h["id"],))]
        admin = t["szerep"] == "admin"
        return {
            "felhasznalo": {"id": f["id"], "nev": f["nev"], "email": f["email"]},
            "haztartas": {"id": h["id"], "nev": h["nev"], "szerep": t["szerep"], "szemely_kulcs": t["szemely_kulcs"],
                          "bank_engedelyezett": bool(h["bank_engedelyezett"]), "meghivokod": h["meghivokod"] if admin else None},
            "tagok": [{"id": x["id"], "nev": x["nev"], "szerep": x["szerep"], "szemely_kulcs": x["szemely_kulcs"],
                       "email": x["email"] if admin else None} for x in tagok],
        }

    def szemely_kapcsolas(self, felh_id: int, haztartas: str, kulcs: str) -> None:
        if not re.fullmatch(r"[a-z0-9_]{1,30}", kulcs or "") or kulcs == "kozos":
            raise HibaKod("Érvénytelen személy.")
        if not self.baserow.szemely_letezik(haztartas, kulcs):
            raise HibaKod("Nincs ilyen személy a háztartásban.", 404)
        with self.db.kapcsolat() as c:
            c.execute("update tagsagok set szemely_kulcs=? where felhasznalo_id=?", (kulcs, felh_id))

    def jelszo_csere(self, felh_id: int, regi: str, uj: str) -> None:
        with self.db.kapcsolat() as c:
            f = c.execute("select * from felhasznalok where id=?", (felh_id,)).fetchone()
            if not b.jelszo_helyes(f["jelszo_hash"], regi or ""):
                raise HibaKod("A jelenlegi jelszó hibás.", 403)
            b.jelszo_szabaly(uj, f["email"])
            c.execute("update felhasznalok set jelszo_hash=? where id=?", (b.jelszo_hash(uj), felh_id))
            c.execute("update frissito_tokenek set visszavonva=1 where felhasznalo_id=?", (felh_id,))  # minden eszköz újra belép

    def _admin(self, c, ctx: dict):
        if ctx["szerep"] != "admin":
            raise HibaKod("Ehhez háztartás-adminisztrátor jogosultság kell.", 403)

    def uj_meghivokod(self, ctx: dict) -> str:
        with self.db.kapcsolat() as c:
            self._admin(c, ctx)
            kod = b.meghivokod()
            c.execute("update haztartasok set meghivokod=? where id=?", (kod, ctx["haztartas"]))
        return kod

    def tag_jelszo_visszaallitas(self, ctx: dict, tag_id: int) -> str:
        with self.db.kapcsolat() as c:
            self._admin(c, ctx)
            t = c.execute("select * from tagsagok where felhasznalo_id=? and haztartas_id=?", (tag_id, ctx["haztartas"])).fetchone()
            if not t or tag_id == ctx["felhasznalo_id"]:
                raise HibaKod("Nincs ilyen tag.", 404)
            ideiglenes = secrets.token_urlsafe(9)
            c.execute("update felhasznalok set jelszo_hash=? where id=?", (b.jelszo_hash(ideiglenes), tag_id))
            c.execute("update frissito_tokenek set visszavonva=1 where felhasznalo_id=?", (tag_id,))
        return ideiglenes

    def tag_eltavolit(self, ctx: dict, tag_id: int) -> None:
        with self.db.kapcsolat() as c:
            self._admin(c, ctx)
            t = c.execute("select * from tagsagok where felhasznalo_id=? and haztartas_id=?", (tag_id, ctx["haztartas"])).fetchone()
            if not t or tag_id == ctx["felhasznalo_id"]:
                raise HibaKod("Nincs ilyen tag (magadat nem távolíthatod el).", 404)
            c.execute("update felhasznalok set aktiv=0 where id=?", (tag_id,))
            c.execute("delete from tagsagok where felhasznalo_id=?", (tag_id,))
            c.execute("update frissito_tokenek set visszavonva=1 where felhasznalo_id=?", (tag_id,))
            c.execute("delete from api_tokenek where felhasznalo_id=?", (tag_id,))

    # ------------------------------------------------------------ API tokenek (pl. iOS Parancsok)
    def api_token_letrehoz(self, felh_id: int, nev: str) -> dict:
        nev = (nev or "").strip()[:60] or "API token"
        token, kivonat = b.uj_token("vsp_")
        with self.db.kapcsolat() as c:
            if c.execute("select count(*) from api_tokenek where felhasznalo_id=?", (felh_id,)).fetchone()[0] >= 10:
                raise HibaKod("Legfeljebb 10 API token lehet.")
            cur = c.execute("insert into api_tokenek(felhasznalo_id, nev, token_hash, letrehozva) values(?,?,?,?)", (felh_id, nev, kivonat, _most()))
        return {"id": cur.lastrowid, "nev": nev, "token": token}

    def api_tokenek(self, felh_id: int) -> list[dict]:
        with self.db.kapcsolat() as c:
            return [dict(r) for r in c.execute("select id, nev, letrehozva, utolso from api_tokenek where felhasznalo_id=? order by id", (felh_id,))]

    def api_token_torol(self, felh_id: int, token_id: int) -> None:
        with self.db.kapcsolat() as c:
            c.execute("delete from api_tokenek where id=? and felhasznalo_id=?", (token_id, felh_id))
