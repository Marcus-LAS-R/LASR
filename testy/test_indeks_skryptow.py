# -*- coding: utf-8 -*-
"""Spójność indeksu skryptów (skrypty/indeks_skryptow.py) z akcjami w
las_r.py + podstawowe wyszukiwania. Bez QGIS-a:
    py testy/test_indeks_skryptow.py   (z katalogu wtyczki)"""
import ast
import importlib.util
import os
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'indeks_skryptow',
    os.path.join(KATALOG, 'skrypty', 'indeks_skryptow.py'))
ix = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ix)


def akcje_las_r():
    """{atrybut: nazwa} - self.X = QAction(..., "nazwa", ...) w las_r.py."""
    with open(os.path.join(KATALOG, 'las_r.py'), encoding='utf-8') as f:
        drzewo = ast.parse(f.read())
    wyn = {}
    for n in ast.walk(drzewo):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and \
                isinstance(n.targets[0], ast.Attribute) and \
                isinstance(n.value, ast.Call) and \
                getattr(n.value.func, 'id', None) == 'QAction':
            teksty = [a.value for a in n.value.args
                      if isinstance(a, ast.Constant) and
                      isinstance(a.value, str)]
            wyn[n.targets[0].attr] = teksty[0] if teksty else ''
    return wyn


class TestIndeks(unittest.TestCase):

    def setUp(self):
        self.akcje = akcje_las_r()
        self.wpisy = [ix.Wpis(k, v, 'Menu' + ' › ' + v)
                      for k, v in self.akcje.items()
                      if k not in ix.POMIJANE]

    def test_kazda_akcja_ma_wpis(self):
        brak = sorted(set(self.akcje) - set(ix.INDEKS) - ix.POMIJANE)
        self.assertEqual(brak, [], 'nowe akcje bez wpisu w INDEKS')

    def test_brak_nieaktualnych_wpisow(self):
        nadmiar = sorted(set(ix.INDEKS) - set(self.akcje))
        self.assertEqual(nadmiar, [], 'wpisy INDEKS bez akcji w las_r.py - '
                         'zmiana identyfikatora? dopisz go do dawne_id')

    def test_dawne_id_nie_koliduja(self):
        for k, v in ix.INDEKS.items():
            for d in v['dawne_id']:
                self.assertNotIn(d, self.akcje, f'{k}: dawne_id {d} żyje')
                self.assertEqual(ix.nowy_id(d), k)

    def test_dawna_nazwa_rozna_od_obecnej(self):
        for k, v in ix.INDEKS.items():
            self.assertNotIn(self.akcje.get(k), v['dawne'], k)

    def _pierwszy(self, zapytanie):
        wyn = ix.szukaj(self.wpisy, zapytanie)
        self.assertTrue(wyn, f'brak wyników dla "{zapytanie}"')
        return wyn[0]

    def test_wyszukiwania(self):
        for zapytanie, oczekiwane in (
                ('kasuj op', {'kas_op'}),
                ('kasuj ls', {'kas_niels'}),
                ('Zaadresuj', {'dop_adrles'}),
                ('przysnapuj', {'a_snapuj_nowy', 'a_snapuj'}),
                ('dociąganie', {'a_snapuj_nowy', 'a_snapuj'}),
                ('utf', {'uutf8'}),
                ('edytor opisu', {'a_opis_taks'}),
                ('klepanie karty', {'przyg_rap', 'przyg_klep'}),
                ('BDL', {'a_pobierz_bdl', 'a_utworz_baze_bdl'})):
            w, _d = self._pierwszy(zapytanie)
            self.assertIn(w.id, oczekiwane, zapytanie)

    def test_dawna_nazwa_w_wyniku(self):
        w, dawna = self._pierwszy('zaadresuj')
        self.assertEqual((w.id, dawna), ('dop_adrles', 'Zaadresuj [ADR_LES]'))

    def test_polskie_znaki(self):
        self.assertEqual(ix.normalizuj('Ściągnij ŁĄKI'), 'sciagnij laki')
        a = [w.id for w, _d in ix.szukaj(self.wpisy, 'sciagnij')]
        self.assertEqual(a[0], 'a_pobierz_bdl')

    def test_wszystkie_slowa(self):
        self.assertEqual(ix.szukaj(self.wpisy, 'kasuj qwertyuiop'), [])


if __name__ == '__main__':
    unittest.main()
