# -*- coding: utf-8 -*-
"""Przeliczanie wieku i wymiarów ze stanu BDL. Bez QGIS-a:
    py testy/test_opis_bdl.py   (z katalogu wtyczki)"""
import importlib.util
import os
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'opis_bdl', os.path.join(KATALOG, 'skrypty', 'opis_bdl.py'))
bdl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bdl)


class TestPrzeliczenie(unittest.TestCase):
    def setUp(self):
        self.tabela, self.mnoznik = bdl.parametry_wzrostu()

    def _g(self, wiek=27, bhd=15, h=14):
        return {'SPECIES_AGE': wiek, 'BHD': bhd, 'HEIGHT': h, 'VOLUME': 140.0}

    def test_dziesiec_lat_jak_f1(self):
        # wiek po 10 latach 37 -> klasa 21-40: wys +5, pierś. +4; bez przejść
        # między klasami (wiek od 22)
        g = bdl.przelicz_gatunek(self._g(wiek=27), 10, self.tabela, self.mnoznik)
        self.assertEqual((g['SPECIES_AGE'], g['HEIGHT'], g['BHD']),
                         (37, 19, 19))

    def test_proporcjonalnie_do_lat(self):
        # 13 lat w klasie 21-40: wys +6,5, pierś. +5,2
        g = bdl.przelicz_gatunek(self._g(wiek=27), 13, self.tabela, self.mnoznik)
        self.assertEqual((g['SPECIES_AGE'], g['HEIGHT'], g['BHD']),
                         (40, 21, 20))

    def test_przejscie_przez_klasy(self):
        # 15 -> 25: 5 lat w 11-20 (wys +2, pierś. +1,5), 5 w 21-40 (+2,5, +2)
        h, b = bdl.przyrosty(15, 10, self.tabela)
        self.assertAlmostEqual(h, 4.5)
        self.assertAlmostEqual(b, 3.5)

    def test_mlode_bez_przyrostu_do_klasy_11(self):
        h, b = bdl.przyrosty(3, 5, self.tabela)
        self.assertEqual((h, b), (0, 0))

    def _masa(self, lata, wolumen=140.0):
        g = bdl.przelicz_gatunek({'SPECIES_AGE': 27, 'VOLUME': wolumen,
                                  'VOLUME_TEMP': wolumen}, lata, self.tabela,
                                 self.mnoznik)
        return g['VOLUME'], g['VOLUME_TEMP']

    def test_masa_dziesiec_lat_jak_f1(self):
        self.assertEqual(self._masa(10), (154.0, 154.0))

    def test_masa_proporcjonalnie_do_lat(self):
        # 1,1 ** 1,3
        self.assertEqual(self._masa(13), (158.47, 158.47))

    def test_masa_zero_lat_bez_zmian(self):
        self.assertEqual(self._masa(0), (140.0, 140.0))

    def test_brak_masy_zostaje_brakiem(self):
        self.assertEqual(self._masa(13, None), (None, None))

    def test_bez_wieku_bez_zmian(self):
        g = bdl.przelicz_gatunek(self._g(wiek=None), 13, self.tabela, self.mnoznik)
        self.assertEqual((g['SPECIES_AGE'], g['BHD'], g['HEIGHT']),
                         (None, 15, 14))

    def test_brak_wymiaru_zostaje_brakiem(self):
        g = bdl.przelicz_gatunek(self._g(bhd=None, h=None), 13, self.tabela, self.mnoznik)
        self.assertEqual((g['SPECIES_AGE'], g['BHD'], g['HEIGHT']),
                         (40, None, None))

    def test_zero_lat(self):
        g = bdl.przelicz_gatunek(self._g(), 0, self.tabela, self.mnoznik)
        self.assertEqual((g['SPECIES_AGE'], g['BHD'], g['HEIGHT']),
                         (27, 15, 14))


if __name__ == '__main__':
    unittest.main()
