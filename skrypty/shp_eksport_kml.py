from qgis.core import QgsProject, QgsVectorLayer, Qgis, QgsVectorFileWriter, \
    QgsCoordinateReferenceSystem
import os
import glob
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from .ui.ui_eksport_kml import Ui_Dialog
import processing


# TODO: rozbić featurki poly/line na warstwy < 2000 poligonów
class EksportujKML():
    def __init__(self, iface):
        self.iface = iface
        self.nowy_temp = True  # trig przy towrzeniu nowego katalogu temp

    def pobierzDane(self):
        """Metoda wyświetla dialog dla użytkownika a następnie przepisuje
        podane dane"""

        d = False
        k = self.iface.activeLayer()
        try:
            if not k.isValid():
                k = False
        except:  # nopep8
            pass

        for key, lyr in QgsProject.instance().mapLayers().items():
            if key[:5] == 'DZKAT':
                d = lyr

        self.dd = PobierzDane(k, d)
        self.dd.exec_()

        if self.dd.poprawne:
            self.ls = QgsVectorLayer(self.dd.ui.ls_sc.text(), 'ls', 'ogr')
            if not self.ls.isValid():
                self.iface.messageBar().pushMessage(
                    'LS',
                    'Niepoprawna warstwa Ls-ów',
                    Qgis.Critical,
                    15
                )
                return False

            self.dz = QgsVectorLayer(self.dd.ui.dz_sc.text(), 'dz', 'ogr')
            if not self.dz.isValid():
                self.iface.messageBar().pushMessage(
                    'LS',
                    'Niepoprawna warstwa DZKAT-ów',
                    Qgis.Critical,
                    15
                )
                return False

            lsc = self.ls.dataProvider().dataSourceUri().split("|")[0]
            self.kat = os.path.dirname(lsc)
            return True

        return self.dd.poprawne

    def przetworz(self):
        """ Metoda przetwarza warstwy poly na linie przy uzyciu algorytmu z
        zestawu alg sagi"""

        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)
            self.nowy_temp = True

        processing.run(
            'saga:convertpolygonstolines',
            {'POLYGONS': self.ls,
             'LINES': os.path.join(self.tempkat, '__ls_lines.shp')
             }
        )

        self.ls_lines = QgsVectorLayer(
            os.path.join(self.tempkat, '__ls_lines.shp'),
            'ls_lines',
            'ogr'
        )

        processing.run(
            'saga:convertpolygonstolines',
            {'POLYGONS': self.dz,
             'LINES': os.path.join(self.tempkat, '__dz_lines.shp')
             }
        )

        self.dz_lines = QgsVectorLayer(
            os.path.join(self.tempkat, '__dz_lines.shp'),
            'dz_lines',
            'ogr'
        )

    def zapisz_kml(self):
        """Metoda zapisuje przetworzone warstwy do plików KML"""

        crs = QgsCoordinateReferenceSystem("epsg:4326")

        try:
            for war in [[self.ls, 'LS_POL.kml'],
                        [self.dz, 'DZ_POL.kml'],
                        [self.ls_lines, 'LS_LIN.kml'],
                        [self.dz_lines, 'DZ_LIN.kml'],
                        ]:
                QgsVectorFileWriter.writeAsVectorFormat(
                    war[0],
                    os.path.join(self.kat, war[1]),
                    "UTF-8",
                    crs,
                    "KML")

            self.iface.messageBar().pushMessage(
                'OK',
                'Warstwy zapisanow w katalogu z Ls-ami',
                Qgis.Success,
                15
            )
        except:  # noqa
            self.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się zapisać KMLi, za dużo baboli...',
                Qgis.Critical,
                10
            )

        self.sprzatnij()

    def sprzatnij(self):
        """ Metoda kasuje pliki tymczasowe i proboje skasowac katalog """
        del self.dz
        del self.ls

        if self.nowy_temp:
            lista = glob.glob(os.path.join(self.tempkat, '*.*'))
        else:
            lista = glob.glob(os.path.join(self.tempkat, '__ls_lines.*'))
            lista += glob.glob(os.path.join(self.tempkat, '__dz_lines.*'))

        for ll in lista:
            os.remove(ll)

        # skasuj jeżeli katalog jest pusty
        os.removedirs(self.tempkat)


class PobierzDane(QDialog):
    def __init__(self, ls=False, dz=False):
        super(PobierzDane, self).__init__()
        self.poprawne = False
        self.kat = ''
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        if ls:
            lsc = ls.dataProvider().dataSourceUri().split("|")[0]
            self.kat = os.path.dirname(lsc)
            self.ui.ls_sc.setText(lsc)
        if dz:
            dzsc = dz.dataProvider().dataSourceUri().split("|")[0]
            self.kat = os.path.dirname(dzsc)
            self.ui.dz_sc.setText(dzsc)

        self.ui.pushButton_dz.clicked.connect(self.pobierz_dzkat)
        self.ui.pushButton_ls.clicked.connect(self.pobierz_ls)
        self.ui.ok.clicked.connect(self.zatwierdz)
        self.ui.pushButton_porzuc.clicked.connect(self.porzuc)

    def zatwierdz(self):
        self.poprawne = True
        self.hide()

    def porzuc(self):
        self.hide()

    def pobierz_dzkat(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę i ją przetwarza"""
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę DZKAT',
                                                self.kat,
                                                "ESRI shp (*.shp)")[0]
        try:
            dz = QgsVectorLayer(warstwa, "dz", "ogr")
            self.kat = os.path.dirname(
                dz.dataProvider().dataSourceUri().split("|")[0]
            )
            self.ui.dz_sc.setText(
                dz.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            msbx = QMessageBox('Nie udało się otworzyć podanej warstwy')
            msbx.exec_()

    def pobierz_ls(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę i ją przetwarza"""
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę Ls',
                                                self.kat,
                                                "ESRI shp (*.shp)")[0]
        try:
            ls = QgsVectorLayer(warstwa, "ls", "ogr")
            self.kat = os.path.dirname(
                ls.dataProvider().dataSourceUri().split("|")[0]
            )
            self.ui.ls_sc.setText(
                ls.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            msbx = QMessageBox('Nie udało się otworzyć podanej warstwy')
            msbx.exec_()
