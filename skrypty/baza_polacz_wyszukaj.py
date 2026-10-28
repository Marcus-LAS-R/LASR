"""Połącz bazy TPU - wyszukiwanie baz w folderze obrębów/gmin i okna
startowe.

Reguły wyszukiwania (znajdz_bazy):
  - bazy bezpośrednio we wskazanym folderze -> łączone tylko one;
  - w przeciwnym razie najpłytszy poziom podfolderów, na którym jest
    jakakolwiek baza (jeden poziom dla całego drzewa) - bazy głębiej są
    pomijane i pokazywane użytkownikowi;
  - pomijane foldery: nazwa zawiera 'arch' albo 'kopi' (Archiwum,
    Kopie_manipulacyjne, kopia...), zaczyna się od '_', folder wyniku
    Baza_polaczona;
  - bazy BDO (nazwa *_BDO) i zwykłe nie są mieszane - tryb wybiera
    użytkownik; pliki baza_polaczona* (wcześniejsze wyniki) pomijane.
"""
import os
import platform

from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QGridLayout, QGroupBox, QLabel,
    QRadioButton, QScrollArea, QVBoxLayout, QWidget,
)
from .przyciski import QDialogButtonBox

from .baza_wybor_katalogu_dialog import WybierzKatalogDialog

KATALOG_WYNIKU = 'Baza_polaczona'
_POMIN_FRAGMENTY = ('arch', 'kopi')


def pomin_folder(nazwa):
    n = nazwa.lower()
    return (n.startswith('_') or n == KATALOG_WYNIKU.lower() or
            any(f in n for f in _POMIN_FRAGMENTY))


def czy_bdo(sciezka):
    return os.path.splitext(os.path.basename(sciezka))[0].upper().endswith(
        '_BDO')


def rozszerzenie_baz():
    return '.mdb' if platform.system()[:3] == 'Win' else '.sqlite'


def bazy_w_folderze(folder, pliki, rozszerzenie, bdo):
    return sorted(
        os.path.join(folder, p) for p in pliki
        if p.lower().endswith(rozszerzenie) and
        not p.lower().startswith('baza_polaczona') and
        czy_bdo(p) == bdo)


def znajdz_bazy(katalog, bdo, rozszerzenie=None):
    """Zwraca (poziom, foldery, glebsze): poziom - głębokość wybranych
    baz (0 = wskazany folder), foldery {folder: [bazy]} na tym poziomie,
    glebsze {folder: [bazy]} - bazy głębiej (pominięte). Gdy brak baz:
    (None, {}, {})."""
    rozszerzenie = rozszerzenie or rozszerzenie_baz()
    katalog = os.path.normpath(katalog)
    wszystkie = {}
    for folder, podfoldery, pliki in os.walk(katalog):
        podfoldery[:] = sorted(p for p in podfoldery if not pomin_folder(p))
        bazy = bazy_w_folderze(folder, pliki, rozszerzenie, bdo)
        if bazy:
            wzgl = os.path.relpath(folder, katalog)
            poziom = 0 if wzgl == '.' else len(wzgl.split(os.sep))
            wszystkie[folder] = (poziom, bazy)
    if not wszystkie:
        return None, {}, {}
    poziom = min(p for p, _ in wszystkie.values())
    foldery = {f: b for f, (p, b) in sorted(wszystkie.items())
               if p == poziom}
    glebsze = {f: b for f, (p, b) in sorted(wszystkie.items())
               if p > poziom}
    return poziom, foldery, glebsze


def sciezka_wzgledna(sciezka, katalog):
    wzgl = os.path.relpath(sciezka, katalog)
    return os.path.basename(sciezka) if wzgl.startswith('..') else wzgl


class StartPolaczDialog(WybierzKatalogDialog):
    """Okno wyboru folderu z obrębami/gminami + tryb (bazy zwykłe / BDO)
    + opcja utworzenia zanonimizowanej bazy BDO po połączeniu."""

    def __init__(self, iface, tytul, wzorzec):
        super().__init__(iface, tytul, wzorzec)
        self.ui.label_naglowek.setText(
            'Wskaż folder z obrębami lub gminami (bazy szukane też '
            'w podfolderach):')

        box = QGroupBox('Łącz bazy', self)
        box.setGeometry(20, 100, 480, 96)
        lay = QVBoxLayout(box)
        self.rb_zwykle = QRadioButton('zwykłe (bez *_BDO)')
        self.rb_bdo = QRadioButton('BDO (tylko *_BDO)')
        self.rb_zwykle.setChecked(True)
        self.cb_utworz_bdo = QCheckBox(
            'Utwórz bazę BDO (kopia połączonej, zanonimizowana jak w '
            '"Anonimizuj bazy TPU", bez kwerend)')
        self.cb_utworz_bdo.setEnabled(rozszerzenie_baz() == '.mdb')
        for w in (self.rb_zwykle, self.rb_bdo, self.cb_utworz_bdo):
            lay.addWidget(w)
        self.rb_bdo.toggled.connect(self._tryb)

        self.ui.pushButton_ok.move(20, 208)
        self.ui.pushButton_cancel.move(340, 208)
        self.resize(520, 258)

    def _tryb(self, *_):
        bdo = self.rb_bdo.isChecked()
        self.cb_utworz_bdo.setEnabled(not bdo and rozszerzenie_baz() == '.mdb')
        if bdo:
            self.cb_utworz_bdo.setChecked(False)

    def bdo(self):
        return self.rb_bdo.isChecked()

    def utworz_bdo(self):
        return self.cb_utworz_bdo.isEnabled() and \
            self.cb_utworz_bdo.isChecked()


class WyborBazyWFolderzeDialog(QDialog):
    """Foldery z więcej niż jedną bazą na wybranym poziomie - wskazanie
    jednej bazy albo pominięcie folderu."""
    _WYBIERZ = '— wybierz bazę —'
    _POMIN = '(pomiń folder)'

    def __init__(self, iface, foldery, katalog):
        super().__init__(iface.mainWindow())
        self.setWindowTitle('Połącz bazy TPU — kilka baz w folderze')
        self.setMinimumWidth(640)
        self._combo = {}

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            'W poniższych folderach jest więcej niż jedna baza - wskaż, '
            'którą łączyć:'))
        siatka_w = QWidget()
        siatka = QGridLayout(siatka_w)
        for i, (folder, bazy) in enumerate(foldery.items()):
            siatka.addWidget(QLabel(sciezka_wzgledna(folder, katalog)), i, 0)
            cb = QComboBox()
            cb.addItem(self._WYBIERZ, None)
            for b in bazy:
                cb.addItem(os.path.basename(b), b)
            cb.addItem(self._POMIN, '')
            cb.currentIndexChanged.connect(self._aktualizuj)
            siatka.addWidget(cb, i, 1)
            self._combo[folder] = cb
        siatka.setColumnStretch(1, 1)
        przewijanie = QScrollArea()
        przewijanie.setWidgetResizable(True)
        przewijanie.setWidget(siatka_w)
        lay.addWidget(przewijanie)

        self.przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.przyciski.button(QDialogButtonBox.Ok).setText('Dalej')
        self.przyciski.button(QDialogButtonBox.Cancel).setText('Anuluj')
        self.przyciski.accepted.connect(self.accept)
        self.przyciski.rejected.connect(self.reject)
        lay.addWidget(self.przyciski)
        self._aktualizuj()

    def _aktualizuj(self, *_):
        self.przyciski.button(QDialogButtonBox.Ok).setEnabled(all(
            cb.currentData() is not None for cb in self._combo.values()))

    def wybor(self):
        """{folder: ścieżka bazy albo None (folder pominięty)}."""
        return {f: (cb.currentData() or None)
                for f, cb in self._combo.items()}
