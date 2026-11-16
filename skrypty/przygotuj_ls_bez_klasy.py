"""Ls bez klasy - krok dodatkowy "Przygotuj Lsy".

Ls bez klasy (LANDID PID.Ls, puste SQ w bazie) nie wystepuje w KLU, tylko w
warstwie UZYTKI (kontury uzytkow bez klas). Po wygenerowaniu warstwy
LS_<czas> z KLU: Ls z UZYTKI przeciete z dzialka, minus Ls juz przyjete do
LS_<czas> na tej dzialce, oczyszczone z wasow (otwarcie buforem -/+0,5 m) i
szumu (< 21 m2), dopisane do LS_<czas> jako jeden obiekt na dzialke.
"""

import os

from qgis.core import Qgis, QgsCoordinateTransform, QgsFeature, \
    QgsFeatureRequest, QgsGeometry, QgsMessageLog, QgsProject, \
    QgsSpatialIndex, QgsVectorLayer, QgsWkbTypes

from .funkcje import isNone, usun_wasy

# polowa szerokosci usuwanego wasa/paska [m] - pasy wezsze niz ok. 1 m znikaja
BUFOR_WASY = 0.5
# ponizej tej powierzchni [m2] kawalek Ls bez klasy jest szumem
PROG_SZUM = 21
# pola z kodem uzytku w UZYTKI (nowy standard AU, stare G5OFU/OFU)
POLA_AU = ['AU', 'G5OFU', 'OFU']

UW_BEZ_KLASY = 'Ls bez klasy z UZYTKI; '
POWOD_BRAK_UZYTKI = 'Brak Ls w warstwie UZYTKI na działce'
POWOD_NIC_NIE_ZOSTALO = ('Po odjęciu Ls z klasą i oczyszczeniu nic nie '
                         'zostało')
POWOD_BRAK_DZKAT = 'Brak działki w warstwie DZKAT'


def ls_bez_klasy_do_przygotowania(p, wl, landidy_w_ls):
    """{PARCELID: LANDID} - Ls bez klasy z bazy, ktorych nie ma jeszcze w
    LS_<czas>. Przy wl == 'OF' pomija dzialki OP (jak raport)."""
    wynik = {}
    for landid in p.ls:
        au, sq, _pow, pid = p.uzytki[landid][:4]
        if sq or landid in landidy_w_ls:
            continue
        if wl == 'OF' and pid[4:] in p.dz_op:
            continue
        wynik[pid] = landid
    return wynik


def znajdz_warstwe_uzytki(kat_klu):
    """Warstwa UZYTKI z projektu (najpierw nazwa dokladnie UZYTKI, potem
    zaczynajaca sie od UZYTKI), a gdy jej nie ma - plik UZYTKI.shp obok KLU.
    Zwraca (warstwa, pole_au) albo (None, None)."""
    warstwy = list(QgsProject.instance().mapLayers().values())
    kandydaci = (
        [x for x in warstwy if x.name().upper() == 'UZYTKI'] +
        [x for x in warstwy if x.name().upper().startswith('UZYTKI')])
    if kat_klu:
        plik = os.path.join(kat_klu, 'UZYTKI.shp')
        if os.path.isfile(plik):
            kandydaci.append(QgsVectorLayer(plik, 'UZYTKI', 'ogr'))

    for lyr in kandydaci:
        if not isinstance(lyr, QgsVectorLayer) or not lyr.isValid():
            continue
        if lyr.geometryType() != QgsWkbTypes.PolygonGeometry:
            continue
        nazwy = {x.upper(): x for x in lyr.fields().names()}
        pole = next((nazwy[x] for x in POLA_AU if x in nazwy), None)
        if pole:
            return lyr, pole
    return None, None


def _tylko_poligony(g):
    """Czesci poligonowe geometrii (przeciecie bywa kolekcja z liniami)."""
    if g is None or g.isEmpty():
        return []
    if g.type() != QgsWkbTypes.PolygonGeometry and not g.isMultipart():
        return []
    czesci = []
    for c in g.asGeometryCollection():
        if c.type() == QgsWkbTypes.PolygonGeometry and not c.isEmpty():
            czesci.append(c)
    return czesci


def _bufor(g, d):
    """Bufor z ostrymi narożnikami (mitre), zeby otwarcie nie scinalo
    rogow Ls."""
    try:
        return g.buffer(d, 8, Qgis.EndCapStyle.Flat, Qgis.JoinStyle.Miter, 2)
    except AttributeError:  # QGIS < 3.30
        return g.buffer(d, 8, QgsGeometry.CapFlat,
                        QgsGeometry.JoinStyleMiter, 2)


def oczysc(g):
    """Usuwa wasy/paski wezsze niz 2*BUFOR_WASY (otwarcie morfologiczne,
    wynik nie wychodzi poza geometrie wejsciowa) i kawalki < PROG_SZUM m2.
    Zwraca multipoligon albo None."""
    otwarte = _bufor(_bufor(g, -BUFOR_WASY), BUFOR_WASY)
    if otwarte is None or otwarte.isEmpty():
        return None
    otwarte = otwarte.intersection(g)
    czesci = [c for c in _tylko_poligony(otwarte) if c.area() >= PROG_SZUM]
    if not czesci:
        return None
    wynik = QgsGeometry.unaryUnion(czesci)
    wynik.convertToMultiType()
    wynik = usun_wasy(wynik)
    if wynik is None or wynik.isEmpty():
        return None
    return wynik


def _geometrie_uzytki_ls(lyr, pole_au, crs_docelowy):
    """{id: geometria} obiektow Ls z UZYTKI w ukladzie DZKAT + indeks."""
    geom = {}
    idx = QgsSpatialIndex()
    tr = None
    if lyr.crs() != crs_docelowy:
        tr = QgsCoordinateTransform(lyr.crs(), crs_docelowy,
                                    QgsProject.instance())
    for f in lyr.getFeatures():
        if isNone(f[pole_au]).lower() != 'ls' or not f.hasGeometry():
            continue
        g = QgsGeometry(f.geometry())
        if tr:
            g.transform(tr)
        g = g.makeValid()
        if g.isEmpty():
            continue
        geom[f.id()] = g
        nf = QgsFeature(f.id())
        nf.setGeometry(g)
        idx.addFeature(nf)
    return geom, idx


def przygotuj(cele, dzkat, lyrls, uzytki, pole_au, p):
    """Dla cele {PARCELID: LANDID} buduje obiekty Ls bez klasy i dopisuje je
    do lyrls. Zwraca slownik:
        dodane:   [QgsFeature, ...] (dopisane do lyrls)
        nieudane: [[LANDID, powod, pow_rej], ...]"""
    wynik = {'dodane': [], 'nieudane': []}

    geom_uz, idx_uz = _geometrie_uzytki_ls(uzytki, pole_au, dzkat.crs())

    # dzialki docelowe
    dzialki = {}
    for f in dzkat.getFeatures():
        pid = f['PARCELID']
        if pid in cele:
            dzialki[pid] = f

    # Ls juz przyjete do LS_<czas>, pogrupowane po dzialce
    ls_na_dz = {}
    req = QgsFeatureRequest().setSubsetOfAttributes(
        ['PARCELID'], lyrls.fields())
    for f in lyrls.getFeatures(req):
        pid = f['PARCELID']
        if pid in cele and f.hasGeometry():
            ls_na_dz.setdefault(pid, []).append(f.geometry())

    nowe = []
    for pid, landid in cele.items():
        pow_rej = p.uzytki[landid][2]
        dz = dzialki.get(pid)
        if dz is None or not dz.hasGeometry():
            wynik['nieudane'].append([landid, POWOD_BRAK_DZKAT, pow_rej])
            continue
        g_dz = dz.geometry().makeValid()

        kawalki = []
        for fid in idx_uz.intersects(g_dz.boundingBox()):
            g = geom_uz[fid]
            if g.intersects(g_dz):
                kawalki += _tylko_poligony(g.intersection(g_dz))
        if not kawalki:
            wynik['nieudane'].append([landid, POWOD_BRAK_UZYTKI, pow_rej])
            continue
        g = QgsGeometry.unaryUnion(kawalki)

        if pid in ls_na_dz:
            ls_klasa = QgsGeometry.unaryUnion(ls_na_dz[pid]).makeValid()
            g = g.difference(ls_klasa)

        g = oczysc(g) if g is not None and not g.isEmpty() else None
        if g is None:
            wynik['nieudane'].append([landid, POWOD_NIC_NIE_ZOSTALO, pow_rej])
            continue

        nowe.append(_nowy_ls(lyrls, dz, landid, g, pow_rej))

    if nowe:
        przed = lyrls.dataProvider().featureCount()
        lyrls.dataProvider().addFeatures(nowe)
        dodano = lyrls.dataProvider().featureCount() - przed
        if dodano < len(nowe):
            QgsMessageLog.logMessage(
                'Ls bez klasy: nie dopisano do warstwy ' +
                str(len(nowe) - dodano) + ' obiektów\n' +
                '\n'.join(lyrls.dataProvider().errors()),
                'Las-R', Qgis.Critical)
        lyrls.updateExtents()
        lyrls.triggerRepaint()
        wynik['dodane'] = nowe

    QgsMessageLog.logMessage(
        f'Ls bez klasy z UZYTKI: dopisano {len(wynik["dodane"])}, '
        f'nie przygotowano {len(wynik["nieudane"])}', 'Las-R', Qgis.Info)
    return wynik


def _nowy_ls(lyrls, dz, landid, g, pow_rej):
    """Obiekt warstwy LS_<czas> - atrybuty jak w dopisz_uwagi_pow."""
    f = QgsFeature(lyrls.fields())
    f.setGeometry(g)
    pow_graf = round(g.area() / 10000, 4)
    uw = UW_BEZ_KLASY
    if max(pow_graf, pow_rej or 0) >= 0.2 and \
            abs(pow_graf - (pow_rej or 0)) > 0.15:
        uw += 'Duża rozbieżność pow. rej/graf; '

    atr = {
        'COUNTY': landid[:2], 'DISTRICT': landid[2:4],
        'MUNICIP': landid[4:7], 'COMMUNITY': landid[7:11],
        'AU': 'Ls', 'SPRAWDZ': uw, 'LANDID': landid,
        'LAND_AR': pow_rej, 'LAND_POW': pow_graf,
    }
    for x in ['PARCELNR', 'PARCELID', 'GRP', 'ARK', 'NIELES', 'UWAGI',
              'PARCEL_AR', 'PARCEL_POW']:
        atr[x] = dz[x]
    for nazwa, wart in atr.items():
        i = f.fieldNameIndex(nazwa)
        if i >= 0:
            f.setAttribute(i, wart)
    return f
