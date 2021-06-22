import pytest
from ..skrypty.baza_wrapper import Baza
from ..skrypty.zabiegi.wydzielenie import Wydzielenie


@pytest.fixture()
def baza():
    baza = 'testy/baza_zabiegi.sqlite'
    bb = Baza(baza)
    bb.polacz()
    return bb


@pytest.fixture()
def baza_pusta():
    baza = 'testy/baza_zabiegi_pusta.sqlite'
    bb = Baza(baza)
    bb.polacz()
    return bb


def test_wczytania_wydz(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(25)
    wyn = baza.pobierz_do_zab(25)
    assert w.odczytaj_dane_z_bazy(wyn) is True
    assert w.reb == 'IB'
    assert w.wiekReb == 120
    assert w.zwarcie == 'PRZ'
    assert w.ile_dzkat == 8


@pytest.mark.parametrize("inp,out", [
    ('BRZ', 'BRZ'), ('SO.L', 'SO'), ('KL.Jw', 'DB'), ('KSZ', 'BRZ')])
def test_generalizacji_gat(inp, out):
    w = Wydzielenie()
    w.przygotuj_strukture(1)
    w.gat_gl = inp
    assert w._zgeneralizuj_gatunek() == out


@pytest.mark.parametrize("inp,out", [
    (['DB', 220], 101), (['DB', 20], 41), (['DB', 310], 101), ])
def test_klasy_wieku(inp, out):
    w = Wydzielenie()
    w.przygotuj_strukture(1)
    w.gat_gl_wiek = inp[1]
    w._ustaw_klase_wieku(inp[0])
    assert w._ustaw_klase_wieku(inp[0]) == out


def test_oblicz_ciecie(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(87)
    wyn = baza.pobierz_do_zab(87)
    w.odczytaj_dane_z_bazy(wyn)
    ww = w._oblicz_ciecie('TW')
    assert w.zwarcie == 'PEŁ'
    assert ww == [15, 10]
