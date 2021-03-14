import os
import pytest
import platform

from skrypty.baza_wrapper import Baza
from skrypty.baza_polacz import Laczenie, PolaczBazy


@pytest.fixture()
def bazy_adr():
    b0 = '/home/qnox/temp/dane_laczenie_baz/baza_rr.sqlite'
    b1 = '/home/qnox/temp/dane_laczenie_baz/baza_resztat.sqlite'
    return [b0, b1]


@pytest.fixture()
def bazy():
    b0 = '/home/qnox/temp/dane_laczenie_baz/baza_rr.sqlite'
    b1 = '/home/qnox/temp/dane_laczenie_baz/baza_resztat.sqlite'

    l = PolaczBazy(False)
    l.lista = [b0, b1]
    l.stworz_docelowa()
    kat, plik = os.path.split(b0)
    plikn = 'baza_polaczona_' + l.czas + '.sqlite'
    baza_lacz = os.path.join(kat, plikn)

    b0 = Baza(baza_lacz)
    b1 = Baza(b1)
    b0.polacz()
    b1.polacz()
    return [b0, b1]


def test_kopiowania_bazy_do_laczenia(bazy_adr):
    l = PolaczBazy(False)
    l.lista = bazy_adr
    l.stworz_docelowa()
    kat, plik = os.path.split(bazy_adr[0])
    plikn = 'baza_polaczona_' + l.czas + '.sqlite'
    assert os.path.isfile(os.path.join(kat, plikn))


def test_sprawdzenie_czy_pokrywaja_sie_wydzielenia_f_arodes(bazy):
    spr = Laczenie(*bazy)
    assert spr.zdublowany_f_arodes()


def test_pobierz_najwieksze_f_arodes(bazy):
    spr = Laczenie(*bazy)
    spr.p_f_max()
    assert spr.maxint == 442 and spr.maxspecstor == 1355


def test_sprawdz_powtarzajace_sie_obr_lesnictwa_w_bazach(bazy):
    spr = Laczenie(*bazy)
    spr.p_f_max()
    spr.p_f_arodes()
    spr.p_tabele()
    assert len(spr.l_wpisanych_innych) > 0


def test_sprawdz_pobranie_info_z_bazy(bazy):
    spr = Laczenie(*bazy)
    spr.p_f_max()
    spr.p_f_arodes()
    spr.p_tabele()
    assert len(spr.tab[0]) > 0 and len(spr.tab[1]) > 0


def test_sprawdz_wpisanie_danych_do_bazy(bazy):
    spr = Laczenie(*bazy)
    spr.p_f_max()
    maxint = spr.maxint
    spr.p_f_arodes()
    spr.p_tabele()
    spr.d_tabele()
    spr.p_f_max()
    maxintn = spr.maxint
    assert maxintn > maxint
