import pytest

from skrypty.baza_wrapper import Baza
from skrypty.baza_zabiegi import Wydzielenie


@pytest.fixture()
def baza():
    baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
    bb = Baza(baza)
    bb.polacz()
    return bb


@pytest.fixture()
def baza_pusta():
    baza = '/home/qnox/upul/testy/grabica/baza_pusta.sqlite'
    bb = Baza(baza)
    bb.polacz()
    return bb


def test_wczytania_wydz(baza):
    w = Wydzielenie(1200)
    baza = baza.pobierz_do_zab(25)
    assert w.wczytaj_dane(baza) is True


def test_poprawnego_wczytania_wydz_gat_gl(baza):
    wr = baza.pobierz_wiek_reb()
    baza = baza.pobierz_do_zab(25)
    b = baza
    w = Wydzielenie(b[4][0][0])
    w.wpisz_wiek_rebnosci(wr)
    w.wczytaj_dane(b)
    if len(b[2]) > 0:
        assert w.gat_gl == b[2][0][1] and \
            w.gat_gl_bhd == w.isNone(b[2][0][4]) and \
            w.gat_gl_wiek == w.isNone(b[2][0][3]) and \
            w.gat_gl_vol == w.isNone(b[2][0][5]) and \
            w.gat_gl_udz == w.isNone(b[2][0][2])
    else:
        assert w.gat_gl == '' and \
            w.gat_gl_bhd == 0 and \
            w.gat_gl_wiek == 0 and \
            w.gat_gl_vol == 0 and \
            w.gat_gl_udz == 0


def test_poprawnego_wczytania_wydz_zabiegi(baza):
    wr = baza.pobierz_wiek_reb()
    baza = baza.pobierz_do_zab(25)
    b = baza
    w = Wydzielenie(1200)
    w.wpisz_wiek_rebnosci(wr)
    w.wczytaj_dane(b)
    assert w.max_cue == len(b[1]) and \
        len(w.cue.keys()) == len(b[1])


def test_poprawnego_wczytania_wydz_pod_nal(baza):
    wr = baza.pobierz_wiek_reb()
    baza = baza.pobierz_do_zab(25)
    b = baza
    w = Wydzielenie(b[4][0][0])
    w.wpisz_wiek_rebnosci(wr)
    w.wczytaj_dane(b)
    podr = 0
    nal = 0
    for l in b[5]:
        if l[1] == 'PODR':
            podr = round(l[2], 1)
        if l[1] == 'NAL':
            nal = round(l[2], 1)

    assert w.podr == podr and w.nal == nal


def test_poprawnego_wczytania_wydz_luki(baza):
    wr = baza.pobierz_wiek_reb()
    baza = baza.pobierz_do_zab(25)
    b = baza
    w = Wydzielenie(b[4][0][0])
    w.wpisz_wiek_rebnosci(wr)
    w.wczytaj_dane(b)
    if len(b[6]) > 0:
        assert w.luki == b[6][0][2]


def test_poprawnego_wczytania_wydz_przest_vol(baza):
    wr = baza.pobierz_wiek_reb()
    baza = baza.pobierz_do_zab(25)
    b = baza
    w = Wydzielenie(b[4][0][0])
    w.wpisz_wiek_rebnosci(wr)
    w.wczytaj_dane(b)
    przes = 0
    nal = 0
    for l in b[5]:
        if l[2] == 'PRZES':
            if l[5] is not None:
                przes += l[5]
        else:
            if l[5] is not None:
                nal += l[5]

    assert w.przest_vol == przes and w.plaz_vol == nal


def test_generowania_zabiegu_ogolny(baza):
    wr = baza.pobierz_wiek_reb()
    b = baza.pobierz_do_zab(560)
    w = Wydzielenie(b[4][0][0])
    w.wpisz_wiek_rebnosci(wr)
    w.wczytaj_dane(b)
    w.wpisz_wiek_rebnosci(baza.pobierz_wiek_reb())
    assert w.generuj_zabiegi()


def test_generowania_zabiegu_zgodny_z_baza(baza):
    b = baza.pobierz_do_zab(1200)
    w = Wydzielenie(b[4][0][0])
    w.wczytaj_dane(b)
    w.wpisz_wiek_rebnosci(baza.pobierz_wiek_reb())
    w.generuj_zabiegi()
    # zab_gen = sorted([x[0] for x in w.zabiegi])
    # zab_baza = sorted([x for x in w.cue.keys()])
    # assert zab_gen == zab_baza
    assert w.typ == 'PŁAZ'


# @pytest.mark.parametrize('licz', [25])
@pytest.mark.parametrize('licz', [x for x in range(155, 156)])
def test_sprawdzenia_ze_stara_baza(licz):
    baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
    bb = Baza(baza)
    bb.polacz()
    if licz not in bb.pobierz_wydzielenia().values():
        assert True
    else:
        b = bb.pobierz_do_zab(licz)
        w = Wydzielenie(licz)
        w.wczytaj_dane(b)
        w.wpisz_wiek_rebnosci(bb.pobierz_wiek_reb())
        w.generuj_zabiegi()
        aa = []
        if w.gen_reb != '':
            aa = [[w.gen_reb, w.gen_pow_reb]]
        assert sorted(w.zabiegi + aa) == \
            sorted([[k, v] for k, v in w.cue.items()])


def test_wpisana_do_pustej(baza_pusta):
    bb = baza_pusta
    bb.wpisz('delete from f_arod_cue;')
    b = bb.pobierz_do_zab(23)
    w = Wydzielenie(23)
    w.wczytaj_dane(b)
    w.wpisz_wiek_rebnosci(bb.pobierz_wiek_reb())
    w.generuj_zabiegi()
    w.dodaj_baze(bb)
    w.dopisz_zabiegi()
    assert w.dodano == 4 and w.zmodyfikowano == 0


def test_zmodyfikowania_rekordu(baza_pusta):
    bb = baza_pusta
    bb.wpisz('update f_arod_cue set cutting_area=6.6666;')
    b = bb.pobierz_do_zab(23)
    w = Wydzielenie(23)
    w.wczytaj_dane(b)
    w.wpisz_wiek_rebnosci(bb.pobierz_wiek_reb())
    w.generuj_zabiegi()
    w.dodaj_baze(bb)
    w.dopisz_zabiegi(False)
    assert w.uw_baza == [] and w.dodano == 0 and w.zmodyfikowano == 4
