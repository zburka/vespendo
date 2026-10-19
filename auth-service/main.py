"""VeSpendo auth gateway: /api/auth/* (fiók, háztartás) és /api/v/{végpont} (n8n továbbítás)."""
import os

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from kapu.baserow import BaserowKliens
from kapu.beallitasok import Beallitasok
from kapu.biztonsag import HibaKod
from kapu.db import Adatbazis
from kapu.proxy import Tovabbito
from kapu.szolgaltatas import Kapu


def alkalmazas(cfg: Beallitasok | None = None, baserow=None, tovabbito=None) -> FastAPI:
    cfg = cfg or Beallitasok.kornyezetbol()
    cfg.ellenoriz()
    kapu = Kapu(cfg, Adatbazis(cfg.db_utvonal), baserow or BaserowKliens(cfg))
    tov = tovabbito or Tovabbito(cfg)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.exception_handler(HibaKod)
    async def hiba(_: Request, e: HibaKod):
        return JSONResponse({"hiba": e.uzenet}, status_code=e.kod)

    def ip(r: Request) -> str:
        return (r.headers.get("x-forwarded-for", "").split(",")[0].strip() or (r.client.host if r.client else ""))

    def ctx(r: Request) -> dict:
        h = r.headers.get("authorization", "")
        if not h.lower().startswith("bearer "):
            raise HibaKod("Bejelentkezés szükséges.", 401)
        return kapu.kontextus(h[7:].strip())

    def csak_ember(c: dict = Depends(ctx)) -> dict:
        if c["api_token"]:
            raise HibaKod("API tokennel ez nem érhető el.", 403)
        return c

    def nem_demo(c: dict = Depends(csak_ember)) -> dict:
        if c["demo"]:
            raise HibaKod("A demóban a fiók- és háztartás-beállítások nem módosíthatók.", 403)
        return c

    class Reg(BaseModel):
        email: str
        jelszo: str
        nev: str
        regisztracios_kod: str = ""
        meghivokod: str = ""
        haztartas_nev: str = ""

    class Bel(BaseModel):
        email: str
        jelszo: str

    class Frissit(BaseModel):
        frissito_token: str

    class JelszoCsere(BaseModel):
        regi: str
        uj: str

    class Szemely(BaseModel):
        kulcs: str

    class Otlet(BaseModel):
        szoveg: str

    class TokenNev(BaseModel):
        nev: str = ""

    @app.post("/api/auth/regisztracio")
    def regisztracio(b: Reg, r: Request):
        return kapu.regisztracio(b.email, b.jelszo, b.nev, b.regisztracios_kod, b.meghivokod, b.haztartas_nev, ip(r),
                                 r.headers.get("user-agent", ""))

    @app.post("/api/auth/belepes")
    def belepes(b: Bel, r: Request):
        return kapu.belepes(b.email, b.jelszo, ip(r), r.headers.get("user-agent", ""))

    @app.post("/api/auth/demo")
    def demo(r: Request):
        return kapu.demo_belepes(ip(r), r.headers.get("user-agent", ""))

    @app.post("/api/auth/frissites")
    def frissites(b: Frissit, r: Request):
        return kapu.frissites(b.frissito_token, r.headers.get("user-agent", ""))

    @app.post("/api/auth/kilepes")
    def kilepes(b: Frissit):
        kapu.kilepes(b.frissito_token)
        return {"ok": True}

    @app.get("/api/auth/en")
    def en(c: dict = Depends(csak_ember)):
        return kapu.en(c["felhasznalo_id"])

    @app.post("/api/auth/szemely")
    def szemely(b: Szemely, c: dict = Depends(csak_ember)):
        kapu.szemely_kapcsolas(c["felhasznalo_id"], c["haztartas"], b.kulcs)
        return kapu.en(c["felhasznalo_id"])

    @app.post("/api/auth/jelszo")
    def jelszo(b: JelszoCsere, c: dict = Depends(nem_demo)):
        kapu.jelszo_csere(c["felhasznalo_id"], b.regi, b.uj)
        return {"ok": True}

    @app.post("/api/auth/meghivokod")
    def meghivo(c: dict = Depends(nem_demo)):
        return {"meghivokod": kapu.uj_meghivokod(c)}

    @app.post("/api/auth/tagok/{tag_id}/jelszo-visszaallitas")
    def visszaallit(tag_id: int, c: dict = Depends(nem_demo)):
        return {"ideiglenes_jelszo": kapu.tag_jelszo_visszaallitas(c, tag_id)}

    @app.delete("/api/auth/tagok/{tag_id}")
    def eltavolit(tag_id: int, c: dict = Depends(nem_demo)):
        kapu.tag_eltavolit(c, tag_id)
        return {"ok": True}

    @app.post("/api/auth/otlet")
    def otlet(b: Otlet, c: dict = Depends(nem_demo)):
        return kapu.otlet(c, b.szoveg)

    @app.get("/api/auth/api-tokenek")
    def tokenek(c: dict = Depends(csak_ember)):
        return kapu.api_tokenek(c["felhasznalo_id"])

    @app.post("/api/auth/api-tokenek")
    def token_uj(b: TokenNev, c: dict = Depends(nem_demo)):
        return kapu.api_token_letrehoz(c["felhasznalo_id"], b.nev)

    @app.delete("/api/auth/api-tokenek/{token_id}")
    def token_torol(token_id: int, c: dict = Depends(nem_demo)):
        kapu.api_token_torol(c["felhasznalo_id"], token_id)
        return {"ok": True}

    @app.api_route("/api/v/{nev}", methods=["GET", "POST"])
    async def vegpont(nev: str, r: Request, c: dict = Depends(ctx)):
        tov.ellenoriz(nev, r.method, c)
        if c["demo"] and r.method == "POST":
            kapu.demo_korlat(ip(r))
        torzs = await r.body()
        if len(torzs) > cfg.max_torzs_bajt:
            raise HibaKod("Túl nagy kérés.", 413)
        v = tov.tovabbit(nev, r.method, c, list(r.query_params.multi_items()), torzs, dict(r.headers))
        return Response(v.content, status_code=v.status_code, media_type=v.headers.get("content-type", "application/json"))

    @app.get("/api/health")
    def health():
        return {"ok": True}

    return app


app = alkalmazas() if os.environ.get("AUTH_JWT_TITOK") else None
