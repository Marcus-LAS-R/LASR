import os
import pytest
from ..skrypty.baza_wrapper import Baza
from ..skrypty.zabiegi.wydzielenie import Wydzielenie
from ..skrypty.zabiegi.main import Zabiegi


@pytest.fixture()
def baza():
    baza = 'testy/baza_zabiegi.sqlite'
    bb = Baza(baza)
    bb.polacz()
    return bb


@pytest.fixture()
def baza_pusta():
    baza = 'testy/baza_zabiegi_pusta.sqlite'
    bb = Baza(baza)
    bb.polacz()
    return bb


def test_wczytania_wydz(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(25)
    wyn = baza.pobierz_do_zab(25)
    assert w.odczytaj_dane_z_bazy(wyn) is True
    assert w.reb == 'IB'
    assert w.wiekReb == 120
    assert w.zwarcie == 'PRZ'
    assert w.ile_dzkat == 8
    assert len(w.drzew_gat) == 2


@pytest.mark.parametrize("inp,out", [
    ('BRZ', 'BRZ'), ('SO.L', 'SO'), ('KL.Jw', 'DB'), ('KSZ', 'BRZ')])
def test_generalizacji_gat(inp, out):
    w = Wydzielenie()
    w.przygotuj_strukture(1)
    w.gat_gl = inp
    assert w._zgeneralizuj_gatunek() == out


@pytest.mark.parametrize("inp,out", [
    (['DB', 220], 101), (['DB', 20], 41), (['DB', 310], 101), ])
def test_klasy_wieku(inp, out):
    w = Wydzielenie()
    w.przygotuj_strukture(1)
    w.gat_gl_wiek = inp[1]
    w._ustaw_klase_wieku(inp[0])
    assert w._ustaw_klase_wieku(inp[0]) == out


def test_oblicz_ciecie(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(87)
    wyn = baza.pobierz_do_zab(87)
    w.odczytaj_dane_z_bazy(wyn)
    ww = w._oblicz_ciecie('TW')
    assert w.zwarcie == 'PEŁ'
    assert ww == [15, 10]


def test_oblicz_ciecie_modyfikator_trzeb_norma(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(87)
    w.dodaj_mod_trzeb(3)
    wyn = baza.pobierz_do_zab(87)
    w.odczytaj_dane_z_bazy(wyn)
    ww = w._oblicz_ciecie('TW')
    assert w.mod_trzeb == 3
    assert w.zwarcie == 'PEŁ'
    assert ww == [18, 11]


def test_oblicz_ciecie_modyfikator_trzeb_przekroczony(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(87)
    w.dodaj_mod_trzeb(44)
    wyn = baza.pobierz_do_zab(87)
    w.odczytaj_dane_z_bazy(wyn)
    ww = w._oblicz_ciecie('TW')
    assert w.mod_trzeb == 44
    assert ww == [20, 13]


def test_sprawdz_slowniki_rebni():
    w = Wydzielenie()
    w.przygotuj_strukture(87)
    assert len(w.rebnieSl) == len(w.rebnieSlnowy)


def test_generuj_zabieg(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.wiekReb = 95  # zmiana żeby wygenerował rębnie
    w.generuj_zabiegi()
    assert w.zabiegi == \
        [['ODN-ZRB', 1.0972], ['PIEL', 1.0972], ['AGROT', 1.0972]]
    assert w.gen_reb == 'IB'


def test_generuj_zabiegi_z_wpisana_rebnia_zupelna(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.reb = 'IB'
    w.proc_reb = 50
    w.wiekReb = 95  # zmiana żeby wygenerował rębnie
    w.generuj_zabiegi()
    assert w.zabiegi == \
        [['ODN-ZRB', 0.5486], ['PIEL', 0.5486], ['AGROT', 0.5486]]
    assert w.gen_reb == 'IB'


def test_generuj_zabiegi_z_wpisana_rebnia_czesciowa(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.reb = 'IIB'
    w.proc_reb = 50
    w.wiekReb = 95  # zmiana żeby wygenerował rębnie
    w.generuj_zabiegi()
    assert w.zabiegi == \
        [['ODN-ZŁOŻ', 0.5486], ['PIEL', 0.5486], ['AGROT', 0.5486]]
    assert w.gen_reb == 'IIB'


def test_generuj_zabiegi_ze_zmiana_na_KO(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.wiekReb = 95  # zmiana żeby wygenerował rębnie
    w.nal = 0.3
    w.podr = 0.2
    w.generuj_zabiegi()
    assert w.zabiegi == \
        [['ODN-ZŁOŻ', 0.3292], ['PIEL', 0.3292], ['AGROT', 0.3292]]
    assert w.gen_reb == 'IIB'
    assert w.zmien_na_ko


def test_wczytania_halizny(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(424)
    wyn = baza.pobierz_do_zab(424)
    wczytanie = w.odczytaj_dane_z_bazy(wyn)
    assert wczytanie
    assert w.zadrzew == 0.4
    assert w.zwarcie == 'PRZ'
    assert len(w.drzew_gat) == 2


def test_sprawdzenia_halizny(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(1)
    w.typ = 'HAL'
    w.stl = 'LG'
    w.zbiorcze_sprawdzenie()
    assert len(w.uw_raport) == 3
    assert w.uw_raport == [
        'Brak ODN-HAL na haliznie',
        'Brak wpisanej pokrywy',
        'Brak wpisanego TD',
    ]


def test_sprawdzenia_dstan(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.zbiorcze_sprawdzenie()
    assert len(w.uw_raport) == 1
    # wiek reb ponizej tego w bazie


def test_sprawdzenia_sumowania_udzialow(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.drzew_gat[0][2] = '6'  # w bazie jest 7
    w.zbiorcze_sprawdzenie()
    assert len(w.uw_raport) == 2
    # wiek reb ponizej tego w bazie, udzialy!=10


def test_sprawdzenia_czy_gatunki_w_drzew(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.drzew_gat = []
    w.zbiorcze_sprawdzenie()
    assert w.struk == 'DRZEW'
    assert len(w.uw_raport) == 2
    # wiek reb ponizej tego w bazie, brak_gat


def test_sprawdzenia_pozyskania_przest(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(452)
    wyn = baza.pobierz_do_zab(452)
    w.odczytaj_dane_z_bazy(wyn)
    w.przest_vol = 9
    w.zbiorcze_sprawdzenie()
    assert 'Pozyskanie PRZEST a miąższość PRZES niezgodne' in w.uw_raport


def test_sprawdzenia_pozyskanie_na_ha(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.sum_cue_volume = 10
    w.zbiorcze_sprawdzenie()
    assert len(w.uw_raport) == 2
    assert 'Pozyskanie <61m³/ha [11 m³/ha], (pow. wydz: 1.0972)' in \
        w.uw_raport
    # wiek reb ponizej tego w bazie, pozyskanie < 61


def test_sprawdzenia_wydz_przest(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(977)
    wyn = baza.pobierz_do_zab(977)
    w.odczytaj_dane_z_bazy(wyn)
    w.zbiorcze_sprawdzenie()
    assert len(w.uw_raport) == 0


def test_sprawdzenia_wydz_sukcesja(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(1172)
    wyn = baza.pobierz_do_zab(1172)
    w.odczytaj_dane_z_bazy(wyn)
    w.zbiorcze_sprawdzenie()
    assert len(w.uw_raport) == 0


def test_sprawdzenia_wydz_inne_wyl(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(211)
    wyn = baza.pobierz_do_zab(211)
    w.odczytaj_dane_z_bazy(wyn)
    w.zbiorcze_sprawdzenie()
    assert len(w.uw_raport) == 0


def test_sprawdzenia_wydz_zrab(baza):
    w = Wydzielenie()
    w.przygotuj_strukture(309)
    wyn = baza.pobierz_do_zab(309)
    w.odczytaj_dane_z_bazy(wyn)
    w.zbiorcze_sprawdzenie()
    assert len(w.uw_raport) == 0


def test_wpisania_rebni_do_bazy(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta
    w.wiekReb = 95  # zmiana żeby wygenerował rębnie
    w.generuj_zabiegi()

    res, txt = w._dopisz_nowa_rebnie()
    cnt_wpisz = baza_pusta.pobierz('select count(*) from f_arod_cue;')

    assert cnt_wpisz == [(1,)]
    assert txt == 'OK'
    assert res


def test_wpisania_zabiegow_do_bazy(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta
    w.wiekReb = 95  # zmiana żeby wygenerował rębnie
    w.generuj_zabiegi()

    w._dopisz_zabiegi()
    wpis = baza_pusta.pobierz('select * from f_arod_cue;')

    assert isinstance(w.zabiegi, list)
    assert len(wpis) == 4
    assert [x[1] for x in wpis] == ['IB', 'ODN-ZRB', 'PIEL', 'AGROT']


def test_zmiany_pow_rebni_w_bazie(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta
    w.wiekReb = 95  # zmiana żeby wygenerował rębnie
    w.generuj_zabiegi()
    w.gen_pow_reb = 0.9

    cnt_przed = baza_pusta.pobierz('select * from f_arod_cue;')
    res = w._zmodyfikuj_pow_rebni()
    cnt_po = baza_pusta.pobierz('select * from f_arod_cue;')
    baza_pusta.wpisz('delete from f_arod_cue;')
    baza_pusta.wpisz('vaccum;')
    cnt = baza_pusta.pobierz('select count(*) from f_arod_cue;')

    assert cnt_przed[0][3] == 1.0972
    assert cnt_po[0][3] == 0.9
    assert cnt == [(0,)]
    assert res


def test_obliczenia_ciecia_dla_tp(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta

    res = w._oblicz_ciecie('TP')
    assert res == [8, 13]


def test_dopisania_zabiegu_tp(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta
    w.max_cue += 1

    res = w._dopisz_ciecie_mlodych(['TP', 1.0])
    val = baza_pusta.pobierz('select * from f_arod_cue;')
    baza_pusta.wpisz('delete from f_arod_cue;')
    baza_pusta.wpisz('vaccum;')
    assert res
    assert val[0][1] == 'TP'


def test_modyfikacja_zabiegu_glowna_metoda_rebnia(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta
    w.wiekReb = 95  # zmiana żeby wygenerował rębnie
    w.generuj_zabiegi()
    w.modyfikuj_zabiegi()

    val = baza_pusta.pobierz('select * from f_arod_cue;')
    baza_pusta.wpisz('delete from f_arod_cue;')
    baza_pusta.wpisz('vaccum;')

    assert len(w.zabiegi) == 3
    assert val[0][1] == 'IB'
    assert val[1][1] == 'ODN-ZRB'
    assert w.uw_baza == []


def test_modyfikacja_zabiegu_glowna_metoda_tp(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(215)
    wyn = baza_pusta.pobierz_do_zab(215)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta
    w.generuj_zabiegi()
    w.modyfikuj_zabiegi()

    val = baza_pusta.pobierz('select * from f_arod_cue;')
    baza_pusta.wpisz('delete from f_arod_cue;')
    baza_pusta.wpisz('vaccum;')

    assert len(w.zabiegi) == 1
    assert val[0][1] == 'TP'
    assert w.uw_baza == []


def test_modyfikacja_zabiegu_glowna_metoda_cp(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(498)
    wyn = baza_pusta.pobierz_do_zab(498)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta
    w.generuj_zabiegi()
    w.modyfikuj_zabiegi()

    val = baza_pusta.pobierz('select * from f_arod_cue;')

    assert len(w.zabiegi) == 4
    assert val[3][1] == 'CP'
    assert w.uw_baza == []


def test_modyfikacja_zabiegu_glowna_metoda_zmiana_pow_cp(baza_pusta):
    baza_pusta.wpisz(
        'update f_arod_cue set cutting_area=0.6 where measure_cd=\'CP\';'
    )
    w = Wydzielenie()
    w.przygotuj_strukture(498)
    wyn = baza_pusta.pobierz_do_zab(498)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta
    w.generuj_zabiegi()

    val = baza_pusta.pobierz('select * from f_arod_cue;')
    w.modyfikuj_zabiegi()
    valz = baza_pusta.pobierz('select * from f_arod_cue;')

    baza_pusta.wpisz('delete from f_arod_cue;')
    baza_pusta.wpisz('vaccum;')

    assert w.uw_baza == []
    assert val[3][3] == 0.6
    assert valz[3][3] == 2.2605


def test_dublowanie_uwagi_o_dz_zrebowych(baza_pusta):
    w = Wydzielenie()
    w.przygotuj_strukture(280)
    wyn = baza_pusta.pobierz_do_zab(280)
    w.odczytaj_dane_z_bazy(wyn)
    w.baza = baza_pusta
    w.generuj_zabiegi()
    w.modyfikuj_zabiegi()

    baza_pusta.wpisz('delete from f_arod_cue;')
    baza_pusta.wpisz('vaccum;')

    val = baza_pusta.pobierz(
        'select subarea_info from f_subarea where arodes_int_num=280;'
    )
    # wpis jest juz w f_subarea'i, w bazie nie jest dodatkowo modyfikowany
    assert val[0][0] == \
        ' Działki ewidencyjne należy traktować jak dz. zrębowe,'
    assert w.uwagi == \
        ' Działki ewidencyjne należy traktować jak dz. zrębowe,'


def test_przetworzenia_ilosciowego_wydzielenia(baza):
    z = Zabiegi()
    z.wybor = 'Spr'
    z.baza = baza
    z.wydz = z.baza.pobierz_wydzielenia()
    z.wr = z.baza.pobierz_wiek_reb()
    assert list(z.wydz.keys())[0] == 'T130420002-102   -s   -00'
    assert 'T130420002-102   -s   -00' in z.wydz
    res, txt = z.przetworz_wydzielenie('T130420002-102   -s   -00')
    assert not isinstance(txt, str)
    assert z.bledy == []


def test_process_wydzielenia(baza):
    z = Zabiegi()
    z.wybor = 'Spr'
    z.baza = baza
    z.wydz = z.baza.pobierz_wydzielenia()
    z.wr = z.baza.pobierz_wiek_reb()
    z._process_wydzielenie('T130420001-103   -p   -00')

    assert z.bledy == []
    assert len(z.sl) == 1
    assert z.sl['T130420001-103   -p   -00'].uw_raport == [
        'Duża odchyłka pierś/wys w 2DB120 ( 38cm/25m )'
    ]


def test_przetworzenia_ilosciowego_wydzielenia_innego(baza):
    z = Zabiegi()
    z.wybor = 'Spr'
    z.baza = baza
    z.wydz = z.baza.pobierz_wydzielenia()
    z.wr = z.baza.pobierz_wiek_reb()
    assert 'T130420002-102   -r   -00' in z.wydz
    res, txt = z.przetworz_wydzielenie('T130420002-102   -r   -00')
    assert not isinstance(txt, str)
    assert z.bledy == []


def test_przetworzenia_ilosciowego_wydzielenia_innego2(baza):
    z = Zabiegi()
    z.wybor = 'Spr'
    z.baza = baza
    z.wydz = z.baza.pobierz_wydzielenia()
    z.wr = z.baza.pobierz_wiek_reb()
    assert 'T130420010-107   -f   -00' in z.wydz
    res, txt = z.przetworz_wydzielenie('T130420010-107   -f   -00')
    assert not isinstance(txt, str)
    assert z.bledy == []


def test_sprawdzenia_wszystkich_wydzielen(baza):
    z = Zabiegi()
    z.wybor = 'Spr'
    z.baza = baza
    z.wydz = z.baza.pobierz_wydzielenia()
    z.wr = z.baza.pobierz_wiek_reb()
    z.przetworz()

    z.generuj_raport()
    assert os.path.isfile(
        os.path.join(z.kat, 'raport_zabiegi_'+z.baza.czas+'.txt')
    )
    os.remove(
        os.path.join(z.kat, 'raport_zabiegi_'+z.baza.czas+'.txt')
    )
    assert not os.path.isfile(
        os.path.join(z.kat, 'raport_zabiegi_'+z.baza.czas+'.txt')
    )


# def test_dopisania_zabiegow_do_bazy(baza_pusta):
    # z = Zabiegi()
    # z.wybor = 'Dop'
    # z.baza = baza_pusta
    # z.kopiuj_baze()
    # z.wydz = z.baza.pobierz_wydzielenia()
    # z.wr = z.baza.pobierz_wiek_reb()
    # z.przetworz()

    # z.generuj_raport()
    # assert os.path.isfile(
        # os.path.join(z.kat, 'raport_zabiegi_'+z.baza.czas+'.txt')
    # )


def test_dopisania_zabiegow_do_bazy(baza):
    z = Zabiegi()
    z.wybor = 'Uzu'
    z.baza = baza
    z.kopiuj_baze()
    z.baza.wpisz('update f_arod_cue set cutting_area=100 where measure_cd in ("TP", "AGROT", "IB", "CP");')
    z.wydz = z.baza.pobierz_wydzielenia()
    z.wr = z.baza.pobierz_wiek_reb()
    z.przetworz()

    z.generuj_raport()
    assert os.path.isfile(
        os.path.join(z.kat, 'raport_zabiegi_'+z.baza.czas+'.txt')
    )
    os.remove(
        os.path.join(z.kat, 'raport_zabiegi_'+z.baza.czas+'.txt')
    )

    res = z.baza.pobierz('select * from f_arod_cue where cutting_area=100;')
    assert len(res) == 1
    # wpisane jest cp w wydzieleniu 1187 a skrypt generuej IIBU i dlatego, nie
    # modyfikuje powierzchni, w raporcie dodana jest dla tego wydz stosowna
    # uwaga.
