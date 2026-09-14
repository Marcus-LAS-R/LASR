"""Dialog "Wydziel właścicieli do nowej bazy": wybór bazy źródłowej,
filtrowanie i zaznaczenie właściciela/właścicieli checkboxami z sortowalnej
tabeli V_ADDRESS, opcje eksportu (opisy taksacyjne/grafika/uprzątnięcie) i
podgląd (dry-run) przed uruchomieniem właściwego eksportu (patrz
__init__.uruchom)."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ...baza_wrapper import Baza
from ..core import eksport

# kolumny tabeli: 0 = checkbox zaznaczenia, reszta = dane z V_ADDRESS
_KOLUMNY = ['', 'ADDR_NR', 'NAME_1', 'NAME_2', 'addr_grp_fl']
_KOL_ADDR_NR = 1


class _NumericItem(QTableWidgetItem):
    """Sortuje ADDR_NR liczbowo zamiast leksykograficznie (inaczej '10' < '2')."""

    def __lt__(self, other):
        try:
            return int(self.text()) < int(other.text())
        except (ValueError, TypeError):
            return super().__lt__(other)


class WydzielWlascicieliDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self._kat_startowy = ''
        self._baza_zrodlowa = None  # Baza połączona do bazy źródłowej
        # zbiór zaznaczonych ADDR_NR - niezależny od tego, które wiersze są
        # aktualnie ukryte przez filtr, żeby filtrowanie nie gubiło wyboru
        self._zaznaczeni_addr = set()

        self.setWindowTitle('Wydziel właścicieli do nowej bazy')
        self.resize(1150, 750)
        layout = QVBoxLayout(self)

        naglowek = QLabel(
            'Wybranych właścicieli (wraz z bezpośrednimi współwłaścicielami '
            'na tych samych działkach) eksportuje do już istniejącej bazy '
            'docelowej. Przed jakąkolwiek zmianą w bazie/plikach '
            'źródłowych zostanie zrobiona kopia bezpieczeństwa.')
        naglowek.setWordWrap(True)
        layout.addWidget(naglowek)

        # --- baza źródłowa ---
        zrodlo_row = QHBoxLayout()
        zrodlo_row.addWidget(QLabel('Baza źródłowa:'))
        self.le_zrodlo = QLineEdit()
        self.le_zrodlo.setReadOnly(True)
        zrodlo_row.addWidget(self.le_zrodlo, 1)
        btn_zrodlo = QPushButton('Wskaż…')
        btn_zrodlo.clicked.connect(self._wybierz_zrodlo)
        zrodlo_row.addWidget(btn_zrodlo)
        layout.addLayout(zrodlo_row)

        # --- tabela właścicieli ---
        layout.addWidget(QLabel(
            'Właściciele (V_ADDRESS) - kliknij nagłówek, żeby posortować; '
            'zaznacz checkboxem jednego lub więcej. Poniżej można '
            'filtrować każdą kolumnę osobno (zaznaczenie jest zapamiętane '
            'także dla wierszy chwilowo odfiltrowanych):'))

        filtry_grid = QGridLayout()
        self._filtry = {}
        for kol in (_KOL_ADDR_NR, 2, 3, 4):
            filtry_grid.addWidget(QLabel(_KOLUMNY[kol] + ':'), 0, kol)
            pole = QLineEdit()
            pole.setPlaceholderText('filtr…')
            pole.textChanged.connect(self._zastosuj_filtry)
            filtry_grid.addWidget(pole, 1, kol)
            self._filtry[kol] = pole
        layout.addLayout(filtry_grid)

        self.tabela = QTableWidget(0, len(_KOLUMNY))
        self.tabela.setHorizontalHeaderLabels(_KOLUMNY)
        self.tabela.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.horizontalHeader().setStretchLastSection(False)
        self.tabela.setSortingEnabled(True)
        self.tabela.itemChanged.connect(self._checkbox_zmieniony)
        layout.addWidget(self.tabela, 1)

        self.label_zaznaczono = QLabel('Zaznaczono: 0')
        layout.addWidget(self.label_zaznaczono)

        # --- opcje ---
        opcje_box = QGroupBox('Opcje eksportu')
        opcje_layout = QVBoxLayout(opcje_box)

        self.chk_opisy = QCheckBox('Wyeksportuj opisy taksacyjne (dane leśne)')
        self.chk_opisy.setChecked(False)
        opcje_layout.addWidget(self.chk_opisy)

        self.chk_grafika = QCheckBox('Wyeksportuj grafikę (SHP)')
        self.chk_grafika.setChecked(False)
        opcje_layout.addWidget(self.chk_grafika)

        shp_row = QHBoxLayout()
        shp_row.addWidget(QLabel('    Folder SHP źródłowy:'))
        self.le_shp = QLineEdit()
        self.le_shp.setEnabled(False)
        shp_row.addWidget(self.le_shp, 1)
        btn_shp = QPushButton('Wskaż…')
        btn_shp.setEnabled(False)
        btn_shp.clicked.connect(self._wybierz_shp)
        shp_row.addWidget(btn_shp)
        opcje_layout.addLayout(shp_row)
        self.chk_grafika.toggled.connect(self.le_shp.setEnabled)
        self.chk_grafika.toggled.connect(btn_shp.setEnabled)

        self.chk_uprzatnij = QCheckBox(
            'Uprzątnij dane wejściowe (usuń wyeksportowane dane z bazy i '
            'plików SHP źródłowych)')
        self.chk_uprzatnij.setChecked(True)
        opcje_layout.addWidget(self.chk_uprzatnij)

        layout.addWidget(opcje_box)

        # --- baza docelowa ---
        cel_row = QHBoxLayout()
        cel_row.addWidget(QLabel('Baza docelowa (istniejąca):'))
        self.le_cel = QLineEdit()
        cel_row.addWidget(self.le_cel, 1)
        btn_cel = QPushButton('Wskaż…')
        btn_cel.clicked.connect(self._wybierz_cel)
        cel_row.addWidget(btn_cel)
        layout.addLayout(cel_row)

        # --- podgląd (dry-run) ---
        podglad_row = QHBoxLayout()
        self.btn_podglad = QPushButton('Podgląd (bez zapisu)')
        self.btn_podglad.clicked.connect(self._pokaz_podglad)
        podglad_row.addWidget(self.btn_podglad)
        podglad_row.addStretch(1)
        layout.addLayout(podglad_row)

        self.label_podglad = QLabel('')
        self.label_podglad.setWordWrap(True)
        layout.addWidget(self.label_podglad)

        # --- przyciski ---
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.btn_ok = buttons.addButton(
            'Wydziel', QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.btn_ok.setEnabled(False)
        self.btn_podglad.setEnabled(False)

        self.le_cel.textChanged.connect(self._aktualizuj_ok)
        self.le_shp.textChanged.connect(self._aktualizuj_ok)
        self.chk_grafika.toggled.connect(self._aktualizuj_ok)

    # --- wybór plików/folderów ---

    def _wybierz_zrodlo(self):
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę źródłową', self._kat_startowy,
            'Access MDB (*.mdb);;SQLite (*.sqlite)')
        if not sc:
            return
        self._kat_startowy = os.path.dirname(sc)

        baza = Baza(sc)
        if not baza.polacz():
            self.label_podglad.setText('BŁĄD: nie udało się połączyć z bazą.')
            return

        if self._baza_zrodlowa is not None:
            self._baza_zrodlowa.zamknij()
        self._baza_zrodlowa = baza
        self.le_zrodlo.setText(sc)
        self._zaznaczeni_addr = set()
        for pole in self._filtry.values():
            pole.blockSignals(True)
            pole.clear()
            pole.blockSignals(False)
        self._wczytaj_wlascicieli()

    def _wybierz_shp(self):
        kat = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder SHP źródłowy', self._kat_startowy)
        if kat:
            self.le_shp.setText(kat)

    def _wybierz_cel(self):
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę docelową', self._kat_startowy,
            'Access MDB (*.mdb);;SQLite (*.sqlite)')
        if sc:
            self.le_cel.setText(sc)

    # --- tabela właścicieli ---

    def _wczytaj_wlascicieli(self):
        wlasciciele = eksport.pobierz_wlascicieli(self._baza_zrodlowa)
        self.tabela.setSortingEnabled(False)
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(len(wlasciciele))
        for wiersz, (addr_nr, name_1, name_2, grp_fl) in enumerate(wlasciciele):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if addr_nr in self._zaznaczeni_addr
                               else Qt.Unchecked)
            self.tabela.setItem(wiersz, 0, chk)
            self.tabela.setItem(wiersz, 1, _NumericItem(str(addr_nr)))
            self.tabela.setItem(wiersz, 2, QTableWidgetItem(str(name_1 or '')))
            self.tabela.setItem(wiersz, 3, QTableWidgetItem(str(name_2 or '')))
            self.tabela.setItem(wiersz, 4, QTableWidgetItem(str(grp_fl or '')))
        self.tabela.blockSignals(False)
        self.tabela.setSortingEnabled(True)
        self.tabela.resizeColumnsToContents()
        self._aktualizuj_zaznaczenie()

    def _checkbox_zmieniony(self, item):
        if item.column() != 0:
            return
        addr_nr = int(self.tabela.item(item.row(), _KOL_ADDR_NR).text())
        if item.checkState() == Qt.Checked:
            self._zaznaczeni_addr.add(addr_nr)
        else:
            self._zaznaczeni_addr.discard(addr_nr)
        self._aktualizuj_zaznaczenie()
        self._aktualizuj_ok()

    def _zastosuj_filtry(self, *_):
        filtry = {kol: pole.text().strip().lower()
                  for kol, pole in self._filtry.items() if pole.text().strip()}
        for wiersz in range(self.tabela.rowCount()):
            widoczny = all(
                tekst in self.tabela.item(wiersz, kol).text().lower()
                for kol, tekst in filtry.items())
            self.tabela.setRowHidden(wiersz, not widoczny)

    def _aktualizuj_zaznaczenie(self):
        self.label_zaznaczono.setText(
            'Zaznaczono: ' + str(len(self._zaznaczeni_addr)))

    # --- podgląd / walidacja ---

    def _pokaz_podglad(self):
        if not self._zaznaczeni_addr or self._baza_zrodlowa is None:
            return
        wynik = eksport.podglad(
            self._baza_zrodlowa, self._zaznaczeni_addr, self.chk_opisy.isChecked())
        tekst = (
            'Zaznaczonych właścicieli: {wlasciciele_zaznaczeni}\n'
            'Dodatkowych współwłaścicieli (na tych samych działkach): '
            '{wspolwlasciciele_dodatkowi}\n'
            'Działek do eksportu: {dzialki}'
        ).format(**wynik)
        if self.chk_opisy.isChecked():
            tekst += '\nWydzieleń do eksportu: {wydzielenia}'.format(**wynik)
        self.label_podglad.setText(tekst)

    def _aktualizuj_ok(self, *_):
        ok = (
            self._baza_zrodlowa is not None and
            bool(self._zaznaczeni_addr) and
            bool(self.le_cel.text().strip()) and
            (not self.chk_grafika.isChecked() or
             bool(self.le_shp.text().strip()))
        )
        self.btn_ok.setEnabled(ok)
        self.btn_podglad.setEnabled(
            self._baza_zrodlowa is not None and bool(self._zaznaczeni_addr))

    # --- wynik ---

    def zrodlo_baza(self):
        """Zwraca połączoną Baza źródłową (właściciel przejmuje - dialog
        po accept() jej już nie zamyka)."""
        return self._baza_zrodlowa

    def wybor(self):
        return {
            'addr_wybrani': set(self._zaznaczeni_addr),
            'cel_sc': self.le_cel.text().strip(),
            'opcja_opisy': self.chk_opisy.isChecked(),
            'opcja_grafika': self.chk_grafika.isChecked(),
            'opcja_uprzatnij': self.chk_uprzatnij.isChecked(),
            'folder_shp': self.le_shp.text().strip() or None,
        }

    def reject(self):
        if self._baza_zrodlowa is not None:
            self._baza_zrodlowa.zamknij()
            self._baza_zrodlowa = None
        super().reject()
