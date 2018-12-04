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
        tomy_gui = Tomowanie(self.tomy_sl)
        if self.tomy:
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
        else:
            self.tomy_sl = tomy_gui.sl

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
        self.powiat_naz = self.nag_raw[0][1]

        self.ops = {''.join(x[4:]): x[1:4] for x in self.nag_raw}
        self.powy = {'_'.join(x[:2]): x[5] for x in self.pow_raw}
        return True

    def generuj_all(self):
        """Metoda zbiorcza do generowania naklejek"""

        self.iface.messageBar().pushMessage(
            'Generowanie naklejek',
            'to potrwa kilka minut, uzbrój się w cierpliwość',
            Qgis.Info,
            5
        )

        _ok = True
        try:
            if self.plyta:
                self.gen_plytke()
        except:  # nopep8
            _ok = False
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Coś poszło nie tak przy generowaniu naklejki na plytkę',
                Qgis.Warning,
                5
            )

        try:
            if self.naklejki:
                self.gen_naklejki()
        except:  # nopep8
            _ok = False
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Coś poszło nie tak przy generowaniu naklejek na operaty',
                Qgis.Warning,
                5
            )

        try:
            if self.okladka:
                self.gen_okladke()
        except:  # nopep8
            _ok = False
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Coś poszło nie tak przy generowaniu okładki na plytkę',
                Qgis.Warning,
                5
            )

        if _ok:
            self.iface.messageBar().pushMessage(
                'OK',
                'Pomyślnie wygenerowano zaznaczone rzeczy',
                Qgis.Success,
                5
            )

        QgsMessageLog.logMessage(
            '\n--- KONIEC ---',
            "LasR",
            Qgis.Info)

    def gen_okladke(self):  # noqa
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
                    sl[l1.boundingRect().width()//110],
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
        l2.setText("Plany na lata: "+str(self.od)+" - "+str(self.do))
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
        xpn = 116
        if przes + 38 > 116:
            xpn = 38 + przes + 5
        l2.attemptMove(
            QgsLayoutPoint(81, xpn,
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
            QgsLayoutPoint(37, ypn,
                           QgsUnitTypes.LayoutMillimeters))
        h.setPicturePath(self.info.lineEdit_herb.text())
        lay.addItem(h)

        # wykonawca opis
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l1.setText("Wykonawca:")
        l1.setFont(QFont("Arial", 7, QFont.Normal))
        l1.setFontColor(QColor("#000000"))
        l1.setHAlign(Qt.AlignCenter)
        l1.attemptResize(
            QgsLayoutSize(50, 5.6, QgsUnitTypes.LayoutMillimeters))

        ypn = 116
        if przes + 38 > 116:
            ypn = 38 + przes

        if not self.info.checkBox_pgllp.isChecked() and \
                self.info.comboBox_nfosigw.currentIndex() == 0:
            ypn = 126
            if przes + 38 > 126:
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

        if not self.info.checkBox_pgllp.isChecked() and \
                self.info.comboBox_nfosigw.currentIndex() == 0:
            ypn = 131
            if przes + 38 > 131:
                ypn = 38 + przes

        h.attemptMove(
            QgsLayoutPoint(120, ypn,
                           QgsUnitTypes.LayoutMillimeters))
        lay.addItem(h)

        # jezeli nie ma dofinansowania konczymy
        if not self.info.checkBox_pgllp.isChecked() and \
                self.info.comboBox_nfosigw.currentIndex() == 0:
            return

        # dofinansowal
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l1.setText("Dofinansował:")
        l1.setFont(QFont("Arial", 7, QFont.Normal))
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

        if not self.info.checkBox_pgllp.isChecked() and \
                self.info.comboBox_nfosigw.currentIndex() > 0:

            # dofinansował wfosigw
            h = QgsLayoutItemPicture(lay)
            h.setReferencePoint(QgsLayoutItem.UpperMiddle)
            h.attemptResize(
                QgsLayoutSize(39.5, 13.5, QgsUnitTypes.LayoutMillimeters))
            ypn = 136
            if przes + 38 > 136:
                ypn = 38 + przes + 7
            h.attemptMove(
                QgsLayoutPoint(120, ypn,
                               QgsUnitTypes.LayoutMillimeters))
            h.setPicturePath(os.path.join(
                os.path.dirname(__file__), '..', 'img',
                self.sl_nfosigw[self.info.comboBox_nfosigw.currentIndex()]
            ))
            lay.addItem(h)

        if self.info.checkBox_pgllp.isChecked() and \
                self.info.comboBox_nfosigw.currentIndex() == 0:

            # dofinansowalo pgllp
            h = QgsLayoutItemPicture(lay)
            h.setReferencePoint(QgsLayoutItem.UpperMiddle)
            h.attemptResize(
                QgsLayoutSize(13.5, 13.5, QgsUnitTypes.LayoutMillimeters))
            ypn = 136
            if przes + 38 > 136:
                ypn = 38 + przes + 7
            h.attemptMove(
                QgsLayoutPoint(120, ypn,
                               QgsUnitTypes.LayoutMillimeters))
            h.setPicturePath(os.path.join(
                os.path.dirname(__file__), '..', 'img', 'PGLLP.jpg'
            ))
            lay.addItem(h)

        if self.info.checkBox_pgllp.isChecked() and \
                self.info.comboBox_nfosigw.currentIndex() > 0:

            # dofinansował wfosigw
            h = QgsLayoutItemPicture(lay)
            h.setReferencePoint(QgsLayoutItem.UpperMiddle)
            h.attemptResize(
                QgsLayoutSize(39.5, 13.5, QgsUnitTypes.LayoutMillimeters))
            ypn = 136
            if przes + 38 > 136:
                ypn = 38 + przes + 7
            h.attemptMove(
                QgsLayoutPoint(130, ypn, QgsUnitTypes.LayoutMillimeters))
            h.setPicturePath(os.path.join(
                os.path.dirname(__file__), '..', 'img',
                self.sl_nfosigw[self.info.comboBox_nfosigw.currentIndex()]
            ))
            lay.addItem(h)

            # dofinansowalo pgllp
            h = QgsLayoutItemPicture(lay)
            h.setReferencePoint(QgsLayoutItem.UpperMiddle)
            h.attemptResize(
                QgsLayoutSize(13.5, 13.5, QgsUnitTypes.LayoutMillimeters))
            ypn = 136
            if przes + 38 > 136:
                ypn = 38 + przes + 7
            h.attemptMove(
                QgsLayoutPoint(100, ypn, QgsUnitTypes.LayoutMillimeters))
            h.setPicturePath(os.path.join(
                os.path.dirname(__file__), '..', 'img', 'PGLLP.jpg'
            ))
            lay.addItem(h)

    def gen_plytke(self):  # noqa
        if 'Płytka' in [l.name() for l in self.mn.layouts()]:
            self.mn.removeLayout(self.mn.layoutByName('Płytka'))

        QgsMessageLog.logMessage(
            u'Generuję naklejkę na płytkę',
            "LasR",
            Qgis.Info)
        lay = QgsPrintLayout(QgsProject.instance())
        lay.initializeDefaults()
        lay.setName('Płytka')
        self.mn.addLayout(lay)

        # nazwa opracowania
        for przes in [0, 130]:
            # zielone krzyzyki do wyciecia
            okl = QgsLayoutItemShape(lay)
            okl.attemptResize(
                QgsLayoutSize(10, 2, QgsUnitTypes.LayoutMillimeters))
            okl.attemptMove(
                QgsLayoutPoint(84+przes, 88, QgsUnitTypes.LayoutMillimeters))
            okl.setShapeType(1)
            okl.setSymbol(self.g)
            lay.addItem(okl)

            okl = QgsLayoutItemShape(lay)
            okl.attemptResize(
                QgsLayoutSize(2, 10, QgsUnitTypes.LayoutMillimeters))
            okl.attemptMove(
                QgsLayoutPoint(88+przes, 84, QgsUnitTypes.LayoutMillimeters))
            okl.setShapeType(1)
            okl.setSymbol(self.g)
            lay.addItem(okl)

            naz = QgsLayoutItemLabel(lay)
            naz.setReferencePoint(QgsLayoutItem.UpperMiddle)
            naz.attemptResize(
                QgsLayoutSize(78, 14.2, QgsUnitTypes.LayoutMillimeters))
            naz.attemptMove(
                QgsLayoutPoint(89+przes, 43.1, QgsUnitTypes.LayoutMillimeters))
            naz.setHAlign(Qt.AlignCenter)
            naz.setText(self.sl_typ[self.typ][1])
            naz.setFont(QFont("Arial", 14, QFont.Bold))
            naz.setFontColor(QColor("#90bc00"))
            lay.addItem(naz)

            # lata opracowania
            l1 = QgsLayoutItemLabel(lay)
            l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
            l1.setText('Plany na lata: ' +
                       self.info.lineEdit_od.text()[-4:] + ' - ' +
                       self.info.lineEdit_do.text()[-4:])
            l1.setFont(QFont("Arial", 14, QFont.Bold))
            naz.setHAlign(Qt.AlignCenter)
            l1.setFontColor(QColor("#90bc00"))
            l1.setHAlign(Qt.AlignCenter)
            l1.attemptResize(
                QgsLayoutSize(63, 8.7, QgsUnitTypes.LayoutMillimeters))
            l1.attemptMove(
                QgsLayoutPoint(89+przes,
                               128.1,
                               QgsUnitTypes.LayoutMillimeters))
            lay.addItem(l1)

            # powiat
            l2 = QgsLayoutItemLabel(lay)
            l2.setReferencePoint(QgsLayoutItem.UpperMiddle)
            l2.setText("Powiat "+list(self.ops.values())[0][0])
            l2.setFont(QFont("Arial", 20, QFont.Bold))
            l2.setFontColor(QColor("#000000"))
            l2.setMarginX(0)
            l2.setMarginY(0)
            l2.setHAlign(Qt.AlignCenter)
            l2.setVAlign(Qt.AlignVCenter)
            l2.attemptResize(
                QgsLayoutSize(93.9, 14.2, QgsUnitTypes.LayoutMillimeters))
            l2.attemptMove(
                QgsLayoutPoint(89+przes, 59, QgsUnitTypes.LayoutMillimeters))
            lay.addItem(l2)

            # gminy
            l1 = QgsLayoutItemLabel(lay)
            l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
            l1.setText("Gminy: "+', '.join(
                sorted(list(set([x[1] for x in self.ops.values()])))))
            l1.setFont(QFont("Arial", 14, QFont.Bold))
            l1.setFontColor(QColor("#000000"))
            l1.setHAlign(Qt.AlignCenter)
            l1.attemptResize(
                QgsLayoutSize(101, 25, QgsUnitTypes.LayoutMillimeters))
            l1.attemptMove(
                QgsLayoutPoint(89+przes, 103,
                               QgsUnitTypes.LayoutMillimeters))
            lay.addItem(l1)

    def gen_naklejki(self):
        if 'Operaty' in [l.name() for l in self.mn.layouts()]:
            self.mn.removeLayout(self.mn.layoutByName('Operaty'))

        QgsMessageLog.logMessage(
            u'Generuję naklejki na operaty',
            "LasR",
            Qgis.Info)
        lay = QgsPrintLayout(QgsProject.instance())
        lay.initializeDefaults()
        lay.setName('Operaty')
        self.mn.addLayout(lay)

        # przesuniecia dla kafelkow i grzebietow
        xprzes = [0, 125, 0, 125]
        yprzes = [0, 80, 80, 0]
        xprzes2 = [0, 60, 120, 180]

        # rozpocznij managera stron i dodaj pierwsza strone
        # pages = QgsLayoutPageCollection(lay)
        pages = lay.pageCollection()
        pages.clear()

        page = QgsLayoutItemPage(lay)
        page.setPageSize(QgsLayoutSize(297, 210))
        pages.addPage(page)

        tab = []  # TODO: tabela z pogrupowanymi danymi
        # kolejnosc danych w tabeli:
        # 0 - przesuniecie px
        # 1 - przesunieceie py
        # 2 - stron w opracowaniu
        # 3 - nazwa obiektu razem z przydomkiem
        # 4 - nazwa gminy, jezeil nie ma zostaw ''
        # 5 - nazwa powiatu
        # 6 - pelny opis okresu obowiazywania planow
        # 7 - powierzchnia z opisem
        # 8 - stan na
        # 9 - tom opracowania jako int
        si = 0
        for k, val in self.tomy_sl.items():
            t = [0, 0, si, ]

            if len(k.split(' ')[0]) == 3:
                t.append('gm. '+' '.join(k.split(' ')[1:]))
                t.append('')
            else:
                t.append('obr. '+' '.join(k.split(' ')[1:]))
                t.append('gm. '+self.sl_gminy[k[:3]])

            t.append('powiat '+self.powiat_naz)
            t.append('na okres: ' + self.od + ' r. do ' + self.do + ' r.')

            if len(k.split(' ')[0]) == 3:
                pp = str(round(sum([y for x, y in self.powy.items()
                                    if x[:3] == k.split(' ')[0]]), 4))
            else:
                pp = str(round(self.powy[k.split(' ')[0]], 4))

            pp_txt = pp.replace('.', ',') + (4 - len(pp.split('.')[1])) * '0'
            t.append('pow. ' + pp_txt + ' ha')

            t.append('stan ewid. na ' + self.geod[k[:3]] + ' r.')
            t.append(0)

            for site in range(1, val+1):
                if si > 0:
                    pages.extendByNewPage()

                if val > 1:
                    t[9] = site

                for px, py in zip(xprzes, yprzes):
                    tab = [px, py, si, ] + t[3:]
                    self.g_kafelek(tab, lay)
                for px in xprzes2:
                    tab = [px, 0, si, ] + t[3:]
                    self.g_grzebiet(tab, lay)

                si += 1

    def g_grzebiet(self, tab, lay):
        """Metoda generuje grzebiety na operaty w zaleznosci od podanego
        przesuniecia i strony, oraz danych w postaci tablicy"""

        si = tab[2]
        px = tab[0]
        ob = tab[3]
        opr = self.sl_typ[self.typ][0]

        dlug_calk = 0  # calkowita dlugosc ramki grzebietu
        add = 0  # przesuniecie calej naklejki ramki w dol o ile mm
        posz = 0  # poszerzenie naklejki o tyle mm

        # ramka grzbietu - generuj na poczatku aby byla jak najnizej w stosie
        okl = QgsLayoutItemShape(lay)

        # nazwa obiektu
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperLeft)
        l1.setText(ob)
        l1.setFont(QFont("Arial", 7, QFont.Bold))
        l1.setHAlign(Qt.AlignCenter)

        # sprawdz czy naklejka nie wymaga poszerzenia
        l1.adjustSizeToText()
        szer = l1.boundingRect().width()
        if szer > 50:
            posz = szer - 50
            # jezeli nakl. jest szersza od 5 cm przesun ja w dol o 9mm jezeli
            # jest parzystą
            if px in [60, 180]:
                add = 9
        else:
            l1.attemptResize(
                QgsLayoutSize(50, 3.3, QgsUnitTypes.LayoutMillimeters))
            posz = 0
            szer = 50

        dlug_calk = szer + 2

        # jeżeli występują tomy dodaj obrocony opis
        if tab[9] > 0:
            dlug_calk += 1.5

            ltom = QgsLayoutItemLabel(lay)
            ltom.setReferencePoint(QgsLayoutItem.UpperMiddle)
            ltom.setText('t. '+str(tab[9]))
            ltom.setFont(QFont("Arial", 7, QFont.Bold))
            ltom.setHAlign(Qt.AlignCenter)
            ltom.attemptResize(
                QgsLayoutSize(6, 6, QgsUnitTypes.LayoutMillimeters))
            ltom.attemptMove(
                QgsLayoutPoint(20+szer+px, 179.7+add,
                               QgsUnitTypes.LayoutMillimeters),
                page=si
            )
            ltom.setFontColor(QColor("#00b050"))
            ltom.setItemRotation(-90)
            lay.addItem(ltom)

        l1.attemptMove(
            QgsLayoutPoint(20+px, 182+add, QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        l1.setFontColor(QColor("#00b050"))
        lay.addItem(l1)

        # dalsze ustawienia ramki
        okl.attemptResize(
            QgsLayoutSize(dlug_calk, 5.4, QgsUnitTypes.LayoutMillimeters))
        okl.attemptMove(
            QgsLayoutPoint(20+px, 180+add,
                           QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        okl.setShapeType(1)
        okl.setSymbol(self.g)
        lay.addItem(okl)

        # nazwa opracowania
        naz = QgsLayoutItemLabel(lay)
        naz.setReferencePoint(QgsLayoutItem.UpperLeft)
        naz.attemptMove(
            QgsLayoutPoint(20.5+posz/2+px, 179.1+add,
                           QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        naz.attemptResize(
            QgsLayoutSize(50, 4, QgsUnitTypes.LayoutMillimeters))
        naz.setHAlign(Qt.AlignCenter)
        naz.setText(opr)
        naz.setFont(QFont("Arial", 6, QFont.Bold))
        naz.setFontColor(QColor("#00b050"))
        lay.addItem(naz)

    def g_kafelek(self, tab, lay):
        """generuje kafelek do naklejenia na czoło operatu"""

        px = tab[0]
        py = tab[1]
        si = tab[2]

        # zielona ramka do wyciecia
        okl = QgsLayoutItemShape(lay)
        okl.attemptResize(
            QgsLayoutSize(115, 70, QgsUnitTypes.LayoutMillimeters))
        okl.attemptMove(
            QgsLayoutPoint(20+px, 20+py, QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        okl.setShapeType(1)
        okl.setSymbol(self.g)
        lay.addItem(okl)

        # nazwa opracowania
        naz = QgsLayoutItemLabel(lay)
        naz.setReferencePoint(QgsLayoutItem.UpperMiddle)
        naz.attemptResize(
            QgsLayoutSize(107, 8, QgsUnitTypes.LayoutMillimeters))
        naz.attemptMove(
            QgsLayoutPoint(77.5+px, 26.1+py, QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        naz.setHAlign(Qt.AlignCenter)
        naz.setText(self.sl_typ[self.typ][0])
        naz.setFont(QFont("Arial", 13, QFont.Bold))
        naz.setFontColor(QColor("#00b050"))
        lay.addItem(naz)

        # obiekt
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l1.setText(tab[3])
        l1.setFont(QFont("Arial", 17, QFont.Bold))
        l1.setHAlign(Qt.AlignCenter)
        l1.attemptResize(
            QgsLayoutSize(106, 17, QgsUnitTypes.LayoutMillimeters))
        l1.attemptMove(
            QgsLayoutPoint(77.5+px, 35+py, QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        l1.setFontColor(QColor("#00b050"))
        lay.addItem(l1)

        # gmina
        if tab[4] != '':
            l1 = QgsLayoutItemLabel(lay)
            l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
            l1.setText(tab[4])
            l1.setFont(QFont("Arial", 14, QFont.Bold))
            l1.setHAlign(Qt.AlignCenter)
            l1.attemptResize(
                QgsLayoutSize(108, 14, QgsUnitTypes.LayoutMillimeters))
            l1.attemptMove(
                QgsLayoutPoint(77.5+px, 52.1+py,
                               QgsUnitTypes.LayoutMillimeters),
                page=si
            )
            l1.setFontColor(QColor("#00b050"))
            lay.addItem(l1)

        # tom opracowania
        if tab[9] > 0:
            l1 = QgsLayoutItemLabel(lay)
            l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
            l1.setText('tom ' + str(tab[9]))
            l1.setFont(QFont("Arial", 9, QFont.Bold))
            l1.setHAlign(Qt.AlignCenter)
            l1.attemptResize(
                QgsLayoutSize(108, 6, QgsUnitTypes.LayoutMillimeters))
            l1.attemptMove(
                QgsLayoutPoint(77.5+px, 60.1+py,
                               QgsUnitTypes.LayoutMillimeters),
                page=si
            )
            l1.setFontColor(QColor("#00b050"))
            lay.addItem(l1)

        # Powiat
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l1.setText(tab[5])
        l1.setFont(QFont("Arial", 11, QFont.Bold))
        l1.setHAlign(Qt.AlignCenter)
        l1.attemptResize(
            QgsLayoutSize(108, 6, QgsUnitTypes.LayoutMillimeters))
        l1.attemptMove(
            QgsLayoutPoint(77.5+px, 65.6+py, QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        l1.setFontColor(QColor("#00b050"))
        lay.addItem(l1)

        # plany na okresy
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l1.setText(tab[6])
        l1.setFont(QFont("Arial", 11, QFont.Bold))
        l1.setHAlign(Qt.AlignCenter)
        l1.attemptResize(
            QgsLayoutSize(108, 6, QgsUnitTypes.LayoutMillimeters))
        l1.attemptMove(
            QgsLayoutPoint(77.5+px, 71.8+py, QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        l1.setFontColor(QColor("#00b050"))
        lay.addItem(l1)

        # powierzchnia
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l1.setText(tab[7])
        l1.setFont(QFont("Arial", 13, QFont.Bold))
        l1.setHAlign(Qt.AlignCenter)
        l1.attemptResize(
            QgsLayoutSize(108, 6, QgsUnitTypes.LayoutMillimeters))
        l1.attemptMove(
            QgsLayoutPoint(77.5+px, 76.8+py, QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        l1.setFontColor(QColor("#00b050"))
        lay.addItem(l1)

        # stan na
        l1 = QgsLayoutItemLabel(lay)
        l1.setReferencePoint(QgsLayoutItem.UpperMiddle)
        l1.setText(tab[8])
        l1.setFont(QFont("Arial", 9, QFont.Bold))
        l1.setHAlign(Qt.AlignCenter)
        l1.attemptResize(
            QgsLayoutSize(108, 6, QgsUnitTypes.LayoutMillimeters))
        l1.attemptMove(
            QgsLayoutPoint(77.5+px, 82+py, QgsUnitTypes.LayoutMillimeters),
            page=si
        )
        l1.setFontColor(QColor("#00b050"))
        lay.addItem(l1)


class PobierzDane(QDialog, Ui_DialogNaklejki):
    def __init__(self):
        super(PobierzDane, self).__init__(None)
        self.setupUi(self)
        self.go_flag = False
        self.lineEdit_sciezka.setText('/home/qnox/upul/testy/grabica/')
        self.kat = ''  # sciezka do podawania w QFileDialogu

        self.pushButton_wybierz.clicked.connect(self.pobierz_katalog_tpu)
        self.pushButton_herb.clicked.connect(self.pobierz_sc_herb)
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

    def pobierz_sc_herb(self):
        plik, _ = QFileDialog.getOpenFileName(
            self,
            'plik z herbem',
            self.kat,
            "obrazy (*.png *.jpg *.bmp *.tif)"
        )

        if os.path.isfile(plik):
            self.lineEdit_herb.setText(plik)

    def zmiana_typu(self):
        if self.comboBox_typ.currentText() == 'ISL':
            self.checkBox_polacz.setEnabled(True)
        else:
            self.checkBox_polacz.setEnabled(False)

        if self.comboBox_typ.currentText() == 'ANEKS':
            self.checkBox_tomy.setEnabled(False)
        else:
            self.checkBox_tomy.setEnabled(True)

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
        self.sl = {}
        for i in range(ilew):
            kod = self.tableWidget.item(i, 0)
            it = self.tableWidget.item(i, 1)
            if it.text().isdigit():
                self.sl[str(kod.text())] = int(it.text())
