# -*- coding: utf-8 -*-
"""Rachunek rozliczenia użytku i kopie ZIP. Bez QGIS-a:
    py testy/test_rozliczenie_uzytku.py   (z katalogu wtyczki)"""
import importlib.util
import os
import tempfile
import unittest
import zipfile

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _modul(nazwa):
    spec = importlib.util.spec_from_file_location(
        nazwa, os.path.join(KATALOG, 'skrypty', nazwa + '.py'))
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


ru = _modul('rozliczenie_uzytku')
kz = _modul('kopie_zip')


class TestRachunek(unittest.TestCase):
    def test_przyklad_wydzielenia_nowego_ze_starego(self):
        wyn = ru.rozlicz_uzytek({'stare': 1.4, 'nowe': 0.6}, 2.0, 2.0)
        self.assertEqual(wyn, [['stare', 1.4], ['nowe', 0.6]])

    def test_suma_rowna_rejestrowi_poprawka_do_najwiekszego(self):
        wyn = ru.rozlicz_uzytek({'a': 1.0, 'b': 1.0, 'c': 1.0}, 1.0, 3.0)
        self.assertEqual(round(sum(x[1] for x in wyn), 4), 1.0)
        self.assertEqual(wyn[0][1], 0.3334)

    def test_rejestr_inny_niz_grafika_proporcjonalnie(self):
        wyn = ru.rozlicz_uzytek({'a': 1.5, 'b': 0.5}, 1.8, 2.0)
        self.assertEqual(wyn, [['a', 1.35], ['b', 0.45]])

    def test_czesciowe_pokrycie_uzytku(self):
        # wydzielenia na połowie użytku - połowa pow. rejestrowej
        caly, rej, graf, brak = ru.do_rozliczenia(1.0, 3.0, 2.0)
        self.assertEqual((caly, rej, graf, brak), (False, 1.5, 1.0, False))

    def test_tolerancja_calego(self):
        self.assertTrue(ru.do_rozliczenia(2.0004, 3.0, 2.0)[0])
        self.assertFalse(ru.do_rozliczenia(2.0006, 3.0, 2.0)[0])

    def test_uzytek_bez_grafiki(self):
        self.assertEqual(ru.do_rozliczenia(1.0, 3.0, 0), (False, 0.0, 1.0, True))


class TestZabiegi(unittest.TestCase):
    def test_procent_zostaje_hektary_sie_zmieniaja(self):
        self.assertEqual(ru.zabiegi_po_zmianie(
            [('IB', 2.0, 100), ('PIEL', 1.0, 50)], 2.0, 1.4),
            [('IB', 1.4), ('PIEL', 0.7)])

    def test_bez_procentu_proporcjonalnie(self):
        self.assertEqual(ru.zabiegi_po_zmianie(
            [('X', 1.0, None)], 2.0, 1.0), [('X', 0.5)])

    def test_bez_zmiany_nie_ma_na_liscie(self):
        self.assertEqual(ru.zabiegi_po_zmianie(
            [('IB', 1.4, 100)], 2.0, 1.4), [])

    def test_nie_da_sie_policzyc(self):
        self.assertEqual(ru.zabiegi_po_zmianie(
            [('X', None, None), ('Y', 1.0, None)], 0, 1.0), [])

    def test_pusta_powierzchnia_z_procentem(self):
        self.assertEqual(ru.zabiegi_po_zmianie(
            [('X', None, 100)], 0, 1.5), [('X', 1.5)])


class TestKopie(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.a = os.path.join(self.tmp.name, 'baza.mdb')
        self.b = os.path.join(self.tmp.name, 'WYDZ.shp')
        for sc, tresc in ((self.a, b'a' * 5000), (self.b, b'b' * 300)):
            with open(sc, 'wb') as f:
                f.write(tresc)
        self.z = os.path.join(self.tmp.name, 'kopia.zip')

    def tearDown(self):
        self.tmp.cleanup()

    def test_pakiet_bazy_z_warstwa(self):
        kz.spakuj(self.z, [(self.a, 'baza.mdb'), (self.b, 'WYDZ.shp')])
        with zipfile.ZipFile(self.z) as zf:
            self.assertEqual(sorted(zf.namelist()), ['WYDZ.shp', 'baza.mdb'])
            self.assertIsNone(zf.testzip())
        self.assertLess(os.path.getsize(self.z), 5300)

    def test_blad_nie_zostawia_plikow(self):
        with self.assertRaises(OSError):
            kz.spakuj(self.z, [(self.a, 'baza.mdb'),
                               (self.a + '_brak', 'x')])
        self.assertFalse(os.path.exists(self.z))
        self.assertFalse(os.path.exists(self.z + '.tmp'))

    def test_przywrocenie(self):
        kz.spakuj(self.z, [(self.a, 'baza.mdb')])
        with open(self.a, 'wb') as f:
            f.write(b'zepsuta')
        kz.wypakuj_plik(self.z, 'baza.mdb', self.a)
        with open(self.a, 'rb') as f:
            self.assertEqual(f.read(), b'a' * 5000)


if __name__ == '__main__':
    unittest.main()
