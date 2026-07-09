from PyQt5.QtWidgets import QDialog, QMessageBox, QTableWidgetItem

from . import td_slownik
from .ui.ui_td_slownik_dialog import Ui_Dialog


class TdSlownikDialog(QDialog):
    """Podgląd i edycja słownika TD (typ drzewostanu docelowego wg TSL) -
    używanego przez utworz_baze_z_BDL.py. "Zapisz" zapisuje bieżącą
    zawartość tabeli w QSettings (td_slownik.zapisz), "Resetuj" usuwa zapis
    użytkownika i przywraca słownik domyślny TPU (td_slownik.DOMYSLNY,
    nienaruszalny)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.pushButton_dodaj.clicked.connect(self._dodaj_wiersz)
        self.ui.pushButton_usun.clicked.connect(self._usun_wiersz)
        self.ui.pushButton_zapisz.clicked.connect(self._zapisz)
        self.ui.pushButton_resetuj.clicked.connect(self._resetuj)
        self.ui.pushButton_zamknij.clicked.connect(self.accept)

        self._wypelnij(td_slownik.wczytaj())

    def _wypelnij(self, slownik):
        tabela = self.ui.tableWidget
        tabela.setRowCount(0)
        for tsl in sorted(slownik):
            self._dodaj_wiersz(tsl, ' '.join(slownik[tsl]))

    def _dodaj_wiersz(self, tsl='', gatunki=''):
        tabela = self.ui.tableWidget
        wiersz = tabela.rowCount()
        tabela.insertRow(wiersz)
        tabela.setItem(wiersz, 0, QTableWidgetItem(tsl))
        tabela.setItem(wiersz, 1, QTableWidgetItem(gatunki))

    def _usun_wiersz(self):
        for indeks in sorted(
                {i.row() for i in self.ui.tableWidget.selectedIndexes()},
                reverse=True):
            self.ui.tableWidget.removeRow(indeks)

    def _odczytaj_tabele(self):
        """Zwraca {tsl: [gatunek, ...]} z bieżącej zawartości tabeli -
        wiersze z pustym TSL albo bez żadnego gatunku są pomijane."""
        slownik = {}
        tabela = self.ui.tableWidget
        for wiersz in range(tabela.rowCount()):
            item_tsl = tabela.item(wiersz, 0)
            item_gat = tabela.item(wiersz, 1)
            tsl = item_tsl.text().strip() if item_tsl else ''
            gatunki = (item_gat.text().split() if item_gat else [])
            if not tsl or not gatunki:
                continue
            slownik[tsl] = gatunki
        return slownik

    def _zapisz(self):
        td_slownik.zapisz(self._odczytaj_tabele())
        QMessageBox.information(
            self, 'Słownik TD', 'Zapisano zmiany w słowniku TD.')

    def _resetuj(self):
        odp = QMessageBox.question(
            self, 'Resetuj słownik TD',
            'Przywrócić domyślny słownik TPU? Utracisz wprowadzone zmiany.',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if odp != QMessageBox.Yes:
            return
        td_slownik.resetuj()
        self._wypelnij(td_slownik.wczytaj())
