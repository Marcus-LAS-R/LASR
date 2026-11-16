# -*- coding: utf-8 -*-
"""Strony atlasu (kompleksy - siatka z zakładką, reszta w całości) i ich
numeracja (skrypty/kafelkowanie.py). Bez QGIS-a:
    py testy/test_kafelkowanie.py   (z katalogu wtyczki)"""
import importlib.util
import os
import random
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'kafelkowanie', os.path.join(KATALOG, 'skrypty', 'kafelkowanie.py'))
k = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(k)

W, H = 900.0, 1335.0  # A4 pionowo, 1:5000
PROG = 20.0
BEZ_SASIADOW = {'L': 0, 'G': 0, 'P': 0, 'D': 0}


def kompleksy(bboxy):
    """Jak GenerujAtlasAuto._kompleksy, dla prostokątnych wydzieleń."""
    grupy = []
    for i, b in enumerate(bboxy):
        laczy = [g for g in grupy if any(
            k._odstep(b[0], b[2], bboxy[j][0], bboxy[j][2]) <= PROG and
            k._odstep(b[1], b[3], bboxy[j][1], bboxy[j][3]) <= PROG
            for j in g)]
        nowa = [i] + [j for g in laczy for j in g]
        grupy = [g for g in grupy if g not in laczy] + [nowa]
    wyn = []
    for g in grupy:
        bbox = (min(bboxy[i][0] for i in g), min(bboxy[i][1] for i in g),
                max(bboxy[i][2] for i in g), max(bboxy[i][3] for i in g))

        def przecina(s, g=g):
            return any(s[0] < bboxy[i][2] and bboxy[i][0] < s[2] and
                       s[1] < bboxy[i][3] and bboxy[i][1] < s[3] for i in g)
        wyn.append((bbox, przecina, g))
    return wyn


def pokryj(bboxy):
    kafle = k.pokryj_atlas(kompleksy(bboxy), bboxy, W, H)
    strony, sasiedzi = k.numeruj_kafle(kafle)
    kolej = sorted(range(len(kafle)), key=lambda i: strony[i])
    return [kafle[i] for i in kolej], [sasiedzi[i] for i in kolej]


def pokryte(bboxy, kafle, krok=10.0):
    """Czy każdy punkt siatki kontrolnej wewnątrz obiektów leży
    w którejś stronie."""
    for x0, y0, x1, y1 in bboxy:
        x = x0
        while x <= x1:
            y = y0
            while y <= y1:
                if not any(a[0] <= x <= a[2] and a[1] <= y <= a[3]
                           for a in kafle):
                    return False
                y += krok
            x += krok
    return True


def w_calosci(b, kafle):
    return any(a[0] <= b[0] and b[2] <= a[2] and a[1] <= b[1] and
               b[3] <= a[3] for a in kafle)


def kompleks(seed):
    """Zwarty kompleks podzielony na długie wydzielenia wschód-zachód -
    tu tryb "każde wydzielenie w całości" mnożył strony."""
    random.seed(seed)
    bb = []
    kw, kh = 5 * W, 3 * H
    y = 0
    while y < kh:
        hh = random.uniform(0.06, 0.2) * H
        x = 0
        while x < kw:
            ww = random.uniform(0.4, 1.6) * W
            bb.append((x, y, min(x + ww, kw), min(y + hh, kh)))
            x += ww
        y += hh
    return bb


class TestPokryjAtlas(unittest.TestCase):

    def test_maly_obiekt_jedna_wycentrowana_strona(self):
        b = [(100, 100, 300, 200)]
        kafle, sas = pokryj(b)
        self.assertEqual(len(kafle), 1)
        x0, y0, x1, y1 = kafle[0]
        self.assertAlmostEqual((x0 + x1) / 2, 200)
        self.assertAlmostEqual((y0 + y1) / 2, 150)
        self.assertEqual(sas[0], BEZ_SASIADOW)

    def test_rozproszone_w_calosci(self):
        random.seed(1)
        b = []
        for _ in range(40):
            x, y = random.uniform(0, 20000), random.uniform(0, 20000)
            b.append((x, y, x + random.uniform(50, 400),
                      y + random.uniform(50, 400)))
        kafle, _ = pokryj(b)
        stare, _ = k.pokryj_kaflami(b, W, H)
        self.assertEqual(len(kafle), len(stare))
        self.assertTrue(all(w_calosci(x, kafle) for x in b))

    def test_dlugie_wydzielenie_wschod_zachod_jeden_wiersz(self):
        b = [(0, 0, 4.5 * W, 0.5 * H)]
        kafle, sas = pokryj(b)
        # (4.5 - 1) / 0.95 -> 4 kroki -> 5 stron
        self.assertEqual(len(kafle), 5)
        self.assertTrue(pokryte(b, kafle))
        self.assertEqual(len({round(a[1], 6) for a in kafle}), 1)
        for nr, s in enumerate(sas, start=1):
            self.assertEqual(s['L'], nr - 1)
            self.assertEqual(s['P'], nr + 1 if nr < len(kafle) else 0)
            self.assertEqual((s['G'], s['D']), (0, 0))

    def test_zakladka_5_procent(self):
        b = [(0, 0, 3 * W, 2.5 * H)]
        kafle, _ = pokryj(b)
        xs = sorted({round(a[0], 6) for a in kafle})
        ys = sorted({round(a[1], 6) for a in kafle})
        for a, c in zip(xs, xs[1:]):
            self.assertAlmostEqual(c - a, 0.95 * W)
        for a, c in zip(ys, ys[1:]):
            self.assertAlmostEqual(c - a, 0.95 * H)
        self.assertTrue(pokryte(b, kafle))

    def test_zwarty_kompleks_mniej_stron(self):
        for seed in range(3):
            b = kompleks(seed)
            kafle, _ = pokryj(b)
            stare, _ = k.pokryj_kaflami(b, W, H)
            self.assertTrue(pokryte(b, kafle, krok=50.0))
            # 5 x 3 stron przy kroku 0.95 -> 6 x 4 = 24
            self.assertLessEqual(len(kafle), 24)
            self.assertLess(len(kafle), len(stare))

    def test_przerwa_do_20_m_nie_rozbija_kompleksu(self):
        # dwa pasy przedzielone 15-metrową drogą - jeden kompleks
        b = [(0, 0, 1.5 * W, 0.4 * H), (1.5 * W + 15, 0, 3 * W, 0.4 * H)]
        self.assertEqual(len(kompleksy(b)), 1)
        kafle, _ = pokryj(b)
        self.assertTrue(pokryte(b, kafle))
        self.assertEqual(len({round(a[1], 6) for a in kafle}), 1)

    def test_pojedyncze_na_stronie_siatki_bez_osobnej_strony(self):
        duzy = (0, 0, 3 * W, 0.4 * H)
        # mała działka 100 m nad kompleksem, w zasięgu jego strony
        maly = (1000, 0.4 * H + 100, 1100, 0.4 * H + 150)
        kafle, _ = pokryj([duzy, maly])
        bez_malego, _ = pokryj([duzy])
        self.assertEqual(len(kafle), len(bez_malego))
        self.assertTrue(w_calosci(maly, kafle))

    def test_wnetrze_litery_L_pominiete(self):
        b = [(0, 0, 3 * W, 0.4 * H), (0, 0, 0.4 * W, 2.5 * H)]
        kafle, sas = pokryj(b)
        self.assertTrue(pokryte(b, kafle))
        # siatka 4 x 2 w obwiedni, niepustych mniej
        self.assertLess(len(kafle), 8)
        # strona 1 (lewa góra) - z prawej pusto
        self.assertEqual(sas[0]['P'], 0)


class TestNumeracja(unittest.TestCase):

    def test_po_recznym_przesunieciu(self):
        # 2x2 z zakładką, prawy górny przesunięty ręcznie o 30 m
        kafle = [
            (950, -30, 1950, 670 + 0),      # prawy dolny (przesunięty)
            (0, 665, 1000, 1365),           # lewy górny
            (0, 0, 1000, 700),              # lewy dolny
            (980, 690, 1980, 1390),         # prawy górny
        ]
        strony, sas = k.numeruj_kafle(kafle)
        self.assertEqual(strony, [4, 1, 3, 2])
        self.assertEqual(sas[1], {'L': 0, 'G': 0, 'P': 2, 'D': 3})
        self.assertEqual(sas[0], {'L': 3, 'G': 2, 'P': 0, 'D': 0})

    def test_skos_nie_jest_sasiadem(self):
        kafle = [(0, 665, 1000, 1365), (950, 0, 1950, 700)]
        strony, sas = k.numeruj_kafle(kafle)
        self.assertEqual(strony, [1, 2])
        self.assertEqual(sas, [{'L': 0, 'G': 0, 'P': 0, 'D': 0}] * 2)

    def test_dorysowane_odlegle_pole_osobny_zespol(self):
        kafle = [(0, 0, 1000, 700), (950, 0, 1950, 700),
                 (5000, 3000, 6000, 3700)]
        strony, sas = k.numeruj_kafle(kafle)
        self.assertEqual(strony, [2, 3, 1])
        self.assertEqual(sas[2], {'L': 0, 'G': 0, 'P': 0, 'D': 0})
        self.assertEqual(sas[0]['P'], 3)

    def test_pusta_lista(self):
        self.assertEqual(k.numeruj_kafle([]), ([], []))


if __name__ == '__main__':
    unittest.main()
