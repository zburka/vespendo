import io
from datetime import date

import pytest

from bankparse import ParseHiba, elemez


def _kulcsok(eredmeny):
    return [(t["datum"], t["osszeg"], t["irany"]) for t in eredmeny["tranzakciok"]]


def test_otp_szeru_csv_windows1250():
    csv = (
        "Könyvelés dátuma;Partner neve;Összeg;Közlemény\r\n"
        "2026.10.16.;LIDL BP KEREPESI;-12 000,50;Vásárlás kártyával\r\n"
        "2026.10.15.;Munkabér Kft.;520.000,00;Fizetés őszi\r\n"
    )
    adat = csv.encode("cp1250")
    r = elemez(adat, "export.csv")
    assert _kulcsok(r) == [("2026-10-16", 12000.5, "kiadas"), ("2026-10-15", 520000.0, "bevetel")]
    assert r["tranzakciok"][0]["kereskedo_nyers"] == "LIDL BP KEREPESI"
    assert r["tranzakciok"][1]["kozlemeny"] == "Fizetés őszi"
    assert r["megbizhatosag"] == "magas"


def test_terheles_jovairas_kulon_oszlop_angol():
    csv = (
        'Date,Description,Debit,Credit,Balance\n'
        '16/10/2026,"Tesco, London",45.10,,954.90\n'
        '17/10/2026,Salary,,"1,500.00","2,454.90"\n'
        '18/10/2026,Netflix,12.99,,2441.91\n'
    )
    r = elemez(csv.encode(), "x.csv")
    assert _kulcsok(r) == [
        ("2026-10-16", 45.1, "kiadas"),
        ("2026-10-17", 1500.0, "bevetel"),
        ("2026-10-18", 12.99, "kiadas"),
    ]


def test_xlsx_elojel_nelkuli_osszeg_egyenlegbol():
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["C1", "C2", "C3", "C4"])
    ws.append([date(2026, 10, 1), "Fizetés", 500000, 600000])
    ws.append([date(2026, 10, 2), "SPAR", 20000, 580000])
    ws.append([date(2026, 10, 3), "MVM", 30000, 550000])
    ws.append([date(2026, 10, 4), "Jutalom", 10000, 560000])
    buf = io.BytesIO()
    wb.save(buf)
    r = elemez(buf.getvalue(), "kivonat.xlsx")
    assert _kulcsok(r)[1:] == [
        ("2026-10-02", 20000.0, "kiadas"),
        ("2026-10-03", 30000.0, "kiadas"),
        ("2026-10-04", 10000.0, "bevetel"),
    ]
    assert r["megbizhatosag"] == "magas"


def test_legujabb_elol_sorrend_egyenleggel():
    csv = (
        "Datum;Text;X;Y\n"
        "2026-10-04;Jutalom;10000;560000\n"
        "2026-10-03;MVM;30000;550000\n"
        "2026-10-02;SPAR;20000;580000\n"
        "2026-10-01;Fizetes;500000;600000\n"
    )
    r = elemez(csv.encode(), "x.csv")
    assert [t["irany"] for t in r["tranzakciok"]][:3] == ["bevetel", "kiadas", "kiadas"]
    assert r["figyelmeztetesek"]


def _pdf_tablazat(sorok):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

    buf = io.BytesIO()
    t = Table(sorok)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    SimpleDocTemplate(buf, pagesize=A4).build([t])
    return buf.getvalue()


def _pdf_szoveg(sorok):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    y = 800
    for s in sorok:
        c.drawString(40, y, s)
        y -= 16
    c.save()
    return buf.getvalue()


def test_pdf_tablazatos():
    pdf = _pdf_tablazat(
        [
            ["Dátum", "Megnevezés", "Összeg", "Egyenleg"],
            ["2026.10.01.", "SPAR", "-20 000", "480 000"],
            ["2026.10.02.", "MVM", "-30 000", "450 000"],
            ["2026.10.03.", "Fizetés", "100 000", "550 000"],
        ]
    )
    r = elemez(pdf, "kivonat.pdf")
    assert _kulcsok(r) == [
        ("2026-10-01", 20000.0, "kiadas"),
        ("2026-10-02", 30000.0, "kiadas"),
        ("2026-10-03", 100000.0, "bevetel"),
    ]


def test_pdf_szoveges_sorok_tobbsoros_leirassal():
    pdf = _pdf_szoveg(
        [
            "Szamlakivonat 2026. oktober",
            "2026.10.01.  Kartyas vasarlas LIDL BUDAPEST    20 000    480 000",
            "   kartyaszam 1234",
            "2026.10.02.  Atutalas MVM Zrt. rezsi    30 000    450 000",
            "2026.10.03.  Beerkezo utalas Munkaado Kft.    100 000    550 000",
        ]
    )
    r = elemez(pdf, "kivonat.pdf")
    assert _kulcsok(r)[1:] == [("2026-10-02", 30000.0, "kiadas"), ("2026-10-03", 100000.0, "bevetel")]
    assert r["figyelmeztetesek"]  # a legrégebbi tétel iránya becsült
    assert "LIDL" in r["tranzakciok"][0]["kereskedo_nyers"]
    assert "kartyaszam 1234" in r["tranzakciok"][0]["kereskedo_nyers"]


def test_csak_pozitiv_osszeg_figyelmeztet():
    csv = "Datum;Nev;Osszeg\n2026-10-01;A;1000\n2026-10-02;B;2000\n2026-10-03;C;3000\n"
    r = elemez(csv.encode(), "x.csv")
    assert r["megbizhatosag"] == "alacsony"
    assert r["figyelmeztetesek"]


@pytest.mark.parametrize("tartalom", [b"", b"semmi;ertelmes\nszoveg;itt\n"])
def test_ertelmetlen_fajl_hiba(tartalom):
    with pytest.raises(ParseHiba):
        elemez(tartalom, "x.csv")


def test_xls_nem_tamogatott():
    with pytest.raises(ParseHiba):
        elemez(b"\xd0\xcf\x11\xe0", "regi.xls")


def test_otp_szeru_pdf_ketjegyu_datum_nyito_zaro_egyenleg():
    """OTP-szerű elrendezés: YY.MM.DD dátumok, két dátum soronként, nyitó/záró egyenleg sor,
    oldalfejléc az új oldal tetején, elromlott betűkódolás."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    def sor(c, y, d1, d2, leiras, osszeg):
        c.drawString(40, y, d1)
        if d2:
            c.drawString(110, y, d2)
        c.drawString(180 if d2 else 110, y, leiras)
        c.drawRightString(560, y, osszeg)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(40, 800, "SZAMLAKIVONAT 1.LAP/2 LAP")
    sor(c, 770, "26.09.02", None, "NYITO EGYENLEG", "10.000")
    sor(c, 754, "26.09.02", "26.09.02", "VASARLAS, 1234567890, Tranzakcio: 26.09.01, SPAR", "-2.790")
    sor(c, 738, "26.09.04", "26.09.04", "AZONNALI FIZETES, Munkaado Kft", "500")
    c.showPage()
    c.drawString(40, 800, "SZAMLASZAM: 12345678 2.LAP/2 LAP")
    c.drawString(40, 784, "FORGALMAK")
    sor(c, 760, "26.09.14", "26.09.14", "VASARLAS KARTYAVAL, Tßp-termÚny bolt", "-1.000")
    sor(c, 744, "26.10.01", None, "ZARO EGYENLEG", "6.710")
    c.drawString(40, 700, "Lablec: tajekoztato szoveg")
    c.save()

    r = elemez(buf.getvalue(), "kivonat.pdf")
    assert _kulcsok(r) == [
        ("2026-09-02", 2790.0, "kiadas"),
        ("2026-09-04", 500.0, "bevetel"),
        ("2026-09-14", 1000.0, "kiadas"),
    ]
    assert r["egyenleg_ellenorzes"]["egyezik"] is True
    assert r["megbizhatosag"] == "magas"
    assert "SPAR" in r["tranzakciok"][0]["kereskedo_nyers"]
    assert "1234567890" not in r["tranzakciok"][0]["kereskedo_nyers"]  # azonosító-zaj kiszűrve
    assert "Táp-termény bolt" in r["tranzakciok"][2]["kereskedo_nyers"]  # betűkódolás javítva
    assert "SZAMLASZAM" not in r["tranzakciok"][1]["kozlemeny"] + r["tranzakciok"][1]["kereskedo_nyers"]


def test_egyenleg_elteres_figyelmeztet():
    csv = "Datum;Nev;Osszeg\n26.09.02;NYITO EGYENLEG;1000\n26.09.03;A;-100\n26.09.04;B;-200\n26.09.05;ZARO EGYENLEG;500\n"
    r = elemez(csv.encode(), "x.csv")
    assert r["egyenleg_ellenorzes"]["egyezik"] is False
    assert any("nem egyezik" in f for f in r["figyelmeztetesek"])
    assert r["megbizhatosag"] != "magas"


def test_devizas_vasarlas_leiras_vegi_toredek_nem_osszeg():
    """'3,560EUR 0,' a leírás része: a végén álló '0,' nem lehet második szám (az összeg a másik oszlopba csúszna)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    def sor(c, y, d, leiras, deviza, osszeg):
        c.drawString(40, y, d)
        c.drawString(110, y, d)
        c.drawString(180, y, leiras)
        if deviza:
            c.drawString(330, y, deviza)
        c.drawRightString(560, y, osszeg)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.drawString(40, 800, "FORGALMAK")
    c.drawString(40, 785, "26.02.01")
    c.drawString(110, 785, "NYITO EGYENLEG")
    c.drawRightString(560, 785, "10.000")
    sor(c, 770, "26.02.02", "VASARLAS, SPAR", None, "-2.000")
    sor(c, 754, "26.02.03", "VASARLAS, APPLE.COM/BILL,", "3,560EUR 0,", "-1.290")
    sor(c, 738, "26.02.04", "VASARLAS, ALDI", None, "-500")
    c.drawString(40, 722, "26.02.28")
    c.drawString(110, 722, "ZARO EGYENLEG")
    c.drawRightString(560, 722, "6.210")
    c.save()

    r = elemez(buf.getvalue(), "kivonat.pdf")
    assert _kulcsok(r) == [
        ("2026-02-02", 2000.0, "kiadas"),
        ("2026-02-03", 1290.0, "kiadas"),
        ("2026-02-04", 500.0, "kiadas"),
    ]
    assert r["kihagyott"] == 0
    assert r["egyenleg_ellenorzes"]["egyezik"] is True
