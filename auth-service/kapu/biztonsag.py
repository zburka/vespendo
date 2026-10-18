import hashlib
import re
import secrets
import time

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

_ph = PasswordHasher()
EMAIL_MINTA = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,24}$")


class HibaKod(Exception):
    """Felhasználónak megjeleníthető hiba, a hozzá tartozó HTTP kóddal."""

    def __init__(self, uzenet: str, kod: int = 400):
        super().__init__(uzenet)
        self.uzenet = uzenet
        self.kod = kod


def jelszo_hash(jelszo: str) -> str:
    return _ph.hash(jelszo)


def jelszo_helyes(hash_: str, jelszo: str) -> bool:
    try:
        return _ph.verify(hash_, jelszo)
    except (VerifyMismatchError, InvalidHashError):
        return False


def jelszo_szabaly(jelszo: str, email: str = "") -> None:
    if len(jelszo) < 10:
        raise HibaKod("A jelszó legalább 10 karakter legyen.")
    if len(jelszo) > 200:
        raise HibaKod("A jelszó túl hosszú.")
    if email and jelszo.lower() == email.lower():
        raise HibaKod("A jelszó ne egyezzen az e-mail címmel.")
    if len(set(jelszo)) < 4:
        raise HibaKod("A jelszó túl egyszerű.")


def email_rendbe(email: str) -> str:
    e = (email or "").strip().lower()
    if not EMAIL_MINTA.match(e):
        raise HibaKod("Érvénytelen e-mail cím.")
    return e


def uj_token(elotag: str = "") -> tuple[str, str]:
    """(token, sha256 kivonat): csak a kivonat kerül az adatbázisba."""
    t = elotag + secrets.token_urlsafe(32)
    return t, hash_token(t)


def hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def meghivokod() -> str:
    abc = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # félreérthető karakterek nélkül
    return "".join(secrets.choice(abc) for _ in range(8))


def access_token(titok: str, felhasznalo_id: int, haztartas_id: str, ttl: int, most: float | None = None) -> str:
    most = int(most or time.time())
    return jwt.encode({"sub": str(felhasznalo_id), "hz": haztartas_id, "typ": "access", "iat": most, "exp": most + ttl},
                      titok, algorithm="HS256")


def access_dekod(titok: str, token: str) -> dict:
    try:
        d = jwt.decode(token, titok, algorithms=["HS256"], options={"require": ["exp", "sub", "typ"]})
    except jwt.ExpiredSignatureError as e:
        raise HibaKod("A munkamenet lejárt.", 401) from e
    except jwt.PyJWTError as e:
        raise HibaKod("Érvénytelen belépés.", 401) from e
    if d.get("typ") != "access":
        raise HibaKod("Érvénytelen belépés.", 401)
    return d
