import pytest
import platform

from skrypty.baza_przetworz import Przetworz
from skrypty import baza_wrapper


@pytest.fixture()
def wczytaj():
    if platform.system() == 'Linux':
        baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
    else:
        baza = r'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'

    b = baza_wrapper.Baza(baza)
    b.polacz()
    p = Przetworz()
    p.u = b.uzytki()
    p.w = b.wlasnosci()
    # p.dodaj_uzytki(u)
    # p.dodaj_wlasnosci(w)
    # p.przetworz_uzytkowanie()
    # p.przetworz_dzialki()

    return p


def test_instancji(wczytaj):
    assert isinstance(wczytaj, Przetworz)


def test_dodania_uztykow_do_obiektu(wczytaj):
    wczytaj.dodaj_uzytki(wczytaj.u)
    assert len(wczytaj.u) == len(wczytaj.baza_uzytki)


def test_dodania_wlasnosci_do_obiektu(wczytaj):
    wczytaj.dodaj_wlasnosci(wczytaj.w)
    assert len(wczytaj.w) == len(wczytaj.baza_wlasnosci)


def test_sprawdzenia_ilosci_dzkat(wczytaj):
    suma = len(wczytaj.dz_of) + len(wczytaj.dz_op) + len(wczytaj.dz_opif)
    assert suma == len(list(wczytaj.dzialki.keys()))


def test_sprawdzenia_wlasnosci(wczytaj):
    wczytaj.dodaj_uzytki(wczytaj.u)
    wczytaj.dodaj_wlasnosci(wczytaj.w)
    wczytaj.przetworz_uzytkowanie()
    wczytaj.przetworz_dzialki()
    kody = []
    for w in wczytaj.sl_kody_wlasciceli_na_dzialce.values():
        kody += w

    assert set(kody).issubset(set(['OP', 'OF']))
