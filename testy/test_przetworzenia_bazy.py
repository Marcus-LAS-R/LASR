import pytest
import platform

from skrypty.baza_przetworz import Przetworz
from skrypty import baza_wrapper


@pytest.fixture()
def polacz():
    if platform.system() == 'Linux':
        baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
    else:
        baza = r'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'

    b = baza_wrapper.Baza(baza)
    wyn = b.polacz()
    b.zamknij()
    return wyn


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
    p.dodaj_uzytki(b.uzytki())
    p.dodaj_wlasnosci(b.wlasnosci())
    b.zamknij()
    p.przetworz_dzialki()
    p.przetworz_wszystkie_ls()
    p.przetworz_uzytkowanie()
    # p.przetworz_uzytkowanie()

    return p


def test_polaczenia_z_baza(polacz):
    assert polacz is True


def test_instancji(wczytaj):
    assert isinstance(wczytaj, Przetworz)


def test_dodania_uztykow_do_obiektu(wczytaj):
    w = wczytaj
    assert len(w.baza_uzytki) == len(w.u)


def test_dodania_wlasnosci_do_obiektu(wczytaj):
    w = wczytaj
    assert len(w.baza_wlasnosci) == len(w.w)


def test_sprawdzenia_ilosci_dzkat(wczytaj):
    suma = len(wczytaj.dz_of) + len(wczytaj.dz_op) + len(wczytaj.dz_opif)
    assert suma == len(list(wczytaj.dzialki.keys()))


def test_sprawdzenia_kodow_wlasnosci(wczytaj):
    kody = []
    for w in wczytaj.sl_kody_wlasciceli_na_dzialce.values():
        kody += w

    assert set(kody).issubset(set(['OP', 'OF']))


def test_sprawdzenia_kodow_w_op(wczytaj):
    assert len(wczytaj.dz_op[0].split('.')[0]) == 7


def test_przetworzenia_listy_lsow(wczytaj):
    assert len(wczytaj.ls) > 2


def test_przetworzenia_podwojnych_ls(wczytaj):
    assert len(wczytaj.ls_podwojne) >= 0


def test_przetworzenia_ile_uzytkow_na_dz(wczytaj):
    assert len(wczytaj.sl_ile_uzytkow_na_dzialce.keys()) > 0


def test_przetworzenia_ile_ls_na_dz(wczytaj):
    assert len(wczytaj.sl_ls_na_dz.keys()) > 0


def test_przetworzenia_l_pow_dla_ls(wczytaj):
    assert len(wczytaj.sl_pow_ls_dzkat.keys()) > 0
