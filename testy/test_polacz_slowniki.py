# -*- coding: utf-8 -*-
"""Kody spoza słowników przy łączeniu baz. Bez QGIS-a:
    py testy/test_polacz_slowniki.py   (z katalogu wtyczki)"""
import importlib.util
import os
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'baza_polacz_slowniki',
    os.path.join(KATALOG, 'skrypty', 'baza_polacz_slowniki.py'))
ps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ps)

UZYTEK = ps.SLOWNIKI[0]
OBR_A = ('18', '04', '08', '0001')
OBR_B = ('18', '04', '08', '0002')


class TestDolicz(unittest.TestCase):
    def test_kod_spoza_slownika_sumowany_miedzy_bazami(self):
        braki = {}
        ps.dolicz(braki, UZYTEK, {'ls'}, [OBR_A + ('Lzr-R', 2, 0.5)], 'a.mdb')
        ps.dolicz(braki, UZYTEK, {'ls'}, [OBR_A + ('Lzr-R', 3, 1.0)], 'b.mdb')
        brak = braki[('F_AREA_USE_DIC', 'lzr-r')]
        self.assertEqual((brak.ile, brak.ha), (5, 1.5))
        self.assertEqual(brak.bazy, {'a.mdb': 2, 'b.mdb': 3})

    def test_inna_wielkosc_liter_i_spacje_to_nie_brak(self):
        braki = {}
        ps.dolicz(braki, UZYTEK, {'dr', 'iiia'},
                  [OBR_A + ('Dr ', 1, 1.0), OBR_A + ('IIIa', 1, 1.0)], 'a.mdb')
        self.assertEqual(braki, {})

    def test_pusty_kod_to_nie_brak(self):
        braki = {}
        ps.dolicz(braki, UZYTEK, {'ls'},
                  [OBR_A + (None, 1, 1.0), OBR_A + ('  ', 1, 1.0)], 'a.mdb')
        self.assertEqual(braki, {})

    def test_obreb_spoza_wyboru_pominiety(self):
        braki = {}
        ps.dolicz(braki, UZYTEK, {'ls'},
                  [OBR_A + ('W-R', 1, 1.0), OBR_B + ('Br-R', 1, 1.0)],
                  'a.mdb', dozwolone={OBR_A})
        self.assertEqual(list(braki), [('F_AREA_USE_DIC', 'w-r')])

    def test_pusta_powierzchnia(self):
        braki = {}
        ps.dolicz(braki, UZYTEK, set(), [OBR_A + ('W-R', 1, None)], 'a.mdb')
        self.assertEqual(braki[('F_AREA_USE_DIC', 'w-r')].ha, 0.0)


class TestNumer(unittest.TestCase):
    def test_wolny_numer_ze_zrodla(self):
        self.assertEqual(ps.numer_w_slowniku(1004, {1, 999}), 1004)

    def test_zajety_numer_to_kolejny_po_najwiekszym(self):
        self.assertEqual(ps.numer_w_slowniku(1, {1, 999}), 1000)

    def test_brak_numeru_i_pusty_slownik(self):
        self.assertEqual(ps.numer_w_slowniku(None, set()), 1)


class TestPytanie(unittest.TestCase):
    def _brak(self, i):
        brak = ps.Brak(UZYTEK, 'K%d' % i)
        brak.ile, brak.ha, brak.bazy = 1, 0.25, {'a.mdb': 1}
        return brak

    def test_tresc_i_szczegoly(self):
        tekst, szczegoly = ps.tresc_pytania([self._brak(1)], 'czysta.mdb')
        self.assertIn('Użytek K1: 1 rek., 0,2500 ha', tekst)
        self.assertIn('czysta.mdb', tekst)
        self.assertIn('a.mdb: 1', szczegoly)

    def test_dluga_lista_skracana_tylko_w_oknie(self):
        tekst, szczegoly = ps.tresc_pytania(
            [self._brak(i) for i in range(20)], 'c.mdb')
        self.assertNotIn('K19:', tekst)
        self.assertIn('5 kolejnych', tekst)
        self.assertIn('K19 ', szczegoly)


if __name__ == '__main__':
    unittest.main()
