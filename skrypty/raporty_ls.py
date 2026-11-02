# -*- coding: utf-8 -*-
"""Odczyt raportów Ls (ls_raport_*, ls_kontrola_*) leżących obok bazy, bez
QGIS-a: najnowszy raport i lista Ls-ów z sekcji BRAKUJĄCE LSy [W SHP].

Tylko ta sekcja mówi, że Ls-a nie ma w warstwie - pozostałe wymieniają Ls-y,
które w warstwie są (zdublowany LANDID, różnica powierzchni), albo te,
których nie ma w bazie."""
import os
import re

PRZEDROSTKI = ('ls_raport_', 'ls_kontrola_')

_SEKCJA = re.compile(r'^-+BRAKUJ.*LSy \[W SHP\]-*\s*$', re.IGNORECASE)
_KONIEC = re.compile(r'^-{10,}\s*$')


def najnowszy_raport(katalog):
    """Ścieżka najnowszego raportu Ls w katalogu (wg daty modyfikacji) albo
    None. Raporty/Archiwum nie jest przeglądane."""
    try:
        nazwy = os.listdir(katalog)
    except OSError:
        return None
    pliki = [os.path.join(katalog, n) for n in nazwy
             if n.startswith(PRZEDROSTKI) and n.lower().endswith('.txt')]
    pliki = [p for p in pliki if os.path.isfile(p)]
    return max(pliki, key=os.path.getmtime) if pliki else None


def _tekst(sciezka):
    with open(sciezka, 'rb') as f:
        dane = f.read()
    try:
        return dane.decode('utf-8')
    except UnicodeDecodeError:
        return dane.decode('cp1250', errors='replace')


def brakujace_w_shp(sciezka):
    """Zbiór LANDID (wielkimi literami) z sekcji BRAKUJĄCE LSy [W SHP]."""
    wyn = set()
    w_sekcji = False
    for linia in _tekst(sciezka).splitlines():
        if not w_sekcji:
            w_sekcji = _SEKCJA.match(linia) is not None
        elif _KONIEC.match(linia):
            break
        elif '\t' in linia:
            wyn.add(linia.split('\t')[0].strip().upper())
    return wyn


def brakujace_obok_bazy(katalog_bazy):
    """Zbiór brakujących Ls-ów z najnowszego raportu albo None, gdy raportu
    nie ma lub nie da się go odczytać."""
    sciezka = najnowszy_raport(katalog_bazy)
    if sciezka is None:
        return None
    try:
        return brakujace_w_shp(sciezka)
    except OSError:
        return None
