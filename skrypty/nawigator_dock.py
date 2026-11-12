"""Nawigator błędów - dockwidget do przeglądania na mapie błędów zebranych
przez skrypty kontrolne (Kontrola Ls, Kontrola słownikowa SULMN) w postaci
pliku waypointów (patrz skrypty/waypointy.py).

Wzorowany na wtyczce Go2NextFeature (materialy/Go2NextFeature3) - ten sam
mechanizm pan/zoom do geometrii bieżącego obiektu, ale zamiast skanować
całą warstwę, nawigator idzie po gotowej liście kluczy z pliku waypointów.
"""
from datetime import datetime

from qgis.PyQt.QtCore import QSettings, Qt, pyqtSignal
from qgis.PyQt.QtGui import QKeySequence
import os
import re

from qgis.PyQt.QtWidgets import (
    QAction, QApplication, QButtonGroup, QCheckBox, QComboBox, QDockWidget,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QRadioButton, QSizePolicy, QToolButton,
    QToolTip, QVBoxLayout, QWidget,
)
from .przyciski import QMessageBox
from qgis.core import (
    Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsFeatureRequest, QgsGeometry, QgsMapLayerProxyModel, QgsPointXY,
    QgsProject, QgsRectangle,
)
from qgis.gui import QgsMapLayerComboBox

from . import klepanie, waypointy
from .funkcje import (
    katalog_startowy, obiekt_warstwy, warstwy_o_nazwie, domyslna_warstwa,
)

# rodzaj klucza -> nazwy warstw, w których Nawigator go szuka
NAZWY_WARSTW = {
    'LANDID': ('LS',),
    'PARCELID': ('DZKAT',),
    'ADR_LES': ('WYDZ',),
}
OPIS_WARSTW = {'LANDID': 'Ls', 'PARCELID': 'działek', 'ADR_LES': 'wydzieleń'}

STATUS_ZROBIONE = 'ZROBIONE'
KLUCZ_MIGNIJ = 'LAS-R/nawigator/mignij'
LICZBA_MIGNIEC = 2  # QGIS domyślnie 3


class NawigatorDock(QDockWidget):

    tytul = 'Nawigator'

    # klepanie z raportu: wszystkie karty wklepane (ścieżka pliku postępu)
    klepanieZakonczone = pyqtSignal(str)

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(self.tytul)
        self.setSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.wiersze = []   # wszystkie wczytane wiersze (wszystkie sekcje)
        self.sciezka = None  # ścieżka do wczytanego pliku CSV
        self.pozycja = -1    # indeks w obrębie bieżącej sekcji
        # klepanie: pokaz_w_edytorze(adr) -> False, gdy karta Edytora
        # została przy niezapisanych zmianach (ustawia las_r)
        self.pokaz_w_edytorze = None

        self._zbuduj_ui()
        self._rejestruj_skroty()

    # ------------------------------------------------------------ UI ----

    def _zbuduj_ui(self):
        # ramka - granica panelu widoczna przy sąsiednich panelach (także
        # w ciemnym motywie); selektor po nazwie - nie dziedziczą jej ramki
        # elementów w środku
        glowny = QFrame(self)
        glowny.setObjectName('ramkaNawigatora')
        glowny.setStyleSheet(
            'QFrame#ramkaNawigatora { border: 1px solid '
            'rgba(128, 128, 128, 170); border-radius: 3px; }')
        self.setWidget(glowny)
        lay = QVBoxLayout(glowny)

        # warstwy dla kluczy z atrybutów - dobierane automatycznie po
        # wczytaniu pliku (_dobierz_warstwy); zwinięte do jednej linii,
        # "Zmień" rozwija pola tylko dla rodzajów kluczy z bieżącego pliku
        fra_warstwy_lin = QFrame(glowny)
        lay_warstwy_lin = QHBoxLayout(fra_warstwy_lin)
        lay_warstwy_lin.setContentsMargins(0, 0, 0, 0)
        self.lbl_warstwy = QLabel('Warstwy: -')
        self.lbl_warstwy.setWordWrap(True)
        self.btn_warstwy = QToolButton()
        self.btn_warstwy.setText('Zmień')
        self.btn_warstwy.setCheckable(True)
        self.btn_warstwy.setToolTip(
            'Pokaż/ukryj wybór warstw, w których Nawigator szuka obiektów '
            '(dobierane automatycznie z obiektu, z którego pochodzi plik).')
        lay_warstwy_lin.addWidget(self.lbl_warstwy, 1)
        lay_warstwy_lin.addWidget(self.btn_warstwy)
        lay.addWidget(fra_warstwy_lin)

        self.fra_warstwy = QFrame(glowny)
        lay_warstwy = QFormLayout(self.fra_warstwy)
        lay_warstwy.setContentsMargins(0, 0, 0, 0)
        self._pola_warstw = {}  # typ_klucza -> (etykieta, combo)
        self._wymuszona_wydz = False
        self._reczne = set()  # typy kluczy z warstwą wybraną ręcznie
        for typ, etykieta in (('LANDID', 'Warstwa Ls:'),
                              ('PARCELID', 'Warstwa działek:'),
                              ('ADR_LES', 'Warstwa wydzieleń:')):
            cbo = QgsMapLayerComboBox()
            cbo.setFilters(QgsMapLayerProxyModel.VectorLayer)
            cbo.setAllowEmptyLayer(True)
            # bez tego combo podstawia pierwszą warstwę projektu
            cbo.setLayer(None)
            cbo.layerChanged.connect(self._opisz_warstwy)
            # wybór ręczny (activated = tylko akcja użytkownika) - ma
            # pierwszeństwo przed doborem po nazwie
            cbo.activated.connect(lambda _i, t=typ: self._reczne.add(t))
            lbl = QLabel(etykieta)
            lay_warstwy.addRow(lbl, cbo)
            self._pola_warstw[typ] = (lbl, cbo)
        self.cbo_ls = self._pola_warstw['LANDID'][1]
        self.cbo_dz = self._pola_warstw['PARCELID'][1]
        self.cbo_wydz = self._pola_warstw['ADR_LES'][1]
        self.fra_warstwy.setVisible(False)
        self.btn_warstwy.toggled.connect(self.fra_warstwy.setVisible)
        lay.addWidget(self.fra_warstwy)

        self.btn_wczytaj = QPushButton('Wczytaj waypointy...')
        self.btn_wczytaj.clicked.connect(self.wczytaj_dialog)
        lay.addWidget(self.btn_wczytaj)

        fra_sekcja = QFrame(glowny)
        lay_sekcja = QFormLayout(fra_sekcja)
        self.cbo_sekcja = QComboBox()
        self.cbo_sekcja.currentIndexChanged.connect(self._zmien_sekcje)
        lay_sekcja.addRow(QLabel('Sekcja:'), self.cbo_sekcja)
        lay.addWidget(fra_sekcja)

        fra_info = QFrame(glowny)
        lay_info = QFormLayout(fra_info)
        self.txt_obiekt = QLineEdit()
        self.txt_obiekt.setReadOnly(True)
        lay_info.addRow(QLabel('Obiekt:'), self.txt_obiekt)

        # błąd - jedna linia; kilka uwag (np. kontrola opisów) rozdzielone
        # " | " z liczbą na początku, pełna lista w dymku po najechaniu
        self.txt_blad = QLineEdit()
        self.txt_blad.setReadOnly(True)
        self.lbl_blad = QLabel('Błąd:')
        lay_info.addRow(self.lbl_blad, self.txt_blad)

        # szczegóły (wartości, powierzchnie) w dymku po przytrzymaniu "i" -
        # przycisk w linii "Pozycja", przy prawej krawędzi
        self.btn_info = QToolButton()
        self.btn_info.setText('i')
        f = self.btn_info.font()
        f.setBold(True)
        f.setItalic(True)
        self.btn_info.setFont(f)
        self.btn_info.setToolTip('Przytrzymaj, żeby zobaczyć szczegóły')
        self.btn_info.pressed.connect(self._pokaz_szczegoly)
        self.btn_info.released.connect(QToolTip.hideText)
        self._szczegoly = ''

        wid_poz = QWidget(fra_info)
        lay_poz = QHBoxLayout(wid_poz)
        lay_poz.setContentsMargins(0, 0, 0, 0)
        self.lbl_licznik = QLabel('- z -')
        lay_poz.addWidget(self.lbl_licznik, 1)
        lay_poz.addWidget(self.btn_info)
        lay_info.addRow(QLabel('Pozycja:'), wid_poz)
        lay.addWidget(fra_info)

        fra_kopiuj = QFrame(glowny)
        lay_kopiuj = QHBoxLayout(fra_kopiuj)
        lay_kopiuj.setContentsMargins(0, 0, 0, 0)
        self.txt_kopiuj = QLineEdit()
        self.txt_kopiuj.setReadOnly(True)
        self.txt_kopiuj.setPlaceholderText(
            '(brak wartości do skopiowania w tej sekcji)')
        self.btn_kopiuj = QPushButton('Kopiuj')
        self.btn_kopiuj.clicked.connect(self.kopiuj_wartosc)
        lay_kopiuj.addWidget(QLabel('Do wklejenia w atrybut:'))
        lay_kopiuj.addWidget(self.txt_kopiuj)
        lay_kopiuj.addWidget(self.btn_kopiuj)
        lay.addWidget(fra_kopiuj)

        fra_akcja = QFrame(glowny)
        lay_akcja = QHBoxLayout(fra_akcja)
        self.rad_pan = QRadioButton('Pan')
        self.rad_pan.setChecked(True)
        self.rad_zoom = QRadioButton('Zoom')
        grp_akcja = QButtonGroup(fra_akcja)
        grp_akcja.addButton(self.rad_pan)
        grp_akcja.addButton(self.rad_zoom)
        lay_akcja.addWidget(self.rad_pan)
        lay_akcja.addWidget(self.rad_zoom)
        lay.addWidget(fra_akcja)

        self.chk_zaznacz = QCheckBox('Zaznacz obiekt(y) na warstwie')
        self.chk_zaznacz.setChecked(False)
        self.chk_zaznacz.setToolTip(
            'Zaznacza na warstwie wszystkie obiekty znalezione pod bieżącym '
            'kluczem - przydatne zwłaszcza przy kilku obiektach naraz '
            '(np. ZDUBLOWANE LANDID), żeby od razu widzieć, które to.')

        self.chk_mignij = QCheckBox('Mrugacz')
        self.chk_mignij.setChecked(
            QSettings().value(KLUCZ_MIGNIJ, True, type=bool))
        self.chk_mignij.setToolTip(
            'Po przesunięciu/przybliżeniu mapy obiekt (albo miejsce) '
            'bieżącej pozycji miga kilka razy na czerwono, żeby od razu '
            'było go widać. Ustawienie jest zapamiętywane.')
        self.chk_mignij.toggled.connect(
            lambda wl: QSettings().setValue(KLUCZ_MIGNIJ, wl))

        fra_chk = QFrame(glowny)
        lay_chk = QHBoxLayout(fra_chk)
        lay_chk.setContentsMargins(0, 0, 0, 0)
        lay_chk.addWidget(self.chk_zaznacz)
        lay_chk.addWidget(self.chk_mignij)
        lay_chk.addStretch(1)
        lay.addWidget(fra_chk)

        fra_nav = QFrame(glowny)
        lay_nav = QHBoxLayout(fra_nav)
        self.btn_prev = QPushButton('\u25C0 Poprzedni')
        self.btn_next = QPushButton('Następny \u25B6')
        lay_nav.addWidget(self.btn_prev)
        lay_nav.addWidget(self.btn_next)
        lay.addWidget(fra_nav)

        self.btn_oznacz = QPushButton('\u2713 Oznacz i dalej')
        lay.addWidget(self.btn_oznacz)

        self.btn_prev.clicked.connect(self.poprzedni)
        self.btn_next.clicked.connect(self.nastepny)
        self.btn_oznacz.clicked.connect(self.oznacz_i_dalej)

        lay.addStretch(1)

        self._ustaw_stan_przyciskow()

    def _rejestruj_skroty(self):
        self.akcja_next = QAction(
            'Nawigator: następny', self.iface.mainWindow())
        self.akcja_next.setShortcut(QKeySequence(Qt.Key_F8))
        self.akcja_next.triggered.connect(self.nastepny)
        self.iface.registerMainWindowAction(self.akcja_next, 'F8')

        self.akcja_prev = QAction(
            'Nawigator: poprzedni', self.iface.mainWindow())
        self.akcja_prev.setShortcut(QKeySequence(Qt.Key_F7))
        self.akcja_prev.triggered.connect(self.poprzedni)
        self.iface.registerMainWindowAction(self.akcja_prev, 'F7')

        self.akcja_oznacz = QAction(
            'Nawigator: oznacz i dalej', self.iface.mainWindow())
        self.akcja_oznacz.setShortcut(QKeySequence(Qt.Key_F9))
        self.akcja_oznacz.triggered.connect(self.oznacz_i_dalej)
        self.iface.registerMainWindowAction(self.akcja_oznacz, 'F9')

    def wyrejestruj_skroty(self):
        for a in (self.akcja_next, self.akcja_prev, self.akcja_oznacz):
            try:
                self.iface.unregisterMainWindowAction(a)
            except Exception:
                pass

    # --------------------------------------------------- wczytywanie ----

    def wczytaj_dialog(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż plik waypointów', katalog_startowy(),
            'Waypointy (*.csv)')[0]
        if sc:
            self.wczytaj_plik(sc)

    def ustaw_wydzielenia(self, warstwa):
        """Warstwa wydzieleń i zaznaczanie obiektów dla listy z Edytora opisu
        (zaznaczenie poligonu przełącza kartę). Przed wczytaj_plik - pierwsza
        pozycja pokazywana jest od razu."""
        self.cbo_wydz.setLayer(warstwa)
        self.chk_zaznacz.setChecked(True)
        # jawnie wskazana warstwa - _dobierz_warstwy jej nie podmienia
        self._wymuszona_wydz = True

    @staticmethod
    def _obiekt_pliku(sciezka):
        """Folder obiektu, z którego pochodzi plik waypointów - kontrole
        zapisują je w <obiekt>\\Raporty (przy bazie)."""
        kat = os.path.dirname(os.path.abspath(sciezka))
        if os.path.basename(kat).lower() == 'raporty':
            kat = os.path.dirname(kat)
        return os.path.normcase(kat)

    def _dobierz_warstwy(self):
        """Po wczytaniu pliku: dla każdego rodzaju klucza z pliku warstwa o
        typowej nazwie (LS, DZKAT, WYDZ) z obiektu, z którego pochodzi
        plik (a gdy takiej nie ma - z obiektu aktywnej warstwy). Warstwa
        już ustawiona z tego obiektu i wskazana jawnie (lista z Edytora)
        zostaje. Pola wyboru widoczne tylko dla rodzajów kluczy z pliku;
        brak warstwy - rozwinięte."""
        typy = {w['typ_klucza'] for w in self.wiersze} & set(NAZWY_WARSTW)
        ob = self._obiekt_pliku(self.sciezka) if self.sciezka else ''
        for typ, (lbl, cbo) in self._pola_warstw.items():
            lbl.setVisible(typ in typy)
            cbo.setVisible(typ in typy)
            if typ not in typy:
                continue
            if typ == 'ADR_LES' and self._wymuszona_wydz:
                continue
            obecna = cbo.currentLayer()
            if obecna is not None and obiekt_warstwy(obecna) == ob and (
                    typ in self._reczne or
                    obecna.name().upper() in NAZWY_WARSTW[typ]):
                continue
            kandydaci = [x for n in NAZWY_WARSTW[typ]
                         for x in warstwy_o_nazwie(n)]
            z_obiektu = [x for x in kandydaci if obiekt_warstwy(x) == ob]
            wybrana = z_obiektu[0] if z_obiektu else \
                domyslna_warstwa(kandydaci, self.iface)
            if wybrana is not None:
                cbo.setLayer(wybrana)
        self._wymuszona_wydz = False
        brak = [t for t in typy if self._pola_warstw[t][1].currentLayer()
                is None]
        if brak:
            self.btn_warstwy.setChecked(True)
        self._opisz_warstwy()

    def _opisz_warstwy(self, *_):
        typy = [t for t in NAZWY_WARSTW
                if self._pola_warstw[t][1].isVisibleTo(self.fra_warstwy)]
        if not self.wiersze:
            self.lbl_warstwy.setText('Warstwy: -')
            return
        if not typy:
            self.lbl_warstwy.setText(
                'Warstwy: niepotrzebne (pozycje to miejsca na mapie)')
            return
        czesci, brak, obiekty = [], [], set()
        for t in typy:
            lyr = self._pola_warstw[t][1].currentLayer()
            if lyr is None:
                brak.append(OPIS_WARSTW[t])
                continue
            czesci.append(lyr.name())
            ob = obiekt_warstwy(lyr)
            if ob:
                obiekty.add(os.path.basename(ob))
        tekst = 'Warstwy: ' + (', '.join(czesci) or '-')
        if obiekty:
            tekst += ' (' + ', '.join(sorted(obiekty)) + ')'
        if brak:
            tekst += ('  <span style="color:#c00000">brak warstwy: ' +
                      ', '.join(brak) + '</span>')
        self.lbl_warstwy.setText(tekst)

    def _pokaz_szczegoly(self):
        """Dymek ze szczegółami bieżącej pozycji - widoczny, dopóki
        przycisk "i" jest wciśnięty (released -> QToolTip.hideText)."""
        if self._szczegoly:
            QToolTip.showText(
                self.btn_info.mapToGlobal(self.btn_info.rect().bottomLeft()),
                self._szczegoly, self.btn_info, self.btn_info.rect(), 600000)

    @staticmethod
    def _opis_obiektu(wiersz):
        if wiersz.get('obiekt'):
            return wiersz['obiekt']
        typ, klucz = wiersz['typ_klucza'], wiersz['klucz']
        if typ == waypointy.TYP_XY:
            return ''
        if typ == 'ADR_LES':
            return re.sub(r'\s+', '', klucz)
        if typ == 'LANDID':
            return f'Ls {klucz}'
        if typ == 'PARCELID':
            return f'działka {klucz}'
        return klucz

    def wczytaj_plik(self, sciezka):
        try:
            wiersze = waypointy.wczytaj(sciezka)
        except Exception as e:
            QMessageBox.warning(
                self, 'Błąd', f'Nie udało się wczytać pliku waypointów:\n{e}')
            return

        self.wiersze = wiersze
        self.sciezka = sciezka

        self.cbo_sekcja.blockSignals(True)
        self.cbo_sekcja.clear()
        sekcje = []
        for w in self.wiersze:
            if w['sekcja'] not in sekcje:
                sekcje.append(w['sekcja'])
        self.cbo_sekcja.addItems(sekcje)
        self.cbo_sekcja.blockSignals(False)

        self._dobierz_warstwy()
        self._zmien_sekcje()

    # -------------------------------------------------------- stan ----

    def _wiersze_sekcji(self):
        sekcja = self.cbo_sekcja.currentText()
        return [w for w in self.wiersze if w['sekcja'] == sekcja]

    def _zmien_sekcje(self):
        wiersze = self._wiersze_sekcji()
        self.pozycja = -1
        for i, w in enumerate(wiersze):
            if w['status'] != STATUS_ZROBIONE:
                self.pozycja = i
                break
        if self.pozycja == -1 and len(wiersze) > 0:
            self.pozycja = 0

        self._pokaz_biezacy(cichy=True)

    # ---------------------------------------------------- nawigacja ----

    def poprzedni(self):
        self._przesun(-1)

    def nastepny(self):
        self._przesun(1)

    def _przesun(self, kierunek):
        wiersze = self._wiersze_sekcji()
        if len(wiersze) == 0:
            return
        stara = self.pozycja
        self.pozycja = max(0, min(self.pozycja + kierunek, len(wiersze) - 1))
        if self._pokaz_biezacy() is False:
            # karta Edytora została przy niezapisanych zmianach
            self.pozycja = stara
            self._pokaz_biezacy()

    def _klepanie(self):
        wiersze = self._wiersze_sekcji()
        return bool(wiersze) and wiersze[0]['zrodlo'] == klepanie.ZRODLO

    def krok_klepania(self, kierunek, adr):
        """Po zapisie karty w Edytorze (Alt+Enter: kierunek 1, Alt+Backspace:
        -1): bieżąca karta - wklepana (gdy to jej wydzielenie), dalej
        następna niewklepana (po końcu listy - pominięte od początku) albo
        poprzednia. Wszystkie wklepane - sygnał klepanieZakonczone."""
        if not self._klepanie() or self.pozycja < 0:
            self.iface.messageBar().pushMessage(
                'Edytor opisu',
                'Zapisano. Przejście do następnej karty działa po "Wczytaj '
                'raport do klepania..." w panelu Edytora.', Qgis.Info, 5)
            return
        self.show()
        wiersze = self._wiersze_sekcji()
        biez = wiersze[self.pozycja]
        if klepanie.bez_spacji(biez['klucz']) == klepanie.bez_spacji(adr)                 and biez['status'] != STATUS_ZROBIONE:
            biez['status'] = STATUS_ZROBIONE
            biez['data_oznaczenia'] =                 datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._zapisz()
        if kierunek < 0:
            self.pozycja = max(0, self.pozycja - 1)
            self._pokaz_biezacy()
            return
        n = len(wiersze)
        dalej = [i for i in range(self.pozycja + 1, n)
                 if wiersze[i]['status'] != STATUS_ZROBIONE]
        pominiete = [i for i in range(0, self.pozycja + 1)
                     if wiersze[i]['status'] != STATUS_ZROBIONE]
        if dalej or pominiete:
            self.pozycja = (dalej or pominiete)[0]
            self._pokaz_biezacy()
            if not dalej:
                self.iface.messageBar().pushMessage(
                    self.tytul, 'Koniec listy - wracam do pominiętych kart '
                    f'({len(pominiete)}).', Qgis.Info, 5)
            return
        self._pokaz_biezacy()
        self.klepanieZakonczone.emit(self.sciezka or '')

    def oznacz_i_dalej(self):
        wiersze = self._wiersze_sekcji()
        if len(wiersze) == 0 or self.pozycja < 0:
            return

        wiersze[self.pozycja]['status'] = STATUS_ZROBIONE
        wiersze[self.pozycja]['data_oznaczenia'] = \
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self._zapisz()

        for i in range(self.pozycja + 1, len(wiersze)):
            if wiersze[i]['status'] != STATUS_ZROBIONE:
                self.pozycja = i
                self._pokaz_biezacy()
                return

        self._pokaz_biezacy()
        self.iface.messageBar().pushMessage(
            self.tytul,
            f'Sekcja "{self.cbo_sekcja.currentText()}" - wszystkie pozycje '
            'oznaczone jako zrobione.',
            Qgis.Success, 4)

    def _zapisz(self):
        if self.sciezka:
            try:
                waypointy.zapisz(self.sciezka, self.wiersze)
            except Exception as e:
                QMessageBox.warning(
                    self, 'Błąd',
                    f'Nie udało się zapisać pliku waypointów:\n{e}')

    # --------------------------------------------------- wyświetlanie ----

    def kopiuj_wartosc(self):
        if self.txt_kopiuj.text():
            QApplication.clipboard().setText(self.txt_kopiuj.text())
            self.iface.messageBar().pushMessage(
                self.tytul,
                f'Skopiowano do schowka: {self.txt_kopiuj.text()}',
                Qgis.Success, 3)

    def _pokaz_biezacy(self, cichy=False):
        wiersze = self._wiersze_sekcji()
        n = len(wiersze)

        self.lbl_blad.setText('Uwagi:' if self._klepanie() else 'Błąd:')
        if n == 0 or self.pozycja < 0:
            self.txt_obiekt.setText('-')
            self.txt_blad.setText('')
            self.txt_blad.setToolTip('')
            self._szczegoly = ''
            self.btn_info.setEnabled(False)
            self.txt_kopiuj.setText('')
            self.btn_kopiuj.setEnabled(False)
            self.lbl_licznik.setText('- z -')
            self._ustaw_stan_przyciskow()
            return

        wiersz = wiersze[self.pozycja]
        pozostalo = sum(1 for w in wiersze if w['status'] != STATUS_ZROBIONE)
        znacznik = ' [ZROBIONE]' if wiersz['status'] == STATUS_ZROBIONE else ''
        self.lbl_licznik.setText(
            f'{self.pozycja + 1} z {n} ({pozostalo} pozostało){znacznik}')
        # pliki sprzed kolumn obiekt/blad: błąd = nazwa sekcji, szczegóły =
        # opis (dla XY opis był też jedynym opisem obiektu)
        blad = wiersz.get('blad') or wiersz['sekcja']
        self.txt_obiekt.setText(self._opis_obiektu(wiersz))
        self.txt_obiekt.setCursorPosition(0)
        uwagi = [x.strip() for x in blad.split(' | ') if x.strip()]
        if len(uwagi) > 1 and uwagi[0].endswith(':'):
            # nagłówek z listą ("Kilka punktów adresowych (2): | a | b")
            tekst = uwagi[0] + ' ' + ' | '.join(uwagi[1:])
        elif len(uwagi) > 1:
            tekst = f'({len(uwagi)}) ' + ' | '.join(uwagi)
        else:
            tekst = ''.join(uwagi)
        self.txt_blad.setText(tekst)
        self.txt_blad.setCursorPosition(0)
        # pełna lista uwag (jedna pod drugą) w dymku po najechaniu
        self.txt_blad.setToolTip('\n'.join(uwagi) if len(uwagi) > 1 else
                                 tekst)
        self._szczegoly = (wiersz.get('opis') or '').strip()
        self.btn_info.setEnabled(bool(self._szczegoly))

        do_skopiowania = wiersz.get('do_skopiowania', '')
        self.txt_kopiuj.setText(do_skopiowania)
        self.btn_kopiuj.setEnabled(bool(do_skopiowania))

        wynik = self._pokaz_na_mapie(wiersz, cichy=cichy)
        self._ustaw_stan_przyciskow()
        return wynik

    def _ustaw_stan_przyciskow(self):
        n = len(self._wiersze_sekcji())
        aktywne = n > 0 and self.pozycja >= 0
        self.btn_prev.setEnabled(aktywne and self.pozycja > 0)
        self.btn_next.setEnabled(aktywne and self.pozycja < n - 1)
        self.btn_oznacz.setEnabled(aktywne)

    def _pokaz_na_mapie(self, wiersz, cichy=False):
        # LANDID (warstwa Ls) = konkretny klasoużytek na działce.
        # PARCELID (warstwa działek) = działka katastralna.
        # ADR_LES (warstwa wydzieleń) = adres leśny (oddział-pododdział) -
        # to zupełnie inny byt niż LANDID, mimo pozornie podobnej roli klucza.
        # XY = miejsce na mapie (bez warstwy) - np. kontrole cięcia.
        if wiersz['typ_klucza'] == waypointy.TYP_XY:
            self._pokaz_xy(wiersz)
            return
        if wiersz['zrodlo'] == klepanie.ZRODLO and                 self.pokaz_w_edytorze is not None and                 not self.pokaz_w_edytorze(wiersz['klucz']):
            return False
        if wiersz['typ_klucza'] == 'LANDID':
            warstwa = self.cbo_ls.currentLayer()
            pole = 'LANDID'
        elif wiersz['typ_klucza'] == 'PARCELID':
            warstwa = self.cbo_dz.currentLayer()
            pole = 'PARCELID'
        else:  # ADR_LES
            warstwa = self.cbo_wydz.currentLayer()
            pole = 'ADR_LES'

        if warstwa is None:
            # cichy=True przy automatycznym pokazaniu pierwszego wiersza po
            # wczytaniu pliku/zmianie sekcji (patrz _zmien_sekcje) - w tym
            # momencie użytkownik nie zdążył jeszcze wskazać warstw w
            # combo, więc to nie błąd, tylko oczekiwany stan początkowy.
            # Przy ręcznej nawigacji (poprzedni/następny/oznacz i dalej)
            # ostrzeżenie zostaje, bo tam użytkownik aktywnie próbuje
            # przeskoczyć na mapę.
            if not cichy:
                self.iface.messageBar().pushMessage(
                    self.tytul,
                    f'Nie wskazano warstwy dla klucza typu {wiersz["typ_klucza"]}.',
                    Qgis.Warning, 4)
            return

        klucz = wiersz['klucz'].replace("'", "''")
        req = QgsFeatureRequest().setFilterExpression(f'"{pole}" = \'{klucz}\'')
        obiekty = [
            f for f in warstwa.getFeatures(req)
            if f.geometry() is not None and not f.geometry().isEmpty()
        ]
        if len(obiekty) == 0:
            warstwa.removeSelection()
            self.iface.messageBar().pushMessage(
                self.tytul,
                f'Nie znaleziono obiektu {pole}={wiersz["klucz"]} w warstwie '
                f'{warstwa.name()}.',
                Qgis.Warning, 4)
            return

        if self.chk_zaznacz.isChecked():
            warstwa.selectByIds([f.id() for f in obiekty])

        canvas = self.iface.mapCanvas()
        renderer = canvas.mapSettings()

        if len(obiekty) == 1:
            # dokładnie jeden obiekt - zwykłe zachowanie pan/zoom
            geom = obiekty[0].geometry()
            if self.rad_pan.isChecked():
                canvas.setCenter(renderer.layerToMapCoordinates(
                    warstwa, geom.centroid().asPoint()))
            else:
                canvas.setExtent(renderer.layerToMapCoordinates(
                    warstwa, geom.boundingBox()))
                canvas.zoomByFactor(1.1)
        else:
            # kilka obiektów pod tym samym kluczem (np. ZDUBLOWANE LANDID) -
            # pokaż je wszystkie naraz, żeby nie gubić duplikatów
            bbox = QgsRectangle()
            bbox.setMinimal()
            for f in obiekty:
                bbox.combineExtentWith(f.geometry().boundingBox())
            canvas.setExtent(renderer.layerToMapCoordinates(warstwa, bbox))
            canvas.zoomByFactor(1.2)
            info_zaznaczenia = (
                'i zaznaczono ' if self.chk_zaznacz.isChecked() else ''
            )
            self.iface.messageBar().pushMessage(
                self.tytul,
                f'Znaleziono {len(obiekty)} obiektów {pole}='
                f'{wiersz["klucz"]} - pokazano {info_zaznaczenia}wszystkie '
                'naraz.',
                Qgis.Info, 4)

        canvas.refresh()
        if self.chk_mignij.isChecked():
            try:
                canvas.flashFeatureIds(warstwa, [f.id() for f in obiekty],
                                       flashes=LICZBA_MIGNIEC)
            except Exception:
                pass

    def _pokaz_xy(self, wiersz):
        """Klucz XY (waypointy.klucz_xy): przybliża/przesuwa mapę do
        prostokąta (punkt - z marginesem 50 m) i miga nim, bez szukania
        obiektu w warstwie."""
        rozbity = waypointy.rozbij_klucz_xy(wiersz['klucz'])
        if rozbity is None:
            self.iface.messageBar().pushMessage(
                self.tytul, f'Niepoprawny klucz XY: {wiersz["klucz"]}',
                Qgis.Warning, 4)
            return
        crs_authid, (xmin, ymin, xmax, ymax) = rozbity
        canvas = self.iface.mapCanvas()
        crs = QgsCoordinateReferenceSystem(crs_authid)
        tr = QgsCoordinateTransform(
            crs, canvas.mapSettings().destinationCrs(), QgsProject.instance())

        prostokat = QgsRectangle(xmin, ymin, xmax, ymax)
        try:
            if prostokat.width() == 0 and prostokat.height() == 0:
                # punkt - środek mapy, a przy powiększaniu skala 1:2000
                # (niezależnie od jednostek układu mapy)
                geom = QgsGeometry.fromPointXY(QgsPointXY(xmin, ymin))
                canvas.setCenter(tr.transform(QgsPointXY(xmin, ymin)))
                if not self.rad_pan.isChecked():
                    canvas.zoomScale(2000)
            else:
                geom = QgsGeometry.fromRect(prostokat)
                prostokat_mapy = tr.transformBoundingBox(prostokat)
                if self.rad_pan.isChecked():
                    canvas.setCenter(prostokat_mapy.center())
                else:
                    canvas.setExtent(prostokat_mapy)
                    canvas.zoomByFactor(1.1)
        except Exception as e:
            self.iface.messageBar().pushMessage(
                self.tytul, f'Nie udało się pokazać miejsca: {e}',
                Qgis.Warning, 4)
            return
        canvas.refresh()
        if self.chk_mignij.isChecked():
            try:
                canvas.flashGeometries([geom], crs, flashes=LICZBA_MIGNIEC)
            except Exception:
                pass
