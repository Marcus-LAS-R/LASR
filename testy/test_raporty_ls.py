# -*- coding: utf-8 -*-
"""Znacznik czasu w nazwach plików i odczyt raportów Ls. Bez QGIS-a:
    py testy/test_raporty_ls.py   (z katalogu wtyczki)"""
import importlib.util
import os
import tempfile
import unittest
from datetime import datetime

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _modul(nazwa):
    spec = importlib.util.spec_from_file_location(
        nazwa, os.path.join(KATALOG, 'skrypty', nazwa + '.py'))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


zc = _modul('znacznik_czasu')
rl = _modul('raporty_ls')

KONTROLA = (
    '-----[ RAPORT ]------\n\nLs w shp: 1241\n\n'
    '---ZDUBLOWANE LANDID [SHP]----------\nZdublowane LANDID: 1\n\n'
    '26041550003.5.LsV\n' + 33 * '-' + '\n\n\n'
    '---BRAKUJĄCE LSy [W SHP]----------\nBrakujących Ls-ów: 2\n\n'
    '26041550001.310/1.LsV\t0.09\n26041550002.453.LsIII\t0.0251\n' +
    33 * '-' + '\n\n\n'
    '---BRAKUJĄCE LSy [W BAZIE]--------\nBrakujących Ls-ów: 1\n\n'
    '26041550009.1.Ls\t2.0\t26041550009.1\n' + 33 * '-' + '\n\n\n'
    '---LS ZE ZNACZNĄ RÓŻNICĄ POW.-----\nLs z dużą: 1\n\n'
    'adr_adm\tpow_graf\tpow_rej\troznica\n'
    '26041550019.92.LsV\t2.0\t2.2\t0.2\n' + 33 * '-' + '\n')
# ls_raport ma trzecią kolumnę z numerem działki
RAPORT = ('RAPORT\n\n---BRAKUJĄCE LSy [W SHP]----------\n'
          'Brakujących Ls-ów: 1\n\n'
          '14160110001.2200/7.LsVa\t0.0017\t14160110001.2200/7\n' +
          33 * '-' + '\n')


def _zapisz(katalog, nazwa, tekst, kiedy=None, kodowanie='cp1250'):
    sc = os.path.join(katalog, nazwa)
    with open(sc, 'w', encoding=kodowanie) as f:
        f.write(tekst)
    if kiedy:
        os.utime(sc, (kiedy, kiedy))
    return sc


class TestZnacznik(unittest.TestCase):
    def test_format(self):
        self.assertEqual(zc.znacznik(datetime(2026, 11, 2, 9, 7, 5)),
                         '26-11-02_T_09_07_05')

    def test_nazwy_sortuja_sie_chronologicznie(self):
        daty = [datetime(2026, 9, 29, 23), datetime(2026, 11, 2, 1),
                datetime(2027, 1, 1)]
        nazwy = [zc.znacznik(d) for d in daty]
        self.assertEqual(sorted(nazwy), nazwy)


class TestRaportyLs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_tylko_sekcja_brakow_w_shp(self):
        sc = _zapisz(self.tmp.name, 'ls_kontrola_x.txt', KONTROLA)
        self.assertEqual(rl.brakujace_w_shp(sc),
                         {'26041550001.310/1.LSV', '26041550002.453.LSIII'})

    def test_trzy_kolumny_i_wielkosc_liter(self):
        sc = _zapisz(self.tmp.name, 'ls_raport_x.txt', RAPORT)
        self.assertEqual(rl.brakujace_w_shp(sc),
                         {'14160110001.2200/7.LSVA'})

    def test_utf8(self):
        sc = _zapisz(self.tmp.name, 'ls_raport_x.txt', RAPORT,
                     kodowanie='utf-8')
        self.assertEqual(len(rl.brakujace_w_shp(sc)), 1)

    def test_raport_bez_brakow(self):
        sc = _zapisz(self.tmp.name, 'ls_raport_x.txt', 'RAPORT\nLs w shp: 1')
        self.assertEqual(rl.brakujace_w_shp(sc), set())

    def test_najnowszy_po_dacie_modyfikacji_nie_po_nazwie(self):
        _zapisz(self.tmp.name, 'ls_kontrola_2026-09-01T230806.txt', '', 1000)
        nowy = _zapisz(self.tmp.name, 'ls_raport_20260716T123617.txt', '', 2000)
        _zapisz(self.tmp.name, 'popraw_ls_kontrola_26-12-01.txt', '', 3000)
        self.assertEqual(rl.najnowszy_raport(self.tmp.name), nowy)

    def test_brak_raportu_to_none_a_nie_pusty_zbior(self):
        self.assertIsNone(rl.brakujace_obok_bazy(self.tmp.name))
        _zapisz(self.tmp.name, 'ls_raport_x.txt', 'RAPORT')
        self.assertEqual(rl.brakujace_obok_bazy(self.tmp.name), set())

    def test_archiwum_nie_jest_przegladane(self):
        os.makedirs(os.path.join(self.tmp.name, 'Raporty', 'Archiwum'))
        _zapisz(os.path.join(self.tmp.name, 'Raporty', 'Archiwum'),
                'ls_raport_x.txt', RAPORT)
        self.assertIsNone(rl.najnowszy_raport(self.tmp.name))


if __name__ == '__main__':
    unittest.main()
