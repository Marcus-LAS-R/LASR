import os

from qgis.core import (
    QgsField, QgsVectorLayer, QgsGeometry, QgsRectangle, QgsFeature,
    QgsCoordinateReferenceSystem, QgsVectorFileWriter, QgsProject,
)
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QDialog, QMessageBox

from . import kafelkowanie
from .ui.ui_atlasuj_auto import Ui_Dialog


class GenerujAtlasAuto:
    """ Automatycznie generuje pola atlasowe (jak "Rysuj pola atlasowe"),
    ale korzysta z kafelkowanie.pokryj_kaflami: każdy kolejny kafel
    pokrywa maksymalną liczbę jeszcze nieobsłużonych obiektów warstwy
    wejściowej i jest na nich wycentrowany - żaden obiekt nie zostaje
    przecięty krawędzią kafla. Numeracja STRONA powstaje automatycznie,
    bez ręcznego digitalizowania linii (jak w "Numeruj pola atlasu").
    """

    def __init__(self, iface):
        self.iface = iface
        self.lyr = False
        self.kat = ''
        self.rozm = []  # rozmiar kafla w metrach [szer, wys]
        self.pola = False

    def wybierz_warstwe(self):
        self.lyr = self.iface.activeLayer()
        if self.lyr is None or self.lyr.wkbType() not in [3, 6]:
            self.iface.messageBar().pushWarning(
                'Atlasuj automatycznie',
                'Zaznacz warstwę powierzchniową do zaatlasowania'
            )
            return False

        try:
            self.kat = os.path.dirname(
                self.lyr.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            self.iface.messageBar().pushWarning(
                'Atlasuj automatycznie',
                'Nie udało się ustalić katalogu warstwy'
            )
            return False
        return True

    def pobierz_dane(self):
        self.d = PobierzDane()
        self.d.exec_()

        if self.d.porzuc:
            return False

        self.rozm = self.d.wynik
        return True

    def generuj_pola(self):
        self.pola = QgsVectorLayer(
            "Polygon?crs=epsg:2180&index=yes", "ATLAS_AUTO", "memory")
        self.pola.startEditing()
        self.pola.dataProvider().addAttributes([
            QgsField("STRONA", QVariant.Int),
            QgsField("ZROBIONE", QVariant.String, len=50),
        ])
        self.pola.updateFields()

        bboxy = []
        for f in self.lyr.getFeatures():
            bb = f.geometry().boundingBox()
            bboxy.append(
                (bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()))

        kafle = kafelkowanie.pokryj_kaflami(
            bboxy, self.rozm[0], self.rozm[1])

        nowe = []
        for nr, (x0, y0, x1, y1) in enumerate(kafle, start=1):
            feat = QgsFeature()
            feat.setFields(self.pola.fields())
            feat.setGeometry(QgsGeometry.fromRect(
                QgsRectangle(x0, y0, x1, y1)))
            feat['STRONA'] = nr
            nowe.append(feat)

        self.pola.dataProvider().addFeatures(nowe)
        self.pola.commitChanges()
        return len(kafle)

    def zapisz_warstwe(self):
        # usun poprzednia warstwe z TOC (zwalnia blokade pliku na Windows)
        stare = [l for l in QgsProject.instance().mapLayers().values()
                 if l.name() == 'ATLAS_AUTO']
        if stare:
            QgsProject.instance().removeMapLayers([l.id() for l in stare])

        rozsz = ['shp', 'shx', 'dbf', 'prj', 'sbx', 'cpg', ]
        try:
            for r in rozsz:
                sciezka = os.path.join(self.kat, 'ATLAS_AUTO.' + r)
                if os.path.isfile(sciezka):
                    os.remove(sciezka)
        except:  # nopep8
            self.iface.messageBar().pushCritical(
                'BŁĄD',
                'Nie udało się usunąć poprzedniej wersji plików '
                'ATLAS_AUTO, proszę zamknąć warstwę w QGIS i ponownie '
                'uruchomić skrypt'
            )
            return False

        crs = QgsCoordinateReferenceSystem("epsg:2180")
        sciezka = os.path.join(self.kat, "ATLAS_AUTO.shp")
        QgsVectorFileWriter.writeAsVectorFormat(
            self.pola, sciezka, "UTF-8", crs, "ESRI Shapefile")

        warstwa = QgsVectorLayer(sciezka, "ATLAS_AUTO", "ogr")
        QgsProject.instance().addMapLayer(warstwa)

        plugin_dir = os.path.dirname(__file__)
        warstwa.loadNamedStyle(
            os.path.join(plugin_dir, '..', 'qml', 'ATLAS_AFT_spr.qml'))
        warstwa.triggerRepaint()
        return True

    def wyswietl_info(self, ile):
        if ile == 0:
            self.iface.messageBar().pushWarning(
                'Atlasuj automatycznie',
                'Warstwa wejściowa nie zawiera żadnych obiektów'
            )
        else:
            self.iface.messageBar().pushSuccess(
                'OK',
                'Utworzono warstwę ATLAS_AUTO z ' + str(ile) + ' polami'
            )


class PobierzDane(QDialog):
    def __init__(self):
        super(PobierzDane, self).__init__()

        self.porzuc = True
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # slownik standardowych rozmiarow papieru [szer, wys] w mm
        self.sl = {
            'A4': [210, 297],
            'A3': [297, 420],
        }

        self.rozmiar = []  # rozmiar papieru w mm
        self.wynik = []  # rozmiar kafla w metrach

        self.ui.pushButton_ok.clicked.connect(self.zatwierdz)
        self.ui.pushButton_porzuc.clicked.connect(self.porzucone)

    def porzucone(self):
        self.hide()

    def zatwierdz(self):
        if self.odczytaj_rozmiar():
            if self.obl_rozm():
                self.porzuc = False
                self.hide()

    def odczytaj_rozmiar(self):
        tekst = ''
        if self.ui.radioButton_a4.isChecked():
            self.rozmiar = self.sl['A4']
        if self.ui.radioButton_a3.isChecked():
            self.rozmiar = self.sl['A3']
        if self.ui.radioButton_inny.isChecked():
            rozm = self.ui.lineEdit_inny.text()
            if 'x' in rozm:
                w = rozm.split('x')
                if len(w) != 2:
                    tekst = 'Powinien być tylko JEDEN x!!!'
                elif w[0].isdigit() and w[1].isdigit():
                    self.rozmiar = [int(w[0]), int(w[1])]
                else:
                    tekst = 'Podany rozmiar nie składa się z samych cyfr ' \
                        'oddzielonych x'
            else:
                tekst = 'rozmiar powinien składać się z liczb całkowitych ' \
                    'oddzielonych x'

        if tekst == '':
            return True
        else:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText(tekst)
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

            return False

    def obl_rozm(self):
        # oblicz rozmiar kafla w metrach na podstawie formatu i skali

        skala = self.ui.lineEdit_skala.text()
        if not skala.isdigit():
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Skala ma być liczbą całkowitą!!!')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

            return False

        papier = list(self.rozmiar)
        if not self.ui.radioButton_inny.isChecked() and \
                self.ui.radioButton_poziom.isChecked():
            papier = papier[::-1]

        self.wynik = kafelkowanie.rozmiar_kafla_z_skali(papier, int(skala))

        if self.wynik[0] < 1 or self.wynik[1] < 1:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Wymiary mają być większe od zera!!!')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()
            return False

        return True
