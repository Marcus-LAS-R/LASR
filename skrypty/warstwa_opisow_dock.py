"""Warstwy do opisów - dockwidget do szybkiego tworzenia trzech warstw
pomocniczych przy pracy nad opisami taksacyjnymi:

- warstwa liniowa "opis_klon" (pola ADR_Z/ADR_DO) - do rysowania
  odcinków źródło->cel, z których "Utwórz KLON.txt"
  (aktualizacja_upul/core/utworz_klon_txt.py) buduje potem plik dla
  "Klonuj opisy wydzieleń",
- warstwa punktowa "opis_pkt" (pole GRUPA) - punkty w kategoriach (INNE
  WYL, L ENERG, SUKCESJA, DROGI L, LZ-Ł, ZRĄB, TURYST, RETENCJA) jako
  podstawa do wgrania krótkiego, generycznego opisu taksacyjnego (osobny
  skrypt, poza zakresem tego widgetu). Dla grupy INNE WYL wymagane jest
  dodatkowo pole INF_ROZNE. Poza L ENERG i LZ-Ł punkt dostaje też STL
  (z WYDZ_POL_stare) i POKRYWA - patrz opis_stl.py,
- warstwa punktowa "opis_notatki" (pole NOTATKA) - każdy dodany punkt
  wymaga wypełnienia tekstu notatki.

Warstwy są wyszukiwane automatycznie przy każdym pokazaniu docka
(`showEvent`) - najpierw już wczytana warstwa o domyślnej nazwie w
projekcie (z weryfikacją, że ma wymagane pola - inaczej pomijana z
ostrzeżeniem), potem plik o tej nazwie w folderze SHP_opis, siostrzanym
do folderu projektu (patrz `_folder_opis`). Dopiero gdy dla którejś z
trzech warstw nic poprawnego nie znaleziono, pojawia się jeden zbiorczy
popup z pytaniem, czy utworzyć brakujące warstwy w tej domyślnej
lokalizacji - "Nie" zostawia je bez zmian (odpowiednie przyciski trybu
zostają wyłączone). Przycisk "Wczytaj/utwórz warstwy" pozwala uruchomić
to samo wyszukiwanie ręcznie, bez chowania/pokazywania docka od nowa.

Punkty dodawane są przez własne narzędzie mapy (QgsMapToolEmitPoint)
bezpośrednio przez dataProvider - bez formularza atrybutów. Można klikać
wiele punktów pod rząd; zmiana aktywnej grupy (warstwa opis_pkt) nie
wyłącza trybu klikania, tylko zmienia wartość wpisywaną w kolejnych
punktach.
"""
import os

from PyQt5 import sip
from PyQt5.QtCore import QPoint, Qt, QVariant
from PyQt5.QtGui import (
    QBrush, QColor, QIcon, QPainter, QPen, QPixmap, QPolygon,
)
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDockWidget, QGroupBox,
    QGridLayout, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsEditFormConfig, QgsFeature, QgsField,
    QgsGeometry, QgsProject, QgsVectorFileWriter, QgsVectorLayer,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsMapToolEmitPoint, QgsRubberBand

from . import opis_stl
from .funkcje import wybierz_warstwe_z_kandydatow

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
    QgsField('STL', QVariant.String, '', 20),
    QgsField('POKRYWA', QVariant.String, '', 10),
]
# pola, bez których warstwa opis_pkt jest odrzucana - STL/POKRYWA doszły
# później i są do starszych warstw dopisywane automatycznie
# (_dopisz_brakujace_pola), więc ich brak nie dyskwalifikuje warstwy
POLA_PUNKTY_WYMAGANE = POLA_PUNKTY[:2]
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

GRUPY = ['DROGI L', 'INNE WYL', 'ZRĄB', 'L ENERG', 'LZ-Ł', 'SUKCESJA',
         'TURYST', 'RETENCJA']

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
    ('Przydomowy', 'Teren przydomowy'),
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


class _PokrywaDialog(QDialog):
    """Wybór pokrywy (VEG_COVER_CD) przyciskami - jedno kliknięcie
    zatwierdza. Anuluj = punkt nie zostanie dodany."""

    def __init__(self, grupa, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Pokrywa')
        self.kod = None
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f'Wybierz pokrywę dla punktu ({grupa}):'))
        siatka = QGridLayout()
        for i, (kod, opis) in enumerate(opis_stl.SLOWNIK_POKRYWY):
            btn = QPushButton(f'{kod} - {opis}')
            btn.clicked.connect(lambda _checked, k=kod: self._wybierz(k))
            siatka.addWidget(btn, i // 2, i % 2)
        lay.addLayout(siatka)
        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.reject)
        lay.addWidget(buttons)

    def _wybierz(self, kod):
        self.kod = kod
        self.accept()


class _BrakZrodlaStlDialog(QDialog):
    """Brak warstwy WYDZ_POL_stare w TOC - wskazanie warstwy zastępczej
    (musi mieć pole STL), zgoda na punkty bez STL albo rezygnacja."""

    ANULUJ, IGNORUJ, DALEJ = range(3)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Brak warstwy ze STL')
        self.wynik = self.ANULUJ
        self.warstwa = None
        self._warstwy = [
            lyr for lyr in QgsProject.instance().mapLayers().values()
            if isinstance(lyr, QgsVectorLayer)
            and lyr.geometryType() == QgsWkbTypes.PolygonGeometry
        ]

        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(
            f'W projekcie nie ma warstwy {opis_stl.NAZWA_ZRODLA_STL} - nie '
            'ma skąd pobrać STL dla punktu.\n\n'
            'Wskaż warstwę zastępczą (poligonową z polem STL) i wybierz '
            '"Przejdź dalej",\nalbo "Ignoruj", aby stawiać punkty bez STL, '
            'albo "Anuluj".'))
        self.combo = QComboBox()
        for lyr in self._warstwy:
            sciezka = lyr.dataProvider().dataSourceUri().split('|')[0]
            self.combo.addItem(f'{lyr.name()}   ({sciezka})')
        self.combo.setEnabled(bool(self._warstwy))
        lay.addWidget(self.combo)

        wiersz = QHBoxLayout()
        for tekst, akcja in (
                ('Anuluj', self.reject),
                ('Ignoruj', self._ignoruj),
                ('Przejdź dalej', self._dalej)):
            btn = QPushButton(tekst)
            btn.clicked.connect(akcja)
            wiersz.addWidget(btn)
        lay.addLayout(wiersz)

    def _ignoruj(self):
        self.wynik = self.IGNORUJ
        self.accept()

    def _dalej(self):
        i = self.combo.currentIndex()
        if not (0 <= i < len(self._warstwy)):
            QMessageBox.warning(
                self, 'Brak warstwy',
                'W projekcie nie ma żadnej warstwy poligonowej do wskazania.')
            return
        lyr = self._warstwy[i]
        if opis_stl.nazwa_pola_stl(lyr) is None:
            QMessageBox.warning(
                self, 'Brak pola STL',
                f'Warstwa "{lyr.name()}" nie ma pola STL - wskaż inną.')
            return
        self.warstwa = lyr
        self.wynik = self.DALEJ
        self.accept()


def _opcje_zapisu():
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    return opcje


def _ma_pola(lyr, pola):
    """Czy `lyr` ma wszystkie pola z listy `pola` (QgsField)? Bez tej
    kontroli warstwa o właściwej nazwie/geometrii, ale z innego szablonu
    (obcy zestaw kolumn) zostaje cicho przyjęta jako "ta" warstwa opisowa,
    a pierwszy zapis punktu/odcinka wywala KeyError na brakującym polu."""
    nazwy = {f.name() for f in lyr.fields()}
    return all(p.name() in nazwy for p in pola)


def _dopisz_brakujace_pola(lyr, pola, iface):
    """Dopisuje do warstwy (bezpośrednio w pliku, przez dataProvider) te
    pola z listy `pola`, których jeszcze nie ma - dla warstw opis_pkt
    utworzonych przed dodaniem STL/POKRYWA."""
    nazwy = {f.name().upper() for f in lyr.fields()}
    brak = [p for p in pola if p.name().upper() not in nazwy]
    if not brak:
        return
    lista = ', '.join(p.name() for p in brak)
    if lyr.dataProvider().addAttributes(brak):
        lyr.updateFields()
        iface.messageBar().pushInfo(
            'Warstwy opisowe',
            f'Do warstwy "{lyr.name()}" dopisano pola: {lista}')
    else:
        iface.messageBar().pushWarning(
            'Warstwy opisowe',
            f'Nie udało się dopisać pól {lista} do warstwy "{lyr.name()}" '
            '- STL/pokrywa nie będą zapisywane.')


def _zywa(lyr):
    """Czy `lyr` to wciąż żywy obiekt QgsVectorLayer (nie None, nie
    usunięty z projektu/zamknięty razem z poprzednim projektem)? Bez tej
    kontroli martwy wskaźnik po QgsProject.cleared (nowy/inny projekt)
    wygląda jak poprawna warstwa (nie jest None), ale każde jej użycie
    wywala RuntimeError: wrapped C/C++ object ... has been deleted."""
    return lyr is not None and not sip.isdeleted(lyr)


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
    """Folder SHP_opis - domyślna lokalizacja tworzenia/wyszukiwania
    warstw opisowych. Najpierw folder samego (zapisanego) projektu QGIS -
    działa nawet w pustym "polu pracy" bez ani jednej wczytanej warstwy.
    Dopiero gdy projekt nie jest jeszcze zapisany na dysku, fallback na
    folder siostrzany do SHP wczytanej warstwy WYDZ (albo pierwszej
    napotkanej warstwy z plikiem na dysku). Nie tworzy folderu - to robi
    _utworz_warstwe w razie potrzeby. Pusty string, jeśli nie da się
    ustalić żadnego punktu odniesienia."""
    projekt = QgsProject.instance().absolutePath()
    if projekt:
        return os.path.join(projekt, NAZWA_FOLDER_OPIS)

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


class _NarzedzieOdcinka(QgsMapTool):
    """Digitalizacja jednego odcinka źródło->cel (dokładnie 2 wierzchołki),
    tak jak natywne narzędzia QGIS: LPM dodaje kolejno źródło i cel (z
    linią "na żywo" śledzącą kursor po pierwszym kliknięciu), PPM
    zatwierdza gotowy odcinek (nie dodaje nowego punktu - działa tylko
    gdy oba wierzchołki są już ustawione), Esc anuluje w dowolnym
    momencie. Trzeci LPM przed PPM jest ignorowany."""

    def __init__(self, canvas, rubber_band, on_zakonczono):
        super().__init__(canvas)
        self._rubber = rubber_band
        self._on_zakonczono = on_zakonczono
        self._zrodlo = None
        self._cel = None
        self.setCursor(Qt.CrossCursor)

    def canvasPressEvent(self, event):
        punkt = self.toMapCoordinates(event.pos())

        if event.button() == Qt.RightButton:
            if self._zrodlo is not None and self._cel is not None:
                self._on_zakonczono(self._zrodlo, self._cel)
            self._resetuj()
            return

        if event.button() != Qt.LeftButton:
            return

        if self._zrodlo is None:
            self._zrodlo = punkt
            self._rubber.reset(QgsWkbTypes.LineGeometry)
            self._rubber.addPoint(punkt)
        elif self._cel is None:
            self._cel = punkt
            self._rubber.reset(QgsWkbTypes.LineGeometry)
            self._rubber.addPoint(self._zrodlo)
            self._rubber.addPoint(self._cel)
        # trzeci i kolejne LPM (oba wierzchołki już ustawione) - ignorowane

    def canvasMoveEvent(self, event):
        if self._zrodlo is None or self._cel is not None:
            return
        punkt = self.toMapCoordinates(event.pos())
        self._rubber.reset(QgsWkbTypes.LineGeometry)
        self._rubber.addPoint(self._zrodlo)
        self._rubber.addPoint(punkt)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self._resetuj()

    def activate(self):
        super().activate()
        self._resetuj()

    def deactivate(self):
        self._resetuj()
        super().deactivate()

    def _resetuj(self):
        self._zrodlo = None
        self._cel = None
        self._rubber.reset(QgsWkbTypes.LineGeometry)


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
        self._rubber_klon = None
        # źródło STL dla punktów (opis_stl.ZrodloSTL) i zgoda na punkty
        # bez STL ("Ignoruj" w _BrakZrodlaStlDialog) - do końca projektu
        self._zrodlo_stl = None
        self._stl_ignoruj = False

        self._zbuduj_ui()
        self._odswiez()
        self.zastosuj_stan_z_projektu()

    # ------------------------------------------------------------ UI ----

    def _zbuduj_ui(self):
        glowny = QWidget(self)
        self.setWidget(glowny)
        lay = QVBoxLayout(glowny)

        # --- gorny wiersz: reczne wczytaj/utworz (lewo) + przypiecie (prawo)
        gorny_wiersz = QHBoxLayout()

        self.btn_wczytaj = QPushButton('Wczytaj/utwórz warstwy')
        self.btn_wczytaj.setToolTip(
            'Ręcznie uruchamia wyszukanie/utworzenie trzech warstw '
            'opisowych - to samo, co dzieje się automatycznie przy każdym '
            'pokazaniu tego okna. Przydatne, gdy trzeba spróbować ponownie '
            'bez chowania i pokazywania docka (np. po dodaniu SHP_opis '
            'ręcznie, albo po odrzuceniu wcześniejszego pytania).')
        self.btn_wczytaj.clicked.connect(self._sprawdz_warstwy_opisowe)
        gorny_wiersz.addWidget(self.btn_wczytaj)

        gorny_wiersz.addStretch(1)

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
        gorny_wiersz.addWidget(self.btn_przypnij)

        lay.addLayout(gorny_wiersz)

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
        """Podpięte pod QgsProject.instance().cleared (nowy/pusty projekt,
        albo wczytanie innego projektu) - taki projekt nie ma zapisanej
        flagi, więc ukrywamy widget i odznaczamy przycisk przypięcia.
        Czyścimy też referencje do warstw z poprzedniego projektu - ich
        obiekty C++ znikają razem z projektem, a bez tego resetu wyglądają
        jak wciąż poprawne (nie są None), co powodowało RuntimeError
        "wrapped C/C++ object ... has been deleted" przy próbie użycia i
        blokowało ponowne wyszukanie/zapytanie o utworzenie warstw."""
        self._odswiez_przycisk_przypniecia(False)
        self.hide()

        self.klon_lyr = None
        self.pkt_lyr = None
        self.notatki_lyr = None
        self._grupa_aktywna = None
        self._zrodlo_stl = None
        self._stl_ignoruj = False
        for btn in self.btn_grupy.values():
            btn.setChecked(False)
        self._odswiez()

    # --------------------------------------------------------- stan UI --

    def _odswiez(self):
        if not _zywa(self.klon_lyr):
            self.klon_lyr = None
        if not _zywa(self.pkt_lyr):
            self.pkt_lyr = None
        if not _zywa(self.notatki_lyr):
            self.notatki_lyr = None

        self.btn_klonuj.setEnabled(self.klon_lyr is not None)

        for btn in self.btn_grupy.values():
            btn.setEnabled(self.pkt_lyr is not None)

        self.btn_notatki.setEnabled(self.notatki_lyr is not None)

    # ------------------------------------------------- wspolna logika ---

    def showEvent(self, event):
        super().showEvent(event)
        self._sprawdz_warstwy_opisowe()

    def _znajdz_automatycznie(self, nazwa, typ_geom, pola):
        """Warstwa już wczytana w projekcie pod domyślną nazwą, albo
        istniejący plik o tej nazwie w folderze SHP_opis - bez otwierania
        żadnego okna. Odrzuca (z ostrzeżeniem na pasku) warstwę/plik o
        właściwej nazwie i geometrii, ale BEZ wymaganych pól (np. obca
        warstwa o tej samej nazwie z innego szablonu) - inaczej pierwszy
        zapis punktu/odcinka wywala KeyError na brakującym polu. None,
        jeśli nic poprawnego nie znaleziono."""
        istniejaca = _znajdz_warstwe(nazwa, typ_geom)
        if istniejaca is not None:
            if _ma_pola(istniejaca, pola):
                return istniejaca
            self.iface.messageBar().pushWarning(
                'Warstwy opisowe',
                f'Wczytana warstwa "{nazwa}" ma niezgodny zestaw pól - '
                'pomijam ją, szukam/tworzę inną.')

        folder = _folder_opis()
        if folder:
            sciezka = os.path.join(folder, nazwa + '.shp')
            if os.path.isfile(sciezka):
                lyr = _wczytaj_plik(sciezka, nazwa)
                if _ma_pola(lyr, pola):
                    return lyr
                QgsProject.instance().removeMapLayer(lyr.id())
                self.iface.messageBar().pushWarning(
                    'Warstwy opisowe',
                    f'Plik "{nazwa}.shp" w {folder} ma niezgodny zestaw '
                    'pól - pomijam.')
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
             'Point', POLA_PUNKTY_WYMAGANE),
            (NAZWA_NOTATKI, 'notatki_lyr', QgsWkbTypes.PointGeometry,
             'Point', POLA_NOTATKI),
        ]

        brakujace = []
        for nazwa, atrybut, typ_geom, typ_geom_txt, pola in spec:
            if _zywa(getattr(self, atrybut)):
                continue
            setattr(self, atrybut, None)
            lyr = self._znajdz_automatycznie(nazwa, typ_geom, pola)
            if lyr is not None and nazwa == NAZWA_PUNKTY:
                _dopisz_brakujace_pola(lyr, POLA_PUNKTY, self.iface)
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
                        if nazwa == NAZWA_PUNKTY:
                            pola = POLA_PUNKTY
                        sciezka = os.path.join(folder, nazwa + '.shp')
                        lyr = _utworz_warstwe(
                            sciezka, typ_geom_txt, pola, nazwa)
                        setattr(self, atrybut, lyr)
                        if nazwa == NAZWA_KLON:
                            _wylacz_formularz(lyr)

        self._odswiez()

    # ------------------------------------------------------ warstwa Klon

    def _klonuj(self):
        if not _zywa(self.klon_lyr):
            return

        if self._rubber_klon is None:
            self._rubber_klon = QgsRubberBand(
                self.iface.mapCanvas(), QgsWkbTypes.LineGeometry)
            self._rubber_klon.setColor(QColor(255, 0, 0))
            self._rubber_klon.setWidth(2)
        self._rubber_klon.reset(QgsWkbTypes.LineGeometry)

        if self._narzedzie_klon is None:
            self._narzedzie_klon = _NarzedzieOdcinka(
                self.iface.mapCanvas(), self._rubber_klon, self._zapisz_klon)
        self.iface.mapCanvas().setMapTool(self._narzedzie_klon)

    def _zapisz_klon(self, zrodlo, cel):
        if not _zywa(self.klon_lyr):
            return

        geom = QgsGeometry.fromPolylineXY([zrodlo, cel])
        f = QgsFeature(self.klon_lyr.fields())
        f.setGeometry(geom)
        self.klon_lyr.dataProvider().addFeatures([f])
        self.klon_lyr.triggerRepaint()

    # -------------------------------------------------- warstwa punktowa

    def _wybierz_grupe(self, grupa):
        if not _zywa(self.pkt_lyr):
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
        if not _zywa(self.pkt_lyr) or self._grupa_aktywna is None:
            return

        grupa = self._grupa_aktywna
        stl = pokrywa = None
        if opis_stl.grupa_wymaga_stl(grupa):
            ok, stl = self._ustal_stl(koord)
            if not ok:
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

        if opis_stl.grupa_wymaga_stl(grupa):
            pokrywa = opis_stl.pokrywa_domyslna(grupa, inf_rozne)
            if pokrywa is None:
                dlg = _PokrywaDialog(grupa, self)
                if dlg.exec_() != QDialog.Accepted or not dlg.kod:
                    return
                pokrywa = dlg.kod

        f = QgsFeature(self.pkt_lyr.fields())
        f.setGeometry(QgsGeometry.fromPointXY(koord))
        f['GRUPA'] = grupa
        pola = {pole.name() for pole in self.pkt_lyr.fields()}
        if 'INF_ROZNE' in pola:
            f['INF_ROZNE'] = inf_rozne
        if stl and 'STL' in pola:
            f['STL'] = stl
        if pokrywa and 'POKRYWA' in pola:
            f['POKRYWA'] = pokrywa
        self.pkt_lyr.dataProvider().addFeatures([f])
        self.pkt_lyr.triggerRepaint()

    def _zrodlo_stl_gotowe(self):
        """ZrodloSTL (budowane raz i trzymane do zmiany/edycji warstwy),
        None po "Ignoruj" albo False, gdy punkt ma nie zostać dodany."""
        if self._zrodlo_stl is not None and _zywa(self._zrodlo_stl.lyr):
            return self._zrodlo_stl
        self._zrodlo_stl = None
        if self._stl_ignoruj:
            return None

        lyr = None
        kandydaci = opis_stl.warstwy_zrodla_stl()
        if kandydaci:
            lyr = wybierz_warstwe_z_kandydatow(
                self.iface, kandydaci, opis_stl.NAZWA_ZRODLA_STL)
            if lyr is None:
                return False
            if opis_stl.nazwa_pola_stl(lyr) is None:
                QMessageBox.warning(
                    self, 'Brak pola STL',
                    f'Warstwa "{lyr.name()}" nie ma pola STL.')
                lyr = None

        if lyr is None:
            dlg = _BrakZrodlaStlDialog(self)
            dlg.exec_()
            if dlg.wynik == dlg.IGNORUJ:
                self._stl_ignoruj = True
                return None
            if dlg.wynik != dlg.DALEJ:
                return False
            lyr = dlg.warstwa

        odczyt, komunikat = opis_stl.warstwa_do_odczytu(lyr)
        if komunikat:
            self.iface.messageBar().pushWarning('STL', komunikat)
        self._zrodlo_stl = opis_stl.ZrodloSTL(lyr, odczyt)
        # edycja warstwy źródłowej unieważnia zbudowany indeks
        lyr.dataChanged.connect(self._uniewaznij_zrodlo_stl)
        return self._zrodlo_stl

    def _uniewaznij_zrodlo_stl(self):
        self._zrodlo_stl = None

    def _ustal_stl(self, koord):
        """(ok, stl) - ok=False: punkt ma nie zostać dodany. STL z
        poligonu pod punktem albo najbliższego w promieniu 20 m; gdy brak -
        wybór ręczny z listy wartości STL warstwy źródłowej (bez wpisywania
        - kod spoza słownika i tak nie przejdzie przy zapisie do bazy)."""
        zrodlo = self._zrodlo_stl_gotowe()
        if zrodlo is False:
            return False, None
        if zrodlo is None:
            return True, None

        crs = self.iface.mapCanvas().mapSettings().destinationCrs()
        stl = zrodlo.stl_dla_punktu(koord, crs)
        if stl:
            return True, stl

        stl, ok = QInputDialog.getItem(
            self, 'Brak STL',
            'Ani pod punktem, ani w promieniu '
            f'{opis_stl.MAX_ODLEGLOSC:.0f} m w warstwie '
            f'"{zrodlo.lyr.name()}" nie ma poligonu z STL.\n'
            'Wybierz STL:',
            zrodlo.wartosci(), 0, False)
        stl = (stl or '').strip()
        if not ok or not stl:
            return False, None
        return True, stl

    # --------------------------------------------------- warstwa notatek

    def _notatki_toggle(self):
        if not _zywa(self.notatki_lyr):
            return

        if self._narzedzie_notatki is None:
            self._narzedzie_notatki = QgsMapToolEmitPoint(
                self.iface.mapCanvas())
            self._narzedzie_notatki.canvasClicked.connect(self._klik_notatki)
        self.iface.mapCanvas().setMapTool(self._narzedzie_notatki)

    def _klik_notatki(self, koord, _btn):
        if not _zywa(self.notatki_lyr):
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
