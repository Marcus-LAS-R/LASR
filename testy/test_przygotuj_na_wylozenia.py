# -*- coding: utf-8 -*-
"""Przygotuj na wyłożenia - część bez QGIS-a. Uruchomienie z katalogu
wtyczki:
    py testy/test_przygotuj_na_wylozenia.py"""
import importlib.util
import os
import sys
import tempfile
import time
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KATALOG, 'skrypty'))
_spec = importlib.util.spec_from_file_location(
    'wylozenia_pliki',
    os.path.join(KATALOG, 'skrypty', 'przygotuj_na_wylozenia_pliki.py'))
pw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pw)


def _plik(sciezka, rozmiar=10):
    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    with open(sciezka, 'wb') as f:
        f.write(os.urandom(rozmiar))


def _gmina(korzen, folder, municip, obreby):
    """Folder gminy z mapami (wprost w PLOTOWANIE), atlasami, operatami
    i BDO dla obrębów [(community, NAZWA)]."""
    g = os.path.join(korzen, folder)
    plot = os.path.join(g, 'PLOTOWANIE', f'{municip}_GMINA')
    for com, nazwa in obreby:
        _plik(os.path.join(plot, 'Mapy', f'{com}_{nazwa}_MAPA_PRZEGLADOWA.pdf'))
        _plik(os.path.join(plot, 'Mapy',
                           f'{com}_{nazwa}_MAPA_PRZEGLADOWA_x2.pdf'))
        _plik(os.path.join(plot, 'Atlasy', f'{com}_{nazwa}_ATLAS.pdf'))
        _plik(os.path.join(plot, 'Atlasy', f'{com}_{nazwa}_LEG.pdf'))
        _plik(os.path.join(g, 'Operaty', f'17-{municip}-{com}-{nazwa}.pdf'))
        _plik(os.path.join(g, 'Operaty', f'17-{municip}-{com}-{nazwa}.docx'))
        _plik(os.path.join(g, 'Operaty_BDO',
                           f'17-{municip}-{com}-{nazwa}_BDO.pdf'))
    return g


def _ob(g, municip, com, nazwa=''):
    return {'folder': g, 'nazwa_folderu': os.path.basename(g),
            'municip': municip, 'community': com, 'nazwa_obrebu': nazwa}


class TestNazwy(unittest.TestCase):
    def test_nazwa_gminy(self):
        self.assertEqual(pw.nazwa_gminy('Gmina Ostrów Wielkopolski'),
                         'Ostrow_Wielkopolski')
        self.assertEqual(pw.nazwa_gminy('Miasto Odolanów'), 'Odolanow')
        self.assertEqual(pw.nazwa_gminy('Miasto i Gmina Raszków'), 'Raszkow')
        self.assertEqual(pw.nazwa_gminy('Gminowo'), 'Gminowo')

    def test_z_folderu(self):
        self.assertEqual(pw.nazwa_z_folderu('301703_5_Odolanow_OW'),
                         'Odolanow')
        self.assertEqual(pw.nazwa_z_folderu('301702_5_Nowe Skalmierzyce_OW'),
                         'Nowe_Skalmierzyce')
        self.assertEqual(pw.teryt_z_folderu('301703_4_Odolanow_M', '034'),
                         '301703')
        self.assertIsNone(pw.teryt_z_folderu('301703_4_Odolanow_M', '035'))
        self.assertIsNone(pw.teryt_z_folderu('Odolanow', '034'))

    def test_powtorzona_nazwa(self):
        n = pw.nazwy_folderow({'301701': 'Lipno', '041001': 'Lipno',
                               '301702': 'Raszkow'})
        self.assertEqual(n['301702'], 'pUPUL_Raszkow')
        self.assertEqual(n['301701'], 'pUPUL_Lipno_301701')


class TestPliki(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = _gmina(self.tmp.name, '301703_5_Odolanow_OW', '035',
                        [('0002', 'GARKI'), ('0003', 'GLISNICA')])

    def tearDown(self):
        self.tmp.cleanup()

    def test_pliki_obrebu(self):
        p = pw.pliki_obrebu(self.g, '035', '0002')
        nazwy = {r: [os.path.basename(x) for x in p[r]] for r in p}
        self.assertEqual(nazwy[pw.MAPY], ['0002_GARKI_MAPA_PRZEGLADOWA.pdf'])
        self.assertEqual(nazwy[pw.ATLASY], ['0002_GARKI_ATLAS.pdf',
                                            '0002_GARKI_LEG.pdf'])
        self.assertEqual(nazwy[pw.OPERATY], ['17-035-0002-GARKI.pdf'])
        self.assertEqual(nazwy[pw.OPERATY_BDO], ['17-035-0002-GARKI_BDO.pdf'])
        self.assertEqual(pw.braki_obrebu(p, pw.RODZAJE), [])

    def test_bdo_z_obu_lokalizacji_nowszy(self):
        stary = os.path.join(self.g, 'Operaty_BDO', '17-035-0002-GARKI_BDO.pdf')
        nowy = os.path.join(self.g, 'Operaty', 'Operaty_BDO',
                            '17-035-0002-GARKI_BDO.pdf')
        _plik(nowy)
        teraz = time.time()
        os.utime(stary, (teraz - 1000, teraz - 1000))
        p = pw.pliki_obrebu(self.g, '035', '0002')
        self.assertEqual(p[pw.OPERATY_BDO], [nowy])
        self.assertEqual(len(pw.podwojne_bdo(_ob(self.g, '035', '0002'))), 1)
        # BDO tylko w Operaty/Operaty_BDO też jest znajdowany
        _plik(os.path.join(self.g, 'Operaty', 'Operaty_BDO',
                           '17-035-0009-SWIECA_BDO.pdf'))
        p = pw.pliki_obrebu(self.g, '035', '0009')
        self.assertEqual(len(p[pw.OPERATY_BDO]), 1)
        self.assertEqual(pw.braki_obrebu(p, pw.RODZAJE),
                         ['mapa', 'atlas', 'legenda', 'operat'])

    def test_braki(self):
        p = pw.pliki_obrebu(self.g, '035', '0099')
        self.assertEqual(pw.braki_obrebu(p, pw.RODZAJE),
                         ['mapa', 'atlas', 'legenda', 'operat', 'operat BDO'])
        self.assertEqual(pw.braki_obrebu(p, (pw.OPERATY,)), ['operat'])

    def test_dostepne(self):
        self.assertEqual(pw.dostepne_rodzaje([self.g]), set(pw.RODZAJE))


class TestPlanIKopiowanie(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        k = self.tmp.name
        self.m = _gmina(k, '301703_4_Odolanow_M', '034', [('0001', 'ODOLANOW')])
        self.ow = _gmina(k, '301703_5_Odolanow_OW', '035',
                         [('0002', 'GARKI'), ('0003', 'GLISNICA')])
        self.wyn = os.path.join(k, '_Na_wylozenia')
        os.makedirs(self.wyn)
        self.gminy = {'301703': {'nazwa': 'Odolanow', 'obreby': [
            _ob(self.ow, '035', '0003'), _ob(self.m, '034', '0001'),
            _ob(self.ow, '035', '0002')]}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_jeden_folder_na_gmine(self):
        plan = pw.zaplanuj(self.gminy, pw.RODZAJE)
        cz = plan[0]['czesci']
        self.assertEqual([c['folder'] for c in cz], ['pUPUL_Odolanow'])
        self.assertEqual([o['community'] for o in cz[0]['obreby']],
                         ['0001', '0002', '0003'])
        self.assertEqual(len(cz[0]['pliki']), 15)
        self.assertIn(os.path.join('Operaty_BDO',
                                   '17-034-0001-ODOLANOW_BDO.pdf'),
                      [s for _, s in cz[0]['pliki']])

    def test_podzial_po_obrebach(self):
        # obręb = 5 plików po 10 B; limit 120 B -> 2 obręby + 1
        plan = pw.zaplanuj(self.gminy, pw.RODZAJE, limit=120)
        cz = plan[0]['czesci']
        self.assertEqual([c['folder'] for c in cz],
                         ['pUPUL_Odolanow_1', 'pUPUL_Odolanow_2'])
        self.assertEqual([len(c['obreby']) for c in cz], [2, 1])
        self.assertTrue(all(c['rozmiar'] < 120 for c in cz))

    def test_wybor_rodzajow(self):
        plan = pw.zaplanuj(self.gminy, (pw.MAPY,))
        sciezki = [s for _, s in plan[0]['czesci'][0]['pliki']]
        self.assertEqual(len(sciezki), 3)
        self.assertTrue(all(s.startswith('Mapy' + os.sep) for s in sciezki))

    def test_kopiowanie_i_podmiana(self):
        stary = os.path.join(self.wyn, 'pUPUL_Odolanow_3')
        _plik(os.path.join(stary, 'Mapy', 'stara.pdf'))
        plan = pw.zaplanuj(self.gminy, pw.RODZAJE, limit=120)
        ist = pw.istniejace_wyniki(self.wyn, plan)
        self.assertEqual(ist, ['pUPUL_Odolanow_3'])
        for cz in plan[0]['czesci']:
            self.assertEqual(pw.kopiuj_czesc(self.wyn, cz), [])
        self.assertEqual(pw.podmien(self.wyn, plan, ist), [])
        self.assertEqual(sorted(os.listdir(self.wyn)),
                         ['pUPUL_Odolanow_1', 'pUPUL_Odolanow_2'])
        self.assertEqual(
            sorted(os.listdir(os.path.join(self.wyn, 'pUPUL_Odolanow_1'))),
            ['Atlasy', 'Mapy', 'Operaty', 'Operaty_BDO'])

    def test_przerwanie_zostawia_stare(self):
        stary = os.path.join(self.wyn, 'pUPUL_Odolanow')
        _plik(os.path.join(stary, 'Mapy', 'stara.pdf'))
        cz = pw.zaplanuj(self.gminy, pw.RODZAJE)[0]['czesci'][0]
        with self.assertRaises(pw.Przerwano):
            pw.kopiuj_czesc(self.wyn, cz, lambda _: False)
        self.assertEqual(os.listdir(self.wyn), ['pUPUL_Odolanow'])
        self.assertTrue(os.path.isfile(os.path.join(stary, 'Mapy',
                                                    'stara.pdf')))

    def test_opis(self):
        self.gminy['301703']['obreby'].append(_ob(self.ow, '035', '0099'))
        opis = pw.opis_planu(pw.zaplanuj(self.gminy, pw.RODZAJE), [],
                             pw.RODZAJE)
        self.assertIn('pUPUL_Odolanow - 3 obr., 15 plików', opis)
        self.assertIn('035.0099 - brak plików', opis)
        self.assertIn('BRAKI PLIKÓW', opis)


if __name__ == '__main__':
    unittest.main()
