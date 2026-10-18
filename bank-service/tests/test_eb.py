import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timezone

from bankapi import eb


@pytest.fixture
def konfig(tmp_path):
    kulcs = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    p = tmp_path / "k.pem"
    p.write_bytes(kulcs.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    k = eb.Konfig()
    k.app_id, k.kulcs_utvonal, k.api_kulcs = "app-123", str(p), "titok"
    k.publikus = kulcs.public_key()
    eb._token_gyorsitotar.clear()
    return k


def test_jwt_fejlec_es_claimek(konfig):
    t = eb.jwt_token(konfig, most=1_000_000)
    assert jwt.get_unverified_header(t) == {"typ": "JWT", "alg": "RS256", "kid": "app-123"}
    d = jwt.decode(t, konfig.publikus, algorithms=["RS256"], audience="api.enablebanking.com", options={"verify_exp": False})
    assert d["iss"] == "enablebanking.com" and d["iat"] == 1_000_000 and d["exp"] == 1_003_600


def test_jwt_ujrahasznositas_es_megujitas(konfig):
    a = eb.jwt_token(konfig, most=1_000_000)
    assert eb.jwt_token(konfig, most=1_000_100) == a          # friss: ugyanaz
    assert eb.jwt_token(konfig, most=1_003_100) != a          # 10 percen belül lejár: új


def test_hianyzo_kulcs_ertheto_hiba(konfig):
    konfig.kulcs_utvonal = "/nincs/ilyen.pem"
    with pytest.raises(eb.BankHiba):
        eb.jwt_token(konfig)


def test_state_alairt_lejaro_hamisithatatlan(konfig):
    s = eb.state_keszit(konfig, "feleseg", most=1000)
    assert eb.state_ellenoriz(konfig, s, most=1100) == "feleseg"
    with pytest.raises(eb.BankHiba):
        eb.state_ellenoriz(konfig, s, most=1000 + 31 * 60)    # lejárt
    b, a = s.rsplit(".", 1)
    with pytest.raises(eb.BankHiba):
        eb.state_ellenoriz(konfig, b + "." + "0" * 32, most=1100)   # hamis aláírás
    with pytest.raises(eb.BankHiba):
        eb.state_ellenoriz(konfig, "szemét", most=1100)


def test_normalizal_kiadas_bevetel_fuggoben_deviza():
    ki = eb.normalizal({"entry_reference": "R1", "booking_date": "2026-10-01", "status": "BOOK", "credit_debit_indicator": "DBIT",
                        "transaction_amount": {"amount": "1290.00", "currency": "HUF"}, "creditor": {"name": "Lidl"},
                        "remittance_information": ["Vásárlás", "kártyával"]})
    assert ki == {"datum": "2026-10-01", "osszeg": 1290.0, "kereskedo_nyers": "Lidl", "kozlemeny": "Kedvezményezett: Lidl | Közlemény: Vásárlás kártyával",
                  "irany": "kiadas", "kulcs": "eb:R1", "penznem": "HUF", "fizetesi_mod": "atutalas"}
    be = eb.normalizal({"transaction_id": "T9", "value_date": "2026-10-02", "credit_debit_indicator": "CRDT",
                        "transaction_amount": {"amount": "500000", "currency": "HUF"}, "debtor": {"name": "Munkaadó Kft"},
                        "remittance_information": ["munkabér"]})
    assert be["irany"] == "bevetel" and be["kereskedo_nyers"] == "Munkaadó Kft" and be["kulcs"] == "eb:T9"
    assert eb.normalizal({"status": "PDNG", "booking_date": "2026-10-01", "transaction_amount": {"amount": "5", "currency": "HUF"}}) is None
    assert eb.normalizal({"booking_date": "2026-10-01", "transaction_amount": {"amount": "0", "currency": "HUF"}}) is None
    fx = eb.normalizal({"booking_date": "2026-10-01", "credit_debit_indicator": "DBIT", "transaction_amount": {"amount": "10.96", "currency": "EUR"},
                        "creditor": {"name": "Tractive"}, "remittance_information": []})
    assert "10.96 EUR" in fx["kozlemeny"] and fx["penznem"] == "EUR" and fx["kulcs"] is None


def test_tranzakciok_lapozas(konfig, monkeypatch):
    oldalak = [{"transactions": [{"entry_reference": "A", "booking_date": "2026-10-01", "credit_debit_indicator": "DBIT",
                                  "transaction_amount": {"amount": "100", "currency": "HUF"}, "creditor": {"name": "X"}}],
                "continuation_key": "k2"},
               {"transactions": [{"entry_reference": "B", "booking_date": "2026-10-02", "status": "PDNG",
                                  "transaction_amount": {"amount": "5", "currency": "HUF"}},
                                 {"entry_reference": "C", "booking_date": "2026-10-03", "credit_debit_indicator": "CRDT",
                                  "transaction_amount": {"amount": "7", "currency": "HUF"}, "debtor": {"name": "Y"}}]}]
    hivasok = []
    def hamis(k, m, ut, **kw):
        hivasok.append((ut, kw.get("params")))
        return oldalak[len(hivasok) - 1]
    monkeypatch.setattr(eb, "_kerj", hamis)
    r = eb.tranzakciok(konfig, "uid-1", "2026-10-01")
    assert [t["kulcs"] for t in r["tranzakciok"]] == ["eb:A", "eb:C"] and r["osszes"] == 3 and r["kihagyott"] == 1
    assert hivasok[1][1]["continuation_key"] == "k2" and hivasok[0][0] == "/accounts/uid-1/transactions"


def test_auth_inditas_lejarat_a_bank_maximuma(konfig, monkeypatch):
    kuldott = {}
    def hamis(k, m, ut, **kw):
        if ut == "/aspsps":
            return {"aspsps": [{"name": "OTP Bank", "maximum_consent_validity": 90 * 86400}]}
        kuldott.update(kw["json"])
        return {"url": "https://bank/auth", "authorization_id": "a1"}
    monkeypatch.setattr(eb, "_kerj", hamis)
    r = eb.auth_inditas(konfig, "ferj", napok=180, most=datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert r["napok"] == 90 and r["url"] == "https://bank/auth"
    assert kuldott["access"]["valid_until"].startswith("2026-04-01T")
    assert kuldott["aspsp"] == {"name": "OTP Bank", "country": "HU"} and kuldott["psu_type"] == "personal"
    assert eb.state_ellenoriz(konfig, kuldott["state"]) == "ferj"


def test_session_letrehozas_szamla_uid(konfig, monkeypatch):
    s = eb.state_keszit(konfig, "feleseg")
    monkeypatch.setattr(eb, "_kerj", lambda k, m, ut, **kw: {"session_id": "S1", "access": {"valid_until": "2027-01-01T00:00:00+00:00"},
                        "accounts": [{"uid": "uuid-1", "account_id": {"iban": "HU00"}, "name": "Folyószámla"}]})
    r = eb.session_letrehozas(konfig, "kod", s)
    assert r["szemely"] == "feleseg" and r["session_id"] == "S1" and r["szamlak"][0]["uid"] == "uuid-1" and r["szamlak"][0]["iban"] == "HU00"


def test_kartyas_vasarlas_felismerese_a_kozlemenybol():
    kartya = eb.normalizal({"entry_reference": "K1", "booking_date": "2026-10-12", "credit_debit_indicator": "DBIT",
                            "transaction_amount": {"amount": "750", "currency": "HUF"}, "creditor": {"name": "Inga Kulturkavezo"},
                            "remittance_information": ["2026.10.09 6296949233 Inga Kulturkavezo        -APPLE"]})
    assert kartya["fizetesi_mod"] == "kartya"
    atutalas = eb.normalizal({"entry_reference": "K2", "booking_date": "2026-10-12", "credit_debit_indicator": "DBIT",
                              "transaction_amount": {"amount": "2721", "currency": "HUF"}, "creditor": {"name": "OTP BANK NYRT."},
                              "remittance_information": ["9801804086826482BIZT"]})
    assert atutalas["fizetesi_mod"] == "atutalas"


def test_tranzakciotipus_a_nevben_es_a_megjegyzesben():
    """Az OTP bank_transaction_code leírása mondja meg a tétel fajtáját; a megjegyzés ne csak azonosító legyen."""
    hitel = eb.normalizal({"entry_reference": "H1", "booking_date": "2026-10-12", "credit_debit_indicator": "DBIT",
                           "transaction_amount": {"amount": "22894.0", "currency": "HUF"}, "creditor": {"name": "OTP BANK NYRT."},
                           "bank_transaction_code": {"description": "ÁRUVÁSÁRLÁSI HITEL TÖRL.", "code": "CBDD"},
                           "remittance_information": ["9801704123370946"]})
    assert hitel["kereskedo_nyers"] == "ÁRUVÁSÁRLÁSI HITEL TÖRL., OTP BANK NYRT."
    assert hitel["kozlemeny"] == "ÁRUVÁSÁRLÁSI HITEL TÖRL. | Kedvezményezett: OTP BANK NYRT. | Közlemény: 9801704123370946"
    assert hitel["fizetesi_mod"] == "atutalas"
    utalas = eb.normalizal({"entry_reference": "U1", "booking_date": "2026-10-09", "credit_debit_indicator": "DBIT",
                            "transaction_amount": {"amount": "350000.0", "currency": "HUF"}, "creditor": {"name": "JODIA Kft."},
                            "bank_transaction_code": {"description": "AZONNALI FIZETÉS BANKON BELÜL", "code": "324"},
                            "remittance_information": ["BSZ/00216"]})
    assert utalas["kereskedo_nyers"] == "AZONNALI FIZETÉS BANKON BELÜL, JODIA Kft."
    kartya = eb.normalizal({"entry_reference": "C1", "booking_date": "2026-10-07", "credit_debit_indicator": "DBIT",
                            "transaction_amount": {"amount": "2880.0", "currency": "HUF"}, "creditor": {"name": "Allegro"},
                            "bank_transaction_code": {"description": "VÁSÁRLÁS KÁRTYÁVAL", "code": "764"},
                            "remittance_information": ["2026.10.05 6296949233 Allegro                  -APPLE"]})
    assert kartya["kereskedo_nyers"] == "Allegro" and kartya["fizetesi_mod"] == "kartya"
    assert kartya["kozlemeny"].startswith("VÁSÁRLÁS KÁRTYÁVAL | Kedvezményezett: Allegro | Közlemény: 2026.10.05")
    bevetel = eb.normalizal({"entry_reference": "B1", "booking_date": "2026-10-02", "credit_debit_indicator": "CRDT",
                             "transaction_amount": {"amount": "682317.0", "currency": "HUF"}, "debtor": {"name": "ISOLUTIONS Kft."},
                             "bank_transaction_code": {"description": "NAPKÖZBENI ÁTUTALÁS", "code": "1"},
                             "remittance_information": ["08. havi munkabér"]})
    assert bevetel["kozlemeny"] == "NAPKÖZBENI ÁTUTALÁS | Feladó: ISOLUTIONS Kft. | Közlemény: 08. havi munkabér"


def test_tobb_alkalmazas_state_es_jwt(konfig, tmp_path):
    kulcs2 = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    p2 = tmp_path / "k2.pem"
    p2.write_bytes(kulcs2.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    konfig.alkalmazasok = {"2": {"app_id": "app-456", "kulcs": str(p2)}}
    assert konfig.app("alap") is konfig and konfig.app().app_id == "app-123"
    masik = konfig.app("2")
    assert masik.app_id == "app-456" and masik.api_kulcs == "titok"
    assert jwt.get_unverified_header(eb.jwt_token(masik))["kid"] == "app-456"
    assert jwt.get_unverified_header(eb.jwt_token(konfig))["kid"] == "app-123"
    s = eb.state_keszit(konfig, "hz_x~feleseg", alkalmazas="2")
    assert eb.state_adat(konfig, s)["a"] == "2" and eb.state_ellenoriz(konfig, s) == "hz_x~feleseg"
    assert eb.state_adat(konfig, eb.state_keszit(konfig, "p"))["a"] == "alap"
    with pytest.raises(eb.BankHiba):
        konfig.app("nincs")
