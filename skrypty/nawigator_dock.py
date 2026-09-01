"""Nawigator błędów - dockwidget do przeglądania na mapie błędów zebranych
przez skrypty kontrolne (Kontrola Ls, Kontrola słownikowa SULMN) w postaci
pliku waypointów (patrz skrypty/waypointy.py).

Wzorowany na wtyczce Go2NextFeature (materialy/Go2NextFeature3) - ten sam
mechanizm pan/zoom do geometrii bieżącego obiektu, ale zamiast skanować
całą warstwę, nawigator idzie po gotowej liście kluczy z pliku waypointów.
"""
from datetime import datetime

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QKeySequence
from qgis.PyQt.QtWidgets import (
    QAction, QApplication, QButtonGroup, QCheckBox, QComboBox, QDockWidget,
    QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QRadioButton, QSizePolicy, QVBoxLayout, QWidget,
)
from qgis.core import (
    Qgis, QgsFeatureRequest, QgsMapLayerProxyModel, QgsRectangle,
)
from qgis.gui import QgsMapLayerComboBox

from . import waypointy

STATUS_ZROBIONE = 'ZROBIONE'


class NawigatorDock(QDockWidget):

    tytul = 'Nawigator błędów'

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(self.tytul)
        self.setSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.wiersze = []   # wszystkie wczytane wiersze (wszystkie sekcje)
        self.sciezka = None  # ścieżka do wczytanego pliku CSV
        self.pozycja = -1    # indeks w obrębie bieżącej sekcji

        self._zbuduj_ui()
        self._rejestruj_skroty()

    # ------------------------------------------------------------ UI ----

    def _zbuduj_ui(self):
        glowny = QWidget(self)
        self.setWidget(glowny)
        lay = QVBoxLayout(glowny)

        fra_warstwy = QFrame(glowny)
        lay_warstwy = QFormLayout(fra_warstwy)
        self.cbo_ls = QgsMapLayerComboBox()
        self.cbo_ls.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.cbo_ls.setAllowEmptyLayer(True)
        lay_warstwy.addRow(QLabel('Warstwa Ls:'), self.cbo_ls)

        self.cbo_dz = QgsMapLayerComboBox()
        self.cbo_dz.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.cbo_dz.setAllowEmptyLayer(True)
        lay_warstwy.addRow(QLabel('Warstwa działek:'), self.cbo_dz)

        self.cbo_wydz = QgsMapLayerComboBox()
        self.cbo_wydz.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.cbo_wydz.setAllowEmptyLayer(True)
        lay_warstwy.addRow(QLabel('Warstwa wydzieleń:'), self.cbo_wydz)
        lay.addWidget(fra_warstwy)

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
        self.txt_wartosc = QLineEdit()
        self.txt_wartosc.setReadOnly(True)
        lay_info.addRow(QLabel('Bieżący błąd:'), self.txt_wartosc)
        self.lbl_licznik = QLabel('- z -')
        lay_info.addRow(QLabel('Pozycja:'), self.lbl_licznik)
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
        lay.addWidget(self.chk_zaznacz)

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
            'Nawigator błędów: następny', self.iface.mainWindow())
        self.akcja_next.setShortcut(QKeySequence(Qt.Key_F8))
        self.akcja_next.triggered.connect(self.nastepny)
        self.iface.registerMainWindowAction(self.akcja_next, 'F8')

        self.akcja_prev = QAction(
            'Nawigator błędów: poprzedni', self.iface.mainWindow())
        self.akcja_prev.setShortcut(QKeySequence(Qt.Key_F7))
        self.akcja_prev.triggered.connect(self.poprzedni)
        self.iface.registerMainWindowAction(self.akcja_prev, 'F7')

        self.akcja_oznacz = QAction(
            'Nawigator błędów: oznacz i dalej', self.iface.mainWindow())
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
            self, 'Wskaż plik waypointów', '', 'Waypointy (*.csv)')[0]
        if sc:
            self.wczytaj_plik(sc)

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

        self._pokaz_biezacy()

    # ---------------------------------------------------- nawigacja ----

    def poprzedni(self):
        self._przesun(-1)

    def nastepny(self):
        self._przesun(1)

    def _przesun(self, kierunek):
        wiersze = self._wiersze_sekcji()
        if len(wiersze) == 0:
            return
        self.pozycja = max(0, min(self.pozycja + kierunek, len(wiersze) - 1))
        self._pokaz_biezacy()

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

    def _pokaz_biezacy(self):
        wiersze = self._wiersze_sekcji()
        n = len(wiersze)

        if n == 0 or self.pozycja < 0:
            self.txt_wartosc.setText('-')
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
        self.txt_wartosc.setText(f"{wiersz['klucz']}   {wiersz['opis']}")

        do_skopiowania = wiersz.get('do_skopiowania', '')
        self.txt_kopiuj.setText(do_skopiowania)
        self.btn_kopiuj.setEnabled(bool(do_skopiowania))

        self._pokaz_na_mapie(wiersz)
        self._ustaw_stan_przyciskow()

    def _ustaw_stan_przyciskow(self):
        n = len(self._wiersze_sekcji())
        aktywne = n > 0 and self.pozycja >= 0
        self.btn_prev.setEnabled(aktywne and self.pozycja > 0)
        self.btn_next.setEnabled(aktywne and self.pozycja < n - 1)
        self.btn_oznacz.setEnabled(aktywne)

    def _pokaz_na_mapie(self, wiersz):
        # LANDID (warstwa Ls) = konkretny klasoużytek na działce.
        # PARCELID (warstwa działek) = działka katastralna.
        # ADR_LES (warstwa wydzieleń) = adres leśny (oddział-pododdział) -
        # to zupełnie inny byt niż LANDID, mimo pozornie podobnej roli klucza.
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
