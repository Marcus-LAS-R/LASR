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

Przycisk "Utwórz/wskaż" dla każdej warstwy najpierw szuka automatycznie -
już wczytanej warstwy o domyślnej nazwie w projekcie, potem pliku o tej
nazwie w folderze SHP_opis, siostrzanym do folderu SHP warstwy WYDZ
(patrz `_folder_opis`). Dopiero gdy nic nie znajdzie, otwiera okienko, w
którym można ręcznie wskazać (istniejący plik) albo utworzyć (nowa
nazwa/lokalizacja) warstwę - wymagane kolumny są wtedy sprawdzane, żeby
uniknąć późniejszego crasha przy braku pola.

Punkty dodawane są przez własne narzędzie mapy (QgsMapToolEmitPoint)
bezpośrednio przez dataProvider - bez formularza atrybutów. Można klikać
wiele punktów pod rząd; zmiana aktywnej grupy (warstwa opis_pkt) nie
wyłącza trybu klikania, tylko zmienia wartość wpisywaną w kolejnych
punktach.
"""
import os

from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QDockWidget, QFileDialog, QGroupBox,
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

GRUPY = ['INNE WYL', 'L ENERG', 'SUKCESJA', 'DROGI L', 'LZ-Ł', 'ZRĄB']

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


def _ma_pola(lyr, wymagane_pola):
    nazwy = {pole.name() for pole in lyr.fields()}
    return set(wymagane_pola).issubset(nazwy)


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


def _zaladuj_styl_klon(lyr):
    """Ładuje domyślny styl (strzałka) na warstwę Klon z pliku qml
    dołączonego do wtyczki - patrz qml/Arrow_klon.qml."""
    sciezka = os.path.join(os.path.dirname(__file__), '..', 'qml', 'Arrow_klon.qml')
    lyr.loadNamedStyle(sciezka)
    lyr.triggerRepaint()


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

    # ------------------------------------------------------------ UI ----

    def _zbuduj_ui(self):
        glowny = QWidget(self)
        self.setWidget(glowny)
        lay = QVBoxLayout(glowny)

        # --- warstwa Klon --------------------------------------------
        box_klon = QGroupBox('Warstwa Klon (do KLON.txt)', glowny)
        lay_klon = QVBoxLayout(box_klon)

        self.lab_klon = QLabel('Warstwa: brak')
        lay_klon.addWidget(self.lab_klon)

        btn = QPushButton(f'Utwórz/wskaż ({NAZWA_KLON})')
        btn.clicked.connect(self._utworz_klon)
        lay_klon.addWidget(btn)

        self.btn_klonuj = QPushButton('Klonuj')
        self.btn_klonuj.setToolTip(
            'Tryb dodawania odcinka dwoma kliknięciami na mapie: pierwszy '
            'klik = wydzielenie źródłowe, drugi klik = docelowe - po '
            'drugim kliknięciu odcinek jest od razu zapisywany.')
        self.btn_klonuj.clicked.connect(self._klonuj)
        lay_klon.addWidget(self.btn_klonuj)

        lay.addWidget(box_klon)

        # --- warstwa punktowa (grupy) -----------------------------------
        box_pkt = QGroupBox('Warstwa punktowa (opisy generyczne)', glowny)
        lay_pkt = QVBoxLayout(box_pkt)

        self.lab_pkt = QLabel('Warstwa: brak')
        lay_pkt.addWidget(self.lab_pkt)

        btn = QPushButton(f'Utwórz/wskaż ({NAZWA_PUNKTY})')
        btn.clicked.connect(self._utworz_punkty)
        lay_pkt.addWidget(btn)

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
        box_notatki = QGroupBox('Warstwa notatek', glowny)
        lay_notatki = QVBoxLayout(box_notatki)

        self.lab_notatki = QLabel('Warstwa: brak')
        lay_notatki.addWidget(self.lab_notatki)

        btn = QPushButton(f'Utwórz/wskaż ({NAZWA_NOTATKI})')
        btn.clicked.connect(self._utworz_notatki)
        lay_notatki.addWidget(btn)

        self.btn_notatki = QPushButton('Notatki')
        self.btn_notatki.setToolTip(
            'Tryb dodawania punktów notatek - każdy klik na mapie od razu '
            'pyta o treść notatki (wymagana) i dodaje punkt.')
        self.btn_notatki.clicked.connect(self._notatki_toggle)
        lay_notatki.addWidget(self.btn_notatki)

        lay.addWidget(box_notatki)
        lay.addStretch(1)

    # --------------------------------------------------------- stan UI --

    def _odswiez(self):
        self.lab_klon.setText(
            'Warstwa: ' + (self.klon_lyr.name() if self.klon_lyr else 'brak'))
        self.btn_klonuj.setEnabled(self.klon_lyr is not None)

        self.lab_pkt.setText(
            'Warstwa: ' + (self.pkt_lyr.name() if self.pkt_lyr else 'brak'))
        for btn in self.btn_grupy.values():
            btn.setEnabled(self.pkt_lyr is not None)

        self.lab_notatki.setText(
            'Warstwa: ' +
            (self.notatki_lyr.name() if self.notatki_lyr else 'brak'))
        self.btn_notatki.setEnabled(self.notatki_lyr is not None)

    # ------------------------------------------------- wspolna logika ---

    def _pobierz_lub_wskaz(self, nazwa, typ_geom, typ_geom_txt, pola):
        """Zwraca warstwę: już wczytaną w projekcie pod domyślną nazwą,
        albo istniejący plik o tej nazwie w folderze SHP_opis. Dopiero
        gdy nic nie znaleziono automatycznie, otwiera okienko, w którym
        można wskazać istniejący plik (zostanie wczytany, po sprawdzeniu
        typu geometrii i wymaganych kolumn) albo podać nową
        nazwę/lokalizację (zostanie utworzona). `pola` (lista QgsField)
        określa też wymagane kolumny przy wskazywaniu ręcznym. None, jeśli
        użytkownik anulował albo wskazana warstwa nie pasuje."""
        istniejaca = _znajdz_warstwe(nazwa, typ_geom)
        if istniejaca is not None:
            return istniejaca

        folder = _folder_opis()
        if folder:
            sciezka = os.path.join(folder, nazwa + '.shp')
            if os.path.isfile(sciezka):
                return _wczytaj_plik(sciezka, nazwa)

        domyslna_sciezka = (
            os.path.join(folder, nazwa + '.shp') if folder else nazwa + '.shp')
        sciezka, _ = QFileDialog.getSaveFileName(
            self, f'Wskaż lub utwórz warstwę {nazwa}', domyslna_sciezka,
            'Shapefile (*.shp)', options=QFileDialog.DontConfirmOverwrite)
        if not sciezka:
            return None

        if not os.path.isfile(sciezka):
            return _utworz_warstwe(
                sciezka, typ_geom_txt,
                pola, os.path.splitext(os.path.basename(sciezka))[0])

        # wskazano istniejacy plik - wczytaj go i sprawdz czy pasuje
        wybrana_nazwa = os.path.splitext(os.path.basename(sciezka))[0]
        lyr = QgsVectorLayer(sciezka, wybrana_nazwa, 'ogr')
        wymagane_pola = [pole.name() for pole in pola]
        if not lyr.isValid() or lyr.geometryType() != typ_geom:
            QMessageBox.warning(
                self, 'Nieprawidłowa warstwa',
                'Wskazany plik nie jest poprawną warstwą oczekiwanego '
                'typu geometrii.')
            return None
        if not _ma_pola(lyr, wymagane_pola):
            QMessageBox.warning(
                self, 'Brak kolumn',
                'Wskazanej warstwie brakuje wymaganych kolumn: ' +
                ', '.join(wymagane_pola))
            return None

        QgsProject.instance().addMapLayer(lyr)
        return lyr

    # ------------------------------------------------------ warstwa Klon

    def _utworz_klon(self):
        lyr = self._pobierz_lub_wskaz(
            NAZWA_KLON, QgsWkbTypes.LineGeometry, 'LineString',
            [QgsField('ADR_Z', QVariant.String, '', 25),
             QgsField('ADR_DO', QVariant.String, '', 25)])
        if lyr is None:
            return
        self.klon_lyr = lyr
        _zaladuj_styl_klon(self.klon_lyr)
        _wylacz_formularz(self.klon_lyr)
        self._odswiez()

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

    def _utworz_punkty(self):
        lyr = self._pobierz_lub_wskaz(
            NAZWA_PUNKTY, QgsWkbTypes.PointGeometry, 'Point',
            [QgsField('GRUPA', QVariant.String, '', 20),
             QgsField('INF_ROZNE', QVariant.String, '', 254)])
        if lyr is None:
            return
        self.pkt_lyr = lyr
        self._odswiez()

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

    def _utworz_notatki(self):
        lyr = self._pobierz_lub_wskaz(
            NAZWA_NOTATKI, QgsWkbTypes.PointGeometry, 'Point',
            [QgsField('NOTATKA', QVariant.String, '', 254)])
        if lyr is None:
            return
        self.notatki_lyr = lyr
        self._odswiez()

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
