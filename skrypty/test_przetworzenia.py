import pytest
import os
import sys
import platform
from qgis.core import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

from skrypty.baza_przetworz import Przetworz
from skrypty.baza_wrapper import Baza
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


@pytest.fixture()
def przetwarzanie():
    b = Baza('/home/qnox/upul/testy/grabica')
    if not b.polacz():
        return False

    p = Przetworz()
    p.dodaj_uzytki(b.uzytki())
    p.dodaj_wlasnosci(b.wlasnosci())

    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    return p


def test_pobrania_wlasnosci(przetwarzanie):
    p = przetwarzanie
    assert len(p.baza_wlasnosci) > 1


def test_pobrania_uzytkow(przetwarzanie):
    p = przetwarzanie
    assert len(p.baza_uzytki) > 1
