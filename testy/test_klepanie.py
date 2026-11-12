# -*- coding: utf-8 -*-
"""Klepanie z raportu kart (skrypty/klepanie.py): odczyt raportu, kolejność
kart, dopasowanie adresów starego raportu, wznowienie postępu. Bez QGIS-a:
    py testy/test_klepanie.py   (z katalogu wtyczki)"""
import importlib.util
import os
import shutil
import sys
import tempfile
import types
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# pakiet zastępczy - bez skrypty/__init__.py (QGIS)
_pakiet = types.ModuleType('_lasr_skrypty')
_pakiet.__path__ = [os.path.join(KATALOG, 'skrypty')]
sys.modules['_lasr_skrypty'] = _pakiet
for _nazwa in ('waypointy', 'klepanie'):
    _spec = importlib.util.spec_from_file_location(
        '_lasr_skrypty.' + _nazwa,
        os.path.join(KATALOG, 'skrypty', _nazwa + '.py'))
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules['_lasr_skrypty.' + _nazwa] = _mod
    _spec.loader.exec_module(_mod)
kl = sys.modules['_lasr_skrypty.klepanie']
wp = sys.modules['_lasr_skrypty.waypointy']

ADR_A = 'T040250024-101   -a   -00'
ADR_B = 'T040250024-101   -b   -00'
ADR_C = 'T040250024-102   -a   -00'
NAGLOWKI = ['MUNICIP', 'COMMUNITY', 'ODDZ', 'WYDZ', 'NR_ROBO', 'OBR',
            'ILE_KLONOW']


def wiersz_raportu(adr, nr, klonow=''):
    return [adr[3:6], adr[6:10], adr[13:17], adr[18:20], nr, 'Obręb',
            klonow]


class TestKlepanie(unittest.TestCase):

    def setUp(self):
        self.kat = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.kat, ignore_errors=True)

    def raport(self, wiersze, z_adresem=True):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Raport kart'
        ws.append(NAGLOWKI + (['ADR_LES'] if z_adresem else []))
        for adr, nr, klonow in wiersze:
            ws.append(wiersz_raportu(adr, nr, klonow) +
                      ([adr] if z_adresem else []))
        wb.create_sheet('Klony')
        sc = os.path.join(self.kat, 'raport_nr_robocze.xlsx')
        wb.save(sc)
        return sc

    def test_kolejnosc_naturalna_i_pominiete_bez_karty(self):
        sc = self.raport([(ADR_C, 'TK-10', ''), (ADR_A, 'TK-2', 3),
                          (ADR_B, '---', ''), (ADR_B, 'SS-1', '')])
        karty = kl.czytaj_raport(sc)
        self.assertEqual([k['nr'] for k in karty], ['TK-10', 'TK-2', 'SS-1'])
        wiersze = kl.wiersze_waypointow(karty)
        self.assertEqual([w['obiekt'] for w in wiersze], [
            'SS-1 → T040250024-101-b-00',
            'TK-2 → T040250024-101-a-00',
            'TK-10 → T040250024-102-a-00'])
        self.assertEqual(wiersze[1]['klucz'], ADR_A.strip())
        self.assertIn('3 wydz.', wiersze[1]['blad'])
        self.assertTrue(all(w['zrodlo'] == kl.ZRODLO for w in wiersze))

    def test_stary_raport_bez_adr_les(self):
        sc = self.raport([(ADR_A, 'TK-1', ''), (ADR_C, 'TK-2', '')],
                         z_adresem=False)
        karty = kl.czytaj_raport(sc)
        z_adr, bez = kl.dopasuj_adresy(karty, [ADR_A, ADR_B])
        self.assertEqual([(k['nr'], k['adr']) for k in z_adr],
                         [('TK-1', ADR_A)])
        self.assertEqual([k['nr'] for k in bez], ['TK-2'])

    def test_wznowienie_postepu(self):
        sc = self.raport([(ADR_A, 'TK-1', ''), (ADR_B, 'TK-2', '')])
        wiersze = kl.wiersze_waypointow(kl.czytaj_raport(sc))
        wiersze[0]['status'] = kl.STATUS_ZROBIONE
        postep = kl.sciezka_postepu(sc)
        wp.zapisz(postep, wiersze)
        nowe = kl.wiersze_waypointow(kl.czytaj_raport(sc),
                                     wp.wczytaj(postep))
        self.assertEqual([w['status'] for w in nowe],
                         [kl.STATUS_ZROBIONE, ''])
        self.assertEqual(os.path.basename(postep),
                         'raport_nr_robocze_klepanie.csv')

    def test_pliki_klonow(self):
        open(os.path.join(self.kat, 'KLON_po_klepaniu.txt'), 'w').close()
        self.assertEqual([os.path.basename(x)
                          for x in kl.pliki_klonow(self.kat)],
                         ['KLON_po_klepaniu.txt'])


if __name__ == '__main__':
    unittest.main()
