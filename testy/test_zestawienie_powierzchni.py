# -*- coding: utf-8 -*-
"""Zestawienie powierzchni (TABELA 1 pkt 1-4) - obliczenia na SQLite
w pamięci i zapis .xlsx. Bez QGIS-a:
    py testy/test_zestawienie_powierzchni.py   (z katalogu wtyczki)"""
import importlib.util
import os
import sqlite3
import sys
import tempfile
import types
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PAKIET = '_zest_pow_test'


def _modul(nazwa):
    """dane.py / arkusz.py bez __init__.py pakietu (ten wymaga QGIS-a)."""
    if _PAKIET not in sys.modules:
        pakiet = types.ModuleType(_PAKIET)
        pakiet.__path__ = []
        sys.modules[_PAKIET] = pakiet
    pelna = _PAKIET + '.' + nazwa
    spec = importlib.util.spec_from_file_location(
        pelna, os.path.join(KATALOG, 'skrypty', 'zestawienie_powierzchni',
                            nazwa + '.py'))
    modul = importlib.util.module_from_spec(spec)
    sys.modules[pelna] = modul
    spec.loader.exec_module(modul)
    return modul


dane = _modul('dane')
arkusz = _modul('arkusz')


class BazaTest:
    def __init__(self):
        self.con = sqlite3.connect(':memory:')
        self.cur = self.con.cursor()
        self.cur.executescript('''
            create table F_MUNICIPALITY (COUNTY_CD text, DISTRICT_CD text,
                MUNICIPALITY_CD text, MUNICIPALITY_NAME text);
            create table F_COMMUNITY (COUNTY_CD text, DISTRICT_CD text,
                MUNICIPALITY_CD text, COMMUNITY_CD text,
                COMMUNITY_NAME text);
            create table F_PARCEL (PARCEL_INT_NUM int, MUNICIPALITY_CD text,
                COMMUNITY_CD text);
            create table F_PARCEL_LAND_USE (PARCEL_INT_NUM int, SHAPE_NR int,
                AREA_USE_CD text);
            create table F_ARODES (ARODES_INT_NUM int, ADRESS_FOREST text);
            create table F_AROD_LAND_USE (ARODES_INT_NUM int,
                PARCEL_INT_NUM int, SHAPE_NR int, AROD_LAND_USE_AREA real);
            insert into F_MUNICIPALITY values ('12', '05', '2', 'Sękowa');
            insert into F_COMMUNITY values
                ('12', '05', '2', '0001', 'Bodaki'),
                ('12', '05', '2', '0002', 'Czarne'),
                ('12', '05', '2', '0003', 'Pusty');
            insert into F_PARCEL values (1, '2', '0001'), (2, '2', '0002');
            insert into F_PARCEL_LAND_USE values
                (1, 1, 'Ls'), (1, 2, 'R'), (2, 1, 'LS');
            insert into F_ARODES values
                (10, '12-05-2-01-1-a-00'), (11, '12-05-2-01-1-Lz-00'),
                (12, '12-05-2-02-3-b-00');
            insert into F_AROD_LAND_USE values
                (10, 1, 1, 1.25), (10, 1, 2, 0.10), (11, 1, 1, 0.15),
                (12, 2, 1, 2.0);
        ''')


class TestDane(unittest.TestCase):
    def test_pkt_1_2_3_4(self):
        obreby, uwagi = dane.pobierz(BazaTest())
        self.assertEqual(uwagi, [])
        self.assertEqual([o.wiersz() for o in obreby], [
            ['2', 'Sękowa', '0001', 'Bodaki', 1.4, 0.1, 0.15, 1.35],
            ['2', 'Sękowa', '0002', 'Czarne', 2.0, 0.0, 0.0, 2.0],
        ])  # pusty obręb 0003 pominięty

    def test_brak_nazwy_obrebu(self):
        obreby, uwagi = dane.policz([('3', '0009', 'LS', 'x', 1.0)], [])
        self.assertEqual(obreby[0].wiersz()[:4], ['3', '', '0009', ''])
        self.assertEqual(len(uwagi), 1)

    def test_nazwa_arkusza(self):
        obreby, _ = dane.pobierz(BazaTest())
        self.assertEqual(dane.nazwa_arkusza(obreby, 'folder'), 'Sękowa')
        self.assertEqual(dane.nazwa_arkusza(obreby[:1], 'folder'), 'Bodaki')
        inna = dane.Obreb('9', '0001')
        self.assertEqual(dane.nazwa_arkusza(obreby + [inna], 'folder'),
                         'folder')


class TestArkusz(unittest.TestCase):
    def test_unikalna_nazwa(self):
        zajete = {'całość'}
        self.assertEqual(arkusz.unikalna_nazwa('A/B:C', zajete), 'A_B_C')
        self.assertEqual(arkusz.unikalna_nazwa('a/b:c', zajete), 'a_b_c (2)')
        self.assertEqual(len(arkusz.unikalna_nazwa('x' * 40, zajete)), 31)
        self.assertEqual(arkusz.unikalna_nazwa('Całość', zajete),
                         'Całość (2)')

    def test_zapis(self):
        import openpyxl
        obreby, _ = dane.pobierz(BazaTest())
        w = [o.wiersz() for o in obreby]
        with tempfile.TemporaryDirectory() as kat:
            sc = os.path.join(kat, 'z.xlsx')
            arkusz.zapisz(sc, [('Sękowa', w), ('Bodaki', w[:1])])
            wb = openpyxl.load_workbook(sc)
            self.assertEqual(wb.sheetnames, ['Całość', 'Sękowa', 'Bodaki'])
            ws = wb['Całość']
            self.assertEqual(ws['A1'].value, 'Nr gminy')
            # Całość: 2 obręby z "Sękowa" + 1 z "Bodaki", posortowane
            self.assertEqual(ws.max_row, 5)
            self.assertEqual([ws.cell(r, 4).value for r in (2, 3, 4)],
                             ['Bodaki', 'Bodaki', 'Czarne'])
            self.assertEqual(ws['A5'].value, 'SUMA')
            self.assertEqual(ws['H5'].value, 4.7)
            self.assertEqual(ws['E2'].number_format, '0.0000')
            self.assertEqual(wb['Bodaki']['H3'].value, 1.35)
            wb.close()


if __name__ == '__main__':
    unittest.main()
