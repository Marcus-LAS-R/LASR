# -*- coding: utf-8 -*-
import os
from qgis.core import QgsVectorLayer, QgsGeometry, QgsPointXY, QgsProject, \
    QgsFeature, QgsSpatialIndex, QgsField, Qgis
from PyQt5.QtCore import QVariant
from collections import defaultdict

from .funkcje import poprawna_topo
from .pw import PasekPostepu


class recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)


class SprawdzTopo():
    def __init__(self, iface, lyr=None):
        # iface moze byc None (uzycie headless/wsadowe) - wtedy pomijamy
        # pasek postepu i komunikaty w messageBar
        self.iface = iface
        self.lyr = lyr if lyr is not None else self.iface.activeLayer()
        self.slf = {}  # slownik feat z warstwy
        self.slfi = QgsSpatialIndex()  # SI z featurow warstwy
        self.bl_pkt = {}  # sl z bledami pktowymi id: [X, Y, typ]

        # tablica z bledami powierzchniowymi, [geometry, typ]
        self.bl_poly = []

        # lista ID obiektow z pusta/brakujaca geometria - pomijane w
        # kontrolach geometrycznych (nie da sie ich przedstawic
        # przestrzennie), ale zgłaszane zamiast wywalac cala kontrole
        self.bl_brak_geom = []

        # sl z wszystkimi pkt w warstwie [X][Y] = [2, 2]
        # pierwsza wartość, liczba wystapien podczas wczytywania z warstwy
        # druga wart. liczba granic poligonow w tym pkt
        self.slpkt = recursivedefaultdict()

        self.trig_spr_wst = False
        self.postep = None
        if self.iface is not None:
            self.postep = PasekPostepu(self.iface).stworz_pasek(
                'Sprawdzanie topologii'
            )

    def _postep(self, wartosc):
        if self.postep is not None:
            self.postep.setValue(wartosc)

    def pobierz_feat(self):
        for f in self.lyr.getFeatures():
            self.slf[f.id()] = f

        self.slfi = QgsSpatialIndex(self.lyr.getFeatures())

        self._postep(5)

    def spr_wstepne(self, prog_koincydencji=0.02):
        """prog_koincydencji - odleglosc [m] ponizej ktorej dwa wierzcholki sa
        uznawane za ten sam, wspolny punkt styku. Musi byc spojny z
        tolerancja uzywana pozniej w spr_styki, inaczej wystapia falszywe
        alarmy wynikajace z niespojnosci progow miedzy obiema fazami.
        """
        self.pkt_c = 0
        self.prog_koinc = prog_koincydencji
        for f in self.slf.values():
            geom = f.geometry()
            if geom is None or geom.isNull() or geom.isEmpty():
                self.bl_brak_geom.append(f.id())
                continue
            s = {}
            for feat in geom.asMultiPolygon():
                if len(feat) > 0:
                    for part in feat:
                        for i, pkt_raw in enumerate(part):
                            # pkt dokladny (prawie bez zaokraglenia) - do
                            # wykrywania zdublowanych wierzcholkow w obrebie
                            # jednego obiektu, tu tolerancja MUSI byc ciasna,
                            # inaczej normalne, gesto zdigitalizowane odcinki
                            # zostana falszywie uznane za duplikaty
                            pkt_dok = [round(pkt_raw[0], 4),
                                       round(pkt_raw[1], 4)]
                            # pkt zgrubny (siatka wsp. prog_koincydencji) -
                            # tylko do globalnego zliczania stykow miedzy
                            # obiektami w spr_styki
                            pkt = [
                                round(round(pkt_raw[0] / prog_koincydencji)
                                      * prog_koincydencji, 6),
                                round(round(pkt_raw[1] / prog_koincydencji)
                                      * prog_koincydencji, 6),
                            ]
                            if i < len(part) - 1:
                                blad = False

                                # sprawdzania lok. featura (tolerancja ciasna)
                                if pkt_dok[0] not in s:
                                    s[pkt_dok[0]] = pkt_dok[1]
                                else:
                                    if s[pkt_dok[0]] == pkt_dok[1]:
                                        self.bl_pkt[self.pkt_c] = [
                                            pkt_dok[0],
                                            pkt_dok[1],
                                            'Zdublowany wierzcholek']
                                        self.pkt_c += 1
                                        blad = True

                                # dodanie do globalnego slownika (siatka)
                                if pkt[0] not in self.slpkt:
                                    self.slpkt[pkt[0]][pkt[1]] = [1, 0]

                                elif pkt[1] not in self.slpkt[pkt[0]]:
                                        self.slpkt[pkt[0]][pkt[1]] = [1, 0]
                                else:
                                    if not blad:
                                        self.slpkt[pkt[0]][pkt[1]][0] += 1

        # trig do dalszych analiz
        self.trig_spr_wst = True
        self._postep(20)

    def spr_styki(self):
        """Metoda sprawdza czy stykajace sie poligony na wspolnym odc maja
        taka sam liczbę wierzchołków. Jeżeli nie generowany jest pkt z bledem.
        """
        if not self.trig_spr_wst:
            return False

        prog = getattr(self, 'prog_koinc', 0.02)
        print('zaczynam sprawdzac styki')
        for f in self.slf.values():
            geom = f.geometry()
            if geom is None or geom.isNull() or geom.isEmpty():
                continue
            gbuff = geom.buffer(prog, 0)
            for xkey in [x for x in self.slpkt.keys()
                         if gbuff.boundingBox().xMinimum() <= x and
                         x <= gbuff.boundingBox().xMaximum()]:
                for ykey in [y for y in self.slpkt[xkey].keys()
                             if gbuff.boundingBox().yMinimum() <= y and
                             y <= gbuff.boundingBox().yMaximum()]:

                    pkt_temp = QgsGeometry().fromPointXY(QgsPointXY(xkey,
                                                                    ykey))
                    if pkt_temp.buffer(prog, 0).intersects(gbuff):
                        self.slpkt[xkey][ykey][1] += 1

        for x in self.slpkt.keys():
            for y in self.slpkt[x].keys():
                if self.slpkt[x][y][0] != self.slpkt[x][y][1]:
                    self.bl_pkt[self.pkt_c] = [x, y, 'Blad stykania']
                    self.pkt_c += 1

        self._postep(40)

    def spr_wasy(self, prog_szer=0.15):
        """Metoda sprawdza czy w poligonie nie występują tzw "wąsy", które są
        błędem topologicznym"""

        for feat in self.slf.values():
            geom = feat.geometry()
            if geom is None or geom.isNull() or geom.isEmpty():
                continue
            for poly in geom.asMultiPolygon():
                if not poprawna_topo(poly, prog_szer=prog_szer):
                    self.bl_poly.append([geom, '"was"'])
                    break

        self._postep(55)

    def spr_luki(self, prog_szer=0.15, prog_pow_szum=0.05):
        """Metoda sprawdza czy miedzy sasiadujacymi poligonami w warstwie nie
        wystepuja waskie luki (obszary ktore powinny sie stykac, a nie
        stykaja). Wykorzystuje sztuczke domykania buforem: jezeli po
        wybuforowaniu unii na zewnatrz i z powrotem do wewnatrz pojawia sie
        dodatkowa powierzchnia wieksza od unii oryginalnej, to jest to luka
        waska (<= 2*delta), ktora domkniecie buforem "zaklejilo".
        Uzywa stylu miter zamiast round przy laczeniu naroznikow, zeby nie
        generowac tysiecy mikroartefaktow zaokraglen na kazdym wierzcholku.

        prog_szer - maksymalna szerokosc luki jaka ma zostac wykryta [m]
        prog_pow_szum - fragmenty ponizej tej powierzchni [m2] sa pomijane
            jako numeryczny szum buforowania, nie realne luki
        """
        geoms = [f.geometry() for f in self.slf.values()
                 if f.geometry() and not f.geometry().isEmpty()]
        if len(geoms) == 0:
            self._postep(65)
            return

        unia = QgsGeometry.unaryUnion(geoms)
        delta = prog_szer / 2
        domknieta = unia.buffer(
            delta, 8, QgsGeometry.CapRound, QgsGeometry.JoinStyleMiter, 2.0
        ).buffer(
            -delta, 8, QgsGeometry.CapRound, QgsGeometry.JoinStyleMiter, 2.0
        )
        luki = domknieta.difference(unia)

        try:
            czesci = luki.asGeometryCollection()
        except Exception:
            czesci = [luki] if not luki.isEmpty() else []

        for czesc in czesci:
            if czesc.area() > prog_pow_szum:
                self.bl_poly.append([czesc, 'luka'])

        self._postep(65)

    def spr_nakladanie(self):
        """Metoda sprawdza czy poligony w warstwie się na siebie nie nakładają,
        jeżeli tak zwracana jest geometria przecięcia"""
        for it in self.slf.values():
            geom = it.geometry()
            if geom is None or geom.isNull() or geom.isEmpty():
                continue
            ids = self.slfi.intersects(geom.boundingBox())
            for id in ids:
                if id != it.id():
                    inter = it.geometry().intersection(self.slf[id].geometry())
                    if inter.area() > 0.01:
                        print('nalozenie: '+str(inter.area()))
                        self.bl_poly.append([inter, 'nakladanie'])

        self._postep(95)

    def dodaj_warstwy(self):
        plug_dir = os.path.dirname(__file__)
        str_problemy = []

        if len(list(self.bl_pkt.keys())) > 0:
            str_problemy.append('punktowe')
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
            str_problemy.append('poligonowe')
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
                feat.setFields(polyLyr.fields())
                feat['TYP'] = it[1]
                feat['ID'] = i
                fs.append(feat)

            polylyr_dp.addFeatures(fs)
            polyLyr.commitChanges()

            polyLyr.loadNamedStyle(os.path.join(plug_dir,
                                                '..',
                                                'qml',
                                                'TOPO_poly.qml'))
            QgsProject.instance().addMapLayer(polyLyr)

        self._postep(100)

        dodatek = 'Sprawdzono topologię! '
        if len(str_problemy) > 0:
            dodatek += ' Znaleziono problemy '
            dodatek += ' i '.join(str_problemy) + '.'

        if self.iface is not None:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage('OK', dodatek, Qgis.Success, 10)
        else:
            print(dodatek)
