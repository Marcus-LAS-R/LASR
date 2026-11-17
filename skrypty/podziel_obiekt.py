# -*- coding: utf-8 -*-
"""Podziel obiekt - Gminami / Obrębami (menu Narzędziowe › Podziel obiekt;
trzecia pozycja - Na UPUL i ISL - to rozdziel_upul_isl).

Wskazuje się bazę (.mdb/.sqlite) i/lub folder SHP. Skrypt ustala jednostki
- gminy (MUNICIPALITY_CD - każdy kod osobno, miasto i obszar wiejski to
dwie gminy) albo obręby - z bazy (F_COMMUNITY/F_PARCEL) i z warstw SHP
(COUNTY..COMMUNITY, PARCELID, ADR_LES/ADR_BDL, identyfikatory TERYT),
a dla każdej zaznaczonej tworzy obok bazy (bez bazy - obok folderu SHP)
folder <TERYT6>_<typ>_<Nazwa>_<M|MW|OW> (gmina) albo
<TERYT6>_<typ>.<obręb>_<Nazwa> (obręb) z:
  - kopią bazy (ta sama nazwa pliku) bez obrębów, działek, wydzieleń
    i właścicieli innych jednostek,
  - SHP/ - warstwami ograniczonymi do obiektów jednostki.
Słownik gmin F_MUNICIPALITY nie jest okrajany - gminy, których w nim brak,
są zgłaszane i (po potwierdzeniu) dopisywane do baz wynikowych.

Silnik czyszczenia bazy i podziału grafiki - rozdziel_upul_isl/core
(grupą jest jednostka zamiast UPUL/ISL). Nazwy, przydział, raport -
podziel_obiekt_pliki.py. Baza i SHP źródłowe nie są zmieniane.
"""
import os
import shutil

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QDialog, QFileDialog,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout,
)
from qgis.core import (
    Qgis, QgsFeatureRequest, QgsMessageLog, QgsVectorLayer,
)

from . import podziel_obiekt_pliki as pg
from .baza_wrapper import Baza
from .funkcje import katalog_startowy
from .przyciski import QDialogButtonBox, QMessageBox
from .pw import PasekPostepu
from .rozdziel_upul_isl.core import rozdziel as R
from .rozdziel_upul_isl.gui.dialog import _LiczbaItem
from .rozdziel_upul_isl.gui.dialog_gmin import (
    opis_dopisanych, zapytaj_o_gminy,
)
from .spakuj_do_opiniowania import _pole, _tekst, _warstwa
from .waypointy import katalog_raportow
from .znacznik_czasu import znacznik

GMINY, OBREBY = pg.GMINY, pg.OBREBY

# warstwa z nazwami jednostek i pola identyfikatora
_WARSTWA_NAZW = {GMINY: ('GMIN.shp', ('IDJEDNOSTK', 'JPT_KOD_JE', 'TERYT')),
                 OBREBY: ('OBR.shp', ('IDOBREBU', 'JPT_KOD_JE', 'TERYT'))}
_POLA_NAZWY = ('NAZWAWLASN', 'JPT_NAZWA_', 'NAZWA', 'NAME')
_SPOSOBY_ADRESOWE = ('ADR_LES', 'ADR_BDL')


def _tytul(tryb):
    return pg.OPISY[tryb][0]


def _log(tekst, poziom=Qgis.Info):
    QgsMessageLog.logMessage(f'Podziel obiekt: {tekst}', 'Las-R', poziom)


# --------------------------------------------------------------------------
# odczyt jednostek
# --------------------------------------------------------------------------

def obreby_bazy(baza_sc):
    """[(klucz, nazwa gminy, nazwa obrębu, działek)] z bazy albo None
    (brak połączenia)."""
    baza = Baza(baza_sc, pomin_blokade=True)
    if not baza.polacz():
        return None
    try:
        return [(o.klucz, o.gmina, o.nazwa, o.dzialki)
                for o in R.pobierz_obreby(baza)]
    finally:
        baza.zamknij()


def nazwy_z_shp(folder_shp, tryb):
    """{grupa: nazwa} z <folder SHP>/GMIN.shp albo OBR.shp."""
    plik, pola_id = _WARSTWA_NAZW[tryb]
    lyr = _warstwa(os.path.join(folder_shp, plik))
    if lyr is None:
        return {}
    i_id, i_nazwa = _pole(lyr, pola_id), _pole(lyr, _POLA_NAZWY)
    if i_id < 0 or i_nazwa < 0:
        return {}
    wyn = {}
    zad = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)
    for f in lyr.getFeatures(zad):
        g = pg.grupa_z_id(_tekst(f[i_id]), tryb)
        if g:
            wyn[g] = _tekst(f[i_nazwa])
    return wyn


def klucze_z_shp(folder_shp, znane=()):
    """Klucze obrębów ze wszystkich warstw folderu. Warstwy z adresem
    leśnym (bez kodu województwa) czytane na końcu - klucz odtwarzany
    z obrębów znanych z bazy i z pozostałych warstw. Zwraca (klucze,
    uwagi)."""
    klucze, uwagi = set(), []
    mapa = {k[1:]: k for k in znane}
    adresowe = []
    zad = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry)

    def _czytaj(lyr, f_klucz):
        for feat in lyr.getFeatures(zad):
            k = f_klucz(feat)
            if k:
                klucze.add(k)
                mapa.setdefault(k[1:], k)

    for plik in sorted(os.listdir(folder_shp)):
        if not plik.lower().endswith('.shp'):
            continue
        nazwa = os.path.splitext(plik)[0]
        lyr = QgsVectorLayer(os.path.join(folder_shp, plik), nazwa, 'ogr')
        if not lyr.isValid():
            uwagi.append(f'{plik}: nie udało się wczytać')
            continue
        sposob, f_klucz = R._funkcja_klucza(lyr, mapa)
        if f_klucz is None:
            continue
        if sposob in _SPOSOBY_ADRESOWE:
            adresowe.append((lyr, f_klucz))
            continue
        _czytaj(lyr, f_klucz)
    # mapa jest przekazana przez referencję - f_adr widzi już pełną mapę
    for lyr, f_klucz in adresowe:
        _czytaj(lyr, f_klucz)
    return klucze, uwagi


# --------------------------------------------------------------------------
# dialog
# --------------------------------------------------------------------------

class PodzielObiektDialog(QDialog):
    def __init__(self, iface, tryb):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.tryb = tryb
        _, _, self._mian, self._dop, _ = pg.OPISY[tryb]
        self._jedn = {}
        self._uwagi = []
        self.setWindowTitle(_tytul(tryb))
        self.resize(760, 560)
        lay = QVBoxLayout(self)

        if tryb == GMINY:
            tekst = ('Dzieli bazę i/lub warstwy SHP na gminy (wg '
                     'MUNICIPALITY - miasto i obszar wiejski osobno). Dla '
                     'każdej zaznaczonej gminy obok bazy (bez bazy - obok '
                     'folderu SHP) powstaje folder <TERYT>_<typ>_<Nazwa>_'
                     '<M/OW> z kopią bazy tylko z tą gminą i podfolderem SHP '
                     'z jej obiektami.')
        else:
            tekst = ('Dzieli bazę i/lub warstwy SHP na obręby ewidencyjne. '
                     'Dla każdego zaznaczonego obrębu obok bazy (bez bazy - '
                     'obok folderu SHP) powstaje folder <TERYT>_<typ>.<obręb>'
                     '_<Nazwa> z kopią bazy tylko z tym obrębem i podfolderem '
                     'SHP z jego obiektami.')
        opis = QLabel(tekst + ' Źródła nie są zmieniane.')
        opis.setWordWrap(True)
        lay.addWidget(opis)

        r = QHBoxLayout()
        r.addWidget(QLabel('Baza:'))
        self.le_baza = QLineEdit()
        r.addWidget(self.le_baza, 1)
        b = QPushButton('Wskaż...')
        b.clicked.connect(self._wybierz_baze)
        r.addWidget(b)
        lay.addLayout(r)

        self.chk_grafika = QCheckBox(
            'Podziel również grafikę (wszystkie warstwy SHP z folderu - do '
            'podfolderów SHP)')
        lay.addWidget(self.chk_grafika)
        r = QHBoxLayout()
        r.addWidget(QLabel('    Folder SHP:'))
        self.le_shp = QLineEdit()
        r.addWidget(self.le_shp, 1)
        self.btn_shp = QPushButton('Wskaż...')
        self.btn_shp.clicked.connect(self._wybierz_shp)
        r.addWidget(self.btn_shp)
        lay.addLayout(r)
        self.chk_grafika.toggled.connect(self.le_shp.setEnabled)
        self.chk_grafika.toggled.connect(self.btn_shp.setEnabled)
        self.le_shp.setEnabled(False)
        self.btn_shp.setEnabled(False)
        for sygnal in (self.le_baza.textChanged, self.le_shp.textChanged,
                       self.chk_grafika.toggled):
            sygnal.connect(self._zmiana_zrodel)

        r = QHBoxLayout()
        self.btn_odczyt = QPushButton(
            'Odczytaj gminy' if tryb == GMINY else 'Odczytaj obręby')
        self.btn_odczyt.clicked.connect(self._odczytaj)
        r.addWidget(self.btn_odczyt)
        r.addStretch(1)
        lay.addLayout(r)

        kolumny = ['', f'Folder ({self._mian})', 'Obrębów', 'Działek',
                   'Źródło']
        self.tabela = QTableWidget(0, len(kolumny))
        self.tabela.setHorizontalHeaderLabels(kolumny)
        self.tabela.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.itemChanged.connect(self._aktualizuj_ok)
        lay.addWidget(self.tabela, 1)

        r = QHBoxLayout()
        for etykieta, stan in (('Zaznacz wszystkie', True),
                               ('Odznacz wszystkie', False)):
            b = QPushButton(etykieta)
            b.clicked.connect(lambda _=False, s=stan: self._zaznacz(s))
            r.addWidget(b)
        r.addStretch(1)
        lay.addLayout(r)

        self.info = QLabel('')
        self.info.setWordWrap(True)
        lay.addWidget(self.info)

        przyciski = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.btn_ok = przyciski.addButton('Podziel',
                                          QDialogButtonBox.AcceptRole)
        przyciski.accepted.connect(self.accept)
        przyciski.rejected.connect(self.reject)
        lay.addWidget(przyciski)
        self.btn_ok.setEnabled(False)

    # --- źródła ---

    def _baza(self):
        sc = self.le_baza.text().strip()
        return sc if os.path.isfile(sc) else ''

    def _shp(self):
        if not self.chk_grafika.isChecked():
            return ''
        kat = self.le_shp.text().strip()
        return kat if os.path.isdir(kat) else ''

    def _wybierz_baze(self):
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę', katalog_startowy(
                self.le_baza.text() or None, szukaj_bazy=True,
                iface=self.iface),
            'Access MDB (*.mdb);;SQLite (*.sqlite)')
        if not sc:
            return
        self.le_baza.setText(sc)
        shp = os.path.join(os.path.dirname(sc), 'SHP')
        if not self.le_shp.text().strip() and os.path.isdir(shp):
            self.le_shp.setText(shp)
            self.chk_grafika.setChecked(True)
        self._odczytaj()

    def _wybierz_shp(self):
        kat = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder SHP', self.le_shp.text() or katalog_startowy(
                self.le_baza.text() or None, iface=self.iface))
        if kat:
            self.le_shp.setText(kat)
            self.chk_grafika.setChecked(True)
            self._odczytaj()

    def _zmiana_zrodel(self, *_):
        # jednostki odczytane z innych źródeł są nieaktualne
        self._jedn = {}
        self.tabela.setRowCount(0)
        self.info.setText(f'Wskaż źródła i kliknij "{self.btn_odczyt.text()}".')
        self._aktualizuj_ok()

    def _odczytaj(self):
        baza_sc, folder_shp = self._baza(), self._shp()
        if not baza_sc and not folder_shp:
            self.info.setText('Wskaż bazę i/lub folder SHP (zaznacz '
                              '"Podziel również grafikę").')
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            uwagi, obr_bazy, klucze_shp, nazwy = [], [], set(), {}
            if baza_sc:
                obr_bazy = obreby_bazy(baza_sc)
                if obr_bazy is None:
                    obr_bazy = []
                    uwagi.append('BŁĄD: nie udało się połączyć z bazą.')
            if folder_shp:
                klucze_shp, u = klucze_z_shp(
                    folder_shp, [o[0] for o in obr_bazy])
                uwagi += u
                nazwy = nazwy_z_shp(folder_shp, self.tryb)
            jedn, zle = pg.zbierz(obr_bazy, klucze_shp, nazwy, self.tryb)
            if zle:
                uwagi.append(f'{len(zle)} obrębów bez poprawnego kodu - '
                             'pominięte')
        finally:
            QApplication.restoreOverrideCursor()
        self._jedn, self._uwagi = jedn, uwagi
        self._wypelnij()

    def _wypelnij(self):
        self.tabela.setSortingEnabled(False)
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(len(self._jedn))
        domyslne = pg.domyslnie_wybrane(self._jedn)
        for w, g in enumerate(sorted(self._jedn)):
            j = self._jedn[g]
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if g in domyslne
                              else Qt.Unchecked)
            chk.setData(Qt.UserRole, g)
            self.tabela.setItem(w, 0, chk)
            komorki = [QTableWidgetItem(j.folder),
                       _LiczbaItem(str(len(j.obreby)), len(j.obreby)),
                       _LiczbaItem(str(j.dzialki), j.dzialki),
                       QTableWidgetItem(j.zrodla)]
            for k, item in enumerate(komorki, 1):
                if k in (2, 3):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabela.setItem(w, k, item)
        self.tabela.blockSignals(False)
        self.tabela.setSortingEnabled(True)
        self.tabela.resizeColumnsToContents()
        linie = [f'Znaleziono {self._dop}: {len(self._jedn)}.']
        if len(domyslne) < len(self._jedn):
            linie.append('Jednostki tylko z SHP (zwykle sąsiedzi z warstw '
                         'EGiB) są odznaczone - ich obiekty nie trafią '
                         'nigdzie.')
        if len(self._jedn) == 1:
            linie.append('Jest tylko jedna jednostka - nie ma czego dzielić.')
        linie += self._uwagi
        self.info.setText('\n'.join(linie))
        self._aktualizuj_ok()

    def _zaznacz(self, stan):
        self.tabela.blockSignals(True)
        for w in range(self.tabela.rowCount()):
            self.tabela.item(w, 0).setCheckState(
                Qt.Checked if stan else Qt.Unchecked)
        self.tabela.blockSignals(False)
        self._aktualizuj_ok()

    def wybrane(self):
        wyn = set()
        for w in range(self.tabela.rowCount()):
            it = self.tabela.item(w, 0)
            if it is not None and it.checkState() == Qt.Checked:
                wyn.add(it.data(Qt.UserRole))
        return wyn

    def _aktualizuj_ok(self, *_):
        self.btn_ok.setEnabled(bool(self._jedn) and bool(self.wybrane()))

    def wybor(self):
        return {'tryb': self.tryb, 'baza_sc': self._baza(),
                'folder_shp': self._shp(), 'jednostki': self._jedn,
                'wybrane': self.wybrane(), 'uwagi': list(self._uwagi)}


# --------------------------------------------------------------------------
# podział
# --------------------------------------------------------------------------

def _potwierdz_konflikty(iface, konflikty, tryb):
    innej = pg.OPISY[tryb][4]
    obce = sum(len(o) for _, _, o in konflikty)
    odp = QMessageBox.question(
        iface.mainWindow(), _tytul(tryb),
        f'{len(konflikty)} wydzieleń ma rozliczenie powierzchni obejmujące '
        f'łącznie {obce} działek {innej} (albo niezaznaczonej jednostki).'
        '\n\nJeśli będziesz kontynuować, wydzielenie trafi do jednostki '
        f'z adresu leśnego, a jego rozliczenie na działkach {innej} zostanie '
        'usunięte - trzeba będzie ponownie rozliczyć powierzchnię (lista '
        'w raporcie).\n\nKontynuować?',
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    return odp == QMessageBox.Yes


def _podziel_baze(baza_sc, foldery, jedn, przydzial, analiza, nowe_gminy,
                  uwagi, postep):
    wyniki = {}
    nazwa = os.path.basename(baza_sc)
    krok = 70 / max(len(foldery), 1)
    for i, (g, kat) in enumerate(sorted(foldery.items())):
        if not jedn[g].w_bazie:
            continue  # jednostka tylko z SHP - pusta kopia bazy na nic
        sc = os.path.join(kat, nazwa)
        try:
            os.makedirs(kat, exist_ok=True)
            R.skopiuj_baze(baza_sc, sc)
        except OSError as e:
            wyniki[g] = (f'nie udało się skopiować bazy ({e})', None)
            continue
        kopia = Baza(sc)
        if not kopia.polacz():
            wyniki[g] = ('nie udało się połączyć z kopią bazy', None)
            continue
        try:
            licz = R.wyczysc_kopie(kopia, przydzial, g,
                                   analiza['arodes_grupa'],
                                   analiza['obreby_adr'])
            if licz is not None and nowe_gminy:
                dop = R.dopisz_gminy_do_kopii(kopia, nowe_gminy)
                if dop is None or dop:
                    uwagi.append(opis_dopisanych(jedn[g].folder, dop,
                                                 nowe_gminy))
        finally:
            kopia.zamknij()
        if licz is None:
            try:
                os.remove(sc)
            except OSError:
                pass
            wyniki[g] = ('błąd czyszczenia kopii - szczegóły w logu Las-R, '
                         'kopia usunięta', None)
            continue
        R.kompaktuj(sc)
        wyniki[g] = (sc, licz)
        postep.setValue(int(10 + krok * (i + 1)))
        QApplication.processEvents()
    return wyniki


def _nazwy_gmin(jedn, tryb):
    """Podpowiedzi nazw do słownika gmin z jednostek (tryb GMINY)."""
    if tryb != GMINY:
        return {}
    return {(g[:2], g[2:4], g[4:7]): j.nazwa for g, j in jedn.items()
            if j.nazwa}


def uruchom(iface, tryb=GMINY):
    dlg = PodzielObiektDialog(iface, tryb)
    if dlg.exec_() != QDialog.Accepted:
        return False
    return podziel(iface, dlg.wybor())


def uruchom_gminami(iface):
    return uruchom(iface, GMINY)


def uruchom_obrebami(iface):
    return uruchom(iface, OBREBY)


def podziel(iface, wybor):  # noqa
    tryb = wybor['tryb']
    tytul, _, _, dop, innej = pg.OPISY[tryb]
    baza_sc, folder_shp = wybor['baza_sc'], wybor['folder_shp']
    jedn, wybrane = wybor['jednostki'], wybor['wybrane']
    katalog = os.path.dirname(baza_sc) if baza_sc else \
        os.path.dirname(os.path.normpath(folder_shp))
    foldery = pg.foldery_wynikowe(katalog, jedn, wybrane)
    przydzial = pg.przydzial(jedn, wybrane)

    istn = pg.istniejace(foldery, os.path.basename(baza_sc) if baza_sc
                         else None, bool(folder_shp))
    if istn:
        odp = QMessageBox.question(
            iface.mainWindow(), tytul,
            'Istnieją już wyniki poprzedniego podziału:\n\n' +
            '\n'.join(istn[:20]) + ('\n...' if len(istn) > 20 else '') +
            '\n\nNadpisać je?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if odp != QMessageBox.Yes:
            return False

    analiza = None
    if baza_sc:
        baza = Baza(baza_sc, pomin_blokade=True)
        if not baza.polacz():
            iface.messageBar().pushMessage(
                'BŁĄD', 'Nie udało się połączyć z bazą.', Qgis.Critical, 0)
            return False
        try:
            analiza = R.analizuj_wydzielenia(baza, przydzial)
            # słownik gmin nie jest okrajany; brakujące gminy - pytanie
            nowe_gminy = zapytaj_o_gminy(iface.mainWindow(), tytul, baza,
                                         _nazwy_gmin(jedn, tryb))
        finally:
            baza.zamknij()
        if nowe_gminy is None:
            return False
        if analiza['konflikty'] and not _potwierdz_konflikty(
                iface, analiza['konflikty'], tryb):
            rap = R.zapisz_raport_konfliktow(
                katalog_raportow(katalog), analiza['konflikty'], tryb,
                tytul.upper(), {g: j.folder for g, j in jedn.items()})
            iface.messageBar().pushMessage(
                'BŁĄD', 'Przerwano - nic nie utworzono. Wydzielenia na '
                'granicy jednostek: ' + rap, Qgis.Critical, 0)
            return False

    iface.messageBar().clearWidgets()
    postep = PasekPostepu(iface).stworz_pasek(tytul)
    postep.setValue(5)

    wyniki_baz, uwagi = {}, list(wybor.get('uwagi', ()))
    if baza_sc:
        wyniki_baz = _podziel_baze(baza_sc, foldery, jedn, przydzial,
                                   analiza, nowe_gminy, uwagi, postep)

    raport_grafiki = []
    if folder_shp:
        katalogi = {g: os.path.join(kat, pg.FOLDER_SHP)
                    for g, kat in foldery.items()}
        for kat in katalogi.values():
            if os.path.isdir(kat):
                shutil.rmtree(kat, ignore_errors=True)
        raport_grafiki = R.podziel_grafike(folder_shp, katalogi, przydzial)
    postep.setValue(95)

    tekst = pg.tekst_raportu(
        [('Baza', baza_sc), ('Folder SHP', folder_shp),
         ('Foldery wynikowe w', katalog)],
        jedn, wybrane, foldery, wyniki_baz, analiza, raport_grafiki,
        uwagi, tryb)
    rap = os.path.join(katalog_raportow(katalog),
                       f'raport_podzial_{tryb}_{znacznik()}.txt')
    try:
        with open(rap, 'w', encoding='utf-8') as f:
            f.write(tekst)
    except OSError as e:
        _log(f'nie udało się zapisać raportu {rap}: {e}', Qgis.Warning)
        rap = '(nie zapisano)'
    postep.setValue(100)
    iface.messageBar().clearWidgets()

    bledy = [jedn[g].folder for g, (_, licz) in wyniki_baz.items()
             if licz is None]
    bledy_shp = [x[0] for x in raport_grafiki if x[4]]
    tresc = f'{dop.capitalize()}: {len(foldery)}, w {katalog}. Raport: {rap}'
    if bledy or bledy_shp:
        iface.messageBar().pushMessage(
            'PODZIAŁ Z BŁĘDAMI', tresc + '. Błędy: ' +
            ', '.join(bledy + bledy_shp) + ' - szczegóły w raporcie i logu '
            'Las-R', Qgis.Warning, 0)
    else:
        iface.messageBar().pushMessage('PODZIAŁ ZAKOŃCZONY', tresc,
                                       Qgis.Success, 0)

    if analiza and analiza['rozliczenie_puste']:
        QMessageBox.warning(
            iface.mainWindow(), tytul,
            'Rozliczenie powierzchni wydzieleń (F_AROD_LAND_USE) w bazie '
            'źródłowej było puste.\n\nPo podziale rozlicz powierzchnię '
            'wydzieleń w bazach wynikowych.')
    elif analiza and analiza['konflikty']:
        QMessageBox.warning(
            iface.mainWindow(), tytul,
            f'{len(analiza["konflikty"])} wydzieleń miało rozliczenie na '
            f'działkach {innej} - ich rozliczenie jest teraz niepełne.'
            '\n\nPonownie rozlicz powierzchnię wydzieleń (lista w raporcie).')
    return not bledy
