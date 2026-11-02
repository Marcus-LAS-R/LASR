# -*- coding: utf-8 -*-
"""Edytor opisu - "Pobierz opis BDL": opis wydzielenia wskazanego na mapie,
pobierany w locie z Banku Danych o Lasach i zamieniany na model karty.

Zapytania i konwersja kodów te same co w "Ściągnij dane z BDL" i "Utwórz bazę
z BDL" (pobierz_BDL.py, utworz_baze_z_BDL.py - importowane w funkcjach, żeby
przeliczenia dało się testować bez QGIS-a). Zabiegi z BDL są pomijane.

Wiek, pierśnica, wysokość i masa są przeliczane na bieżący rok ze stanu BDL
(a_year, "stan na") wg parametrów operacji F1 aktualizacji UPUL
(aktualizacja_upul/config/constants.json, sekcja f1): wiek + liczba lat,
wymiary wg growth_table (przyrost na 10 lat wg klasy wieku) rok po roku, żeby
liczyć poprawnie przy przejściu przez kolejne klasy, masa razy
volume_multiplier ** (lata / 10) - tak samo jak kolejne przebiegi F1.
"""
import json
import os
from urllib.parse import quote

_STALE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'aktualizacja_upul', 'config', 'constants.json')

_URL_PUNKT = (
    'https://mapserver.bdl.lasy.gov.pl/ArcGIS/rest/services/'
    'Mapa_podstawowa_BDL/MapServer/21/query?f=json&returnGeometry=false'
    '&geometry=%7Bx%3A{}%2Cy%3A{}%7D&geometryType=esriGeometryPoint'
    '&inSR=2180&outFields=arodes_int_num%2Cadress_forest%2Ca_year'
    '%2Cowner_cat_name'
)
_LIMIT_CZASU = 20  # [s] - karta czeka na odpowiedź


class BladBDL(Exception):
    """Komunikat dla użytkownika: sieć, serwer albo niepełna odpowiedź."""


# ------------------------------------------------------- przeliczenie stanu

def parametry_wzrostu():
    """(tabela przyrostów, mnożnik masy na 10 lat) - sekcja f1 stałych."""
    with open(_STALE, encoding='utf-8') as f:
        f1 = json.load(f)['f1']
    return f1['growth_table'], f1['volume_multiplier']


def _przyrost_10_lat(wiek, tabela):
    for w in tabela:
        if wiek >= w['min_age'] and (w['max_age'] is None
                                     or wiek <= w['max_age']):
            return w['height_delta'], w['bhd_delta']
    return 0, 0  # młodsze - bez przyrostu, jak w F1


def przyrosty(wiek, lata, tabela):
    """(przyrost wysokości, przyrost pierśnicy) przez `lata` lat."""
    h, b = 0.0, 0.0
    for rok in range(1, lata + 1):
        dh, db = _przyrost_10_lat(wiek + rok, tabela)
        h += dh / 10
        b += db / 10
    return h, b


def _zaokraglij(x):
    return int(x + 0.5)


def przelicz_gatunek(gatunek, lata, tabela, mnoznik_masy):
    """Wiek, pierśnica, wysokość i masa (pola F_STOREY_SPECIES) o `lata` lat
    do przodu. Bez wieku - bez zmian; brak wymiaru lub masy zostaje brakiem."""
    wiek = gatunek.get('SPECIES_AGE')
    if lata <= 0 or wiek is None:
        return gatunek
    h, b = przyrosty(wiek, lata, tabela)
    gatunek['SPECIES_AGE'] = wiek + lata
    if gatunek.get('HEIGHT'):
        gatunek['HEIGHT'] = _zaokraglij(gatunek['HEIGHT'] + h)
    if gatunek.get('BHD'):
        gatunek['BHD'] = _zaokraglij(gatunek['BHD'] + b)
    for pole in ('VOLUME', 'VOLUME_TEMP'):
        if gatunek.get(pole):
            gatunek[pole] = round(
                gatunek[pole] * mnoznik_masy ** (lata / 10), 2)
    return gatunek


# ------------------------------------------------------------- pobieranie

def _pobierz_json(url, naglowki):
    import requests
    try:
        odp = requests.get(url, headers=naglowki, timeout=_LIMIT_CZASU)
    except requests.RequestException as e:
        raise BladBDL(f'brak połączenia z BDL ({type(e).__name__})')
    if odp.status_code != 200:
        raise BladBDL(f'serwer BDL zwrócił HTTP {odp.status_code}')
    try:
        return json.loads(odp.text)
    except ValueError:
        raise BladBDL('nieczytelna odpowiedź serwera BDL')


def szukaj_w_punkcie(x, y):
    """Wydzielenia BDL w punkcie (EPSG:2180): atrybuty, najnowszy stan
    pierwszy. Pusta lista - w tym miejscu BDL nie ma wydzielenia."""
    from .pobierz_BDL import _HEADERS_GEOM
    wynik = _pobierz_json(_URL_PUNKT.format(x, y), _HEADERS_GEOM)
    if 'features' not in wynik:
        raise BladBDL('serwer BDL odrzucił zapytanie')
    return sorted((f['attributes'] for f in wynik['features']),
                  key=lambda a: a.get('a_year') or 0, reverse=True)


def pobierz_opis(atrybuty):
    from .pobierz_BDL import _HEADERS_OPIS, _URL_OPIS
    return _pobierz_json(
        _URL_OPIS.format(atrybuty['arodes_int_num'], atrybuty['a_year'],
                         quote(str(atrybuty['adress_forest']))),
        _HEADERS_OPIS)


# ------------------------------------------------------------- model karty

def opis_karty(odpowiedz, lata, tabela, mnoznik_masy):
    """(pola opisu {pole F_SUBAREA: kod}, wiersze warstw, wiersze gatunków) -
    wiersze w kształcie tabel, jak czytane z bazy przez kartę."""
    from .utworz_baze_z_BDL import (
        _zbuduj_f_arod_storey_wiersze, _zbuduj_f_storey_species_wiersze,
        _zbuduj_f_subarea_wiersz)

    def _po_kolei(kategoria):
        return {0: [dict(w, kolej=i)
                    for i, w in enumerate(odpowiedz.get(kategoria) or [])]}

    sub = _zbuduj_f_subarea_wiersz(0, _po_kolei('generalData'),
                                   _po_kolei('generalData2'))
    if sub is None:
        raise BladBDL('BDL nie zwrócił opisu tego wydzielenia')
    pola = {p: sub.get(p) for p in (
        'AREA_TYPE_CD', 'STAND_STRUCT_CD', 'DAMAGE_DEGREE_CD', 'CAUSE_CD',
        'SITE_TYPE_CD', 'VEG_COVER_CD')}

    gatunki_bdl = _po_kolei('layerSpecies')
    warstwy = sorted(
        _zbuduj_f_arod_storey_wiersze(0, gatunki_bdl, _po_kolei('layer')),
        key=lambda w: w['STOREY_RANK_ORDER'] or 99)
    gatunki = []
    for g in _zbuduj_f_storey_species_wiersze(0, gatunki_bdl):
        g['SPEC_STOR_INT_NUM'] = None  # nowy rekord
        gatunki.append(przelicz_gatunek(g, lata, tabela, mnoznik_masy))
    return pola, warstwy, gatunki
