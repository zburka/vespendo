"""Enable Banking API kliens: JWT, jóváhagyás indítása, munkamenet, tranzakciók, normalizálás.

A privát kulcs csak ebben a konténerben él (csak olvasható csatolás), az n8n nem látja.
"""
import base64
import copy
import hashlib
import hmac
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt

API = "https://api.enablebanking.com"
ASPSP_NEV = "OTP Bank"
ASPSP_ORSZAG = "HU"
STATE_ERVENYESSEG_MP = 30 * 60
MOCK = os.environ.get("BANK_MOCK") == "1"  # csak tesztkonténerben: hamis bank, nincs külső hívás


class BankHiba(Exception):
    """Felhasználónak megjeleníthető hiba (a hívó 4xx/5xx kódra fordítja)."""

    def __init__(self, uzenet: str, kod: int = 502):
        super().__init__(uzenet)
        self.kod = kod


class Konfig:
    def __init__(self):
        self.app_id = os.environ.get("ENABLEBANKING_APP_ID", "")
        self.kulcs_utvonal = os.environ.get("ENABLEBANKING_KEY_PATH", "/run/secrets/enablebanking.pem")
        self.redirect_url = os.environ.get("BANK_REDIRECT_URL", "https://n8n.cloudoptima.hu/webhook/bank-callback")
        self.api_kulcs = os.environ.get("BANK_API_KEY", "")
        self.api = os.environ.get("ENABLEBANKING_API", API)
        # további Enable Banking alkalmazások (pl. másik személy saját alkalmazása): {"2": {"app_id": "...", "kulcs": "/run/secrets/...pem"}}
        self.alkalmazasok: dict = json.loads(os.environ.get("BANK_ALKALMAZASOK", "") or "{}")

    def app(self, nev: str = "alap") -> "Konfig":
        """Az adott nevű alkalmazás beállításai (az 'alap' az alapértelmezett)."""
        if not nev or nev == "alap":
            return self
        a = self.alkalmazasok.get(nev)
        if not a:
            raise BankHiba(f"Ismeretlen banki alkalmazás: {nev}", 400)
        k = copy.copy(self)
        k.app_id, k.kulcs_utvonal = a["app_id"], a["kulcs"]
        return k


_token_gyorsitotar: dict = {}


def jwt_token(konfig: Konfig, most: float | None = None) -> str:
    """Bearer JWT az Enable Banking API-hoz (RS256, kid = Application ID, TTL 1 óra, 50 percig újrahasznosítva)."""
    most = most or time.time()
    t = _token_gyorsitotar.get((konfig.app_id, konfig.kulcs_utvonal))
    if t and t[1] > most + 600:
        return t[0]
    try:
        privat = open(konfig.kulcs_utvonal, "rb").read()
    except OSError as e:
        raise BankHiba("A privát kulcs nem olvasható a szolgáltatásban.", 500) from e
    lejar = int(most) + 3600
    token = jwt.encode(
        {"iss": "enablebanking.com", "aud": "api.enablebanking.com", "iat": int(most), "exp": lejar},
        privat,
        algorithm="RS256",
        headers={"typ": "JWT", "kid": konfig.app_id},
    )
    _token_gyorsitotar[(konfig.app_id, konfig.kulcs_utvonal)] = (token, lejar)
    return token


def _kerj(konfig: Konfig, metodus: str, ut: str, **kw):
    try:
        with httpx.Client(timeout=45) as c:
            r = c.request(metodus, konfig.api + ut, headers={"Authorization": f"Bearer {jwt_token(konfig)}"}, **kw)
    except httpx.HTTPError as e:
        raise BankHiba(f"Az Enable Banking nem érhető el: {e.__class__.__name__}") from e
    if r.status_code >= 400:
        try:
            reszlet = r.json()
        except ValueError:
            reszlet = {}
        uzenet = reszlet.get("message") or reszlet.get("error") or r.text[:200]
        raise BankHiba(f"Enable Banking hiba ({r.status_code}): {uzenet}", 502 if r.status_code >= 500 else 400)
    return r.json() if r.content else {}


# --- state: állapotmentes, aláírt (nem kell tárolni, lejár)
def state_keszit(konfig: Konfig, szemely: str, most: float | None = None, alkalmazas: str = "alap") -> str:
    adat = json.dumps({"p": szemely, "a": alkalmazas, "t": int(most or time.time()), "n": uuid.uuid4().hex[:12]}, separators=(",", ":"))
    b = base64.urlsafe_b64encode(adat.encode()).decode().rstrip("=")
    alair = hmac.new(konfig.api_kulcs.encode(), b.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{b}.{alair}"


def state_ellenoriz(konfig: Konfig, state: str, most: float | None = None) -> str:
    return state_adat(konfig, state, most)["p"]


def state_adat(konfig: Konfig, state: str, most: float | None = None) -> dict:
    try:
        b, alair = state.rsplit(".", 1)
        vart = hmac.new(konfig.api_kulcs.encode(), b.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(alair, vart):
            raise ValueError
        adat = json.loads(base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)))
    except Exception as e:
        raise BankHiba("Érvénytelen állapot (state): a hivatkozás nem tőlünk származik.", 400) from e
    if (most or time.time()) - adat["t"] > STATE_ERVENYESSEG_MP:
        raise BankHiba("A jóváhagyási hivatkozás lejárt, indítsd újra az összekötést.", 400)
    adat.setdefault("a", "alap")
    return adat


def maximalis_hozzaferes_napok(konfig: Konfig) -> int:
    """Az OTP megengedett hozzáférési időtartama napokban (a bank adata, hiánya esetén 90 nap)."""
    try:
        lista = _kerj(konfig, "GET", "/aspsps", params={"country": ASPSP_ORSZAG}).get("aspsps", [])
        for a in lista:
            if a.get("name") == ASPSP_NEV and a.get("maximum_consent_validity"):
                return max(1, int(a["maximum_consent_validity"]) // 86400)
    except BankHiba:
        pass
    return 90


def auth_inditas(konfig: Konfig, szemely: str, napok: int | None = None, most: datetime | None = None,
                 alkalmazas: str = "alap") -> dict:
    most = most or datetime.now(timezone.utc)
    app = konfig.app(alkalmazas)  # ismeretlen alkalmazásnál hiba, még mock módban is
    if MOCK:
        st = state_keszit(konfig, szemely, alkalmazas=alkalmazas)
        return {"url": f"{konfig.redirect_url}?code=mock&state={st}", "authorization_id": "mock", "napok": napok or 90}
    napok = min(napok or 180, maximalis_hozzaferes_napok(app))
    lejar = (most + timedelta(days=napok)).strftime("%Y-%m-%dT%H:%M:%S.000000+00:00")
    valasz = _kerj(app, "POST", "/auth", json={
        "access": {"valid_until": lejar},
        "aspsp": {"name": ASPSP_NEV, "country": ASPSP_ORSZAG},
        "state": state_keszit(konfig, szemely, alkalmazas=alkalmazas),
        "redirect_url": konfig.redirect_url,
        "psu_type": "personal",
        "language": "hu",
    })
    return {"url": valasz.get("url"), "authorization_id": valasz.get("authorization_id"), "napok": napok}


def session_letrehozas(konfig: Konfig, code: str, state: str) -> dict:
    adat = state_adat(konfig, state)
    szemely, alkalmazas = adat["p"], adat["a"]
    app = konfig.app(alkalmazas)
    if MOCK:
        lejar = (datetime.now(timezone.utc) + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%S.000000+00:00")
        return {"szemely": szemely, "alkalmazas": alkalmazas, "session_id": f"mock-session-{szemely}",
                "szamlak": [{"uid": f"mock-uid-{szemely}", "iban": "HU00MOCK0000", "nev": "Mock folyószámla"}], "valid_until": lejar}
    v = _kerj(app, "POST", "/sessions", json={"code": code})
    # diagnosztika (személyes adat nélkül): milyen mezőket és hány számlát ad vissza az Enable Banking
    logging.getLogger("uvicorn.error").info(
        "session: mezők=%s számla=%s accounts_data=%s aspsp=%s",
        sorted(v.keys()), len(v.get("accounts", [])), len(v.get("accounts_data", []) or []), (v.get("aspsp") or {}).get("name"),
    )
    szamlak = [
        {"uid": a.get("uid"), "iban": (a.get("account_id") or {}).get("iban"), "nev": a.get("name") or a.get("details")}
        for a in v.get("accounts", [])
    ]
    return {
        "szemely": szemely,
        "alkalmazas": alkalmazas,
        "session_id": v.get("session_id"),
        "szamlak": szamlak,
        "valid_until": (v.get("access") or {}).get("valid_until"),
    }


def normalizal(t: dict) -> dict | None:
    """Egy banki tétel a VeSpendo import formátumára. A függőben lévő (nem BOOK) tételeket kihagyja."""
    if (t.get("status") or "BOOK") != "BOOK":
        return None
    datum = t.get("booking_date") or t.get("value_date") or t.get("transaction_date")
    ta = t.get("transaction_amount") or {}
    try:
        osszeg = abs(float(ta.get("amount")))
    except (TypeError, ValueError):
        return None
    if not datum or osszeg == 0:
        return None
    bevetel = t.get("credit_debit_indicator") == "CRDT"
    partner = (t.get("debtor") if bevetel else t.get("creditor")) or {}
    partner_nev = (partner.get("name") or "").strip()
    # a bank tranzakciótípusa (pl. 'AZONNALI FIZETÉS BANKON BELÜL', 'ÁRUVÁSÁRLÁSI HITEL TÖRL.') mondja meg, mi a tétel
    bt = ((t.get("bank_transaction_code") or {}).get("description") or "").strip()
    if partner_nev.upper() == bt.upper():  # pl. visszatérítésnél a bank a típust adja névként: ne írjuk ki duplán
        partner_nev = ""
    kozl = " ".join(x.strip() for x in (t.get("remittance_information") or []) if x and x.strip())
    deviza = ta.get("currency")
    # kártyás vásárlás: a típus vagy a közlemény mintája ('ÉÉÉÉ.HH.NN <kártya/hivatkozás szám> <kereskedő> -APPLE')
    kartya = bt.upper().startswith("VÁSÁRLÁS KÁRTYÁVAL") or bool(re.match(r"^\d{4}\.\d{2}\.\d{2}\s+\d{6,}", kozl))
    if kartya:
        nev = partner_nev or kozl[:80] or "Ismeretlen"
    else:  # a PDF-es névvel azonos szerkezet: '<típus>, <partner>'
        nev = ", ".join(x for x in (bt, partner_nev) if x) or kozl[:80] or "Ismeretlen"
    reszek = [bt] if bt else []
    if partner_nev:
        reszek.append(f"{'Feladó' if bevetel else 'Kedvezményezett'}: {partner_nev}")
    if kozl:
        reszek.append(f"Közlemény: {kozl}")
    if deviza and deviza != "HUF":
        reszek.append(f"{ta.get('amount')} {deviza}")
    kozlemeny = " | ".join(reszek)
    ref = t.get("entry_reference") or t.get("transaction_id")
    return {
        "datum": datum,
        "osszeg": round(osszeg, 2),
        "kereskedo_nyers": nev,
        "kozlemeny": kozlemeny,
        "irany": "bevetel" if bevetel else "kiadas",
        "kulcs": f"eb:{ref}" if ref else None,
        "penznem": deviza or "HUF",
        "fizetesi_mod": "kartya" if kartya else "atutalas",
    }


def _mock_tetelek() -> list[dict]:
    ma = datetime.now(timezone.utc).date()
    nap = lambda n: (ma - timedelta(days=n)).isoformat()
    return [
        {"entry_reference": "mock1", "booking_date": nap(2), "status": "BOOK", "credit_debit_indicator": "DBIT",
         "transaction_amount": {"amount": "12345.00", "currency": "HUF"}, "creditor": {"name": "LIDL MOCK"}, "remittance_information": ["Vásárlás kártyával"]},
        {"entry_reference": "mock2", "booking_date": nap(1), "status": "BOOK", "credit_debit_indicator": "CRDT",
         "transaction_amount": {"amount": "500000.00", "currency": "HUF"}, "debtor": {"name": "MOCK MUNKAADÓ KFT"}, "remittance_information": ["munkabér"]},
        {"entry_reference": "mock3", "booking_date": nap(0), "status": "BOOK", "credit_debit_indicator": "DBIT",
         "transaction_amount": {"amount": "4490.00", "currency": "HUF"}, "creditor": {"name": "NETFLIX MOCK"}, "remittance_information": []},
        {"entry_reference": "mock4", "booking_date": nap(0), "status": "PDNG", "credit_debit_indicator": "DBIT",
         "transaction_amount": {"amount": "999.00", "currency": "HUF"}, "creditor": {"name": "FÜGGŐBEN"}},
    ]


def tranzakciok(konfig: Konfig, uid: str, date_from: str, date_to: str | None = None, max_oldal: int = 30) -> dict:
    kulcs, ossz, ki, kihagyott = None, 0, [], 0
    if MOCK:
        for t in _mock_tetelek():
            ossz += 1
            n = normalizal(t) if t["booking_date"] >= date_from else None
            ki.append(n) if n else None
            kihagyott += 0 if n else 1
        return {"tranzakciok": ki, "osszes": ossz, "kihagyott": kihagyott}
    for _ in range(max_oldal):
        params = {"date_from": date_from, "transaction_status": "BOOK"}
        if date_to:
            params["date_to"] = date_to
        if kulcs:
            params["continuation_key"] = kulcs
        v = _kerj(konfig, "GET", f"/accounts/{uid}/transactions", params=params)
        for t in v.get("transactions", []):
            ossz += 1
            n = normalizal(t)
            if n:
                ki.append(n)
            else:
                kihagyott += 1
        kulcs = v.get("continuation_key")
        if not kulcs:
            break
    return {"tranzakciok": ki, "osszes": ossz, "kihagyott": kihagyott}


def egyenleg(konfig: Konfig, uid: str) -> list:
    if MOCK:
        return [{"name": "mock", "balance_amount": {"amount": "1000000.00", "currency": "HUF"}, "balance_type": "CLAV"}]
    return _kerj(konfig, "GET", f"/accounts/{uid}/balances").get("balances", [])


def alkalmazas(konfig: Konfig) -> dict:
    if MOCK:
        return {"name": "MOCK", "kid": "mock", "environment": "MOCK", "active": True}
    return _kerj(konfig, "GET", "/application")
