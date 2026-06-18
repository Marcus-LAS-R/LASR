import os
import glob

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsMessageLog, QgsProcessingOutputLayerDefinition
)
from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox, \
    QTableWidgetItem
from qgis.PyQt.QtCore import Qt
import processing
from qgis.utils import iface

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'ui_konwertuj_shp.ui'))
project = QgsProject.instance()


class KonwertujWarstwy(QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        super(KonwertujWarstwy, self).__init__(parent)
        self.setupUi(self)
        self.sl = {}

    def ustaw_dialog(self):
        self.resetuj_tabele()
        self.pushButton_in.clicked.connect(lambda: self.pobierz_sciezke('in'))
        self.pushButton_out.clicked.connect(
            lambda: self.pobierz_sciezke('out'))
        self.pushButton_zaznacz_all.clicked.connect(
            lambda: self.ustaw_wartosc('TAK'))
        self.pushButton_odznacz_all.clicked.connect(
            lambda: self.ustaw_wartosc('NIE'))
        self.pushButton_ok.clicked.connect(self.konwertuj)

    def resetuj_tabele(self):
        self.sl = {}
        headers = ['Z', 'Warstwa | (zadeklarowany układ wspł.)']
        table = self.tableWidget
        table.clear()
        table.setColumnCount(2)
        table.setRowCount(0)
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)

    def pobierz_sciezke(self, typ):
        sc = QFileDialog.getExistingDirectory(
            self, "Wybierz katalog")
        if not sc:
            return

        if typ == 'out':
            self.lineEdit_out.setText(sc)
            return

        self.lineEdit_in.setText(sc)
        self.wczytaj_warstwy(sc)

    def wczytaj_warstwy(self, sc):
        """Pobierz wszystkie shp z podanego katalogu, sprawdz jaki maja uklad
        wspl i dodaj do table widgeta
        """
        trig = False
        lista = glob.glob(os.path.join(sc, '*.shp'))
        if len(lista) == 0:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText(
                'Brak warstw shp w podanym katalogu!')
            message.addButton("Zamknij", QMessageBox.ActionRole)
            message.exec_()
            self.resetuj_tabele()
            return

        self.tableWidget.setRowCount(len(lista))
        for row, it in enumerate(lista):
            lyr = QgsVectorLayer(it, 'wtemp', 'ogr')
            if not lyr.isValid():
                continue

            name = it.split(os.sep)[-1][:-4]
            crs = lyr.crs().authid()
            crs = crs if crs != '' else 'unknown'
            if crs == 'unknown':
                trig = True

            item = QTableWidgetItem()
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            if crs != 'unknown':
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
            self.tableWidget.setItem(row, 0, item)

            item2 = QTableWidgetItem(f'{name} | ({crs})')
            self.tableWidget.setItem(row, 1, item2)

            self.sl[f'{name} | ({crs})'] = it

        self.tableWidget.resizeColumnsToContents()

        if trig:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('UWAGA')
            message.setText(
                'Znaleziono warstwy bez zadeklarowanego układu '
                'współrzędnych.\nPrzed konwersją zaznacz je i wybierz dla '
                'nich poprawny "Układ wejściowy" — zostanie im przypisany '
                'przed reprojekcją.')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

    def pobierz_zaznaczone_warstwy(self):
        """ pobierz liste zaznaczonych warstw"""
        lista = []
        for row in range(self.tableWidget.rowCount()):
            item = self.tableWidget.item(row, 0)
            if item.checkState():
                lista.append(self.tableWidget.item(row, 1).text())

        return lista

    def ustaw_wartosc(self, val):
        """Zanznacz lub odznacz wszystki"""
        if val == 'TAK':
            state = Qt.Checked
        else:
            state = Qt.Unchecked
        for row in range(self.tableWidget.rowCount()):
            new_item = QTableWidgetItem()
            new_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            new_item.setCheckState(state)
            self.tableWidget.setItem(row, 0, new_item)

    def konwertuj(self):
        zaz = self.pobierz_zaznaczone_warstwy()
        if not os.path.exists(self.lineEdit_out.text()):
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Ścieżka do eksportowania jest niepoprawna')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()
            return

        if len(zaz) == 0:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText(
                'Zaznacz przynajmniej jedną warstwę aby kontynuować,\n'
                'albo anuluj.')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()
            return

        folder_in = os.path.normcase(os.path.abspath(self.lineEdit_in.text()))
        folder_out = os.path.normcase(os.path.abspath(self.lineEdit_out.text()))
        if folder_in == folder_out:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText(
                'Katalog docelowy musi być inny niż katalog z warstwami '
                'źródłowymi (zapis nadpisałby wczytywany plik).')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()
            return

        crs_to = self.comboBox_crs.currentText().split('(')[-1][:-1]
        crs_in = self.comboBox_crs_in.currentText().split('(')[-1][:-1]

        bledy = []
        for zz in zaz:
            pth = self.sl[zz]
            try:
                if zz.endswith('(unknown)'):
                    pth = processing.run(
                        'native:assignprojection',
                        {
                            'INPUT': pth,
                            'CRS': crs_in,
                            'OUTPUT': 'TEMPORARY_OUTPUT',
                        }
                    )['OUTPUT']

                output_def = QgsProcessingOutputLayerDefinition(
                    os.path.join(
                        self.lineEdit_out.text(), zz.split(' | ')[0]+'.shp'
                    )
                )
                output_def.createOptions = {'fileEncoding': 'UTF-8'}
                params = {
                    'INPUT': pth,
                    'OUTPUT': output_def,
                    'TARGET_CRS': crs_to,
                }
                processing.run('native:reprojectlayer', params)
            except Exception as e:
                bledy.append(zz)
                QgsMessageLog.logMessage(
                    f'Błąd reprojekcji warstwy {zz}: {e}', 'Las-R'
                )

        ile_ok = len(zaz) - len(bledy)
        if bledy:
            iface.messageBar().pushWarning(
                'Uwaga',
                f'Przetworzono {ile_ok}/{len(zaz)} warstw. Nie udało się: '
                + ', '.join(b.split(' | ')[0] for b in bledy)
                + ' (szczegóły w logu komunikatów "Las-R")')
        else:
            iface.messageBar().pushSuccess(
                'Sukces', f'Przetworzono {ile_ok} warstw')
        self.accept()
        self.hide()
