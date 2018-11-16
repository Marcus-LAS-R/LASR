from datetime import datetime
import os
import platform
import glob
from qgis.core import QgsMessageLog, Qgis, QgsFillSymbol
from PyQt5.QtWidgets import QDialog, QFileDialog, QTableWidgetItem

from .baza_wrapper import Baza

from ..ui.ui_naklejki_dialog import Ui_DialogNaklejki
from ..ui.ui_naklejki_tomy import Ui_DialogTomy


class GenerujNaklejki:
    def __init__(self, iface):
        self.iface = iface
        self.tomy_sl = {}  # slownik z ilością tomów dla kazdego z opracowan

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
            datetime.now().year+11
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
