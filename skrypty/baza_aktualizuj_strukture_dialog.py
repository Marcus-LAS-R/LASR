import os
import glob
import platform
from PyQt5.QtWidgets import QDialog, QFileDialog

from .ui.ui_baza_aktualizuj_strukture import Ui_Dialog
from .baza_wybor_katalogu_dialog import przegladaj_katalog_z_podgladem


class WyborTrybuAktualizacjiDialog(QDialog):
    """Jeden dialog na cały pierwszy krok: katalog ze starymi bazami +
    tryb (połącz/osobno) + szablon + folder eksportu - zamiast dwóch
    osobnych okienek pod rząd."""

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.wzorzec = "*.mdb" if platform.system()[:3] == 'Win' else "*.sqlite"
        self.kat_startowy = ''
        self.lista = []  # wypelniana na biezaco przez _na_zmiane_katalogu

        self.ui.label_info.setText(
            'Szablon jest zawsze tylko kopiowany, nigdy nie jest zmieniany. '
            '"Połącz" tworzy w folderze eksportu JEDNĄ bazę (kopię '
            'szablonu) i ładuje do niej wszystkie stare bazy. "Osobno" '
            'tworzy w folderze eksportu OSOBNĄ kopię szablonu dla każdej '
            'starej bazy, bez łączenia.')

        self.ui.lineEdit_katalog.textChanged.connect(self._na_zmiane_katalogu)
        self.ui.lineEdit_szablon.textChanged.connect(self._aktualizuj_ok)
        self.ui.lineEdit_folder_wyjsciowy.textChanged.connect(self._aktualizuj_ok)
        self.ui.pushButton_przegladaj_katalog.clicked.connect(
            self._przegladaj_katalog)
        self.ui.pushButton_przegladaj_szablon.clicked.connect(
            self._przegladaj_szablon)
        self.ui.pushButton_przegladaj_folder.clicked.connect(
            self._przegladaj_folder)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

        self._na_zmiane_katalogu()

    def _przegladaj_katalog(self):
        start = self.ui.lineEdit_katalog.text() or ''
        sc = przegladaj_katalog_z_podgladem(
            self, "Katalog ze starymi bazami", self.wzorzec, start)
        if sc:
            self.ui.lineEdit_katalog.setText(sc)

    def _przegladaj_szablon(self):
        sc = QFileDialog().getOpenFileName(
            self, 'Wskaż bazę-szablon', self.kat_startowy,
            "Bazy danych (*.mdb *.sqlite)")[0]
        if sc != '':
            self.kat_startowy = os.path.dirname(sc)
            self.ui.lineEdit_szablon.setText(sc)

    def _przegladaj_folder(self):
        sc = QFileDialog().getExistingDirectory(
            self, 'Wskaż folder eksportu', self.kat_startowy)
        if sc != '':
            self.kat_startowy = sc
            self.ui.lineEdit_folder_wyjsciowy.setText(sc)

    def _na_zmiane_katalogu(self, *_):
        katalog = self.ui.lineEdit_katalog.text().strip().strip('"')
        if katalog:
            self.kat_startowy = katalog
            self.lista = sorted(glob.glob(os.path.join(katalog, self.wzorzec)))
        else:
            self.lista = []

        if not katalog:
            self.ui.label_status_katalog.setText('')
        elif not self.lista:
            self.ui.label_status_katalog.setText(
                'Nie znaleziono żadnej bazy w tym katalogu.')
        else:
            self.ui.label_status_katalog.setText(
                'Znaleziono ' + str(len(self.lista)) + ' starych baz.')

        self._aktualizuj_ok()

    def _aktualizuj_ok(self, *_):
        ok = (len(self.lista) > 0 and
              self.ui.lineEdit_szablon.text().strip() != '' and
              self.ui.lineEdit_folder_wyjsciowy.text().strip() != '')
        self.ui.pushButton_ok.setEnabled(ok)

    def wybor(self):
        """Zwraca (lista_starych_baz, tryb, szablon_sc, folder_wyjsciowy) -
        tryb 'polacz'|'szablon'."""
        tryb = 'polacz' if self.ui.radioButton_polacz.isChecked() else 'szablon'
        return (self.lista, tryb, self.ui.lineEdit_szablon.text().strip(),
                self.ui.lineEdit_folder_wyjsciowy.text().strip())
