"""Warstwa do opisów - dockwidget do szybkiego tworzenia dwóch warstw
pomocniczych przy pracy nad opisami taksacyjnymi:

- warstwa liniowa "Klon" (pola ADR_Z/ADR_DO) - do rysowania odcinków
  źródło->cel, z których "Utwórz KLON.txt"
  (aktualizacja_upul/core/utworz_klon_txt.py) buduje potem plik dla
  "Klonuj opisy wydzieleń",
- warstwa punktowa (pole GRUPA) - punkty w czterech kategoriach (INNE
  WYL, L ENERG, SUKCESJA, DROGI L) jako podstawa do wgrania krótkiego,
  generycznego opisu taksacyjnego (osobny skrypt, poza zakresem tego
  widgetu).

Przyciski grup aktywują klikanie po mapie własnym narzędziem
(QgsMapToolEmitPoint), które dodaje punkt bezpośrednio przez
dataProvider - bez formularza atrybutów, z GRUPA już wypełnioną. Można
klikać wiele punktów pod rząd; zmiana aktywnej grupy nie wyłącza trybu
klikania, tylko zmienia wartość wpisywaną w kolejnych punktach.
"""
import os

from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (
    QDockWidget, QFileDialog, QGroupBox, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsFeature, QgsField, QgsGeometry,
    QgsProject, QgsVectorFileWriter, QgsVectorLayer, QgsWkbTypes,
)
from qgis.gui import QgsMapToolEmitPoint

CRS = QgsCoordinateReferenceSystem('EPSG:2180')

NAZWA_KLON = 'Klon'
NAZWA_PUNKTY = 'Opisy_pkt'

GRUPY = ['INNE WYL', 'L ENERG', 'SUKCESJA', 'DROGI L', 'LZ-Ł']


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

    lyr = QgsVectorLayer(sciezka, nazwa, 'ogr')
    QgsProject.instance().addMapLayer(lyr)
    return lyr


class WarstwaOpisowDock(QDockWidget):

    tytul = 'Warstwa do opisów'

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle(self.tytul)
        self.setSizePolicy(
            QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.klon_lyr = None
        self.pkt_lyr = None
        self._grupa_aktywna = None
        self._narzedzie_pkt = None

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

        row_klon = QHBoxLayout()
        self.btn_utworz_klon = QPushButton('Utwórz/wskaż warstwę Klon')
        self.btn_utworz_klon.clicked.connect(self._utworz_klon)
        row_klon.addWidget(self.btn_utworz_klon)

        self.btn_klonuj = QPushButton('Klonuj')
        self.btn_klonuj.setToolTip(
            'Włącza edycję warstwy Klon i tryb dodawania nowego odcinka '
            '(początek = wydzielenie źródłowe, koniec = docelowe).')
        self.btn_klonuj.clicked.connect(self._klonuj)
        row_klon.addWidget(self.btn_klonuj)
        lay_klon.addLayout(row_klon)

        lay.addWidget(box_klon)

        # --- warstwa punktowa ------------------------------------------
        box_pkt = QGroupBox('Warstwa punktowa (opisy generyczne)', glowny)
        lay_pkt = QVBoxLayout(box_pkt)

        self.lab_pkt = QLabel('Warstwa: brak')
        lay_pkt.addWidget(self.lab_pkt)

        self.btn_utworz_pkt = QPushButton('Utwórz/wskaż warstwę punktową')
        self.btn_utworz_pkt.clicked.connect(self._utworz_punkty)
        lay_pkt.addWidget(self.btn_utworz_pkt)

        lay_pkt.addWidget(QLabel('Grupa (klik = tryb dodawania punktów):'))
        siatka = QGridLayout()
        self.btn_grupy = {}
        for i, grupa in enumerate(GRUPY):
            btn = QPushButton(grupa)
            btn.setCheckable(True)
            btn.clicked.connect(
                lambda _checked, g=grupa: self._wybierz_grupe(g))
            siatka.addWidget(btn, i // 2, i % 2)
            self.btn_grupy[grupa] = btn
        lay_pkt.addLayout(siatka)

        lay.addWidget(box_pkt)
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

    def _folder_startowy(self):
        for lyr in QgsProject.instance().mapLayers().values():
            try:
                sc = lyr.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    return os.path.dirname(sc)
            except Exception:
                pass
        return ''

    # ------------------------------------------------------ warstwa Klon

    def _utworz_klon(self):
        istniejaca = _znajdz_warstwe(NAZWA_KLON, QgsWkbTypes.LineGeometry)
        if istniejaca is not None:
            self.klon_lyr = istniejaca
            self._odswiez()
            return

        sciezka, _ = QFileDialog.getSaveFileName(
            self, 'Zapisz warstwę Klon',
            os.path.join(self._folder_startowy(), NAZWA_KLON + '.shp'),
            'Shapefile (*.shp)')
        if not sciezka:
            return

        pola = [
            QgsField('ADR_Z', QVariant.String, '', 25),
            QgsField('ADR_DO', QVariant.String, '', 25),
        ]
        self.klon_lyr = _utworz_warstwe(
            sciezka, 'LineString', pola, os.path.splitext(
                os.path.basename(sciezka))[0])
        self._odswiez()

    def _klonuj(self):
        if self.klon_lyr is None:
            return
        self.iface.setActiveLayer(self.klon_lyr)
        if not self.klon_lyr.isEditable():
            self.klon_lyr.startEditing()
        self.iface.actionAddFeature().trigger()

    # -------------------------------------------------- warstwa punktowa

    def _utworz_punkty(self):
        istniejaca = _znajdz_warstwe(NAZWA_PUNKTY, QgsWkbTypes.PointGeometry)
        if istniejaca is not None:
            self.pkt_lyr = istniejaca
            self._odswiez()
            return

        sciezka, _ = QFileDialog.getSaveFileName(
            self, 'Zapisz warstwę punktową',
            os.path.join(self._folder_startowy(), NAZWA_PUNKTY + '.shp'),
            'Shapefile (*.shp)')
        if not sciezka:
            return

        pola = [QgsField('GRUPA', QVariant.String, '', 20)]
        self.pkt_lyr = _utworz_warstwe(
            sciezka, 'Point', pola, os.path.splitext(
                os.path.basename(sciezka))[0])
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

        f = QgsFeature(self.pkt_lyr.fields())
        f.setGeometry(QgsGeometry.fromPointXY(koord))
        f['GRUPA'] = self._grupa_aktywna
        self.pkt_lyr.dataProvider().addFeatures([f])
        self.pkt_lyr.triggerRepaint()
