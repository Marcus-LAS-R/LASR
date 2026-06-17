# -*- coding: utf-8 -*-
import os
import numpy as np
from qgis.core import (
    QgsVectorLayer, QgsGeometry, QgsProject, Qgis, QgsField,
    QgsFeatureRenderer, QgsReadWriteContext, QgsRenderContext,
    QgsSymbolLayerUtils,
)
from qgis.PyQt.QtXml import QDomDocument
from PyQt5.QtCore import QVariant, QSize, QFile, QIODevice


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


def usun_wasy(geom):  # noqa
    """ Funkcja sprawdza czy w przekazanej geom mulitpoligonu
    znajdują się jakieś wąsy i ewentualne powtórzone pkt.
    Jeżeli tak, zostają pominięte w zwracanej nowej geom.
    """
    pg = []  # tablica z poprawnym multi

    for k, poly in enumerate(geom.asMultiPolygon()):
        pg.append([])
        for j, part in enumerate(poly):
            pp = []
            o1 = False  # ostatni pkt
            o2 = False  # pkt przedprzedostatni
            was = 0
            for i, pkt in enumerate(part):
                # jezeli was < 0 to znaczy ze mamy zerowy was w z
                # wierzcholkami w różnych pktach, zostawiamy pierwszy i ostatni
                # z analizowanych pkt czyli pomijamy śrokowy - właśnie ten
                if was < 0:
                    was = 0
                    continue

                if i < len(part) - 2:
                    o1 = part[i+1]
                    o2 = part[i+2]
                elif i == len(part) - 2:
                    o1 = part[i+1]
                    o2 = part[0]
                else:
                    pass

                was = czy_was(pkt, o1, o2)
                if was > 0 and i < len(part) - 2:
                    was -= 1
                    continue

                # pomiń zdublowane wierzchołki
                if len(pp) == 0:
                    pp.append(pkt)
                elif round(pkt.x(), 7) != round(pp[-1].x(), 7) and \
                        round(pkt.y(), 7) != round(pp[-1].y(), 7):
                    pp.append(pkt)

            # jezeli całość poligonu jest większa od 3 dodaj
            if len(pp) > 3:
                # dodaj poprawne pkt do tabeli
                # sprawdz czy pierwszy i ostatni pkt jest w tym samym miejscu
                if pp[0] != pp[-1]:
                    pp.append(pp[0])
                pg[k].append(pp)

    return QgsGeometry().fromMultiPolygonXY(pg)


def czy_was(p1, p2, p3):
    if round(p1.x(), 7) == round(p3.x(), 7) and \
            round(p1.y(), 7) == round(p3.y(), 7):
        return 2

    azym2 = 180 + oblicz_azymut(p2, p3)
    if azym2 >= 360:
        azym2 -= 360
    if abs(oblicz_azymut(p1, p2)-azym2) < 1:
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
        gtemp = fe.geometry().asWkt(3)
        new_geom = QgsGeometry().fromWkt(gtemp)
        zabezp = 0
        while new_geom.removeDuplicateNodes(0.0001) and zabezp < 10:
            zabezp += 1

        fe.clearGeometry()
        fe.setGeometry(new_geom)
        feats.append(fe)

    virt.dataProvider().addFeatures(feats)
    virt.commitChanges()

    QgsProject.instance().addMapLayer(virt)


def isNone(a):
    if a in [None, 'NULL', '', ]:
        return ''
    elif isinstance(a, QVariant):
        if a.isNull():
            return ''
        else:
            return str(a)
    else:
        return a


def ustaw_utf8(iface):
    # metoda ustawia kodowanie utf aktywnej warstwy
    try:
        iface.activeLayer().dataProvider().setEncoding('UTF-8')
        iface.messageBar().pushMessage(
            'OK', 'Ustawiono kodowanie UTF-8', Qgis.Success)
    except:  # nopep8
        iface.messageBar().pushMessage(
            'BŁĄD', 'Nie udało się ustawić kodowaniu UTF-8 dla warstwy',
            Qgis.Critical)


def oblicz_pow_graf(iface):
    """ Funkcja sprawdza czy w aktywnej warstwie są pola trzymające pow graf
    takie jak PARCEL_POW, LAND_POW, jeżeli tak oblicza w nich pow graf.
    Jeżeli nie ma powyższych pól, dodaje nowe POW_GRAF i w nim oblicza pow.
    Powierzchnia obliczana jest na podstawie układu wspł z ramki.
    """

    if iface.activeLayer().wkbType() not in [3, 6]:
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Warstwa musi mieć geometrię powierzchniową!',
            Qgis.Critical
        )
        return False

    try:
        if not iface.activeLayer().isValid():
            iface.messageBar().pushMessage(
                'BŁĄD',
                'Warstwa niepoprawna!',
                Qgis.Critical
            )
            return False

    except Exception:
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Warstwa niepoprawna!',
            Qgis.Critical
        )
        return False

    # ustal pole w którym będziemy oblczać pow graf
    fnm = iface.activeLayer().dataProvider().fieldNameMap()
    ind = -1
    nazwa_pola = 'POW_GRAF'
    if 'LAND_POW' in fnm:
        ind = fnm['LAND_POW']
        nazwa_pola = 'LAND_POW'
    elif 'PARCEL_POW' in fnm:
        ind = fnm['PARCEL_POW']
        nazwa_pola = 'PARCEL_POW'
    elif 'POW_GRAF' in [k.upper() for k in fnm.keys()]:
        ind = [v for k, v in fnm.items() if k.upper() == 'POW_GRAF'][0]
    else:
        pole = QgsField("POW_GRAF", QVariant.Double, "double", 10, 4)

        iface.activeLayer().startEditing()
        iface.activeLayer().dataProvider().addAttributes([pole])
        iface.activeLayer().updateFields()
        iface.activeLayer().commitChanges()

        fnm = iface.activeLayer().dataProvider().fieldNameMap()
        ind = fnm['POW_GRAF']

    bledy = 0
    tabb = []   # tab z featurami z bledna geometria
    print('obliczam pow')
    for feat in iface.activeLayer().getFeatures():
        iface.activeLayer().dataProvider().changeAttributeValues({
            feat.id(): {ind: feat.geometry().area()/10000}
        })
        if not feat.geometry().isGeosValid():
            tabb.append(feat)
            bledy += 1

    if bledy == 0:
        wyps_gl = 'OK'
        wyps = \
            'Powierzchnia graficzna obliczona i zapisana w polu [' + \
            nazwa_pola + ']'
        typ = Qgis.Success
    else:
        wyps_gl = 'BŁĘDY'
        wyps = \
            'Powierzchnia graficzna obliczona i zapisana w polu [' + \
            nazwa_pola + \
            '] -->  Znaleziono poligony z błędną geometrią (GEOS): ' + \
            str(bledy)
        typ = Qgis.Warning

    if len(tabb) > 0:
        bledy = QgsVectorLayer("MultiPolygon?crs=epsg:2180&index=yes",
                               "Poligony_z_błędną_geom",
                               "memory"
                               )

        bledy.startEditing()
        bledy.dataProvider().addAttributes(
            iface.activeLayer().dataProvider().fields().toList())
        bledy.updateFields()
        bledy.addFeatures(tabb)
        bledy.commitChanges()
        QgsProject.instance().addMapLayer(bledy)

    iface.messageBar().pushMessage(wyps_gl, wyps, typ)


def dodaj_adm(iface):
    # metoda dodaje do zaznaczonej warstwy wektorowej, kolumny MUNICIP,
    # COMMUNITY o ile ich już nie ma w terj warstwie
    lyr = iface.activeLayer()
    try:
        if lyr.wkbType() in [1, 2, 3, 4, 5, 6]:
            pass
    except:  # nopep8
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Wspierane są tylko warstwy wektorowe',
            Qgis.Warning
        )

    pola = [
        QgsField("MUNICIP", QVariant.String, len=3),
        QgsField("COMMUNITY", QVariant.String, len=4),
    ]
    attr = [y for y in pola if y.name() not in
            [x.name() for x in lyr.fields()]]
    if len(attr) > 0:
        lyr.startEditing()
        lyr.dataProvider().addAttributes(attr)
        lyr.updateFields()
        lyr.commitChanges()

        iface.messageBar().pushMessage(
            'OK',
            'Warstwa uzupełniono o brakujące pola [' +
            ', '.join([x.name() for x in attr]),
            Qgis.Success
        )
    else:
        iface.messageBar().pushMessage(
            'OK',
            'W warstwie były już niezbędne pola, nic nie zmieniałem...',
            Qgis.Success
        )


def otworz_kompozycje(iface):
    project = QgsProject.instance()
    projectLayoutManager = project.layoutManager()
    lays = projectLayoutManager.layouts()
    if len(lays) == 1:
        iface.openLayoutDesigner(lays[0])
    else:
        iface.showLayoutManager()


def podglad_ikony_qml(sciezka):
    """Generuje QIcon z pierwszego symbolu renderera zapisanego w pliku .qml
    (działa dla singleSymbol/categorized/graduated/RuleRenderer).
    Zwraca None jeśli nie da się odczytać/wyrenderować.
    """
    try:
        qfile = QFile(sciezka)
        if not qfile.open(QIODevice.ReadOnly):
            return None
        doc = QDomDocument()
        ok = doc.setContent(qfile)
        qfile.close()
        if not ok:
            return None

        wezly = doc.elementsByTagName('renderer-v2')
        if wezly.length() == 0:
            return None

        renderer = QgsFeatureRenderer.load(
            wezly.at(0).toElement(), QgsReadWriteContext()
        )
        if renderer is None:
            return None

        symbole = renderer.symbols(QgsRenderContext())
        if not symbole:
            return None

        return QgsSymbolLayerUtils.symbolPreviewIcon(symbole[0], QSize(24, 24))
    except Exception:
        return None


def wczytaj_styl(iface, sciezka):
    """Wczytuje plik .qml jako styl aktywnej warstwy."""
    lyr = iface.activeLayer()
    if lyr is None:
        iface.messageBar().pushMessage(
            'Brak warstwy', 'Zaznacz warstwę przed wczytaniem stylu',
            Qgis.Critical, 10
        )
        return
    try:
        lyr.loadNamedStyle(sciezka)
        lyr.triggerRepaint()
        iface.mapCanvas().refresh()
    except Exception as e:
        iface.messageBar().pushMessage(
            'Wczytanie stylu',
            f'Nie udało się wczytać stylu {os.path.basename(sciezka)}: {e}',
            Qgis.Critical, 10
        )
