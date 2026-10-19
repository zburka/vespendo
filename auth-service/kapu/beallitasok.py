import json
import os
from dataclasses import dataclass, field


@dataclass
class Beallitasok:
    """A kapu beállításai (környezeti változókból)."""

    db_utvonal: str = "/data/auth.db"
    jwt_titok: str = ""
    # új háztartás létrehozásához kell (üres = bárki létrehozhat); meghívókóddal csatlakozáshoz nem kell
    regisztracios_kod: str = ""
    n8n_url: str = "http://n8n:5678"
    n8n_ut_elotag: str = ""          # pl. 'h/' az új, háztartás-szűrő workflow-k útvonalához a cutover előtt
    n8n_belso_kulcs: str = ""        # az n8n webhookok X-App-Key fejléce: csak a kapu ismeri
    baserow_url: str = ""
    baserow_token: str = ""
    baserow_tablak: dict = field(default_factory=dict)
    # a bemutató (demó) fiók e-mail címe: ha meg van adva, a belépőképernyőn jelszó nélkül megnyitható (a fiókot `demo=1` jelöli)
    demo_email: str = ""
    # ötletek e-mailes értesítése (SMTP); ha nincs megadva, az ötlet csak a Baserow-ba kerül
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_felhasznalo: str = ""
    smtp_jelszo: str = ""
    smtp_felado: str = ""
    otlet_cim: str = "zoli@burka.hu"
    access_ttl_mp: int = 15 * 60
    frissito_ttl_nap: int = 30
    max_torzs_bajt: int = 25 * 1024 * 1024

    @classmethod
    def kornyezetbol(cls) -> "Beallitasok":
        e = os.environ.get
        return cls(
            db_utvonal=e("AUTH_DB", "/data/auth.db"),
            jwt_titok=e("AUTH_JWT_TITOK", ""),
            regisztracios_kod=e("REGISZTRACIOS_KOD", ""),
            demo_email=e("DEMO_EMAIL", ""),
            smtp_host=e("SMTP_HOST", ""),
            smtp_port=int(e("SMTP_PORT", "587") or 587),
            smtp_felhasznalo=e("SMTP_FELHASZNALO", ""),
            smtp_jelszo=e("SMTP_JELSZO", ""),
            smtp_felado=e("SMTP_FELADO", ""),
            otlet_cim=e("OTLET_CIM", "zoli@burka.hu"),
            n8n_url=e("N8N_URL", "http://n8n:5678"),
            n8n_ut_elotag=e("N8N_UT_ELOTAG", ""),
            n8n_belso_kulcs=e("N8N_BELSO_KULCS", ""),
            baserow_url=e("BASEROW_URL", ""),
            baserow_token=e("BASEROW_TOKEN", ""),
            baserow_tablak=json.loads(e("BASEROW_TABLAK", "{}") or "{}"),
        )

    def ellenoriz(self):
        if len(self.jwt_titok) < 32:
            raise RuntimeError("AUTH_JWT_TITOK legalább 32 karakter legyen")
