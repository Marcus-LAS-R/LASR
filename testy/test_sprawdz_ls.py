import pytest
import os
import sys
import platform
from qgis.core import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# from skrypty.sprawdz_ls import PrzetworzKlu
# from skrypty.baza_przetworz import Przetworz
# from skrypty import baza_wrapper


sys.setrecursionlimit(100000)

# sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
# from attribute_transfer import AttributeTransfer
# from create_dummy_data import create_dummy_data_polygon_or_line

app = QApplication(sys.argv)
QgsApplication.setPrefixPath("/usr", True)
# qgs = QgsApplication([], False)
QgsApplication.initQgis()

# app = QCoreApplication(sys.argv)
# QgsApplication.setPrefixPath("/usr/share/qgis", True)
# QgsApplication.initQgis()


# @pytest.fixture()
# def w():
    # dzl = QgsVectorLayer('/home/qnox/upul/testy/grabica/test/DZKATwyb.shp',
                         # 'dz',
                         # 'ogr')
    # dzf = [x for x in dzl.getFeatures()]

    # klul = QgsVectorLayer('/home/qnox/upul/testy/grabica/test/LSwyb.shp', 'ls',
                          # 'ogr')
    # lsf = [x for x in klul.getFeatures()]

    # if platform.system() == 'Linux':
        # baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
    # else:
        # baza = r'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'

    # b = baza_wrapper.Baza(baza)
    # b.polacz()
    # u = b.uzytki()
    # w = b.wlasnosci()
    # p = Przetworz()
    # p.dodaj_uzytki(u)
    # p.dodaj_wlasnosci(w)
    # p.przetworz_uzytkowanie()
    # p.przetworz_dzialki()

    # pp = PrzetworzKlu(dzf, lsf, p)
    # return pp


# @pytest.mark.parametrize('baza, dzf, lsf', [dzf, lsf, p])
def test_poprawnosc_sprawdzenia():
    dzl = QgsVectorLayer('/home/qnox/upul/testy/grabica/test/DZKATwyb.shp',
                         'dz',
                         'ogr')
    a = 1  # w.is_valid()
    assert dzl.isValid() is True

def test_liczby_poly():
    dzl = QgsVectorLayer('/home/qnox/upul/testy/grabica/test/DZKATwyb.shp',
                         'dz',
                         'ogr')
    assert dzl.featureCount() > 10
