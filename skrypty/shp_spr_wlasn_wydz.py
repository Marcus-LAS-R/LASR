import os
from qgis.core import QgsVectorLayer, Qgis, QgsSpatialIndex, \
    QgsProject, QgsFeature, QgsField, QgsFields
from PyQt5.QtWidgets import QFileDialog, QDialog, QMessageBox
from PyQt5.QtCore import QVariant

from .ui.ui_wlasn_wydz import Ui_Dialog


class SprawdzWlasnosciWydzielen():
    def __init__(self, iface):
        self.iface = iface

        self.fields_def = [
            QgsField('ADR_LES', QVariant.String, len=30),
            QgsField('LANDID', QVariant.String, len=30),
            QgsField('GRP_WYDZ', QVariant.String, len=10),
            QgsField('GRP_KLU', QVariant.String, len=10),
        ]

    def pobierz_warstwy(self):
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        ls = [x for x in lyrs if x.name()[:2].upper() == 'LS']
        wydz = [x for x in lyrs if x.name()[:4].upper() == 'WYDZ']

        try:
            self.ls = ls[0]
            self.ls.dataProvider().setEncoding('UTF-8')
            ls_sc = self.ls.dataProvider().dataSourceUri().split("|")[0]
        except:  # nopep8
            ls_sc = False

        try:
            self.wydz = wydz[0]
            # self.wydz.dataProvider().setEncoding('UTF-8')
            wydz_sc = self.wydz.dataProvider().dataSourceUri().split("|")[0]

        except:  # nopep8
            wydz_sc = False

        self.pobierz_dane = PobierzDane(wydz_sc, ls_sc)
        self.pobierz_dane.exec_()

        if self.pobierz_dane.porzucone:
            return False

        self.wydz = QgsVectorLayer(self.pobierz_dane.ui.lineEdit_wydz.text(),
                                   'wydz', 'ogr')
        self.ls = QgsVectorLayer(self.pobierz_dane.ui.lineEdit_klu.text(),
                                 'ls', 'ogr')

        # sprawdz niezbedne pola w poszczegolnych warstwach
        if len([x.name() for x in self.wydz.dataProvider().fields().toList()
                if x.name() in ['ADR_LES', 'GRP']]) != 2:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Brak kolumn ADR_LES lub GRP w warstwie WYDZ - ',
                Qgis.Critical,
                0
            )
            return False

        ls_niez_pola = [x.name() for x in
                        self.ls.dataProvider().fields().toList()
                        if x.name() in ['LANDID', 'GRP']]
        if 2 != len(ls_niez_pola):
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'W warstwie LS brakuje którejś z kolumn: LANDID, GRP'
                '. Odnaleziono: ['+', '.join(ls_niez_pola)+']',
                Qgis.Critical,
                0
            )
            return False

        return True

    def sprawdz_wlasnosci(self):
        """Metoda sprawdza przecięcia wydzieleń z klu i jeżeli przecięcie ma
        powierzchnię większą od 1m2 oraz własność z wydzielenia jest inna niż
        z klu zwraca poligon z błędnym kodowaniem """

        # SpatialIndexy
        ls_si = QgsSpatialIndex()

        # slowniki wydz
        sl_wydz = {}
        sl_ls = {}

        # zbuduj struktury
        for f in self.wydz.getFeatures():
            sl_wydz[f.id()] = f

        for f in self.ls.getFeatures():
            ls_si.insertFeature(f)
            sl_ls[f.id()] = f

        self.feat_bl = []
        for key, val in sl_wydz.items():
            ids = ls_si.intersects(val.geometry().boundingBox())
            for id in ids:
                inter = sl_ls[id].geometry().intersection(val.geometry())
                if inter.area() > 1 and val['GRP'] != sl_ls[id]['GRP']:
                    nf = self.new_feat(
                        val['ADR_LES'],
                        sl_ls[id]['LANDID'],
                        val['GRP'],
                        sl_ls[id]['GRP'],
                    )
                    nf.setGeometry(inter)
                    self.feat_bl.append(nf)

        if len(self.feat_bl) > 0:
            self.lyrbl = QgsVectorLayer(
                "MultiPolygon?crs=epsg:2180&index=yes",
                "BŁĘDY_WŁASNOŚCI",
                "memory"
            )
            self.lyrbl.startEditing()
            self.lyrbl.dataProvider().addAttributes(self.fields_def)
            self.lyrbl.updateFields()
            self.lyrbl.addFeatures(self.feat_bl)
            self.lyrbl.commitChanges()
            QgsProject.instance().addMapLayer(self.lyrbl)

    def wyswietl_info(self):
        if len(self.feat_bl) > 0:
            self.iface.messageBar().pushMessage(
                'ZNALEZIONO BŁĘDY',
                'Własności w wydzieleniach i klu nie zgadzają się, '
                'proszę sprawdzić warstwę w TOC! Znaleziono rozbieżności: ' +
                str(len(self.feat_bl)),
                Qgis.Warning,
                15
            )
        else:
            self.iface.messageBar().pushMessage(
                'OK',
                'Nie znaleziono rozbieżności między warstwami WYDZ i KLU',
                Qgis.Success
            )

    def do_raportu(self):
        wyps = '---[ SPRAWDZANIE ZGODNOŚCI WŁASNOŚCI WYDZ<->KLU ]---\n'
        if len(self.feat_bl) > 0:
            wyps += 'Brak rozbieżności'
        else:
            wyps += 'Znaleziono rozbieżności: ' + str(len(self.feat_bl))

        wyps += '\n\n---[ KONIEC ]---\n\n'

    def new_feat(self, wydz='', landid='', grpw='', grpl=''):
        f = QgsFeature()
        fds = QgsFields()
        for fi in self.fields_def:
            fds.append(fi)

        f.setFields(fds)
        f.setAttribute(f.fieldNameIndex('ADR_LES'), wydz)
        f.setAttribute(f.fieldNameIndex('LANDID'), landid)
        f.setAttribute(f.fieldNameIndex('GRP_WYDZ'), grpw)
        f.setAttribute(f.fieldNameIndex('GRP_KLU'), grpl)
        return f


class PobierzDane(QDialog):
    def __init__(self, wydz=False, ls=False):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # katalog który będzie uzupełniony po pierwszym wskazaniu warstwy, bazy
        self.kat = ''

        # wartosc True jezeli uzytkownik zrezygnowal z przetwarzania
        self.porzucone = True

        # wpisz sciezki do przekazanych warstw i bazy
        if wydz:
            self.ui.lineEdit_wydz.setText(wydz)
            self.kat = os.path.dirname(wydz)
        if ls:
            self.ui.lineEdit_klu.setText(ls)
            self.kat = os.path.dirname(ls)

        # trigger do sprawdzenia poprawnosci wpisanych danych przez
        # uzyszkodnika
        self.valid = False

        # sygnały
        self.ui.pushButton_ok.clicked.connect(self.sprawdz_ok)
        self.ui.pushButton_porzuc.clicked.connect(self.porzuc)
        self.ui.pushButton_wydz.clicked.connect(self.kat_warstwa)
        self.ui.pushButton_klu.clicked.connect(self.kat_fochr)

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if os.path.isfile(self.ui.lineEdit_wydz.text()) and \
                os.path.isfile(self.ui.lineEdit_klu.text()):
            self.valid = True
            self.porzucone = False
            self.hide()
        else:
            msbx = QMessageBox(
                'Nie udało się odnaleźć wszystkich podanych plików!')
            msbx.exec_()

    def kat_warstwa(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż warstwę wydzielen',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_wydz.setText(sc)

    def kat_fochr(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż warstwę ls',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_klu.setText(sc)
