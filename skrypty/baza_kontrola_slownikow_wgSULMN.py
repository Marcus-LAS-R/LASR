import os
import platform
from datetime import date, datetime
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza
from . import waypointy

# (tabela_danych, pole, tabela_słownikowa, pole_sl, opis)
KONTROLE = [
    # F_SUBAREA
    ('F_SUBAREA',        'AREA_TYPE_CD',    'F_AREA_TYPE_DIC',      'AREA_TYPE_CD',    'F_SUBAREA.AREA_TYPE_CD — rodzaj powierzchni'),
    ('F_SUBAREA',        'SITE_TYPE_CD',    'F_SITE_TYPE_DIC',      'SITE_TYPE_CD',    'F_SUBAREA.SITE_TYPE_CD — typ siedliskowy'),
    ('F_SUBAREA',        'STAND_STRUCT_CD', 'F_STAND_STRUCT_DIC',   'STAND_STRUCT_CD', 'F_SUBAREA.STAND_STRUCT_CD — budowa pionowa'),
    ('F_SUBAREA',        'VEG_COVER_CD',    'F_VEG_COVER_DIC',      'VEG_COVER_CD',    'F_SUBAREA.VEG_COVER_CD — pokrycie roślinne'),
    ('F_SUBAREA',        'CAUSE_CD',        'F_END_CAUSE_DIC',      'CAUSE_CD',        'F_SUBAREA.CAUSE_CD — przyczyna uszkodzeń'),
    ('F_SUBAREA',        'POSITION_CD',     'F_POSITION_DIC',       'POSITION_CD',     'F_SUBAREA.POSITION_CD — położenie'),
    ('F_SUBAREA',        'RELIEF_CD',       'F_RELIEF_DIC',         'RELIEF_CD',       'F_SUBAREA.RELIEF_CD — rzeźba terenu'),
    ('F_SUBAREA',        'DEGRADATION_CD',  'F_DEGRADATION_DIC',    'DEGRADATION_CD',  'F_SUBAREA.DEGRADATION_CD — degradacja'),
    ('F_SUBAREA',        'SLOPE_CD',        'F_SLOPE_DIC',          'SLOPE_CD',        'F_SUBAREA.SLOPE_CD — opis stoku'),
    ('F_SUBAREA',        'EXPOSURE_CD',     'F_EXPOSURE_DIC',       'EXPOSURE_CD',     'F_SUBAREA.EXPOSURE_CD — wystawa'),
    ('F_SUBAREA',        'MOISTURE_CD',     'F_MOISTENING_DIC',     'MOISTURE_CD',     'F_SUBAREA.MOISTURE_CD — uwilgotnienie'),
    ('F_SUBAREA',        'SOIL_PEC_CD',     'F_SOIL_PEC_DIC',       'SOIL_PEC_CD',     'F_SUBAREA.SOIL_PEC_CD — cecha gleby'),
    ('F_SUBAREA',        'SOIL_SUBTYPE_CD', 'F_SOIL_SUBTYPE_DIC',   'SOIL_SUBTYPE_CD', 'F_SUBAREA.SOIL_SUBTYPE_CD — podtyp gleby'),
    # F_STOREY_SPECIES
    ('F_STOREY_SPECIES', 'SPECIES_CD',      'F_TREE_SPECIES',       'SPECIES_CD',      'F_STOREY_SPECIES.SPECIES_CD — gatunek'),
    ('F_STOREY_SPECIES', 'SITE_CLASS_CD',   'F_SITE_CLASS_DIC',     'SITE_CLASS_CD',   'F_STOREY_SPECIES.SITE_CLASS_CD — bonitacja'),
    ('F_STOREY_SPECIES', 'PART_CD',         'F_PART_DIC',           'PART_CD',         'F_STOREY_SPECIES.PART_CD — udział'),
    # F_AROD_STOREY
    ('F_AROD_STOREY',    'DENSITY_CD',      'F_DENSITY_DIC',        'DENSITY_CD',      'F_AROD_STOREY.DENSITY_CD — zadrzewienie'),
    ('F_AROD_STOREY',    'MIXTURE_CD',      'F_MIXTURE_DIC',        'MIXTURE_CD',      'F_AROD_STOREY.MIXTURE_CD — mieszanka'),
    ('F_AROD_STOREY',    'TREE_STOCK_CD',   'F_TREE_STOCK_DIC',     'TREE_STOCK_CD',   'F_AROD_STOREY.TREE_STOCK_CD — zwarcie drzew'),
    # F_SPECIES_SPAREA
    ('F_SPECIES_SPAREA', 'SPECIES_CD',      'F_TREE_SPECIES',       'SPECIES_CD',      'F_SPECIES_SPAREA.SPECIES_CD — gatunek PNSW'),
    # F_AROD_CUE
    ('F_AROD_CUE',       'MEASURE_CD',      'F_MEASURE',            'measure_cd',      'F_AROD_CUE.MEASURE_CD — wskazówka gosp.'),
    # F_AROD_PHENOMENA
    ('F_AROD_PHENOMENA', 'PHENOMENA_CD',    'F_PHENOMENA_DIC',      'PHENOMENA_CD',    'F_AROD_PHENOMENA.PHENOMENA_CD — osobliwość przyrodnicza'),
    ('F_AROD_PHENOMENA', 'LOCATION_CD',     'F_LOCATION_DIC',       'LOCATION_CD',     'F_AROD_PHENOMENA.LOCATION_CD — lokalizacja osobliwości'),
    ('F_AROD_PHENOMENA', 'PLANT_CD',        'F_PLANT_DIC',          'PLANT_CD',        'F_AROD_PHENOMENA.PLANT_CD — gatunek rośliny'),
    # F_AROD_STAND_PEC (dopisane pod kątem kontroli wstępnej przed łączeniem baz TPU)
    ('F_AROD_STAND_PEC', 'FOREST_PEC_CD',   'F_FOREST_PEC_DIC',     'FOREST_PEC_CD',   'F_AROD_STAND_PEC.FOREST_PEC_CD — cecha szczególna drzewostanu'),
    # F_AROD_SPEC_AREA (dopisane pod kątem kontroli wstępnej przed łączeniem baz TPU)
    ('F_AROD_SPEC_AREA',  'SPECIAL_AREA_CD', 'F_SPECIALAREA_DIC',   'SPECIAL_AREA_CD', 'F_AROD_SPEC_AREA.SPECIAL_AREA_CD — rodzaj powierzchni specjalnej'),
    ('F_AROD_SPEC_AREA',  'LOCATION_CD',     'F_LOCATION_DIC',      'LOCATION_CD',     'F_AROD_SPEC_AREA.LOCATION_CD — lokalizacja powierzchni specjalnej'),
    # F_AROD_GOAL (dopisane pod kątem kontroli wstępnej przed łączeniem baz TPU)
    ('F_AROD_GOAL',       'SPECIES_CD',      'F_TREE_SPECIES',      'SPECIES_CD',      'F_AROD_GOAL.SPECIES_CD — gatunek docelowy'),
    # F_AROD_CATEGORY, F_AROD_SOIL_SPEC, F_AROD_DAMAGE (dopisane po
    # rozszerzeniu "Połącz bazy TPU" o Grupę leśną)
    ('F_AROD_CATEGORY',   'PROT_CATEGORY_CD', 'F_PROT_CATEG_DIC',   'PROT_CATEGORY_CD', 'F_AROD_CATEGORY.PROT_CATEGORY_CD — kategoria ochronności'),
    ('F_AROD_SOIL_SPEC',  'SOIL_SPECIES_CD', 'F_SOIL_SPECIES_DIC',  'SOIL_SPECIES_CD', 'F_AROD_SOIL_SPEC.SOIL_SPECIES_CD — gatunek glebowy'),
    ('F_AROD_SOIL_SPEC',  'SOIL_LEVEL_CD',   'F_SOIL_LEVEL_DIC',    'SOIL_LEVEL_CD',   'F_AROD_SOIL_SPEC.SOIL_LEVEL_CD — poziom glebowy'),
    ('F_AROD_DAMAGE',     'damage_grad_cd',  'F_DAMAGE_GRAD_DIC',   'damage_grad_cd',  'F_AROD_DAMAGE.damage_grad_cd — stopień szkody'),
]

# (tabela_danych_rooted_w_F_PARCEL, pole, tabela_słownikowa, pole_sl, opis) -
# dopisane po rozszerzeniu "Połącz bazy TPU" o Grupę ewidencyjną. F_PARCEL
# nie jest powiązane z F_ARODES, więc te kontrole nie mogą użyć _sprawdz()
# (JOIN przez F_ARODES) - patrz _sprawdz_parcel().
KONTROLE_PARCEL = [
    ('F_PARCEL', 'OWNERSHIP_CD', 'F_OWNERSHIP_DIC',   'OWNERSHIP_CD', 'F_PARCEL.OWNERSHIP_CD — forma własności'),
    ('F_PARCEL', 'LAND_USE_CD',  'F_LAND_USE_PL_DIC', 'LAND_USE_CD',  'F_PARCEL.LAND_USE_CD — sposób użytkowania gruntu'),
    # Uwaga: F_PARCEL_LAND_USE.SOIL_QUALITY_CD i AREA_USE_CD świadomie
    # pominięte - słowniki (F_SOIL_QUALITY_DIC/F_AREA_USE_DIC) używają innej
    # wielkości liter (IIIA/Dr) niż faktycznie zapisywane dane (IIIa/dr) w
    # KAŻDEJ dostępnej próbce bazy, a StrComp(...,...,0) jest tu binarny
    # (uwzględnia wielkość liter) - dodanie tych kontroli generowałoby
    # dziesiątki/setki fałszywych alarmów na każdej bazie
]

# F_AROD_GOAL.GOAL_TYPE_FL nie ma w bazie osobnej tabeli słownikowej (brak FK) —
# w próbkach baz obserwowana jest wyłącznie wartość 'D', więc kontrolowana jest
# przez whitelistę, tak jak F_SUBAREA.AREA_TYPE_CD.
_WHITELIST_GOAL_TYPE_FL = ('D',)

# F_SET.SET_TYPE_FL nie ma osobnej tabeli słownikowej - w dostępnych
# próbkach (tylko 2 niepuste bazy) obserwowana jest wyłącznie wartość 'K'.
_WHITELIST_SET_TYPE_FL = ('K',)

# F_AROD_CUE.URGENCY nie ma osobnej tabeli słownikowej - w dostępnych
# próbkach obserwowane wartości 'N' i 'T'.
_WHITELIST_URGENCY = ('N', 'T')

# V_PARCEL_PARTICIPATION.cwd nie ma osobnej tabeli słownikowej - w
# dostępnych próbkach obserwowane wyłącznie 'WD' i 'WL'.
_WHITELIST_CWD = ('WD', 'WL')


_WHITELIST_AREA_TYPE_CD = (
    'D-STAN', 'INNE WYL', 'PŁAZ', 'SUKCESJA', 'HAL',
    'L ENERG', 'ZRĄB', 'LZ-Ł', 'DROGI L', 'RETEN', 'ARBOR',
)


def _sprawdz_whitelist(baza: Baza, tab_d: str, pole_d: str, whitelist: tuple):
    """Zwraca listę (adr_les, arodes_int_num, wartość) dla wartości spoza
    whitelisty. Pusta lista = brak błędów. False = nie udało się wykonać
    zapytania.
    """
    warunki = ' AND '.join(
        f"StrComp(RTrim(d.{pole_d}), '{w}', 0) <> 0" for w in whitelist
    )
    sql = (
        f"SELECT DISTINCT a.ADRESS_FOREST, a.ARODES_INT_NUM, d.{pole_d} "
        f"FROM F_ARODES AS a "
        f"INNER JOIN {tab_d} AS d ON a.ARODES_INT_NUM = d.ARODES_INT_NUM "
        f"WHERE d.{pole_d} IS NOT NULL AND {warunki} "
        f"ORDER BY a.ADRESS_FOREST;"
    )
    return baza.pobierz(sql)


def _sprawdz_f_parameter(baza: Baza):
    """Sprawdza czy F_PARAMETER.ObjectFullName jest wypełnione (wg Mapa PU).
    Zwraca [] jeśli OK, [('F_PARAMETER', opis)] jeśli błąd, False przy niepowodzeniu.
    """
    wynik = baza.pobierz("SELECT ObjectFullName FROM F_PARAMETER;")
    if wynik is False:
        return False
    if len(wynik) == 0 or wynik[0][0] is None or str(wynik[0][0]).strip() == '':
        return [('F_PARAMETER', 'ObjectFullName jest puste lub brak rekordu')]
    return []


def _sprawdz(baza: Baza, tab_d: str, pole_d: str, tab_sl: str, pole_sl: str):
    """Zwraca listę (adr_les, arodes_int_num, wartość) dla rekordów
    niezgodnych ze słownikiem. Pusta lista = brak błędów. False = nie udało
    się wykonać zapytania.
    """
    sql = (
        f"SELECT DISTINCT a.ADRESS_FOREST, a.ARODES_INT_NUM, d.{pole_d} "
        f"FROM (F_ARODES AS a "
        f"INNER JOIN {tab_d} AS d ON a.ARODES_INT_NUM = d.ARODES_INT_NUM) "
        f"LEFT JOIN {tab_sl} AS s ON "
        f"StrComp(RTrim(d.{pole_d}), RTrim(s.{pole_sl}), 0) = 0 "
        f"WHERE d.{pole_d} IS NOT NULL AND s.{pole_sl} IS NULL "
        f"ORDER BY a.ADRESS_FOREST;"
    )
    return baza.pobierz(sql)


def _sprawdz_parcel(baza: Baza, pole_d: str, tab_sl: str, pole_sl: str):
    """Jak _sprawdz(), ale dla pól bezpośrednio w F_PARCEL - ta tabela nie
    ma ARODES_INT_NUM (nie jest powiązana z F_ARODES), więc rekordy
    niezgodne ze słownikiem raportowane są po adresie działki
    (COUNTY.DISTRICT.MUNICIPALITY.COMMUNITY.PARCEL_NR) zamiast adresu
    leśnego. Zwraca listę (adres_dzialki, wartość) - Access nie pozwala
    sortować po kolumnie skonkatenowanej w SQL razem z DISTINCT, więc
    sklejamy adres w Pythonie zamiast w zapytaniu.
    """
    sql = (
        f"SELECT DISTINCT p.COUNTY_CD, p.DISTRICT_CD, p.MUNICIPALITY_CD, "
        f"p.COMMUNITY_CD, p.PARCEL_NR, p.{pole_d} "
        f"FROM F_PARCEL AS p "
        f"LEFT JOIN {tab_sl} AS s ON "
        f"StrComp(RTrim(p.{pole_d}), RTrim(s.{pole_sl}), 0) = 0 "
        f"WHERE p.{pole_d} IS NOT NULL AND s.{pole_sl} IS NULL "
        f"ORDER BY p.PARCEL_NR;"
    )
    wynik = baza.pobierz(sql)
    if wynik is False:
        return False
    return [('.'.join(str(x) for x in row[:5]), row[5]) for row in wynik]


def _sprawdz_whitelist_parcel_dziecko(baza: Baza, tab_d: str, pole_d: str,
                                       whitelist: tuple):
    """Jak _sprawdz_whitelist(), ale dla tabel-dzieci F_PARCEL (join przez
    PARCEL_INT_NUM zamiast ARODES_INT_NUM), np. V_PARCEL_PARTICIPATION."""
    warunki = ' AND '.join(
        f"StrComp(RTrim(d.{pole_d}), '{w}', 0) <> 0" for w in whitelist
    )
    sql = (
        f"SELECT DISTINCT p.PARCEL_NR, d.{pole_d} "
        f"FROM (F_PARCEL AS p "
        f"INNER JOIN {tab_d} AS d ON p.PARCEL_INT_NUM = d.parcel_int_num) "
        f"WHERE d.{pole_d} IS NOT NULL AND {warunki} "
        f"ORDER BY p.PARCEL_NR;"
    )
    return baza.pobierz(sql)


def _uruchom_kontrole(baza: Baza):
    """Uruchamia wszystkie kontrole słownikowe (KONTROLE + whitelisty + F_PARAMETER)
    na już połączonej bazie. Zwraca listę (opis, bledy, typ_klucza).

    typ_klucza mówi, jak zbudować waypoint z wiersza błędu (patrz
    _zbierz_waypointy poniżej):
      'arodes' - wiersz (ADRESS_FOREST, ARODES_INT_NUM, wartość), błąd
                 nawigowalny po adresie leśnym (pole ADR_LES w warstwie
                 wydzieleń - UWAGA: to NIE jest LANDID z warstwy Ls, LANDID
                 to kod klasoużytku na działce, zupełnie inny byt niż adres
                 leśny)
      'parcel' - wiersz (adres_dzialki, wartość), błąd nawigowalny po
                 adresie działki (PARCELID w warstwie działek)
      'brak'   - kształt wiersza niewystarczający do wskazania obiektu na
                 mapie (np. sam PARCEL_NR bez pełnego adresu, albo brak
                 adresu w ogóle) - błąd trafia tylko do raportu TXT
    """
    wyniki = []
    for tab_d, pole_d, tab_sl, pole_sl, opis in KONTROLE:
        bledy = _sprawdz(baza, tab_d, pole_d, tab_sl, pole_sl)
        wyniki.append((opis, bledy, 'arodes'))
        if bledy is False:
            QgsMessageLog.logMessage(
                f'Kontrola słowników — pominięto: {opis}', 'Las-R', Qgis.Warning
            )

    for tab_d, pole_d, tab_sl, pole_sl, opis in KONTROLE_PARCEL:
        bledy = _sprawdz_parcel(baza, pole_d, tab_sl, pole_sl)
        wyniki.append((opis, bledy, 'parcel'))
        if bledy is False:
            QgsMessageLog.logMessage(
                f'Kontrola słowników — pominięto: {opis}', 'Las-R', Qgis.Warning
            )

    opis_set = 'F_SET.SET_TYPE_FL — wartości spoza listy dopuszczalnych'
    bledy_set = _sprawdz_whitelist(baza, 'F_SET', 'SET_TYPE_FL', _WHITELIST_SET_TYPE_FL)
    wyniki.append((opis_set, bledy_set, 'arodes'))
    if bledy_set is False:
        QgsMessageLog.logMessage(
            f'Kontrola słowników — pominięto: {opis_set}', 'Las-R', Qgis.Warning
        )

    opis_urg = 'F_AROD_CUE.URGENCY — wartości spoza listy dopuszczalnych'
    bledy_urg = _sprawdz_whitelist(baza, 'F_AROD_CUE', 'URGENCY', _WHITELIST_URGENCY)
    wyniki.append((opis_urg, bledy_urg, 'arodes'))
    if bledy_urg is False:
        QgsMessageLog.logMessage(
            f'Kontrola słowników — pominięto: {opis_urg}', 'Las-R', Qgis.Warning
        )

    # Uwaga: V_PARCEL_PARTICIPATION nie ma powiązania z F_ARODES ani pełnego
    # adresu działki (tylko PARCEL_NR) - błędy tej kontroli nie da się
    # jednoznacznie wskazać na mapie, więc typ='brak' (pomijane w
    # waypointach, obecne tylko w raporcie TXT).
    opis_cwd = 'V_PARCEL_PARTICIPATION.cwd — wartości spoza listy dopuszczalnych'
    bledy_cwd = _sprawdz_whitelist_parcel_dziecko(
        baza, 'V_PARCEL_PARTICIPATION', 'cwd', _WHITELIST_CWD)
    wyniki.append((opis_cwd, bledy_cwd, 'brak'))
    if bledy_cwd is False:
        QgsMessageLog.logMessage(
            f'Kontrola słowników — pominięto: {opis_cwd}', 'Las-R', Qgis.Warning
        )

    opis_wl = 'F_SUBAREA.AREA_TYPE_CD — wartości spoza listy dopuszczalnych'
    bledy_wl = _sprawdz_whitelist(baza, 'F_SUBAREA', 'AREA_TYPE_CD', _WHITELIST_AREA_TYPE_CD)
    wyniki.append((opis_wl, bledy_wl, 'arodes'))
    if bledy_wl is False:
        QgsMessageLog.logMessage(
            f'Kontrola słowników — pominięto: {opis_wl}', 'Las-R', Qgis.Warning
        )

    opis_goal = 'F_AROD_GOAL.GOAL_TYPE_FL — wartości spoza listy dopuszczalnych'
    bledy_goal = _sprawdz_whitelist(baza, 'F_AROD_GOAL', 'GOAL_TYPE_FL', _WHITELIST_GOAL_TYPE_FL)
    wyniki.append((opis_goal, bledy_goal, 'arodes'))
    if bledy_goal is False:
        QgsMessageLog.logMessage(
            f'Kontrola słowników — pominięto: {opis_goal}', 'Las-R', Qgis.Warning
        )

    # F_PARAMETER nie ma adresu w ogóle (jeden rekord globalny) - typ='brak'.
    opis_param = 'F_PARAMETER.ObjectFullName — nazwa obiektu leśnego'
    bledy_param = _sprawdz_f_parameter(baza)
    wyniki.append((opis_param, bledy_param, 'brak'))
    if bledy_param is False:
        QgsMessageLog.logMessage(
            f'Kontrola słowników — pominięto: {opis_param}', 'Las-R', Qgis.Warning
        )

    return wyniki


def _zbierz_waypointy(wyniki):
    """Buduje listę waypointów (do Nawigatora błędów) z wyników
    _uruchom_kontrole(). Pomija kontrole typu 'brak' (nienawigowalne) oraz
    te bez błędów."""
    wiersze = []
    for opis, bledy, typ in wyniki:
        if bledy is False or len(bledy) == 0 or typ == 'brak':
            continue

        if typ == 'arodes':
            for adr_les, arodes_int_num, wartosc in bledy:
                wiersze.append(waypointy.wiersz(
                    'Kontrola słownikowa SULMN', opis, 'ADR_LES', adr_les,
                    f'wartość={wartosc!r}'))
        elif typ == 'parcel':
            for adr_dzialki, wartosc in bledy:
                wiersze.append(waypointy.wiersz(
                    'Kontrola słownikowa SULMN', opis, 'PARCELID', adr_dzialki,
                    f'wartość={wartosc!r}'))

    return wiersze


def _zapisz_raport(plik, opis_baza, wyniki):
    """Dopisuje do otwartego pliku raportu sekcję z wynikami dla jednej bazy."""
    lp = '=' * 72
    l = '-' * 72
    nl = '\r\n'

    plik.write(lp + nl)
    plik.write(f'Baza:  {opis_baza}{nl}')
    plik.write(lp + nl + nl)

    for opis, bledy, _typ in wyniki:
        if bledy is False:
            plik.write(f'[POMINIĘTO]  {opis}{nl}')
        elif len(bledy) == 0:
            plik.write(f'[OK]         {opis}{nl}')
        else:
            plik.write(nl + l + nl)
            plik.write(f'[BŁĄD]       {opis}{nl}')
            plik.write(l + nl)
            for wiersz in bledy:
                plik.write('  ' + '\t'.join(str(x) for x in wiersz) + nl)

    plik.write(nl)


def KontrolaSlownikowWiele(katalog_raportu: str, sciezki: list):
    """Uruchamia kontrolę słownikową kolejno na wielu bazach (np. przed
    łączeniem baz TPU) i zapisuje jeden wspólny raport TXT w podanym katalogu.
    Zwraca (ile_blednych_lacznie, sciezka_raportu)."""
    czas = datetime.now().strftime('%d-%m-%Y_g%H-%M-%S')
    rap_sc = os.path.join(katalog_raportu, f'kontrola_slownikow_przed_laczeniem_{czas}.txt')

    nl = '\r\n'
    ile_blednych = 0

    with open(rap_sc, 'w', encoding='utf-8') as plik:
        plik.write(f'KONTROLA SŁOWNIKOWA BAZ WEJŚCIOWYCH PRZED ŁĄCZENIEM TPU{nl}')
        plik.write(f'Data:  {date.today()}{nl}{nl}')

        for baza_sc in sciezki:
            baza = Baza(baza_sc)
            if not baza.polacz():
                plik.write(f'[BŁĄD POŁĄCZENIA]  {baza_sc}{nl}{nl}')
                QgsMessageLog.logMessage(
                    f'Kontrola słowników — nie udało się połączyć z bazą: {baza_sc}',
                    'Las-R', Qgis.Warning
                )
                continue

            wyniki = _uruchom_kontrole(baza)
            baza.zamknij()

            ile_blednych += sum(
                len(b) for _, b, _typ in wyniki if b is not False and len(b) > 0
            )
            _zapisz_raport(plik, baza_sc, wyniki)

        plik.write('=' * 72 + nl)
        plik.write(f'Błędnych wartości łącznie (wszystkie bazy): {ile_blednych}{nl}')

    return ile_blednych, rap_sc


def KontrolaSlownikow(iface):
    baza_sc = QFileDialog().getOpenFileName(
        iface.mainWindow(),
        'Wskaż bazę Taksatora',
        '',
        'Access MDB (*.mdb)',
    )[0]
    if not baza_sc:
        return

    baza = Baza(baza_sc)
    if not baza.polacz():
        iface.messageBar().pushMessage(
            'BŁĄD', f'Nie można połączyć się z bazą: {baza_sc}',
            Qgis.Critical, 10
        )
        return

    wyniki = _uruchom_kontrole(baza)

    czas = datetime.now().strftime('%d-%m-%Y_g%H-%M-%S')
    baza.zamknij()

    ile_blednych = sum(len(b) for _, b, _t in wyniki if b is not False and len(b) > 0)
    ile_z_bledami = sum(1 for _, b, _t in wyniki if b is not False and len(b) > 0)
    ile_ok = sum(1 for _, b, _t in wyniki if b is not False and len(b) == 0)
    ile_pom = sum(1 for _, b, _t in wyniki if b is False)

    # raport TXT obok bazy
    nazwa_bazy = os.path.splitext(os.path.basename(baza_sc))[0]
    rap_sc = os.path.join(
        os.path.dirname(baza_sc),
        f'kontrola_slownikow_{nazwa_bazy}_{czas}.txt'
    )

    lp = '=' * 72
    l  = '-' * 72
    nl = '\r\n'

    with open(rap_sc, 'w', encoding='utf-8') as plik:
        plik.write(f'KONTROLA SŁOWNIKOWA BAZY TAKSATORA{nl}')
        plik.write(lp + nl)
        plik.write(f'Baza:  {baza_sc}{nl}')
        plik.write(f'Data:  {date.today()}{nl}')
        plik.write(lp + nl + nl)

        for opis, bledy, _typ in wyniki:
            if bledy is False:
                plik.write(f'[POMINIĘTO]  {opis}{nl}')
            elif len(bledy) == 0:
                plik.write(f'[OK]         {opis}{nl}')
            else:
                plik.write(nl + l + nl)
                plik.write(f'[BŁĄD]       {opis}{nl}')
                plik.write(l + nl)
                for wiersz in bledy:
                    plik.write('  ' + '\t'.join(str(x) for x in wiersz) + nl)

        plik.write(nl + lp + nl)
        plik.write(
            f'OK: {ile_ok} | Z błędami: {ile_z_bledami} | '
            f'Pominięto: {ile_pom} | Błędnych wartości łącznie: {ile_blednych}{nl}'
        )

    waypointy_sc = None
    wiersze_wp = _zbierz_waypointy(wyniki)
    if len(wiersze_wp) > 0:
        waypointy_sc = os.path.join(
            os.path.dirname(baza_sc),
            f'kontrola_slownikow_waypointy_{nazwa_bazy}_{czas}.csv'
        )
        waypointy.zapisz(waypointy_sc, wiersze_wp)

    poziom = Qgis.Success if ile_blednych == 0 else Qgis.Warning
    iface.messageBar().pushMessage(
        'Kontrola słownikowa',
        f'Błędnych wartości: {ile_blednych}. Raport: {rap_sc}',
        poziom, 10
    )

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle('Kontrola słownikowa')
    msg.setText(
        f'Kontrola zakończona.\n'
        f'Błędnych wartości: {ile_blednych}\n\n'
        f'Pokazać raport?'
    )
    msg.addButton('Nie', QMessageBox.ActionRole)
    msg.addButton('Tak', QMessageBox.ActionRole)
    if msg.exec_() == 1 and platform.system()[:3] == 'Win':
        os.startfile(rap_sc)

    return waypointy_sc
