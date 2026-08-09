"""Buduje DZKAT_kontrola: podzbiór warstwy DZKAT ograniczony do działek
faktycznie przypisanych (w bazie, przez F_AROD_LAND_USE/F_PARCEL - patrz
core/protokol.pobierz_dzialki) do kontrolowanych wydzieleń, zamiast
całej (zwykle dużo większej) warstwy DZKAT. Zapisywany jako osobny .shp
w katalogu docelowym - i to on, nie cała warstwa DZKAT, trafia do
eksportu KML (core/kml_eksport.py).
"""

from qgis.core import QgsVectorFileWriter, QgsVectorLayer

from ...funkcje import isNone
from .kody import kod_gminy


def _klucz_dzkat(feat):
    return (kod_gminy(feat), isNone(feat['COMMUNITY']), isNone(feat['PARCELNR']))


def zbuduj_klucze_dzialek(wpisy, dzialki_wg_arodes):
    """wpisy: (feat, baza_sc, arodes_int_num) wszystkich dopasowanych
    kontrolowanych wydzieleń. dzialki_wg_arodes: {ARODES_INT_NUM:
    {nr_dzialki, ...}} z core/protokol.pobierz_dzialki().

    Zwraca zbiór kluczy (kod_gminy, community, nr_dzialki) do
    dopasowania featurów w warstwie DZKAT."""
    klucze = set()
    for feat, _baza_sc, arodes_int_num in wpisy:
        community = isNone(feat['COMMUNITY'])
        for parcelnr in dzialki_wg_arodes.get(arodes_int_num, set()):
            klucze.add((kod_gminy(feat), community, parcelnr))
    return klucze


def zbuduj_warstwe(dzkat_layer, klucze_dzialek):
    """Zwraca warstwę memory z tylko dopasowanymi działkami, albo None
    gdy nic nie pasuje (np. brak dopasowanych baz / pustych wyników
    pobierz_dzialki)."""
    dopasowane = [feat for feat in dzkat_layer.getFeatures()
                  if _klucz_dzkat(feat) in klucze_dzialek]
    if not dopasowane:
        return None

    lyr = QgsVectorLayer(
        'Polygon?crs=' + dzkat_layer.crs().authid(), 'DZKAT_kontrola', 'memory')
    lyr.startEditing()
    lyr.dataProvider().addAttributes(dzkat_layer.dataProvider().fields().toList())
    lyr.updateFields()
    lyr.dataProvider().addFeatures(dopasowane)
    lyr.commitChanges()
    return lyr


def zapisz_shp(lyr, sciezka_docelowa):
    QgsVectorFileWriter.writeAsVectorFormat(
        lyr, sciezka_docelowa, 'UTF-8', lyr.crs(), 'ESRI Shapefile')
