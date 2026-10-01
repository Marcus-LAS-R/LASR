"""Dialog "Podmień wybrane zabiegi": baza, zakres (cała baza / obręby /
formy ochrony przyrody), reguły podmiany "zabieg źródłowy -> docelowy
(albo usuń), nowy %", uwaga do dopisania w opisie i podgląd zmian."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (
    QAbstractItemView, QButtonGroup, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QRadioButton, QTableWidget, QVBoxLayout,
)
from qgis.core import QgsProject

from ...baza_wrapper import Baza
from ..core import podmien as P

USUN = '(usuń zabieg)'


class PodmienZabiegiDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self._baza_sc = ''
        self._zabiegi_w_bazie = {}
        self._slownik = []
        self._obreby = []
        self._fop = []

        self.setWindowTitle('Podmień wybrane zabiegi')
        self.resize(820, 760)
        layout = QVBoxLayout(self)

        naglowek = QLabel(
            'Podmienia albo usuwa wskazane zabiegi w F_AROD_CUE i poprawia '
            'odnowienia (ODN-ZRB / ODN-ZŁOŻ, PIEL, AGROT) tak jak '
            '"Dopisz/sprawdź zabiegi". Masa nie jest przeliczana - przelicz '
            'ją w TPU. Przed zapisem powstaje kopia bazy.')
        naglowek.setWordWrap(True)
        layout.addWidget(naglowek)

        # --- baza ---
        rz = QHBoxLayout()
        rz.addWidget(QLabel('Baza:'))
        self.le_baza = QLineEdit()
        self.le_baza.setReadOnly(True)
        rz.addWidget(self.le_baza, 1)
        btn = QPushButton('Wskaż…')
        btn.clicked.connect(self._wybierz_baze)
        rz.addWidget(btn)
        layout.addLayout(rz)

        # --- zakres ---
        zakres_box = QGroupBox('Zakres podmiany')
        zl = QVBoxLayout(zakres_box)
        rr = QHBoxLayout()
        self.rb_baza = QRadioButton('Cała baza')
        self.rb_obreby = QRadioButton('Obręby')
        self.rb_fop = QRadioButton('Formy ochrony przyrody')
        self.rb_baza.setChecked(True)
        grupa = QButtonGroup(self)
        for rb in (self.rb_baza, self.rb_obreby, self.rb_fop):
            grupa.addButton(rb)
            rr.addWidget(rb)
            rb.toggled.connect(self._zmiana_zakresu)
        rr.addStretch(1)
        zl.addLayout(rr)
        self.lista_zakresu = QListWidget()
        self.lista_zakresu.setMaximumHeight(140)
        self.lista_zakresu.itemChanged.connect(self._niewazny_podglad)
        zl.addWidget(self.lista_zakresu)
        layout.addWidget(zakres_box)

        # --- reguły ---
        reg_box = QGroupBox('Reguły podmiany')
        rl = QVBoxLayout(reg_box)
        opis = QLabel(
            'Zabieg źródłowy (z liczbą wpisów w bazie) -> zabieg docelowy '
            'albo "' + USUN + '". Nowy % (rębnia: % rębni, trzebież: % '
            'pozyskania) - puste = bez zmian; przy zmianie zabiegu nie-rębnego '
            'na rębnię % jest wymagany.')
        opis.setWordWrap(True)
        rl.addWidget(opis)
        self.tabela = QTableWidget(0, 3)
        self.tabela.setHorizontalHeaderLabels(
            ['Zabieg źródłowy', 'Zabieg docelowy', 'Nowy %'])
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.horizontalHeader().setStretchLastSection(True)
        rl.addWidget(self.tabela)
        rb_ = QHBoxLayout()
        self.btn_dodaj = QPushButton('Dodaj regułę')
        self.btn_dodaj.clicked.connect(self._dodaj_regule)
        self.btn_usun = QPushButton('Usuń zaznaczoną regułę')
        self.btn_usun.clicked.connect(self._usun_regule)
        rb_.addWidget(self.btn_dodaj)
        rb_.addWidget(self.btn_usun)
        rb_.addStretch(1)
        rl.addLayout(rb_)
        layout.addWidget(reg_box, 1)

        # --- uwaga ---
        ru = QHBoxLayout()
        ru.addWidget(QLabel('Uwaga do opisu:'))
        self.le_uwaga = QLineEdit()
        self.le_uwaga.setPlaceholderText(
            'puste = bez zmian; tekst trafi na koniec uwag (SUBAREA_INFO) '
            'zmienionych wydzieleń')
        ru.addWidget(self.le_uwaga, 1)
        layout.addLayout(ru)

        # --- podgląd ---
        rp = QHBoxLayout()
        self.btn_podglad = QPushButton('Podgląd (bez zapisu)')
        self.btn_podglad.clicked.connect(self._pokaz_podglad)
        rp.addWidget(self.btn_podglad)
        rp.addStretch(1)
        layout.addLayout(rp)
        self.label_info = QLabel('')
        self.label_info.setWordWrap(True)
        layout.addWidget(self.label_info)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.btn_ok = buttons.addButton('Podmień', QDialogButtonBox.AcceptRole)
        buttons.accepted.connect(self._zatwierdz)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._ustaw_dostepnosc()

    # --- baza ---

    def _wybierz_baze(self):
        start = os.path.dirname(self._baza_sc) if self._baza_sc else (
            QgsProject.instance().homePath() or '')
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę', start, 'Access MDB (*.mdb);;SQLite (*.sqlite)')
        if not sc:
            return
        baza = Baza(sc)
        if not baza.polacz():
            self.label_info.setText('BŁĄD: nie udało się połączyć z bazą.')
            return
        try:
            self._zabiegi_w_bazie = P.pobierz_zabiegi_w_bazie(baza)
            self._slownik = P.pobierz_slownik_zabiegow(baza)
            self._obreby = P.pobierz_obreby(baza)
            self._fop = P.pobierz_formy_ochrony(baza)
        finally:
            baza.zamknij()
        self._baza_sc = sc
        self.le_baza.setText(sc)
        self.tabela.setRowCount(0)
        self._dodaj_regule()
        self._zmiana_zakresu()
        self._ustaw_dostepnosc()

    # --- zakres ---

    def _zmiana_zakresu(self, *_):
        self.lista_zakresu.blockSignals(True)
        self.lista_zakresu.clear()
        pozycje = []
        if self.rb_obreby.isChecked():
            pozycje = self._obreby
        elif self.rb_fop.isChecked():
            pozycje = self._fop
        for klucz, opis in pozycje:
            it = QListWidgetItem(opis)
            it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            it.setCheckState(Qt.Unchecked)
            it.setData(Qt.UserRole, klucz)
            self.lista_zakresu.addItem(it)
        self.lista_zakresu.setEnabled(not self.rb_baza.isChecked())
        self.lista_zakresu.blockSignals(False)
        self._niewazny_podglad()

    def _zakres(self):
        if self.rb_baza.isChecked():
            return 'baza', []
        wybrane = [self.lista_zakresu.item(i).data(Qt.UserRole)
                   for i in range(self.lista_zakresu.count())
                   if self.lista_zakresu.item(i).checkState() == Qt.Checked]
        return ('obreby' if self.rb_obreby.isChecked() else 'fop'), wybrane

    def opis_zakresu(self):
        if self.rb_baza.isChecked():
            return 'cała baza'
        nazwy = [self.lista_zakresu.item(i).text()
                 for i in range(self.lista_zakresu.count())
                 if self.lista_zakresu.item(i).checkState() == Qt.Checked]
        rodzaj = 'obręby' if self.rb_obreby.isChecked() else 'formy ochrony'
        return rodzaj + ': ' + '; '.join(nazwy)

    # --- reguły ---

    def _dodaj_regule(self):
        w = self.tabela.rowCount()
        self.tabela.insertRow(w)
        zrodlo = QComboBox()
        for cd in sorted(self._zabiegi_w_bazie):
            zrodlo.addItem(f'{cd}  ({self._zabiegi_w_bazie[cd]})', cd)
        cel = QComboBox()
        cel.addItem(USUN, None)
        for cd in self._slownik:
            cel.addItem(cd, cd)
        proc = QLineEdit()
        proc.setValidator(QIntValidator(1, 100, proc))
        proc.setPlaceholderText('bez zmian')
        zrodlo.currentIndexChanged.connect(self._niewazny_podglad)
        cel.currentIndexChanged.connect(self._niewazny_podglad)
        proc.textChanged.connect(self._niewazny_podglad)
        self.tabela.setCellWidget(w, 0, zrodlo)
        self.tabela.setCellWidget(w, 1, cel)
        self.tabela.setCellWidget(w, 2, proc)
        self.tabela.resizeColumnsToContents()
        self._niewazny_podglad()

    def _usun_regule(self):
        w = self.tabela.currentRow()
        if w >= 0:
            self.tabela.removeRow(w)
            self._niewazny_podglad()

    def reguly(self):
        wynik = []
        for w in range(self.tabela.rowCount()):
            zrodlo = self.tabela.cellWidget(w, 0).currentData()
            cel = self.tabela.cellWidget(w, 1).currentData()
            tekst = self.tabela.cellWidget(w, 2).text().strip()
            proc = int(tekst) if tekst else None
            if zrodlo:
                wynik.append((zrodlo, cel, proc))
        return wynik

    def _bledy_regul(self, reguly):
        if not reguly:
            return 'Dodaj co najmniej jedną regułę.'
        zrodla = [r[0] for r in reguly]
        dubel = sorted({z for z in zrodla if zrodla.count(z) > 1})
        if dubel:
            return 'Zabieg źródłowy w kilku regułach: ' + ', '.join(dubel)
        for z, c, p in reguly:
            if z == c:
                return f'Reguła {z} -> {c}: zabieg docelowy taki sam jak ' \
                       'źródłowy.'
            if c in P.REBNIE and z not in P.REBNIE and p is None:
                return f'Reguła {z} -> {c}: podaj % rębni.'
        return ''

    # --- podgląd / zatwierdzenie ---

    def _niewazny_podglad(self, *_):
        self.label_info.setText('')
        self._ustaw_dostepnosc()

    def _ustaw_dostepnosc(self):
        jest = bool(self._baza_sc)
        self.btn_dodaj.setEnabled(jest)
        self.btn_usun.setEnabled(jest)
        self.btn_podglad.setEnabled(jest)
        self.btn_ok.setEnabled(jest)

    def _sprawdz(self):
        blad = self._bledy_regul(self.reguly())
        if not blad:
            zakres, wybrane = self._zakres()
            if zakres != 'baza' and not wybrane:
                blad = 'Zaznacz co najmniej jedną pozycję zakresu.'
        if blad:
            self.label_info.setText('BŁĄD: ' + blad)
        return not blad

    def _pokaz_podglad(self):
        if not self._sprawdz():
            return
        baza = Baza(self._baza_sc)
        if not baza.polacz():
            self.label_info.setText('BŁĄD: nie udało się połączyć z bazą.')
            return
        try:
            zakres, wybrane = self._zakres()
            wydz = P.wydzielenia_w_zakresie(baza, zakres, wybrane)
            plany = P.zaplanuj(baza, wydz, self.reguly(),
                               self.le_uwaga.text().strip())
        finally:
            baza.zamknij()
        s = P.podsumuj(plany)
        self.label_info.setText(
            f'Wydzieleń w zakresie: {len(wydz)}\n'
            f'Wydzieleń do zmiany: {s["wydzielenia"]} (w tym z uwagami do '
            f'sprawdzenia: {s["z_uwagami"]})\n'
            f'Pominiętych: {s["pominiete"]} (powody w raporcie po zapisie)')

    def _zatwierdz(self):
        if self._sprawdz():
            self.accept()

    def wybor(self):
        zakres, wybrane = self._zakres()
        return {
            'baza_sc': self._baza_sc,
            'zakres': zakres,
            'wybrane': wybrane,
            'zakres_opis': self.opis_zakresu(),
            'reguly': self.reguly(),
            'uwaga': self.le_uwaga.text().strip(),
        }
