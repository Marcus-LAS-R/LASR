from qgis.core import QgsProject, Qgis
from PyQt5.QtWidgets import QMessageBox

from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .funkcje import wybierz_warstwe_z_kandydatow

# siedliska "wilgotne", dla ktorych przyczyna uszkodzenia D-STANu to WODA
# zamiast domyslnego KLIMAT
SITE_TYPY_WODA = ('OL', 'OLJ', 'OLJG', 'LŁ', 'LŁG', 'OLJWYŻ', 'LŁWYŻ')


class UzupelnijUszkodzenia:
    def __init__(self, iface):
        self.iface = iface
        self.baza = Baza('')
        self.ile_woda = 0
        self.ile_klimat = 0
        self.ile_stopien = 0

    def pobierz_sciezke(self):
        """Baza nie jest wyszukiwana automatycznie - zawsze pokazuje okno
        "Wskaż bazę Taksatora" do recznego wyboru. Jezeli w TOC znajduje sie
        warstwa WYDZ, okno startuje domyslnie piętro wyzej niz jej folder
        SHP (tam, gdzie zwykle lezy baza taksatora)."""
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        wydz_kandydaci = [x for x in lyrs if x.name()[:4].upper() == 'WYDZ']
        wydz = wybierz_warstwe_z_kandydatow(self.iface, wydz_kandydaci, 'WYDZ')

        baza_sc = znajdz_baze_do_wydz(self.iface, wydz, poz=1, wskaz=True)
        if baza_sc is False:
            return False

        self.baza.baza = baza_sc
        return True

    def policz(self):
        """Laczy sie z baza i liczy, ile rekordow F_SUBAREA zostanie
        zmienionych - osobno dla CAUSE_CD (z podzialem KLIMAT/WODA) i dla
        DAMAGE_DEGREE_CD. Zmieniane sa tylko puste (NULL) pola."""
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                'BAZA', 'Nie udało się połączyć z bazą', Qgis.Critical, 10)
            return False

        site_lista = "', '".join(SITE_TYPY_WODA)

        pob = self.baza.pobierz(
            "select count(*) from F_SUBAREA where AREA_TYPE_CD='D-STAN' "
            "and CAUSE_CD is null and SITE_TYPE_CD in ('" + site_lista + "');"
        )
        self.ile_woda = pob[0][0] if pob else 0

        pob = self.baza.pobierz(
            "select count(*) from F_SUBAREA where AREA_TYPE_CD='D-STAN' "
            "and CAUSE_CD is null;"
        )
        self.ile_klimat = (pob[0][0] if pob else 0) - self.ile_woda

        pob = self.baza.pobierz(
            "select count(*) from F_SUBAREA where AREA_TYPE_CD='D-STAN' "
            "and DAMAGE_DEGREE_CD is null;"
        )
        self.ile_stopien = pob[0][0] if pob else 0

        return True

    def potwierdz(self):
        """Pokazuje podsumowanie znalezionych pustych rekordow i pyta o
        potwierdzenie zapisu. Zwraca False (bez pytania) jesli nie ma nic
        do uzupelnienia."""
        razem_cause = self.ile_woda + self.ile_klimat
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
            '   (KLIMAT: ' + str(self.ile_klimat) + ', WODA: ' +
            str(self.ile_woda) + ')\n'
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
        WODA dla siedlisk wilgotnych (tylko puste CAUSE_CD), potem KLIMAT
        dla pozostalych pustych CAUSE_CD w D-STANach - dzieki temu WODA nie
        zostanie nadpisane przez KLIMAT. DAMAGE_DEGREE_CD jest niezalezne od
        wyboru przyczyny."""
        self.baza.utworz_kopie('uzupelnij_uszkodzenia')

        site_lista = "', '".join(SITE_TYPY_WODA)

        self.baza.wpisz(
            "update F_SUBAREA set CAUSE_CD='WODA' where "
            "AREA_TYPE_CD='D-STAN' and CAUSE_CD is null and "
            "SITE_TYPE_CD in ('" + site_lista + "');"
        )
        self.baza.wpisz(
            "update F_SUBAREA set CAUSE_CD='KLIMAT' where "
            "AREA_TYPE_CD='D-STAN' and CAUSE_CD is null;"
        )
        self.baza.wpisz(
            "update F_SUBAREA set DAMAGE_DEGREE_CD='0' where "
            "AREA_TYPE_CD='D-STAN' and DAMAGE_DEGREE_CD is null;"
        )

        self.iface.messageBar().pushMessage(
            'OK',
            'Uzupełniono uszkodzenia w F_SUBAREA - CAUSE_CD: ' +
            str(self.ile_woda + self.ile_klimat) + ' (WODA: ' +
            str(self.ile_woda) + ', KLIMAT: ' + str(self.ile_klimat) +
            '), DAMAGE_DEGREE_CD: ' + str(self.ile_stopien),
            Qgis.Success, 10)

        self.baza.zamknij()
