import pytest
import sys
from qgis.core import QgsGeometry, QgsPointXY, QgsApplication, QgsVectorLayer,\
    QgsField, QgsFields, QgsFeature
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
qgs = QgsApplication([], False)
# QgsApplication.initQgis()  # noqa
qgs.initQgis()  # noqa


@pytest.fixture()
def przetwarzanie_wejsciowe():
    dzl = QgsVectorLayer('/home/qnox/upul/testy/grabica/shp/DZKAT.shp',
                         'dz',
                         'ogr')
    lsl = QgsVectorLayer('/home/qnox/upul/testy/grabica/shp/KLU_wybrane.shp',
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
def mikro_data():
    klu = []

    sl_ops = {
        1: ['Ls', 'V', ''],
        2: ['Ls', 'VI', ''],
        3: ['Ls', 'V', ''],
        4: ['Ps', 'V', 'Brak w bazie, '],
        5: ['Ls', 'VI', ''],
        6: ['Ls', 'VI', ''],
        7: ['Ł', 'III', 'Brak w bazie, '],
        8: ['Ls', 'V', ''],
        9: ['Ls', 'V', ''],
        10: ['Ls', 'II', 'Brak w bazie, '],
        11: ['W', '', ''],
    }

    sl_geom = {
        1: [[QgsPointXY(0, 0),
             QgsPointXY(0, 30),
             QgsPointXY(30, 30),
             QgsPointXY(30, 0),
             QgsPointXY(0, 0),
             ]],

        2: [[QgsPointXY(30, 0),
             QgsPointXY(30, 40),
             QgsPointXY(50, 40),
             QgsPointXY(50, 0),
             QgsPointXY(30, 0),
             ]],

        3: [[QgsPointXY(0, 50),
             QgsPointXY(20, 50),
             QgsPointXY(20, 49),
             QgsPointXY(0, 49),
             QgsPointXY(0, 50),
             ]],

        4: [[QgsPointXY(29, 30),
             QgsPointXY(29, 45),
             QgsPointXY(30, 45),
             QgsPointXY(30, 30),
             QgsPointXY(29, 30),
             ]],

        5: [[QgsPointXY(49, 40),
             QgsPointXY(49, 50),
             QgsPointXY(50, 50),
             QgsPointXY(50, 40),
             QgsPointXY(49, 40),
             ]],

        6: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(1, 10),
             QgsPointXY(1, 0),
             QgsPointXY(0, 0),
             ]],

        7: [[QgsPointXY(25, 0),
             QgsPointXY(25, 1),
             QgsPointXY(41, 1),
             QgsPointXY(41, 0),
             QgsPointXY(25, 0),
             ]],

        8: [[QgsPointXY(0, 30),
             QgsPointXY(0, 20),
             QgsPointXY(1, 20),
             QgsPointXY(1, 30),
             QgsPointXY(0, 30),
             ]],

        9: [[QgsPointXY(0, 20),
             QgsPointXY(0, 10),
             QgsPointXY(1, 10),
             QgsPointXY(1, 20),
             QgsPointXY(0, 20),
             ]],

        10: [[QgsPointXY(0, 49),
              QgsPointXY(10, 49),
              QgsPointXY(10, 48),
              QgsPointXY(0, 48),
              QgsPointXY(0, 49),
              ]],

        11: [[QgsPointXY(0, 40),
              QgsPointXY(2, 40),
              QgsPointXY(2, 38),
              QgsPointXY(0, 38),
              QgsPointXY(0, 40),
              ]],
    }

    fields = QgsFields()
    fields.append(QgsField('PARCELID', QVariant.String, len=30))  # noqa
    fields.append(QgsField('AU', QVariant.String, len=10))  # noqa
    fields.append(QgsField('SQ', QVariant.String, len=10))  # noqa
    fields.append(QgsField('UWAGI', QVariant.String, len=50))  # noqa

    for fid in range(1, 12):
        f = QgsFeature(fid)
        f.setFields(fields)

        f.setAttribute(f.fieldNameIndex('PARCELID'), '1')
        f.setAttribute(f.fieldNameIndex('AU'), sl_ops[fid][0])
        f.setAttribute(f.fieldNameIndex('SQ'), sl_ops[fid][1])
        f.setAttribute(f.fieldNameIndex('UWAGI'), sl_ops[fid][2])

        f.setGeometry(QgsGeometry().fromPolygonXY(sl_geom[fid]))

        klu.append(f)

    return klu


def test_aKlu_pobrania_danych_od_uzytk(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe

    assert a.dd.ui.lineEdit_klu.text() == \
        '/home/qnox/upul/testy/grabica/shp/KLU_wybrane.shp'
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
    assert len(a.uzytki) > 0
    assert len(a.wlasnosci) > 0


def test_aKlu_pobrania_danych_przetworzenie_baz(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe

    assert len(a.bazy) > 0


def test_aKlu_sprawdzenie_popr_warstw_wejsciowych(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe
    assert a.sprawdz_warunki() is True


def test_aKlu_sprawdzenie_przyg_do_analiz(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe
    a.typ == 'LAN'
    a.przygotuj_tabele()
    a.przygotuj_do_analizy()

    assert len([x.name() for x in a.klu.dataProvider().fields()
                if x.name() in ['SQ', 'AU', ]]) == 2


def test_aKlu_pobrania_danych_uzytki(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe
    assert len(a.uzytki) > 2


def test_aKlu_pobrania_danych_wlasnosci(przetwarzanie_wejsciowe):
    a = przetwarzanie_wejsciowe
    assert len(a.wlasnosci) > 2


def test_poprawnosci_mikrusow(mikro_data):
    wyn = set(map(lambda x: x.isValid(), mikro_data))
    assert wyn == set([True])


def test_mikrusow_usun_wysepki(mikro_data):
    d = mikro_data
    s = SprawdzMikro(d)
    s.przetworz()
    popr, spr, usun = s.zwroc_wyn()

    # u = [x.id() for x in usun if x.id() in [5, 7, 8, 9, 6, ]]
    p = [1, 2, 11]

    # assert len(s.slk) == 11
    # assert len(s.do_usun) == len(usun)
    # assert len(u) == 6
    assert len(p) == len(popr)
    # assert 5 == len([x.id() for x in popr])
