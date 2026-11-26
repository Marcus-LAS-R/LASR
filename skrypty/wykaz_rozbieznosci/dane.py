# -*- coding: utf-8 -*-
"""Wykaz rozbieżności (dokumentacja geodezyjna) - pobranie danych z bazy
TPU i zbudowanie wierszy tabeli "stan stary (EGiB) / stan nowy (UPUL)".
Bez Qt - testowalne poza QGIS-em.

Reguły (odtworzone ze wzoru Łętownia, materialy/Wykaz rozbieznosci):
- w wykazie są działki, w których choć jeden klasoużytek Ls leży
  w wydzieleniu o rodzaju powierzchni z TYPY_ZMIANY (wyłączenia i Lz);
- działka wypisana w całości - pozostałe klasoużytki (B, Ps, R...) bez
  zmian (stan nowy = stan stary);
- klasoużytek Ls podzielony między wydzielenia daje kilka wierszy:
  najpierw części zmienione (po jednym wierszu na nowy klasoużytek
  i wyjaśnienie), potem część bez zmian (jeden wiersz, suma);
- kolejność w działce: najpierw klasoużytki ze zmianą, potem pozostałe,
  w obu grupach wg polskiego alfabetu;
- nowy klasoużytek: wg SLOWNIK_RODZAJOW (LZ-* -> Lz), dla INNE WYL wg
  SLOWNIK_INFO (GUR / grunt użytkowany rolniczo -> R + klasa Ls;
  budynki, zabudowania, podwórko -> B); bez dopasowania komórka pusta
  i żółta - do uzupełnienia ręcznie (w bazie nowego klasoużytku nie ma);
- wyjaśnienie zmian: F_SUBAREA.SUBAREA_INFO.
"""
import re

import re as _re

# --- SŁOWNIKI (do rozbudowy) -------------------------------------------
# rodzaj powierzchni (F_SUBAREA.AREA_TYPE_CD) -> nowy użytek (bez klasy)
SLOWNIK_RODZAJOW = {
    'LZ-Ł': 'Lz',
    'LZ-R': 'Lz',
    'LZ-Ps': 'Lz',
}
# INNE WYL: wzorce w informacjach różnych (SUBAREA_INFO, bez rozróżniania
# wielkości liter) -> (użytek, czy dopisać klasę Ls); pierwsza pasująca
# reguła wygrywa. Bez dopasowania - komórka pusta, na żółto, do
# uzupełnienia ręcznie.
SLOWNIK_INFO = (
    (r'\bgur\b|grunt\w* u[żz]ytkowan\w* rolniczo', 'R', True),
    (r'budyn|zabudow|podw[óo]rk', 'B', False),
)
# -----------------------------------------------------------------------

TYP_INNE_WYL = 'INNE WYL'
TYPY_ZMIANY = tuple(SLOWNIK_RODZAJOW) + (TYP_INNE_WYL,)
UZYTEK_LESNY = 'Ls'
TOLERANCJA = 0.00005  # ha - reszta Ls bez wydzielenia pomijana poniżej


def _t(x):
    return '' if x is None else str(x).strip()


def _f(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def klucz_dzialki(nr):
    """Sortowanie naturalne numerów działek: 9305 < 9364/1 < 12508/1."""
    return [(0, int(c), '') if c.isdigit() else (1, 0, c.lower())
            for c in re.split(r'(\d+)', _t(nr)) if c != '']


_ALFABET = ('-0123456789aąbcćdeęfghijklłmnńoóprsśtuvwxyzźż')


def klucz_pl(tekst):
    """Sortowanie wg polskiego alfabetu (ŁIV przed RV), bez locale."""
    return [(_ALFABET.find(z.lower()) if z.lower() in _ALFABET else 999,
             z.islower()) for z in tekst]


def klasouzytek_inne_wyl(info, klasa):
    """Nowy klasoużytek dla Ls wyłączonego jako INNE WYL wg SLOWNIK_INFO,
    '' gdy żadna reguła nie pasuje (do uzupełnienia ręcznie)."""
    tekst = _t(info).lower()
    for wzorzec, uzytek, z_klasa in SLOWNIK_INFO:
        if _re.search(wzorzec, tekst):
            return uzytek + (klasa if z_klasa else '')
    return ''


class Obreb:
    """Dane jednego obrębu do wykazu."""

    def __init__(self, klucz, woj, powiat, gmina, obreb, nazwa_gminy,
                 nazwa_powiatu, nazwa_obrebu):
        self.klucz = klucz          # (COUNTY, DISTRICT, MUNICIP, COMMUNITY)
        self.klucz_gminy = klucz[:3]
        self.nazwa_gminy = nazwa_gminy
        self.nazwa_powiatu = nazwa_powiatu
        self.nazwa_obrebu = nazwa_obrebu
        self.wiersze = []
        self.bazy = []
        self.dzialek = 0   # działek obrębu w bazie (0 - obręb pomijany)

    @property
    def kod(self):
        return ''.join(self.klucz)


class Wiersz:
    """Jeden wiersz tabeli (kolumny 1-6 wzoru)."""

    def __init__(self, gmina, obreb, nr, ku_stary, pow_stary, ku_nowy,
                 pow_nowy, wyjasnienie='', do_weryfikacji=False,
                 ksztalt=None):
        self.ksztalt = ksztalt   # SHAPE_NR klasoużytku (scalanie 4a/4b)
        self.gmina = gmina
        self.obreb = obreb
        self.nr = nr
        self.ku_stary = ku_stary
        self.pow_stary = pow_stary
        self.ku_nowy = ku_nowy
        self.pow_nowy = pow_nowy
        self.wyjasnienie = wyjasnienie
        self.do_weryfikacji = do_weryfikacji

    def komorki(self):
        return [self.gmina, self.obreb, self.nr, self.ku_stary,
                format_pow(self.pow_stary), self.ku_nowy,
                format_pow(self.pow_nowy), self.wyjasnienie]


def format_pow(x):
    return '{:.4f}'.format(x).replace('.', ',')


_SQL = {
    'obreby': '''
        SELECT c.COUNTY_CD, c.DISTRICT_CD, c.MUNICIPALITY_CD,
            c.COMMUNITY_CD, c.COMMUNITY_NAME, m.MUNICIPALITY_NAME,
            d.DISTRICT_NAME
        FROM (F_COMMUNITY c LEFT JOIN F_MUNICIPALITY m ON
            (c.COUNTY_CD = m.COUNTY_CD) AND (c.DISTRICT_CD = m.DISTRICT_CD)
            AND (c.MUNICIPALITY_CD = m.MUNICIPALITY_CD))
            LEFT JOIN F_DISTRICT d ON (c.COUNTY_CD = d.COUNTY_CD) AND
            (c.DISTRICT_CD = d.DISTRICT_CD)''',
    'dzialki': '''
        SELECT PARCEL_INT_NUM, PARCEL_NR, COUNTY_CD, DISTRICT_CD,
            MUNICIPALITY_CD, COMMUNITY_CD FROM F_PARCEL''',
    'uzytki': '''
        SELECT PARCEL_INT_NUM, SHAPE_NR, AREA_USE_CD, SOIL_QUALITY_CD,
            LAND_USE_AREA FROM F_PARCEL_LAND_USE''',
    'w_wydz': '''
        SELECT PARCEL_INT_NUM, SHAPE_NR, ARODES_INT_NUM, AROD_LAND_USE_AREA
        FROM F_AROD_LAND_USE''',
    'subarea': '''
        SELECT ARODES_INT_NUM, AREA_TYPE_CD, SUBAREA_INFO FROM F_SUBAREA''',
}


def pobierz(baza):
    """baza: obiekt z metodą pobierz(sql) (baza_wrapper.Baza po polacz()).
    Zwraca {klucz_obrebu: Obreb} z wierszami wykazu albo rzuca
    RuntimeError z nazwą tabeli, której nie dało się odczytać."""
    wyn = {}
    for nazwa, sql in _SQL.items():
        r = baza.pobierz(sql)
        if r is False:
            raise RuntimeError('nie można odczytać danych ({})'.format(
                nazwa))
        wyn[nazwa] = r
    return zbuduj(**wyn)


def zbuduj(obreby, dzialki, uzytki, w_wydz, subarea):
    """Czysta logika na krotkach z zapytań _SQL."""
    sl_obr = {}
    for c, d, m, o, n_obr, n_gm, n_pow in obreby:
        k = (_t(c), _t(d), _t(m), _t(o))
        sl_obr[k] = Obreb(k, *k, _t(n_gm), _t(n_pow), _t(n_obr).upper())

    rodzaj = {}
    for aid, typ, info in subarea:
        rodzaj.setdefault(aid, (_t(typ), _t(info)))

    uz_dz = {}
    for pid, shp, au, sq, pow_ in uzytki:
        uz_dz.setdefault(pid, []).append(
            (shp, _t(au), _t(sq), _f(pow_)))

    czesci = {}  # (pid, shape) -> [(typ, info, pow)]
    for pid, shp, aid, pow_ in w_wydz:
        typ, info = rodzaj.get(aid, ('', ''))
        czesci.setdefault((pid, shp), []).append((typ, info, _f(pow_)))

    for pid, nr, c, d, m, o in dzialki:
        k = (_t(c), _t(d), _t(m), _t(o))
        obr = sl_obr.get(k)
        if obr is None:
            obr = sl_obr[k] = Obreb(k, *k, '', '', '')
        obr.dzialek += 1
        klasouzytki = uz_dz.get(pid, [])
        zmienione = [u for u in klasouzytki if u[1] == UZYTEK_LESNY and any(
            cz[0] in TYPY_ZMIANY for cz in czesci.get((pid, u[0]), []))]
        if not zmienione:
            continue
        def kolejnosc(u):
            return (klucz_pl(u[1] + u[2]), u[0])

        reszta = sorted((u for u in klasouzytki if u not in zmienione),
                        key=kolejnosc)
        nr = _t(nr)
        for u in sorted(zmienione, key=kolejnosc):
            obr.wiersze.extend(_wiersze_klasouzytku(
                obr, nr, u, czesci.get((pid, u[0]), [])))
        for shp, au, sq, pow_ in reszta:
            obr.wiersze.append(Wiersz(obr.nazwa_gminy, obr.nazwa_obrebu, nr,
                                      au + sq, pow_, au + sq, pow_,
                                      ksztalt=shp))

    for obr in sl_obr.values():
        # stabilne sortowanie po numerze działki - kolejność klasoużytków
        # w działce zostaje
        obr.wiersze.sort(key=lambda w: klucz_dzialki(w.nr))
    return sl_obr


def _wiersze_klasouzytku(obr, nr, uzytek, czesci):
    shp, au, sq, pow_ = uzytek
    ku = au + sq
    zmiany = {}   # (nowy ku, wyjaśnienie, do_weryfikacji) -> pow
    bez_zmian = 0.0
    for typ, info, p in czesci:
        if typ in SLOWNIK_RODZAJOW:
            k = (SLOWNIK_RODZAJOW[typ], info, False)
        elif typ == TYP_INNE_WYL:
            nowy = klasouzytek_inne_wyl(info, sq)
            k = (nowy, info, nowy == '')
        else:
            bez_zmian += p
            continue
        zmiany[k] = zmiany.get(k, 0.0) + p
    poza = pow_ - bez_zmian - sum(zmiany.values())
    if poza > TOLERANCJA:   # część Ls bez wydzielenia - bez zmian
        bez_zmian += poza

    wiersze = [Wiersz(obr.nazwa_gminy, obr.nazwa_obrebu, nr, ku, pow_,
                      nowy, p, info, weryf, shp)
               for (nowy, info, weryf), p in zmiany.items()]
    if bez_zmian > TOLERANCJA:
        wiersze.append(Wiersz(obr.nazwa_gminy, obr.nazwa_obrebu, nr, ku,
                              pow_, ku, bez_zmian, ksztalt=shp))
    return wiersze
