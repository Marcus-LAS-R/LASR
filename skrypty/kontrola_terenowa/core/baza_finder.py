"""Dopasowanie zaznaczonych wydzieleń (WYDZ_kontrola.ADR_LES) do bazy
.mdb, w której się znajdują - i przy okazji nazw gmin/obrębów z tej samej
bazy (F_COMMUNITY/F_MUNICIPALITY), do protokołu i nagłówków OT.

Katalog z bazami jest płaski (jeden poziom, jak w PolaczBazy z
baza_polacz.py) - może zawierać wiele baz .mdb, po jednej na obręb.
Dopasowanie wydzieleń idzie przez ADRESS_FOREST z F_ARODES (ta sama
kolumna, którą zapisuje ADR_LES w warstwie WYDZ), a nie przez nazwę
pliku - nazwy baz nie mają wymuszonej konwencji.

UWAGA (poprzedni bug): Baza.pobierz_naglowek() (baza_wrapper.py) zwraca
tylko gotowe F_COMMUNITY.MUNICIPALITY_CD, bez COUNTY_CD/DISTRICT_CD - a
te trzy pola w bazie są ROZŁĄCZNE (tak samo jak w F_PARCEL, patrz
Baza.pobierz_klucze_dzialek()), więc samo MUNICIPALITY_CD NIE jest tym
samym co kod_gminy() z core/kody.py (COUNTY+DISTRICT+MUNICIP sklejone z
warstwy WYDZ) - przez co dopasowanie po kluczu zawsze zawodziło i nazwy
gmin/obrębów wychodziły puste. Tu pobierane są wszystkie 4 kody osobno
i sklejane DOKŁADNIE tą samą funkcją co dla featurów z warstwy, żeby
klucze na pewno się zgadzały niezależnie od tego, ile znaków ma
MUNICIPALITY_CD w tej konkretnej bazie.
"""

import glob
import os

from ...baza_wrapper import Baza
from ...funkcje import isNone

KWERENDA_NAZWY = '''
SELECT
    F_COMMUNITY.COUNTY_CD,
    F_COMMUNITY.DISTRICT_CD,
    F_COMMUNITY.MUNICIPALITY_CD,
    F_COMMUNITY.COMMUNITY_CD,
    F_COMMUNITY.COMMUNITY_NAME,
    F_MUNICIPALITY.MUNICIPALITY_NAME
FROM
    F_COMMUNITY LEFT JOIN F_MUNICIPALITY ON
    F_COMMUNITY.COUNTY_CD = F_MUNICIPALITY.COUNTY_CD AND
    F_COMMUNITY.DISTRICT_CD = F_MUNICIPALITY.DISTRICT_CD AND
    F_COMMUNITY.MUNICIPALITY_CD = F_MUNICIPALITY.MUNICIPALITY_CD
;
'''


def znajdz_bazy(katalog):
    """Zwraca posortowaną listę ścieżek do plików .mdb w katalogu
    (płasko, bez podkatalogów)."""
    return sorted(glob.glob(os.path.join(katalog, '*.mdb')))


def zbuduj_mape_wydzielen(sciezki_baz):
    """Otwiera po kolei podane bazy i buduje:
    - mapę ADR_LES -> (sciezka_bazy, ARODES_INT_NUM)
    - słownik nazw gmin {kod_gminy: MUNICIPALITY_NAME}
    - słownik nazw obrębów {kod_obrebu: COMMUNITY_NAME}
      (klucze w DOKŁADNIE tym samym formacie co core/kody.py
      kod_gminy()/kod_obrebu() liczone z warstwy WYDZ - string
      COUNTY+DISTRICT+MUNICIP[+COMMUNITY], żeby dopasowanie działało
      niezależnie od naturalnej szerokości MUNICIPALITY_CD w bazie)

    Jeżeli ten sam ADR_LES/kod występuje w więcej niż jednej bazie,
    wygrywa pierwszy napotkany (kolejność jak w sciezki_baz) - błędy
    tego typu powinna wcześniej wyłapać kontrola duplikatów wydzieleń
    (baza_polacz.py), nie ten skrypt.

    Zwraca (mapa_wydzielen, nazwy_gmin, nazwy_obr, bledy) gdzie bledy to
    lista opisów baz, z którymi nie udało się połączyć.
    """
    mapa = {}
    nazwy_gmin = {}
    nazwy_obr = {}
    bledy = []

    for sc in sciezki_baz:
        baza = Baza(sc)
        if not baza.polacz():
            bledy.append('Nie udało się połączyć z bazą: ' + sc)
            continue

        wydz = baza.pobierz_wydzielenia()
        nazwy = baza.pobierz(KWERENDA_NAZWY)
        baza.zamknij()

        if wydz is False:
            bledy.append('Brak wydzieleń (F_ARODES) w bazie: ' + sc)
        else:
            for adr_les, arodes_int_num in wydz.items():
                if adr_les not in mapa:
                    mapa[adr_les] = (sc, arodes_int_num)

        if not nazwy:
            bledy.append('Brak danych F_COMMUNITY/F_MUNICIPALITY w bazie: ' + sc)
            continue

        for county_cd, district_cd, municip_cd, community_cd, obreb_nazwa, gmina_nazwa in nazwy:
            kod_gm = isNone(county_cd) + isNone(district_cd) + isNone(municip_cd)
            kod_obr = kod_gm + isNone(community_cd)
            nazwy_gmin.setdefault(kod_gm, isNone(gmina_nazwa))
            nazwy_obr.setdefault(kod_obr, isNone(obreb_nazwa))

    return mapa, nazwy_gmin, nazwy_obr, bledy
