# import skrypty.sprawdz_dzkat as spr
from ..skrypty.baza_wrapper import Baza
import pytest


def test_polaczenia():
    # a = spr.AnalizujDzKat(False, False)
    baza = 'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'
    b = Baza(baza)
    b_lacz = b.polacz()
    assert b_lacz == True

def test_pobierz_uzytki():
    baza = 'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'
    b = Baza(baza)
    b.polacz()
    u = b.uzytki()
    print(len(u))
    assert len(u) > 3

def test_pobierz_wlasnosci():
    baza = 'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'
    b = Baza(baza)
    b.polacz()
    u = b.wlasnosci()
    print(len(u))
    assert len(u) > 3

