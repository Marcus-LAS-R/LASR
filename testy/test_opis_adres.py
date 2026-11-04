# -*- coding: utf-8 -*-
"""Adres leśny w Edytorze opisu: wydzielenie Lz. Bez QGIS-a:
    py testy/test_opis_adres.py   (z katalogu wtyczki)"""
import importlib.util
import os
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'opis_adres', os.path.join(KATALOG, 'skrypty', 'opis_adres.py'))
oa = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oa)

PREFIKS = 'T04025'
ADR_LZ = 'T040250024-101   -Lz  -00'
ADR_A = 'T040250024-101   -a   -00'


def docelowy(wydz, adresy=None, adres_bazy=None):
    cz = {'obreb': '0024', 'grp': '10', 'oddz': '1', 'wydz': wydz}
    return oa.docelowy(PREFIKS, cz, ['a', 'b'],
                       adresy if adresy is not None else {ADR_A: 'WYDZIEL'},
                       adres_bazy)


class TestWydzielenieLz(unittest.TestCase):
    def test_kazdy_zapis_to_lz(self):
        for wpis in ('Lz', 'lz', 'LZ', 'lZ', ' Lz '):
            self.assertEqual(oa.normalizuj('wydz', wpis), 'Lz', wpis)

    def test_inne_litery_male(self):
        self.assertEqual(oa.normalizuj('wydz', 'A'), 'a')
        self.assertEqual(oa.normalizuj('wydz', 'AX'), 'ax')
        self.assertEqual(oa.normalizuj('wydz', 'L'), 'l')

    def test_wpisanie_lz_daje_adres(self):
        for wpis in ('Lz', 'lz'):
            self.assertEqual(docelowy(wpis), (ADR_LZ, '', None))

    def test_adres_z_bazy_bez_zmian(self):
        """Zapis karty nie moze przeadresowac Lz na lz."""
        adresy = {ADR_LZ: 'WYDZIEL', ADR_A: 'WYDZIEL'}
        cz = oa.skladowe(ADR_LZ)
        self.assertEqual(cz['wydz'], 'Lz')
        wyn = oa.docelowy(PREFIKS, cz, ['a', 'b'], adresy, ADR_LZ)
        self.assertEqual(wyn, (ADR_LZ, '', None))

    def test_zajety_lz(self):
        adr, blad, _auto = docelowy('lz', {ADR_LZ: 'WYDZIEL'})
        self.assertIsNone(adr)
        self.assertIn('zajęty', blad)

    def test_niepoprawne_wydzielenie(self):
        adr, blad, _auto = docelowy('a1')
        self.assertIsNone(adr)
        self.assertIn('Lz', blad)

    def test_wolna_litera_pomija_zajete(self):
        self.assertEqual(docelowy('')[2], 'b')


if __name__ == '__main__':
    unittest.main()
