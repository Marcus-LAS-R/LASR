# -*- coding: utf-8 -*-
"""Podziel obiekt (Gminami / Obrębami) - część bez QGIS-a: grupowanie
obrębów w jednostki, nazwy folderów, przydział obrębów i raport.

Klucz obrębu: (COUNTY, DISTRICT, MUNICIP, COMMUNITY), np.
('30', '17', '035', '0002'). Grupa (jednostka):
  - GMINY:  COUNTY+DISTRICT+MUNICIP, np. '3017035' (TERYT 301703 + typ 5;
            każdy MUNICIPALITY_CD osobno - miasto 034 i obszar wiejski 035
            to dwie gminy),
  - OBREBY: gmina + '.' + COMMUNITY, np. '3017035.0002'.
Foldery: 301703_5_Odolanow_OW, 301703_5.0002_Garki (jak 121505_2.0003_Osielec).
"""
import os
import re

try:
    from . import przygotuj_na_wylozenia_pliki as pw
    from . import spakuj_do_opiniowania_pliki as sp
except ImportError:
    import przygotuj_na_wylozenia_pliki as pw
    import spakuj_do_opiniowania_pliki as sp

GMINY = 'gminy'
OBREBY = 'obreby'

POMIN = 'POMIN'  # obręby jednostek niezaznaczonych - nie trafiają nigdzie
FOLDER_SHP = 'SHP'

# (tytuł, nagłówek raportu, mianownik, dopełniacz l.mn., "innej ...")
OPISY = {
    GMINY: ('Podziel obiekt - gminami', 'GMINY', 'gmina', 'gmin',
            'innej gminy'),
    OBREBY: ('Podziel obiekt - obrębami', 'OBRĘBY', 'obręb', 'obrębów',
             'innego obrębu'),
}

# typ gminy (ostatnia cyfra TERYT) -> przyrostek folderu; gmina wiejska
# bez przyrostka (jak 120509_2_Sekowa)
PRZYROSTKI = {'1': 'M', '2': '', '3': 'MW', '4': 'M', '5': 'OW',
              '8': 'DZ', '9': 'DEL'}


def _gmina_klucza(klucz):
    if not klucz or len(klucz) < 3:
        return None
    county, district, municip = (str(x or '').strip() for x in klucz[:3])
    g = county + district + municip
    return g if len(g) == 7 and g.isdigit() else None


def grupa_obrebu(klucz, tryb=GMINY):
    """('30', '17', '035', '0002') -> '3017035' (GMINY) albo
    '3017035.0002' (OBREBY); None dla niepełnego klucza."""
    g = _gmina_klucza(klucz)
    if g is None or tryb == GMINY:
        return g
    com = str(klucz[3] or '').strip() if len(klucz) > 3 else ''
    return f'{g}.{com}' if len(com) == 4 and com.isdigit() else None


def teryt6(grupa):
    return grupa[:6]


def typ_gminy(grupa):
    return grupa[6:7]


def grupa_z_id(tekst, tryb=GMINY):
    """Identyfikator z GMIN.shp/OBR.shp ('301703_5', '301703_5.0002')
    -> grupa ('3017035', '3017035.0002')."""
    cyfry = ''.join(c for c in str(tekst or '') if c.isdigit())
    if tryb == GMINY:
        return cyfry[:7] if len(cyfry) >= 7 else None
    return f'{cyfry[:7]}.{cyfry[7:11]}' if len(cyfry) >= 11 else None


# 'Ozimek - miasto', 'Ozimek Obszar wiejski' (F_MUNICIPALITY, PRG)
_TYP_W_NAZWIE = re.compile(
    r'(\s*[-–(]\s*|\s+)(miasto|obszar\s+wiejski|gmina(\s+(miejska|wiejska|'
    r'miejsko-wiejska))?)\s*\)?\s*$', re.IGNORECASE)


def _nazwa_obrebu(tekst):
    """'Nowa Wieś Mała' -> 'Nowa_Wies_Mala'."""
    tekst = sp.bez_polskich(str(tekst or '').strip())
    return re.sub(r'[^A-Za-z0-9-]+', '_', tekst).strip('_')


def folder_jednostki(grupa, nazwa, tryb=GMINY):
    """GMINY:  '3017035', 'Gmina Odolanów' -> '301703_5_Odolanow_OW';
               'Ozimek - miasto' -> '160908_4_Ozimek_M'.
    OBREBY: '3017035.0002', 'Garki' -> '301703_5.0002_Garki'."""
    if tryb == OBREBY:
        czesci = [f'{teryt6(grupa)}_{typ_gminy(grupa)}.{grupa[8:]}']
        n = _nazwa_obrebu(nazwa)
        if n:
            czesci.append(n)
        return '_'.join(czesci)
    czesci = [teryt6(grupa), typ_gminy(grupa)]
    n = pw.nazwa_gminy(_TYP_W_NAZWIE.sub('', str(nazwa or '')))
    if n:
        czesci.append(n)
    przyrostek = PRZYROSTKI.get(typ_gminy(grupa), '')
    if przyrostek:
        czesci.append(przyrostek)
    return '_'.join(czesci)


class Jednostka:
    def __init__(self, grupa, tryb=GMINY):
        self.grupa = grupa
        self.tryb = tryb
        self.nazwa = ''
        self.obreby = set()
        self.dzialki = 0
        self.w_bazie = False
        self.w_shp = False

    @property
    def folder(self):
        return folder_jednostki(self.grupa, self.nazwa, self.tryb)

    @property
    def zrodla(self):
        z = []
        if self.w_bazie:
            z.append('baza')
        if self.w_shp:
            z.append('SHP')
        return ', '.join(z)


def zbierz(obreby_bazy=(), klucze_shp=(), nazwy=None, tryb=GMINY):
    """obreby_bazy: [(klucz, nazwa gminy, nazwa obrębu, działek)] z bazy,
    klucze_shp: klucze obrębów znalezione w warstwach SHP,
    nazwy: {grupa: nazwa} (GMIN.shp/OBR.shp) - gdy baza nie ma nazwy.
    Zwraca {grupa: Jednostka} i listę kluczy bez poprawnego kodu."""
    nazwy = nazwy or {}
    jedn, zle = {}, []

    def _j(klucz):
        g = grupa_obrebu(klucz, tryb)
        if g is None:
            zle.append(klucz)
            return None
        if g not in jedn:
            jedn[g] = Jednostka(g, tryb)
        return jedn[g]

    for klucz, n_gminy, n_obrebu, dzialki in obreby_bazy:
        j = _j(klucz)
        if j is None:
            continue
        j.obreby.add(tuple(klucz))
        j.dzialki += dzialki or 0
        j.w_bazie = True
        nazwa = n_obrebu if tryb == OBREBY else n_gminy
        if nazwa and not j.nazwa:
            j.nazwa = nazwa
    for klucz in klucze_shp:
        j = _j(klucz)
        if j is None:
            continue
        j.obreby.add(tuple(klucz))
        j.w_shp = True
    for g, j in jedn.items():
        if not j.nazwa:
            j.nazwa = nazwy.get(g, '')
    return jedn, zle


def przydzial(jedn, wybrane):
    """{klucz obrębu: grupa} - obręby jednostek niezaznaczonych -> POMIN."""
    wynik = {}
    for g, j in jedn.items():
        for k in j.obreby:
            wynik[k] = g if g in wybrane else POMIN
    return wynik


def domyslnie_wybrane(jedn):
    """Gdy są jednostki z bazy - tylko one (jednostki wyłącznie z SHP to
    zwykle sąsiedzi z warstw EGiB); bez bazy - wszystkie."""
    z_bazy = {g for g, j in jedn.items() if j.w_bazie}
    return z_bazy or set(jedn)


def foldery_wynikowe(katalog, jedn, wybrane):
    return {g: os.path.join(katalog, jedn[g].folder) for g in wybrane}


def istniejace(foldery, nazwa_bazy=None, z_shp=False):
    """Pliki/foldery wynikowe, które zostaną nadpisane."""
    wyn = []
    for kat in foldery.values():
        if nazwa_bazy and os.path.exists(os.path.join(kat, nazwa_bazy)):
            wyn.append(os.path.join(kat, nazwa_bazy))
        if z_shp and os.path.exists(os.path.join(kat, FOLDER_SHP)):
            wyn.append(os.path.join(kat, FOLDER_SHP))
    return wyn


def tekst_raportu(zrodla, jedn, wybrane, foldery, wyniki_baz=None,
                  analiza=None, raport_grafiki=None, uwagi=(), tryb=GMINY):
    """Treść raportu txt. wyniki_baz {grupa: (ścieżka|komunikat, liczniki
    |None)}, raport_grafiki - wiersze z rozdziel.podziel_grafike."""
    tytul, naglowek, _, mn, innej = OPISY[tryb]
    L = [tytul.upper(), '']
    for etykieta, wartosc in zrodla:
        L.append(f'{etykieta}: {wartosc or "-"}')
    L += ['', naglowek]
    for g in sorted(jedn):
        j = jedn[g]
        if g not in wybrane:
            L.append(f'  {j.folder} - pominięto (niezaznaczone), '
                     f'{len(j.obreby)} obr.')
            continue
        wiersz = f'  {j.folder} - {len(j.obreby)} obr., {j.dzialki} dz.'
        if analiza:
            wiersz += f', {analiza["liczba_wydz"].get(g, 0)} wydz.'
        L.append(wiersz)
        L.append(f'      folder: {foldery[g]}')
        if wyniki_baz and g in wyniki_baz:
            sc, licz = wyniki_baz[g]
            if licz is None:
                L.append(f'      BAZA: {sc}')
            else:
                L.append(
                    f'      baza: {sc} (usunięto: działek '
                    f'{licz["dzialki_usuniete"]}, wierszy F_ARODES '
                    f'{licz["arodes_usuniete"]}, właścicieli '
                    f'{licz["wlasciciele_usunieci"]})')

    if raport_grafiki:
        L += ['', f'WARSTWY SHP (liczba obiektów; obiekty bez rozpoznanego '
              f'obrębu trafiają do wszystkich {mn})']
        for nazwa, sposob, liczby, bez, blad in raport_grafiki:
            if blad:
                L.append(f'  {nazwa}: BŁĄD - {blad}')
                continue
            if not liczby:
                L.append(f'  {nazwa}: {sposob}')
                continue
            rozklad = ', '.join(f'{jedn[g].folder}: {n}'
                                for g, n in sorted(liczby.items()) if n)
            L.append(f'  {nazwa} [{sposob}]: {rozklad or "brak obiektów"}')
            if isinstance(bez, tuple) and any(bez):
                L.append(f'      bez obrębu: {bez[0]}, spoza listy obrębów: '
                         f'{bez[1]} (do wszystkich {mn})')

    if analiza:
        if analiza['nieprzypisane']:
            L += ['', 'WYDZIELENIA Z ADRESEM SPOZA ZNANYCH OBRĘBÓW '
                  '(zostają we wszystkich bazach)']
            L += ['  ' + a for a in analiza['nieprzypisane']]
        if analiza['konflikty']:
            L += ['', f'WYDZIELENIA ROZLICZONE NA DZIAŁKACH {innej.upper()} '
                  '(rozliczenie do ponownego wykonania)']
            for adr, g, obce in analiza['konflikty']:
                nazwa = jedn[g].folder if g in jedn else g
                L.append(f'  {adr} [{nazwa}]: {", ".join(obce)}')
        if analiza['rozliczenie_puste']:
            L += ['', 'Rozliczenie powierzchni wydzieleń (F_AROD_LAND_USE) '
                  'było puste - rozlicz powierzchnię w bazach wynikowych.']

    if uwagi:
        L += ['', 'UWAGI']
        L += ['  ' + u for u in uwagi]
    return '\n'.join(L) + '\n'
