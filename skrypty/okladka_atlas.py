from datetime import datetime
import os
import platform
import glob
from qgis.core import QgsMessageLog, Qgis, QgsFillSymbol, QgsProject, \
    QgsPrintLayout, QgsLayoutSize, QgsLayoutItemShape, QgsLayoutItemLabel, \
    QgsUnitTypes, QgsLayoutPoint, QgsLayoutItem, QgsLayoutItemPicture, \
    QgsLayoutItemPage
from PyQt5.QtWidgets import QDialog, QFileDialog, QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from .pw import PasekPostepu
from .baza_wrapper import Baza

from qgis.PyQt.uic import loadUiType

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui',  'ui_okladki_dialog.ui'))


class GenerujOkladki:
    def __init__(self, iface):
        self.iface = iface

        self.mn = QgsProject.instance().layoutManager()

        # przesuniecie ustawiane przez skrypt gdy nazwa obrebu
        # jest dluzsza niz standard ustawiony przy generowanie grzebietu
        self.poszerzenie = 0
        self.geod = {}  # {MUNICIPALITY_CD: data_stanu_ewid}

        g = {'color': '255, 255, 255, 255', 'color_border': '0, 176, 80, 255'}
        self.g = QgsFillSymbol.createSimple(g)

        self.sl_typ = {
            'ISL': ['Inwentaryzacja Stanu Lasu',
                    'Inwentaryzacja Stanu Lasu'],
            'UPUL': ['Uproszczony Plan Urządzenia Lasu',
                     'Uproszczony Plan Urządzenia Lasu\nWłasności osób fizycznych'],
            'ANEKS': ['Aneks', 'Aneks'],
        }

        self.sl_nfosigw = {
            1: 'WFOSIGW_podlaskie.jpg',
            2: 'WFOSIGW_pomorskie.jpg',
            3: 'WFOSIGW_slaskie.jpg',
            4: 'WFOSIGW_swietokrzyskie.jpg',
            5: 'WFOSIGW_malopolskie.jpg',
            6: 'WFOSIGW_lodzkie.jpg',
            7: 'WFOSIGW_lubelskie.jpg',
            8: 'WFOSIGW_warminsko-mazurskie.jpg',
            9: 'WFOSIGW_opolskie.jpg',
            10: 'WFOSIGW_wielkopolskie.jpg',
            11: 'WFOSIGW_podkarpackie.jpg',
            12: 'WFOSIGW_zachodnio-pomorskie.jpg',
            13: 'WFOSIGW_kujawsko-pomorskie.jpg',
            14: 'WFOSIGW_mazowieckie.jpg',
            15: 'WFOSIGW_dolnoslaskie.jpg',
            16: 'WGOSIGW_lubuskie.jpg',
        }

    def inne_layouty(self):
        """Metoda sprawdza czy w otwarym projekcie sa już jakieś layouty,
        jeżeli tak pyta użytkownika czy chce kontynuować.
        Zwraca True/False"""

        self.postep = PasekPostepu(self.iface).stworz_pasek(
            'Generowanie wybranych raportów'
        )
        self.postep.setValue(5)

        if len(self.mn.layouts()) == 0:
            return False
        else:
            m = QMessageBox()
            m.setText(
                'W otwartym projekcie wykryto layouty, '
                'istnieje możliwość ich nadpisania, kontynuować?')
            m.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            m.exec_()

            if m == QMessageBox.No:
                self.iface.messageBar().clearWidgets()
                return True
            return False

    def pobierz_dane(self):  # noqa
        """Metoda pobiera od uzytkownika sciezke do baz, oraz informacje o
        rodzaju opracowania i tomach"""

        self.info = PobierzDane()
        self.info.exec_()

        if not self.info.go_flag:
            self.iface.messageBar().clearWidgets()
            return False

        # postawowe zmienne pobrane od uzyszkodnika
        self.od = self.info.lineEdit_od.text()
        self.do = self.info.lineEdit_do.text()
        self.typ = self.info.comboBox_typ.currentText()
        self.kat = self.info.lineEdit_sciezka.text()

        self.nag_raw = []
        self.pow_raw = []

        # czy udalo sie pobrac jakies dane z baz
        if not self.polacz_z_baza():
            return False

        # for n in self.nag_raw:
            # nobr = '_'.join(n[-2:])+' '+self.sl_obr['_'.join(n[-2:])]
            # if nobr not in self.tomy_sl:
                # self.tomy_sl[nobr] = 1
            # else:
                # QgsMessageLog.logMessage(
                    # 'zdublowany rekord obrębu, '
                    # '(2 bazy z tego samego obiektu?): ' +
                    # nobr,
                    # "Las-R", Qgis.Warning)

        self.postep.setValue(15)
        return True

    def znajdz_bazy(self):
        """Metoda szuka w podanej scieżce baz w zależności od systemu"""

        try:
            if platform.system()[:3] == 'Win':
                self.bazy = glob.glob(os.path.join(self.kat, "*.mdb"))
            else:
                self.bazy = glob.glob(os.path.join(self.kat, "*.sqlite"))

            if len(self.bazy) > 0:
                QgsMessageLog.logMessage(u'Odnalazłem baz: ' +
                                         str(len(self.bazy)),
                                         "Las-R",
                                         Qgis.Info)
                return True
            return False
        except:  # nopep8
            return False

    def polacz_z_baza(self):
        """Metoda zbiorcza do pobrania danych z baz i przetworzenia do
        odpowiednich struktur"""

        if self.znajdz_bazy():
            for b in self.bazy:
                baza = Baza(b)

                try:
                    if baza.polacz():
                        self.nag_raw += list(baza.pobierz_naglowek())

                        # sqlite date zwraca jako tekst :/
                        try:
                            self.geod[self.nag_raw[-1][4]] = \
                                baza.pobierz_daty_waznosci(
                                    )[0][2].strftime("%d.%m.%Y")
                        except:  # nopep8
                            data = baza.pobierz_daty_waznosci(
                                )[0][2]
                            self.geod[self.nag_raw[-1][4]] = \
                                data[:6].replace('/', '.') + '20' + data[6:8]
                        baza.zamknij()

                except:  # nopep8
                    QgsMessageLog.logMessage(
                        'Nie udało się przetworzyć bazy: '+b,
                        'Las-R',
                        Qgis.Warning
                    )

        else:
            QgsMessageLog.logMessage(
                'Nie udało się odnaleźć baz',
                'Las-R',
                Qgis.Critical
            )
            return False

        # slowniki nazw i kodow w posataci {KOD: NAZWA, ...}
        self.sl_gminy = {x[4]: x[2] for x in self.nag_raw}
        self.sl_obr = {x[4]+'_'+x[5]: x[3] for x in self.nag_raw}
        self.powiat_naz = self.nag_raw[0][1]

        self.ops = {''.join(x[4:]): x[1:4] for x in self.nag_raw}
        return True

    def generuj_okladki(self):  # noqa
        if 'Okladki' in [l.name() for l in self.mn.layouts()]:
            self.mn.removeLayout(self.mn.layoutByName('Okladki'))

        lay = QgsPrintLayout(QgsProject.instance())
        lay.initializeDefaults()
        lay.setName('Okladki')
        self.mn.addLayout(lay)

        pages = lay.pageCollection()
        pages.clear()
        page = QgsLayoutItemPage(lay)
        page.setPageSize('A4', QgsLayoutItemPage.Orientation.Portrait)

        for pg, row in enumerate(self.nag_raw):
            y = 20
            page = QgsLayoutItemPage(lay)
            page.setPageSize('A4', QgsLayoutItemPage.Orientation.Portrait)
            pages.addPage(page)

            # nazwa opracowania
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(190, 20.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(10, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignCenter)
            naz.setText(self.sl_typ[self.typ][1])
            naz.setFont(QFont("Arial", 26, QFont.Bold))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            y += 30
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(190, 10.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(10, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignCenter)
            naz.setText('Atlas')
            naz.setFont(QFont("Arial", 20, QFont.Bold))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            y += 18
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(190, 10.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(10, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignCenter)
            naz.setText(f'Na okres: {self.od} r. - {self.do} r.')
            naz.setFont(QFont("Arial", 14, QFont.Normal))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            y += 20
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(108, 25.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(92, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignLeft)
            naz.setText(f'Obręb: {row[3]}')
            naz.setFont(QFont("Arial", 20, QFont.Bold))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            # herb
            h = QgsLayoutItemPicture(lay)
            h.setReferencePoint(QgsLayoutItem.UpperLeft)
            h.setPicturePath(self.info.lineEdit_herb.text())
            h.attemptResize(
                QgsLayoutSize(46, 58, QgsUnitTypes.LayoutMillimeters))
            h.attemptMove(
                QgsLayoutPoint(38, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            lay.addItem(h)

            y += 25
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(108, 25.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(92, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignLeft)
            naz.setText(f'Gmina: {row[2]}')
            naz.setFont(QFont("Arial", 20, QFont.Normal))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            y += 25
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(108, 15.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(92, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignLeft)
            naz.setText(f'Powiat: {row[1]}')
            naz.setFont(QFont("Arial", 20, QFont.Normal))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            y += 15
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(108, 15.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(92, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignLeft)
            naz.setText(f'Województwo: {row[0]}')
            naz.setFont(QFont("Arial", 20, QFont.Normal))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            if self.info.checkBox_ewid.isChecked():
                y += 12
                naz = QgsLayoutItemLabel(lay)
                naz.setReferencePoint(QgsLayoutItem.UpperLeft)
                naz.attemptResize(
                    QgsLayoutSize(190, 8, QgsUnitTypes.LayoutMillimeters))
                naz.attemptMove(
                    QgsLayoutPoint(10, y, QgsUnitTypes.LayoutMillimeters),
                    page=pg)
                naz.setHAlign(Qt.AlignCenter)
                naz.setText(
                    'Stan ewidencji gruntów: ' + self.geod.get(row[4], ''))
                naz.setFont(QFont("Arial", 10, QFont.Normal))
                naz.setFontColor(QColor("#000000"))
                lay.addItem(naz)
                y += 18
            else:
                y += 30
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(190, 5.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(10, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignCenter)
            naz.setText('Wykonawca:')
            naz.setFont(QFont("Arial", 10, QFont.Normal))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            # logo
            y += 6
            h = QgsLayoutItemPicture(lay)
            h.setReferencePoint(QgsLayoutItem.UpperLeft)
            h.setPicturePath(os.path.join(
                os.path.dirname(__file__), '..', 'img', 'logo.png'
            ))
            h.attemptResize(
                QgsLayoutSize(38.0, 16, QgsUnitTypes.LayoutMillimeters))
            h.attemptMove(
                QgsLayoutPoint(87.6, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            lay.addItem(h)

            y += 20
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(190, 20.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(6, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignCenter)
            naz.setText('LAS-R Sp z o.o.')
            naz.setFont(QFont("Arial", 11, QFont.Bold))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            y += 5
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(190, 20.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(10, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignCenter)
            naz.setText('ul.Snycerska 34/13, 30-817 Kraków\nbiuro@las-r.pl             www.las-r.pl')
            naz.setFont(QFont("Arial", 10, QFont.Normal))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            # sponsoring
            if not self.info.checkBox_pgllp.isChecked() and \
                    self.info.comboBox_nfosigw.currentIndex() == 0:
                # nie ma sponsora
                continue

            y += 30
            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperLeft)
            naz.attemptResize(
                QgsLayoutSize(190, 10.1, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(10, y, QgsUnitTypes.LayoutMillimeters), page=pg)
            naz.setHAlign(Qt.AlignCenter)
            naz.setText('Dofinansowano ze środków:')
            naz.setFont(QFont("Arial", 14, QFont.Bold))
            naz.setFontColor(QColor("#000000"))
            lay.addItem(naz)

            y += 10
            if self.info.checkBox_pgllp.isChecked() and \
                    self.info.comboBox_nfosigw.currentIndex() > 0:
                # jest 2 sponsorow
                h = QgsLayoutItemPicture(lay)
                h.setReferencePoint(QgsLayoutItem.UpperLeft)
                h.setPicturePath(os.path.join(
                    os.path.dirname(__file__), '..', 'img',
                    self.sl_nfosigw[self.info.comboBox_nfosigw.currentIndex()]
                ))
                h.attemptResize(
                    QgsLayoutSize(90, 38, QgsUnitTypes.LayoutMillimeters))
                h.attemptMove(
                    QgsLayoutPoint(100, y,
                                   QgsUnitTypes.LayoutMillimeters), page=pg)
                h.setPictureAnchor(QgsLayoutItem.Middle)
                lay.addItem(h)

                h = QgsLayoutItemPicture(lay)
                h.setReferencePoint(QgsLayoutItem.UpperLeft)
                h.setPicturePath(os.path.join(
                    os.path.dirname(__file__), '..', 'img', 'PGLLP.jpg'
                ))
                h.attemptResize(
                    QgsLayoutSize(38, 38, QgsUnitTypes.LayoutMillimeters))
                h.attemptMove(
                    QgsLayoutPoint(46, y,
                                   QgsUnitTypes.LayoutMillimeters), page=pg)
                lay.addItem(h)
                continue

            # zostal tylko jeden sponsor
            if self.info.comboBox_nfosigw.currentIndex() > 0:
                h = QgsLayoutItemPicture(lay)
                h.setReferencePoint(QgsLayoutItem.UpperLeft)
                h.setPicturePath(os.path.join(
                    os.path.dirname(__file__), '..', 'img',
                    self.sl_nfosigw[self.info.comboBox_nfosigw.currentIndex()]
                ))
                h.attemptResize(
                    QgsLayoutSize(90, 30, QgsUnitTypes.LayoutMillimeters))
                h.attemptMove(
                    QgsLayoutPoint(60, y,
                                   QgsUnitTypes.LayoutMillimeters), page=pg)
                h.setPictureAnchor(QgsLayoutItem.Middle)
                lay.addItem(h)
                continue

            if self.info.checkBox_pgllp.isChecked():
                h = QgsLayoutItemPicture(lay)
                h.setReferencePoint(QgsLayoutItem.UpperLeft)
                h.setPicturePath(os.path.join(
                    os.path.dirname(__file__), '..', 'img', 'PGLLP.jpg'
                ))
                h.attemptResize(
                    QgsLayoutSize(38, 38, QgsUnitTypes.LayoutMillimeters))
                h.attemptMove(
                    QgsLayoutPoint(86, y,
                                   QgsUnitTypes.LayoutMillimeters), page=pg)
                lay.addItem(h)

        self.postep.setValue(100)


class PobierzDane(QDialog, FORM_CLASS):
    def __init__(self):
        super(PobierzDane, self).__init__(None)
        self.setupUi(self)
        self.go_flag = False
        self.kat = ''  # sciezka do podawania w QFileDialogu
        self.lineEdit_sciezka.setText('/Users/pawel/lasr/qgis_taksator/')

        self.pushButton_wybierz.clicked.connect(self.pobierz_katalog_tpu)
        self.pushButton_herb.clicked.connect(self.pobierz_sc_herb)
        self.buttonBox.accepted.connect(self.ok)

        self.lineEdit_do.setText('31.12.'+str(
            datetime.now().year+10
        ))
        self.lineEdit_od.setText('01.01.'+str(
            datetime.now().year+1
        ))

    def ok(self):
        self.go_flag = True

    def pobierz_sc_herb(self):
        plik, _ = QFileDialog.getOpenFileName(
            self,
            'plik z herbem',
            self.kat,
            "obrazy (*.png *.jpg *.bmp *.tif)"
        )

        if os.path.isfile(plik):
            self.lineEdit_herb.setText(plik)

    def pobierz_katalog_tpu(self):
        plik = QFileDialog.getExistingDirectory(
            self,
            'Katalog z bazami TPU',
            self.kat,
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        self.lineEdit_sciezka.setText(plik)
        self.kat = plik

        if os.path.isfile(os.path.join(plik, 'herb.png')):
            self.lineEdit_herb.setText(os.path.join(plik, 'herb.png'))
