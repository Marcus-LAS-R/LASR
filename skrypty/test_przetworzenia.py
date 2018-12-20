import platform
from .baza_wrapper import Baza
from .baza_przetworz import Przetworz


if platform.system() == 'Linux':
    baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
else:
    baza = r'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'

b = Baza(baza)
b_lacz = b.polacz()
u = b.uzytki()
w = b.wlasnosci()
p = Przetworz()
p.dodaj_uzytki(u)
p.dodaj_wlasnosci(w)
p.przetworz_uzytkowanie()
p.przetworz_dzialki()

pass
