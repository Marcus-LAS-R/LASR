# -*- coding: utf-8 -*-
"""Utwórz płyty na oddanie - część bez QGIS-a. Uruchomienie z katalogu
wtyczki:
    py testy/test_plyty_na_oddanie.py"""
import importlib.util
import os
import sys
import tempfile
import time
import unittest

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KATALOG, 'skrypty'))
_spec = importlib.util.spec_from_file_location(
    'plyty_pliki',
    os.path.join(KATALOG, 'skrypty', 'plyty_na_oddanie_pliki.py'))
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)


def _plik(sciezka, rozmiar=10):
    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    with open(sciezka, 'wb') as f:
        f.write(os.urandom(rozmiar))
    return sciezka


def _gmina(korzen, folder, municip, obreby, baza=True):
    """Folder gminy jak w oddaniu: PLOTOWANIE (mapy, atlasy), Operaty
    (pdf, docx), Operaty_BDO, baza .mdb, _MAPY/<gmina>/<obręb>/SHP,
    _MAPY/<gmina>/OGOLNE."""
    g = os.path.join(korzen, folder)
    plot = os.path.join(g, 'PLOTOWANIE', f'{municip}_GMINA')
    mapy = os.path.join(g, '_MAPY', f'{municip}_GMINA')
    for com, nazwa in obreby:
        _plik(os.path.join(plot, 'Mapy', f'{com}_{nazwa}_MAPA_PRZEGLADOWA.pdf'))
        _plik(os.path.join(plot, 'Atlasy', f'{com}_{nazwa}_ATLAS.pdf'))
        _plik(os.path.join(g, 'Operaty', f'17-{municip}-{com}-{nazwa}.pdf'))
        _plik(os.path.join(g, 'Operaty', f'17-{municip}-{com}-{nazwa}.docx'))
        _plik(os.path.join(g, 'Operaty', f'~$-{municip}-{com}.docx'))
        _plik(os.path.join(g, 'Operaty_BDO',
                           f'17-{municip}-{com}-{nazwa}_BDO.pdf'))
        _plik(os.path.join(g, 'Operaty_BDO',
                           f'17-{municip}-{com}-{nazwa}_BDO.docx'))
        for w in ('WYDZ_POL', 'ODDZ'):
            for r in ('.shp', '.dbf', '.shx'):
                _plik(os.path.join(mapy, f'{com}_{nazwa}', 'SHP', w + r))
    _plik(os.path.join(mapy, 'OGOLNE', 'DROGI_LFT.shp'))
    _plik(os.path.join(mapy, 'OGOLNE', 'DROGI_LFT.dbf'))
    if baza:
        stara = _plik(os.path.join(g, f'{folder}_stara.mdb'))
        teraz = time.time()
        os.utime(stara, (teraz - 1000, teraz - 1000))
        _plik(os.path.join(g, f'{folder}_14.10.2026.mdb'))
        _plik(os.path.join(g, f'{folder}_BDO.mdb'))
        _plik(os.path.join(g, 'arch', 'najnowsza_w_archiwum.mdb'))
    return g


def _ob(g, municip, com, nazwa=''):
    return {'folder': g, 'nazwa_folderu': os.path.basename(g),
            'municip': municip, 'community': com, 'nazwa_obrebu': nazwa}


WSZYSTKO = {k: True for k in pp.KLUCZE}
CALOSC = pp.DOMYSLNE_PLYT[pp.CALOSC]


def _przygotowanie(korzen, nazwa):
    """Bazy/SHP jak po przygotowaniu (na niby)."""
    przyg = os.path.join(korzen, 'przyg')
    for p in (f'{nazwa}.mdb', f'{nazwa}_anonim.mdb'):
        _plik(os.path.join(przyg, nazwa, pp.BAZY, p))
    for p in ('WYDZ_POL.shp', 'WYDZ_POL.dbf', 'OGOLNE/DROGI_LFT.shp'):
        _plik(os.path.join(przyg, nazwa, pp.SHP, p))
    return przyg


class TestNazwy(unittest.TestCase):
    def test_nazwa_czesci(self):
        self.assertEqual(pp.nazwa_czesci('301703', '035', 'Odolanow'),
                         '301703_5_Odolanow_OW')
        self.assertEqual(pp.nazwa_czesci('120509', '092', 'Sekowa'),
                         '120509_2_Sekowa')
        self.assertEqual(pp.nazwa_czesci('', '035', 'Odolanow',
                                         '035 Odolanów OW'),
                         '035_Odolanow_OW')

    def test_plyty_gmin(self):
        n = pp.nazwy_plyt_gmin({'301703': 'Odolanow', '301701': 'Lipno',
                                '041001': 'Lipno'})
        self.assertEqual(n['301703'], 'Gm.Odolanow')
        self.assertEqual(n['301701'], 'Gm.Lipno_301701')

    def test_domyslne_list(self):
        for p in (pp.CALOSC, pp.GMINY):
            d = pp.DOMYSLNE_PLYT[p]
            self.assertFalse(d['sulmn'])
            self.assertFalse(d['raporty'])
            self.assertTrue(all(v for k, v in d.items()
                                if k not in ('sulmn', 'raporty')))
        self.assertEqual(sorted(k for k, v in
                                pp.DOMYSLNE_PLYT[pp.PGLLP].items() if v),
                         ['atlasy', 'mapy', 'operaty_bdo'])
        s = pp.suma_opcji(pp.DOMYSLNE_PLYT[pp.PGLLP], {'sulmn': True})
        self.assertTrue(s['sulmn'] and s['mapy'])
        self.assertFalse(s['bazy'])

    def test_podfoldery(self):
        self.assertEqual(pp.podfoldery_plyty(pp.DOMYSLNE_PLYT[pp.PGLLP]),
                         ('Operaty_BDO', 'Mapy', 'Atlasy'))
        o = dict(CALOSC, bazy=False, anonim=False, shp=False, mapy=False)
        # same pliki ogólne -> SHP/OGOLNE
        self.assertEqual(pp.podfoldery_plyty(o),
                         ('SHP', 'Operaty', 'Operaty_BDO', 'Atlasy'))
        self.assertNotIn('SHP', pp.podfoldery_plyty(dict(o, ogolne=False)))


class TestPliki(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        k = self.tmp.name
        self.m = _gmina(k, '301703_4_Odolanow_M', '034', [('0001', 'ODOLANOW')])
        self.ow = _gmina(k, '301703_5_Odolanow_OW', '035',
                         [('0002', 'GARKI'), ('0003', 'GLISNICA')])
        self.g = _gmina(k, '120509_2_Sekowa', '092', [('0004', 'BARTNE')],
                        baza=False)
        self.gminy = {
            '301703': {'nazwa': 'Odolanow', 'obreby': [
                _ob(self.ow, '035', '0003'), _ob(self.m, '034', '0001'),
                _ob(self.ow, '035', '0002', 'Garki')]},
            '120509': {'nazwa': 'Sekowa', 'obreby': [
                _ob(self.g, '092', '0004')]}}

    def tearDown(self):
        self.tmp.cleanup()

    def _czesci(self, opcje=WSZYSTKO):
        return [pp.uzupelnij_czesc(c, opcje)
                for c in pp.czesci_z_gmin(self.gminy)]

    def test_baza_najnowsza_z_glownego(self):
        bazy = pp.bazy_folderu(self.ow)
        self.assertEqual([os.path.basename(b) for b in bazy],
                         ['301703_5_Odolanow_OW_14.10.2026.mdb',
                          '301703_5_Odolanow_OW_stara.mdb'])

    def test_docx(self):
        zw, bdo = pp.docx_obrebu(self.ow, '035', '0002')
        self.assertEqual([os.path.basename(p) for p in zw],
                         ['17-035-0002-GARKI.docx'])
        self.assertEqual([os.path.basename(p) for p in bdo],
                         ['17-035-0002-GARKI_BDO.docx'])

    def test_czesci_i_pliki(self):
        cz = self._czesci()
        self.assertEqual([c['nazwa'] for c in cz],
                         ['120509_2_Sekowa', '301703_4_Odolanow_M',
                          '301703_5_Odolanow_OW'])
        ow = cz[2]
        self.assertEqual([o['community'] for o in ow['obreby']],
                         ['0002', '0003'])
        self.assertEqual({k: len(v) for k, v in ow['pliki'].items()},
                         {'operaty': 2, 'operaty_docx': 2, 'operaty_bdo': 2,
                          'operaty_bdo_docx': 2, 'mapy': 2, 'atlasy': 2})
        self.assertEqual(sorted(ow['shp']), ['ODDZ', 'WYDZ_POL'])
        self.assertEqual(len(ow['shp']['WYDZ_POL']), 2)
        self.assertEqual(len(ow['ogolne']), 2)
        self.assertEqual(ow['braki'], [])
        self.assertIn('BRAK BAZY', cz[0]['braki'][0])
        # wyłączone pozycje - nie szukane i bez braków
        bez = pp.uzupelnij_czesc(pp.czesci_z_gmin(self.gminy)[0],
                                 pp.DOMYSLNE_PLYT[pp.PGLLP])
        self.assertEqual(bez['pliki']['operaty'], [])
        self.assertEqual(bez['shp'], {})
        self.assertEqual(bez['braki'], [])

    def test_pliki_wg_listy_plyty(self):
        cz = self._czesci()
        ow = cz[2]
        plan = pp.zaplanuj(cz, pp.PLYTY, None, {
            pp.CALOSC: dict(CALOSC, docx=False),
            pp.PGLLP: dict(pp.DOMYSLNE_PLYT[pp.PGLLP], docx=True)})
        cal, pgl = plan[0], plan[-1]
        n = sorted(os.path.basename(w) for _, w in pp.pliki_czesci(cal, ow))
        self.assertFalse(any(x.endswith('.docx') for x in n))
        self.assertEqual(len(n), 8)
        n = [w for _, w in pp.pliki_czesci(pgl, ow)]
        self.assertTrue(all(w.split(os.sep)[0] in ('Operaty_BDO', 'Mapy',
                                                   'Atlasy') for w in n))
        self.assertEqual(sum(w.endswith('_BDO.docx') for w in n), 2)

    def test_plan_i_kopiowanie(self):
        cz = self._czesci()
        sulmn = _plik(os.path.join(self.tmp.name, 'SULMN.pdf'))
        opcje = {pp.CALOSC: dict(CALOSC, sulmn=True, raporty=True,
                                 anonim=False),
                 pp.GMINY: dict(pp.DOMYSLNE_PLYT[pp.GMINY], bazy=False),
                 pp.PGLLP: dict(pp.DOMYSLNE_PLYT[pp.PGLLP], sulmn=True)}
        plan = pp.zaplanuj(cz, pp.PLYTY, sulmn, opcje)
        self.assertEqual([p['nazwa'] for p in plan],
                         ['Calosciowa', 'Gm.Odolanow', 'Gm.Sekowa', 'PGLLP'])
        self.assertEqual([c['nazwa'] for c in plan[1]['czesci']],
                         ['301703_4_Odolanow_M', '301703_5_Odolanow_OW'])
        self.assertIsNone(plan[1]['sulmn'])
        self.assertTrue(pp.potrzebne_przygotowanie(plan))
        self.assertFalse(pp.potrzebne_przygotowanie(
            pp.zaplanuj(cz, [pp.PGLLP], sulmn)))

        przyg = _przygotowanie(self.tmp.name, '301703_5_Odolanow_OW')
        wyn = os.path.join(self.tmp.name, 'wynik')
        os.makedirs(os.path.join(wyn, 'Calosciowa', 'stary'))
        ist = pp.istniejace_wyniki(wyn, plan)
        self.assertEqual(ist, ['Calosciowa'])
        for p in plan:
            self.assertEqual(pp.kopiuj_plyte(wyn, p, przyg), [])
        self.assertEqual(pp.podmien(wyn, plan, ist), [])
        self.assertEqual(sorted(os.listdir(wyn)),
                         ['Calosciowa', 'Gm.Odolanow', 'Gm.Sekowa', 'PGLLP'])
        cal = os.path.join(wyn, 'Calosciowa')
        self.assertEqual(sorted(os.listdir(cal)),
                         ['120509_2_Sekowa', '301703_4_Odolanow_M',
                          '301703_5_Odolanow_OW', 'SULMN.pdf'])
        ow = os.path.join(cal, '301703_5_Odolanow_OW')
        self.assertEqual(sorted(os.listdir(ow)),
                         ['Atlasy', 'Bazy_danych', 'Mapy', 'Operaty',
                          'Operaty_BDO', 'Raporty', 'SHP'])
        self.assertEqual(os.listdir(os.path.join(ow, 'Raporty')), [])
        # Całościowa: tylko zwykła baza; gminy: tylko anonim, bez Raportów
        self.assertEqual(os.listdir(os.path.join(ow, 'Bazy_danych')),
                         ['301703_5_Odolanow_OW.mdb'])
        gow = os.path.join(wyn, 'Gm.Odolanow', '301703_5_Odolanow_OW')
        self.assertEqual(os.listdir(os.path.join(gow, 'Bazy_danych')),
                         ['301703_5_Odolanow_OW_anonim.mdb'])
        self.assertNotIn('Raporty', os.listdir(gow))
        self.assertTrue(os.path.isfile(os.path.join(
            ow, 'SHP', 'OGOLNE', 'DROGI_LFT.shp')))
        pgl = os.path.join(wyn, 'PGLLP', '301703_5_Odolanow_OW')
        self.assertEqual(sorted(os.listdir(pgl)),
                         ['Atlasy', 'Mapy', 'Operaty_BDO'])
        self.assertTrue(os.path.isfile(os.path.join(wyn, 'PGLLP',
                                                    'SULMN.pdf')))
        self.assertNotIn('SULMN.pdf', os.listdir(os.path.join(
            wyn, 'Gm.Odolanow')))

    def test_podzial_po_gminach(self):
        cz = self._czesci()
        sulmn = _plik(os.path.join(self.tmp.name, 'SULMN.pdf'), 5)
        plan = pp.zaplanuj(cz, [pp.CALOSC, pp.PGLLP], sulmn, {
            pp.CALOSC: CALOSC,
            pp.PGLLP: dict(pp.DOMYSLNE_PLYT[pp.PGLLP], sulmn=True)})
        rozm = {p['nazwa']: pp.rozmiar_plyty(p) for p in plan}
        # PGLLP: Sekowa 3 pliki, M 3 pliki, OW 6 plików (po 10 B) + SULMN
        self.assertEqual(rozm['PGLLP'], 125)
        limit = 80
        self.assertEqual(sorted(pp.za_duze(plan, limit=limit)),
                         ['Calosciowa', 'PGLLP'])
        nowy = pp.podziel_plyty(plan, limit=limit)
        pg = [p for p in nowy if p['nazwa'].startswith('PGLLP')]
        self.assertEqual([p['nazwa'] for p in pg], ['PGLLP_1', 'PGLLP_2'])
        self.assertEqual([[c['nazwa'] for c in p['czesci']] for p in pg],
                         [['120509_2_Sekowa', '301703_4_Odolanow_M'],
                          ['301703_5_Odolanow_OW']])
        self.assertTrue(all(p['sulmn'] == sulmn for p in pg))
        self.assertEqual(pp.za_duze(pg, limit=limit), {})
        wyn = os.path.join(self.tmp.name, 'wynik')
        for n in ('PGLLP_1', 'PGLLP_2', 'PGLLP_x', 'Calosciowa'):
            os.makedirs(os.path.join(wyn, n))
        self.assertEqual(pp.istniejace_wyniki(wyn, plan),
                         ['Calosciowa', 'PGLLP_1', 'PGLLP_2'])

    def test_przerwanie(self):
        p = pp.zaplanuj(self._czesci(), [pp.PGLLP])[0]
        wyn = os.path.join(self.tmp.name, 'wynik')
        os.makedirs(wyn)
        with self.assertRaises(pp.Przerwano):
            pp.kopiuj_plyte(wyn, p, None, lambda _: False)
        self.assertEqual(os.listdir(wyn), [])

    def test_opis_i_ostrzezenie(self):
        cz = self._czesci()
        plan = pp.zaplanuj(cz, [pp.CALOSC])
        opis = pp.opis_planu(plan, cz, rozmiary={'Calosciowa': 5 * 10 ** 9})
        self.assertIn('Calosciowa (Całościowa) - 3 gmin, 5,00 GB', opis)
        self.assertIn('nie zmieści się na DVD', opis)
        self.assertIn('wgrywane: Bazy danych - zwykłe', opis)
        self.assertNotIn('Plik SULMN', opis)
        self.assertIn('BRAK: BRAK BAZY', opis)
        self.assertIn('starsze bazy: 301703_5_Odolanow_OW_stara.mdb', opis)
        self.assertNotIn('nie zmieści', pp.opis_planu(plan, cz))
        bez = pp.opis_planu(plan, cz, limit=None,
                            rozmiary={'Calosciowa': 5 * 10 ** 9})
        self.assertNotIn('nie zmieści', bez)
        self.assertIn('brak limitu', bez)


if __name__ == '__main__':
    unittest.main()
