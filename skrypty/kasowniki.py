"""Warstwa "kasowników" - krótkich kresek prostopadłych do granicy,
oznaczających że dana linia NIE dzieli wydzielenia na osobne wydzielenia
(np. granica między częściami tego samego wieloczęściowego wydzielenia,
albo linia podziału powierzchniowego z warstwy LINIE).

Port z wtyczki LCH (skrypty/kasowniki.py, klasa GenerujKasowniki) - sam
algorytm geometryczny (generowanie punktów na granicach, dobór najbliższych
par punktów między częściami, rysowanie kresek) bez zmian. Zmieniony tylko
sposób podania danych wejściowych/wyjściowych: zamiast wyszukiwania warstwy
"WYDZ_POL" po nazwie w projekcie i zapisu zawsze do folderu projektu jako
"KAS.shp", GenerujKasowniki przyjmuje warstwę wydzieleń, folder wyjściowy i
nazwę pliku wynikowego jako parametry - żeby dało się go użyć też dla
danych ze starego UPUL (skrypty/shp_przygCiecieStUPUL.py, warstwa
KAS_stare w folderze SHP_stare).
"""
import math
import os
from collections import defaultdict

from numpy import arctan2, rad2deg, pi
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor
from qgis.core import (
    QgsFeature, QgsField, QgsGeometry, QgsMessageLog, QgsPointXY,
    QgsProject, QgsVectorFileWriter, QgsVectorLayer, Qgis,
)
import processing


class _recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)


def _opcje_zapisu():
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    return opcje


class GenerujKasowniki:
    """Generuje warstwę liniową kasowników na podstawie wieloczęściowych
    poligonów wydzieleń (pole ADR_LES, adres 25-znakowy UPUL) i -
    opcjonalnie - warstwy LINIE (dodatkowe podziały powierzchniowe).

    Wynik zapisywany jako `<kat_wyj>/<nazwa>.shp` - dostępny potem jako
    `self.warstwa` (QgsVectorLayer albo None, jeśli zapis się nie udał).
    Warstwa NIE jest dodawana do projektu - o tym decyduje wywołujący.
    """

    def __init__(self, wydz_lyr, kat_wyj, nazwa='KAS', linie_sc=None,
                 kat_temp=None):
        self.wydz = wydz_lyr
        self.kat_wyj = kat_wyj
        self.nazwa = nazwa
        self.linie_sc = linie_sc
        self.kattemp = kat_temp or os.path.join(kat_wyj, 'temp_kas')
        os.makedirs(self.kattemp, exist_ok=True)

        self.interval = 15  # rozstaw punktów na granicy [m]
        self.bBfRadius = -6
        self.sBfRadius = -2
        self.ramie = 4
        self.canLength = 7  # długość kreski kasownika [m]

        self.warstwa = None

        self._ustaw_warstwe()

        self.arodPoints = _recursivedefaultdict()  # słownik wszystkich punktów
        self.arodDist = _recursivedefaultdict()  # słownik najbliższych odległości
        self._generuj_punkty()
        self._kasowniki_wydzielen()
        if self.linie_sc:
            self._kasowniki_linii()
        self._zapisz()

    # ------------------------------------------------------- I/O

    def _ustaw_warstwe(self):
        self.layerCan = QgsVectorLayer(
            'LineString?crs=epsg:2180&index=yes', self.nazwa, 'memory')
        self.prCan = self.layerCan.dataProvider()
        self.prCan.addAttributes([
            QgsField('ID', QVariant.Int),
            QgsField('COMMUNITY', QVariant.String),
            QgsField('MUNICIP', QVariant.String),
        ])
        self.layerCan.updateFields()

    def _zapisz(self):
        self.layerCan.commitChanges()
        os.makedirs(self.kat_wyj, exist_ok=True)
        sciezka = os.path.join(self.kat_wyj, self.nazwa + '.shp')
        QgsVectorFileWriter.writeAsVectorFormatV3(
            self.layerCan, sciezka, QgsProject.instance().transformContext(),
            _opcje_zapisu())

        warstwa = QgsVectorLayer(sciezka, self.nazwa, 'ogr')
        if not warstwa.isValid():
            QgsMessageLog.logMessage(
                f'Nie udało się zapisać warstwy {self.nazwa}', 'Las-R',
                Qgis.Warning)
            return
        symbol = warstwa.renderer().symbol()
        symbol.setColor(QColor.fromRgb(0, 0, 0))
        self.warstwa = warstwa

    # ------------------------------------------------- geometria - wspólne

    def mag(self, point):
        return math.sqrt(point.x()**2 + point.y()**2)

    def diff(self, point2, point1):
        return QgsPointXY(point2.x()-point1.x(), point2.y() - point1.y())

    def length(self, point1, point2):
        return math.sqrt(point1.sqrDist(point2))

    def dircos(self, point):
        cosa = point.x() / self.mag(point)
        cosb = point.y() / self.mag(point)
        return cosa, cosb

    def calcDistance(self, point0, point1):
        return math.sqrt((point0[0]-point1[0])**2+(point0[1]-point1[1])**2)

    def calcAngle(self, tab):
        # kąt linii kartezjańsko, przeciwnie do wskazówek zegara od N
        ang1 = arctan2(tab[0][1], tab[0][0])
        ang2 = arctan2(tab[1][1], tab[1][0])
        angle_org = rad2deg((ang1 - ang2) % (2 * pi))
        return 360 - angle_org

    def calculateCanceller(self, tab):
        if tab[0][0] <= tab[1][0]:
            tab_temp = tab[0]
            tab[0] = tab[1]
            tab[1] = tab_temp

        tabw = [[0, 10], [tab[1][0]-tab[0][0], tab[1][1]-tab[0][1]]]
        angle_org = self.calcAngle(tabw)

        if tab[0][1] <= tab[1][1]:
            angle = angle_org + 90 - 30
            if angle > 360:
                angle -= 360
            angle2 = angle_org + 270 - 30
            if angle2 < 0:
                angle2 += 360
        else:
            angle = angle_org + 90 - 30
            if angle > 360:
                angle -= 360
            angle2 = (angle_org - 90) - 30
            if angle2 < 0:
                angle2 += 360

        angle = math.radians(angle)
        angle2 = math.radians(angle2)

        points = []
        points.append(QgsPointXY(tab[0][0]+self.ramie*math.cos(angle),
                                  tab[0][1]+self.ramie*math.sin(angle)))
        points.append(QgsPointXY(tab[0][0], tab[0][1]))
        points.append(QgsPointXY(tab[1][0], tab[1][1]))
        points.append(QgsPointXY(tab[1][0]+self.ramie*math.cos(angle2),
                                  tab[1][1]+self.ramie*math.sin(angle2)))
        return points

    def calcPosOnLine(self, tab, ll):
        # dwa punkty prostopadłe do linii w danej odległości
        tabw = [[0, 10], [tab[1][0]-tab[0][0], tab[1][1]-tab[0][1]]]
        angle_org = self.calcAngle(tabw)
        if angle_org > 360:
            angle_org -= 360

        pointm = self.diff(QgsPointXY(tab[1][0], tab[1][1]),
                            QgsPointXY(tab[0][0], tab[0][1]))
        cosa, cosb = self.dircos(pointm)
        ppoint = [tab[0][0]+(ll*cosa), tab[0][1]+(ll*cosb)]

        angle2 = angle_org
        if angle2 > 360:
            angle2 -= 360
        angle3 = angle_org + 180
        if angle3 < 0:
            angle3 += 360

        angle2r = math.radians(angle2)
        angle3r = math.radians(angle3)

        tab2 = [[ppoint[0]+self.canLength*math.cos(angle2r),
                 ppoint[1]+self.canLength*math.sin(angle2r)],
                [ppoint[0]+self.canLength*math.cos(angle3r),
                 ppoint[1]+self.canLength*math.sin(angle3r)]]
        return [angle_org, ppoint], tab2

    def addArodCanceller(self, tab, wydz_key):
        # adres UPUL (25 znaków): COUNTY_L[0]-DISTRICT[1:3]-MUNICIP[3:6]
        # -COMMUNITY[6:10]-GRP[11:13]-ODDZ[13:17]-WYDZ[18:22]-SUFIKS[23:25]
        fet = QgsFeature()
        fet.setGeometry(
            QgsGeometry.fromPolylineXY(self.calculateCanceller(tab)))
        fet.setAttributes([0, wydz_key[6:10], wydz_key[3:6]])
        self.prCan.addFeatures([fet])
        self.layerCan.updateExtents()

    # ------------------------------------- generowanie punktów na granicach

    def _generuj_punkty(self):
        for f in self.wydz.getFeatures():
            geom = f.geometry()
            adr = f['ADR_LES']
            if not adr:
                continue
            if geom.isMultipart() and adr[18:20].upper() != 'LZ':
                for nrp, p in enumerate(geom.asMultiPolygon()):
                    self.arodPoints[adr][nrp] = []
                    pBgeom = QgsGeometry.fromPolygonXY(p)
                    bf = pBgeom.buffer(self.bBfRadius, 5)
                    if not self._sprawdz_metode_generacji(adr, nrp, bf):
                        if not self._sprawdz_metode_generacji(
                                adr, nrp, pBgeom.buffer(self.sBfRadius, 5)):
                            self._generuj_centroid(
                                adr, nrp, QgsGeometry.fromPolygonXY(p))

    def _sprawdz_metode_generacji(self, adr, nrp, bf):
        """Sprawdza czy bufor jest poligonem/multipoligonem - jeśli tak,
        generuje z niego punkty na granicy."""
        if not bf.isMultipart():
            if len(bf.asPolygon()) > 0 and bf.asPolygon()[0] != []:
                self._generuj_punkty_bufora(adr, nrp, bf)
                return True
        else:
            if len(bf.asMultiPolygon()) > 0 and bf.asMultiPolygon()[0] != []:
                for pol in bf.asMultiPolygon():
                    self._generuj_punkty_bufora(
                        adr, nrp, QgsGeometry.fromPolygonXY(pol))
                return True
            return False
        return False

    def _generuj_punkty_bufora(self, adr, nrp, bf):
        start_point = False
        for i, pii in enumerate(bf.asPolygon()):
            for j, pj in enumerate(pii):
                if not start_point:
                    start_point = QgsPointXY(pj[0], pj[1])
                else:
                    line_start = start_point
                    self.arodPoints[adr][nrp].append(
                        [line_start.x(), line_start.y()])
                    line_end = QgsPointXY(pj[0], pj[1])

                    pointm = self.diff(line_end, line_start)
                    cosa, cosb = self.dircos(pointm)
                    lg = self.length(line_end, line_start)

                    for ii in range(self.interval, int(round(lg, 0)),
                                     self.interval):
                        self.arodPoints[adr][nrp].append([
                            line_start.x() + (ii*cosa),
                            line_start.y() + (ii*cosb)])
                    start_point = line_end

    def _generuj_centroid(self, adr, nrp, geom):
        self.arodPoints[adr][nrp].append([
            geom.centroid().asPoint().x(),
            geom.centroid().asPoint().y()])

    # --------------------------------------- kasowniki między częściami

    def _kasowniki_wydzielen(self):
        self._oblicz_odleglosci()
        self._wybierz_kasowniki()

    def _oblicz_odleglosci(self):
        for wydz_key, wydz in self.arodPoints.items():
            for nrp in wydz.keys():
                restKeys = list(wydz.keys())
                restKeys.remove(nrp)
                min_odl = {x: [99999, 0, 0] for x in restKeys}
                for i in range(len(wydz[nrp])):
                    point0 = wydz[nrp][i]
                    for nrpi in restKeys:
                        tab = [[self.calcDistance(point0, x), point0, x]
                               for x in wydz[nrpi]]
                        tab = sorted(tab, key=lambda x: x[0])
                        if min_odl[nrpi][0] > tab[0][0]:
                            min_odl[nrpi] = tab[0]
                for k, tab in min_odl.items():
                    self.arodDist[wydz_key][nrp][k] = tab

    def _wybierz_kasowniki(self):
        for wydz_key, wydz in self.arodDist.items():
            l_con = [0]
            l_uncon = [x for x in wydz.keys() if x > 0]
            while len(l_uncon) > 0:
                closest = []
                for itc in l_con:
                    closest += [[itc, itu] + x
                                for itu, x in wydz[itc].items()
                                if itu != itc and itu not in l_con]
                closest = sorted(closest, key=lambda x: x[2])
                self.addArodCanceller(closest[0][3:], wydz_key)
                l_con += [closest[0][1]]
                l_uncon.remove(int(closest[0][1]))

    # ------------------------------------------ kasowniki na liniach

    def _kasowniki_linii(self):
        lin = QgsVectorLayer(self.linie_sc, 'LINIE', 'ogr')
        if not lin.isValid():
            QgsMessageLog.logMessage(
                f'Brak warstwy LINIE: {self.linie_sc}', 'Las-R', Qgis.Warning)
            return

        singleparts_sc = os.path.join(
            self.kattemp, 'wydz_pol_singleparts.shp')
        processing.run('native:multiparttosingleparts', {
            'INPUT': self.wydz,
            'OUTPUT': singleparts_sc,
        })

        buffer_sc = os.path.join(self.kattemp, 'wydz_pol_buffer5.shp')
        processing.run('native:buffer', {
            'INPUT': singleparts_sc,
            'DISTANCE': -5.0,
            'SEGMENTS': 1,
            'DISSOLVE': False,
            'OUTPUT': buffer_sc,
        })

        clip_sc = os.path.join(self.kattemp, 'LINIE_CLIP.shp')
        processing.run('native:intersection', {
            'INPUT': self.linie_sc,
            'OVERLAY': buffer_sc,
            'INPUT_FIELDS': '',
            'OVERLAY_FILEDS': '',
            'OUTPUT': clip_sc,
        })

        clip_sp_sc = os.path.join(
            self.kattemp, 'LINIE_CLIP_SINGLEPARTS.shp')
        processing.run('native:multiparttosingleparts', {
            'INPUT': clip_sc,
            'OUTPUT': clip_sp_sc,
        })
        linie = QgsVectorLayer(clip_sp_sc, 'LINIE_clip', 'ogr')

        for feat in linie.getFeatures():
            geom = feat.geometry()
            adr = feat['ADR_LES']
            if not adr:
                continue
            ll = geom.length()
            distPrev = 0
            trig = True
            for line in geom.asMultiPolyline():
                for i, pt in enumerate(line):
                    if i == 0:
                        pt0 = pt
                    else:
                        dist = self.calcDistance(pt0, pt)
                        if distPrev + dist > ll / 2 and trig:
                            distAdd = (ll / 2) - distPrev
                            if pt0[0] <= pt[0]:
                                tab_temp = pt0
                                pt0 = pt
                                pt = tab_temp
                            _, tab = self.calcPosOnLine(
                                [pt0, pt], dist-distAdd)
                            self.addArodCanceller(tab, adr)
                            trig = False
                        distPrev += dist
                        pt0 = pt
