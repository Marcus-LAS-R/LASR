import os
import re
import glob
import shutil
from datetime import datetime
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QVariant
from qgis.core import *
import processing
from collections import Counter, namedtuple
from .baza_wrapper import Baza
from ..ui.ui_sprawdz_ls import Ui_Dialog


class SprawdzLs(object):
    def __init__(self, i):
        self.iface = i
        k = False
        d = False

        # sprawdz czy uzyszkodnik zaznaczyl warstwe
        try:
            k = self.iface.activeLayer()
        except:
            pass

        for key, lyr in QgsProject.instance().mapLayers().items():
            if key[:5] == 'DZKAT':
                d = lyr

        analizuj = AnalizujKlu(self.iface, k, d)


class AnalizujKlu(object):
    def __init__(self, i, k, d):
        self.iface = i
        self.klu = k
        self.dzkat = d

        self.indeks = False
        self.lyrw = False  # warstwa wyjsciowa
        self.bledy_topo = []  # lista feats, ktore przecinaja sie z innymi
        self.iatr = False  # indeks pól w warstwie wyjsciowej
        self.county = ''  # kod wojewodztwa
        self.district = ''  # kod powiatu
        self.dz_nieles = []  # lista dzialek nielesnych

        self.czas = datetime.now().isoformat().replace(":", "")[:-7].replace('-', '')

        self.kolumny_dz = [
            QgsField("COUNTY", QVariant.String, len=2),
            QgsField("DISTRICT", QVariant.String, len=2),
            QgsField("MUNICIP", QVariant.String, len=3),
            QgsField("COMMUNITY", QVariant.String, len=4),
            QgsField("PARCELNR", QVariant.String, len=20),
            QgsField("PARCELID", QVariant.String, len=50),
            QgsField("GRP", QVariant.String, len=2),
            QgsField("ARK", QVariant.String, len=12),
            QgsField("NIELES", QVariant.String, len=3),
            QgsField("UWAGI", QVariant.String, len=150),
            QgsField("PARCEL_AR", QVariant.Double, "double", 10, 4),
            QgsField("PARCEL_POW", QVariant.Double, "double", 10, 4),
        ]

        self.kolumny_ls = [
            QgsField("AU", QVariant.String, len=10),
            QgsField("SQ", QVariant.String, len=10),
            QgsField("SPRAWDZ", QVariant.String, len=150),
            QgsField("LANDID", QVariant.String, len=50),
            QgsField("LAND_AR", QVariant.Double, "double", 10, 4),
            QgsField("LAND_POW", QVariant.Double, "double", 10, 4),
        ]

    def pobierz_dane_od_uzytkownika(self):
        self.dd = PobierzDane(self.lyr)
        self.dd.exec_()

    def sprawdz_warunki(self):
        """Sprawdz czy warstwy maja odpowiednie struktury"""
        if not self.dd.lyrk.isValid() and not self.dd.lyrd.isValid():
            return False

        if [x.name() for x in self.dd.lyrd.dataProvider().fields()] not in \
                self.kolumny_dz:
            return False

        return True

    def pobierz_dane(self):
        self.lyrk = self.dd.lyrk
        self.lyrd = self.dd.lyrd
        self.bazy = glob.glob(
            os.path.join(self.dd.ui.lineEdit_bazy.text(),
                         '*.mdb'))
        self.typ = self.dd.ui.comboBox_ident.currentText()[:3]
        self.wl = self.dd.ui.comboBox_wlas.currentText()[:2]
        self.landid = self.dd.ui.comboBox_landid.currentText()
        self.sq = self.dd.ui.comboBox_sq.currentText()
        self.au = self.dd.ui.comboBox_au.currentText()

        # Pobierz dane z baz danych
        self.uzytki = []
        self.wlasnosci = []

        QgsMessageLog.logMessage(
            'Znaleziono bazy: '+', '.join(self.bazy),
            "Las-R"
        )
        for baza in self.bazy:
            b = Baza(baza)
            if b.polacz():
                self.uzytki += b.uzytki()
                self.wlasnosci += b.wlasnosci()
            else:
                QgsMessageLog.logMessage(
                    'Nie udało połączyć się z: ' + baza,
                    "Las-R"
                )

class PobierzDane(QDialog):
    def __init__(self, k=False, d=False):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.lyrk = k
        self.lyrd = d
        self.pola = []
        self.ile_baz = 0
        self.ui.comboBox_ident.setDisabled(True)

        # Jezeli jest warstwa klu, odczytaj jej dane
        if self.lyrk:
            if self.lyrk.isValid():
                self.ui.lineEdit_klu.setText(
                    self.lyrk.dataProvider().dataSourceUri().split("|")[0])
                self.ui.comboBox_ident.setDisabled(False)
                self.wczytaj_pola()

        # Jezeli jest warstwa dzkat, odczytaj jej dane
        if self.lyrd:
            if self.lyrd.isValid():
                self.ui.lineEdit_klu.setText(
                    self.lyrd.dataProvider().dataSourceUri().split("|")[0])

        self.ui.pushButton_klu.clicked.connect(self.pobierz_klu)
        self.ui.pushButton_dzkat.clicked.connect(self.pobierz_dzkat)
        self.ui.pushButton_bazy.clicked.connect(self.pobierz_bazy)
        self.ui.comboBox_ident.currentTextChanged.connect(self.identyfikuj)

    def wczytaj_pola(self):
        """Metoda uzupelnia comboboxy na podstawie podanej warstwy"""
        # wybierz nazwy pol z warstwy, ktore nie sa numeryczne
        self.pola = ['---'] + [x.name() for x in self.lyrk.dataProvider().fields(
                               ).toList() if not x.isNumeric()]

        # wyczysc wszystkie comboboxy z kolumnami
        comboboxy = [
            self.ui.comboBox_sq,
            self.ui.comboBox_au,
            self.ui.comboBox_landid,
        ]

        # wyczysc i dodaj przetworzone pola do comboboxow
        for x in comboboxy:
            x.clear()
            x.addItems(self.pola)

    def pobierz_klu(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę i ją przetwarza"""
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę',
                                                '',
                                                "ESRI shp (*.shp)")[0]
        try:
            self.lyrk = QgsVectorLayer(warstwa, "klu", "ogr")
            self.ui.lineEdit_klu.setText(
                self.lyrk.dataProvider().dataSourceUri().split("|")[0])
            self.ui.comboBox_ident.setDisabled(False)
        except:
            msbx = QMessageBox('Nie udało się otworzyć podanej warstwy')
            msbx.exec()
            self.lyrk = False
            self.ui.comboBox_ident.setDisabled(True)

    def pobierz_dzkat(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę i ją przetwarza"""
        if self.lyrk:
            kat = os.path.dirname(self.lyrk.dataProvider().dataSourceUri().split("|")[0])
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę',
                                                kat,
                                                "ESRI shp (*.shp)")[0]
        try:
            self.lyrd = QgsVectorLayer(warstwa, "dz", "ogr")
            self.ui.lineEdit_dz.setText(
                self.lyrd.dataProvider().dataSourceUri().split("|")[0])
        except:
            msbx = QMessageBox('Nie udało się otworzyć podanej warstwy')
            msbx.exec()
            self.lyrd = False

    def pobierz_bazy(self):
        """Metoda pobiera wskazany przez użytkownika katalog"""
        kat = ""
        if self.lyrk:
            kat = os.path.dirname(self.lyrk.dataProvider().dataSourceUri().split("|")[0])
        bazy_kat = QFileDialog().getExistingDirectory(self,
                                                      "Katalog z bazami danych",
                                                      kat)
        self.ile_baz = len(glob.glob(os.path.join(bazy_kat, '*.mdb')))
        if self.ile_baz > 0:
            self.ui.label_bazy.setText("Znalazałem baz: "+str(self.ile_baz))
            self.ui.lineEdit_bazy.setText(bazy_kat)

        else:
            self.ui.label_bazy.setText("Nie znaleziono baz *.mdb")

    def identyfikuj(self):
        """Metoda sprawdza wybór uzytkownika i udostepnia odpowiednie pola do wyboru"""
        if self.ui.comboBox_ident.currentText() == '---':
            self.ui.groupBox_adradm.setDisabled(True)
            self.ui.groupBox_kol.setDisabled(True)
            self.ui.pushButton_ok.setDisabled(True)
        elif self.ui.comboBox_ident.currentText()[:3] == 'AU ':
            self.ui.groupBox_adradm.setDisabled(False)
            self.ui.pushButton_ok.setDisabled(False)
            self.ui.groupBox_kol.setDisabled(True)
        elif self.ui.comboBox_ident.currentText()[:3] == 'LAN':
            self.ui.groupBox_adradm.setDisabled(True)
            self.ui.pushButton_ok.setDisabled(False)
            self.ui.groupBox_kol.setDisabled(False)
