# -*- coding: utf-8 -*-
import numpy as np
from qgis.core import QgsVectorLayer, QgsGeometry, QgsProject


def poprawna_topo(poly):
    """ funkcja sprawdza poprawnosc topologiczną poligonu:
        - nakładające się wierzchołki w poligonie
        - 'wąsy'
    """

    for part in poly:
        if len(part) > 4:
            for i, pkt in enumerate(part):
                # sprawdzanie występowania wąsów w poligonach
                tazym = []   # tablica azymutow
                todl = []  # tablica odleglosci

                if i == 0:
                    tsp = [part[-4], part[-3], part[-2], pkt]
                else:
                    tsp = tsp[1:] + [pkt]

                # oblicz zestawienia dla 4 ostatnich pkt
                for x in range(1, 4):
                    tazym.append(oblicz_azymut(tsp[x-1], tsp[x]))
                    todl.append(oblicz_odl(tsp[x-1], tsp[x]))

                # czy pary maja maly azymut
                for ai in range(1, 3):
                    pierwszy = tazym[ai-1]
                    drugi = 180 + tazym[ai]
                    if drugi >= 360:
                        drugi -= 360
                        if abs(pierwszy-drugi) < 2:
                            return False

                # czy pierwszy i ostatni odcinek maja przeciwny azymut a
                #  odc miedzy nimi jest mniejszy od kilku metrow
                trzeci = 180 + tazym[-1]
                if trzeci >= 360:
                    trzeci -= 360

                if abs(tazym[0]-trzeci) < 2 and todl[1] < 1:
                    return False

    return True


def oblicz_odl(A, B):
    """funkcja oblicza odległość pomiędzy 2 pkt na płaszczyźnie"""
    return np.sqrt((B.y()-A.y()) * (B.y()-A.y()) +
                   (B.x()-A.x()) * (B.x()-A.x()))


def oblicz_azymut(A, B):
    """funkcja oblicza azymut pomiędzy podanymi punktami (QgsPointXY)
        kolejność punków oczywiście mna znaczenie.
        Zwracana wartość jest z zakresu od 0-360
    """

    kat = np.rad2deg(np.arctan2(B.y() - A.y(), B.x() - A.x()))
    # kat = np.rad2deg(np.arctan2(B[-1] - A[-1], B[0] - A[0]))
    if kat == 90:
        return 0
    elif kat == 0:
        return 90
    elif kat == -90:
        return 180
    elif abs(kat) == 180:
        return 270
    elif 90 > kat > 0:  # I cwiartka
        return 90 - kat
    elif 180 > kat > 90:  # IV cwiartka
        return 360 - (kat-90)
    elif -180 < kat < 0:  # II i III cwiartka
        return 90 + abs(kat)


def usun_wasy(geom):
    """ Funkcja sprawdza czy w przekazanej geom mulitpoligonu
    znajdują się jakieś wąsy i ewentualne powtórzone pkt.
    Jeżeli tak, zostają pominięte w zwracanej nowej geom.
    """
    pg = []  # tablica z poprawnym multi

    o1 = False  # ostatni pkt
    o2 = False  # pkt przedprzedostatni
    was = 0
    for k, poly in enumerate(geom.asMultiPolygon()):
        pg.append([])
        for j, part in enumerate(poly):
            pp = []

            # jezeli was < 0 to znaczy ze mamy zerowy was w z wierzcholkami w
            # różnych pktach, zostawiamy pierwszy i ostatni z analizowanych pkt
            # czyli pomijamy śrokowy - właśnie ten
            if was < 0:
                was = 0
                continue

            for i, pkt in enumerate(part):

                if i < len(part) - 2:
                    o1 = part[i+1]
                    o2 = part[i+2]
                elif i == len(part) - 2:
                    o1 = part[i+1]
                    o2 = part[0]
                else:
                    pass

                was = czy_was(pkt, o1, o2)
                if was > 0:
                    was -= 1
                    continue

                # pomiń zdublowane wierzchołki
                if i == 0:
                    pp.append(pkt)
                elif round(pkt.x(), 5) != round(pp[-1].x(), 5) and \
                        round(pkt.y(), 5) != round(pp[-1].y(), 5):
                    pp.append(pkt)

            # dodaj poprawne pkt do tabeli
            pg[k].append(pp)

    return QgsGeometry().fromMultiPolygonXY(pg)


def czy_was(p1, p2, p3):
    if round(p1.x(), 5) == round(p3.x(), 5) and \
            round(p1.y(), 5) == round(p3.y(), 5):
        return 2

    azym2 = 180 + oblicz_azymut(p2, p3)
    if azym2 >= 360:
        azym2 -= 360

    if abs(oblicz_azymut(p1, p2)-azym2) < 2:
        return -1

    return 0


def rozbij_multipoly(feat):
    """ Funkcja sprawdza czy w podanym feat, znajduja się
    prymitywy sytkające się jednym pkt, jeżeli tak, rozbija
    je na pojedyncze featurki i zwraca jako tablica"""


def zaokraglij_wsp(warstwa):
    virt = QgsVectorLayer(
        "Polygon?crs=epsg:2180&index=yes", 'zaokr', "memory"
    )

    virt.startEditing()
    virt.dataProvider().addAttributes(
        warstwa.dataProvider().fields().toList()
    )
    virt.updateFields()

    feats = []
    for fe in warstwa.getFeatures():
        gtemp = fe.geometry().asWkt(4)
        new_geom = QgsGeometry().fromWkt(gtemp)
        fe.clearGeometry()
        fe.setGeometry(new_geom)
        feats.append(fe)

    virt.dataProvider().addFeatures(feats)
    virt.commitChanges()

    QgsProject.instance().addMapLayer(virt)
