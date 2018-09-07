from ..skrypty.sprawdz_ls import PrzetworzKlu, Przetworz
from ..skrypty import baza_wrapper
import pytest
import platform
from qgis.core import QgsVectorLayer

dzl = QgsVectorLayer('/home/qnox/upul/testy/grabica/test/DZKATwyb.shp', 'dz',
                     'ogr')
dzf = [x for x in dzl.getFeatures()]

klul = QgsVectorLayer('/home/qnox/upul/testy/grabica/test/LSwyb.shp', 'ls',
                      'ogr')
lsf = [x for x in klul.getFeatures()]

if platform.system() == 'Linux':
    baza = '/home/qnox/upul/testy/grabica/baza.sqlite'
else:
    baza = r'e:\TEMP\sprawdz_ls\Bobrowniki_Gmina.mdb'

b = baza_wrapper.Baza(baza)
b_lacz = b.polacz()
u = b.uzytki()
w = b.wlasnosci()
p = Przetworz()
p.dodaj_uzytki(u)
p.dodaj_wlasnosci(w)
p.przetworz_uzytkowanie()
p.przetworz_dzialki()


@pytest.mark.parametrize('baza, dzf, lsf', [dzf, lsf, p])
def test_poprawnosc_sprawdzenia(dzf, lsf, p):
    pk = PrzetworzKlu(dzf, lsf, p)

    assert pk.is_valid()
