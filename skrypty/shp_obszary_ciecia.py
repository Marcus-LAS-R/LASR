import os

from qgis.core import (
    QgsField, QgsVectorLayer, QgsGeometry, QgsRectangle,
    QgsFeature, QgsCoordinateReferenceSystem, QgsVectorFileWriter,
    QgsProject,
)
from PyQt5.QtCore import QVariant

from . import kafelkowanie

# kandydaci na pole z czytelnym identyfikatorem wydzielenia do raportu
# "przeciete" - ta sama mala prywatna stala co w shp_atlasuj_auto.py
# (zduplikowana zamiast importu w poprzek modulow, zgodnie z konwencja
# projektu)
_KANDYDACI_POLE_ID = ('ADR_LES', 'ADRESS_FOREST', 'WYDZ')


def _pole_identyfikatora(warstwa):
    nazwy = {p.name() for p in warstwa.fields()}
    for kandydat in _KANDYDACI_POLE_ID:
        if kandydat in nazwy:
            return kandydat
    return None


class ObszaryCiecia:
    """ Tworzy warstwę OBSZARY_CIECIA - kafle (format A3 w poziomie,
    skala 1:12000) wycentrowane na poligonach WYDZ przygotowanych do
    cięcia. Warstwa służy do przeglądu feature-by-feature (np. wtyczką
    Go2NextFeature), żeby sprawdzić, czy podział na poletka/etaty cięcia
    wykonano poprawnie. Kafle mogą się nachodzić, jeśli wydzielenia leżą
    blisko siebie. Wydzielenie, które samo w sobie nie mieści się w
    kaflu (rzadkie), dostaje kafel wycentrowany na sobie i zostaje
    przecięte krawędzią - zgłaszane w podsumowaniu (self.przeciete).

    Wywoływana automatycznie z shp_przygCiecie.przygotuj_wydz_do_ciecia
    na świeżo utworzonej warstwie WYDZ (brak osobnej pozycji w menu).
    """

    PAPIER_MM = [297, 420]  # A3
    SKALA = 12000
    MARGINES_MM = 30  # 1cm zakładki z każdej strony, jak w Atlasuj

    def __init__(self, iface):
        self.iface = iface
        self.wydz = False
        self.kat = ''
        self.rozm = []  # rozmiar kafla w metrach [x, y], w poziomie
        self.lyr = False
        self.przeciete = []  # identyfikatory (albo fid) obiektow przecietych

    def wybierz_warstwe(self, wydz=None):
        """ `wydz` pozwala podać warstwę programowo (np. z poziomu
        innego skryptu, tuż po jej utworzeniu) - bez tego brana jest
        aktywna warstwa w QGIS-ie. """
        self.wydz = wydz if wydz is not None else self.iface.activeLayer()
        if self.wydz is None or self.wydz.wkbType() not in [3, 6]:
            self.iface.messageBar().pushWarning(
                'Obszary cięcia',
                'Zaznacz warstwę powierzchniową WYDZ przygotowaną do cięcia'
            )
            return False

        try:
            self.kat = os.path.dirname(
                self.wydz.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            self.iface.messageBar().pushWarning(
                'Obszary cięcia',
                'Nie udało się ustalić katalogu warstwy WYDZ'
            )
            return False

        # rozmiar kafla w metrach, A3 w poziomie przy skali 1:12000
        self.rozm = kafelkowanie.rozmiar_kafla_z_skali(
            [self.PAPIER_MM[1], self.PAPIER_MM[0]],  # w poziomie
            self.SKALA, self.MARGINES_MM
        )
        return True

    def generuj_siatke(self):
        self.lyr = QgsVectorLayer(
            "Polygon?crs=epsg:2180&index=yes", "OBSZARY_CIECIA", "memory")
        self.lyr.startEditing()
        self.lyr.dataProvider().addAttributes([
            QgsField("NR", QVariant.Int),
            QgsField("ZROBIONE", QVariant.String, len=50),
        ])
        self.lyr.updateFields()

        pole_id = _pole_identyfikatora(self.wydz)
        bboxy = []
        identyfikatory = []
        for f in self.wydz.getFeatures():
            bb = f.geometry().boundingBox()
            bboxy.append(
                (bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()))
            identyfikatory.append(f[pole_id] if pole_id else f.id())

        kafle, przeciete = kafelkowanie.pokryj_kaflami(
            bboxy, self.rozm[0], self.rozm[1])
        self.przeciete = [identyfikatory[i] for i in przeciete]

        nowe = []
        for nr, (x0, y0, x1, y1) in enumerate(kafle, start=1):
            feat = QgsFeature()
            feat.setFields(self.lyr.fields())
            feat.setGeometry(QgsGeometry.fromRect(
                QgsRectangle(x0, y0, x1, y1)))
            feat['NR'] = nr
            nowe.append(feat)

        self.lyr.dataProvider().addFeatures(nowe)
        self.lyr.commitChanges()
        return len(kafle)

    def zapisz_warstwe(self):
        # usun poprzednia warstwe z TOC (zwalnia blokade pliku na Windows)
        stare = [l for l in QgsProject.instance().mapLayers().values()
                 if l.name() == 'OBSZARY_CIECIA']
        if stare:
            QgsProject.instance().removeMapLayers([l.id() for l in stare])

        rozsz = ['shp', 'shx', 'dbf', 'prj', 'sbx', 'cpg', ]
        try:
            for r in rozsz:
                sciezka = os.path.join(self.kat, 'OBSZARY_CIECIA.' + r)
                if os.path.isfile(sciezka):
                    os.remove(sciezka)
        except:  # nopep8
            self.iface.messageBar().pushCritical(
                'BŁĄD',
                'Nie udało się usunąć poprzedniej wersji plików '
                'OBSZARY_CIECIA, proszę zamknąć warstwę w QGIS i ponownie '
                'uruchomić skrypt'
            )
            return False

        crs = QgsCoordinateReferenceSystem("epsg:2180")
        sciezka = os.path.join(self.kat, "OBSZARY_CIECIA.shp")
        QgsVectorFileWriter.writeAsVectorFormat(
            self.lyr, sciezka, "UTF-8", crs, "ESRI Shapefile")

        warstwa = QgsVectorLayer(sciezka, "OBSZARY_CIECIA", "ogr")
        QgsProject.instance().addMapLayer(warstwa)

        plugin_dir = os.path.dirname(__file__)
        warstwa.loadNamedStyle(
            os.path.join(plugin_dir, '..', 'qml', 'poly_red_outline.qml'))
        warstwa.triggerRepaint()
        return True

    def wyswietl_info(self, ile):
        if ile == 0:
            self.iface.messageBar().pushWarning(
                'Obszary cięcia',
                'Warstwa WYDZ nie zawiera żadnych wydzieleń'
            )
            return

        self.iface.messageBar().pushSuccess(
            'OK',
            'Utworzono warstwę OBSZARY_CIECIA z ' + str(ile) +
            ' obszarami do przeglądu (np. wtyczką Go2NextFeature)'
        )
        if self.przeciete:
            lista = ', '.join(str(x) for x in self.przeciete[:10])
            if len(self.przeciete) > 10:
                lista += ', … (+' + str(len(self.przeciete) - 10) + ')'
            self.iface.messageBar().pushWarning(
                'Obszary cięcia',
                str(len(self.przeciete)) + ' wydzielenie(a) nie zmieściło '
                'się w całości w jednym obszarze i zostało przecięte '
                'krawędzią (zbyt duże przy tej skali/formacie): ' + lista
            )
