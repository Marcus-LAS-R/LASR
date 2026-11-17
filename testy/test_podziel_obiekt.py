# -*- coding: utf-8 -*-
"""Podziel obiekt (gminami / obrębami) - część bez QGIS-a. Uruchomienie
z katalogu wtyczki:
    py testy/test_podziel_obiekt.py"""
import importlib.util
import os
import sys
import tempfile
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KATALOG, 'skrypty'))
_spec = importlib.util.spec_from_file_location(
    'podziel_pliki',
    os.path.join(KATALOG, 'skrypty', 'podziel_obiekt_pliki.py'))
pg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pg)

M = ('30', '17', '034', '0001')       # Odolanów miasto
OW1 = ('30', '17', '035', '0002')     # Odolanów obszar wiejski
OW2 = ('30', '17', '035', '0003')
G = ('12', '05', '092', '0004')       # Sękowa - gmina wiejska

BAZA = [(M, 'Odolanów', 'Odolanów', 10), (OW1, 'Odolanów', 'Garki', 5),
        (OW2, 'Odolanów', 'Gliśnica', 7)]


class TestNazwy(unittest.TestCase):
    def test_grupa(self):
        self.assertEqual(pg.grupa_obrebu(OW1), '3017035')
        self.assertEqual(pg.grupa_obrebu(OW1, pg.OBREBY), '3017035.0002')
        self.assertIsNone(pg.grupa_obrebu(('30', '17', '', '0002')))
        self.assertIsNone(pg.grupa_obrebu(('30', '17', '35', '0002')))
        self.assertIsNone(pg.grupa_obrebu(('30', '17', '035', ''),
                                          pg.OBREBY))
        self.assertEqual(pg.grupa_z_id('301703_5'), '3017035')
        self.assertEqual(pg.grupa_z_id('3017035'), '3017035')
        self.assertIsNone(pg.grupa_z_id('301703'))
        self.assertEqual(pg.grupa_z_id('301703_5.0002', pg.OBREBY),
                         '3017035.0002')
        self.assertIsNone(pg.grupa_z_id('301703_5', pg.OBREBY))

    def test_folder_gminy(self):
        f = pg.folder_jednostki
        self.assertEqual(f('3017035', 'Gmina Odolanów'),
                         '301703_5_Odolanow_OW')
        self.assertEqual(f('3017034', 'Miasto Odolanów'),
                         '301703_4_Odolanow_M')
        self.assertEqual(f('1205092', 'Sękowa'), '120509_2_Sekowa')
        self.assertEqual(f('1205092', ''), '120509_2')
        self.assertEqual(f('1609084', 'Ozimek - miasto'), '160908_4_Ozimek_M')
        self.assertEqual(f('1609085', 'Ozimek Obszar wiejski'),
                         '160908_5_Ozimek_OW')
        self.assertEqual(f('1609084', 'Miasto'), '160908_4_Miasto_M')

    def test_folder_obrebu(self):
        f = pg.folder_jednostki
        self.assertEqual(f('1215052.0003', 'Osielec', pg.OBREBY),
                         '121505_2.0003_Osielec')
        self.assertEqual(f('3017035.0002', 'Nowa Wieś Mała', pg.OBREBY),
                         '301703_5.0002_Nowa_Wies_Mala')
        self.assertEqual(f('3017035.0002', '', pg.OBREBY), '301703_5.0002')


class TestGminy(unittest.TestCase):
    def setUp(self):
        self.gminy, self.zle = pg.zbierz(
            BAZA, [OW1, G, ('30', '17', 'x', '1')], {'1205092': 'Sękowa'})

    def test_zbierz(self):
        self.assertEqual(sorted(self.gminy), ['1205092', '3017034',
                                              '3017035'])
        ow = self.gminy['3017035']
        self.assertEqual(ow.obreby, {OW1, OW2})
        self.assertEqual(ow.dzialki, 12)
        self.assertEqual(ow.zrodla, 'baza, SHP')
        self.assertEqual(self.gminy['3017034'].zrodla, 'baza')
        self.assertEqual(self.gminy['1205092'].folder, '120509_2_Sekowa')
        self.assertEqual(len(self.zle), 1)

    def test_domyslnie_tylko_z_bazy(self):
        self.assertEqual(pg.domyslnie_wybrane(self.gminy),
                         {'3017034', '3017035'})
        tylko_shp, _ = pg.zbierz([], [OW1, G])
        self.assertEqual(pg.domyslnie_wybrane(tylko_shp),
                         {'3017035', '1205092'})

    def test_przydzial(self):
        p = pg.przydzial(self.gminy, {'3017035', '1205092'})
        self.assertEqual(p[OW1], '3017035')
        self.assertEqual(p[G], '1205092')
        self.assertEqual(p[M], pg.POMIN)

    def test_foldery_i_istniejace(self):
        with tempfile.TemporaryDirectory() as k:
            f = pg.foldery_wynikowe(k, self.gminy, {'3017035'})
            self.assertEqual(f, {'3017035':
                                 os.path.join(k, '301703_5_Odolanow_OW')})
            self.assertEqual(pg.istniejace(f, 'baza.mdb', True), [])
            os.makedirs(os.path.join(f['3017035'], 'SHP'))
            open(os.path.join(f['3017035'], 'baza.mdb'), 'w').close()
            self.assertEqual(len(pg.istniejace(f, 'baza.mdb', True)), 2)
            self.assertEqual(len(pg.istniejace(f, None, True)), 1)

    def test_raport(self):
        wybrane = {'3017035', '1205092'}
        f = pg.foldery_wynikowe('C:\\obiekt', self.gminy, wybrane)
        analiza = {'liczba_wydz': {'3017035': 4}, 'nieprzypisane': [],
                   'konflikty': [('R301703500020001-01-a', '3017035',
                                  ['30170340001.1 [POMIN]'])],
                   'rozliczenie_puste': False}
        t = pg.tekst_raportu(
            [('Baza', 'C:\\obiekt\\baza.mdb')], self.gminy, wybrane, f,
            {'3017035': ('C:\\b.mdb', {'dzialki_usuniete': 10,
                                       'arodes_usuniete': 3,
                                       'wlasciciele_usunieci': 2}),
             '1205092': ('błąd czyszczenia', None)},
            analiza, [('DZKAT', 'PARCELID', {'3017035': 12, '1205092': 0},
                       (1, 0), '')])
        self.assertIn('PODZIEL OBIEKT - GMINAMI', t)
        self.assertIn('301703_4_Odolanow_M - pominięto', t)
        self.assertIn('301703_5_Odolanow_OW - 2 obr., 12 dz., 4 wydz.', t)
        self.assertIn('BAZA: błąd czyszczenia', t)
        self.assertIn('DZKAT [PARCELID]: 301703_5_Odolanow_OW: 12', t)
        self.assertIn('bez obrębu: 1', t)
        self.assertIn('DZIAŁKACH INNEJ GMINY', t)
        self.assertIn('R301703500020001-01-a [301703_5_Odolanow_OW]', t)


class TestObreby(unittest.TestCase):
    def setUp(self):
        self.obr, _ = pg.zbierz(BAZA, [OW1, G],
                                {'1205092.0004': 'Bartne'}, pg.OBREBY)

    def test_zbierz(self):
        self.assertEqual(sorted(self.obr), ['1205092.0004', '3017034.0001',
                                            '3017035.0002', '3017035.0003'])
        self.assertEqual(self.obr['3017035.0003'].folder,
                         '301703_5.0003_Glisnica')
        self.assertEqual(self.obr['3017035.0002'].dzialki, 5)
        self.assertEqual(self.obr['1205092.0004'].folder,
                         '120509_2.0004_Bartne')
        self.assertEqual(pg.domyslnie_wybrane(self.obr),
                         {'3017034.0001', '3017035.0002', '3017035.0003'})

    def test_przydzial_i_raport(self):
        wybrane = {'3017035.0002'}
        p = pg.przydzial(self.obr, wybrane)
        self.assertEqual(p[OW1], '3017035.0002')
        self.assertEqual(p[OW2], pg.POMIN)
        t = pg.tekst_raportu([], self.obr, wybrane,
                             pg.foldery_wynikowe('C:\\o', self.obr, wybrane),
                             tryb=pg.OBREBY)
        self.assertIn('OBRĘBY', t)
        self.assertIn('301703_5.0002_Garki - 1 obr., 5 dz.', t)


if __name__ == '__main__':
    unittest.main()
