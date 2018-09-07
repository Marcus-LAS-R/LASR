from baza_wrapper import Baza
from baza_przetworz import Przetworz


baza = '/home/qnox/upul/testy/grabica/baza.sqlite'

b = Baza(baza)
b_lacz = b.polacz()
u = b.uzytki()
w = b.wlasnosci()
p = Przetworz()
p.dodaj_uzytki(u)
p.dodaj_wlasnosci(w)
p.przetworz_uzytkowanie()
p.przetworz_dzialki()
