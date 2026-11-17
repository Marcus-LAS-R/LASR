# -*- coding: utf-8 -*-
"""Spakuj do opiniowania - część bez QGIS-a. Uruchomienie z katalogu wtyczki:
    py testy/test_spakuj_do_opiniowania.py"""
import importlib.util
import os
import tempfile
import unittest
import zipfile

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    'spakuj_pliki',
    os.path.join(KATALOG, 'skrypty', 'spakuj_do_opiniowania_pliki.py'))
sp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sp)


def _plik(sciezka, rozmiar=10):
    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    with open(sciezka, 'wb') as f:
        f.write(os.urandom(rozmiar))


def _obiekt(korzen):
    """Gmina 042: obręb 0013 komplet (legenda bez A3), 0014 bez operatu,
    do tego pliki, których skrypt nie może wziąć."""
    g = os.path.join(korzen, '042_Debica_OW')
    plot = os.path.join(g, 'PLOTOWANIE', '042_DEBICA')
    _plik(os.path.join(plot, 'Mapy', '0013_STOBIERNA_MAPA_PRZEGLADOWA.pdf'))
    _plik(os.path.join(plot, 'Atlasy', '0013_STOBIERNA_ATLAS.pdf'))
    _plik(os.path.join(plot, 'Atlasy', '0013_STOBIERNA_LEG.pdf'))
    _plik(os.path.join(plot, 'Mapy', '0014_ZAWADA_MAPA_PRZEGLADOWA.pdf'))
    _plik(os.path.join(plot, 'Atlasy', '0014_ZAWADA_ATLAS.pdf'))
    _plik(os.path.join(plot, 'Atlasy', '0014_ZAWADA_LEG_A3.pdf'))
    op = os.path.join(g, 'Operaty_BDO')
    _plik(os.path.join(op, '03-042-0013-Stobierna_BDO.pdf'))
    # nie do wzięcia
    _plik(os.path.join(op, '03-042-0013-Stobierna_BDO.docx'))
    _plik(os.path.join(op, '03-042-0014-Zawada.pdf'))
    _plik(os.path.join(plot, 'arch', '0013_STOBIERNA_MAPA_PRZEGLADOWA.pdf'))
    _plik(os.path.join(g, 'Operaty', '03-042-0013-Stobierna.pdf'))
    return g


def _ob(g, com, nazwa=''):
    return {'folder': g, 'nazwa_folderu': os.path.basename(g),
            'municip': '042', 'community': com, 'nazwa_gminy': 'Dębica gmina',
            'nazwa_obrebu': nazwa}


class TestNazwy(unittest.TestCase):
    def test_bez_polskich(self):
        self.assertEqual(sp.nazwa_pliku('DĘBICA'), 'DEBICA')
        self.assertEqual(sp.nazwa_pliku('GŁOGÓW'), 'GLOGOW')
        self.assertEqual(sp.nazwa_pliku('Czarna Białostocka'),
                         'CZARNA_BIALOSTOCKA')

    def test_ta_sama_nazwa_w_dwoch_rdlp(self):
        n = sp.nazwy_zipow({('04', '08'): {'nazwa': 'GŁOGÓW',
                                           'rdlp': 'KROSNO'},
                            ('13', '08'): {'nazwa': 'GŁOGÓW',
                                           'rdlp': 'WROCŁAW'},
                            ('04', '01'): {'nazwa': 'DĘBICA',
                                           'rdlp': 'KROSNO'}})
        self.assertEqual(n[('04', '08')], 'GLOGOW_KROSNO')
        self.assertEqual(n[('13', '08')], 'GLOGOW_WROCLAW')
        self.assertEqual(n[('04', '01')], 'DEBICA')

    def test_etykieta(self):
        self.assertEqual(sp.etykieta_obrebu(
            {'community': '0002', 'nazwa_obrebu': 'Brzeźnica'}),
            '0002_BRZEZNICA')
        self.assertEqual(sp.etykieta_obrebu(
            {'community': '0002', 'nazwa_obrebu': ''}), '0002')


class TestPodzial(unittest.TestCase):
    def test_ponizej_limitu_jedna_czesc(self):
        self.assertEqual(sp.podziel_na_czesci([('a', 4), ('b', 5)], 10),
                         [['a', 'b']])

    def test_rowno_limit_to_juz_podzial(self):
        self.assertEqual(sp.podziel_na_czesci([('a', 5), ('b', 5)], 10),
                         [['a'], ['b']])

    def test_obiekt_ponad_limit_ma_wlasna_czesc(self):
        self.assertEqual(
            sp.podziel_na_czesci([('a', 3), ('b', 20), ('c', 3)], 10),
            [['a'], ['b'], ['c']])

    def test_pusto(self):
        self.assertEqual(sp.podziel_na_czesci([], 10), [])


class TestPliki(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = _obiekt(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_pliki_obrebu_tylko_wlasciwe(self):
        p = sp.pliki_obrebu(self.g, '042', '0013')
        self.assertEqual([os.path.basename(x) for x in p[sp.MAPY]],
                         ['0013_STOBIERNA_MAPA_PRZEGLADOWA.pdf'])
        self.assertEqual([os.path.basename(x) for x in p[sp.ATLASY]],
                         ['0013_STOBIERNA_ATLAS.pdf',
                          '0013_STOBIERNA_LEG.pdf'])
        self.assertEqual([os.path.basename(x) for x in p[sp.OPERATY]],
                         ['03-042-0013-Stobierna_BDO.pdf'])
        for lista in p.values():
            for sc in lista:
                self.assertNotIn(os.sep + 'arch' + os.sep, sc)

    def test_zwykly_operat_nigdy_nie_wchodzi(self):
        p = sp.pliki_obrebu(self.g, '042', '0014')
        self.assertEqual(p[sp.OPERATY], [])
        self.assertEqual(sp.braki_obrebu(p, (sp.MAPY, sp.ATLASY, sp.OPERATY)),
                         ['operat BDO'])

    def test_legenda_ze_starym_przyrostkiem_a3(self):
        p = sp.pliki_obrebu(self.g, '042', '0014')
        self.assertIn('0014_ZAWADA_LEG_A3.pdf',
                      [os.path.basename(x) for x in p[sp.ATLASY]])

    def test_inna_gmina_nie_pasuje(self):
        p = sp.pliki_obrebu(self.g, '011', '0013')
        self.assertEqual(p, {r: [] for r in sp.RODZAJE})

    def test_dostepne_rodzaje(self):
        self.assertEqual(sp.dostepne_rodzaje([self.g]),
                         set(sp.RODZAJE) - {sp.SHP})
        self.assertEqual(sp.dostepne_rodzaje([]), set())

    def test_x2_obok_zwyklych_pominiety(self):
        plot = os.path.join(self.g, 'PLOTOWANIE', '042_DEBICA')
        _plik(os.path.join(plot, '0013_STOBIERNA_MAPA_PRZEGLADOWA_x2.pdf'))
        _plik(os.path.join(plot, 'Mapy',
                           '0013_STOBIERNA_MAPA_PRZEGLADOWA_X2.pdf'))
        p = sp.pliki_obrebu(self.g, '042', '0013')
        self.assertEqual([os.path.basename(x) for x in p[sp.MAPY]],
                         ['0013_STOBIERNA_MAPA_PRZEGLADOWA.pdf'])
        self.assertFalse(sp.czy_x2('0013_X2OWO_MAPA.pdf'))

    def test_x2_pominiety(self):
        x2 = os.path.join(self.g, 'PLOTOWANIE', '042_DEBICA_x2')
        _plik(os.path.join(x2, '0013_STOBIERNA_MAPA_PRZEGLADOWA.pdf'))
        _plik(os.path.join(x2, 'Mapy', '0013_STOBIERNA_MAPA_PRZEGLADOWA.pdf'))
        p = sp.pliki_obrebu(self.g, '042', '0013')
        self.assertEqual(len(p[sp.MAPY]), 1)
        self.assertNotIn('_x2', p[sp.MAPY][0])

    def test_nazwa_z_plikow(self):
        p = sp.pliki_obrebu(self.g, '042', '0013')
        self.assertEqual(sp.nazwa_obrebu_z_plikow(p, '0013'), 'Stobierna')
        p = sp.pliki_obrebu(self.g, '042', '0014')
        self.assertEqual(sp.nazwa_obrebu_z_plikow(p, '0014'), 'ZAWADA')


class TestBezPodzialu(unittest.TestCase):
    """LCH nie dzieli na Mapy/Atlasy, gdy gmina ma tylko jeden rodzaj -
    PDF-y leżą wprost w folderze gminy."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = os.path.join(self.tmp.name, '042_Debica_OW')
        self.plot = os.path.join(self.g, 'PLOTOWANIE', '042_DEBICA')

    def tearDown(self):
        self.tmp.cleanup()

    def _nazwy(self, p, rodzaj):
        return [os.path.basename(x) for x in p[rodzaj]]

    def test_same_atlasy(self):
        _plik(os.path.join(self.plot, '0013_STOBIERNA_ATLAS.pdf'))
        _plik(os.path.join(self.plot, '0013_STOBIERNA_LEG.pdf'))
        p = sp.pliki_obrebu(self.g, '042', '0013')
        self.assertEqual(self._nazwy(p, sp.ATLASY),
                         ['0013_STOBIERNA_ATLAS.pdf', '0013_STOBIERNA_LEG.pdf'])
        self.assertEqual(p[sp.MAPY], [])
        self.assertNotIn('atlas', sp.braki_obrebu(p, (sp.ATLASY,)))
        self.assertNotIn('legenda', sp.braki_obrebu(p, (sp.ATLASY,)))
        self.assertEqual(sp.dostepne_rodzaje([self.g]), {sp.ATLASY})

    def test_same_mapy(self):
        _plik(os.path.join(self.plot, '0013_STOBIERNA_MAPA_PRZEGLADOWA.pdf'))
        _plik(os.path.join(self.plot, '0013_STOBIERNA_MAPA_TSL_A3.pdf'))
        _plik(os.path.join(self.plot, 'wymiary.txt'))
        p = sp.pliki_obrebu(self.g, '042', '0013')
        self.assertEqual(len(p[sp.MAPY]), 2)
        self.assertEqual(p[sp.ATLASY], [])
        self.assertEqual(sp.dostepne_rodzaje([self.g]), {sp.MAPY})

    def test_rodzaj_po_czlonie_nazwy(self):
        self.assertEqual(sp.rodzaj_z_nazwy('0014_ZAWADA_LEG_A3.pdf'),
                         sp.ATLASY)
        self.assertEqual(sp.rodzaj_z_nazwy('0013_STOBIERNA_ATLAS.pdf'),
                         sp.ATLASY)
        # LEG/ATLAS jako fragment nazwy obrębu to nie legenda
        self.assertEqual(sp.rodzaj_z_nazwy('0005_LEGNICA_MAPA.pdf'), sp.MAPY)
        self.assertEqual(sp.rodzaj_z_nazwy('0005_ATLASOWO_MAPA.pdf'),
                         sp.MAPY)


def _warstwy(katalog, nazwy=sp.WARSTWY_SHP, rozsz=('shp', 'shx', 'dbf')):
    for n in nazwy:
        for r in rozsz:
            _plik(os.path.join(katalog, f'{n}.{r}'))


class TestWarstwySHP(unittest.TestCase):
    """WYDZ_POL/PNSW/ODDZ z _MAPY/<gmina>/<obręb>/SHP."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = _obiekt(self.tmp.name)
        self.mapy = os.path.join(self.g, '_MAPY', '042_DEBICA')
        _warstwy(os.path.join(self.mapy, '0013_STOBIERNA', 'SHP'))
        # nie do wzięcia: inne warstwy, SHP całej gminy, inny obręb
        _warstwy(os.path.join(self.mapy, '0013_STOBIERNA', 'SHP'),
                 ('WYDZ', 'WYDZ_POL_stare'))
        _warstwy(os.path.join(self.g, '_MAPY', 'SHP'))
        _warstwy(os.path.join(self.mapy, '0014_ZAWADA', 'SHP'), ('ODDZ',))

    def tearDown(self):
        self.tmp.cleanup()

    def _nazwy(self, com):
        p = sp.pliki_obrebu(self.g, '042', com)
        return p, [os.path.basename(x) for x in p[sp.SHP]]

    def test_tylko_trzy_warstwy_obrebu(self):
        _, nazwy = self._nazwy('0013')
        self.assertEqual(len(nazwy), 9)
        self.assertEqual({os.path.splitext(n)[0] for n in nazwy},
                         set(sp.WARSTWY_SHP))

    def test_braki_warstw(self):
        p, _ = self._nazwy('0014')
        self.assertEqual(sp.braki_obrebu(p, (sp.SHP,)),
                         ['WYDZ_POL.shp', 'PNSW.shp'])
        p, _ = self._nazwy('0013')
        self.assertEqual(sp.braki_obrebu(p, (sp.SHP,)), [])

    def test_robocze_gdy_brak_glownego(self):
        rob = os.path.join(self.g, '_MAPY', '_ROBOCZE', '042_DEBICA',
                           '0015_LUBZINA', 'SHP')
        _warstwy(rob, ('PNSW',))
        _, nazwy = self._nazwy('0015')
        self.assertEqual(nazwy, ['PNSW.dbf', 'PNSW.shp', 'PNSW.shx'])

    def test_dostepne(self):
        self.assertIn(sp.SHP, sp.dostepne_rodzaje([self.g]))

    def test_w_zipie_podfolder_shp(self):
        ob = _ob(self.g, '0013', 'Stobierna')
        plan = sp.zaplanuj({'A': {'k'}}, {'k': ob},
                           {'A': {'nazwa': 'DĘBICA', 'rdlp': ''}},
                           (sp.MAPY, sp.SHP))
        sciezki = [a for _, a in plan[0]['czesci'][0]['pliki']]
        self.assertIn('042_Debica_OW/0013_STOBIERNA/SHP/WYDZ_POL.shp',
                      sciezki)
        self.assertIn('042_Debica_OW/0013_STOBIERNA/'
                      '0013_STOBIERNA_MAPA_PRZEGLADOWA.pdf', sciezki)


class TestPlanIZip(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = _obiekt(self.tmp.name)
        self.wyn = os.path.join(self.tmp.name, 'wynik')
        os.makedirs(self.wyn)
        self.ob = {('g', '042', '0013'): _ob(self.g, '0013', 'Stobierna'),
                   ('g', '042', '0014'): _ob(self.g, '0014')}
        self.nadl = {'A': {'nazwa': 'DĘBICA', 'rdlp': 'KROSNO'},
                     'B': {'nazwa': 'STRZYŻÓW', 'rdlp': 'KROSNO'}}
        # 0014 wspólny dla obu nadleśnictw
        self.przyp = {'A': set(self.ob), 'B': {('g', '042', '0014')}}

    def tearDown(self):
        self.tmp.cleanup()

    def _plan(self, rodzaje=sp.RODZAJE, limit=sp.LIMIT_ZIP):
        return sp.zaplanuj(self.przyp, self.ob, self.nadl, rodzaje, limit)

    def test_wspolny_obreb_w_obu_zipach(self):
        plan = self._plan()
        self.assertEqual([p['stem'] for p in plan], ['DEBICA', 'STRZYZOW'])
        self.assertEqual(plan[0]['czesci'][0]['plik'], 'DEBICA.zip')
        for p in plan:
            sciezki = [a for _, a in p['czesci'][0]['pliki']]
            self.assertTrue(any('0014_ZAWADA' in a for a in sciezki))

    def test_podzial_trzyma_obreb_w_jednej_czesci(self):
        # limit mniejszy niż dwa obręby: mapy i operat obrębu razem
        plan = self._plan(limit=45)
        cz = plan[0]['czesci']
        self.assertEqual([c['plik'] for c in cz],
                         ['DEBICA_1.zip', 'DEBICA_2.zip'])
        self.assertEqual(cz[0]['obreby'][0]['community'], '0013')
        self.assertEqual(len(cz[0]['pliki']), 4)  # mapa, atlas, leg., operat
        self.assertEqual(cz[1]['obreby'][0]['community'], '0014')

    def test_wybor_rodzajow(self):
        plan = self._plan(rodzaje=(sp.OPERATY,))
        pliki = [a for _, a in plan[0]['czesci'][0]['pliki']]
        self.assertEqual(pliki, ['042_Debica_OW/0013_STOBIERNA/'
                                 '03-042-0013-Stobierna_BDO.pdf'])
        # STRZYŻÓW: jedyny obręb bez operatu - brak ZIP-a, ale w planie jest
        self.assertEqual(plan[1]['czesci'], [])
        self.assertEqual(len(plan[1]['obreby']), 1)

    def test_zip_powstaje_bez_tmp(self):
        cz = self._plan()[0]['czesci'][0]
        self.assertEqual(sp.spakuj_czesc(self.wyn, cz), [])
        self.assertEqual(os.listdir(self.wyn), ['DEBICA.zip'])
        with zipfile.ZipFile(os.path.join(self.wyn, 'DEBICA.zip')) as z:
            self.assertIn('042_Debica_OW/0013_STOBIERNA/'
                          '03-042-0013-Stobierna_BDO.pdf', z.namelist())
            self.assertIsNone(z.testzip())

    def test_przerwanie_nie_zostawia_pliku(self):
        cz = self._plan()[0]['czesci'][0]
        with self.assertRaises(sp.Przerwano):
            sp.spakuj_czesc(self.wyn, cz, lambda _: False)
        self.assertEqual(os.listdir(self.wyn), [])

    def test_istniejace_wyniki(self):
        for n in ('DEBICA.zip', 'DEBICA_2.zip', 'DEBICA_X.zip', 'INNE.zip',
                  sp.PLIK_XLSX):
            _plik(os.path.join(self.wyn, n))
        self.assertEqual(
            sp.istniejace_wyniki(self.wyn, self._plan()),
            sorted(['DEBICA.zip', 'DEBICA_2.zip', sp.PLIK_XLSX]))

    def test_opis_zawiera_braki_i_wspolny_obreb(self):
        opis = sp.opis_planu(self._plan(), [], [], sp.RODZAJE)
        self.assertIn('DEBICA.zip', opis)
        self.assertIn('STRZYZOW.zip', opis)
        self.assertIn('0014 ZAWADA: operat BDO', opis)


if __name__ == '__main__':
    unittest.main()
