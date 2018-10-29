# -*- coding: utf-8 -*-
import numpy as np


def poprawna_topo(poly):
    """ funkcja sprawdza poprawnosc topologiczną poligonu:
        - nakładające się wierzchołki w poligonie
        - 'wąsy'
    """

    for part in poly:
        if len(part) > 5:
            for i, pkt in enumerate(part):
                # sprawdzanie występowania wąsów w poligonach
                tazym = []   # tablica azymotow
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
                #  doc miedzy nimi jest mniejszy od kilku metrow
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
