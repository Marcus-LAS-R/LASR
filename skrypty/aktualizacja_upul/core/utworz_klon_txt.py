"""Tworzy raporty KLON.txt i NOTATKI_zmiany.txt na podstawie warstwy
odcinków "Klon", warstwy punktowej notatek (opis_notatki) i warstwy
wydzieleń WYDZ - format zgodny z Klonuj.dane_konf() z baza_klonuj_wydz.py
(wartość TAB wartość, jedna para na linię).

KLON.txt (patrz `wykonaj`): każdy odcinek warstwy Klon - początek =
wydzielenie źródłowe (skąd kopiujemy opis), koniec = wydzielenie
docelowe. Tylko pierwszy i ostatni wierzchołek odcinka mają znaczenie -
ewentualne pośrednie wierzchołki są ignorowane.

Przed zapisem KLON.txt trzy kontrole:

1. Oba końce KAŻDEGO odcinka muszą leżeć na jakimś wydzieleniu WYDZ -
   inaczej nie da się rozstrzygnąć adresu. Punkty poza wydzieleniami
   trafiają do warstwy memory + komunikat, generowanie przerywane.
2. Źródło i cel odcinka nie mogą leżeć w tym samym poligonie (klonowanie
   wydzielenia do samego siebie nie ma sensu). Odcinki z tym błędem
   trafiają do warstwy memory + komunikat, generowanie przerywane.
3. Dopasowanie 1:1 i 1:wiele (jedno źródło klonuje do wielu celów) jest
   dopuszczalne - to typowy przypadek podziału wydzielenia. Wiele:1
   (kilka różnych źródeł klonuje do tego samego celu) jest błędem - nie
   da się jednoznacznie rozstrzygnąć, który opis ma trafić do
   wydzielenia docelowego (klonowanie w bazie i tak odrzuciłoby wszystkie
   pary oprócz pierwszej). Trafia do warstwy memory + komunikat,
   generowanie przerywane.

NOTATKI_zmiany.txt (patrz `wykonaj_notatki`): każdy punkt warstwy notatek
musi leżeć na jakimś wydzieleniu WYDZ - punkty poza wydzieleniami trafiają
do warstwy memory + komunikat, generowanie przerywane. W odróżnieniu od
KLON.txt NIE ma kontroli 1:1/dubletów - kilka notatek na tym samym
wydzieleniu jest normalne i dopuszczalne.
"""

import os

from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsFeature, QgsField, QgsGeometry, QgsProject, QgsSpatialIndex,
    QgsVectorLayer,
)

_QML_DIR = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'qml')


def _znajdz_poligon(si, poligony, punkt_geom):
    """Zwraca fid poligonu WYDZ zawierającego punkt, albo None."""
    for fid in si.intersects(punkt_geom.boundingBox()):
        if poligony[fid].geometry().contains(punkt_geom):
            return fid
    return None


def _konce_odcinka(geom):
    """Zwraca (start, koniec) jako QgsPointXY - tylko pierwszy/ostatni
    wierzchołek, wierzchołki pośrednie są ignorowane. Dla geometrii
    wieloczęściowej (rzadkie w shapefile typu Arc) bierze pierwszą część."""
    linia = geom.asMultiPolyline()[0] if geom.isMultipart() else geom.asPolyline()
    return linia[0], linia[-1]


def _warstwa_bledow_punktowych(crs, tytul, punkty):
    """punkty: lista (QgsPointXY, opis). Styl - point_drop_shadow_red.qml,
    tak jak warstwy błędów w shp_sprawdz_polozenie_opisow.py."""
    lyr = QgsVectorLayer(f'Point?crs={crs.authid()}', tytul, 'memory')
    lyr.dataProvider().addAttributes(
        [QgsField('OPIS', QVariant.String, '', 100)])
    lyr.updateFields()
    feats = []
    for pkt, opis in punkty:
        f = QgsFeature(lyr.fields())
        f.setGeometry(QgsGeometry.fromPointXY(pkt))
        f['OPIS'] = opis
        feats.append(f)
    lyr.dataProvider().addFeatures(feats)
    dodana = QgsProject.instance().addMapLayer(lyr)
    dodana.loadNamedStyle(
        os.path.join(_QML_DIR, 'point_drop_shadow_red.qml'))
    return dodana


def _warstwa_bledow_poligonowych(wydz_lyr, poligony, fidy, tytul):
    """Kopiuje wskazane poligony WYDZ do nowej warstwy memory (podgląd
    błędu). Styl - WYDZ_z_wieloma_kartami.qml."""
    lyr = QgsVectorLayer(
        f'MultiPolygon?crs={wydz_lyr.crs().authid()}', tytul, 'memory')
    lyr.dataProvider().addAttributes(wydz_lyr.fields().toList())
    lyr.updateFields()
    feats = [poligony[fid] for fid in fidy]
    lyr.dataProvider().addFeatures(feats)
    dodana = QgsProject.instance().addMapLayer(lyr)
    dodana.loadNamedStyle(
        os.path.join(_QML_DIR, 'WYDZ_z_wieloma_kartami.qml'))
    return dodana


def wykonaj(klon_lyr, wydz_lyr):
    """Waliduje warstwę Klon względem WYDZ i - jeśli poprawna - wpisuje
    ADR_Z/ADR_DO do warstwy Klon.

    Returns:
        Dict z kluczem 'ok'. Gdy False - dodatkowo 'komunikat' (str) do
        pokazania użytkownikowi (warstwa błędów już dodana do projektu).
        Gdy True - dodatkowo 'pary': lista (adr_z, adr_do).
    """
    poligony = {f.id(): f for f in wydz_lyr.getFeatures()}
    si = QgsSpatialIndex()
    for f in poligony.values():
        si.insertFeature(f)

    # 1. geometria - oba konce kazdego odcinka musza lezec na wydzieleniu
    dopasowania = {}  # klon_fid -> (start_fid, koniec_fid)
    zle_punkty = []
    for f in klon_lyr.getFeatures():
        start, koniec = _konce_odcinka(f.geometry())

        start_fid = _znajdz_poligon(si, poligony, QgsGeometry.fromPointXY(start))
        koniec_fid = _znajdz_poligon(si, poligony, QgsGeometry.fromPointXY(koniec))

        if start_fid is None:
            zle_punkty.append((start, f'odcinek fid={f.id()} - początek'))
        if koniec_fid is None:
            zle_punkty.append((koniec, f'odcinek fid={f.id()} - koniec'))

        if start_fid is not None and koniec_fid is not None:
            dopasowania[f.id()] = (start_fid, koniec_fid)

    if zle_punkty:
        _warstwa_bledow_punktowych(
            klon_lyr.crs(), 'Klon - punkty poza wydzieleniami', zle_punkty)
        return {
            'ok': False,
            'komunikat': (
                f'{len(zle_punkty)} punkt(ów) warstwy Klon nie leży na żadnym '
                'wydzieleniu warstwy WYDZ. Popraw geometrię (patrz warstwa '
                '"Klon - punkty poza wydzieleniami") i uruchom ponownie.'
            ),
        }

    # 2. zrodlo i cel w tym samym poligonie - klonowanie do samego siebie
    petle = {
        klon_fid for klon_fid, (s, k) in dopasowania.items() if s == k
    }
    if petle:
        petle_wydz = {dopasowania[klon_fid][0] for klon_fid in petle}
        _warstwa_bledow_poligonowych(
            wydz_lyr, poligony, petle_wydz,
            'Klon - źródło i cel w tym samym wydzieleniu')
        return {
            'ok': False,
            'komunikat': (
                f'{len(petle)} odcinek(ów) ma początek i koniec w tym samym '
                'wydzieleniu (klonowanie do samego siebie nie ma sensu). '
                'Popraw warstwę Klon (patrz "Klon - źródło i cel w tym samym '
                'wydzieleniu") i uruchom ponownie.'
            ),
        }

    # 3. wiele-do-jeden: kilka roznych zrodel do tego samego celu
    cele = {}  # koniec_fid -> set(start_fid)
    for start_fid, koniec_fid in dopasowania.values():
        cele.setdefault(koniec_fid, set()).add(start_fid)

    kolizyjne_cele = {k for k, v in cele.items() if len(v) > 1}
    if kolizyjne_cele:
        _warstwa_bledow_poligonowych(
            wydz_lyr, poligony, kolizyjne_cele,
            'Klon - konflikt wiele-do-jeden')
        return {
            'ok': False,
            'komunikat': (
                f'{len(kolizyjne_cele)} wydzielenie(a) docelowe mają więcej '
                'niż jedno źródło klonowania (kilka różnych wydzieleń '
                'klonuje do tego samego celu). Popraw warstwę Klon (patrz '
                '"Klon - konflikt wiele-do-jeden") i uruchom ponownie.'
            ),
        }

    if not dopasowania:
        return {'ok': True, 'pary': []}

    # 4. wyciagniecie adresow ADR_LES + zapis do warstwy Klon
    fnm = klon_lyr.dataProvider().fieldNameMap()
    zmiany = {}
    pary = []
    for klon_fid, (start_fid, koniec_fid) in dopasowania.items():
        adr_z = poligony[start_fid]['ADR_LES']
        adr_do = poligony[koniec_fid]['ADR_LES']
        zmiany[klon_fid] = {fnm['ADR_Z']: adr_z, fnm['ADR_DO']: adr_do}
        pary.append((adr_z, adr_do))

    klon_lyr.startEditing()
    for fid, wpis in zmiany.items():
        klon_lyr.dataProvider().changeAttributeValues({fid: wpis})
    klon_lyr.commitChanges()

    return {'ok': True, 'pary': pary}


def wykonaj_notatki(notatki_lyr, wydz_lyr):
    """Dla każdego punktu warstwy notatek (opis_notatki) znajduje adres
    leśny wydzielenia WYDZ, na którym leży.

    W odróżnieniu od `wykonaj` (Klon) sprawdzane jest TYLKO położenie -
    punkt musi trafiać w jakieś WYDZ - bez kontroli 1:1/dubletów, bo kilka
    notatek na tym samym wydzieleniu jest normalne i dopuszczalne.

    Returns:
        Dict z kluczem 'ok'. Gdy False - dodatkowo 'komunikat' (str),
        warstwa błędów już dodana do projektu. Gdy True - dodatkowo
        'pary': lista (adr_les, notatka).
    """
    poligony = {f.id(): f for f in wydz_lyr.getFeatures()}
    si = QgsSpatialIndex()
    for f in poligony.values():
        si.insertFeature(f)

    zle_punkty = []
    pary = []
    for f in notatki_lyr.getFeatures():
        geom = f.geometry()
        fid = _znajdz_poligon(si, poligony, geom)
        if fid is None:
            zle_punkty.append((geom.asPoint(), f'notatka fid={f.id()}'))
            continue
        pary.append((poligony[fid]['ADR_LES'], f['NOTATKA']))

    if zle_punkty:
        _warstwa_bledow_punktowych(
            notatki_lyr.crs(), 'Notatki - punkty poza wydzieleniami',
            zle_punkty)
        return {
            'ok': False,
            'komunikat': (
                f'{len(zle_punkty)} punkt(ów) warstwy notatek nie leży na '
                'żadnym wydzieleniu warstwy WYDZ. Popraw geometrię (patrz '
                'warstwa "Notatki - punkty poza wydzieleniami") i uruchom '
                'ponownie.'
            ),
        }

    return {'ok': True, 'pary': pary}


def zapisz_plik(pary, sciezka):
    """Zapisuje plik tekstowy (KLON.txt w formacie wymaganym przez
    Klonuj.dane_konf(), albo NOTATKI_zmiany.txt) - dwie kolumny
    rozdzielone tabulatorem, bez pustej linii na końcu."""
    with open(sciezka, 'w', encoding='utf-8', newline='') as plik:
        for a, b in pary:
            plik.write(f'{a}\t{b}\n')
