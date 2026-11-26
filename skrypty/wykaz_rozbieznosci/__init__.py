# -*- coding: utf-8 -*-
"""Wykaz rozbieżności (dokumentacja geodezyjna, "użytki gruntowe leśne do
wylesień") - zestawienie EGiB (stan stary) vs UPUL i stan na gruncie
(stan nowy) wg wzoru LP (materialy/Wykaz rozbieznosci, Łętownia).

Bazy szukane we wskazanym folderze tak jak w "Połącz bazy TPU"
(baza_polacz_wyszukaj.znajdz_bazy: wskazany folder albo najpłytszy poziom
podfolderów z bazami, pomijane Archiwum/Kopie/_*). Wynik w folderze
Wykaz_rozbieznosci_<znacznik> we wskazanym folderze:
  Obreby/<gmina>_<obręb>.docx  - osobno dla każdego obrębu,
  Gminy/<gmina>.docx           - razem dla gminy,
  Wykaz_rozbieznosci_calosc.docx - cały obiekt.

Kolumna 5a (klasoużytek nowy) ze słowników w dane.py (LZ -> Lz, INNE WYL
wg informacji różnych); bez dopasowania - pusta komórka z żółtym tłem do
ręcznego uzupełnienia. Gmina/obręb/nr działki scalane w obrębie działki.
"""
import os
import re

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QGroupBox, QHBoxLayout, QLabel,
    QLineEdit, QProgressDialog, QPushButton, QRadioButton, QVBoxLayout,
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

_TYTUL = 'Wykaz rozbieżności'
_KLUCZ_KAT = 'lasr/wykaz_rozbieznosci/katalog'
_KLUCZ_BDO = 'lasr/wykaz_rozbieznosci/bdo'


class StartDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle(_TYTUL)
        self.setMinimumWidth(560)
        ust = QgsSettings()
        lay = QVBoxLayout(self)

        lay.addWidget(QLabel(
            'Wskaż folder obiektu, gminy lub obrębu (bazy szukane też '
            'w podfolderach):'))
        wiersz = QHBoxLayout()
        self.le_kat = QLineEdit(ust.value(_KLUCZ_KAT, '') or
                                katalog_startowy(szukaj_bazy=True,
                                                 iface=iface))
        wiersz.addWidget(self.le_kat)
        pb = QPushButton('Wskaż...')
        pb.clicked.connect(self._wskaz)
        wiersz.addWidget(pb)
        lay.addLayout(wiersz)

        box = QGroupBox('Bazy')
        bl = QVBoxLayout(box)
        self.rb_zwykle = QRadioButton('zwykłe (bez *_BDO)')
        self.rb_bdo = QRadioButton('BDO (tylko *_BDO)')
        bdo = str(ust.value(_KLUCZ_BDO, 'false')).lower() == 'true'
        (self.rb_bdo if bdo else self.rb_zwykle).setChecked(True)
        bl.addWidget(self.rb_zwykle)
        bl.addWidget(self.rb_bdo)
        lay.addWidget(box)

        box = QGroupBox('Generuj wykazy')
        bl = QVBoxLayout(box)
        self.cb_obreby = QCheckBox('osobno dla każdego obrębu')
        self.cb_gminy = QCheckBox('razem dla gmin')
        self.cb_obiekt = QCheckBox('razem dla całego obiektu')
        for cb in (self.cb_obreby, self.cb_gminy, self.cb_obiekt):
            cb.setChecked(True)
            cb.toggled.connect(self._aktualizuj)
            bl.addWidget(cb)
        lay.addWidget(box)

        lay.addWidget(QLabel(
            'Kolumna 5a (klasoużytek nowy): LZ -> Lz; INNE WYL wg informacji '
            'różnych\n(GUR -> R + klasa, budynki/zabudowania/podwórko -> B). '
            'Pozostałe -\npuste komórki z żółtym tłem do uzupełnienia '
            'ręcznie.'))

        self.przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.przyciski.button(QDialogButtonBox.Ok).setText('Generuj')
        self.przyciski.button(QDialogButtonBox.Cancel).setText('Anuluj')
        self.przyciski.accepted.connect(self._ok)
        self.przyciski.rejected.connect(self.reject)
        lay.addWidget(self.przyciski)
        self.le_kat.textChanged.connect(self._aktualizuj)
        self._aktualizuj()

    def _wskaz(self):
        sc = przegladaj_katalog_z_podgladem(
            self, 'Folder z bazami', '*' + rozszerzenie_baz(),
            self.katalog())
        if sc:
            self.le_kat.setText(os.path.normpath(sc))

    def _aktualizuj(self, *_):
        self.przyciski.button(QDialogButtonBox.Ok).setEnabled(
            bool(self.katalog()) and any(self.zakres()))

    def _ok(self):
        if not os.path.isdir(self.katalog()):
            QMessageBox.warning(self, _TYTUL, 'Folder nie istnieje.')
            return
        ust = QgsSettings()
        ust.setValue(_KLUCZ_KAT, self.katalog())
        ust.setValue(_KLUCZ_BDO, self.bdo())
        self.accept()

    def katalog(self):
        return self.le_kat.text().strip().strip('"')

    def bdo(self):
        return self.rb_bdo.isChecked()

    def zakres(self):
        return (self.cb_obreby.isChecked(), self.cb_gminy.isChecked(),
                self.cb_obiekt.isChecked())


def _nazwa_pliku(tekst):
    tekst = re.sub(r'[\\/:*?"<>|]+', '_', tekst.strip())
    return re.sub(r'\s+', '_', tekst) or 'bez_nazwy'


def _lista(nazwy):
    wyn = []
    for n in nazwy:
        if n and n not in wyn:
            wyn.append(n)
    return ', '.join(wyn)


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


def _wczytaj(bazy, postep):
    """{klucz_obrebu: dane.Obreb} ze wszystkich baz + lista uwag."""
    obreby, uwagi = {}, []
    for i, sc in enumerate(bazy):
        postep.setLabelText('Odczyt bazy {} ({}/{})'.format(
            os.path.basename(sc), i + 1, len(bazy)))
        postep.setValue(i)
        QApplication.processEvents()
        if postep.wasCanceled():
            return None, uwagi
        baza = Baza(sc)
        try:
            if not baza.polacz():
                uwagi.append('Nie można połączyć z bazą: ' + sc)
                continue
            wynik = dane.pobierz(baza)
        except Exception as e:
            uwagi.append('{}: {}'.format(sc, e))
            continue
        finally:
            baza.zamknij()
        for k, obr in wynik.items():
            if not obr.dzialek:
                continue
            obr.bazy.append(sc)
            if k in obreby:
                obreby[k].wiersze.extend(obr.wiersze)
                obreby[k].bazy.append(sc)
                obreby[k].wiersze.sort(
                    key=lambda w: dane.klucz_dzialki(w.nr))
                uwagi.append('Obręb {} ({}) w kilku bazach - wiersze '
                             'połączone: {}'.format(
                                 obr.nazwa_obrebu, obr.kod,
                                 ', '.join(obreby[k].bazy)))
            else:
                obreby[k] = obr
    return obreby, uwagi


def _zadania(obreby, katalog_wyn, zakres):
    """[(ścieżka, wiersze, linie_tytułu)] wg wybranego zakresu."""
    z_obr, z_gm, z_obiekt = zakres
    po_kolei = sorted(obreby.values(), key=lambda o: o.klucz)
    gminy = {}
    for o in po_kolei:
        gminy.setdefault(o.klucz_gminy, []).append(o)
    zad = []
    if z_obr:
        for o in po_kolei:
            zad.append((
                os.path.join(katalog_wyn, 'Obreby', _nazwa_pliku(
                    '{}_{}_{}'.format(o.klucz[2], o.nazwa_gminy,
                                      o.nazwa_obrebu or o.klucz[3])) +
                    '.docx'),
                o.wiersze,
                {'OBRĘB EWIDENCYJNY:': 'OBRĘB EWIDENCYJNY: ' +
                 o.nazwa_obrebu,
                 'GMINA:': 'GMINA: ' + o.nazwa_gminy.upper(),
                 'POWIAT:': 'POWIAT: ' + o.nazwa_powiatu.upper()}))
    if z_gm:
        for kg, lista in gminy.items():
            o0 = lista[0]
            zad.append((
                os.path.join(katalog_wyn, 'Gminy', _nazwa_pliku(
                    '{}_{}'.format(kg[2], o0.nazwa_gminy)) + '.docx'),
                [w for o in lista for w in o.wiersze],
                {'OBRĘB EWIDENCYJNY:': ('OBRĘBY EWIDENCYJNE: ' if
                                        len(lista) > 1 else
                                        'OBRĘB EWIDENCYJNY: ') +
                 _lista(o.nazwa_obrebu for o in lista),
                 'GMINA:': 'GMINA: ' + o0.nazwa_gminy.upper(),
                 'POWIAT:': 'POWIAT: ' + o0.nazwa_powiatu.upper()}))
    if z_obiekt and po_kolei:
        nazwy_gm = _lista(o.nazwa_gminy.upper() for o in po_kolei)
        nazwy_pow = _lista(o.nazwa_powiatu.upper() for o in po_kolei)
        zad.append((
            os.path.join(katalog_wyn, 'Wykaz_rozbieznosci_calosc.docx'),
            [w for o in po_kolei for w in o.wiersze],
            {'OBRĘB EWIDENCYJNY:': None,
             'GMINA:': ('GMINY: ' if len(gminy) > 1 else 'GMINA: ') +
             nazwy_gm,
             'POWIAT:': ('POWIATY: ' if ', ' in nazwy_pow else 'POWIAT: ') +
             nazwy_pow}))
    return zad


def uruchom(iface):  # noqa
    try:
        import docx  # noqa: F401
    except ImportError:
        QMessageBox.critical(
            iface.mainWindow(), 'Brak pakietu python-docx',
            'Do generowania plików .docx wymagany jest pakiet python-docx. '
            'Zainstaluj go w Pythonie QGIS-a (powłoka OSGeo4W):\n\n'
            'python -m pip install python-docx')
        return
    from . import dokument

    dlg = StartDialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return
    katalog, zakres = os.path.normpath(dlg.katalog()), dlg.zakres()
    bazy = _wybierz_bazy(iface, katalog, dlg.bdo())
    if not bazy:
        return

    postep = QProgressDialog('', 'Przerwij', 0, len(bazy),
                             iface.mainWindow())
    postep.setWindowTitle(_TYTUL)
    postep.setWindowModality(Qt.WindowModal)
    postep.setMinimumDuration(0)
    obreby, uwagi = _wczytaj(bazy, postep)
    if obreby is None:
        postep.close()
        return
    if not obreby:
        postep.close()
        QMessageBox.warning(iface.mainWindow(), _TYTUL,
                            'W bazach nie ma obrębów z działkami.\n\n' +
                            '\n'.join(uwagi))
        return

    katalog_wyn = os.path.join(katalog, 'Wykaz_rozbieznosci_' + znacznik())
    zadania = _zadania(obreby, katalog_wyn, zakres)
    postep.setMaximum(len(zadania))
    zapisane = 0
    for i, (sc, wiersze, tytul) in enumerate(zadania):
        postep.setLabelText('Zapis: ' + os.path.relpath(sc, katalog_wyn))
        postep.setValue(i)
        QApplication.processEvents()
        if postep.wasCanceled():
            uwagi.append('Przerwano - zapisano {} z {} plików.'.format(
                zapisane, len(zadania)))
            break
        try:
            dokument.zapisz(sc, wiersze, tytul)
            zapisane += 1
        except Exception as e:
            uwagi.append('{}: {}'.format(os.path.basename(sc), e))
    postep.close()

    wiersze = sum(len(o.wiersze) for o in obreby.values())
    weryf = sum(w.do_weryfikacji for o in obreby.values()
                for w in o.wiersze)
    bez = [o.nazwa_obrebu for o in obreby.values() if not o.wiersze]
    tekst = ('Zapisano {} plików w:\n{}\n\nBazy: {}, obręby: {}, wiersze '
             'wykazu: {}, działki: {}.\nWiersze bez klasoużytku nowego '
             '(żółte, do uzupełnienia ręcznie): {}.').format(
        zapisane, katalog_wyn, len(bazy), len(obreby), wiersze,
        len({(o.klucz, w.nr) for o in obreby.values() for w in o.wiersze}),
        weryf)
    if bez:
        tekst += '\n\nObręby bez rozbieżności: ' + _lista(bez)
    if uwagi:
        tekst += '\n\nUwagi:\n' + '\n'.join(uwagi)
    odp = QMessageBox.information(
        iface.mainWindow(), _TYTUL, tekst + '\n\nOtworzyć folder z wynikami?',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
    if odp == QMessageBox.Yes and os.path.isdir(katalog_wyn):
        os.startfile(katalog_wyn)
