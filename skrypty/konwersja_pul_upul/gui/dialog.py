"""Dialog wyboru źródeł/celu dla konwersji PUL -> UPUL. Zbudowany ręcznie
w kodzie (bez osobnego pliku ui_*.py), wzorem
baza_korekta_gmin_dialog.KorektaGminDialog - prostsze niż Qt Designer dla
stałego, niewielkiego zestawu pól."""

import os

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog,
)


class KonwersjaPulUpulDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self._kat_startowy = ''

        self.setWindowTitle('Konwertuj PUL → UPUL')
        self.resize(640, 320)
        layout = QVBoxLayout(self)

        naglowek = QLabel(
            'Konwertuje bazę PUL (Lasy Państwowe) do formatu UPUL. Adres '
            'leśny jest wyznaczany na nowo z geometrii warstwy wydzieleń '
            'względem warstwy obrębów ewidencyjnych — dane F_ARODES '
            'źródła (RDLP/Nadleśnictwo) nie są kopiowane wprost, bo bywają '
            'błędne. Dane zostaną wczytane bezpośrednio do wskazanej '
            'pustej bazy docelowej.')
        naglowek.setWordWrap(True)
        layout.addWidget(naglowek)

        grid = QGridLayout()
        wiersz = 0

        self.le_baza_pul = QLineEdit()
        wiersz = self._dodaj_wiersz(
            grid, wiersz, 'Baza PUL (źródłowa):', self.le_baza_pul,
            self._wybierz_baza_pul)

        self.le_wydz = QLineEdit()
        wiersz = self._dodaj_wiersz(
            grid, wiersz, 'Warstwa wydzieleń (SHP):', self.le_wydz,
            self._wybierz_wydz)

        self.le_obreby = QLineEdit()
        wiersz = self._dodaj_wiersz(
            grid, wiersz, 'Warstwa obrębów ewidencyjnych (SHP):',
            self.le_obreby, self._wybierz_obreby)

        self.le_cel = QLineEdit()
        wiersz = self._dodaj_wiersz(
            grid, wiersz, 'Pusta baza docelowa (UPUL):',
            self.le_cel, self._wybierz_cel)

        layout.addLayout(grid)

        self.label_status = QLabel('')
        self.label_status.setWordWrap(True)
        layout.addWidget(self.label_status)

        przyciski = QHBoxLayout()
        self.pushButton_ok = QPushButton('Konwertuj')
        self.pushButton_ok.setEnabled(False)
        self.pushButton_cancel = QPushButton('Anuluj')
        przyciski.addStretch(1)
        przyciski.addWidget(self.pushButton_ok)
        przyciski.addWidget(self.pushButton_cancel)
        layout.addLayout(przyciski)

        for pole in (self.le_baza_pul, self.le_wydz, self.le_obreby,
                     self.le_cel):
            pole.textChanged.connect(self._aktualizuj_ok)

        self.pushButton_ok.clicked.connect(self.accept)
        self.pushButton_cancel.clicked.connect(self.reject)

        self._aktualizuj_ok()

    def _dodaj_wiersz(self, grid, wiersz, etykieta, pole, slot_przegladaj):
        grid.addWidget(QLabel(etykieta), wiersz, 0)
        grid.addWidget(pole, wiersz, 1)
        przycisk = QPushButton('Przeglądaj…')
        przycisk.clicked.connect(slot_przegladaj)
        grid.addWidget(przycisk, wiersz, 2)
        return wiersz + 1

    def _wybierz_baza_pul(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę PUL (źródłową)', self._kat_startowy,
            'Access MDB (*.mdb)')[0]
        if sc:
            self._kat_startowy = os.path.dirname(sc)
            self.le_baza_pul.setText(sc)

    def _wybierz_wydz(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż warstwę wydzieleń', self._kat_startowy,
            'Shapefile (*.shp)')[0]
        if sc:
            self._kat_startowy = os.path.dirname(sc)
            self.le_wydz.setText(sc)

    def _wybierz_obreby(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż warstwę obrębów ewidencyjnych', self._kat_startowy,
            'Shapefile (*.shp)')[0]
        if sc:
            self._kat_startowy = os.path.dirname(sc)
            self.le_obreby.setText(sc)

    def _wybierz_cel(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż pustą bazę docelową (UPUL)',
            self._kat_startowy, 'Access MDB (*.mdb)')[0]
        if sc:
            self._kat_startowy = os.path.dirname(sc)
            self.le_cel.setText(sc)

    def _aktualizuj_ok(self, *_):
        ok = (
            bool(self.le_baza_pul.text().strip()) and
            bool(self.le_wydz.text().strip()) and
            bool(self.le_obreby.text().strip()) and
            bool(self.le_cel.text().strip())
        )
        self.pushButton_ok.setEnabled(ok)

    def wybor(self):
        """Zwraca dict ze ścieżkami wybranymi przez użytkownika."""
        return {
            'baza_pul_sc': self.le_baza_pul.text().strip(),
            'wydz_sc': self.le_wydz.text().strip(),
            'obreby_sc': self.le_obreby.text().strip(),
            'cel_sc': self.le_cel.text().strip(),
        }
