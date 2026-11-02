# -*- coding: utf-8 -*-
"""Dane zakładki Ewidencja Edytora opisu. Bez QGIS-a:
    py testy/test_opis_ewidencja.py   (z katalogu wtyczki)"""
import importlib.util
import os
import sys
import types
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKRYPTY = os.path.join(KATALOG, 'skrypty')


def _modul(nazwa, pakiet):
    spec = importlib.util.spec_from_file_location(
        f'{pakiet}.{nazwa}', os.path.join(SKRYPTY, nazwa + '.py'))
    modul = importlib.util.module_from_spec(spec)
    sys.modules[f'{pakiet}.{nazwa}'] = modul
    spec.loader.exec_module(modul)
    return modul


# moduł używa importu względnego - pakiet bez skrypty/__init__.py (QGIS)
PAKIET = '_test_ew'
_p = types.ModuleType(PAKIET)
_p.__path__ = [SKRYPTY]
sys.modules[PAKIET] = _p
_modul('spakuj_do_opiniowania_pliki', PAKIET)
d = _modul('opis_ewidencja_dane', PAKIET)


def ewidencja(rozliczenie=True, nazwa1='Łukasik'):
    dzialki = [
        # pid, nr, district, municip, community, jr, arkusz
        (1, '10/2', '03', '042', '0001', 'G10', None),
        (2, '2', '03', '042', '0001', 'G10', None),
        (3, '5', '03', '042', '0002', 'G10', '3'),   # ta sama JR, inny obręb
        (4, '9', '03', '042', '0002', 'G77', None),
    ]
    uzytki = [(1, 1, 'V', 'Ls', 0.5), (1, 2, 'VI', 'Ls', 0.25),
              (2, 1, 'IV', 'Ls', 1.0), (3, 1, 'V', 'Ls', 0.3),
              (4, 1, None, 'Ł', 0.1)]
    rozl = [(1, 1, 100, 0.5), (1, 2, 101, 0.25), (2, 1, 100, 1.0),
            (3, 1, 101, 0.3)] if rozliczenie else []
    udzialy = [
        # addr, działka, licznik, mianownik, drugi, rodzaj
        (1, 1, 1, 2, 2, 'WL'), (1, 2, 1, 2, 2, 'WL'),  # wspólny wpis
        (3, 1, 1, 2, 0, 'WD'), (3, 2, 1, 2, 0, 'WD'),
        (3, 3, 1.0, 1.0, 0, 'WL'), (4, 4, 1, 1, 0, 'WL'),
    ]
    adresy = [(1, nazwa1, 'Jan', 'Dębica'), (2, nazwa1, 'Anna', 'Dębica'),
              (3, 'Nowak', 'Żaneta', 'Brody'), (4, 'Gmina Brody', None, None),
              (5, 'Bez działek', 'X', None)]
    obreby = {'030420001': 'Brody', '030420002': 'Łaziska'}
    return d.Ewidencja(dzialki, uzytki, rozl, udzialy, adresy, obreby)


class TestWidokWydzielenia(unittest.TestCase):
    def test_dzialki_z_klasouzytkiem_i_rozliczeniem(self):
        w = ewidencja().dzialki_wydzielenia(100)
        self.assertEqual(
            [(x['dzialka'], x['uzytek'], x['pow_uzytku'], x['rozliczona'])
             for x in w],
            [('2', 'LsIV', 1.0, 1.0), ('10/2', 'LsV', 0.5, 0.5)])

    def test_arkusz_w_numerze_dzialki(self):
        w = ewidencja().dzialki_wydzielenia(101)
        self.assertIn('3.5', [x['dzialka'] for x in w])

    def test_wlasciciele_bez_dubli_z_kilku_dzialek(self):
        w = ewidencja().wlasciciele_wydzielenia(100)
        self.assertEqual(
            [(x['jr'], x['wlasciciel'], x['udzial'], x['rodzaj'], x['miejsc'])
             for x in w],
            [('G10', 'Łukasik Jan i Łukasik Anna', '1/2', 'WL', 'Dębica'),
             ('G10', 'Nowak Żaneta', '1/2', 'WD', 'Brody')])

    def test_ta_sama_jr_w_innym_obrebie_osobno(self):
        w = ewidencja().wlasciciele_wydzielenia(101)
        self.assertEqual(sorted((x['udzial']) for x in w if
                                x['wlasciciel'] == 'Nowak Żaneta'),
                         ['1/1', '1/2'])

    def test_udzial_liczby_float(self):
        self.assertEqual(d.udzial(1.0, 6.0), '1/6')
        self.assertEqual(d.udzial(None, None), '')

    def test_nieznane_wydzielenie_puste(self):
        e = ewidencja()
        self.assertEqual(e.dzialki_wydzielenia(999), [])
        self.assertEqual(e.wlasciciele_wydzielenia(999), [])


class TestWyszukiwanie(unittest.TestCase):
    def setUp(self):
        self.e = ewidencja()
        self.wl = self.e.podpowiedzi_wlascicieli()
        self.dz = self.e.podpowiedzi_dzialek()

    def test_bez_polskich_i_wielkosci_liter(self):
        t = [p.tekst for p in d.filtruj(self.wl, 'zaneta')]
        self.assertEqual(t, ['Nowak Żaneta, Brody'])

    def test_kazde_slowo_gdziekolwiek(self):
        t = [p.tekst for p in d.filtruj(self.wl, 'brody nowak')]
        self.assertEqual(t, ['Nowak Żaneta, Brody'])

    def test_kilka_wydzielen(self):
        p = d.filtruj(self.wl, 'nowak')[0]
        self.assertEqual(self.e.wydzielenia_pozycji(p), {100, 101})
        self.assertTrue(p.etykieta.endswith('[2 wydz.]'))

    def test_druga_osoba_wpisu_znajduje_wydzielenie(self):
        p = d.filtruj(self.wl, 'anna')[0]
        self.assertEqual(p.tekst, 'Łukasik Anna, Dębica')
        self.assertEqual(self.e.wydzielenia_pozycji(p), {100, 101})

    def test_wlasciciel_bez_dzialek_nie_ma_podpowiedzi(self):
        self.assertEqual(d.filtruj(self.wl, 'bez dzialek'), [])

    def test_instytucja_bez_imienia_i_miejscowosci(self):
        self.assertEqual(d.filtruj(self.wl, 'gmina')[0].etykieta,
                         'Gmina Brody [0 wydz.]')

    def test_dzialka_z_nazwa_obrebu(self):
        p = d.filtruj(self.dz, 'laziska 9')[0]
        self.assertEqual(p.etykieta, '0002 Łaziska - 9 [0 wydz.]')
        self.assertEqual(self.e.wydzielenia_pozycji(p), set())

    def test_szukanie_po_obrebie(self):
        self.assertEqual(len(d.filtruj(self.dz, '0001')), 2)
        self.assertEqual(len(d.filtruj(self.dz, '000')), 4)

    def test_dokladny_numer_przed_dluzszymi(self):
        poz = [d.Pozycja(f'0001 Brody - {n}', {1})
               for n in ('140', '14/1', '14', '2')]
        self.assertEqual([p.tekst for p in d.filtruj(poz, '14')][0],
                         '0001 Brody - 14')
        self.assertEqual(len(d.filtruj(poz, '14')), 3)

    def test_dokladna_pozycja(self):
        poz = [d.Pozycja('0001 Brody - 14', {1}),
               d.Pozycja('0001 Brody - 14/1', {1})]
        self.assertIs(d.dokladna(poz, '0001 brody - 14'), poz[0])
        self.assertIsNone(d.dokladna(poz, '14'))

    def test_puste_szukanie_i_limit(self):
        self.assertEqual(d.filtruj(self.dz, ''), [])
        self.assertEqual(len(d.filtruj(self.dz, '000', limit=2)), 2)


class TestStanBazy(unittest.TestCase):
    def test_nierozliczona(self):
        e = ewidencja(rozliczenie=False)
        self.assertFalse(e.rozliczona)
        self.assertTrue(all(p.etykieta.endswith('[0 wydz.]')
                            for p in e.podpowiedzi_dzialek()))

    def test_anonimowa_tylko_gdy_wszyscy(self):
        self.assertFalse(ewidencja().anonimowa)
        e = d.Ewidencja([], [], [], [], [(1, 'NAZWISKO', 'IMIE', 'M'),
                                         (2, 'NAZWISKO', 'IMIE', 'M')], {})
        self.assertTrue(e.anonimowa)


if __name__ == '__main__':
    unittest.main()
