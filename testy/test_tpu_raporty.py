# -*- coding: utf-8 -*-
"""Zestawienia raportów TPU - część bez QGIS-a, Taksatora i Excela.
Uruchomienie z katalogu wtyczki:
    py testy/test_tpu_raporty.py"""
import importlib.util
import os
import sys
import tempfile
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KATALOG, 'skrypty'))
_spec = importlib.util.spec_from_file_location(
    'tpu_pliki', os.path.join(KATALOG, 'skrypty', 'tpu_raporty_pliki.py'))
tp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tp)

OB = [{'municip': '115', 'community': '0001', 'nazwa': 'Białęgi'},
      {'municip': '115', 'community': '0002', 'nazwa': 'Białężyn'}]


class TestRaporty(unittest.TestCase):
    def test_tabela(self):
        ids = [i for i, *_ in tp.RAPORTY]
        self.assertEqual(ids, list(range(19)))
        self.assertEqual(tp.OSOBOWE, {3, 5, 8})
        self.assertEqual(len(tp.ZESTAWIENIE_ARKUSZE), 16)
        self.assertNotIn(9, tp.ARKUSZE)
        self.assertNotIn(18, tp.ARKUSZE)
        self.assertEqual(tp.ARKUSZE_OSOBOWE, ('Sheet4', 'WzUPUL',
                                              'WykazWlasc'))
        self.assertEqual(len(set(tp.FOLDERY.values())), 19)

    def test_nazwa_pliku(self):
        self.assertEqual(tp.nazwa_pliku('115', '0009', 'Łoskoń Stary'),
                         '115-0009-Łoskoń Stary')
        self.assertEqual(tp.nazwa_pliku('115', '0001', 'A/B?'),
                         '115-0001-A_B_')
        self.assertEqual(tp.nazwa_pliku('115', '0001', ''), '115-0001')

    def test_obreby_z_bazy(self):
        w = [('30', '21', '115', '0002', 'Białężyn '),
             ('30', '21', '115', '0001', 'Białęgi'),
             ('30', '21', '115', '0001', 'Białęgi'),
             ('30', '21', '116', '0001', None)]
        ob = tp.obreby_z_bazy(w)
        self.assertEqual([(o['municip'], o['community']) for o in ob],
                         [('115', '0001'), ('115', '0002'),
                          ('116', '0001')])
        self.assertEqual(ob[1]['nazwa'], 'Białężyn')
        self.assertEqual(tp.powtorzone_obreby(ob), ['0001'])
        self.assertEqual(tp.powtorzone_obreby(OB), [])

    def test_plan(self):
        baza = os.path.join('C:\\', 'obiekt', 'baza.mdb')
        wyn, zad = tp.zaplanuj(baza, [4, tp.ZESTAWIENIE], OB, 'T')
        # kolejność wg tabeli: zestawienie, potem raport 4
        self.assertEqual([w['raport'] for w in wyn], [0, 0, 4, 4])
        self.assertEqual(wyn[0]['cel'], os.path.join(
            'C:\\', 'obiekt', 'Raporty_TPU', 'Zestawienie_raportow',
            '115-0001-Białęgi.xlsx'))
        self.assertEqual(wyn[2]['cel'], os.path.join(
            'C:\\', 'obiekt', 'Raporty_TPU', 'Opis_taksacyjny',
            '115-0001-Białęgi.xlsx'))
        self.assertEqual([i for i, _ in wyn[0]['zrodla']],
                         [i for i, _ in tp.ZESTAWIENIE_ARKUSZE])
        # raport 4 wspólny dla zestawienia i pojedynczego - raz
        self.assertEqual(len(zad), 2 * 16)
        self.assertEqual(wyn[2]['zrodla'][0][1], dict(wyn[0]['zrodla'])[4])
        self.assertEqual(len({z[3] for z in zad}), len(zad))
        self.assertEqual([z[0] for z in zad], list(range(1, len(zad) + 1)))

    def test_zadania_i_parsuj(self):
        with tempfile.TemporaryDirectory() as k:
            sc = os.path.join(k, 'z.txt')
            tp.zapisz_zadania([(1, 4, '0001', r'C:\x\ą.xls')], sc)
            with open(sc, encoding='utf-8') as f:
                self.assertEqual(f.read(), '1\t4\t0001\tC:\\x\\ą.xls\n')
        self.assertEqual(tp.parsuj('OK\t3\r\n'), ('OK', '3', ''))
        self.assertEqual(tp.parsuj('BLAD\t3\topis'), ('BLAD', '3', 'opis'))
        self.assertEqual(tp.parsuj('WERSJA\t50\t52'), ('WERSJA', '50', '52'))

    def test_opis_wynikow(self):
        wyn, _ = tp.zaplanuj('baza.mdb', [6], OB, 'T')
        t = tp.opis_wynikow(wyn, {wyn[1]['zrodla'][0][1]: 'zły obręb'}, {})
        self.assertIn('Zadania_gospodarcze: 1/2', t)
        self.assertIn('BŁĄD 115-0002 Białężyn: raport 6: zły obręb', t)


class TestPlyty(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.k = self.tmp.name
        kat = os.path.join(self.k, tp.FOLDER_RAPORTOW)
        for podf, plik in (
                ('Zestawienie_raportow', '115-0001-Białęgi.xlsx'),
                ('Zestawienie_raportow', '115-0002-Białężyn.xlsx'),
                ('Zestawienie_raportow', '116-0001-Inna.xlsx'),
                ('Zestawienie_raportow', '~$115-0001-Białęgi.xlsx'),
                ('Opis_taksacyjny', '115-0001-Białęgi.xlsx'),
                ('Wykaz_wlascicieli', '115-0001-Białęgi.xlsx'),
                ('Rejestr_dzialek_i_wlascicieli', '115-0001-Białęgi.xlsx'),
                ('Zadania_dla_wlascicieli', '115-0001-Białęgi.xlsx'),
                ('Moje', '115-0001-Białęgi.xlsx')):
            os.makedirs(os.path.join(kat, podf), exist_ok=True)
            open(os.path.join(kat, podf, plik), 'wb').close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_raporty_na_plyte(self):
        r = tp.raporty_na_plyte(self.k, '115', ['0001'])
        wzgl = sorted(w for _, w, _ in r)
        self.assertEqual(wzgl, sorted([
            os.path.join('Zestawienie_raportow', '115-0001-Białęgi.xlsx'),
            os.path.join('Opis_taksacyjny', '115-0001-Białęgi.xlsx')]))
        ark = {w.split(os.sep)[0]: a for _, w, a in r}
        self.assertEqual(ark['Zestawienie_raportow'], tp.ARKUSZE_OSOBOWE)
        self.assertEqual(ark['Opis_taksacyjny'], ())
        self.assertEqual(tp.raporty_na_plyte(self.k, '117', ['0001']), [])
        self.assertEqual(
            len(tp.raporty_na_plyte(self.k, '115', ['0001', '0002'])), 3)

    def test_kopiuj_bez_arkuszy(self):
        import openpyxl
        wb = openpyxl.Workbook()
        wb.active.title = 'OT'
        for n in ('Sheet4', 'WzUPUL', 'Zestawienie', 'WykazWlasc'):
            wb.create_sheet(n)['A1'] = n
        wb['WzUPUL']['A2'] = 'NAZWISKO IMIE'
        zr = os.path.join(self.k, 'z.xlsx')
        wb.save(zr)
        cel = os.path.join(self.k, 'plyta', 'Raporty', 'z.xlsx')
        tp.kopiuj_bez_arkuszy(zr, cel, tp.ARKUSZE_OSOBOWE)
        self.assertEqual(openpyxl.load_workbook(cel).sheetnames,
                         ['OT', 'Zestawienie'])
        self.assertEqual(openpyxl.load_workbook(zr).sheetnames,
                         ['OT', 'Sheet4', 'WzUPUL', 'Zestawienie',
                          'WykazWlasc'])
        cel2 = os.path.join(self.k, 'plyta', 'kopia.xlsx')
        tp.kopiuj_bez_arkuszy(zr, cel2, ())
        self.assertEqual(len(openpyxl.load_workbook(cel2).sheetnames), 5)


if __name__ == '__main__':
    unittest.main()
