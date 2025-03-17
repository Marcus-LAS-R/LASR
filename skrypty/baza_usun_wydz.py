from qgis.core import Qgis, QgsField, QgsFeatureRequest, QgsMessageLog, QgsProject
from PyQt5.QtCore import QVariant

from .sprawdzenia_warstw import SprawdzWydzielenia
from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .shp_literkuj import Literkuj
from .shp_adr_les import Zaadresuj

from .baza_dopisz_wydz import DopiszWydzielenia
from .shp_dopOddzWydz import dopOddzWydz


def usun_wydz(iface):
    lyr = iface.activeLayer()

    baza_sc = znajdz_baze_do_wydz(iface, lyr)
    if baza_sc is False:
        iface.messageBar().pushMessage(
            "BRAK BAZY", "Bez bazy ani rusz!", Qgis.Critical, 10
        )
        return False

    baza = Baza(baza_sc)
    if not baza.polacz():
        iface.messageBar().pushMessage(
            "BAZA", "Nie mogłem podłączyć się do bazy", Qgis.Critical, 10
        )
        return False

    baza.utworz_kopie("kopia_usun_wydz")
    f_arod = baza.pobierz_wydzielenia()
    spis_wydz_lyr = [f["ADR_LES"] for f in lyr.getFeatures()]

    brak_baza = [vv for fi, vv in f_arod.items() if fi not in spis_wydz_lyr]
    
    print('W bazie: ', len(f_arod))
    print('Brakuje w bazie: ', len(brak_baza))
    print(brak_baza[:10])

    if len(brak_baza) == 0:
        iface.messageBar().pushMessage(
            "BRAK", "Nie ma wydzieleń do usunięcia", Qgis.Warning, 10
        )
        return

    res = baza.usun_rekordy(brak_baza)
    if res:
        iface.messageBar().pushMessage(
            "OK", "Usunięto rekordy z bazy", Qgis.Success, 10
        )
        return

    iface.messageBar().pushMessage(
        "BŁAD", "Coś poszło nie tak, sprawdz log messages", Qgis.Warning, 10
    )
