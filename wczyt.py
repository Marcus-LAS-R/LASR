from baza_wrapper import Baza
from baza_zabiegi import Wydzielenie
from pprint import pprint as pp

b = Baza('/home/qnox/upul/testy/moszczenica/baza.sqlite')
b.polacz()


lista = [x for x in b.pobierz_wydzielenia().values()]
for i in lista:
    bw = b.pobierz_do_zab(i)

    w = Wydzielenie(i)
    w.wpisz_wiek_rebnosci(b.pobierz_wiek_reb())
    w.wczytaj_dane(bw)

    w.generuj_zabiegi()
    w.sprawdz_zabiegi()
    if len(w.uw_raport) > 0:
        pp(bw)
        print('rebnia gen', w.gen_reb)
        print('rebnia org.', w.reb)
        print(w.zabiegi, w.cue)
        print(w.uwagi)
        pp(w.uw_raport)
        print('--------------------\n\n')
