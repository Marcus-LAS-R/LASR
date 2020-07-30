import os
import pytest

from skrypty.baza_napraw_stor_spec import NaprawFStorSpec


@pytest.fixture()
def baz():
    sc = '/home/qnox/temp/framopol/baza.sqlite'


def test_pobierz_z_bazy():
    sc = '/home/qnox/temp/framopol/baza.sqlite'
    np = NaprawFStorSpec(True)
    np.baza.baza = sc
    polacz = np.pobierz_z_bazy()
    assert polacz
    assert len(np.raw) > 9000


def test_zbuduj_strukture():
    sc = '/home/qnox/temp/framopol/baza.sqlite'
    np = NaprawFStorSpec(True)
    np.baza.baza = sc
    np.pobierz_z_bazy()
    np.zbuduj_strukture()
    assert len(np.sl) > 0


def test_sortuj_strukture():
    sc = '/home/qnox/temp/framopol/baza.sqlite'
    np = NaprawFStorSpec(True)
    np.baza.baza = sc
    np.pobierz_z_bazy()
    np.zbuduj_strukture()
    np.popraw()
    assert len(np.sl) > 0
    assert len(np.uwagi) == 3

def test_dopisu_do_bazy():
    sc = '/home/qnox/temp/framopol/baza.sqlite'
    np = NaprawFStorSpec(True)
    np.baza.baza = sc
    np.pobierz_z_bazy()
    np.zbuduj_strukture()
    np.popraw()
    np.dopisz_poprawki()
    np.raport()
    assert len(np.uwagi) / 2 == 3
    assert np.wpisanych == 580
