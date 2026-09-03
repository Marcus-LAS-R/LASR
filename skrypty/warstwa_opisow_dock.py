"""Warstwy do opisów - dockwidget do szybkiego tworzenia trzech warstw
pomocniczych przy pracy nad opisami taksacyjnymi:

- warstwa liniowa "opis_klon" (pola ADR_Z/ADR_DO) - do rysowania
  odcinków źródło->cel, z których "Utwórz KLON.txt"
  (aktualizacja_upul/core/utworz_klon_txt.py) buduje potem plik dla
  "Klonuj opisy wydzieleń",
- warstwa punktowa "opis_pkt" (pole GRUPA) - punkty w kategoriach (INNE
  WYL, L ENERG, SUKCESJA, DROGI L, LZ-Ł, ZRĄB) jako podstawa do wgrania
  krótkiego, generycznego opisu taksacyjnego (osobny skrypt, poza
  zakresem tego widgetu). Dla grupy INNE WYL wymagane jest dodatkowo
  pole INF_ROZNE,
- warstwa punktowa "opis_notatki" (pole NOTATKA) - każdy dodany punkt
  wymaga wypełnienia tekstu notatki.

Warstwy są wyszukiwane automatycznie przy każdym pokazaniu docka
(`showEvent`) - najpierw już wczytana warstwa o domyślnej nazwie w
projekcie, potem plik o tej nazwie w folderze SHP_opis, siostrzanym do
folderu SHP warstwy WYDZ (patrz `_folder_opis`). Dopiero gdy dla którejś
z trzech warstw nic nie znaleziono, pojawia się jeden zbiorczy popup z
pytaniem, czy utworzyć brakujące warstwy w tej domyślnej lokalizacji -
"Nie" zostawia je bez zmian (odpowiednie przyciski trybu zostają
wyłączone), do ponownej próby trzeba schować i pokazać dock jeszcze raz.

Punkty dodawane są przez własne narzędzie mapy (QgsMapToolEmitPoint)
bezpośrednio przez dataProvider - bez formularza atrybutów. Można klikać
wiele punktów pod rząd; zmiana aktywnej grupy (warstwa opis_pkt) nie
wyłącza trybu klikania, tylko zmienia wartość wpisywaną w kolejnych
punktach.
"""
import os

from PyQt5.QtCore import QPoint, Qt, QVariant
from PyQt5.QtGui import (
    QBrush, QColor, QIcon, QPainter, QPen, QPixmap, QPolygon,
)
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QDockWidget, QGroupBox,
    QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsEditFormConfig, QgsFeature, QgsField,
    QgsGeometry, QgsProject, QgsVectorFileWriter, QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand

CRS = QgsCoordinateReferenceSystem('EPSG:2180')

NAZWA_KLON = 'opis_klon'
NAZWA_PUNKTY = 'opis_pkt'
NAZWA_NOTATKI = 'opis_notatki'
NAZWA_FOLDER_OPIS = 'SHP_opis'

POLA_KLON = [
    QgsField('ADR_Z', QVariant.String, '', 25),
    QgsField('ADR_DO', QVariant.String, '', 25),
]
POLA_PUNKTY = [
    QgsField('GRUPA', QVariant.String, '', 20),
    QgsField('INF_ROZNE', QVariant.String, '', 254),
]
POLA_NOTATKI = [
    QgsField('NOTATKA', QVariant.String, '', 254),
]

# (nazwa, typ geometrii jako tekst dla QgsVectorLayer, pola) - "grupa opis":
# komplet warstw pomocniczych do opisów taksacyjnych, patrz moduł wyżej
WARSTWY_OPIS = [
    (NAZWA_KLON, 'LineString', POLA_KLON),
    (NAZWA_PUNKTY, 'Point', POLA_PUNKTY),
    (NAZWA_NOTATKI, 'Point', POLA_NOTATKI),
]

GRUPY = ['DROGI L', 'INNE WYL', 'ZRĄB', 'L ENERG', 'LZ-Ł', 'SUKCESJA']

# klucz w projekcie (QgsProject.writeEntry/readBoolEntry) pod którym
# zapisywana jest flaga "dockwidget ma się sam otwierać przy wczytaniu
# tego projektu" - patrz _toggle_przypiecie/zastosuj_stan_z_projektu
_PROJ_SCOPE = 'LasR'
_PROJ_KEY_PRZYPIETY = 'opis_dock_przypiety'


def _ikona_flagi(kolor):
    """Rysuje prostą ikonę flagi (maszt + proporzec) w podanym kolorze -
    używana na przycisku "Przypnij do pola pracy", żeby stan przypięcia
    był widoczny na pierwszy rzut oka niezależnie od stylu Qt (na to
    nakłada się jeszcze natywny "wciśnięty" wygląd z setCheckable)."""
    pix = QPixmap(16, 16)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(70, 70, 70), 1.5))
    p.drawLine(3, 1, 3, 15)
    p.setPen(Qt.NoPen)
    p.setBrush(QBrush(kolor))
    p.drawPolygon(QPolygon(
        [QPoint(3, 2), QPoint(14, 5), QPoint(3, 8)]))
    p.end()
    return QIcon(pix)

# jedyna grupa, dla ktorej pole INF_ROZNE jest wymagane przy dodawaniu punktu
GRUPA_WYMAGA_INF_ROZNE = 'INNE WYL'

# przyciski szybkiego uzupelniania pola INF_ROZNE: (etykieta, wstawiany tekst)
PRESETY_INF_ROZNE = [
    ('GUR', 'Grunt użytkowany rolniczo'),
    ('Droga', 'Droga'),
    ('Woda', 'Woda'),
    ('Zabudowania', 'Zabudowania'),
]


class _InfoRozneDialog(QDialog):
    """Okienko do wpisania INF_ROZNE przy dodawaniu punktu grupy
    GRUPA_WYMAGA_INF_ROZNE - z przyciskami szybkiego uzupełniania pola
    gotowymi frazami (PRESETY_INF_ROZNE)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Informacje różne')
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            f'Podaj informacje różne dla punktu ({GRUPA_WYMAGA_INF_ROZNE}):'))

        self.pole = QLineEdit()
        lay.addWidget(self.pole)

        siatka = QHBoxLayout()
        for etykieta, wartosc in PRESETY_INF_ROZNE:
            btn = QPushButton(etykieta)
            btn.clicked.connect(
                lambda _checked, w=wartosc: self.pole.setText(w))
            siatka.addWidget(btn)
        lay.addLayout(siatka)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def tekst(self):
        return self.pole.text().strip()


def _opcje_zapisu():
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    return opcje


def _znajdz_warstwe(nazwa, typ_geom):
    """Pierwsza wczytana warstwa wektorowa o podanej nazwie (bez względu na
    wielkość liter) i typie geometrii - albo None."""
    for lyr in QgsProject.instance().mapLayers().values():
        if not isinstance(lyr, QgsVectorLayer):
            continue
        if lyr.name().upper() != nazwa.upper():
            continue
        if lyr.geometryType() != typ_geom:
            continue
        return lyr
    return None


def _pierwsza_sciezka_z_dysku():
    """Ścieżka pliku pierwszej wczytanej warstwy, dla której da się ją
    ustalić - do wyznaczania folderów domyślnych. WYDZ ma pierwszeństwo,
    jeśli jest wczytana."""
    wydz = _znajdz_warstwe('WYDZ', QgsWkbTypes.PolygonGeometry)
    warstwy = [wydz] if wydz is not None else []
    warstwy += list(QgsProject.instance().mapLayers().values())

    for lyr in warstwy:
        try:
            sc = lyr.dataProvider().dataSourceUri().split('|')[0]
            if sc and os.path.isfile(sc):
                return sc
        except Exception:
            pass
    return ''


def _folder_startowy():
    """Folder do otwierania dialogów wyboru pliku - katalog warstwy WYDZ
    (albo pierwszej napotkanej warstwy z plikiem na dysku)."""
    sc = _pierwsza_sciezka_z_dysku()
    return os.path.dirname(sc) if sc else ''


def _folder_opis():
    """Folder SHP_opis, siostrzany do folderu warstwy WYDZ (albo
    pierwszej napotkanej warstwy z plikiem na dysku) - domyślna
    lokalizacja tworzenia/wyszukiwania warstw opisowych. Nie tworzy
    folderu - to robi _utworz_warstwe w razie potrzeby. Pusty string,
    jeśli nie da się ustalić żadnego punktu odniesienia."""
    folder_zrodlowy = _folder_startowy()
    if not folder_zrodlowy:
        return ''
    return os.path.join(os.path.dirname(folder_zrodlowy), NAZWA_FOLDER_OPIS)


def _wczytaj_plik(sciezka, nazwa):
    lyr = QgsVectorLayer(sciezka, nazwa, 'ogr')
    QgsProject.instance().addMapLayer(lyr)
    return lyr


def _utworz_warstwe(sciezka, typ_geom_txt, pola, nazwa):
    """Tworzy pustą warstwę SHP (bez featurków) z podanymi polami pod
    wskazaną ścieżką i wczytuje ją do projektu."""
    tmp = QgsVectorLayer(f'{typ_geom_txt}?crs={CRS.authid()}', 'tmp', 'memory')
    dp = tmp.dataProvider()
    tmp.startEditing()
    dp.addAttributes(pola)
    tmp.updateFields()
    tmp.commitChanges()

    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    QgsVectorFileWriter.writeAsVectorFormatV3(
        tmp, sciezka, QgsProject.instance().transformContext(), _opcje_zapisu())

    return _wczytaj_plik(sciezka, nazwa)


def _wylacz_formularz(lyr):
    """Wyłącza formularz atrybutów przy dodawaniu obiektu (ADR_Z/ADR_DO
    warstwy Klon i tak są nadpisywane później przez "Utwórz KLON.txt" na
    podstawie geometrii - ręczne wypełnianie ich przy rysowaniu odcinka
    jest zbędnym klikaniem). editFormConfig() bywa zwracane przez wartość,
    więc konfigurację trzeba jawnie zapisać z powrotem przez
    setEditFormConfig()."""
    cfg = lyr.editFormConfig()
    cfg.setSuppress(QgsEditFormConfig.SuppressOn)
    lyr.setEditFormConfig(cfg)


class WarstwaOpisowDock(QDockWidget):

    tytul = 'Warstwy do opisów'

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(self.tytul)
        self.setSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.klon_lyr = None
        self.pkt_lyr = None
        self.notatki_lyr = None
        self._grupa_aktywna = None
        self._narzedzie_pkt = None
        self._narzedzie_klon = None
        self._narzedzie_notatki = None
        self._klon_pierwszy = None
        self._rubber_klon = None

        self._zbuduj_ui()
        self._odswiez()
        self.zastosuj_stan_z_projektu()

    # ------------------------------------------------------------ UI ----

    def _zbuduj_ui(self):
        glowny = QWidget(self)
        self.setWidget(glowny)
        lay = QVBoxLayout(glowny)

        # --- przypięcie do pola pracy ------------------------------------
        self.btn_przypnij = QPushButton('Przypnij do pola pracy')
        self.btn_przypnij.setCheckable(True)
        self.btn_przypnij.setToolTip(
            'Zapamiętuje w projekcie, że ten widget ma się sam otwierać '
            'przy jego wczytaniu (np. w szablonowym "polu pracy"). '
            'Ustawienie zapisuje się dopiero przy zapisie projektu '
            '(Ctrl+S).')
        self.btn_przypnij.clicked.connect(self._toggle_przypiecie)
        self._ikona_przypieta = _ikona_flagi(QColor(200, 0, 0))
        self._ikona_wolna = _ikona_flagi(QColor(160, 160, 160))
        self.btn_przypnij.setIcon(self._ikona_wolna)
        lay.addWidget(self.btn_przypnij, alignment=Qt.AlignRight)

        # --- warstwa Klon --------------------------------------------
        box_klon = QGroupBox(f'Warstwa {NAZWA_KLON} (do KLON.txt)', glowny)
        lay_klon = QVBoxLayout(box_klon)

        self.btn_klonuj = QPushButton('Klonuj')
        self.btn_klonuj.setToolTip(
            'Tryb dodawania odcinka dwoma kliknięciami na mapie: pierwszy '
            'klik = wydzielenie źródłowe, drugi klik = docelowe - po '
            'drugim kliknięciu odcinek jest od razu zapisywany.')
        self.btn_klonuj.clicked.connect(self._klonuj)
        lay_klon.addWidget(self.btn_klonuj)

        lay.addWidget(box_klon)

        # --- warstwa punktowa (grupy) -----------------------------------
        box_pkt = QGroupBox(f'Warstwa {NAZWA_PUNKTY} (opisy generyczne)', glowny)
        lay_pkt = QVBoxLayout(box_pkt)

        lay_pkt.addWidget(QLabel('Grupa (klik = tryb dodawania punktów):'))
        siatka = QGridLayout()
        self.btn_grupy = {}
        for i, grupa in enumerate(GRUPY):
            gbtn = QPushButton(grupa)
            gbtn.setCheckable(True)
            gbtn.clicked.connect(
                lambda _checked, g=grupa: self._wybierz_grupe(g))
            siatka.addWidget(gbtn, i // 2, i % 2)
            self.btn_grupy[grupa] = gbtn
        lay_pkt.addLayout(siatka)

        lay.addWidget(box_pkt)

        # --- warstwa notatek ---------------------------------------------
        box_notatki = QGroupBox(
            f'Warstwa {NAZWA_NOTATKI} (notatki tekstowe)', glowny)
        lay_notatki = QVBoxLayout(box_notatki)

        self.btn_notatki = QPushButton('Notatki')
        self.btn_notatki.setToolTip(
            'Tryb dodawania punktów notatek - każdy klik na mapie od razu '
            'pyta o treść notatki (wymagana) i dodaje punkt.')
        self.btn_notatki.clicked.connect(self._notatki_toggle)
        lay_notatki.addWidget(self.btn_notatki)

        lay.addWidget(box_notatki)
        lay.addStretch(1)

    # ------------------------------------------------- pole pracy (pin) --

    def _toggle_przypiecie(self, przypiety):
        QgsProject.instance().writeEntry(
            _PROJ_SCOPE, _PROJ_KEY_PRZYPIETY, przypiety)
        self._odswiez_przycisk_przypniecia(przypiety)

    def _odswiez_przycisk_przypniecia(self, przypiety):
        self.btn_przypnij.setChecked(przypiety)
        self.btn_przypnij.setText(
            'Odepnij od pola pracy' if przypiety else 'Przypnij do pola pracy')
        self.btn_przypnij.setIcon(
            self._ikona_przypieta if przypiety else self._ikona_wolna)

    def zastosuj_stan_z_projektu(self):
        """Pokazuje/ukrywa widget zgodnie z flagą zapisaną w projekcie
        (patrz _toggle_przypiecie). Podpięte pod
        QgsProject.instance().readProject w las_r.py, żeby dockwidget sam
        się otwierał przy wczytaniu zapisanego "pola pracy"."""
        przypiety, _ = QgsProject.instance().readBoolEntry(
            _PROJ_SCOPE, _PROJ_KEY_PRZYPIETY, False)
        self._odswiez_przycisk_przypniecia(przypiety)
        self.setVisible(przypiety)

    def zresetuj_stan_projektu(self):
        """Podpięte pod QgsProject.instance().cleared (nowy/pusty projekt)
        - taki projekt nie ma zapisanej flagi, więc ukrywamy widget i
        odznaczamy przycisk przypięcia."""
        self._odswiez_przycisk_przypniecia(False)
        self.hide()

    # --------------------------------------------------------- stan UI --

    def _odswiez(self):
        self.btn_klonuj.setEnabled(self.klon_lyr is not None)

        for btn in self.btn_grupy.values():
            btn.setEnabled(self.pkt_lyr is not None)

        self.btn_notatki.setEnabled(self.notatki_lyr is not None)

    # ------------------------------------------------- wspolna logika ---

    def showEvent(self, event):
        super().showEvent(event)
        self._sprawdz_warstwy_opisowe()

    def _znajdz_automatycznie(self, nazwa, typ_geom):
        """Warstwa już wczytana w projekcie pod domyślną nazwą, albo
        istniejący plik o tej nazwie w folderze SHP_opis - bez otwierania
        żadnego okna. None, jeśli nic nie znaleziono."""
        istniejaca = _znajdz_warstwe(nazwa, typ_geom)
        if istniejaca is not None:
            return istniejaca

        folder = _folder_opis()
        if folder:
            sciezka = os.path.join(folder, nazwa + '.shp')
            if os.path.isfile(sciezka):
                return _wczytaj_plik(sciezka, nazwa)
        return None

    def _sprawdz_warstwy_opisowe(self):
        """Uruchamiane przy każdym pokazaniu docka (showEvent) - dla
        każdej z trzech warstw szuka automatycznie już wczytanej warstwy
        albo pliku w SHP_opis (`_znajdz_automatycznie`). Dla warstw,
        których nie znaleziono, pokazuje jeden zbiorczy popup z pytaniem,
        czy je utworzyć w domyślnej lokalizacji - "Nie" zostawia je jako
        None (odpowiednie przyciski trybu zostają wyłączone w
        `_odswiez`)."""
        spec = [
            (NAZWA_KLON, 'klon_lyr', QgsWkbTypes.LineGeometry,
             'LineString', POLA_KLON),
            (NAZWA_PUNKTY, 'pkt_lyr', QgsWkbTypes.PointGeometry,
             'Point', POLA_PUNKTY),
            (NAZWA_NOTATKI, 'notatki_lyr', QgsWkbTypes.PointGeometry,
             'Point', POLA_NOTATKI),
        ]

        brakujace = []
        for nazwa, atrybut, typ_geom, typ_geom_txt, pola in spec:
            if getattr(self, atrybut) is not None:
                continue
            lyr = self._znajdz_automatycznie(nazwa, typ_geom)
            if lyr is not None:
                setattr(self, atrybut, lyr)
                if nazwa == NAZWA_KLON:
                    _wylacz_formularz(lyr)
            else:
                brakujace.append((nazwa, atrybut, typ_geom_txt, pola))

        if brakujace:
            folder = _folder_opis()
            odp = QMessageBox.question(
                self, 'Warstwy opisowe',
                'Nie znaleziono w domyślnej lokalizacji'
                + (f' ({folder})' if folder else '')
                + ' następujących warstw:\n- '
                + '\n- '.join(n for n, *_ in brakujace)
                + '\n\nUtworzyć brakujące warstwy?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if odp == QMessageBox.Yes:
                if not folder:
                    QMessageBox.warning(
                        self, 'Brak lokalizacji',
                        'Nie udało się ustalić domyślnej lokalizacji '
                        '(brak wczytanej warstwy z plikiem na dysku w '
                        'projekcie) - nie można utworzyć warstw.')
                else:
                    for nazwa, atrybut, typ_geom_txt, pola in brakujace:
                        sciezka = os.path.join(folder, nazwa + '.shp')
                        lyr = _utworz_warstwe(
                            sciezka, typ_geom_txt, pola, nazwa)
                        setattr(self, atrybut, lyr)
                        if nazwa == NAZWA_KLON:
                            _wylacz_formularz(lyr)

        self._odswiez()

    # ------------------------------------------------------ warstwa Klon

    def _klonuj(self):
        if self.klon_lyr is None:
            return

        self._klon_pierwszy = None
        if self._rubber_klon is None:
            self._rubber_klon = QgsRubberBand(
                self.iface.mapCanvas(), QgsWkbTypes.PointGeometry)
            self._rubber_klon.setColor(QColor(255, 0, 0))
            self._rubber_klon.setWidth(4)
        self._rubber_klon.reset(QgsWkbTypes.PointGeometry)

        if self._narzedzie_klon is None:
            self._narzedzie_klon = QgsMapToolEmitPoint(self.iface.mapCanvas())
            self._narzedzie_klon.canvasClicked.connect(self._klik_klon)
        self.iface.mapCanvas().setMapTool(self._narzedzie_klon)

    def _klik_klon(self, koord, _btn):
        if self.klon_lyr is None:
            return

        if self._klon_pierwszy is None:
            # pierwszy klik - zapamiętaj punkt startowy, pokaż go na mapie
            self._klon_pierwszy = koord
            self._rubber_klon.reset(QgsWkbTypes.PointGeometry)
            self._rubber_klon.addPoint(koord)
            return

        # drugi klik - dokladnie 2 wierzcholki, odcinek od razu zapisywany
        geom = QgsGeometry.fromPolylineXY([self._klon_pierwszy, koord])
        f = QgsFeature(self.klon_lyr.fields())
        f.setGeometry(geom)
        self.klon_lyr.dataProvider().addFeatures([f])
        self.klon_lyr.triggerRepaint()

        self._klon_pierwszy = None
        self._rubber_klon.reset(QgsWkbTypes.PointGeometry)

    # -------------------------------------------------- warstwa punktowa

    def _wybierz_grupe(self, grupa):
        if self.pkt_lyr is None:
            self.btn_grupy[grupa].setChecked(False)
            return

        if self._grupa_aktywna == grupa:
            # ponowny klik aktywnej grupy - wylacz tryb dodawania
            self.btn_grupy[grupa].setChecked(False)
            self._grupa_aktywna = None
            self.iface.actionPan().trigger()
            return

        for inna, btn in self.btn_grupy.items():
            btn.setChecked(inna == grupa)
        self._grupa_aktywna = grupa

        if self._narzedzie_pkt is None:
            self._narzedzie_pkt = QgsMapToolEmitPoint(self.iface.mapCanvas())
            self._narzedzie_pkt.canvasClicked.connect(self._dodaj_punkt)
        self.iface.mapCanvas().setMapTool(self._narzedzie_pkt)

    def _dodaj_punkt(self, koord, _btn):
        if self.pkt_lyr is None or self._grupa_aktywna is None:
            return

        inf_rozne = ''
        if self._grupa_aktywna == GRUPA_WYMAGA_INF_ROZNE:
            dlg = _InfoRozneDialog(self)
            tekst = dlg.tekst() if dlg.exec_() == QDialog.Accepted else ''
            if not tekst:
                QMessageBox.warning(
                    self, 'Wymagane pole',
                    f'Dla grupy {GRUPA_WYMAGA_INF_ROZNE} pole "informacje '
                    'różne" jest wymagane - punkt nie został dodany.')
                return
            inf_rozne = tekst

        f = QgsFeature(self.pkt_lyr.fields())
        f.setGeometry(QgsGeometry.fromPointXY(koord))
        f['GRUPA'] = self._grupa_aktywna
        if 'INF_ROZNE' in {pole.name() for pole in self.pkt_lyr.fields()}:
            f['INF_ROZNE'] = inf_rozne
        self.pkt_lyr.dataProvider().addFeatures([f])
        self.pkt_lyr.triggerRepaint()

    # --------------------------------------------------- warstwa notatek

    def _notatki_toggle(self):
        if self.notatki_lyr is None:
            return

        if self._narzedzie_notatki is None:
            self._narzedzie_notatki = QgsMapToolEmitPoint(
                self.iface.mapCanvas())
            self._narzedzie_notatki.canvasClicked.connect(self._klik_notatki)
        self.iface.mapCanvas().setMapTool(self._narzedzie_notatki)

    def _klik_notatki(self, koord, _btn):
        if self.notatki_lyr is None:
            return

        tekst, ok = QInputDialog.getText(
            self, 'Notatka', 'Podaj treść notatki dla punktu:')
        tekst = tekst.strip()
        if not ok or not tekst:
            QMessageBox.warning(
                self, 'Wymagane pole',
                'Treść notatki jest wymagana - punkt nie został dodany.')
            return

        f = QgsFeature(self.notatki_lyr.fields())
        f.setGeometry(QgsGeometry.fromPointXY(koord))
        f['NOTATKA'] = tekst
        self.notatki_lyr.dataProvider().addFeatures([f])
        self.notatki_lyr.triggerRepaint()
