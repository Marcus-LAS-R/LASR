import os
import glob
import shutil
from datetime import datetime

from qgis.core import Qgis, QgsMessageLog


def zrob_kopie_manipulacyjna(baza_sc, warstwy, nazwa_czynnosci):
    """ Migawka stanu PRZED destrukcyjna operacja (usuwanie wydzielen z
    warstwy lub z bazy) - w katalogu bazy (poziom projektu) tworzy folder
    Kopie_manipulacyjne/<nazwa_czynnosci>_<data>_<godzina-minuta-sekunda>/
    i kopiuje tam NIEZMIENIONY komplet: cala baza (.mdb/.sqlite) oraz
    wszystkie pliki towarzyszace (.shp/.shx/.dbf/.prj/...) podanych warstw.

    `warstwy` moze zawierac None (np. brakujaca/nieuzywana warstwa PNSW) -
    takie wpisy sa pomijane.

    Zwraca sciezke do utworzonego folderu kopii, albo None przy bledzie
    (callerzy powinni w takim przypadku przerwac operacje - bez kopii nie
    usuwamy nic). """
    try:
        kat_projektu = os.path.dirname(baza_sc)
        kat_kopii = os.path.join(kat_projektu, 'Kopie_manipulacyjne')
        if not os.path.isdir(kat_kopii):
            os.mkdir(kat_kopii)

        czas = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        podkat = os.path.join(kat_kopii, nazwa_czynnosci + '_' + czas)
        os.mkdir(podkat)

        shutil.copyfile(
            baza_sc, os.path.join(podkat, os.path.basename(baza_sc)))

        for lyr in warstwy:
            if lyr is None:
                continue
            sciezka = lyr.dataProvider().dataSourceUri().split("|")[0]
            baza_nazwy = os.path.splitext(sciezka)[0]
            for plik in glob.glob(baza_nazwy + '.*'):
                shutil.copyfile(
                    plik, os.path.join(podkat, os.path.basename(plik)))

        return podkat
    except Exception as e:
        QgsMessageLog.logMessage(
            f'zrob_kopie_manipulacyjna: błąd przy tworzeniu kopii: {e}',
            'Las-R', Qgis.Critical
        )
        return None
