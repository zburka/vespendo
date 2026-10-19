"""E-mail küldés SMTP-n (az ötlet-értesítésekhez). Hibája sosem akadályozza a kérést: az ötlet előbb tárolódik."""
import logging
import smtplib
from email.message import EmailMessage

from .beallitasok import Beallitasok

naplo = logging.getLogger("uvicorn.error")


def beallitva(cfg: Beallitasok) -> bool:
    return bool(cfg.smtp_host and cfg.smtp_felado and cfg.otlet_cim)


def kuld(cfg: Beallitasok, targy: str, szoveg: str, valasz_cim: str = "") -> bool:
    """True, ha elment. Fejléc-injekció ellen a tárgyból és a válaszcímből kivesszük az újsorokat."""
    if not beallitva(cfg):
        naplo.info("ötlet: nincs SMTP beállítva, csak tárolás")
        return False
    m = EmailMessage()
    m["Subject"] = targy.replace("\r", " ").replace("\n", " ")[:150]
    m["From"] = cfg.smtp_felado
    m["To"] = cfg.otlet_cim
    if valasz_cim and "\n" not in valasz_cim and "\r" not in valasz_cim:
        m["Reply-To"] = valasz_cim
    m.set_content(szoveg)
    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=20) as s:
            s.starttls()
            if cfg.smtp_felhasznalo:
                s.login(cfg.smtp_felhasznalo, cfg.smtp_jelszo)
            s.send_message(m)
        return True
    except (OSError, smtplib.SMTPException) as e:
        naplo.warning("ötlet: az e-mail küldése nem sikerült: %s", e.__class__.__name__)
        return False
