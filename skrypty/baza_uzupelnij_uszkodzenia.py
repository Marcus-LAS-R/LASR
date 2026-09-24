from qgis.core import QgsProject, Qgis
from PyQt5.QtWidgets import QMessageBox

from .baza_wrapper import Baza, znajdz_baze_do_wydz

# siedliska "wilgotne", dla ktorych przyczyna uszkodzenia D-STANu to WODNE
# zamiast domyslnego KLIMAT
SITE_TYPY_WODA = ('OL', 'OLJ', 'OLJG', 'LŁ', 'LŁG', 'OLJWYŻ', 'LŁWYŻ')

# ponizej tego wieku gatunku panujacego (pietro DRZEW, rank 1) przyczyna
# uszkodzenia to ZWIERZ - ma pierwszenstwo przed WODNE i KLIMAT
WIEK_ZWIERZ = 20

# D-STANy z mlodym gatunkiem panujacym
SQL_MLODE = (
    "ARODES_INT_NUM in (select ARODES_INT_NUM from F_STOREY_SPECIES "
    "where STOREY_CD='DRZEW' and SPECIES_RANK_ORDER=1 and "
    "SPECIES_AGE < " + str(WIEK_ZWIERZ) + ")"
)


class UzupelnijUszkodzenia:
    def __init__(self, iface):
        self.iface = iface
        self.baza = Baza('')
        self.ile_zwierz = 0
        self.ile_woda = 0
        self.ile_klimat = 0
        self.ile_stopien = 0

    def pobierz_sciezke(self):
        """Jezeli w TOC jest dokladnie jedna warstwa WYDZ, baza jest szukana
        automatycznie katalog wyzej (okno wyboru tylko gdy nie ma tam
        dokladnie jednej bazy). W przeciwnym razie uzytkownik wskazuje baze -
        o warstwe nie pytamy, bo sluzy ona tylko do odnalezienia bazy."""
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        wydz_kandydaci = [x for x in lyrs if x.name().upper() == 'WYDZ']

        if len(wydz_kandydaci) == 1:
            baza_sc = znajdz_baze_do_wydz(
                self.iface, wydz_kandydaci[0], poz=1)
        else:
            # przy kilku warstwach WYDZ okno startuje w katalogu pierwszej
            wydz = wydz_kandydaci[0] if wydz_kandydaci else None
            baza_sc = znajdz_baze_do_wydz(self.iface, wydz, poz=1, wskaz=True)
        if baza_sc is False:
            return False

        self.baza.baza = baza_sc
        return True

    def _policz(self, warunek):
        pob = self.baza.pobierz(
            "select count(*) from F_SUBAREA where AREA_TYPE_CD='D-STAN' "
            "and " + warunek + ";"
        )
        return pob[0][0] if pob else 0

    def policz(self):
        """Laczy sie z baza i liczy, ile rekordow F_SUBAREA zostanie
        zmienionych - osobno dla CAUSE_CD (z podzialem ZWIERZ/WODNE/KLIMAT) i
        dla DAMAGE_DEGREE_CD. Zmieniane sa tylko puste (NULL) pola."""
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                'BAZA', 'Nie udało się połączyć z bazą', Qgis.Critical, 10)
            return False

        site_lista = "', '".join(SITE_TYPY_WODA)

        self.ile_zwierz = self._policz("CAUSE_CD is null and " + SQL_MLODE)
        self.ile_woda = self._policz(
            "CAUSE_CD is null and SITE_TYPE_CD in ('" + site_lista + "') "
            "and not " + SQL_MLODE)
        self.ile_klimat = self._policz("CAUSE_CD is null") - \
            self.ile_zwierz - self.ile_woda
        self.ile_stopien = self._policz("DAMAGE_DEGREE_CD is null")

        return True

    def potwierdz(self):
        """Pokazuje podsumowanie znalezionych pustych rekordow i pyta o
        potwierdzenie zapisu. Zwraca False (bez pytania) jesli nie ma nic
        do uzupelnienia."""
        razem_cause = self.ile_zwierz + self.ile_woda + self.ile_klimat
        if razem_cause == 0 and self.ile_stopien == 0:
            self.iface.messageBar().pushMessage(
                'Uzupełnij uszkodzenia',
                'Brak pustych rekordów do uzupełnienia w F_SUBAREA (D-STAN)',
                Qgis.Info, 10)
            return False

        odp = QMessageBox.question(
            self.iface.mainWindow(),
            'Uzupełnij uszkodzenia w bazie',
            'W tabeli F_SUBAREA (wydzielenia D-STAN) znaleziono puste pola:\n\n'
            'CAUSE_CD - do uzupełnienia: ' + str(razem_cause) + '\n'
            '   (ZWIERZ - gat. panujący poniżej ' + str(WIEK_ZWIERZ) +
            ' lat: ' + str(self.ile_zwierz) + ',\n'
            '    WODNE - siedliska wilgotne: ' + str(self.ile_woda) + ',\n'
            '    KLIMAT - pozostałe: ' + str(self.ile_klimat) + ')\n'
            'DAMAGE_DEGREE_CD - do uzupełnienia (\'0\'): ' +
            str(self.ile_stopien) + '\n\n'
            'Istniejące, niepuste wartości nie zostaną zmienione.\n\n'
            'Kontynuować zapis do bazy?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return odp == QMessageBox.Yes

    def zapisz(self):
        """Zapisuje zmiany w F_SUBAREA. Kolejnosc ma znaczenie: najpierw
        ZWIERZ dla mlodych d-stanow, potem WODNE dla siedlisk wilgotnych,
        na koncu KLIMAT dla pozostalych - kazdy krok zmienia tylko puste
        CAUSE_CD, wiec pozniejszy nie nadpisze wczesniejszego.
        DAMAGE_DEGREE_CD jest niezalezne od wyboru przyczyny."""
        self.baza.utworz_kopie('uzupelnij_uszkodzenia')

        site_lista = "', '".join(SITE_TYPY_WODA)

        zapytania = [
            "update F_SUBAREA set CAUSE_CD='ZWIERZ' where "
            "AREA_TYPE_CD='D-STAN' and CAUSE_CD is null and " +
            SQL_MLODE + ";",
            "update F_SUBAREA set CAUSE_CD='WODNE' where "
            "AREA_TYPE_CD='D-STAN' and CAUSE_CD is null and "
            "SITE_TYPE_CD in ('" + site_lista + "');",
            "update F_SUBAREA set CAUSE_CD='KLIMAT' where "
            "AREA_TYPE_CD='D-STAN' and CAUSE_CD is null;",
            "update F_SUBAREA set DAMAGE_DEGREE_CD='0' where "
            "AREA_TYPE_CD='D-STAN' and DAMAGE_DEGREE_CD is null;",
        ]
        # przerwij na pierwszym bledzie - inaczej KLIMAT wpisalby sie tam,
        # gdzie nie udalo sie wpisac ZWIERZ/WODNE
        for sql in zapytania:
            if not self.baza.wpisz(sql):
                self.iface.messageBar().pushMessage(
                    'BAZA',
                    'Błąd zapisu uszkodzeń do F_SUBAREA - przerwano. '
                    'Kopia bazy sprzed zmian w Kopie_manipulacyjne.',
                    Qgis.Critical, 0)
                self.baza.zamknij()
                return False

        self.iface.messageBar().pushMessage(
            'OK',
            'Uzupełniono uszkodzenia w F_SUBAREA - CAUSE_CD: ' +
            str(self.ile_zwierz + self.ile_woda + self.ile_klimat) +
            ' (ZWIERZ: ' + str(self.ile_zwierz) + ', WODNE: ' +
            str(self.ile_woda) + ', KLIMAT: ' + str(self.ile_klimat) +
            '), DAMAGE_DEGREE_CD: ' + str(self.ile_stopien),
            Qgis.Success, 10)

        self.baza.zamknij()
        return True
