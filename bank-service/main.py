"""VeSpendo banki szolgáltatás (Enable Banking). Az n8n hívja, kívülről nem elérhető."""
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bankapi import eb

konfig = eb.Konfig()
app = FastAPI(title="VeSpendo bank")


def _jog(kulcs: str):
    if not konfig.api_kulcs or kulcs != konfig.api_kulcs:
        raise HTTPException(status_code=401, detail="Hibás API kulcs")


@app.exception_handler(eb.BankHiba)
def bank_hiba(_, e: eb.BankHiba):
    return JSONResponse(status_code=e.kod, content={"status": "error", "uzenet": str(e)})


class AuthKeres(BaseModel):
    szemely: str
    napok: int | None = None


class SessionKeres(BaseModel):
    code: str
    state: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ellenorzes")
def ellenorzes(x_api_key: str = Header(default="")):
    """A kulcs és az alkalmazás ellenőrzése az Enable Banking felé."""
    _jog(x_api_key)
    a = eb.alkalmazas(konfig)
    return {"status": "success", "alkalmazas": {k: a.get(k) for k in ("name", "kid", "environment", "active", "restricted")}}


@app.post("/auth")
def auth(k: AuthKeres, x_api_key: str = Header(default="")):
    _jog(x_api_key)
    return {"status": "success", **eb.auth_inditas(konfig, k.szemely, k.napok)}


@app.post("/sessions")
def sessions(k: SessionKeres, x_api_key: str = Header(default="")):
    _jog(x_api_key)
    return {"status": "success", **eb.session_letrehozas(konfig, k.code, k.state)}


@app.get("/transactions")
def transactions(uid: str, date_from: str = Query(...), date_to: str | None = None, x_api_key: str = Header(default="")):
    _jog(x_api_key)
    return {"status": "success", **eb.tranzakciok(konfig, uid, date_from, date_to)}


@app.get("/balances")
def balances(uid: str, x_api_key: str = Header(default="")):
    _jog(x_api_key)
    return {"status": "success", "balances": eb.egyenleg(konfig, uid)}
