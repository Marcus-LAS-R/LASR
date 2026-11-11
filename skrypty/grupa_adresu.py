# -*- coding: utf-8 -*-
"""Czysta logika (bez QGIS-a) dla "Sprawdź poprawność grupy": porównanie
adresów leśnych z bazy z adresami z grafiki z pominięciem grupy (formy
własności, pozycje [11:13] adresu - patrz project_grp_forma_wlasnosci) i
plan przemianowania adresów w bazie na grupę z grafiki.
Testy: testy/test_grupa_adresu.py."""
from collections import defaultdict

GRP_OD, GRP_DO = 11, 13
TYPY = ('WYDZIEL', 'ODDZ')


def grupa(adres):
    return str(adres)[GRP_OD:GRP_DO]


def bez_grupy(adres):
    adres = str(adres)
    return adres[:GRP_OD] + adres[GRP_DO:]


def adres_oddzialu(adres_wydz):
    """Adres rekordu ODDZ dla adresu wydzielenia (ta sama długość 25):
    'K110620003-991   -a   -00' -> 'K110620003-991   -    -  '."""
    return str(adres_wydz)[:18] + '    -  '


def plan_przemianowania(adresy_bazy, adresy_grafiki):
    """adresy_bazy: {adres: typ_rekordu} (F_ARODES), adresy_grafiki: adresy
    wydzieleń z warstwy. Rekordy WYDZIEL i ODDZ z bazy, których adresu nie
    ma w grafice, są parowane z grafiką po adresie bez grupy (dla ODDZ -
    po adresach oddziałów wyprowadzonych z wydzieleń grafiki).

    Zwraca dict:
    - zmiany: [(stary, nowy)] - różni się tylko grupą, nowego nie ma w
      bazie -> do przemianowania,
    - kolizje: [(stary, nowy)] - nowy adres już jest w bazie (np. pusty
      duplikat dopisany z grafiki) -> nie ruszamy, do wyjaśnienia,
    - niejednoznaczne: [(stary, [kandydaci])] - kilka adresów grafiki
      pasuje bez grupy,
    - bez_pary: [stary] - brak odpowiednika w grafice,
    - zgodne: liczba rekordów z adresem obecnym w grafice."""
    graf = {str(a) for a in adresy_grafiki if a}
    graf |= {adres_oddzialu(a) for a in list(graf)}
    wg_klucza = defaultdict(set)
    for a in graf:
        wg_klucza[bez_grupy(a)].add(a)

    wynik = {'zmiany': [], 'kolizje': [], 'niejednoznaczne': [],
             'bez_pary': [], 'zgodne': 0}
    for adres, typ in sorted(adresy_bazy.items()):
        if typ not in TYPY or not grupa(adres).strip():
            continue
        if adres in graf:
            wynik['zgodne'] += 1
            continue
        kandydaci = sorted(wg_klucza.get(bez_grupy(adres), ()))
        if not kandydaci:
            wynik['bez_pary'].append(adres)
        elif len(kandydaci) > 1:
            wynik['niejednoznaczne'].append((adres, kandydaci))
        elif kandydaci[0] in adresy_bazy:
            wynik['kolizje'].append((adres, kandydaci[0]))
        else:
            wynik['zmiany'].append((adres, kandydaci[0]))
    return wynik


def bledy_grup(przypisania):
    """przypisania: [(klucz_wydz, grupa_wydz, grupa_ls)] dla przecięć WYDZ x
    LS. Zwraca (na_kilku, rozne): na_kilku - {klucz: {grupy LS}} dla
    wydzieleń leżących na >1 grupie LS; rozne - {klucz: (grupa_wydz,
    {grupy LS})} dla wydzieleń na jednej grupie LS, innej niż ich własna."""
    grupy_ls = defaultdict(set)
    wlasna = {}
    for klucz, gw, gl in przypisania:
        grupy_ls[klucz].add(str(gl))
        wlasna[klucz] = str(gw)
    na_kilku = {k: g for k, g in grupy_ls.items() if len(g) > 1}
    rozne = {k: (wlasna[k], g) for k, g in grupy_ls.items()
             if len(g) == 1 and wlasna[k] not in g}
    return na_kilku, rozne
