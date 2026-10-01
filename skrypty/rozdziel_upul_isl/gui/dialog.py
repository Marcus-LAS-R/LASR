"""Dialog "Rozdziel bazy na UPUL i ISL": wybór bazy, tryb automatyczny
(próg sumy LS w obrębie) albo ręczny (użytkownik zaznacza obręby ISL),
opcjonalnie folder SHP do podziału grafiki (patrz __init__.uruchom)."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QDialog, QDialogButtonBox,
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QRadioButton, QTableWidget, QTableWidgetItem, QVBoxLayout,
)
from qgis.core import QgsProject

from ...baza_wrapper import Baza
from ..core import rozdziel as R

_KOLUMNY = ['ISL', 'Kod obrębu', 'Gmina', 'Obręb', 'Pow. LS [ha]',
            'Działek', 'Trafia do']
_KOL_ISL, _KOL_KOD, _KOL_POW, _KOL_GRUPA = 0, 1, 4, 6
_OPIS_GRUPY = {R.UPUL: 'UPUL', R.ISL: 'ISL',
               R.BEZ_LS: 'bez LS - usunięty z obu baz'}


class _LiczbaItem(QTableWidgetItem):
    """Sortowanie liczbowe kolumn powierzchni/liczby działek."""

    def __init__(self, tekst, wartosc):
        super().__init__(tekst)
        self._wartosc = wartosc

    def __lt__(self, other):
        if isinstance(other, _LiczbaItem):
            return self._wartosc < other._wartosc
        return super().__lt__(other)


def _pow(x):
    return f'{x:.4f}'.replace('.', ',')


class RozdzielUpulIslDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self._obreby = []
        self._isl_reczne = set()  # klucze obrębów zaznaczonych jako ISL
        self._baza_sc = ''

        self.setWindowTitle('Rozdziel bazy na UPUL i ISL')
        self.resize(950, 700)
        layout = QVBoxLayout(self)

        naglowek = QLabel(
            'Dzieli bazę na dwie nowe bazy (<nazwa>_UPUL i <nazwa>_ISL obok '
            'bazy źródłowej) według sumy powierzchni użytku LS w obrębach '
            'ewidencyjnych. Obręby bez użytku LS są usuwane z obu baz. Baza '
            'źródłowa nie jest zmieniana.')
        naglowek.setWordWrap(True)
        layout.addWidget(naglowek)

        # --- baza źródłowa ---
        rz = QHBoxLayout()
        rz.addWidget(QLabel('Baza źródłowa:'))
        self.le_baza = QLineEdit()
        self.le_baza.setReadOnly(True)
        rz.addWidget(self.le_baza, 1)
        btn = QPushButton('Wskaż…')
        btn.clicked.connect(self._wybierz_baze)
        rz.addWidget(btn)
        layout.addLayout(rz)

        # --- tryb ---
        tryb_box = QGroupBox('Tryb podziału')
        tryb_l = QVBoxLayout(tryb_box)
        self.rb_auto = QRadioButton(
            f'Automatyczny - do ISL obręby z sumą LS poniżej '
            f'{_pow(R.PROG_ISL)} ha, do UPUL {_pow(R.PROG_ISL)} ha i więcej')
        self.rb_reczny = QRadioButton(
            'Ręczny - zaznacz w tabeli obręby, które mają trafić do ISL')
        self.rb_auto.setChecked(True)
        grupa = QButtonGroup(self)
        grupa.addButton(self.rb_auto)
        grupa.addButton(self.rb_reczny)
        tryb_l.addWidget(self.rb_auto)
        tryb_l.addWidget(self.rb_reczny)
        layout.addWidget(tryb_box)
        self.rb_auto.toggled.connect(self._zmiana_trybu)

        # --- tabela obrębów ---
        self.tabela = QTableWidget(0, len(_KOLUMNY))
        self.tabela.setHorizontalHeaderLabels(_KOLUMNY)
        self.tabela.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.itemChanged.connect(self._checkbox_zmieniony)
        layout.addWidget(self.tabela, 1)

        self.label_podsumowanie = QLabel('')
        self.label_podsumowanie.setWordWrap(True)
        layout.addWidget(self.label_podsumowanie)

        # --- grafika ---
        self.chk_grafika = QCheckBox(
            'Podziel również grafikę (wszystkie warstwy SHP z folderu - do '
            'SHP_UPUL i SHP_ISL obok bazy)')
        layout.addWidget(self.chk_grafika)
        rs = QHBoxLayout()
        rs.addWidget(QLabel('    Folder SHP:'))
        self.le_shp = QLineEdit()
        rs.addWidget(self.le_shp, 1)
        self.btn_shp = QPushButton('Wskaż…')
        self.btn_shp.clicked.connect(self._wybierz_shp)
        rs.addWidget(self.btn_shp)
        layout.addLayout(rs)
        self.chk_grafika.toggled.connect(self.le_shp.setEnabled)
        self.chk_grafika.toggled.connect(self.btn_shp.setEnabled)
        self.chk_grafika.toggled.connect(self._aktualizuj_ok)
        self.le_shp.textChanged.connect(self._aktualizuj_ok)
        self.le_shp.setEnabled(False)
        self.btn_shp.setEnabled(False)

        # --- przyciski ---
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.btn_ok = buttons.addButton('Rozdziel', QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.btn_ok.setEnabled(False)

    # --- wybór plików ---

    def _katalog_startowy(self):
        if self._baza_sc:
            return os.path.dirname(self._baza_sc)
        return QgsProject.instance().homePath() or ''

    def _wybierz_baze(self):
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę źródłową', self._katalog_startowy(),
            'Access MDB (*.mdb);;SQLite (*.sqlite)')
        if not sc:
            return
        # skrypt bazę źródłową tylko czyta - można ją otworzyć mimo
        # podłączenia do Edytora opisu
        baza = Baza(sc, pomin_blokade=True)
        if not baza.polacz():
            self.label_podsumowanie.setText(
                'BŁĄD: nie udało się połączyć z bazą.')
            return
        try:
            obreby = R.pobierz_obreby(baza)
        finally:
            baza.zamknij()

        self._baza_sc = sc
        self.le_baza.setText(sc)
        self._obreby = obreby
        self._isl_reczne = {o.klucz for o in obreby
                            if o.grupa_auto() == R.ISL}

        shp = os.path.join(os.path.dirname(sc), 'SHP')
        if os.path.isdir(shp):
            self.le_shp.setText(shp)
            self.chk_grafika.setChecked(True)

        self._wypelnij_tabele()

    def _wybierz_shp(self):
        kat = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder SHP', self.le_shp.text() or
            self._katalog_startowy())
        if kat:
            self.le_shp.setText(kat)

    # --- tabela ---

    def przydzial(self):
        if self.rb_auto.isChecked():
            return R.podziel_auto(self._obreby)
        return R.podziel_reczny(self._obreby, self._isl_reczne)

    def _wypelnij_tabele(self):
        przydzial = self.przydzial()
        auto = self.rb_auto.isChecked()
        szary = QBrush(QColor(150, 150, 150))

        self.tabela.setSortingEnabled(False)
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(len(self._obreby))
        for w, o in enumerate(self._obreby):
            g = przydzial[o.klucz]
            chk = QTableWidgetItem()
            flagi = Qt.ItemIsUserCheckable
            if o.ma_ls and not auto:
                flagi |= Qt.ItemIsEnabled
            chk.setFlags(flagi)
            chk.setCheckState(Qt.Checked if g == R.ISL else Qt.Unchecked)
            chk.setData(Qt.UserRole, o.klucz)
            self.tabela.setItem(w, _KOL_ISL, chk)
            komorki = [
                QTableWidgetItem(R.klucz_tekst(o.klucz)),
                QTableWidgetItem(o.gmina),
                QTableWidgetItem(o.nazwa),
                _LiczbaItem(_pow(o.pow_ls), o.pow_ls),
                _LiczbaItem(str(o.dzialki), o.dzialki),
                QTableWidgetItem(_OPIS_GRUPY[g]),
            ]
            for k, item in enumerate(komorki, start=1):
                if k in (_KOL_POW, 5):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if not o.ma_ls:
                    item.setForeground(szary)
                self.tabela.setItem(w, k, item)
        self.tabela.blockSignals(False)
        self.tabela.setSortingEnabled(True)
        self.tabela.resizeColumnsToContents()
        self._aktualizuj_podsumowanie(przydzial)
        self._aktualizuj_ok()

    def _zmiana_trybu(self, *_):
        # ręczny startuje od podziału automatycznego (_isl_reczne ustawiane
        # przy wczytaniu bazy), potem pamięta zaznaczenie użytkownika
        if self._obreby:
            self._wypelnij_tabele()

    def _checkbox_zmieniony(self, item):
        if item.column() != _KOL_ISL or self.rb_auto.isChecked():
            return
        klucz = item.data(Qt.UserRole)
        if item.checkState() == Qt.Checked:
            self._isl_reczne.add(klucz)
        else:
            self._isl_reczne.discard(klucz)
        przydzial = self.przydzial()
        wiersz = item.row()
        self.tabela.blockSignals(True)
        self.tabela.item(wiersz, _KOL_GRUPA).setText(
            _OPIS_GRUPY[przydzial[klucz]])
        self.tabela.blockSignals(False)
        self._aktualizuj_podsumowanie(przydzial)
        self._aktualizuj_ok()

    def _aktualizuj_podsumowanie(self, przydzial):
        linie = []
        for g in (R.UPUL, R.ISL, R.BEZ_LS):
            obr = [o for o in self._obreby if przydzial[o.klucz] == g]
            linie.append(
                f'{_OPIS_GRUPY[g]}: {len(obr)} obrębów, LS '
                f'{_pow(sum(o.pow_ls for o in obr))} ha, działek '
                f'{sum(o.dzialki for o in obr)}')
        self.label_podsumowanie.setText('\n'.join(linie))

    def _aktualizuj_ok(self, *_):
        przydzial = self.przydzial() if self._obreby else {}
        ok = (
            bool(self._baza_sc) and
            any(g in (R.UPUL, R.ISL) for g in przydzial.values()) and
            (not self.chk_grafika.isChecked() or
             os.path.isdir(self.le_shp.text().strip()))
        )
        self.btn_ok.setEnabled(ok)

    # --- wynik ---

    def wybor(self):
        return {
            'baza_sc': self._baza_sc,
            'tryb': 'automatyczny' if self.rb_auto.isChecked() else 'ręczny',
            'obreby': list(self._obreby),
            'przydzial': self.przydzial(),
            'folder_shp': (self.le_shp.text().strip()
                           if self.chk_grafika.isChecked() else None),
        }
