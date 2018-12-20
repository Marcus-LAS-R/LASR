# import skrypty.sprawdz_dzkat as spr
from skrypty.baza_wrapper import Baza
# from collections import Counter
import pytest
import platform
from collections import Counter

if platform.system() == 'Linux':
    baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
else:
    baza = r'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'

b = Baza(baza)
b_lacz = b.polacz()


@pytest.mark.parametrize('baza', [b])
def test_polaczenia(baza):
    # a = spr.AnalizujDzKat(False, False)
    assert b_lacz


@pytest.mark.parametrize('baza', [b])
def test_pobierz_uzytki(baza):
    u = b.uzytki()
    print(len(u))
    assert len(u) > 3


@pytest.mark.parametrize('baza', [b])
def test_poprawnosc_uzytkow(baza):
    u = b.uzytki()
    assert u[0][9][0] in ['L', 'R', 'P', 'Ł', 'N', 'B', 'W', 'S']


@pytest.mark.parametrize('baza', [b])
def test_pobierz_wlasnosci(baza):
    w = b.wlasnosci()
    print(len(w))
    assert len(w) > 3


@pytest.mark.parametrize('baza', [b])
def test_pobierz_pow(baza):
    p = b.pobierz_pow_oprac()
    assert len(p) > 0
    assert len(p[0]) == 6
    assert len(p[0][0]) == 3
    assert len(p[0][1]) == 4


@pytest.mark.parametrize('baza', [b])
def test_pobierz_wydz(baza):
    p = b.pobierz_wydzielenia()
    assert len(p) > 0
    assert Counter(p.values()).most_common(1)[0][1] == 1

