# -*- coding: utf-8 -*-
"""Przygotuj Lsy: utrata geometrii, dopasowanie do bazy, kontrole, raport.
Wymaga PyQGIS (bez GRASS-a, baz i okien):
    python-qgis-ltr.bat testy/test_przygotuj_ls.py   (z katalogu wtyczki)"""
import os
import sys
import tempfile
import types
import unittest
import warnings

warnings.simplefilter('ignore', DeprecationWarning)
sys.dont_write_bytecode = True

KATALOG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# pakiet bez __init__.py wtyczki (ten wymaga iface)
_pkg = types.ModuleType('lasr')
_pkg.__path__ = [KATALOG]
sys.modules['lasr'] = _pkg

from qgis.core import (  # noqa: E402
    NULL, QgsApplication, QgsFeature, QgsField, QgsFields, QgsGeometry,
    QgsPointXY, QgsVectorFileWriter, QgsVectorLayer)
from PyQt5.QtCore import QVariant  # noqa: E402

app = QgsApplication([], False)
app.initQgis()

from lasr.skrypty.baza_przetworz import Przetworz  # noqa: E402
from lasr.skrypty.funkcje import usun_wasy  # noqa: E402
from lasr.skrypty.przygotuj_ls import (  # noqa: E402
    AnalizujKlus, GenerujRaport, PrzetworzKlu)
from lasr.skrypty.przygotuj_ls_test import PrzetworzKluTest  # noqa: E402

PID = '24070620003.5821'


def kw(x, y, bok):
    return QgsGeometry.fromWkt(
        f'POLYGON(({x} {y},{x+bok} {y},{x+bok} {y+bok},{x} {y+bok},{x} {y}))')


def wiersz(au, sq, pow_u, pow_dz=1.0, pid=PID):
    r = [None] * 13
    r[0], r[1] = pid[:2], pid[2:4]
    r[6], r[7], r[9], r[10], r[11], r[12] = 1, pow_dz, au, sq, pow_u, pid
    return r


WLASC = [[1, 'KOWALSKI', 'OF', '24', '07', '062', '0003', None, '5821']]


def baza(uzytki, wlasnosci=None, **kw_p):
    p = Przetworz(**kw_p)
    p.dodaj_uzytki(uzytki)
    p.dodaj_wlasnosci(WLASC if wlasnosci is None else wlasnosci)
    p.przetworz_dzialki()
    p.przetworz_uzytkowanie()
    return p


def dzialka(pid=PID, bok=100, pow_rej=1.0):
    fs = QgsFields()
    fs.append(QgsField('PARCELID', QVariant.String))
    fs.append(QgsField('PARCEL_AR', QVariant.Double))
    f = QgsFeature(fs)
    f['PARCELID'] = pid
    f['PARCEL_AR'] = pow_rej
    f.setGeometry(kw(0, 0, bok))
    return f


def kawalki_klu(lista):
    """[(au, sq, pow_m2), ...] -> rozlaczne kwadraty jak po GRASS-ie."""
    lyr = QgsVectorLayer(
        'Polygon?crs=epsg:2180&field=PARCELID:string&field=AU:string'
        '&field=SQ:string', 'k', 'memory')
    wyn = []
    for i, (au, sq, pow_m2) in enumerate(lista):
        f = QgsFeature(lyr.fields())
        f.setId(i)
        f.setAttributes([PID, au, sq])
        f.setGeometry(kw(i * 200, 0, pow_m2 ** .5))
        wyn.append(f)
    return wyn


class Bar:
    def __init__(self):
        self.komunikaty = []

    def clearWidgets(self):
        pass

    def pushMessage(self, *a):
        self.komunikaty.append(a)

    def pushWarning(self, *a):
        self.komunikaty.append(a)


class Iface:
    def __init__(self):
        self.bar = Bar()

    def messageBar(self):
        return self.bar


class TestUsunWasy(unittest.TestCase):
    def multi(self, *wkt):
        return QgsGeometry.collectGeometry(
            [QgsGeometry.fromWkt(w) for w in wkt])

    def test_trojkat_domykany_na_zachod_nie_znika(self):
        """Bodzentyn, 814/1: 251 m2 znikalo przy laczeniu czesci Ls."""
        g = self.multi(
            'POLYGON((0 0,50 0,50 50,0 50,0 0))',
            'POLYGON((633022.291 351020.873,633030.455 351037.664,'
            '633052.054 351020.561,633022.291 351020.873))')
        w = usun_wasy(g)
        self.assertAlmostEqual(w.area(), g.area(), 2)
        self.assertEqual(len(w.asMultiPolygon()), 2)
        self.assertTrue(w.isGeosValid())

    def test_krawedzie_rownolegle_do_osi_zostaja(self):
        g = self.multi('POLYGON((0 0,10 0,10 10,0 10,0 0))')
        self.assertAlmostEqual(usun_wasy(g).area(), 100, 6)

    def test_dluga_igla_nie_jest_wasem(self):
        """Ostry klin ma realna powierzchnie (8.1556/4: 140 m2)."""
        g = self.multi('POLYGON((0 0,200 1.5,0 3,-50 3,-50 0,0 0))')
        self.assertAlmostEqual(usun_wasy(g).area(), g.area(), 3)

    def test_prawdziwy_was_jest_usuwany(self):
        g = self.multi('POLYGON((0 0,10 0,10 5,15 5.001,10 5.002,'
                       '10 10,0 10,0 0))')
        w = usun_wasy(g)
        self.assertAlmostEqual(w.area(), 100, 1)
        self.assertEqual(len(w.asMultiPolygon()[0][0]), 7)

    def test_otwor_zostaje(self):
        g = self.multi('POLYGON((0 0,30 0,30 30,0 30,0 0),'
                       '(10 10,20 10,20 20,10 20,10 10))')
        self.assertAlmostEqual(usun_wasy(g).area(), 800, 6)

    def test_brak_pustych_czesci(self):
        g = self.multi('POLYGON((0 0,10 0,10 10,0 10,0 0))',
                       'POLYGON((50 50,60 50,60 50,50 50))')
        w = usun_wasy(g)
        self.assertEqual(len(w.asMultiPolygon()), 1)
        self.assertTrue(w.isGeosValid())


class TestMikro(unittest.TestCase):
    def przebieg(self, kawalki):
        o = PrzetworzKlu(dzialka(bok=300), [],
                         baza([wiersz('Ls', 'V', .012)]))
        o.pid = PID
        for i, (au, sq, pow_m2) in enumerate(kawalki):
            f = o.new_feat(au, sq, '')
            f.setGeometry(kw(i * 100, 0, pow_m2 ** .5))
            o.klus_popr.append(f)
        o.sprawdz_mikro()
        o.polacz_ostateczne()
        return o

    def pow_ls(self, o):
        return (sum(f.geometry().area() for f in o.poprawne.values()
                    if f['AU'] == 'Ls') +
                sum(f.geometry().area() for f in o.klus_do_spr
                    if f['AU'] == 'Ls'))

    def test_istotny_mikrus_nie_znika(self):
        o = self.przebieg([('Ls', 'V', 100), ('Ls', 'V', 20), ('R', 'V', 2500)])
        self.assertAlmostEqual(self.pow_ls(o), 120, 3)

    def test_caly_ls_z_mikrusow_zostaje(self):
        o = self.przebieg([('Ls', 'V', 15), ('Ls', 'V', 15), ('R', 'V', 2500)])
        self.assertIn(PID + '.LsV', o.poprawne)
        self.assertAlmostEqual(self.pow_ls(o), 30, 3)

    def test_kolejnosc_nie_zmienia_wyniku(self):
        o = self.przebieg([('Ls', 'V', 15), ('Ls', 'V', 100), ('R', 'V', 2500)])
        self.assertAlmostEqual(
            o.poprawne[PID + '.LsV'].geometry().area(), 100, 3)
        self.assertAlmostEqual(self.pow_ls(o), 115, 3)


class TestPrzetworz(unittest.TestCase):
    def test_baza_bez_wlascicieli(self):
        p = baza([wiersz('Ls', 'V', .5)], [], wymagaj_wlasnosci=False)
        self.assertIn(PID, p.dzialki)
        self.assertIn(PID + '.LsV', p.ls)

    def test_inne_skrypty_bez_zmian(self):
        self.assertEqual(baza([wiersz('Ls', 'V', .5)], []).dzialki, {})

    def test_ls_na_calosci_patrzy_na_ls(self):
        p = baza([wiersz('Ls', 'V', 0.0), wiersz('R', 'V', 1.0)])
        self.assertEqual(p.sl_pow_ls_dzkat[PID], [0.0, 1.0])
        p = baza([wiersz('Ls', 'V', 1.0), wiersz('N', 'V', 0.0)])
        self.assertEqual(p.sl_pow_ls_dzkat[PID], [1.0, 1.0])

    def test_podwojne_z_arkuszem(self):
        pid = '24070620003.AM-2.5821'
        p = baza([wiersz('Ls', 'V', .5, pid=pid)] * 2)
        self.assertEqual(p.ls_podwojne_by_pid, {pid: [pid + '.LsV']})


class TestDopasowanie(unittest.TestCase):
    def przebieg(self, kawalki, rekordy):
        p = baza([wiersz('Ls', sq, a) for sq, a in rekordy])
        o = PrzetworzKluTest(dzialka(), kawalki_klu(kawalki), p)
        o.przetworz()
        wynik = o.s_dopasuj_ls_po_pow()
        o.s_dopisz_uzyt()
        return wynik, o

    def test_odlamek_nie_blokuje_dopasowania(self):
        wynik, o = self.przebieg(
            [('Ls', 'IV', 5000), ('Ls', 'VI', 2000), ('Ls', 'IV', 5)],
            [('V', .5), ('III', .2)])
        self.assertTrue(wynik)
        self.assertEqual(
            sorted(f['SQ'] for f in o.klus_popr
                   if f.geometry().area() > 21), ['III', 'V'])
        self.assertEqual(o.uwagi['brakb'], [PID + '.LsIV'])  # tylko odlamek

    def test_klasa_w_kilku_kawalkach(self):
        wynik, o = self.przebieg(
            [('Ls', 'IV', 3000), ('Ls', 'IV', 2000), ('Ls', 'VI', 2000)],
            [('V', .5), ('III', .2)])
        self.assertTrue(wynik)
        self.assertEqual(sorted(f['SQ'] for f in o.klus_popr),
                         ['III', 'V', 'V'])
        self.assertEqual(o.uwagi['brakb'], [])

    def test_zgodne_klasy_zostaja(self):
        _w, o = self.przebieg(
            [('Ls', 'V', 2000), ('Ls', 'V', 3000), ('Ls', 'III', 2000)],
            [('V', .5), ('III', .2)])
        self.assertEqual(sorted(f['SQ'] for f in o.klus_popr),
                         ['III', 'V', 'V'])
        self.assertEqual(len(o.uwagi['podmsq']), 0)

    def test_niezgodna_liczba_klas_bez_dopasowania(self):
        wynik, _o = self.przebieg(
            [('Ls', 'IV', 3000), ('Ls', 'V', 2000), ('Ls', 'VI', 2000)],
            [('V', .5), ('III', .2)])
        self.assertFalse(wynik)

    def test_powierzchnia_w_raporcie_podmiany_z_ls(self):
        p = baza([wiersz('Ls', 'V', .5), wiersz('R', 'V', .5)])
        o = PrzetworzKlu(dzialka(), kawalki_klu(
            [('Ls', 'IV', 5000), ('R', 'V', 2000)]), p)
        o.przetworz()
        o.s_czy_jeden_ls()
        self.assertEqual(o.uwagi['podmsq'][PID + '.LsV'][3], '0.5')


class TestAnaliza(unittest.TestCase):
    def setUp(self):
        # QGIS trzyma uchwyty do SHP, sprzatanie jest best-effort
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.iface = Iface()

    def tearDown(self):
        self.tmp.cleanup()

    def warstwa(self, nazwa, pola, wiersze):
        uri = 'Polygon?crs=epsg:2180&' + '&'.join(
            'field=' + p + ':string(30)' for p in pola)
        mem = QgsVectorLayer(uri, 'x', 'memory')
        fs = []
        for i, wart in enumerate(wiersze):
            f = QgsFeature(mem.fields())
            f.setAttributes(list(wart))
            f.setGeometry(kw(i * 50, 0, 10))
            fs.append(f)
        mem.dataProvider().addFeatures(fs)
        sc = os.path.join(self.tmp.name, nazwa + '.shp')
        QgsVectorFileWriter.writeAsVectorFormat(
            mem, sc, 'UTF-8', mem.crs(), 'ESRI Shapefile')
        return QgsVectorLayer(sc, nazwa, 'ogr')

    def analiza(self, dz_pid=(PID,), pola_dz=None):
        pola_dz = pola_dz or AnalizujKlus.POLA_DZKAT
        klu = self.warstwa('KLU', ['AU', 'SQ', 'KOD'], [('Ls', 'iva', 'x')])
        dz = self.warstwa('DZKAT', pola_dz,
                          [[p] + [''] * (len(pola_dz) - 1) for p in dz_pid])
        a = AnalizujKlus(self.iface, klu, dz)
        a.typ, a.landid, a.au, a.sq = 'AU ', '---', 'AU', 'SQ'
        a.uzytki = [wiersz('Ls', 'V', .5)]
        a.wlasnosci = WLASC
        a.dd = types.SimpleNamespace(ui=types.SimpleNamespace(
            lineEdit_bazy=types.SimpleNamespace(text=lambda: 'bazy')))
        return a

    def test_poprawne_przechodzi(self):
        self.assertTrue(self.analiza().sprawdz_warunki())

    def test_brak_pola_dzkat(self):
        a = self.analiza(pola_dz=['PARCELID', 'PARCELNR'])
        self.assertFalse(a.sprawdz_warunki())
        self.assertIn('GRP', self.iface.bar.komunikaty[-1][1])

    def test_dwa_rekordy_tej_samej_dzialki(self):
        self.assertFalse(self.analiza(dz_pid=(PID, PID)).sprawdz_warunki())

    def test_puste_parcelid(self):
        self.assertFalse(self.analiza(dz_pid=('',)).sprawdz_warunki())

    def test_brak_uzytkow(self):
        a = self.analiza()
        a.uzytki = []
        self.assertFalse(a.sprawdz_warunki())

    def test_niewskazana_kolumna(self):
        a = self.analiza()
        a.sq = '---'
        self.assertFalse(a.sprawdz_warunki())

    def test_powtorzone_bazy_przerwij(self):
        a = self.analiza()
        a.bazy_powtorzone = [['a.mdb', 'b.mdb', 5]]
        a.pytaj_o_powtorzone_bazy = lambda: False
        self.assertFalse(a.sprawdz_warunki())

    def test_zrodlo_klu_nietkniete(self):
        a = self.analiza()
        a.p = baza(a.uzytki)
        zrodlo = a.klu
        przed = [f.attributes() for f in zrodlo.getFeatures()]
        a.przygotuj_do_analizy()
        self.assertEqual(przed, [f.attributes() for f in
                                 QgsVectorLayer(zrodlo.source(), 'k', 'ogr')
                                 .getFeatures()])
        self.assertEqual(os.path.basename(a.tempkat), 'temp')
        wyn = next(a.klu.getFeatures())
        self.assertEqual(wyn['KLU'], 'LsIVA')
        self.assertTrue(wyn.geometry().isMultipart())

    def test_puste_au_nie_wywala(self):
        a = self.analiza()
        a.klu = self.warstwa('KLU2', ['AU', 'SQ'], [(NULL, NULL), ('', 'V')])
        a.p = baza(a.uzytki)
        a.przygotuj_do_analizy()
        self.assertEqual({f['KLU'] for f in a.klu.getFeatures()}, {'xxxxxx'})

    def test_za_dlugi_tekst_nie_gubi_obiektu(self):
        a = self.analiza()
        lyr = QgsVectorLayer(
            'MultiPolygon?crs=epsg:2180&field=PARCELID:string(50)'
            '&field=GRP:string(2)', 'x', 'memory')
        f = QgsFeature(lyr.fields())
        f.setAttributes([PID, '12345'])
        f.setGeometry(kw(0, 0, 5))
        f.geometry().convertToMultiType()
        a.dodaj_do_warstwy(lyr, [f])
        self.assertEqual(lyr.featureCount(), 1)
        self.assertEqual(next(lyr.getFeatures())['GRP'], '12')


class TestRaport(unittest.TestCase):
    def test_sekcje_i_filtr_op(self):
        pid_nowa = '24070620003.9999'
        pid_poza = '24070620003.8888'
        pid_cala = '24070620003.7777'
        p = baza(
            [wiersz('Ls', 'V', .5), wiersz('R', 'V', .5, pid=pid_nowa),
             wiersz('Ls', 'V', 1.0, pid=pid_cala)],
            [[1, 'SKARB', 'OP', '24', '07', '062', '0003', None, '5821'],
             [2, 'KOWALSKI', 'OF', '24', '07', '062', '0003', None, '9999'],
             [3, 'KOWALSKI', 'OF', '24', '07', '062', '0003', None, '7777']])

        o_op = PrzetworzKlu(dzialka(), kawalki_klu([('Ls', 'V', 100)]), p)
        o_op.przetworz()
        self.assertTrue(o_op.uwagi['op'])

        o_bez = PrzetworzKlu(dzialka(pid_nowa), [], p)
        o_bez.przetworz()

        o_cala = PrzetworzKlu(dzialka(pid_cala), [], p)
        o_cala.przetworz()
        self.assertTrue(o_cala.s_czy_ls_na_calosci())
        o_cala.polacz_ostateczne()

        kaw = kawalki_klu([('Ls', 'V', 100)])
        kaw[0]['PARCELID'] = pid_poza
        o_poza = PrzetworzKlu(dzialka(pid_poza), kaw, p)
        o_poza.przetworz()
        self.assertFalse(o_poza.s_czy_dz_w_bazie())

        for lid, f in o_cala.poprawne.items():
            f['LANDID'] = lid

        s = {PID: o_op, pid_nowa: o_bez, pid_cala: o_cala, pid_poza: o_poza}
        r = GenerujRaport(s, 'Ws', p, bledne=['24070620003.6666'])
        r.zestaw_dane()
        tekst = r.generuj_raport()

        self.assertEqual(r.lista_bez_uzytkow, [pid_nowa])
        self.assertEqual(r.ls_poza_baza, [pid_poza])
        self.assertIn('DZIALKI BEZ UŻYTKÓW', tekst)
        self.assertIn('DZIALKI Z PODMIENIONYMI', tekst)
        self.assertIn(pid_cala, tekst)
        self.assertIn('SPOZA BAZY', tekst)
        self.assertIn('24070620003.6666', tekst)


if __name__ == '__main__':
    wyn = unittest.main(exit=False, verbosity=1).result
    app.exitQgis()
    sys.exit(0 if wyn.wasSuccessful() else 1)
