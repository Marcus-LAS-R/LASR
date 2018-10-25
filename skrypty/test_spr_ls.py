import pytest
import platform
from qgis.core import *
import qgis.utils
import sys
from qgis.gui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui

from sprawdz_ls import PrzetworzKlu
from baza_przetworz import Przetworz
import baza_wrapper

sys.setrecursionlimit(100000)

QgsApplication.setPrefixPath('/usr/', True)
qgs = QgsApplication([], False)
qgs.initQgis()

@pytest.fixture()
def w():

    dzl = QgsVectorLayer('/home/qnox/upul/testy/grabica/test/DZKATwyb.shp',
                         'dz',
                         'ogr')
    dzf = [x for x in dzl.getFeatures()]

    klul = QgsVectorLayer('/home/qnox/upul/testy/grabica/test/LSwyb.shp', 'ls',
                          'ogr')
    lsf = [x for x in klul.getFeatures()]

    if platform.system() == 'Linux':
        baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
    else:
        baza = r'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'

    b = baza_wrapper.Baza(baza)
    b.polacz()
    u = b.uzytki()
    w = b.wlasnosci()
    p = Przetworz()
    p.dodaj_uzytki(u)
    p.dodaj_wlasnosci(w)
    p.przetworz_uzytkowanie()
    p.przetworz_dzialki()

    pp = PrzetworzKlu(dzf, lsf, p)
    return pp


# @pytest.mark.parametrize('baza, dzf, lsf', [dzf, lsf, p])
def test_poprawnosc_sprawdzenia(w):
    a = 1  # w.is_valid()
    assert a == 2
