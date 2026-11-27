# -*- coding: utf-8 -*-
"""Uzupełnianie pustych uszkodzeń (wydzielenia z piętrem drzewostanu, (CAUSE_CD, DAMAGE_DEGREE_CD) na
bazie SQLite w pamięci. Bez QGIS-a:
    py testy/test_uzupelnij_uszkodzenia.py   (z katalogu wtyczki)"""
import importlib.util
import os
import sqlite3
import sys
import types
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _modul():
    """Ładuje skrypty/baza_uzupelnij_uszkodzenia.py z zaślepkami qgis i
    modułów wtyczki (importy względne)."""
    qgis = types.ModuleType('qgis')
    core = types.ModuleType('qgis.core')
    core.QgsProject = core.Qgis = object
    qgis.core = core
    sys.modules.setdefault('qgis', qgis)
    sys.modules.setdefault('qgis.core', core)

    pakiet = types.ModuleType('_skrypty_test')
    pakiet.__path__ = []
    przyciski = types.ModuleType('_skrypty_test.przyciski')
    przyciski.QMessageBox = object
    wrapper = types.ModuleType('_skrypty_test.baza_wrapper')
    wrapper.Baza = wrapper.znajdz_baze_do_wydz = None
    sys.modules['_skrypty_test'] = pakiet
    sys.modules['_skrypty_test.przyciski'] = przyciski
    sys.modules['_skrypty_test.baza_wrapper'] = wrapper

    nazwa = '_skrypty_test.baza_uzupelnij_uszkodzenia'
    spec = importlib.util.spec_from_file_location(
        nazwa, os.path.join(KATALOG, 'skrypty',
                            'baza_uzupelnij_uszkodzenia.py'))
    modul = importlib.util.module_from_spec(spec)
    sys.modules[nazwa] = modul
    spec.loader.exec_module(modul)
    return modul


uu = _modul()


class BazaTest:
    """Minimalny odpowiednik Baza (pobierz/wpisz/utworz_kopie)."""

    def __init__(self):
        self.con = sqlite3.connect(':memory:')
        self.cur = self.con.cursor()
        self.kopie = 0
        self.cur.executescript('''
            create table F_SUBAREA (ARODES_INT_NUM int, AREA_TYPE_CD text,
                SITE_TYPE_CD text, CAUSE_CD text, DAMAGE_DEGREE_CD text);
            create table F_STOREY_SPECIES (ARODES_INT_NUM int,
                STOREY_CD text, SPECIES_RANK_ORDER int, SPECIES_AGE int);
            create table F_AROD_STOREY (ARODES_INT_NUM int, STOREY_CD text);
        ''')

    def pobierz(self, sql):
        return self.cur.execute(sql).fetchall()

    def wpisz(self, sql):
        try:
            self.cur.execute(sql)
            self.con.commit()
        except sqlite3.Error:
            return False
        return True

    def utworz_kopie(self, wpis=''):
        self.kopie += 1

    def dodaj(self, aid, typ, tsl, wiek, przyczyna=None, stopien=None,
              pietro='DRZEW'):
        """pietro - kod piętra w F_AROD_STOREY (None - brak pięter)"""
        self.cur.execute('insert into F_SUBAREA values (?, ?, ?, ?, ?)',
                         (aid, typ, tsl, przyczyna, stopien))
        if pietro is None:
            return
        self.cur.execute('insert into F_AROD_STOREY values (?, ?)',
                         (aid, pietro))
        self.cur.execute(
            'insert into F_STOREY_SPECIES values (?, ?, 1, ?)',
            (aid, pietro, wiek))

    def wynik(self, aid):
        return tuple(self.cur.execute(
            'select CAUSE_CD, DAMAGE_DEGREE_CD from F_SUBAREA '
            'where ARODES_INT_NUM=?', (aid,)).fetchone())


class TestUzupelnijUszkodzenia(unittest.TestCase):
    def setUp(self):
        self.b = BazaTest()
        self.b.dodaj(1, 'D-STAN', 'BŚW', 60)            # KLIMAT
        self.b.dodaj(2, 'D-STAN', 'OL', 60)             # ols - WODNE
        self.b.dodaj(3, 'D-STAN', 'LŁG', 60)            # łęg - WODNE
        self.b.dodaj(4, 'D-STAN', 'BMB', 60)            # bagienne - WODNE
        self.b.dodaj(5, 'D-STAN', 'OL', 15)             # młody - ZWIERZ
        self.b.dodaj(6, 'D-STAN', 'LMŚW', 10)           # młody - ZWIERZ
        self.b.dodaj(7, 'D-STAN', 'OL', 60, 'GRZYB', '2')  # wpisane - bez zmian
        self.b.dodaj(8, 'D-STAN', 'LB', 60, None, '1')  # tylko przyczyna
        self.b.dodaj(9, 'HAL', 'BŚW', 0, pietro=None)   # bez pięter - pomijane
        self.b.dodaj(10, 'D-STAN', 'OL', 5, pietro='PODR')  # bez drzewostanu
        self.b.dodaj(11, 'D-STAN', 'LŚW', 70, pietro='IP')  # KO - KLIMAT
        self.b.dodaj(12, 'INNE WYL', 'BŚW', 60)         # ma DRZEW - KLIMAT

    def test_policz(self):
        self.assertEqual(uu.policz_puste(self.b),
                         {'zwierz': 2, 'woda': 3, 'klimat': 4, 'stopien': 8})

    def test_uzupelnij(self):
        ile = uu.uzupelnij_po_cichu(self.b, kopia=False)
        self.assertEqual(sum(ile.values()), 17)
        self.assertEqual(self.b.kopie, 0)
        self.assertEqual(self.b.wynik(1), ('KLIMAT', '0'))
        self.assertEqual(self.b.wynik(2), ('WODNE', '0'))
        self.assertEqual(self.b.wynik(3), ('WODNE', '0'))
        self.assertEqual(self.b.wynik(4), ('WODNE', '0'))
        self.assertEqual(self.b.wynik(5), ('ZWIERZ', '0'))
        self.assertEqual(self.b.wynik(6), ('ZWIERZ', '0'))
        self.assertEqual(self.b.wynik(7), ('GRZYB', '2'))
        self.assertEqual(self.b.wynik(8), ('KLIMAT', '1'))
        self.assertEqual(self.b.wynik(9), (None, None))
        self.assertEqual(self.b.wynik(10), (None, None))
        self.assertEqual(self.b.wynik(11), ('KLIMAT', '0'))
        self.assertEqual(self.b.wynik(12), ('KLIMAT', '0'))

    def test_kopia_tylko_gdy_jest_co_uzupelniac(self):
        uu.uzupelnij_po_cichu(self.b)
        self.assertEqual(self.b.kopie, 1)
        ile = uu.uzupelnij_po_cichu(self.b)
        self.assertEqual(sum(ile.values()), 0)
        self.assertEqual(self.b.kopie, 1)


if __name__ == '__main__':
    unittest.main()
