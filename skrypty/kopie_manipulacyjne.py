import os
import glob
from .kopie_zip import spakuj
from .znacznik_czasu import znacznik
from qgis.core import Qgis, QgsMessageLog


def zrob_kopie_manipulacyjna(baza_sc, warstwy, nazwa_czynnosci):
    """ Migawka stanu PRZED destrukcyjna operacja (usuwanie wydzielen z
    warstwy lub z bazy) - w katalogu bazy (poziom projektu) tworzy ZIP
    Kopie_manipulacyjne/<nazwa_czynnosci>_<znacznik czasu>.zip
    z NIEZMIENIONYM kompletem: cala baza (.mdb/.sqlite) oraz wszystkie pliki
    towarzyszace (.shp/.shx/.dbf/.prj/...) podanych warstw - jeden pakiet.

    `warstwy` moze zawierac None (np. brakujaca/nieuzywana warstwa PNSW) -
    takie wpisy sa pomijane.

    `baza_sc` moze byc None (operacja tylko na warstwach) - wtedy kopiowane
    sa same warstwy, a Kopie_manipulacyjne powstaje w katalogu pierwszej
    podanej warstwy.

    Zwraca sciezke do utworzonego ZIP-a, albo None przy bledzie
    (callerzy powinni w takim przypadku przerwac operacje - bez kopii nie
    usuwamy nic). """
    try:
        if baza_sc:
            kat_projektu = os.path.dirname(baza_sc)
        else:
            pierwsza = [x for x in warstwy if x is not None][0]
            kat_projektu = os.path.dirname(
                pierwsza.dataProvider().dataSourceUri().split("|")[0])
        kat_kopii = os.path.join(kat_projektu, 'Kopie_manipulacyjne')
        if not os.path.isdir(kat_kopii):
            os.mkdir(kat_kopii)

        pliki = []
        if baza_sc:
            pliki.append((baza_sc, os.path.basename(baza_sc)))

        for lyr in warstwy:
            if lyr is None:
                continue
            sciezka = lyr.dataProvider().dataSourceUri().split("|")[0]
            baza_nazwy = os.path.splitext(sciezka)[0]
            for plik in glob.glob(baza_nazwy + '.*'):
                pliki.append((plik, os.path.basename(plik)))

        return spakuj(os.path.join(
            kat_kopii, nazwa_czynnosci + '_' + znacznik() + '.zip'), pliki)
    except Exception as e:
        QgsMessageLog.logMessage(
            f'zrob_kopie_manipulacyjna: błąd przy tworzeniu kopii: {e}',
            'Las-R', Qgis.Critical
        )
        return None
