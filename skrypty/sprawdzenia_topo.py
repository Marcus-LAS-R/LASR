# -*- coding: utf-8 -*-
import os
from qgis.core import QgsVectorLayer, QgsGeometry, QgsPointXY, QgsProject, \
    QgsFeature, QgsSpatialIndex, QgsField
from PyQt5.QtCore import QVariant
from collections import defaultdict

from .funkcje import poprawna_topo


class recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)


class SprawdzTopo():
    def __init__(self, lyr):
        self.lyr = lyr
        self.slf = {}  # slownik feat z warstwy
        self.slfi = QgsSpatialIndex()  # SI z featurow warstwy
        self.bl_pkt = {}  # sl z bledami pktowymi id: [X, Y, typ]

        # tablica z bledami powierzchniowymi, [geometry, typ]
        self.bl_poly = []

        # sl z wszystkimi pkt w warstwie [X][Y] = [2, 2]
        # pierwsza wartość, liczba wystapien podczas wczytywania z warstwy
        # druga wart. liczba granic poligonow w tym pkt
        self.slpkt = recursivedefaultdict()

        self.trig_spr_wst = False

    def pobierz_feat(self):
        for f in self.lyr.getFeatures():
            self.slf[f.id()] = f

        self.slfi = QgsSpatialIndex(self.lyr.getFeatures())

    def spr_wstepne(self):
        self.pkt_c = 0
        for f in self.slf.values():
            s = {}
            for feat in f.geometry().asMultiPolygon():
                if len(feat) > 0:
                    for part in feat:
                        for i, pkt_raw in enumerate(part):
                            pkt = [round(pkt_raw[0], 3),
                                   round(pkt_raw[1], 3)]
                            if i < len(part) - 1:
                                blad = False

                                # sprawdzania lok. featura
                                if pkt[0] not in s:
                                    s[pkt[0]] = pkt[1]
                                else:
                                    if s[pkt[0]] == pkt[1]:
                                        self.bl_pkt[self.pkt_c] = [
                                            pkt[0],
                                            pkt[1],
                                            'Zdublowany wierzcholek']
                                        self.pkt_c += 1
                                        blad = True

                                # dodanie do globalnego slownika
                                if pkt[0] not in self.slpkt:
                                    self.slpkt[pkt[0]][pkt[1]] = [1, 0]

                                elif pkt[1] not in self.slpkt[pkt[0]]:
                                        self.slpkt[pkt[0]][pkt[1]] = [1, 0]
                                else:
                                    if not blad:
                                        self.slpkt[pkt[0]][pkt[1]][0] += 1

        # trig do dalszych analiz
        self.trig_spr_wst = True

    def spr_styki(self):
        """Metoda sprawdza czy stykajace sie poligony na wspolnym odc maja
        taka sam liczbę wierzchołków. Jeżeli nie generowany jest pkt z bledem.
        """
        if not self.trig_spr_wst:
            return False

        print('zaczynam sprawdzac styki')
        for f in self.slf.values():
            gbuff = f.geometry().buffer(0.01, 0)
            for xkey in [x for x in self.slpkt.keys()
                         if gbuff.boundingBox().xMinimum() <= x and
                         x <= gbuff.boundingBox().xMaximum()]:
                for ykey in [y for y in self.slpkt[xkey].keys()
                             if gbuff.boundingBox().yMinimum() <= y and
                             y <= gbuff.boundingBox().yMaximum()]:

                    pkt_temp = QgsGeometry().fromPointXY(QgsPointXY(xkey,
                                                                    ykey))
                    if pkt_temp.buffer(0.01, 0).intersects(gbuff):
                        self.slpkt[xkey][ykey][1] += 1

        for x in self.slpkt.keys():
            for y in self.slpkt[x].keys():
                if self.slpkt[x][y][0] != self.slpkt[x][y][1]:
                    self.bl_pkt[self.pkt_c] = [x, y, 'Blad stykania']
                    self.pkt_c += 1

        print('skonczylem sprawdzac styki')

    def spr_wasy(self):
        """Metoda sprawdza czy w poligonie nie występują tzw "wąsy", które są
        błędem topologicznym"""

        for feat in self.slf.values():
            for poly in feat.geometry().asMultiPolygon():
                if not poprawna_topo(poly):
                    self.bl_poly.append([feat.geometry(), '"was"'])
                    break

    def spr_nakladanie(self):
        """Metoda sprawdza czy poligony w warstwie się na siebie nie nakładają,
        jeżeli tak zwracana jest geometria przecięcia"""
        for it in self.slf.values():
            ids = self.slfi.intersects(it.geometry().boundingBox())
            for id in ids:
                if id != it.id():
                    inter = it.geometry().intersection(self.slf[id].geometry())
                    if inter.area() > 0.01:
                        print('nalozenie: '+str(inter.area()))
                        self.bl_poly.append([inter, 'nakladanie'])

    def dodaj_warstwy(self):
        plug_dir = os.path.dirname(__file__)
        if len(list(self.bl_pkt.keys())) > 0:
            pktlyr = QgsVectorLayer(
                    "Point?crs=epsg:2180",
                    "TOPO_bledy_pkt",
                    "memory")

            pktlyr_dp = pktlyr.dataProvider()
            pktlyr.startEditing()
            pktlyr_dp.addAttributes([
                QgsField("ID", QVariant.Int),
                QgsField("TYP", QVariant.String, len=35),
                QgsField("X", QVariant.Double, 'double', 10, 4),
                QgsField("Y", QVariant.Double, 'double', 10, 4),
            ])
            pktlyr.updateFields()

            fs = []
            for i, it in enumerate(self.bl_pkt.values()):
                feat = QgsFeature()
                geom = QgsGeometry().fromPointXY(QgsPointXY(it[0], it[1]))
                feat.setGeometry(geom)
                feat.setFields(pktlyr.fields())
                feat['TYP'] = it[2]
                feat['ID'] = i
                feat['X'] = geom.boundingBox().xMinimum()
                feat['Y'] = geom.boundingBox().yMinimum()
                fs.append(feat)

            pktlyr_dp.addFeatures(fs)
            pktlyr.commitChanges()

            # pyqgis3
            pktlyr.loadNamedStyle(os.path.join(plug_dir,
                                               '..',
                                               'qml',
                                               'TOPO_pkt.qml'))
            QgsProject.instance().addMapLayer(pktlyr)

        if len(self.bl_poly) > 0:
            polyLyr = QgsVectorLayer(
                    "MultiPolygon?crs=epsg:2180",
                    "TOPO_bledy_poly",
                    "memory")

            polylyr_dp = polyLyr.dataProvider()
            polyLyr.startEditing()
            polylyr_dp.addAttributes([
                QgsField("ID", QVariant.Int),
                QgsField("TYP", QVariant.String, len=35),
            ])
            polyLyr.updateFields()

            fs = []
            for i, it in enumerate(self.bl_poly):
                feat = QgsFeature()
                geom = it[0]
                feat.setGeometry(geom)
                feat.setFields(pktlyr.fields())
                feat['TYP'] = it[1]
                feat['ID'] = i
                fs.append(feat)

            polylyr_dp.addFeatures(fs)
            polyLyr.commitChanges()

            # pyqgis3
            polyLyr.loadNamedStyle(os.path.join(plug_dir,
                                                '..',
                                                'qml',
                                                'TOPO_poly.qml'))
            QgsProject.instance().addMapLayer(polyLyr)


# if __name__ == '__console__':
    # b = SprawdzTopo(iface.activeLayer())  # nopep8
    # b.pobierz_feat()
    # b.spr_wstepne()
    # b.spr_styki()
    # b.spr_wasy()
    # b.spr_nakladanie()
    # b.dodaj_warstwy()
