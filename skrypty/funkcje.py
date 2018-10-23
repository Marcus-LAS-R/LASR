import numpy as np


def sprawdz_topo(poly):
    """ funkcja sprawdza poprawnosc topologiczną poligonu:
        - nakładające się wierzchołki w poligonie
        - 'wąsy'
    """

    sl = {}  # slownik z punktami w poligonie do sprawdzenia powtorzen
    powt = []  # tablica z powtarzajacymi sie pkt w obrebie poligonu
    for part in poly:
        for i, pkt in enumerate(part):
            # sprawdzanie nakladajacych sie pkt w multipoligonach
            if i < len(part):
                if pkt[0] not in sl:
                    sl[pkt[0]] = []
                    sl[pkt[0]].append(pkt[1])
                else:
                    # jezeli pkt ma wsp x taka sama ale innego y dodaj do sl
                    if pkt[1] not in sl[pkt[0]]:
                        sl[pkt[0]].append(pkt[1])
                    # jezeli pkt jest juz w slowniku - blad topo
                    else:
                        powt.append(pkt)

            # sprawdzanie występowania wąsów w poligonach
            tazym = []   # tablica azymotow
            todl = []  # tablica odleglosci

            if i == 0:
                tsp = [part[-3], part[-2], part[-1], pkt]

            # oblicz zestawienia dla 4 ostatnich pkt
            for x in range(1, 4):
                tazym.append(oblicz_azymut(tsp[x-1], tsp[x]))
                todl.append(oblicz_odl(tsp[x-1], tsp[x]))

            # czy pierwsza para ma maly azymut
            pass





def oblicz_odl(A, B):
    """funkcja oblicza odległość pomiędzy 2 pkt na płaszczyźnie"""
    return np.sqrt((B.y-A.y) * (B.y-A.y) + (B.x-A.x) * (B.x-A.x))


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
