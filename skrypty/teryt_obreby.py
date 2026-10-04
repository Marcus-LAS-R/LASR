# -*- coding: utf-8 -*-
"""Słownik obrębów ewidencyjnych TERYT (cała Polska) dołączony do wtyczki.

Plik szablony/teryt_obreby.csv (UTF-8, separator ';', nagłówek):
    id_obr;nazwa_obr;nazwa_gmi;jedn_ewid
np. 121108_2.0007;Niedzica;Łapsze Niżne;ŁAPSZE NIŻNE
id_obr ma ten sam format co początek idDzialki w GML EGiB
(WWPPGG_R.OOOO), więc działkę łączy się z obrębem bez konwersji.

Źródło: słownik programu MAPA_m6 (C:\\ProgramData\\MAPA_m6\\teryt.dat,
SQLite, tabela obreby; program aktualizuje go z
softline.geo.pl/pliki/teryt_obr.zip). Odświeżenie słownika we wtyczce:
    wygeneruj_z_mapa_m6(r'C:\\ProgramData\\MAPA_m6\\teryt.dat')
GML z EWMAPY (eksport "podstawowy/do modyfikacji") nie zawiera
EGB_ObrebEwidencyjny - nazwy obrębów trzeba brać stąd.
"""
import csv
import os
import sqlite3

SCIEZKA_CSV = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'szablony', 'teryt_obreby.csv')

_NAGLOWEK = ['id_obr', 'nazwa_obr', 'nazwa_gmi', 'jedn_ewid']

_cache = None


def wczytaj(sciezka=SCIEZKA_CSV):
    """{id_obr: (nazwa_obr, nazwa_gmi, jedn_ewid)}; pusty dict, gdy brak
    pliku. Wynik dla domyślnej ścieżki jest zapamiętywany."""
    global _cache
    if sciezka == SCIEZKA_CSV and _cache is not None:
        return _cache
    slownik = {}
    if os.path.isfile(sciezka):
        with open(sciezka, encoding='utf-8', newline='') as plik:
            for wiersz in csv.DictReader(plik, delimiter=';'):
                slownik[wiersz['id_obr']] = (
                    wiersz['nazwa_obr'], wiersz['nazwa_gmi'],
                    wiersz['jedn_ewid'])
    if sciezka == SCIEZKA_CSV:
        _cache = slownik
    return slownik


def nazwa_obrebu(id_obr):
    """'121108_2.0007' -> 'Niedzica' albo None."""
    wpis = wczytaj().get(id_obr)
    return wpis[0] if wpis else None


def id_obrebu(county, district, municipality, community):
    """Kody jak w bazie (MUNICIPALITY_CD = gmina(2) + rodzaj(1)) ->
    id_obr TERYT, np. ('12','11','082','0007') -> '121108_2.0007'."""
    return '%s%s%s_%s.%s' % (county, district, municipality[:2],
                             municipality[2:], community)


def jednostka(teryt_jedn):
    """'121112_5' -> (nazwa_gmi, jedn_ewid) z dowolnego obrębu tej
    jednostki ewidencyjnej albo None."""
    prefiks = teryt_jedn + '.'
    for id_obr, (_obr, gmi, jedn) in wczytaj().items():
        if id_obr.startswith(prefiks):
            return gmi, jedn
    return None


def inne_rodzaje(id_obr):
    """Obręby o tym samym numerze w tej samej gminie, ale innym rodzaju
    gminy - podpowiedź przy kodzie spoza słownika (np. GML z
    '121112_2.0001', a w TERYT jest '121112_5.0001' Chabówka).
    Zwraca [(id_obr, nazwa_obr, jedn_ewid)]."""
    if len(id_obr) < 13 or id_obr[6] != '_':
        return []
    gmina, obreb = id_obr[:6], id_obr[8:]
    wynik = []
    for rodzaj in '12345':
        kandydat = '%s_%s%s' % (gmina, rodzaj, obreb)
        if kandydat == id_obr:
            continue
        wpis = wczytaj().get(kandydat)
        if wpis:
            wynik.append((kandydat, wpis[0], wpis[2]))
    return wynik


def wygeneruj_z_mapa_m6(sciezka_dat, sciezka_csv=SCIEZKA_CSV):
    """Ekstrakcja słownika z teryt.dat (SQLite MAPA_m6) do CSV wtyczki.
    Duplikaty id_obr: wygrywa nazwa nie zapisana samymi wielkimi literami
    (np. 'Baczyn' zamiast 'BACZYN'). Zwraca liczbę zapisanych obrębów."""
    global _cache
    con = sqlite3.connect('file:%s?mode=ro' % sciezka_dat.replace('\\', '/'),
                          uri=True)
    try:
        wiersze = con.execute(
            'SELECT id_obr, nazwa_obr, nazwa_gmi, jedn_ewid FROM obreby '
            'ORDER BY id').fetchall()
    finally:
        con.close()

    slownik = {}
    for id_obr, nazwa_obr, nazwa_gmi, jedn_ewid in wiersze:
        if not id_obr or not nazwa_obr:
            continue
        wpis = (nazwa_obr.strip(), (nazwa_gmi or '').strip(),
                (jedn_ewid or '').strip())
        stary = slownik.get(id_obr)
        if stary is None or (stary[0].isupper() and not wpis[0].isupper()):
            slownik[id_obr] = wpis

    os.makedirs(os.path.dirname(sciezka_csv), exist_ok=True)
    with open(sciezka_csv, 'w', encoding='utf-8', newline='') as plik:
        zapis = csv.writer(plik, delimiter=';', lineterminator='\n')
        zapis.writerow(_NAGLOWEK)
        for id_obr in sorted(slownik):
            zapis.writerow((id_obr,) + slownik[id_obr])
    _cache = None
    return len(slownik)
