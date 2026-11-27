from qgis.core import QgsProject, Qgis
from .przyciski import QMessageBox

from .baza_wrapper import Baza, znajdz_baze_do_wydz

# Uszkodzenia (stopien + przyczyna) wpisuje sie tylko w wydzieleniach z
# pietrem drzewostanu (DRZEW, IP, IIP w F_AROD_STOREY) - bez niego (HAL,
# PŁAZ, ZRĄB, DROGI L, same uprawy pod oslona itp.) pola zostaja puste
PIETRA_DRZEWOSTANU = ('DRZEW', 'IP', 'IIP')
SQL_DRZEWOSTAN = (
    "ARODES_INT_NUM in (select ARODES_INT_NUM from F_AROD_STOREY "
    "where STOREY_CD in ('" + "', '".join(PIETRA_DRZEWOSTANU) + "'))"
)

# siedliska bagienne, olsy i legi - przyczyna uszkodzenia WODNE zamiast
# domyslnego KLIMAT
SITE_TYPY_BAGIENNE = ('BB', 'BMB', 'LMB', 'BGB', 'BMGB')
SITE_TYPY_OLSY = ('OL', 'OLJ', 'OLJG', 'OLJWYŻ')
SITE_TYPY_LEGI = ('LŁ', 'LŁG', 'LŁWYŻ')
SITE_TYPY_WODA = SITE_TYPY_BAGIENNE + SITE_TYPY_OLSY + SITE_TYPY_LEGI

# ponizej tego wieku gatunku panujacego (pietro DRZEW, rank 1) przyczyna
# uszkodzenia to ZWIERZ - ma pierwszenstwo przed WODNE i KLIMAT
WIEK_ZWIERZ = 20

# wydzielenia z mlodym gatunkiem panujacym
SQL_MLODE = (
    "ARODES_INT_NUM in (select ARODES_INT_NUM from F_STOREY_SPECIES "
    "where STOREY_CD='DRZEW' and SPECIES_RANK_ORDER=1 and "
    "SPECIES_AGE < " + str(WIEK_ZWIERZ) + ")"
)

_SITE_LISTA = "', '".join(SITE_TYPY_WODA)
_SQL_WODA = "SITE_TYPE_CD in ('" + _SITE_LISTA + "')"

# Kolejnosc ma znaczenie: najpierw ZWIERZ dla mlodych d-stanow, potem WODNE
# dla siedlisk bagiennych/olsow/legow, na koncu KLIMAT dla pozostalych -
# kazdy krok zmienia tylko puste CAUSE_CD, wiec pozniejszy nie nadpisze
# wczesniejszego. DAMAGE_DEGREE_CD jest niezalezne od wyboru przyczyny.
_ZAPYTANIA = [
    "update F_SUBAREA set CAUSE_CD='ZWIERZ' where " +
    SQL_DRZEWOSTAN + " and CAUSE_CD is null and " + SQL_MLODE + ";",
    "update F_SUBAREA set CAUSE_CD='WODNE' where " +
    SQL_DRZEWOSTAN + " and CAUSE_CD is null and " + _SQL_WODA + ";",
    "update F_SUBAREA set CAUSE_CD='KLIMAT' where " +
    SQL_DRZEWOSTAN + " and CAUSE_CD is null;",
    "update F_SUBAREA set DAMAGE_DEGREE_CD='0' where " +
    SQL_DRZEWOSTAN + " and DAMAGE_DEGREE_CD is null;",
]


def _policz(baza, warunek):
    pob = baza.pobierz(
        "select count(*) from F_SUBAREA where " + SQL_DRZEWOSTAN +
        " and " + warunek + ";"
    )
    return pob[0][0] if pob else 0


def policz_puste(baza):
    """Liczy w podlaczonej bazie, ile rekordow F_SUBAREA (z pietrem
    drzewostanu) zostanie uzupelnionych. Zwraca slownik {zwierz, woda, klimat, stopien}."""
    zwierz = _policz(baza, "CAUSE_CD is null and " + SQL_MLODE)
    woda = _policz(
        baza, "CAUSE_CD is null and " + _SQL_WODA + " and not " + SQL_MLODE)
    klimat = _policz(baza, "CAUSE_CD is null") - zwierz - woda
    return {
        'zwierz': zwierz,
        'woda': woda,
        'klimat': klimat,
        'stopien': _policz(baza, "DAMAGE_DEGREE_CD is null"),
    }


def zapisz_puste(baza):
    """Uzupelnia puste CAUSE_CD i DAMAGE_DEGREE_CD w podlaczonej bazie.
    Niepuste wartosci nie sa zmieniane. Przerywa na pierwszym bledzie -
    inaczej KLIMAT wpisalby sie tam, gdzie nie udalo sie wpisac ZWIERZ/WODNE.
    """
    for sql in _ZAPYTANIA:
        if not baza.wpisz(sql):
            return False
    return True


def uzupelnij_po_cichu(baza, kopia=True):
    """Wersja bez okien dla innych skryptow (np. Dopisz/sprawdź zabiegi).
    baza - podlaczony obiekt Baza (nie jest zamykany).
    kopia - przed zapisem zrob kopie w Kopie_manipulacyjne (tylko gdy jest
    co uzupelniac).
    Zwraca slownik z policz_puste() albo False przy bledzie zapisu."""
    ile = policz_puste(baza)
    if sum(ile.values()) == 0:
        return ile
    if kopia:
        baza.utworz_kopie('uzupelnij_uszkodzenia')
    if not zapisz_puste(baza):
        return False
    return ile


def opis_wyniku(ile):
    """Krotkie podsumowanie do paska komunikatow/raportu."""
    return (
        'CAUSE_CD: ' + str(ile['zwierz'] + ile['woda'] + ile['klimat']) +
        ' (ZWIERZ: ' + str(ile['zwierz']) + ', WODNE: ' + str(ile['woda']) +
        ', KLIMAT: ' + str(ile['klimat']) + '), DAMAGE_DEGREE_CD: ' +
        str(ile['stopien'])
    )


class UzupelnijUszkodzenia:
    def __init__(self, iface):
        self.iface = iface
        self.baza = Baza('')
        self.ile = {'zwierz': 0, 'woda': 0, 'klimat': 0, 'stopien': 0}

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

    def policz(self):
        """Laczy sie z baza i liczy, ile rekordow F_SUBAREA zostanie
        zmienionych - osobno dla CAUSE_CD (z podzialem ZWIERZ/WODNE/KLIMAT) i
        dla DAMAGE_DEGREE_CD. Zmieniane sa tylko puste (NULL) pola."""
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                'BAZA', 'Nie udało się połączyć z bazą', Qgis.Critical, 10)
            return False
        self.ile = policz_puste(self.baza)
        return True

    def potwierdz(self):
        """Pokazuje podsumowanie znalezionych pustych rekordow i pyta o
        potwierdzenie zapisu. Zwraca False (bez pytania) jesli nie ma nic
        do uzupelnienia."""
        ile = self.ile
        razem_cause = ile['zwierz'] + ile['woda'] + ile['klimat']
        if razem_cause == 0 and ile['stopien'] == 0:
            self.iface.messageBar().pushMessage(
                'Uzupełnij uszkodzenia',
                'Brak pustych rekordów do uzupełnienia w F_SUBAREA (wydzielenia '
                'z piętrem drzewostanu)',
                Qgis.Info, 10)
            return False

        odp = QMessageBox.question(
            self.iface.mainWindow(),
            'Uzupełnij uszkodzenia w bazie',
            'W tabeli F_SUBAREA (wydzielenia z piętrem drzewostanu DRZEW/'
            'IP/IIP) znaleziono puste pola:\n\n'
            'CAUSE_CD - do uzupełnienia: ' + str(razem_cause) + '\n'
            '   (ZWIERZ - gat. panujący poniżej ' + str(WIEK_ZWIERZ) +
            ' lat: ' + str(ile['zwierz']) + ',\n'
            '    WODNE - siedliska bagienne, olsy i łęgi: ' +
            str(ile['woda']) + ',\n'
            '    KLIMAT - pozostałe: ' + str(ile['klimat']) + ')\n'
            'DAMAGE_DEGREE_CD - do uzupełnienia (\'0\'): ' +
            str(ile['stopien']) + '\n\n'
            'Istniejące, niepuste wartości nie zostaną zmienione.\n'
            'Wydzielenia bez piętra drzewostanu nie są uzupełniane.\n\n'
            'Kontynuować zapis do bazy?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return odp == QMessageBox.Yes

    def zapisz(self):
        """Zapisuje zmiany w F_SUBAREA (z kopia w Kopie_manipulacyjne)."""
        self.baza.utworz_kopie('uzupelnij_uszkodzenia')

        if not zapisz_puste(self.baza):
            self.iface.messageBar().pushMessage(
                'BAZA',
                'Błąd zapisu uszkodzeń do F_SUBAREA - przerwano. '
                'Kopia bazy sprzed zmian w Kopie_manipulacyjne.',
                Qgis.Critical, 0)
            self.baza.zamknij()
            return False

        self.iface.messageBar().pushMessage(
            'OK',
            'Uzupełniono uszkodzenia w F_SUBAREA - ' + opis_wyniku(self.ile),
            Qgis.Success, 10)

        self.baza.zamknij()
        return True
