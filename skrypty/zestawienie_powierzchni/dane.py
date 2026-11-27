# -*- coding: utf-8 -*-
"""Zestawienie powierzchni - odczyt z bazy (bez QGIS-a).

Odpowiednik kwerendy Access "TABELA 1 POW z pkt 1 , 3 i 4_POW_LS_WPISANE"
(łańcuch 8 kwerend) jako jedno zapytanie + sumowanie w Pythonie, dla
każdego obrębu (MUNICIPALITY_CD + COMMUNITY_CD z działki):
  pkt1 - użytki Ls wpisane do wydzieleń (F_PARCEL_LAND_USE.AREA_USE_CD = LS),
  pkt2 - użytki inne niż Ls wpisane do wydzieleń (lasy pozaewidencyjne),
  pkt3 - powierzchnia wydzieleń Lz (ADRESS_FOREST zawiera 'Lz') - liczona
         przez działkę, więc każdy obręb dostaje tylko swoją część (kwerenda
         Access dla Lz w kilku obrębach wlicza całość do każdego z nich),
  pkt4 - do rozliczenia = pkt1 + pkt2 - pkt3.
Działa na .mdb i .sqlite (bez kwerend zapisanych w bazie). Obręby z samymi
zerami są pomijane.
"""

# nazwy kolumn zestawienia (materialy/NAzwy_zestawienie.xlsx, ujednolicone)
KOLUMNY = (
    'Nr gminy',
    'Nazwa gminy',
    'Nr obrębu ewid.',
    'Nazwa obrębu ewid.',
    'Pow. użytków Ls [ha]',
    'Pow. lasów pozaewidencyjnych [ha]',
    'Pow. użytków do Lz (>0,1 ha) [ha]',
    'Pow. do rozliczenia [ha]',
)
KOLUMNY_POW = 4  # od tej kolumny (indeks) liczby [ha]

# F_PARCEL_LAND_USE dołączony LEFT JOIN - pkt3 (Lz) jak w kwerendzie Access
# liczy całe AROD_LAND_USE wydzielenia, także bez dopasowanego użytku
SQL_UZYTKI = '''
    select p.MUNICIPALITY_CD, p.COMMUNITY_CD, pl.AREA_USE_CD,
           a.ADRESS_FOREST, l.AROD_LAND_USE_AREA
    from ((F_AROD_LAND_USE as l
        inner join F_PARCEL as p on l.PARCEL_INT_NUM = p.PARCEL_INT_NUM)
        inner join F_ARODES as a on l.ARODES_INT_NUM = a.ARODES_INT_NUM)
        left join F_PARCEL_LAND_USE as pl on
            (pl.PARCEL_INT_NUM = l.PARCEL_INT_NUM) and
            (pl.SHAPE_NR = l.SHAPE_NR)
'''

SQL_NAZWY = '''
    select c.MUNICIPALITY_CD, c.COMMUNITY_CD, m.MUNICIPALITY_NAME,
           c.COMMUNITY_NAME
    from F_COMMUNITY as c inner join F_MUNICIPALITY as m on
        (c.COUNTY_CD = m.COUNTY_CD) and (c.DISTRICT_CD = m.DISTRICT_CD) and
        (c.MUNICIPALITY_CD = m.MUNICIPALITY_CD)
'''


def _kod(v):
    return '' if v is None else str(v).strip()


def _tekst(v):
    return '' if v is None else str(v).strip()


class Obreb:
    def __init__(self, nr_gminy, nr_obrebu):
        self.nr_gminy = nr_gminy
        self.nr_obrebu = nr_obrebu
        self.nazwa_gminy = ''
        self.nazwa_obrebu = ''
        self.ls = 0.0
        self.inne = 0.0
        self.lz = 0.0

    @property
    def klucz(self):
        return (self.nr_gminy, self.nr_obrebu)

    @property
    def do_rozliczenia(self):
        return self.ls + self.inne - self.lz

    def pusty(self):
        return not (round(self.ls, 4) or round(self.inne, 4) or
                    round(self.lz, 4))

    def wiersz(self):
        """Wiersz zestawienia w kolejności KOLUMNY."""
        return [self.nr_gminy, self.nazwa_gminy, self.nr_obrebu,
                self.nazwa_obrebu, round(self.ls, 4), round(self.inne, 4),
                round(self.lz, 4), round(self.do_rozliczenia, 4)]


def policz(uzytki, nazwy):
    """uzytki - wiersze SQL_UZYTKI, nazwy - wiersze SQL_NAZWY.
    Zwraca (lista Obreb bez pustych, posortowana po kodach; uwagi)."""
    obreby = {}
    for gm, obr, uzytek, adres, pow_ in uzytki:
        if not pow_:
            continue
        klucz = (_kod(gm), _kod(obr))
        o = obreby.get(klucz)
        if o is None:
            o = obreby[klucz] = Obreb(*klucz)
        pow_ = float(pow_)
        if uzytek is not None:
            if _tekst(uzytek).upper() == 'LS':
                o.ls += pow_
            else:
                o.inne += pow_
        if 'LZ' in _tekst(adres).upper():
            o.lz += pow_

    uwagi = []
    znane = {}
    for gm, obr, n_gm, n_obr in nazwy:
        znane.setdefault((_kod(gm), _kod(obr)), (_tekst(n_gm), _tekst(n_obr)))
    wynik = []
    for k in sorted(obreby):
        o = obreby[k]
        if o.pusty():
            continue
        if k in znane:
            o.nazwa_gminy, o.nazwa_obrebu = znane[k]
        else:
            uwagi.append('Brak obrębu {}/{} w F_COMMUNITY - bez nazwy'.format(
                *k))
        wynik.append(o)
    return wynik, uwagi


def pobierz(baza):
    """Obręby z podłączonej bazy (Baza z baza_wrapper albo obiekt z .cur)."""
    uzytki = baza.cur.execute(SQL_UZYTKI).fetchall()
    nazwy = baza.cur.execute(SQL_NAZWY).fetchall()
    return policz(uzytki, nazwy)


def nazwa_arkusza(obreby, zapasowa):
    """Baza z jednym obrębem -> nazwa obrębu, z jedną gminą -> nazwa gminy,
    w pozostałych przypadkach (albo bez nazwy) - zapasowa (folder bazy)."""
    if len(obreby) == 1 and obreby[0].nazwa_obrebu:
        return obreby[0].nazwa_obrebu
    gminy = {o.nr_gminy for o in obreby}
    if len(gminy) == 1 and obreby and obreby[0].nazwa_gminy:
        return obreby[0].nazwa_gminy
    return zapasowa
