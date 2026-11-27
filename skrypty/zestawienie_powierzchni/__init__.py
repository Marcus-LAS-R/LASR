# -*- coding: utf-8 -*-
"""Utwórz zestawienie powierzchni (menu Generuj).

Dla każdej bazy we wskazanym folderze (szukane jak w "Połącz bazy TPU":
wskazany folder albo najpłytszy poziom podfolderów gmin/obrębów, pomijane
Archiwum/Kopie/_*) liczy powierzchnie z TABELI 1 (pkt 1, 2, 3, 4 - patrz
dane.py; obliczenia w skrypcie, kwerenda w bazie nie jest potrzebna) i
zapisuje do wskazanego folderu zestawienie_powierzchni_<znacznik>.xlsx:
  Całość               - wszystkie obręby + SUMA,
  <gmina> / <obręb>    - po arkuszu na bazę (obręby bazy + SUMA); nazwa:
                         baza z jednym obrębem -> nazwa obrębu, z jedną
                         gminą -> nazwa gminy, inaczej nazwa folderu bazy.
Obręby z samymi zerami są pomijane.
"""
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QProgressDialog, QPushButton, QRadioButton, QVBoxLayout,
)
from qgis.core import QgsSettings

from ..przyciski import QDialogButtonBox, QMessageBox
from ..baza_wrapper import Baza
from ..baza_wybor_katalogu_dialog import przegladaj_katalog_z_podgladem
from ..baza_polacz_wyszukaj import (
    WyborBazyWFolderzeDialog, rozszerzenie_baz, sciezka_wzgledna,
    znajdz_bazy,
)
from ..funkcje import katalog_startowy
from ..znacznik_czasu import znacznik
from . import dane

_TYTUL = 'Zestawienie powierzchni'
_KLUCZ_KAT = 'lasr/zestawienie_powierzchni/katalog'
_KLUCZ_WYN = 'lasr/zestawienie_powierzchni/katalog_wyniku'
_KLUCZ_BDO = 'lasr/zestawienie_powierzchni/bdo'


class StartDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle(_TYTUL)
        self.setMinimumWidth(560)
        ust = QgsSettings()
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel(
            'Folder obiektu, gmin lub obrębów (bazy szukane też '
            'w podfolderach):'))
        self.le_kat = self._wiersz_folderu(
            lay, ust.value(_KLUCZ_KAT, '') or
            katalog_startowy(szukaj_bazy=True, iface=iface), True)

        lay.addWidget(QLabel('Folder, do którego zapisać plik .xlsx:'))
        self.le_wyn = self._wiersz_folderu(
            lay, ust.value(_KLUCZ_WYN, '') or self.le_kat.text(), False)

        box = QGroupBox('Bazy')
        bl = QVBoxLayout(box)
        self.rb_zwykle = QRadioButton('zwykłe (bez *_BDO)')
        self.rb_bdo = QRadioButton('BDO (tylko *_BDO)')
        bdo = str(ust.value(_KLUCZ_BDO, 'false')).lower() == 'true'
        (self.rb_bdo if bdo else self.rb_zwykle).setChecked(True)
        bl.addWidget(self.rb_zwykle)
        bl.addWidget(self.rb_bdo)
        lay.addWidget(box)

        lay.addWidget(QLabel(
            'Arkusze: Całość (wszystkie obręby + suma) oraz osobny arkusz '
            'dla każdej bazy\n(nazwa obrębu albo gminy). Obręby bez '
            'powierzchni są pomijane.'))

        self.przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.przyciski.button(QDialogButtonBox.Ok).setText('Generuj')
        self.przyciski.button(QDialogButtonBox.Cancel).setText('Anuluj')
        self.przyciski.accepted.connect(self._ok)
        self.przyciski.rejected.connect(self.reject)
        lay.addWidget(self.przyciski)
        self.le_kat.textChanged.connect(self._aktualizuj)
        self.le_wyn.textChanged.connect(self._aktualizuj)
        self._aktualizuj()

    def _wiersz_folderu(self, lay, tekst, bazy):
        wiersz = QHBoxLayout()
        le = QLineEdit(tekst)
        wiersz.addWidget(le)
        pb = QPushButton('Wskaż...')
        pb.clicked.connect(lambda: self._wskaz(le, bazy))
        wiersz.addWidget(pb)
        lay.addLayout(wiersz)
        return le

    def _wskaz(self, le, bazy):
        start = self._sciezka(le)
        if bazy:
            sc = przegladaj_katalog_z_podgladem(
                self, 'Folder z bazami', '*' + rozszerzenie_baz(), start)
        else:
            sc = przegladaj_katalog_z_podgladem(
                self, 'Folder na zestawienie', '*.xlsx', start)
        if sc:
            le.setText(os.path.normpath(sc))

    @staticmethod
    def _sciezka(le):
        # "Kopiuj jako ścieżkę" w Windows dokleja cudzysłowy
        return le.text().strip().strip('"')

    def _aktualizuj(self, *_):
        self.przyciski.button(QDialogButtonBox.Ok).setEnabled(
            bool(self.katalog()) and bool(self.katalog_wyniku()))

    def _ok(self):
        for sc, opis in ((self.katalog(), 'z bazami'),
                         (self.katalog_wyniku(), 'na zestawienie')):
            if not os.path.isdir(sc):
                QMessageBox.warning(self, _TYTUL,
                                    'Folder {} nie istnieje.'.format(opis))
                return
        ust = QgsSettings()
        ust.setValue(_KLUCZ_KAT, self.katalog())
        ust.setValue(_KLUCZ_WYN, self.katalog_wyniku())
        ust.setValue(_KLUCZ_BDO, self.bdo())
        self.accept()

    def katalog(self):
        return self._sciezka(self.le_kat)

    def katalog_wyniku(self):
        return self._sciezka(self.le_wyn)

    def bdo(self):
        return self.rb_bdo.isChecked()


def _wybierz_bazy(iface, katalog, bdo):
    """Lista baz do przetworzenia (jak w Połącz bazy TPU) albo None."""
    poziom, foldery, glebsze = znajdz_bazy(katalog, bdo)
    if poziom is None:
        QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            'Nie znaleziono baz {} w folderze:\n{}'.format(
                '*_BDO' if bdo else '(bez *_BDO)', katalog))
        return None
    if glebsze:
        odp = QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            'Bazy głębiej w drzewie folderów zostaną pominięte:\n' +
            '\n'.join(sciezka_wzgledna(b, katalog)
                      for bb in glebsze.values() for b in bb)[:2000],
            QMessageBox.Yes | QMessageBox.Abort, QMessageBox.Abort)
        if odp != QMessageBox.Yes:
            return None
    wiele = {f: b for f, b in foldery.items() if len(b) > 1}
    bazy = [b[0] for b in foldery.values() if len(b) == 1]
    if wiele:
        dlg = WyborBazyWFolderzeDialog(iface, wiele, katalog)
        dlg.setWindowTitle(_TYTUL + ' — kilka baz w folderze')
        if dlg.exec_() != QDialog.Accepted:
            return None
        bazy += [b for b in dlg.wybor().values() if b]
    return sorted(bazy)


def _nazwa_zapasowa(sc, katalog):
    """Nazwa folderu bazy, a gdy baza leży wprost we wskazanym folderze -
    nazwa pliku bez rozszerzenia."""
    folder = os.path.dirname(sc)
    if os.path.normcase(folder) == os.path.normcase(katalog):
        return os.path.splitext(os.path.basename(sc))[0]
    return os.path.basename(folder)


def _wczytaj(bazy, katalog, postep):
    """[(nazwa_arkusza, wiersze)] + uwagi; None przy przerwaniu."""
    wynik, uwagi = [], []
    for i, sc in enumerate(bazy):
        wzgl = sciezka_wzgledna(sc, katalog)
        postep.setLabelText('Odczyt bazy {} ({}/{})'.format(
            os.path.basename(sc), i + 1, len(bazy)))
        postep.setValue(i)
        QApplication.processEvents()
        if postep.wasCanceled():
            return None, uwagi
        baza = Baza(sc)
        try:
            if not baza.polacz():
                uwagi.append('Nie można połączyć z bazą: ' + wzgl)
                continue
            obreby, uw = dane.pobierz(baza)
        except Exception as e:
            uwagi.append('{}: {}'.format(wzgl, e))
            continue
        finally:
            baza.zamknij()
        uwagi += ['{}: {}'.format(wzgl, u) for u in uw]
        if not obreby:
            uwagi.append('{}: brak obrębów z powierzchnią - pominięto'.format(
                wzgl))
            continue
        wynik.append((dane.nazwa_arkusza(obreby, _nazwa_zapasowa(sc, katalog)),
                      [o.wiersz() for o in obreby]))
    return wynik, uwagi


def uruchom(iface):
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        QMessageBox.critical(
            iface.mainWindow(), 'Brak pakietu openpyxl',
            'Do zapisu plików .xlsx wymagany jest pakiet openpyxl. '
            'Zainstaluj go w Pythonie QGIS-a (powłoka OSGeo4W):\n\n'
            'python -m pip install openpyxl')
        return
    from . import arkusz

    dlg = StartDialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return
    katalog = os.path.normpath(dlg.katalog())
    katalog_wyn = os.path.normpath(dlg.katalog_wyniku())
    bazy = _wybierz_bazy(iface, katalog, dlg.bdo())
    if not bazy:
        return

    postep = QProgressDialog('', 'Przerwij', 0, len(bazy),
                             iface.mainWindow())
    postep.setWindowTitle(_TYTUL)
    postep.setWindowModality(Qt.WindowModal)
    postep.setMinimumDuration(0)
    arkusze, uwagi = _wczytaj(bazy, katalog, postep)
    postep.close()
    if arkusze is None:
        return
    if not arkusze:
        QMessageBox.warning(iface.mainWindow(), _TYTUL,
                            'W bazach nie ma obrębów z powierzchnią.\n\n' +
                            '\n'.join(uwagi))
        return

    sc = os.path.join(katalog_wyn,
                      'zestawienie_powierzchni_' + znacznik() + '.xlsx')
    try:
        arkusz.zapisz(sc, arkusze)
    except Exception as e:
        QMessageBox.critical(iface.mainWindow(), _TYTUL,
                             'Nie udało się zapisać pliku:\n{}\n\n{}'.format(
                                 sc, e))
        return

    obrebow = sum(len(w) for _, w in arkusze)
    suma = round(sum(r[7] for _, w in arkusze for r in w), 4)
    tekst = ('Zapisano:\n{}\n\nBazy: {} (arkusze: {}), obręby: {}.\n'
             'Powierzchnia do rozliczenia razem: {:.4f} ha.').format(
        sc, len(bazy), len(arkusze), obrebow, suma)
    if uwagi:
        tekst += '\n\nUwagi:\n' + '\n'.join(uwagi)[:3000]
    odp = QMessageBox.information(
        iface.mainWindow(), _TYTUL, tekst + '\n\nOtworzyć plik?',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
    if odp == QMessageBox.Yes:
        os.startfile(sc)
