"""Buduje dane do protokołu kontroli terenowej: numery działek per
wydzielenie, w płaskiej tabeli z kolumnami gmina/obręb/wydzielenie/
działki/uwagi (gmina i obręb są już w kolumnach, więc bez osobnych
wierszy-nagłówków grup) - posortowanej po kodzie obrębu, a w obrębie po
adresie leśnym.

Numery działek NIE są liczone przez przecięcie geometrii WYDZ_kontrola x
DZKAT (dwie osobne warstwy shp mogą się nieznacznie rozjeżdżać przez
digitalizację/snapping, co dawałoby fałszywe trafienia albo pomijało
działki stykające się tylko wąskim paskiem) - zamiast tego pobierane są
wprost z bazy, z przypisania zapisanego przez taksatora
(F_AROD_LAND_USE -> F_PARCEL, ten sam wzorzec złączenia co kwerenda
OT_register w core/ot.py, tylko po PARCEL_NR zamiast LAND_REGISTER_NR).

Ani WYDZ, ani DZKAT nie mają w atrybutach nazw gminy/obrębu (tylko kody
administracyjne COUNTY/DISTRICT/MUNICIP/COMMUNITY) - nazwy (nazwy_obr,
nazwy_gm) przychodzą gotowe z zewnątrz, zbudowane przez
baza_finder.zbuduj_mape_wydzielen() z tabeli F_COMMUNITY tej samej bazy
.mdb, do której dopasowano dane wydzielenie (MUNICIPALITY_NAME /
COMMUNITY_NAME przez Baza.pobierz_naglowek()) - nie z warstwy OBR,
której schemat pól nie jest ujednolicony między projektami.
"""

import re

from ...funkcje import isNone
from .kody import kod_gminy as _kod_gminy, kod_obrebu as _kod_obrebu

KWERENDA_DZIALKI = '''
SELECT
    F_AROD_LAND_USE.ARODES_INT_NUM,
    F_PARCEL.PARCEL_NR
FROM
    F_AROD_LAND_USE INNER JOIN F_PARCEL ON
    F_AROD_LAND_USE.PARCEL_INT_NUM = F_PARCEL.PARCEL_INT_NUM
WHERE
    F_AROD_LAND_USE.ARODES_INT_NUM in ({})
;
'''


def pobierz_dzialki(baza, arodes_ids):
    """Zwraca {ARODES_INT_NUM: {nr_dzialki, ...}} z otwartej bazy, dla
    podanej listy ARODES_INT_NUM (jedna baza = jedno wywołanie, tak samo
    jak GeneratorOT w core/ot.py)."""
    ids_sql = ','.join(str(int(a)) for a in arodes_ids)
    wynik = baza.pobierz(KWERENDA_DZIALKI.format(ids_sql))

    dzialki = {}
    for arodes_int_num, parcel_nr in (wynik or []):
        dzialki.setdefault(arodes_int_num, set()).add(isNone(parcel_nr))
    return dzialki


def _adres_z_adr_les(adr_les):
    """Ten sam format co Wydzielenie.dodaj_opis() w core/ot.py, żeby
    adresy w OT.docx i w protokole wyglądały tak samo."""
    adr = adr_les[13:17] + '-' + adr_les[18:22]
    return adr.replace(' ', '')


def _klucz_naturalny(tekst):
    """Klucz sortowania numerów działek w postaci np. '11/3' - liczby
    porównywane liczbowo, nie leksykograficznie (żeby '2' < '11')."""
    return [int(cz) if cz.isdigit() else cz
            for cz in re.split(r'(\d+)', tekst)]


def zbuduj_dane_protokolu(wpisy, dzialki_wg_arodes, nazwy_obr=None,
                          nazwy_gm=None):
    """wpisy: lista (feat, arodes_int_num) - zaznaczone obiekty
    WYDZ_kontrola z dopasowanym ARODES_INT_NUM (patrz baza_finder.py),
    jednej grupy (Nadleśnictwa albo całości, zależnie od checkboxa
    razem/osobno).
    dzialki_wg_arodes: {ARODES_INT_NUM: {nr_dzialki, ...}}, złączenie
    wyników pobierz_dzialki() ze wszystkich baz obecnych w wpisach.

    Zwraca płaską listę wierszy, posortowaną po (kod_obrebu, adres_lesny):
    [{'gmina': .., 'obreb': .., 'wydzielenie': .., 'dzialki': .., 'uwagi': ..}]
    """
    nazwy_obr = nazwy_obr or {}
    nazwy_gm = nazwy_gm or {}

    wiersze = []
    for feat, arodes_int_num in wpisy:
        dzialki = dzialki_wg_arodes.get(arodes_int_num, set())

        kod_obr = _kod_obrebu(feat)
        kod_gm = _kod_gminy(feat)
        adr_les = isNone(feat['ADR_LES'])

        wiersze.append({
            'gmina': nazwy_gm.get(kod_gm, kod_gm),
            'obreb': kod_obr[-4:] + ' ' + nazwy_obr.get(kod_obr, ''),
            'wydzielenie': _adres_z_adr_les(adr_les) if adr_les else '',
            'dzialki': ';'.join(sorted(dzialki, key=_klucz_naturalny)),
            'uwagi': '',
            '_sort_klucz': (kod_obr, adr_les),
        })

    wiersze.sort(key=lambda w: w['_sort_klucz'])
    for w in wiersze:
        del w['_sort_klucz']
    return wiersze
