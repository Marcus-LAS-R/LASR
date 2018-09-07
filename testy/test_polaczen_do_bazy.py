# import skrypty.sprawdz_dzkat as spr
from ..skrypty.baza_wrapper import Baza
from collections import Counter
import pytest
import platform

if platform.system() == 'Linux':
    baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
else:
    baza = 'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'

b = Baza(baza)
b_lacz = b.polacz()

@pytest.mark.parametrize('baza', [b])
def test_polaczenia(baza):
    # a = spr.AnalizujDzKat(False, False)
    assert b_lacz == True

@pytest.mark.parametrize('baza', [b])
def test_pobierz_uzytki(baza):
    u = b.uzytki()
    print(len(u))
    assert len(u) > 3

@pytest.mark.parametrize('baza', [b])
def test_poprawnosc_uzytkow(baza):
    u = b.uzytki()
    print(u[0])
    assert u[0][9][0] in ['L', 'R', 'P', 'Ł', 'N', 'B', 'W', 'S']

@pytest.mark.parametrize('baza', [b])
def test_pobierz_wlasnosci(baza):
    w = b.wlasnosci()
    print(len(w))
    assert len(w) > 3

