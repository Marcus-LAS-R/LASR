import pytest
import sys
from qgis.core import *  # noqa
from PyQt5.QtWidgets import *  # noqa
from PyQt5.QtCore import *  # noqa
from PyQt5.QtGui import *  # noqa

from skrypty.sprawdz_ls import SprawdzMikro, AnalizujKlus, PobierzDane
# from skrypty.baza_przetworz import Przetworz
# from skrypty import baza_wrapper

sys.setrecursionlimit(100000)

# sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
# from attribute_transfer import AttributeTransfer
# from create_dummy_data import create_dummy_data_polygon_or_line

app = QApplication(sys.argv)  # noqa
QgsApplication.setPrefixPath("/usr", True)  # noqa
# qgs = QgsApplication([], False)
QgsApplication.initQgis()  # noqa


@pytest.fixture()
def przetwarzanie_wejsciowe():
    dzl = QgsVectorLayer('/home/qnox/upul/testy/grabica/shp/DZKAT.shp',
                         'dz',
                         'ogr')
    lsl = QgsVectorLayer('/home/qnox/upul/testy/grabica/shp/KLU.shp',
                         'klu',
                         'ogr')
    iface = 1

    a = AnalizujKlus(iface, lsl, dzl)
    a.dd = PobierzDane(k=lsl, d=dzl)
    # a.dd.ui.lineEdit_klu.setText('/home/qnox/upul/testy/shp/KLU.shp')
    # a.dd.ui.lineEdit_dzkat.setText('/home/qnox/upul/testy/shp/DZKAT.shp')
    a.dd.ui.lineEdit_bazy.setText('/home/qnox/upul/testy/grabica')
    a.dd.ui.comboBox_ident.setCurrentIndex(2)
    a.dd.ui.comboBox_au.setCurrentIndex(1)
    a.dd.ui.comboBox_sq.setCurrentIndex(2)

    a.przetworz()

    return a


@pytest.fixture()
def mikro():
    pass


def test_aKlu_pobrania_danych_od_uzytk(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe

    assert a.dd.ui.lineEdit_klu.text() == \
        '/home/qnox/upul/testy/grabica/shp/KLU.shp'
    assert a.dd.ui.lineEdit_dzkat.text() == \
        '/home/qnox/upul/testy/grabica/shp/DZKAT.shp'
    assert a.dd.ui.lineEdit_bazy.text() == \
        '/home/qnox/upul/testy/grabica'
    assert a.dd.ui.comboBox_ident.isEnabled() is True
    assert a.dd.ui.comboBox_ident.currentIndex() == 2
    assert a.dd.ui.comboBox_au.isEnabled() is True
    assert a.dd.ui.comboBox_sq.isEnabled() is True
    assert a.dd.ui.comboBox_au.currentIndex() == 1
    assert a.dd.ui.comboBox_sq.currentIndex() == 2


def test_aKlu_pobrania_danych_przetworzenie_baz(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe

    assert len(a.bazy) > 0


def test_aKlu_pobrania_danych_uzytki(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe
    assert len(a.uzytki) > 2


def test_aKlu_pobrania_danych_wlasnosci(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe
    assert len(a.wlasnosci) > 2
