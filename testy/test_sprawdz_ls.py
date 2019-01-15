import pytest
import sys
from qgis.core import QgsGeometry, QgsPointXY, QgsApplication, QgsVectorLayer,\
    QgsField, QgsFields, QgsFeature
from PyQt5.QtWidgets import *  # noqa
from PyQt5.QtCore import *  # noqa
from PyQt5.QtGui import *  # noqa

from skrypty.sprawdz_ls import SprawdzMikro, AnalizujKlus, PobierzDane, \
    PrzetworzKlu
from skrypty.baza_przetworz import Przetworz
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
def data():
    # uniwersalana struktura indentyfikujace dzkat
    dodaj_pocz = ['10', '10', '042', '0001', '', ]

    # slownik uzytkow na dzialce
    uzt = [
         ['1', 1, 0.01, 1, 'Ls', 'V', 0.01, ],
         ['2', 2, 0.02, 2, 'Ls', 'V', 0.01, ],
         ['3', 3, 0.02, 3, 'Ls', 'V', 0.01, ],
         ['3', 3, 0.02, 4, 'Ls', 'IV', 0.01, ],
         ['4', 4, 0.04, 5, 'Ls', 'IV', 0.02, ],
    ]

    uz = []
    sl_int = {}
    for u in uzt:
        uz.append(dodaj_pocz+u+[''.join(dodaj_pocz+['.', u[0]])])
        sl_int[u[1]] = [u[0]]

    # sl wlascicieli dla poszcz dzkat
    wlt = [
        [1, 'a', 'OF', ],
        [2, 'a', 'OF', ],
        [3, 'a', 'OF', ],
        [3, 'b', 'OP', ],
        [4, 'b', 'OP', ],
    ]

    wl = []
    for w in wlt:
        wl.append(w+dodaj_pocz+sl_int[w[0]])

    # geometria dla uzytkow
    sl_uzg = {
        1: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(10, 10),
             QgsPointXY(10, 0),
             QgsPointXY(0, 0),
             ]],

        2: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(10, 10),
             QgsPointXY(10, 0),
             QgsPointXY(0, 0),
             ]],

        3: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(10, 10),
             QgsPointXY(10, 0),
             QgsPointXY(0, 0),
             ]],

        4: [[QgsPointXY(10, 0),
             QgsPointXY(10, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(10, 0),
             ]],

        5: [[QgsPointXY(10, 0),
             QgsPointXY(10, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(10, 0),
             ]],

    }

    # metadane dla atrybutow uzytkow
    sl_uzm = {
        1: ['10100420001.1', 'Ls', 'V'],
        2: ['10100420001.2', 'Ls', 'V'],
        3: ['10100420001.3', 'Ls', 'V'],
        4: ['10100420001.3', 'Ls', 'IV'],
        5: ['10100420001.4', 'Ps', 'IV'],
    }

    # zestawienie feat uzytkow do testow
    fds = QgsFields()
    for f in [
            QgsField("PARCELID", QVariant.String, len=50),  # noqa
            QgsField("AU", QVariant.String, len=10),  # noqa
            QgsField("SQ", QVariant.String, len=10),  # noqa
    ]:
        fds.append(f)

    u_feats = {}
    for i in range(1, 1+len(sl_uzg.keys())):
        feat = QgsFeature(i)
        feat.setFields(fds)
        feat.setAttribute(feat.fieldNameIndex('PARCELID'), sl_uzm[i][0])
        feat.setAttribute(feat.fieldNameIndex('AU'), sl_uzm[i][1])
        feat.setAttribute(feat.fieldNameIndex('SQ'), sl_uzm[i][2])
        feat.setGeometry(QgsGeometry().fromPolygonXY(sl_uzg[i]))

        if sl_uzm[i][0] not in u_feats:
            u_feats[sl_uzm[i][0]] = []
        u_feats[sl_uzm[i][0]].append(feat)

    # geometria dla dz
    sl_dzg = {
        1: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(10, 10),
             QgsPointXY(10, 0),
             QgsPointXY(0, 0),
             ]],

        2: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(0, 0),
             ]],

        3: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(0, 0),
             ]],

        4: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(30, 10),
             QgsPointXY(30, 0),
             QgsPointXY(0, 0),
             ]],

        5: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(30, 10),
             QgsPointXY(30, 0),
             QgsPointXY(0, 0),
             ]],
    }

    # metadane dla atrybutow uzytkow
    sl_dzm = {
        1: ['10100420001.1', ],
        2: ['10100420001.2', ],
        3: ['10100420001.3', ],
        4: ['10100420001.4', ],
        5: ['10100420001.94', ],  # sprawdzenie czy dz jest w bazie
    }

    # zestawienie feat uzytkow do testow
    fdsdz = QgsFields()
    fdsdz.append(QgsField("PARCELID", QVariant.String, len=50))  # noqa

    d_feats = {}
    for i in range(1, 1+len(sl_dzg.keys())):
        feat = QgsFeature(i)
        feat.setFields(fdsdz)
        feat.setAttribute(feat.fieldNameIndex('PARCELID'), sl_dzm[i][0])
        feat.setGeometry(QgsGeometry().fromPolygonXY(sl_dzg[i]))

        d_feats[sl_dzm[i][0]] = [feat, ]

    return [uz, wl, u_feats, d_feats]


@pytest.fixture()
def data_topo():
    # uniwersalana struktura indentyfikujace dzkat
    dodaj_pocz = ['10', '10', '042', '0001', '', ]

    # slownik uzytkow na dzialce
    # PARCELNR, PARCEL_INT_NUM, PARCELAREA, LAND_INT_NUM, AU, SQ, LANDAREA
    uzt = [
         ['1', 1, 0.03, 1, 'Ls', 'V', 0.01, ],  # 3 popr w bazie
         ['1', 1, 0.03, 2, 'Ps', 'IV', 0.01, ],
         ['1', 1, 0.03, 3, 'Ls', 'VI', 0.01, ],
         ['2', 2, 0.04, 4, 'Ps', 'IV', 0.01, ],  # 2 przecinajace sie, w bazie
         ['2', 2, 0.04, 5, 'Ls', 'IV', 0.02, ],
         ['3', 3, 0.04, 6, 'Ps', 'V', 0.01, ],  # 2 nakladajce sie, oba w bazie
         ['3', 3, 0.04, 7, 'Ls', 'V', 0.01, ],
         ['4', 4, 0.04, 8, 'Ps', 'V', 0.01, ],  # 1 nakladajacy, oba w bazie
         ['4', 4, 0.04, 9, 'Ls', 'V', 0.01, ],
    ]

    uz = []
    sl_int = {}
    for u in uzt:
        uz.append(dodaj_pocz+u+[''.join(dodaj_pocz+['.', u[0]])])
        sl_int[u[1]] = [u[0]]

    # sl wlascicieli dla poszcz dzkat
    wlt = [
        [1, 'a', 'OF', ],
        [2, 'a', 'OF', ],
        [3, 'a', 'OF', ],
        [4, 'b', 'OF', ],
    ]

    wl = []
    for w in wlt:
        wl.append(w+dodaj_pocz+sl_int[w[0]])

    # geometria dla uzytkow
    sl_uzg = {
        1: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(10, 10),
             QgsPointXY(10, 0),
             QgsPointXY(0, 0),
             ]],

        2: [[QgsPointXY(10, 0),
             QgsPointXY(10, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(10, 0),
             ]],

        3: [[QgsPointXY(20, 0),
             QgsPointXY(20, 10),
             QgsPointXY(30, 10),
             QgsPointXY(30, 0),
             QgsPointXY(20, 0),
             ]],

        4: [[QgsPointXY(00, 0),
             QgsPointXY(00, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(00, 0),
             ]],

        5: [[QgsPointXY(19, 0),
             QgsPointXY(19, 10),
             QgsPointXY(30, 10),
             QgsPointXY(30, 0),
             QgsPointXY(19, 0),
             ]],

        6: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(0, 0),
             ]],

        7: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(0, 0),
             ]],

        8: [[QgsPointXY(0, 0),
             QgsPointXY(0, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(0, 0),
             ]],

        9: [[QgsPointXY(10, 0),
             QgsPointXY(10, 10),
             QgsPointXY(20, 10),
             QgsPointXY(20, 0),
             QgsPointXY(10, 0),
             ]],

    }

    # metadane dla atrybutow uzytkow
    sl_uzm = {
        1: ['10100420001.1', 'Ls', 'V'],
        2: ['10100420001.1', 'Ps', 'IV'],
        3: ['10100420001.1', 'Ls', 'VI'],
        4: ['10100420001.2', 'Ps', 'IV'],
        5: ['10100420001.2', 'Ls', 'IV'],
        6: ['10100420001.3', 'Ps', 'V'],
        7: ['10100420001.3', 'Ls', 'V'],
        8: ['10100420001.4', 'Ps', 'V'],
        9: ['10100420001.4', 'Ls', 'V'],
    }

    # zestawienie feat uzytkow do testow
    fds = QgsFields()
    for f in [
            QgsField("PARCELID", QVariant.String, len=50),  # noqa
            QgsField("AU", QVariant.String, len=10),  # noqa
            QgsField("SQ", QVariant.String, len=10),  # noqa
    ]:
        fds.append(f)

    u_feats = {}
    for i in range(1, 1+len(sl_uzg.keys())):
        feat = QgsFeature(i)
        feat.setFields(fds)
        feat.setAttribute(feat.fieldNameIndex('PARCELID'), sl_uzm[i][0])
        feat.setAttribute(feat.fieldNameIndex('AU'), sl_uzm[i][1])
        feat.setAttribute(feat.fieldNameIndex('SQ'), sl_uzm[i][2])
        feat.setGeometry(QgsGeometry().fromPolygonXY(sl_uzg[i]))

        if sl_uzm[i][0] not in u_feats:
            u_feats[sl_uzm[i][0]] = []
        u_feats[sl_uzm[i][0]].append(feat)

    feat = QgsFeature()
    feat.setFields(fds)
    feat.setAttribute(feat.fieldNameIndex('PARCELID'), '')

    return [uz, wl, u_feats, feat]


@pytest.fixture()
def mikro_data():
    klu = []

    sl_ops = {
        1: ['Ls', 'V', ''],
        2: ['Ls', 'VI', ''],
        3: ['Ls', 'V', ''],
        4: ['Ps', 'V', 'Brak w bazie; '],
        5: ['Ls', 'VI', ''],
        6: ['Ls', 'VI', ''],
        7: ['Ł', 'III', 'Brak w bazie; '],
        8: ['Ls', 'V', ''],
        9: ['Ls', 'V', ''],
        10: ['Ls', 'II', 'Brak w bazie; '],
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
    fields.append(QgsField('SPRAWDZ', QVariant.String, len=50))  # noqa

    for fid in range(1, 12):
        f = QgsFeature(fid)
        f.setFields(fields)

        f.setAttribute(f.fieldNameIndex('PARCELID'), '1')
        f.setAttribute(f.fieldNameIndex('AU'), sl_ops[fid][0])
        f.setAttribute(f.fieldNameIndex('SQ'), sl_ops[fid][1])
        f.setAttribute(f.fieldNameIndex('SPRAWDZ'), sl_ops[fid][2])

        f.setGeometry(QgsGeometry().fromPolygonXY(sl_geom[fid]))

        klu.append(f)

    return klu


def test_poprawnosci_danych_kwer(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    assert (p.sl_ile_uzytkow_na_dzialce['10100420001.3'] == 2) and \
        (p.sl_ls_na_dz['10100420001.3'] == ['V', 'IV'])


def test_poprawnosci_feat_u(data):
    u = []
    for us in data[2].values():
        u += us
    wyn = set(map(lambda x: x.isValid(), u))
    assert wyn == set([True])


def test_poprawnosci_feat_u_topo(data_topo):
    u = []
    for us in data_topo[2].values():
        u += us
    wyn = set(map(lambda x: x.isValid(), u))
    assert wyn == set([True])


def test_poprawnosci_feat_dz(data):
    wyn = set(map(lambda x: x.isValid(),
                  [x[0] for x in list(data[3].values())]))
    assert wyn == set([True])


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


def test_pKlu_sprawdzenie_popr_feats_wejsciowych(data):
    p = PrzetworzKlu(list(data[3]['10100420001.3'])[0],
                     data[2]['10100420001.3'],
                     '')

    assert p.is_valid() is True


def test_pKlu_sprawdzenie_niepopr_feats_wejsciowych(data):
    p = PrzetworzKlu(list(data[3]['10100420001.3'])[0],
                     data[2]['10100420001.3'] +
                     data[2]['10100420001.2'],
                     '')

    assert p.is_valid() is False


def test_pKlu_sprawdzenie_pustych_uz_wejsciowych(data):
    p = PrzetworzKlu(list(data[3]['10100420001.3'])[0],
                     [],
                     '')

    assert p.is_valid() is True


def test_pKlu_test_przetworzenia_pow_sumarycznej(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu(list(data[3]['10100420001.3'])[0],
                      data[2]['10100420001.3'],
                      p)

    pk.przetworz()
    assert len(pk.sl_klus_grupy.keys()) == 2


def test_pKlu_test_sprawdzenia_czy_dz_w_bazie(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu(list(data[3]['10100420001.3'])[0],
                      data[2]['10100420001.3'],
                      p)
    pk.przetworz()

    assert pk.s_czy_dz_w_bazie() is True


def test_pKlu_test_sprawdzenia_czy_dz_niema_w_bazie(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu(list(data[3]['10100420001.94'])[0],
                      [],
                      p)
    pk.przetworz()

    assert pk.s_czy_dz_w_bazie() is False


def test_pKlu_jeden_ls_na_dz_dopasowany(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu(list(data[3]['10100420001.1'])[0],
                      data[2]['10100420001.1'],
                      p)
    pk.przetworz()
    pk.s_czy_ls_na_calosci()

    assert pk.dz.geometry().area() == pk.klus_popr[0].geometry().area() and \
        isinstance(pk.klus_popr[0]['SQ'], str)


def test_pKlu_jeden_ls_na_dz_niedopasowany(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu(list(data[3]['10100420001.2'])[0],
                      data[2]['10100420001.2'],
                      p)
    pk.przetworz()
    pk.s_czy_jeden_ls()

    assert len(pk.klus_popr) == 1


def test_pKlu_brak_ls_na_dz_w_graf(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu(list(data[3]['10100420001.1'])[0],
                      [],
                      p)
    pk.przetworz()
    if not pk.s_czy_ls_na_calosci():
        pk.s_czy_jeden_ls()

    assert pk.dz.geometry().area() == pk.klus_popr[0].geometry().area() and \
        isinstance(pk.klus_popr[0]['SQ'], str)


def test_pKlu_jeden_ls_na_dz_zly_AU(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu(list(data[3]['10100420001.4'])[0],
                      data[2]['10100420001.4'],
                      p)
    pk.przetworz()
    pk.s_czy_jeden_ls()

    assert len(pk.klus_popr) == 1 and pk.klus_popr[0]['AU'] == 'Ls'


def test_pKlu_jeden_ls_na_dz_zly_SQ(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    uz = data[2]['10100420001.2'][0]
    uz.setAttribute(uz.fieldNameIndex('SQ'), 'I')
    pk = PrzetworzKlu(list(data[3]['10100420001.2'])[0],
                      [uz],
                      p)
    pk.przetworz()
    pk.s_czy_jeden_ls()

    assert len(pk.klus_popr) == 1 and pk.klus_popr[0]['AU'] == 'Ls' and \
        pk.klus_popr[0]['SPRAWDZ'] == 'Podmieniono SQ na zgodny z bazą; '


def test_pKlu_spr_topo_poprawnych(data_topo):
    data = data_topo
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu('',
                      data[2]['10100420001.1'],
                      p)
    pk.pid = '10100420001.1'
    pk.sprawdz_topologie()

    assert len(pk.klus) == 3 and len(pk.klus_do_spr) == 0


def test_pKlu_spr_topo_1_przecinajacy_oba_w_bazie(data_topo):
    data = data_topo
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu('',
                      data[2]['10100420001.2'],
                      p)
    pk.pid = '10100420001.2'
    pk.sprawdz_topologie()

    assert len(pk.klus_do_spr) == 1 and \
        len(pk.klus) == 2 and \
        pk.klus_do_spr[0]['SPRAWDZ'] == 'nałożona część poligonów' and \
        pk.klus_do_spr[0].geometry().area() == 10


def test_pKlu_spr_topo_1_przecinajacy_jeden_w_bazie(data_topo):
    data = data_topo
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    uz = data[2]['10100420001.2'][0]
    uz.setAttribute(uz.fieldNameIndex('SQ'), 'I')
    pk = PrzetworzKlu('',
                      [uz]+[data[2]['10100420001.2'][1]],
                      p)
    pk.pid = '10100420001.2'
    pk.sprawdz_topologie()

    assert len(pk.klus_do_spr) == 1 and \
        len(pk.klus) == 2 and \
        pk.klus_do_spr[0]['SPRAWDZ'] == 'nałożona część poligonów' and \
        pk.klus_do_spr[0].geometry().area() == 10


def test_pKlu_spr_topo_2_nakladajace_oba_w_bazie(data_topo):
    data = data_topo
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu('',
                      data[2]['10100420001.3'],
                      p)
    pk.pid = '10100420001.3'
    pk.sprawdz_topologie()

    assert len(pk.klus) == 1 and \
        pk.klus[0]['AU'] == 'Ls' and \
        pk.klus_bledy[0]['AU'] == 'Ps' and \
        pk.klus_bledy[0]['SPRAWDZ'] == 'nakłada się z innym' and \
        len(pk.klus_bledy) == 1


def test_pKlu_spr_topo_2_nakladajace_jeden_w_bazie(data_topo):
    data = data_topo
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    uz = data[2]['10100420001.3'][1]
    uz.setAttribute(uz.fieldNameIndex('SQ'), 'I')
    pk = PrzetworzKlu('',
                      [uz]+[data[2]['10100420001.3'][0]],
                      p)
    pk.pid = '10100420001.3'
    pk.sprawdz_topologie()

    assert len(pk.klus) == 1 and \
        pk.klus[0]['AU'] == 'Ps' and \
        pk.klus_bledy[0]['SQ'] == 'I' and \
        pk.klus_bledy[0]['SPRAWDZ'] == 'nakłada się z innym' and \
        len(pk.klus_bledy) == 1


def test_pKlu_spr_topo_1_nakladajacy_oba_w_bazie(data_topo):
    data = data_topo
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    dz = data[3]
    dz.setAttribute(dz.fieldNameIndex('PARCELID'), '10100420001.4')
    pk = PrzetworzKlu(dz,
                      data[2]['10100420001.4'],
                      p)
    # pk.pid = '10100420001.4'
    pk.przetworz()
    pk.sprawdz_topologie()

    assert len(pk.klus) == 2 and \
        pk.klus_do_spr[0]['SPRAWDZ'] == \
        'nałożona część poligonu, na inny cały' and \
        len(pk.klus_do_spr) == 1


def test_pKlu_spr_polacz_ostateczne(data):
    p = Przetworz()
    p.dodaj_uzytki(data[0])
    p.dodaj_wlasnosci(data[1])
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()

    pk = PrzetworzKlu(list(data[3]['10100420001.3'])[0],
                      data[2]['10100420001.3'],
                      p)
    pk.przetworz()
    if not pk.s_czy_ls_na_calosci():
        pk.s_czy_jeden_ls()
    pk.s_dopisz_uzyt()
    pk.polacz_ostateczne()

    # assert isinstance(pk.klus_popr[0]['SQ'], str)
    # assert pk.stworz_landid(pk.klus_popr[0]) == '10100420001.3.LsV'
    assert len(pk.poprawne.keys()) == 2 and pk.poprawne[0]['AU'] == 'Ls'
