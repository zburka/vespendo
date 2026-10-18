import httpx
import pytest
from fastapi.testclient import TestClient

from kapu.beallitasok import Beallitasok
from main import alkalmazas

JELSZO = "Hosszu-Jelszo-123"


class HamisBaserow:
    def __init__(self):
        self.letrehozva = []

    def haztartas_letrehozas(self, hz, nev):
        self.letrehozva.append(hz)
        return nev.lower()

    def szemely_letezik(self, hz, kulcs):
        return kulcs in ("anna", "bela")


class HamisN8n:
    def __init__(self):
        self.hivasok = []

    def request(self, metodus, url, params=None, content=None, headers=None):
        self.hivasok.append((metodus, url, params, headers))
        return httpx.Response(200, json={"ok": True})


class Tov:
    pass


@pytest.fixture
def kozeg(tmp_path):
    from kapu.proxy import Tovabbito
    cfg = Beallitasok(db_utvonal=str(tmp_path / "a.db"), jwt_titok="x" * 40, n8n_belso_kulcs="belso", regisztracios_kod="mesterkod")
    n8n = HamisN8n()
    t = Tovabbito(cfg, kliens=n8n)
    bs = HamisBaserow()
    return TestClient(alkalmazas(cfg, bs, t)), n8n, bs


def reg(c, email, **kw):
    return c.post("/api/auth/regisztracio", json={"email": email, "jelszo": JELSZO, "nev": "Anna", **kw})


def fej(r):
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_regisztracio_kodot_kovetel(kozeg):
    c, _, _ = kozeg
    assert reg(c, "a@x.hu").status_code == 403
    assert reg(c, "a@x.hu", regisztracios_kod="mesterkod").status_code == 200


def test_gyenge_jelszo_es_duplikalt_email(kozeg):
    c, _, _ = kozeg
    assert c.post("/api/auth/regisztracio", json={"email": "a@x.hu", "jelszo": "rovid", "nev": "A", "regisztracios_kod": "mesterkod"}).status_code == 400
    assert reg(c, "a@x.hu", regisztracios_kod="mesterkod").status_code == 200
    assert reg(c, "A@x.hu", regisztracios_kod="mesterkod").status_code == 409


def test_meghivokoddal_csatlakozas_es_jogosultsag(kozeg):
    c, _, _ = kozeg
    a = reg(c, "a@x.hu", regisztracios_kod="mesterkod")
    kod = c.get("/api/auth/en", headers=fej(a)).json()["haztartas"]["meghivokod"]
    b = reg(c, "b@x.hu", meghivokod=kod)  # regisztrációs kód nélkül
    assert b.status_code == 200
    en = c.get("/api/auth/en", headers=fej(b)).json()
    assert en["haztartas"]["szerep"] == "tag" and en["haztartas"]["meghivokod"] is None
    assert all(t["email"] is None for t in en["tagok"])
    assert c.post("/api/auth/meghivokod", headers=fej(b)).status_code == 403
    assert reg(c, "c@x.hu", meghivokod="HAMISKOD").status_code == 404


def test_belepes_es_ratelimit(kozeg):
    c, _, _ = kozeg
    reg(c, "a@x.hu", regisztracios_kod="mesterkod")
    assert c.post("/api/auth/belepes", json={"email": "a@x.hu", "jelszo": JELSZO}).status_code == 200
    for _ in range(5):
        assert c.post("/api/auth/belepes", json={"email": "a@x.hu", "jelszo": "rossz-jelszo-1"}).status_code == 401
    assert c.post("/api/auth/belepes", json={"email": "a@x.hu", "jelszo": JELSZO}).status_code == 429


def test_frissito_rotacio_es_ujrahasznalat(kozeg):
    c, _, _ = kozeg
    r = reg(c, "a@x.hu", regisztracios_kod="mesterkod").json()
    uj = c.post("/api/auth/frissites", json={"frissito_token": r["frissito_token"]})
    assert uj.status_code == 200
    # a régi token újrahasználata minden munkamenetet lezár
    assert c.post("/api/auth/frissites", json={"frissito_token": r["frissito_token"]}).status_code == 401
    assert c.post("/api/auth/frissites", json={"frissito_token": uj.json()["frissito_token"]}).status_code == 401


def test_proxy_haztartast_a_kapu_allit(kozeg):
    c, n8n, _ = kozeg
    a = reg(c, "a@x.hu", regisztracios_kod="mesterkod")
    hz = c.get("/api/auth/en", headers=fej(a)).json()["haztartas"]["id"]
    h = {**fej(a), "X-Haztartas": "hz_masik", "X-Szemely": "bela"}
    assert c.get("/api/v/adatok?haztartas=hz_masik", headers=h).status_code == 200
    _, url, params, fejlec = n8n.hivasok[-1]
    assert fejlec["X-Haztartas"] == hz and fejlec["X-Szemely"] == "anna" and fejlec["X-App-Key"] == "belso"
    assert ("haztartas", "hz_masik") not in params


def test_proxy_whitelist_es_hitelesites(kozeg):
    c, n8n, _ = kozeg
    a = reg(c, "a@x.hu", regisztracios_kod="mesterkod")
    assert c.get("/api/v/adatok").status_code == 401
    assert c.get("/api/v/adatok", headers={"Authorization": "Bearer hamis"}).status_code == 401
    assert c.get("/api/v/ismeretlen", headers=fej(a)).status_code == 404
    assert c.post("/api/v/adatok", headers=fej(a)).status_code == 405
    assert c.get("/api/v/bank-allapot", headers=fej(a)).status_code == 403  # bank nincs engedélyezve
    assert n8n.hivasok == []


def test_api_token_csak_gyors_importra(kozeg):
    c, n8n, _ = kozeg
    a = reg(c, "a@x.hu", regisztracios_kod="mesterkod")
    t = c.post("/api/auth/api-tokenek", json={"nev": "iPhone"}, headers=fej(a)).json()["token"]
    ah = {"Authorization": f"Bearer {t}"}
    assert c.get("/api/v/adatok", headers=ah).status_code == 403
    assert c.get("/api/auth/en", headers=ah).status_code == 403
    assert c.post("/api/v/banki-fajl-gyors-import", content=b"x", headers=ah).status_code == 200


def test_tag_eltavolitas_azonnal_hatalyos(kozeg):
    c, _, _ = kozeg
    a = reg(c, "a@x.hu", regisztracios_kod="mesterkod")
    kod = c.get("/api/auth/en", headers=fej(a)).json()["haztartas"]["meghivokod"]
    b = reg(c, "b@x.hu", meghivokod=kod)
    bid = c.get("/api/auth/en", headers=fej(b)).json()["felhasznalo"]["id"]
    assert c.get("/api/v/adatok", headers=fej(b)).status_code == 200
    assert c.delete(f"/api/auth/tagok/{bid}", headers=fej(a)).status_code == 200
    assert c.get("/api/v/adatok", headers=fej(b)).status_code == 401  # a még érvényes access token sem él tovább
    assert c.post("/api/auth/frissites", json={"frissito_token": b.json()["frissito_token"]}).status_code == 401


def test_jelszocsere_lezarja_a_tobbi_eszkozt(kozeg):
    c, _, _ = kozeg
    r = reg(c, "a@x.hu", regisztracios_kod="mesterkod")
    assert c.post("/api/auth/jelszo", json={"regi": JELSZO, "uj": "Uj-Hosszu-Jelszo-9"}, headers=fej(r)).status_code == 200
    assert c.post("/api/auth/frissites", json={"frissito_token": r.json()["frissito_token"]}).status_code == 401
    assert c.post("/api/auth/belepes", json={"email": "a@x.hu", "jelszo": "Uj-Hosszu-Jelszo-9"}).status_code == 200
