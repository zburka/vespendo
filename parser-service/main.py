"""Banki fájl elemző mikroszolgáltatás. Az n8n hívja (HTTP Request node), az app nem közvetlenül."""
import base64
import binascii
import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from bankparse import ParseHiba, elemez

MAX_BAJT = 10 * 1024 * 1024
API_KULCS = os.environ.get("PARSER_API_KEY", "")

app = FastAPI(title="VeSpendo banki elemző")


class Keres(BaseModel):
    fajl_nev: str
    fajl_base64: str  # tiszta base64 vagy data URI


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/parse")
def parse(keres: Keres, x_api_key: str = Header(default="")):
    if API_KULCS and x_api_key != API_KULCS:
        raise HTTPException(status_code=401, detail="Hibás API kulcs")
    try:
        adat = base64.b64decode(keres.fajl_base64.split(",", 1)[-1], validate=False)
    except (binascii.Error, ValueError):
        return JSONResponse(status_code=422, content={"status": "error", "uzenet": "Hibás base64 tartalom."})
    if len(adat) > MAX_BAJT:
        return JSONResponse(status_code=413, content={"status": "error", "uzenet": "A fájl túl nagy (max. 10 MB)."})
    try:
        return {"status": "success", "data": elemez(adat, keres.fajl_nev)}
    except ParseHiba as e:
        return JSONResponse(status_code=422, content={"status": "error", "uzenet": str(e)})
