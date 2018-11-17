from datetime import datetime
import os
import platform
import glob
from qgis.core import QgsMessageLog, Qgis, QgsFillSymbol, QgsProject, \
    QgsPrintLayout, QgsLayoutSize, QgsLayoutItemShape, QgsLayoutItemLabel, \
    QgsUnitTypes, QgsLayoutPoint, QgsLayoutItem, QgsLayoutItemPicture
from PyQt5.QtWidgets import QDialog, QFileDialog, QTableWidgetItem, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

from .baza_wrapper import Baza

from ..ui.ui_naklejki_dialog import Ui_DialogNaklejki
from ..ui.ui_naklejki_tomy import Ui_DialogTomy


class GenerujNaklejki:
    def __init__(self, iface):
        self.iface = iface
        self.tomy_sl = {}  # slownik z ilością tomów dla kazdego z opracowan

        # LayoutManager - obsluga layoutow
        self.mn = QgsProject.instance().layoutManager()

        # przesuniecie ustawiane przez skrypt gdy nazwa obrebu
        # jest dluzsza niz standard ustawiony przy generowanie grzebietu
        self.poszerzenie = 0

        g = {'color': '255, 255, 255, 255', 'color_border': '0, 176, 80, 255'}
        self.g = QgsFillSymbol.createSimple(g)

        # slowniki przetrzymujace dane z bazy,
        # gggoooo: [powiatnazwa, gminanazwa, obrebnazwa]
        self.ops = {}
        self.powy = {}

        # slownik ze stanem geodezji na, ggg: "ddmmrrrr"
        self.geod = {}

        self.sl_typ = {
            'ISL': [u'Inwentaryzacja Stanu Lasu',
                    u'Inwentaryzacja Stanu Lasu'],
            'UPUL': [u'Uproszczony Plan Urządzenia Lasu',
                     u'Uproszczone Plany Urządzenia Lasu'],
            'ANEKS': [u'Aneks', u'Aneks'],
        }

    def inne_layouty(self):
        """Metoda sprawdza czy w otwarym projekcie sa już jakieś layouty,
        jeżeli tak pyta użytkownika czy chce kontynuować.
        Zwraca True/False"""

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
                return True
            return False

    def pobierz_dane(self):
        """Metoda pobiera od uzytkownika sciezke do baz, oraz informacje o
        rodzaju opracowania i tomach"""

        self.info = PobierzDane()
        self.info.exec_()

        if not self.info.go_flag:
            return False

        # postawowe zmienne pobrane od uzyszkodnika
        self.od = self.info.lineEdit_od.text()
        self.do = self.info.lineEdit_do.text()
        self.typ = self.info.comboBox_typ.currentText()
        self.kat = self.info.lineEdit_sciezka.text()
        self.tomy = self.info.checkBox_tomy.isChecked()
        self.polacz = False

        self.plyta = self.info.checkBox_plyta.isChecked()
        self.okladka = self.info.checkBox_okladka.isChecked()
        self.naklejki = self.info.checkBox_naklejki.isChecked()

        if self.info.checkBox_polacz.isEnabled():
            self.polacz = self.info.checkBox_polacz.isChecked()
        self.nag_raw = []
        self.pow_raw = []

        # czy udalo sie pobrac jakies dane z baz
        if not self.polacz_z_baza():
            return False

        for n in self.nag_raw:
            if self.typ == 'UPUL' or \
                    (self.typ == 'ISL' and not self.polacz):

                nobr = '_'.join(n[-2:])+' '+self.sl_obr['_'.join(n[-2:])]
                if nobr not in self.tomy_sl:
                    self.tomy_sl[nobr] = 1
                else:
                    QgsMessageLog.logMessage(
                        u'zdublowany rekord obrębu, '
                        '(2 bazy z tego samego obiektu?): ' +
                        nobr,
                        "LasR",
                        Qgis.Warning)

            if self.typ == 'ISL' and self.polacz:
                ngm = n[4] + ' ' + self.sl_gminy[n[4]]
                if ngm not in self.tomy_sl:
                    self.tomy_sl[ngm] = 1

        # jezeli uzyszkodnik zaznaczyl ze ma wiele tomow niech wprowadzi
        if self.tomy:
            tomy_gui = Tomowanie(self.tomy_sl)
            tomy_gui.exec_()

            if tomy_gui.go_flag:
                self.tomy_sl = tomy_gui.sl

                zloz = [key+'\t['+str(v)+' t.]' for key, v in
                        self.tomy_sl.items() if int(v) > 1]
                QgsMessageLog.logMessage('Opracowań z wieloma tomami: ' +
                                         str(len(zloz)) + '\n   ' +
                                         '\n   '.join(zloz),
                                         "LasR",
                                         Qgis.Info)

        if len(list(self.geod.keys())) > 0:
            QgsMessageLog.logMessage(
                'Daty ważności geodezji zapisane w bazach:\n   ' +
                '\n   '.join(['('+k+') '+self.sl_gminy[k] + ' - ' + v
                              for k, v in self.geod.items()]),
                "LasR",
                Qgis.Info)

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
                                         "LasR",
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
                        self.pow_raw += list(baza.pobierz_pow_oprac())

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
                        'LasR',
                        Qgis.Warning
                    )

        else:
            QgsMessageLog.logMessage(
                'Nie udało się odnaleźć baz',
                'LasR',
                Qgis.Critical
            )
            return False

        # slowniki nazw i kodow w posataci {KOD: NAZWA, ...}
        self.sl_gminy = {x[4]: x[2] for x in self.nag_raw}
        self.sl_obr = {x[4]+'_'+x[5]: x[3] for x in self.nag_raw}

        self.ops = {''.join(x[4:]): x[1:4] for x in self.nag_raw}
        self.powy = {''.join(x[:2]): x[5] for x in self.pow_raw}
        return True

    def generuj_all(self):
        """Metoda zbiorcza do generowania naklejek"""

        self.iface.messageBar().pushMessage(
            'Generowanie naklejek',
            'to potrwa kilka minut, uzbrój się w cierpliwość',
            Qgis.Warning,
            5
        )

    def gen_okladke(self):
        if 'Okładka' in [l.name() for l in self.mn.layouts()]:
            self.mn.removeLayout(self.mn.layoutByName('Okładka'))

        QgsMessageLog.logMessage(
            u'Generuj okładkę na płytkę',
            "LasR",
            Qgis.Info)

        sl = {
            1: 8.6,
            2: 11.7,
            3: 15,
            4: 17.5,
            5: 20.9,
            6: 24,
            7: 27,
            8: 30,
            9: 33,
            10: 36,
            11: 39,
            12: 41.5,
        }

        lay = QgsPrintLayout(QgsProject.instance())
        lay.initializeDefaults()
        lay.setName('Okładka')
        self.mn.addLayout(lay)

        # zielona ramka do wyciecia
        okl = QgsLayoutItemShape(lay)
        okl.attemptResize(
            QgsLayoutSize(120, 120, QgsUnitTypes.LayoutMillimeters))
        okl.attemptMove(
            QgsLayoutPoint(30, 30, QgsUnitTypes.LayoutMillimeters))
        okl.setShapeType(1)
        okl.setSymbol(self.g)
        lay.addItem(okl)

        # nazwa opracowania
        naz = QgsLayoutItemLabel(lay)
        naz.setReferencePoint(QgsLayoutItem.UpperMiddle)
        naz.attemptResize(
            QgsLayoutSize(110, 15.1, QgsUnitTypes.LayoutMillimeters))
        naz.attemptMove(
            QgsLayoutPoint(90, 29.8, QgsUnitTypes.LayoutMillimeters))
        naz.setHAlign(Qt.AlignCenter)
        naz.setText(self.sl_typ[self.typ][1])
        naz.setFont(QFont("Arial", 16, QFont.Bold))
        naz.setFontColor(QColor("#000000"))
        lay.addItem(naz)

        przes = 3
        obr = []
        for k in sorted(self.sl_gminy.keys()):
            # nazwa gminy
            l1 = QgsLayoutItemLabel(lay)
            l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
            l1.setText('Gmina ' + self.sl_gminy[k]+" ("+k+")")
            l1.setFont(QFont("Arial", 12, QFont.Bold))
            l1.setFontColor(QColor("#000000"))
            l1.setHAlign(Qt.AlignCenter)
            l1.attemptResize(
                QgsLayoutSize(110, 6.73, QgsUnitTypes.LayoutMillimeters))
            l1.attemptMove(
                QgsLayoutPoint(90,
                               38+przes,
                               QgsUnitTypes.LayoutMillimeters))
            lay.addItem(l1)
            przes += 5

            # nazwy obrebow
            obr = [ko[4:]+' '+v for ko, v in self.sl_obr.items()
                   if ko[:3] == k]
            l1 = QgsLayoutItemLabel(lay)
            l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
            l1.setText(', '.join(sorted(obr)))
            l1.setFont(QFont("Arial", 8, QFont.Normal))
            l1.setFontColor(QColor("#000000"))
            l1.setHAlign(Qt.AlignCenter)
            l1.setMarginX(0)
            l1.setMarginY(0)
            l1.attemptResize(
                QgsLayoutSize(110, 5.2,
                              QgsUnitTypes.LayoutMillimeters))
            l1.attemptMove(
                QgsLayoutPoint(90, 38.2+przes,
                               QgsUnitTypes.LayoutMillimeters))
            l1.setHAlign(Qt.AlignCenter)
            l1.adjustSizeToText()

            if l1.boundingRect().width() // 110 > 0:
                l1.setHAlign(Qt.AlignCenter)
                l1.attemptResize(QgsLayoutSize(
                    110,
                    sl[l1.boundingRect().width()//100],
                    QgsUnitTypes.LayoutMillimeters))
                l1.attemptMove(
                    QgsLayoutPoint(90, 38.2+przes,
                                   QgsUnitTypes.LayoutMillimeters))
            else:
                l1.setHAlign(Qt.AlignCenter)
                l1.attemptResize(
                    QgsLayoutSize(110, 5.2,
                                  QgsUnitTypes.LayoutMillimeters))
                l1.attemptMove(
                    QgsLayoutPoint(90, 38.2+przes,
                                   QgsUnitTypes.LayoutMillimeters))

            lay.addItem(l1)
            przes += l1.boundingRect().height() - 3

        # okres obowiazywania
        przes += 5
        l2 = QgsLayoutItemLabel(lay)
        l2.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l2.setText("Plany na okres: "+str(self.od)+" - "+str(self.do))
        l2.setFont(QFont("Arial", 12, QFont.Bold))
        l2.setFontColor(QColor("#000000"))
        l2.setMarginX(0)
        l2.setMarginY(0)
        l2.setHAlign(Qt.AlignCenter)
        l2.attemptResize(
            QgsLayoutSize(110, 7, QgsUnitTypes.LayoutMillimeters))
        l2.attemptMove(
            QgsLayoutPoint(90,
                           38+przes,
                           QgsUnitTypes.LayoutMillimeters))
        lay.addItem(l2)
        przes += 10

        # powiat
        l2 = QgsLayoutItemLabel(lay)
        l2.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l2.setText("Powiat "+list(self.ops.values())[0][0])
        l2.setFont(QFont("Arial", 16, QFont.Bold))
        l2.setFontColor(QColor("#000000"))
        l2.setMarginX(0)
        l2.setMarginY(0)
        l2.setHAlign(Qt.AlignLeft)
        l2.setVAlign(Qt.AlignVCenter)
        l2.attemptResize(
            QgsLayoutSize(40, 22, QgsUnitTypes.LayoutMillimeters))
        xpn = 121
        if przes + 38 > 121:
            xpn = 38 + przes + 5
        l2.attemptMove(
            QgsLayoutPoint(76, xpn,
                           QgsUnitTypes.LayoutMillimeters))
        lay.addItem(l2)

        # herb
        h = QgsLayoutItemPicture(lay)
        h.attemptResize(
            QgsLayoutSize(23, 30, QgsUnitTypes.LayoutMillimeters))
        ypn = 116
        if przes + 38 > 116:
            ypn = 38 + przes
        h.attemptMove(
            QgsLayoutPoint(32, ypn,
                           QgsUnitTypes.LayoutMillimeters))
        lay.addItem(h)

        # wykonawca opis
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l1.setText("Wykonawca:")
        l1.setFont(QFont("Arial", 10, QFont.Normal))
        l1.setFontColor(QColor("#000000"))
        l1.setHAlign(Qt.AlignCenter)
        l1.attemptResize(
            QgsLayoutSize(50, 5.6, QgsUnitTypes.LayoutMillimeters))
        ypn = 116
        if przes + 38 > 116:
            ypn = 38 + przes
        l1.attemptMove(
            QgsLayoutPoint(120, ypn, QgsUnitTypes.LayoutMillimeters))
        lay.addItem(l1)

        # wykonawca logo
        h = QgsLayoutItemPicture(lay)
        h.setReferencePoint(QgsLayoutItem.UpperMiddle)
        h.setPicturePath(os.path.join(
            os.path.dirname(__file__), '..', 'img', 'lasr.tif'
        ))
        h.attemptResize(
            QgsLayoutSize(36, 10, QgsUnitTypes.LayoutMillimeters))
        ypn = 121
        if przes + 38 > 121:
            ypn = 38 + przes + 7
        h.attemptMove(
            QgsLayoutPoint(120, ypn,
                           QgsUnitTypes.LayoutMillimeters))
        lay.addItem(h)

        # dofinansowal
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l1.setText("Dofinansował:")
        l1.setFont(QFont("Arial", 10, QFont.Normal))
        l1.setFontColor(QColor("#000000"))
        l1.setHAlign(Qt.AlignCenter)
        l1.attemptResize(
            QgsLayoutSize(50, 5.6, QgsUnitTypes.LayoutMillimeters))
        ypn = 130
        if przes + 38 > 130:
            ypn = 38 + przes + 19
        l1.attemptMove(
            QgsLayoutPoint(120, ypn, QgsUnitTypes.LayoutMillimeters))
        lay.addItem(l1)

        # dofinansował logo
        h = QgsLayoutItemPicture(lay)
        h.setReferencePoint(QgsLayoutItem.UpperMiddle)
        h.attemptResize(
            QgsLayoutSize(42, 15, QgsUnitTypes.LayoutMillimeters))
        ypn = 136
        if przes + 38 > 136:
            ypn = 38 + przes + 7
        h.attemptMove(
            QgsLayoutPoint(120, ypn,
                           QgsUnitTypes.LayoutMillimeters))
        lay.addItem(h)


class PobierzDane(QDialog, Ui_DialogNaklejki):
    def __init__(self):
        super(PobierzDane, self).__init__(None)
        self.setupUi(self)
        self.go_flag = False
        self.lineEdit_sciezka.setText('/home/qnox/upul/testy/grabica/')

        self.pushButton_wybierz.clicked.connect(self.pobierz_katalog)
        self.buttonBox.accepted.connect(self.ok)
        self.comboBox_typ.currentIndexChanged.connect(self.zmiana_typu)

        self.lineEdit_do.setText('31.12.'+str(
            datetime.now().year+10
        ))
        self.lineEdit_od.setText('01.01.'+str(
            datetime.now().year+1
        ))

    def ok(self):
        self.go_flag = True

    def zmiana_typu(self):
        if self.comboBox_typ.currentText() == 'ISL':
            self.checkBox_polacz.setEnabled(True)
        else:
            self.checkBox_polacz.setEnabled(False)

        if self.comboBox_typ.currentText() == 'ANEKS':
            self.checkBox_tomy.setEnabled(False)
        else:
            self.checkBox_tomy.setEnabled(True)

    def pobierz_katalog(self):
        plik = QFileDialog.getExistingDirectory(
            self,
            'Katalog z bazami TPU',
            '', QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        self.lineEdit_sciezka.setText(plik)


class Tomowanie(QDialog, Ui_DialogTomy):
    def __init__(self, sl):
        super(Tomowanie, self).__init__(None)

        self.sl = sl
        self.setupUi(self)
        self.go_flag = False

        self.buttonBox.accepted.connect(self.ok)

        self.tableWidget.clear()
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(['Obiekt', 'Tomy'])
        self.tableWidget.setRowCount(len(list(self.sl.keys())))
        self.tableWidget.setAlternatingRowColors(True)

        for i, key in enumerate(sorted(list(self.sl.keys()))):
            self.tableWidget.setItem(
                i,
                0,
                QTableWidgetItem(key)
            )

            self.tableWidget.setItem(
                i,
                1,
                QTableWidgetItem(str(self.sl[key]))
            )

        self.tableWidget.resizeColumnsToContents()

        self.buttonBox.accepted.connect(self.ok)

    def ok(self):
        self.go_flag = True

        ilew = self.tableWidget.rowCount()
        for i in range(ilew):
            kod = self.tableWidget.item(i, 0)
            it = self.tableWidget.item(i, 1)
            if it.text().isdigit():
                if int(it.text()) > 1:
                    self.sl[str(kod.text())] = int(it.text())
