import os
from PyQt5.QtWidgets import QDialog, QFileDialog

from .ui.ui_baza_polacz_docelowa import Ui_Dialog


class WyborBazyDocelowejDialog(QDialog):
    def __init__(self, iface, lista_baz):
        super().__init__(iface.mainWindow())
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.lista_baz = lista_baz
        self.kat_startowy = os.path.dirname(lista_baz[0]) if lista_baz else ''

        self.ui.label_info.setText(
            'Domyślnie (bez zaznaczenia poniżej) bazą docelową będzie '
            '(w kolejności alfabetycznej): ' +
            (os.path.basename(lista_baz[0]) if lista_baz else '-'))

        self.ui.checkBox_wskaz.toggled.connect(self.ui.lineEdit_baza.setEnabled)
        self.ui.checkBox_wskaz.toggled.connect(
            self.ui.pushButton_przegladaj.setEnabled)
        self.ui.checkBox_wskaz.toggled.connect(self._aktualizuj_ok)
        self.ui.lineEdit_baza.textChanged.connect(self._aktualizuj_ok)
        self.ui.pushButton_przegladaj.clicked.connect(self._przegladaj)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)
        self._aktualizuj_ok()

    def _przegladaj(self):
        sc = QFileDialog().getOpenFileName(
            self, 'Wskaż bazę docelową', self.kat_startowy,
            "Bazy danych (*.mdb *.sqlite)")[0]
        if sc != '':
            self.kat_startowy = os.path.dirname(sc)
            self.ui.lineEdit_baza.setText(sc)

    def _aktualizuj_ok(self, *_):
        wymagana_sciezka = self.ui.checkBox_wskaz.isChecked()
        self.ui.pushButton_ok.setEnabled(
            not wymagana_sciezka or self.ui.lineEdit_baza.text() != '')

    def wybor(self):
        """Zwraca ścieżkę wskazanej bazy docelowej, albo None jeśli checkbox
        odznaczony (zachowaj domyślne zachowanie - lista[0])."""
        if not self.ui.checkBox_wskaz.isChecked():
            return None
        return self.ui.lineEdit_baza.text()
