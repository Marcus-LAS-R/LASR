# -*- coding: utf-8 -*-
"""Pobieranie wydzieleń z BDL (usługa REST za WMS-em
https://mapserver.bdl.lasy.gov.pl/ArcGIS/services/WMS_BDL/mapserver/WMSServer).

WMS daje tylko obraz - ta sama usługa jako ArcGIS MapServer odpowiada na
zapytania /query z geometrią (GeoJSON, od razu w EPSG:2180):
- warstwa 5: Wydzielenia PGL LP,
- warstwa 6: Wydzielenia poza PGL LP wg PUL.
Serwer zwraca najwyżej 2000 obiektów na zapytanie, więc obszar dzielony jest
na stałą siatkę kwadratów (ROZMIAR_KOMORKI, wspólną dla całego kraju - przy
dociąganiu nowe komórki nie nakładają się na pobrane), a w komórce wyniki
są stronicowane (resultOffset)."""
import json
import math
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

import requests
from osgeo import ogr
from qgis.core import QgsGeometry, QgsRectangle, QgsWkbTypes

URL = ("https://mapserver.bdl.lasy.gov.pl/ArcGIS/rest/services/WMS_BDL/"
       "MapServer/{}/query")
WARSTWY = {5: "PGL", 6: "INNE"}       # numer warstwy BDL -> ZRODLO
POLA = "subarea_id,adress_forest,area_type_cd"
POLA_INNE = POLA + ",owner_cat_name"
ROZMIAR_KOMORKI = 2000.0              # m
STRONA = 2000                         # maxRecordCount serwera
PROBY = 3
TIMEOUT = 60
WATKI = 6                             # równoległe zapytania do serwera


def komorki(prostokat):
    """Indeksy (i, j) komórek siatki przecinających prostokąt (EPSG:2180)."""
    r = ROZMIAR_KOMORKI
    return {(i, j)
            for i in range(int(math.floor(prostokat.xMinimum() / r)),
                           int(math.floor(prostokat.xMaximum() / r)) + 1)
            for j in range(int(math.floor(prostokat.yMinimum() / r)),
                           int(math.floor(prostokat.yMaximum() / r)) + 1)}


def prostokat_komorki(kom):
    r = ROZMIAR_KOMORKI
    return QgsRectangle(kom[0] * r, kom[1] * r, (kom[0] + 1) * r,
                        (kom[1] + 1) * r)


def _zapytanie(warstwa, prost, offset):
    parametry = {
        "f": "geojson",
        "where": "1=1",
        "geometry": json.dumps({
            "xmin": prost.xMinimum(), "ymin": prost.yMinimum(),
            "xmax": prost.xMaximum(), "ymax": prost.yMaximum()}),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "inSR": 2180, "outSR": 2180,
        "outFields": POLA_INNE if WARSTWY[warstwa] == "INNE" else POLA,
        "returnGeometry": "true",
        "orderByFields": "subarea_id",
        "resultOffset": offset,
        "resultRecordCount": STRONA,
    }
    blad = None
    for _ in range(PROBY):
        try:
            odp = requests.get(URL.format(warstwa), params=parametry,
                               timeout=TIMEOUT)
            if odp.status_code != 200:
                blad = "HTTP %d" % odp.status_code
                continue
            dane = odp.json()
            if "error" in dane:
                blad = str(dane["error"])
                continue
            return dane
        except (requests.RequestException, ValueError) as e:
            blad = str(e)
    raise RuntimeError("BDL (warstwa %d, komórka %s): %s"
                       % (warstwa, prost.toString(0), blad))


def _geometria(geojson):
    if not geojson:
        return None
    g = ogr.CreateGeometryFromJson(json.dumps(geojson))
    if g is None:
        return None
    geom = QgsGeometry()
    geom.fromWkb(bytes(g.ExportToIsoWkb()))
    return napraw(geom)


def napraw(geom):
    """Poprawna geometria poligonowa (makeValid może dać kolekcję z
    liniami - zostają same poligony) albo None."""
    if geom is None or geom.isNull() or geom.isEmpty():
        return None
    if not geom.isGeosValid():
        geom = geom.makeValid()
        if QgsWkbTypes.flatType(geom.wkbType()) == \
                QgsWkbTypes.GeometryCollection:
            geom = geom.convertGeometryCollectionToSubclass(
                QgsWkbTypes.PolygonGeometry)
    if geom.isNull() or geom.isEmpty() or \
            geom.type() != QgsWkbTypes.PolygonGeometry:
        return None
    return geom


def _pobierz_surowe(kom, warstwa):
    """Obiekty GeoJSON (dict) przecinające komórkę - wszystkie strony.
    Tylko sieć i JSON, więc można wołać z wątków."""
    prost = prostokat_komorki(kom)
    wynik, offset = [], 0
    while True:
        dane = _zapytanie(warstwa, prost, offset)
        obiekty = dane.get("features") or []
        wynik += obiekty
        przekroczono = dane.get("exceededTransferLimit") or \
            (dane.get("properties") or {}).get("exceededTransferLimit")
        if not obiekty or (len(obiekty) < STRONA and not przekroczono):
            return wynik
        offset += len(obiekty)


def _na_krotki(obiekty):
    wynik = []
    for f in obiekty:
        p = f.get("properties") or {}
        g = _geometria(f.get("geometry"))
        if g is None:
            continue
        wynik.append((p.get("subarea_id", f.get("id")), g,
                      (p.get("adress_forest") or "").strip(),
                      (p.get("area_type_cd") or "").strip(),
                      (p.get("owner_cat_name") or "").strip()))
    return wynik


def pobierz_komorke(kom, warstwa):
    """[(subarea_id, geometria, adres, typ_pow, własność)] wydzieleń
    przecinających komórkę."""
    return _na_krotki(_pobierz_surowe(kom, warstwa))


def pobierz_rownolegle(zadania, postep=None):
    """{(komórka, warstwa): [krotki jak pobierz_komorke]} dla listy zadań
    (komórka, warstwa); zapytania w WATKI wątkach, geometrie budowane w
    wątku wołającym. postep(k, n) -> False przerywa (zwraca None)."""
    wyniki = {}
    pula = ThreadPoolExecutor(max_workers=WATKI)
    przyszle = {pula.submit(_pobierz_surowe, kom, w): (kom, w)
                for kom, w in zadania}
    oczekujace = set(przyszle)
    try:
        while oczekujace:
            gotowe, oczekujace = wait(oczekujace, timeout=0.2,
                                      return_when=FIRST_COMPLETED)
            for p in gotowe:
                wyniki[przyszle[p]] = _na_krotki(p.result())
            if postep is not None and not postep(len(wyniki), len(zadania)):
                return None
    finally:
        for p in oczekujace:
            p.cancel()
        pula.shutdown(wait=False)
    return wyniki
