# -*- coding: utf-8 -*-
"""Plan przemianowania grupy w adresach leśnych (skrypty/grupa_adresu.py).
Bez QGIS-a:
    py testy/test_grupa_adresu.py   (z katalogu wtyczki)"""
import importlib.util
import os
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'grupa_adresu', os.path.join(KATALOG, 'skrypty', 'grupa_adresu.py'))
ga = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ga)

S = 'K110620003-101   '   # stara grupa 10, oddz 1
N = 'K110620003-991   '   # nowa grupa 99, oddz 1


def w(pref, lit):
    return f'{pref}-{lit}   -00'


def o(pref):
    return f'{pref}-    -  '


class TestPlan(unittest.TestCase):

    def test_adres_oddzialu(self):
        self.assertEqual(ga.adres_oddzialu(w(N, 'a')), o(N))
        self.assertEqual(len(ga.adres_oddzialu(w(N, 'a'))), 25)

    def test_sama_zmiana_grupy(self):
        baza = {o(S): 'ODDZ', w(S, 'b'): 'WYDZIEL', w(S, 'c'): 'WYDZIEL',
                'K110620003-      -    -  ': 'L-CTWO',
                'K11062    -      -    -  ': 'OBRĘB'}
        plan = ga.plan_przemianowania(baza, [w(N, 'b'), w(N, 'c')])
        self.assertEqual(sorted(plan['zmiany']), sorted([
            (o(S), o(N)), (w(S, 'b'), w(N, 'b')), (w(S, 'c'), w(N, 'c'))]))
        self.assertEqual(plan['kolizje'], [])
        self.assertEqual(plan['bez_pary'], [])

    def test_kolizja_z_pustym_duplikatem(self):
        # stan Zawodzia: nowe adresy dopisane do bazy obok starych
        baza = {w(S, 'b'): 'WYDZIEL', w(N, 'b'): 'WYDZIEL',
                o(S): 'ODDZ', o(N): 'ODDZ'}
        plan = ga.plan_przemianowania(baza, [w(N, 'b')])
        self.assertEqual(plan['zmiany'], [])
        self.assertEqual(sorted(plan['kolizje']),
                         sorted([(w(S, 'b'), w(N, 'b')), (o(S), o(N))]))
        self.assertEqual(plan['zgodne'], 2)

    def test_bez_pary_i_zgodne(self):
        baza = {w(S, 'x'): 'WYDZIEL', w(N, 'a'): 'WYDZIEL'}
        plan = ga.plan_przemianowania(baza, [w(N, 'a')])
        self.assertEqual(plan['bez_pary'], [w(S, 'x')])
        self.assertEqual(plan['zgodne'], 1)

    def test_niejednoznaczne(self):
        baza = {w('K110620003-101   ', 'b'): 'WYDZIEL'}
        graf = [w('K110620003-991   ', 'b'), w('K110620003-051   ', 'b')]
        plan = ga.plan_przemianowania(baza, graf)
        self.assertEqual(len(plan['niejednoznaczne']), 1)
        self.assertEqual(plan['zmiany'], [])

    def test_bledy_grup(self):
        na_kilku, rozne = ga.bledy_grup([
            ('a', '99', '99'), ('b', '99', '99'), ('b', '99', '10'),
            ('c', '10', '99'), ('d', '99', '99')])
        self.assertEqual(na_kilku, {'b': {'99', '10'}})
        self.assertEqual(rozne, {'c': ('10', {'99'})})


if __name__ == '__main__':
    unittest.main()
