import os
import processing
from ui_baza_dopiszFO import Ui_Dialog
from qgis.core import QgsVectorLayer, Qgis
from PyQt5.QtGui import QDialog, QFileDialog, QMessageBox

from baza_wrapper import Baza


class DopiszFO(object):
    def __init__(self, iface):
        self.iface = iface

        # slownik z powierzchniami wydzielen przecinajacych sie z FO
        self.sl = {}

    def pobierz_dane_od_uzytkownika(self):
        """Pobierz dane przez formularz"""
        self.Dane = PobierzDane()
        self.Dane.exec_()

        if self.Dane.porzucone:
            return False

        # otworz potrzebne warstwy i sprawdz czy wszystko jest jak potrzeba
        self.wydz = QgsVectorLayer(self.Dane.ui.lineEdit_warstwa.text(),
                                   'wydz',
                                   'ogr'
                                   )
        self.fo = QgsVectorLayer(self.Dane.ui.lineEdit_fochr.text(),
                                 'fochr',
                                 'ogr'
                                 )

        if 'ADR_LES' not in self.wydz.dataProvider().fieldNameMap():
            self.iface.messageBar.pushMessage(
                'Wydzielenia',
                'Brak kolumny ADR_LES w warstwie',
                Qgis.Critical,
                5)
            return False

        braki = []
        for x in ['TYP', 'NAZWA']:
            if x not in self.fo.dataProvider().fieldNameMap():
                braki.append(x)

        if len(braki) > 0:
            self.iface.messageBar.pushMessage(
                'formy ochrony',
                'Brak wymaganych kolumn w warstwie ['+', '.join(braki)+']',
                Qgis.Critical,
                5)
            return False

        self.baza = Baza(self.Dane.ui.lineEdit_warstwa.text())
        if self.baza.polacz():
            if self.baza.dopisane_FO():
                self.iface.messageBar.pushMessage(
                    'BAZA',
                    'W bazie znajdują się już dopisane formy ochrony!',
                    Qgis.Critical,
                    5)
                return False
        else:
            self.iface.messageBar.pushMessage(
                'BAZA',
                'Nie udało się połączyć ze wskazaną bazą!',
                Qgis.Critical,
                5)
            return False

        return True


class PobierzDane(QDialog):
    def __init__(self):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # katalog który będzie uzupełniony po pierwszym wskazaniu warstwy, bazy
        self.kat = ''

        # wartosc True jezeli uzytkownik zrezygnowal z przetwarzania
        self.porzucone = False

        # trigger do sprawdzenia poprawnosci wpisanych danych przez
        # uzyszkodnika
        self.valid = False

        # sygnały
        self.ui.pushButton_ok.clicked.connect(self.sprawdz_ok)
        self.ui.pushButton_cancel.clicked.connect(self.porzuc)
        self.ui.pushButton_bazy.clicked.connect(self.kat_baza)
        self.ui.pushButton_warstwa.clicked.connect(self.kat_warstwa)
        self.ui.pushButton_fochr.clicked.connect(self.kat_fochr)

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if os.path.isfile(self.ui.lineEdit_warstwa) and \
                os.path.isfile(self.ui.lineEdit_bazy) and \
                os.path.isfile(self.ui.lineEdit_fochr):
            self.valid = True
            self.hide()
        else:
            msbx = QMessageBox(
                'Nie udało się odnaleźć wszystkich podanych plików!')
            msbx.exec_()

    def kat_baza(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż baze Taksatora',
                                           self.kat,
                                           "Access MDB (*.mdb)")[0]
        self.kat = os.path.dirname(sc)
        self.ui.lineEdit_bazy.setText(sc)

    def kat_warstwa(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż warstwę wydzielen',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        self.kat = os.path.dirname(sc)
        self.ui.lineEdit_warstwa.setText(sc)

    def kat_fochr(self):
            sc = QFileDialog().getOpenFileName(self,
                                               'Wskaż warstwę form ochrony',
                                               self.kat,
                                               "ESRI Shapefile (*.shp)")[0]
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_warstwa.setText(sc)
