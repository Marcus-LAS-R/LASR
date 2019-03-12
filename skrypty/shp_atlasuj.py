import os
from qgis.core import QgsField, QgsVectorLayer, QgsPointXY, QgsGeometry, Qgis,\
    QgsFeature, QgsCoordinateReferenceSystem, QgsVectorFileWriter, QgsProject
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QDialog, QMessageBox
from .ui.ui_atlasuj import Ui_Dialog


class GenerujAtlas():
    def __init__(self, iface):
        self.iface = iface
        self.lyr = False
        self.rozm = []  # tablica z rozmiarem pola atlasowego w metrach x, y

    def wybierz_warstwe(self, lyr=False):
        try:
            if lyr is False:
                self.lyr = self.iface.activeLayer()
            else:
                self.lyr = lyr
            self.kat = os.path.dirname(
                self.lyr.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            return False

        return True

    def stworz_warstwy(self):
        if self.lyr is False:
            return False

        # pola atlasu do ustawienia i zanumerowania
        self.pola = QgsVectorLayer("Polygon?crs=epsg:2180&index=yes",
                                   "ATLAS_AFT",
                                   "memory")
        self.polaPr = self.pola.dataProvider()
        self.pola.startEditing()
        self.polaPr.addAttributes([
            QgsField("STRONA", QVariant.Int),
            QgsField("L", QVariant.Int),
            QgsField("G", QVariant.Int),
            QgsField("P", QVariant.Int),
            QgsField("D", QVariant.Int),
            ])
        self.pola.updateFields()
        self.pola.commitChanges()

        # Linia do numerowania kolejnych pol w atlasie, zamiast wpisywania
        # recznego
        self.linia = QgsVectorLayer("LineString?crs=epsg:2180&index=yes",
                                    "AtlasLinia",
                                    "memory")
        self.liniaPr = self.linia.dataProvider()

    def pobierz_dane(self):
        """ Metoda pobiera dane od użytkownika i na podstawie danych
        generuje pola o odpowiednich rozmiarach
        """
        self.d = PobierzDane()
        self.d.exec_()

        if self.d.porzuc:
            return False

        self.rozm = self.d.wyn
        return True

    def generuj_pola(self):
        # pobierz rozmiary warstwy którą będziemy atlasować
        xmin = self.lyr.extent().xMinimum()
        xmax = self.lyr.extent().xMaximum()
        ymin = self.lyr.extent().yMinimum()
        ymax = self.lyr.extent().yMaximum()

        self.pola.startEditing()
        x = xmin
        y = ymin
        polaPoly = []
        while x < xmax:
            while y < ymax:
                f = QgsFeature()
                f.setFields(self.pola.fields())
                poly = [
                    QgsPointXY(x, y),
                    QgsPointXY(x, y+self.rozm[1]),
                    QgsPointXY(x+self.rozm[0], y+self.rozm[1]),
                    QgsPointXY(x+self.rozm[0], y),
                    QgsPointXY(x, y),
                ]

                g = QgsGeometry().fromPolygonXY([poly])
                f.setGeometry(g)
                polaPoly.append(f)
                y += self.rozm[1]

            x += self.rozm[0]
            y = ymin

        self.pola.addFeatures(polaPoly)
        self.pola.commitChanges()

    def zapisz_warstwy(self):
        crs = QgsCoordinateReferenceSystem("epsg:2180")
        QgsVectorFileWriter.writeAsVectorFormat(
            self.pola,
            os.path.join(os.path.join(self.kat, "ATLAS_AFT.shp")),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        print(self.kat)
        self.atlasF = QgsVectorLayer(
            os.path.join(self.kat, "ATLAS_AFT.shp"), "ATLAS_AFT", "ogr")

        QgsProject.instance().addMapLayer(self.atlasF)
        QgsProject.instance().addMapLayer(self.linia)

        plugin_dir = os.path.dirname(__file__)
        self.atlasF.loadNamedStyle(
            os.path.join(plugin_dir, '..', 'qml', 'ATLAS_AFT_spr.qml'))
        self.linia.loadNamedStyle(
            os.path.join(plugin_dir, 'qml', '..', 'ATLAS_LINIA.qml'))


class Zanumeruj():
    def __init__(self, iface):
        self.iface = iface

    def wczytaj_warstwy(self):
        try:
            lyrs = [x for x in QgsProject.instance().mapLayers().values()]
            pola = [x for x in lyrs if
                    x.name()[:8].upper() == 'ATLAS_AFT']
            lin = [x for x in lyrs if
                   x.name()[:8].upper() == 'ATLAS_LIN']

            if len(pola) != 1 and len(lin) != 1:
                return False

            self.pola = pola[0]
            self.lin = lin[0]
            if self.pola.isvalid() and self.lin.isvalid():
                return True

        except:  # nopep8
            pass

        self.iface.messageBar().pushMessage(
            "BŁĄD",
            'W TOC powinny znajdować się po jednej warstwie z nazwą z '
            'nawiasu [ATLAS_AFT, ATLAS_LINIA]',
            Qgis.Critical,
            0
        )
        return False

    def sprawdz_warstwy(self):
        """ Sprawdza czy w warstwie liniowej jest tylko jedna linia i ma tyle
        wierzhołków co pól w atlasie
        """
        if self.lin.featureCount() != 1:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'W warstwie liniowej powinna znajdować się tylko jedna linia',
                Qgis.Critical,
                0
            )
            return False

        linia = next(self.lin.getFeatures())
        if self.wydz.featureCount() != linia:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Linia powinna mieć tyle wierzchołków ile jest  pól w atlasie',
                Qgis.Critical,
                0
            )
            return False


class PobierzDane(QDialog):
    def __init__(self):
        super(PobierzDane, self).__init__()

        self.porzuc = True
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # slownik standardowych rozmiarow papieru
        self.sl = {
            'A4': [210, 297],
            'A3': [297, 410],
        }

        # rozmiar i uklad wybrany przez uzyszkodnika, przeliczony do
        # odpowiedzneij skali z zostawieniem 1cm na zakladke z kazdej strony
        self.rozmiar = []  # rozmiar kafla w mm
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
        if self.ui.radioButton_a3.isChecked():
            self.rozmiar = self.sl['A3']
        if self.ui.radioButton_a4.isChecked():
            self.rozmiar = self.sl['A4']
        if self.ui.radioButton_inny.isChecked():
            rozm = self.ui.lineEdit_inny.text()
            if 'x' in rozm:
                w = rozm.split('x')
                if len(w) != 2:
                    tekst = 'Powinien być tylko JEDEN x!!!'
                elif w[0].isdigit() and w[1].isdigit():
                    self.rozmiar = [int(rozm[0]), int(rozm[1])]
                    self.uklad = ''
                else:
                    tekst = 'Podany rozmiar nie składa się z samych cyfr ' + \
                        'oddzielonych x'
            else:
                tekst = 'rozmiar powinien składać się z liczb całkowitych ' +\
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
        # oblicz rozmiar prostokątu do wygenerowania jako pole atlasowe

        skala = self.ui.lineEdit_skala.text()
        if not skala.isdigit():
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Skala ma być liczbą całkowitą!!!')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

            return False

        self.wyn = [
            (((self.rozmiar[0]-30)/10)*int(skala))/100,
            (((self.rozmiar[1]-30)/10)*int(skala))/100,
        ]

        if not self.ui.radioButton_inny.isChecked():
            if self.rozmiar[0] in [210, 297] and \
                    self.ui.radioButton_poziom.isChecked():
                self.wyn = self.wyn[::-1]

        print(self.wyn)
        return True
