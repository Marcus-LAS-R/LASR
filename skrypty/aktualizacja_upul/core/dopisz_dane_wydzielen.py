"""Dopisywanie danych do wydzieleń na podstawie starych punktów
(odpowiednik "Join attributes by location", ale zapisujący wynik od razu
do wskazanej warstwy docelowej zamiast tworzyć nową warstwę).

Dopasowanie jest przestrzenne typu punkt-w-poligonie: dla każdego obiektu
warstwy docelowej (WYDZ) szukamy punktów warstwy źródłowej
(WYDZ_PKT_stare) leżących w jego granicach. Wydzielenia, w których trafił
więcej niż jeden stary punkt (scalenie kilku starych wydzieleń w jedno
nowe) są pomijane i zgłaszane w raporcie - nie ma jednoznacznego wyboru,
którego punktu dane wpisać.
"""

from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsFeature, QgsField, QgsProject, QgsSpatialIndex, QgsVectorLayer,
)

TRYB_PUSTE = 'puste'
TRYB_NADPISZ = 'nadpisz'

_PUSTE_WARTOSCI = ('', ' ', 'NULL', None)


def _puste(wartosc):
    return wartosc in _PUSTE_WARTOSCI or (
        isinstance(wartosc, str) and wartosc.strip() == '')


def _warstwa_pkt_bledow(crs, tytul, punkty_z_opisem):
    """punkty_z_opisem: lista (QgsGeometry punktowa, opis)."""
    lyr = QgsVectorLayer(f'Point?crs={crs.authid()}', tytul, 'memory')
    lyr.dataProvider().addAttributes(
        [QgsField('OPIS', QVariant.String, '', 150)])
    lyr.updateFields()
    feats = []
    for geom, opis in punkty_z_opisem:
        f = QgsFeature(lyr.fields())
        f.setGeometry(geom)
        f['OPIS'] = opis
        feats.append(f)
    lyr.dataProvider().addFeatures(feats)
    QgsProject.instance().addMapLayer(lyr)
    return lyr


def _warstwa_poly_bledow(cel_lyr, cel_feats, fidy, tytul):
    lyr = QgsVectorLayer(
        f'MultiPolygon?crs={cel_lyr.crs().authid()}', tytul, 'memory')
    lyr.dataProvider().addAttributes(cel_lyr.fields().toList())
    lyr.updateFields()
    feats = [cel_feats[fid] for fid in fidy]
    lyr.dataProvider().addFeatures(feats)
    QgsProject.instance().addMapLayer(lyr)
    return lyr


def waliduj_geometrie(zrodlo_lyr, cel_lyr):
    """Kontrola geometryczna PRZED wykonaj() - kazdy punkt zrodlowy musi
    trafiac w dokladnie jeden poligon celu (nie 0 - poza WYDZ, nie >1 -
    nakladajace sie poligony WYDZ), a kazdy poligon celu moze miec
    najwyzej jeden trafiajacy punkt (dublet = scalenie kilku starych
    wydzielen w jedno nowe - nie da sie jednoznacznie rozstrzygnac,
    ktorego punktu dane wpisac).

    Returns:
        Dict z kluczem 'ok'. Gdy False - dodatkowo 'komunikat' (str), a
        warstwy bledow sa juz dodane do projektu.
    """
    zrodlo_feats = {f.id(): f for f in zrodlo_lyr.getFeatures()}
    cel_feats = {f.id(): f for f in cel_lyr.getFeatures()}

    si = QgsSpatialIndex()
    for f in cel_feats.values():
        si.insertFeature(f)

    trafienia = {}
    for zfid, zf in zrodlo_feats.items():
        geom = zf.geometry()
        trafienia[zfid] = [
            cfid for cfid in si.intersects(geom.boundingBox())
            if cel_feats[cfid].geometry().contains(geom)
        ]

    poza_cel = [zfid for zfid, t in trafienia.items() if len(t) == 0]
    niejednoznaczne = [zfid for zfid, t in trafienia.items() if len(t) > 1]
    jednoznaczne = {
        zfid: t[0] for zfid, t in trafienia.items() if len(t) == 1
    }

    wg_cel = {}
    for zfid, cfid in jednoznaczne.items():
        wg_cel.setdefault(cfid, []).append(zfid)
    dublety_cel = {cfid for cfid, zfidy in wg_cel.items() if len(zfidy) > 1}
    dublety_pkt = {zfid for cfid in dublety_cel for zfid in wg_cel[cfid]}

    bledy = {}
    if poza_cel:
        bledy['poza_cel'] = poza_cel
    if niejednoznaczne:
        bledy['niejednoznaczne'] = niejednoznaczne
    if dublety_cel:
        bledy['dublety_pkt'] = sorted(dublety_pkt)
        bledy['dublety_cel'] = sorted(dublety_cel)

    if not bledy:
        return {'ok': True}

    czesci = []
    crs = zrodlo_lyr.crs()

    if 'poza_cel' in bledy:
        pkty = [(zrodlo_feats[fid].geometry(), 'poza WYDZ')
                for fid in bledy['poza_cel']]
        _warstwa_pkt_bledow(
            crs, 'Przepisz ODDZ/WYDZ - punkty poza WYDZ', pkty)
        czesci.append(f"{len(bledy['poza_cel'])} punkt(ów) poza WYDZ")

    if 'niejednoznaczne' in bledy:
        pkty = [(zrodlo_feats[fid].geometry(), 'nakładające się WYDZ')
                for fid in bledy['niejednoznaczne']]
        _warstwa_pkt_bledow(
            crs, 'Przepisz ODDZ/WYDZ - punkty niejednoznaczne', pkty)
        czesci.append(
            f"{len(bledy['niejednoznaczne'])} punkt(ów) leży na więcej niż "
            "jednym WYDZ (nakładające się wydzielenia)")

    if 'dublety_cel' in bledy:
        pkty = [
            (zrodlo_feats[fid].geometry(),
             'dublet - kilka punktów na tym samym WYDZ')
            for fid in bledy['dublety_pkt']
        ]
        _warstwa_pkt_bledow(
            crs, 'Przepisz ODDZ/WYDZ - dublety (punkty)', pkty)
        _warstwa_poly_bledow(
            cel_lyr, cel_feats, bledy['dublety_cel'],
            'Przepisz ODDZ/WYDZ - dublety (poligony)')
        czesci.append(
            f"{len(bledy['dublety_cel'])} wydzielenie(a) WYDZ mają więcej "
            f"niż 1 trafiający punkt ({len(bledy['dublety_pkt'])} "
            "punkt(ów) łącznie)")

    komunikat = (
        'Znaleziono błędy do poprawy:\n- ' + '\n- '.join(czesci) +
        '\n\nSzczegóły w dodanych warstwach memory. Popraw dane i uruchom '
        'ponownie.'
    )
    return {'ok': False, 'komunikat': komunikat}


def _etykieta_obiektu(f):
    """Krótki opis wydzielenia do raportu - ODDZ/WYDZ, jeśli warstwa ma
    takie pola, w przeciwnym razie numer obiektu (fid)."""
    nazwy_pol = {pole.name() for pole in f.fields()}
    if {'ODDZ', 'WYDZ'}.issubset(nazwy_pol):
        return f"{f['ODDZ']}{f['WYDZ']}"
    return f"fid={f.id()}"


def policz_juz_wypelnione(zrodlo_lyr, cel_lyr, nazwy_pol):
    """Liczy wydzielenia `cel_lyr`, które mają jednoznacznie dopasowany
    punkt `zrodlo_lyr` ORAZ przynajmniej jedno z `nazwy_pol` już
    wypełnione - używane PRZED `wykonaj()`, żeby zapytać użytkownika, czy
    nadpisać te wartości, czy zostawić je bez zmian (TRYB_PUSTE)."""
    nazwy_pol_cel = {pole.name() for pole in cel_lyr.fields()}
    pola = [n for n in nazwy_pol if n in nazwy_pol_cel]
    if not pola:
        return 0

    si = QgsSpatialIndex()
    zrodlo_pkt = {}
    for f in zrodlo_lyr.getFeatures():
        si.insertFeature(f)
        zrodlo_pkt[f.id()] = f

    liczba = 0
    for f in cel_lyr.getFeatures():
        geom = f.geometry()
        kandydaci = si.intersects(geom.boundingBox())
        trafienia = [
            idk for idk in kandydaci
            if geom.contains(zrodlo_pkt[idk].geometry())
        ]
        if len(trafienia) != 1:
            continue
        if any(not _puste(f[nazwa]) for nazwa in pola):
            liczba += 1
    return liczba


def wykonaj(zrodlo_lyr, cel_lyr, wybor_pol):
    """Dopisuje dane z `zrodlo_lyr` (punkty) do `cel_lyr` (poligony).

    Args:
        zrodlo_lyr: Warstwa punktowa ze starymi danymi (np. WYDZ_PKT_stare).
        cel_lyr: Warstwa poligonowa, do której wpisujemy dane (np. WYDZ).
        wybor_pol: Lista (nazwa_pola, tryb) - tryb to TRYB_PUSTE (wpisuj
            tylko gdy pole docelowe jest puste) albo TRYB_NADPISZ (zawsze
            nadpisz wartością ze źródła).

    Returns:
        Słownik z podsumowaniem: zaktualizowane (int), scalenia_pominiete
        (lista etykiet), pola_pominiete (lista nazw pól spoza cel_lyr),
        zmiany_na_pole (słownik nazwa_pola -> liczba zmienionych wartości).
    """
    raport = {
        'zaktualizowane': 0,
        'scalenia_pominiete': [],
        'pola_pominiete': [],
        'zmiany_na_pole': {},
    }

    nazwy_pol_cel = {pole.name() for pole in cel_lyr.fields()}
    do_zapisu = []
    for nazwa, tryb in wybor_pol:
        if nazwa not in nazwy_pol_cel:
            raport['pola_pominiete'].append(nazwa)
            continue
        do_zapisu.append((nazwa, tryb))

    if not do_zapisu:
        return raport

    si = QgsSpatialIndex()
    zrodlo_pkt = {}
    for f in zrodlo_lyr.getFeatures():
        si.insertFeature(f)
        zrodlo_pkt[f.id()] = f

    fnm = cel_lyr.dataProvider().fieldNameMap()
    zmiany = {}
    zmiany_na_pole = {nazwa: 0 for nazwa, _ in do_zapisu}

    for f in cel_lyr.getFeatures():
        geom = f.geometry()
        kandydaci = si.intersects(geom.boundingBox())
        trafienia = [
            idk for idk in kandydaci
            if geom.contains(zrodlo_pkt[idk].geometry())
        ]

        if len(trafienia) == 0:
            continue
        if len(trafienia) > 1:
            raport['scalenia_pominiete'].append(_etykieta_obiektu(f))
            continue

        pkt = zrodlo_pkt[trafienia[0]]
        wpis = {}
        for nazwa, tryb in do_zapisu:
            if tryb == TRYB_PUSTE and not _puste(f[nazwa]):
                continue
            wpis[fnm[nazwa]] = pkt[nazwa]
            zmiany_na_pole[nazwa] += 1
        if wpis:
            zmiany[f.id()] = wpis

    if zmiany:
        cel_lyr.startEditing()
        for fid, wpis in zmiany.items():
            cel_lyr.dataProvider().changeAttributeValues({fid: wpis})
        cel_lyr.commitChanges()

    raport['zaktualizowane'] = len(zmiany)
    raport['zmiany_na_pole'] = zmiany_na_pole
    return raport
