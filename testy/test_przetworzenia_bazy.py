import pytest
import platform

from ..skrypty.baza_przetworz import Przetworz
from ..skrypty import baza_wrapper

if platform.system() == 'Linux':
    baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
else:
    baza = r'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'

b = baza_wrapper.Baza(baza)
b_lacz = b.polacz()
u = b.uzytki()
w = b.wlasnosci()
p = Przetworz()
p.dodaj_uzytki(u)
# p.dodaj_wlasnosci(w)
# p.przetworz_uzytkowanie()
# p.przetworz_dzialki()


@pytest.mark.parametrize('p', [p])
def test_instancji(p):
    assert isinstance(p, Przetworz)


@pytest.mark.parametrize('p, u', [p, u])
def test_dodania_uztykow_do_obiektu(p, u):
    assert isinstance(p.baza_uzytki, list)


# @pytest.mark.parametrize('p, u', [p, w])
# def test_dodania_wlasnosci_do_obiektu(p, u):
    # u_przed = len(p.baza_wlasnosci)
    # p.dodaj_uzytki(u)
    # u_po = len(p.baza_wlasnosci)
    # assert u_przed == u_po


# @pytest.mark.parametrize('p', [p])
# def test_przetworz_uztyki(p):
    # pass
