"""Tworzy plik KLON.txt na podstawie warstwy odcinków "Klon" i warstwy
wydzieleń WYDZ - format zgodny z Klonuj.dane_konf() z baza_klonuj_wydz.py
(ADR_LES źródłowy TAB ADR_LES docelowy, jedna para na linię).

Każdy odcinek warstwy Klon: początek = wydzielenie źródłowe (skąd
kopiujemy opis), koniec = wydzielenie docelowe. Tylko pierwszy i ostatni
wierzchołek odcinka mają znaczenie - ewentualne pośrednie wierzchołki są
ignorowane.

Przed zapisem trzy kontrole (patrz `wykonaj`):

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
"""

from PyQt5.QtCore import QVariant
from qgis.core import (
    QgsFeature, QgsField, QgsGeometry, QgsProject, QgsSpatialIndex,
    QgsVectorLayer,
)


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


def _warstwa_bledow_punktowych(crs, punkty):
    """punkty: lista (QgsPointXY, opis)."""
    lyr = QgsVectorLayer(
        f'Point?crs={crs.authid()}', 'Klon - punkty poza wydzieleniami',
        'memory')
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
    QgsProject.instance().addMapLayer(lyr)
    return lyr


def _warstwa_bledow_liniowych(klon_lyr, fidy, tytul):
    """Kopiuje wskazane odcinki Klon do nowej warstwy memory (podgląd błędu)."""
    lyr = QgsVectorLayer(
        f'LineString?crs={klon_lyr.crs().authid()}', tytul, 'memory')
    lyr.dataProvider().addAttributes(klon_lyr.fields().toList())
    lyr.updateFields()
    feats = [f for f in klon_lyr.getFeatures() if f.id() in fidy]
    lyr.dataProvider().addFeatures(feats)
    QgsProject.instance().addMapLayer(lyr)
    return lyr


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
        _warstwa_bledow_punktowych(klon_lyr.crs(), zle_punkty)
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
        _warstwa_bledow_liniowych(
            klon_lyr, petle, 'Klon - źródło i cel w tym samym wydzieleniu')
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
        fidy_bledne = {
            klon_fid for klon_fid, (s, k) in dopasowania.items()
            if k in kolizyjne_cele
        }
        _warstwa_bledow_liniowych(
            klon_lyr, fidy_bledne, 'Klon - konflikt wiele-do-jeden')
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


def zapisz_plik(pary, sciezka):
    """Zapisuje plik KLON.txt - format wymagany przez Klonuj.dane_konf():
    dwie kolumny rozdzielone tabulatorem, bez pustej linii na końcu."""
    with open(sciezka, 'w', encoding='utf-8', newline='') as plik:
        for adr_z, adr_do in pary:
            plik.write(f'{adr_z}\t{adr_do}\n')
