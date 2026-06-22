import os

from qgis.core import (
    QgsField, QgsVectorLayer, QgsGeometry, QgsRectangle,
    QgsFeature, QgsCoordinateReferenceSystem, QgsVectorFileWriter,
    QgsProject,
)
from PyQt5.QtCore import QVariant

from . import kafelkowanie


class ObszaryCiecia:
    """ Tworzy warstwę OBSZARY_CIECIA - kafle (format A3 w poziomie,
    skala 1:12000) wycentrowane na poligonach WYDZ przygotowanych do
    cięcia. Warstwa służy do przeglądu feature-by-feature (np. wtyczką
    Go2NextFeature), żeby sprawdzić, czy podział na poletka/etaty cięcia
    wykonano poprawnie. Kafle mogą się nachodzić, jeśli wydzielenia leżą
    blisko siebie - każde wydzielenie zostaje w całości w jednym kaflu.
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

    def wybierz_warstwe(self):
        self.wydz = self.iface.activeLayer()
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

        bboxy = []
        for f in self.wydz.getFeatures():
            bb = f.geometry().boundingBox()
            bboxy.append(
                (bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum()))

        kafle = kafelkowanie.pokryj_kaflami(
            bboxy, self.rozm[0], self.rozm[1])

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
        else:
            self.iface.messageBar().pushSuccess(
                'OK',
                'Utworzono warstwę OBSZARY_CIECIA z ' + str(ile) +
                ' obszarami do przeglądu (np. wtyczką Go2NextFeature)'
            )
