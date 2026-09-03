"""Sprawdza, czy warstwa WYDZ_PKT_stare i warstwy "grupy opis"
(opis_klon/opis_pkt/opis_notatki, patrz warstwa_opisow_dock.py) leżą na
wydzieleniach z warstwy WYDZ - na wzór shp_sprawdz_ciecie.py (kontrola
"Pkt_poza_wydz"/sprawdz_pnsw). Dla każdej sprawdzanej warstwy, która jest
akurat wczytana w projekcie, wierzchołki leżące poza WYDZ trafiają jako
osobna, czerwono podświetlona warstwa "<źródło>_poza_WYDZ" - do ręcznej
korekty w QGIS. Warstwy, których nie ma w projekcie, są pomijane bez
błędu (nie każdy projekt ma je wszystkie na raz)."""
import os

from qgis.core import (
    Qgis, QgsFeature, QgsGeometry, QgsProject, QgsSpatialIndex,
    QgsVectorLayer, QgsWkbTypes,
)

from .funkcje import wybierz_warstwe_z_kandydatow
from . import warstwa_opisow_dock as opis

_WARSTWY_DO_SPRAWDZENIA = [
    'WYDZ_PKT_stare',
    opis.NAZWA_KLON,
    opis.NAZWA_PUNKTY,
    opis.NAZWA_NOTATKI,
]


class SprawdzPolozenieOpisow:
    def __init__(self, iface):
        self.iface = iface

    def uruchom(self):
        lyrs = list(QgsProject.instance().mapLayers().values())
        kandydaci_wydz = [x for x in lyrs if x.name().upper() == 'WYDZ']
        wydz = wybierz_warstwe_z_kandydatow(self.iface, kandydaci_wydz, 'WYDZ')
        if wydz is None:
            self.iface.messageBar().pushWarning(
                'Wydzielenia',
                'Tylko jedna warstwa w TOC powinna nazywać się WYDZ')
            return

        si = QgsSpatialIndex()
        sl_wydz = {}
        for feat in wydz.getFeatures():
            si.insertFeature(feat)
            sl_wydz[feat.id()] = feat

        podsumowanie = []
        sprawdzono = 0
        for nazwa in _WARSTWY_DO_SPRAWDZENIA:
            kandydaci = [x for x in lyrs if x.name().upper() == nazwa.upper()]
            zrodlo = wybierz_warstwe_z_kandydatow(self.iface, kandydaci, nazwa)
            if zrodlo is None:
                continue
            sprawdzono += 1

            poza = self._szukaj_poza_wydz(zrodlo, si, sl_wydz)
            if poza:
                self._utworz_warstwe_poza(zrodlo, poza, nazwa)
            podsumowanie.append(f'{nazwa}: {len(poza)} poza WYDZ')

        if sprawdzono == 0:
            self.iface.messageBar().pushWarning(
                'Brak warstw',
                'W projekcie nie znalazłem żadnej z warstw do sprawdzenia '
                '(WYDZ_PKT_stare, ' + opis.NAZWA_KLON + ', ' +
                opis.NAZWA_PUNKTY + ', ' + opis.NAZWA_NOTATKI + ')')
            return

        self.iface.messageBar().pushMessage(
            'OK', 'Sprawdzanie położenia zakończone: ' +
            '; '.join(podsumowanie), Qgis.Success, 10)

    def _szukaj_poza_wydz(self, zrodlo, si, sl_wydz):
        """Zwraca listę (feature, punkt) dla wierzchołków źródła, które nie
        leżą na żadnym wydzieleniu z WYDZ. Dla warstw punktowych to sam
        punkt obiektu, dla linii (opis_klon) - oba jej końce (początek =
        wydzielenie źródłowe, koniec = docelowe)."""
        wynik = []
        for feat in zrodlo.getFeatures():
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue

            if geom.type() == QgsWkbTypes.PointGeometry:
                if geom.isMultipart():
                    punkty = [QgsGeometry.fromPointXY(p)
                              for p in geom.asMultiPoint()]
                else:
                    punkty = [geom]
            elif geom.type() == QgsWkbTypes.LineGeometry:
                if geom.isMultipart():
                    punkty = [QgsGeometry.fromPointXY(p)
                              for linia in geom.asMultiPolyline()
                              for p in linia]
                else:
                    punkty = [QgsGeometry.fromPointXY(p)
                              for p in geom.asPolyline()]
            else:
                continue

            for pkt in punkty:
                ids = si.intersects(pkt.boundingBox())
                if not any(sl_wydz[it].geometry().intersects(pkt)
                           for it in ids):
                    wynik.append((feat, pkt))
        return wynik

    def _utworz_warstwe_poza(self, zrodlo, wynik, nazwa):
        plug = os.path.dirname(__file__)
        lyr = QgsVectorLayer(
            f'MultiPoint?crs={zrodlo.crs().authid()}',
            nazwa + '_poza_WYDZ', 'memory')
        dp = lyr.dataProvider()
        lyr.startEditing()
        dp.addAttributes(zrodlo.fields().toList())
        lyr.updateFields()

        nowe = []
        for feat, pkt in wynik:
            nf = QgsFeature(lyr.fields())
            nf.setGeometry(pkt)
            nf.setAttributes(feat.attributes())
            nowe.append(nf)
        dp.addFeatures(nowe)
        lyr.commitChanges()

        dodana = QgsProject.instance().addMapLayer(lyr)
        dodana.loadNamedStyle(os.path.join(
            plug, '..', 'qml', 'point_drop_shadow_red.qml'))
