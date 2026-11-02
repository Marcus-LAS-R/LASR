# -*- coding: utf-8 -*-
"""Edytor opisu, zakładka Ewidencja - dane bez Qt i QGIS-a (tylko odczyt).

Powiązanie wydzielenie-działka bierze się wyłącznie z rozliczenia
(F_AROD_LAND_USE): w bazie nierozliczonej działki i właściciele nie prowadzą
do żadnego wydzielenia. Jednostka rejestrowa jest unikalna tylko w obrębie.
Właściciele to wpisy V_PARCEL_PARTICIPATION z drugą osobą wspólnego wpisu
(second_addr_nr, małżonkowie) - wyszukiwanie działa po każdej z nich. W bazie
zanonimizowanej (BDO) wszyscy mają NAME_1 = NAZWISKO.
"""
import re

from .spakuj_do_opiniowania_pliki import bez_polskich

NAZWA_ANONIMOWA = 'NAZWISKO'
LIMIT_PODPOWIEDZI = 100


def _t(wartosc):
    return '' if wartosc is None else str(wartosc).strip()


def klucz_naturalny(tekst):
    """Sortowanie z liczbami: 2/1 przed 10, G9 przed G10."""
    return [(0, int(c), '') if c.isdigit() else (1, 0, c.lower())
            for c in re.findall(r'\d+|\D+', _t(tekst))]


def znormalizuj(tekst):
    return bez_polskich(_t(tekst)).upper()


def pasuje_do_szukania(klucz, szukane):
    """Każde słowo szukanego tekstu występuje gdziekolwiek w kluczu."""
    return all(s in klucz for s in znormalizuj(szukane).split())


def udzial(licznik, mianownik):
    if licznik in (None, '') and mianownik in (None, ''):
        return ''
    return f'{_t(_liczba(licznik))}/{_t(_liczba(mianownik))}'


def _liczba(v):
    return int(v) if isinstance(v, float) and v == int(v) else v


def _nazwa(adres):
    return ' '.join(x for x in (adres['nazwa1'], adres['nazwa2']) if x)


class Pozycja:
    """Podpowiedź wyszukiwarki: etykieta i działki, do których prowadzi."""

    def __init__(self, tekst, dzialki):
        self.tekst = tekst
        self.dzialki = set(dzialki)
        self.klucz = znormalizuj(tekst)
        self.etykieta = tekst


class Ewidencja:
    """Migawka tabel ewidencji. Argumenty - wiersze zapytań z wczytaj()."""

    def __init__(self, dzialki, uzytki, rozliczenie, udzialy, adresy, obreby):
        self.obreby = obreby
        self.dzialki = {}
        for pid, nr, d, m, c, jr, ark in dzialki:
            nr, ark = _t(nr), _t(ark)
            self.dzialki[pid] = {
                'numer': f'{ark}.{nr}' if ark else nr,
                'obreb': _t(c), 'jr': _t(jr),
                'nazwa_obrebu': obreby.get(_t(d) + _t(m) + _t(c), ''),
            }
        self.uzytki = {(pid, sh): (_t(au) + _t(sq), pow_u)
                       for pid, sh, sq, au, pow_u in uzytki}
        self.rozliczenie = {}     # {aint: [(działka, nr użytku, pow.)]}
        self.wydz_dzialki = {}    # {działka: {aint}}
        for pid, sh, aint, pow_r in rozliczenie:
            self.rozliczenie.setdefault(aint, []).append((pid, sh, pow_r))
            self.wydz_dzialki.setdefault(pid, set()).add(aint)
        self.adresy = {a: {'nazwa1': _t(n1), 'nazwa2': _t(n2),
                           'miejsc': _t(pl)}
                       for a, n1, n2, pl in adresy}
        self.udzialy = {}         # {działka: [wpis]}
        for a, pid, li, mi, drugi, rodzaj in udzialy:
            self.udzialy.setdefault(pid, []).append(
                (a, li, mi, drugi, _t(rodzaj)))

    # ---------------------------------------------------------- stan bazy

    @property
    def rozliczona(self):
        return bool(self.rozliczenie)

    @property
    def anonimowa(self):
        return bool(self.adresy) and all(
            a['nazwa1'].upper() == NAZWA_ANONIMOWA
            for a in self.adresy.values())

    # ------------------------------------------------- widok wydzielenia

    def dzialki_wydzielenia(self, aint):
        """[{obreb, dzialka, jr, uzytek, pow_uzytku, rozliczona}]."""
        wyn = []
        for pid, sh, pow_r in self.rozliczenie.get(aint, []):
            d = self.dzialki.get(pid, {})
            uz, pow_u = self.uzytki.get((pid, sh), ('', None))
            wyn.append({
                'obreb': d.get('obreb', ''), 'dzialka': d.get('numer', ''),
                'jr': d.get('jr', ''), 'uzytek': uz, 'pow_uzytku': pow_u,
                'rozliczona': pow_r})
        return sorted(wyn, key=lambda w: (
            w['obreb'], klucz_naturalny(w['dzialka']), w['uzytek']))

    def wlasciciele_wydzielenia(self, aint):
        """[{jr, wlasciciel, udzial, rodzaj, miejsc}] - po jednym wierszu na
        wpis jednostki (te same wpisy na kilku działkach raz)."""
        wyn, byly = [], set()
        for pid in {x[0] for x in self.rozliczenie.get(aint, [])}:
            d = self.dzialki.get(pid, {})
            for a, li, mi, drugi, rodzaj in self.udzialy.get(pid, []):
                klucz = (d.get('obreb'), d.get('jr'), a, drugi, li, mi, rodzaj)
                if klucz in byly:
                    continue
                byly.add(klucz)
                adr = self.adresy.get(a, {'nazwa1': '', 'nazwa2': '',
                                          'miejsc': ''})
                nazwa = _nazwa(adr)
                if drugi and drugi in self.adresy:
                    nazwa += ' i ' + _nazwa(self.adresy[drugi])
                wyn.append({'jr': d.get('jr', ''), 'wlasciciel': nazwa,
                            'udzial': udzial(li, mi), 'rodzaj': rodzaj,
                            'miejsc': adr['miejsc']})
        return sorted(wyn, key=lambda w: (klucz_naturalny(w['jr']),
                                          znormalizuj(w['wlasciciel']),
                                          w['udzial']))

    # -------------------------------------------------------- wyszukiwanie

    def _wydzielenia(self, dzialki):
        wyn = set()
        for pid in dzialki:
            wyn |= self.wydz_dzialki.get(pid, set())
        return wyn

    def _z_licznikiem(self, poz):
        for p in poz:
            p.etykieta = f'{p.tekst} [{len(self._wydzielenia(p.dzialki))} wydz.]'
        return sorted(poz, key=lambda p: klucz_naturalny(p.tekst))

    def podpowiedzi_wlascicieli(self):
        """Ta sama nazwa i miejscowość to jedna pozycja (kilka ADDR_NR)."""
        grupy = {}
        for pid, wpisy in self.udzialy.items():
            for a, _li, _mi, drugi, _r in wpisy:
                for osoba in (a, drugi):
                    adr = self.adresy.get(osoba)
                    if adr is None or not adr['nazwa1']:
                        continue
                    tekst = _nazwa(adr)
                    if adr['miejsc']:
                        tekst += ', ' + adr['miejsc']
                    grupy.setdefault(tekst, set()).add(pid)
        return self._z_licznikiem([Pozycja(t, d) for t, d in grupy.items()])

    def podpowiedzi_dzialek(self):
        grupy = {}
        for pid, d in self.dzialki.items():
            tekst = f"{d['obreb']} {d['nazwa_obrebu']} - {d['numer']}".replace(
                '  ', ' ')
            grupy.setdefault(tekst, set()).add(pid)
        return self._z_licznikiem([Pozycja(t, d) for t, d in grupy.items()])

    def wydzielenia_pozycji(self, pozycja):
        return self._wydzielenia(pozycja.dzialki)


def _calymi_slowami(klucz, szukane):
    """Każde szukane słowo jest całym słowem klucza (działka 14, nie 14/1
    ani 140)."""
    slowa = set(klucz.replace(',', ' ').split())
    return all(s in slowa for s in znormalizuj(szukane).split())


def filtruj(pozycje, szukane, limit=LIMIT_PODPOWIEDZI):
    """Pasujące pozycje, najpierw trafienia całymi słowami - dokładny numer
    działki nie ginie wśród dłuższych."""
    if not _t(szukane):
        return []
    wyn = [p for p in pozycje if pasuje_do_szukania(p.klucz, szukane)]
    wyn.sort(key=lambda p: not _calymi_slowami(p.klucz, szukane))
    return wyn[:limit]


def dokladna(pozycje, tekst):
    """Pozycja o dokładnie takiej etykiecie albo opisie (bez licznika)."""
    szukane = znormalizuj(tekst)
    return next((p for p in pozycje if szukane in (
        p.klucz, znormalizuj(p.etykieta))), None)


def wczytaj(cur):
    """Ewidencja z bazy; błąd odczytu leci do wywołującego."""
    def wiersze(sql):
        return [tuple(w) for w in cur.execute(sql).fetchall()]

    try:
        obreby = {_t(d) + _t(m) + _t(c): _t(n) for d, m, c, n in wiersze(
            'select DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD, COMMUNITY_NAME '
            'from F_COMMUNITY')}
    except Exception:
        obreby = {}
    return Ewidencja(
        wiersze('select PARCEL_INT_NUM, PARCEL_NR, DISTRICT_CD, '
                'MUNICIPALITY_CD, COMMUNITY_CD, LAND_REGISTER_NR, '
                'REG_SHEET_NR2 from F_PARCEL'),
        wiersze('select PARCEL_INT_NUM, SHAPE_NR, SOIL_QUALITY_CD, '
                'AREA_USE_CD, LAND_USE_AREA from F_PARCEL_LAND_USE'),
        wiersze('select PARCEL_INT_NUM, SHAPE_NR, ARODES_INT_NUM, '
                'AROD_LAND_USE_AREA from F_AROD_LAND_USE'),
        wiersze('select addr_nr, parcel_int_num, part_numerator, '
                'part_denominator, second_addr_nr, cwd '
                'from V_PARCEL_PARTICIPATION'),
        wiersze('select ADDR_NR, NAME_1, NAME_2, PLACE from V_ADDRESS'),
        obreby)
