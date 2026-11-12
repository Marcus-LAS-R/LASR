# -*- coding: utf-8 -*-
"""Klepanie opisów z kart pomiarowych w Edytorze opisu.

Raport kart do klepania (raport_nr_robocze.xlsx ze "Stwórz raport kart do
klepania", arkusz "Raport kart") -> waypointy Nawigatora w kolejności kart
taksatorów (kod taksatora, potem numer: TK-2, TK-10, SS-1...). Plik
postępu (CSV obok raportu) pamięta wklepane karty - ponowne wczytanie
raportu wraca do pierwszej niewklepanej.

Bez Qt/QGIS - testy: testy/test_klepanie.py.
"""
import glob
import os
import re

from . import waypointy

ZRODLO = 'Klepanie'
SEKCJA = 'Klepanie kart'
ARKUSZ = 'Raport kart'
STATUS_ZROBIONE = 'ZROBIONE'
STRZALKA = ' → '
WZORZEC_KLONOW = 'KLON_po_klepaniu*.txt'


def _t(wartosc):
    return '' if wartosc is None else str(wartosc).strip()


def bez_spacji(adr):
    return re.sub(r'\s+', '', _t(adr))


def klucz_karty(nr):
    """Sortowanie naturalne numeru karty: kod taksatora, potem liczby
    rosnąco (TK-2 przed TK-10)."""
    return [(0, int(c), '') if c.isdigit() else (1, 0, c.lower())
            for c in re.findall(r'\d+|\D+', _t(nr))]


def _bez_karty(nr):
    """'---' (wydzielenie bez karty) albo pusty numer."""
    return re.fullmatch(r'[-\s]*', _t(nr)) is not None


def czesci_adresu(adr):
    """(gmina, obręb, oddział, wydzielenie) z ADR_LES - te same wycinki co
    w raporcie kart (shp_sprawdz_ciecie.raport_spis_kart), bez spacji
    dopełnienia (oddział '1   ' w adresie, '1' w odczytanym raporcie)."""
    adr = '' if adr is None else str(adr)
    return tuple(adr[a:b].strip() for a, b in ((3, 6), (6, 10), (13, 17),
                                                (18, 20)))


def czytaj_raport(sciezka):
    """Karty z arkusza "Raport kart": [{nr, adr, czesci, obr, klonow}].
    Wiersze bez karty ('---') pominięte; stary raport (bez ADR_LES) - adr
    pusty, do dopasowania (dopasuj_adresy)."""
    import openpyxl
    wb = openpyxl.load_workbook(sciezka, read_only=True, data_only=True)
    try:
        ws = wb[ARKUSZ] if ARKUSZ in wb.sheetnames else wb.worksheets[0]
        wiersze = ws.iter_rows(values_only=True)
        naglowki = [_t(x).upper() for x in next(wiersze, ())]
        if 'NR_ROBO' not in naglowki:
            raise ValueError('brak kolumny NR_ROBO - to nie jest raport kart '
                             'do klepania')
        idx = {n: i for i, n in enumerate(naglowki) if n}

        def pole(w, nazwa):
            i = idx.get(nazwa)
            return _t(w[i]) if i is not None and i < len(w) else ''

        karty = []
        for w in wiersze:
            nr = pole(w, 'NR_ROBO')
            if _bez_karty(nr):
                continue
            klonow = pole(w, 'ILE_KLONOW')
            karty.append({
                'nr': nr,
                'adr': pole(w, 'ADR_LES'),
                'czesci': (pole(w, 'MUNICIP'), pole(w, 'COMMUNITY'),
                           pole(w, 'ODDZ'), pole(w, 'WYDZ')),
                'obr': pole(w, 'OBR'),
                'klonow': int(float(klonow)) if klonow else 0,
            })
        return karty
    finally:
        wb.close()


def dopasuj_adresy(karty, adresy):
    """Karty bez ADR_LES (stary raport) - adres z warstwy po częściach
    adresu (gmina, obręb, oddział, wydzielenie), gdy pasuje dokładnie jeden.
    Zwraca (karty z adresem, karty bez adresu)."""
    po_czesciach = {}
    for adr in adresy:
        po_czesciach.setdefault(czesci_adresu(adr), []).append(_t(adr))
    z_adresem, bez = [], []
    for k in karty:
        if not k['adr']:
            pasujace = po_czesciach.get(tuple(k['czesci']), [])
            if len(pasujace) == 1:
                k = dict(k, adr=pasujace[0])
        (z_adresem if k['adr'] else bez).append(k)
    return z_adresem, bez


def nr_z_obiektu(obiekt):
    return _t(obiekt).split(STRZALKA.strip())[0].strip()


def wiersze_waypointow(karty, stare=()):
    """Waypointy w kolejności kart; status z poprzedniego pliku postępu
    (para numer karty + adres)."""
    postep = {(nr_z_obiektu(w.get('obiekt')), bez_spacji(w.get('klucz'))):
              (w.get('status', ''), w.get('data_oznaczenia', ''))
              for w in stare if w.get('zrodlo') == ZRODLO}
    wyn = []
    for k in sorted(karty, key=lambda x: klucz_karty(x['nr'])):
        adr = _t(k['adr'])
        if k['klonow']:
            uwagi = (f'wzorzec - po klepaniu sklonuj do {k["klonow"]} '
                     'wydz. (KLON_po_klepaniu)')
        else:
            uwagi = 'do wklepania'
        szczegoly = f'Karta: {k["nr"]}\nAdres leśny: {adr}'
        if k['obr'] and k['obr'] != '---':
            szczegoly += f'\nObręb: {k["obr"]}'
        w = waypointy.wiersz(
            ZRODLO, SEKCJA, 'ADR_LES', adr, szczegoly,
            obiekt=k['nr'] + STRZALKA + bez_spacji(adr), blad=uwagi)
        status, data = postep.get((k['nr'], bez_spacji(adr)), ('', ''))
        w['status'], w['data_oznaczenia'] = status, data
        wyn.append(w)
    return wyn


def sciezka_postepu(sciezka_raportu):
    """Plik postępu obok raportu - ten sam przy ponownym wczytaniu."""
    return os.path.splitext(sciezka_raportu)[0] + '_klepanie.csv'


def pliki_klonow(katalog):
    return sorted(glob.glob(os.path.join(katalog, WZORZEC_KLONOW)))
