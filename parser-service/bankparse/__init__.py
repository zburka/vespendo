from .extract import ParseHiba, kinyer
from .normalize import normalizal

__all__ = ["ParseHiba", "kinyer", "normalizal", "elemez"]


def elemez(adat: bytes, fajlnev: str) -> dict:
    """Bármilyen banki kivonat (CSV / XLSX / PDF) -> egységes tranzakciólista. Nem használ AI-t."""
    return normalizal(kinyer(adat, fajlnev))
