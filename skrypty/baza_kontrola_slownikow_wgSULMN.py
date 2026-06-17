import os
import platform
from datetime import date, datetime
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza

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
]


_WHITELIST_AREA_TYPE_CD = (
    'D-STAN', 'INNE WYL', 'PŁAZ', 'SUKCESJA', 'HAL',
    'L ENERG', 'ZRĄB', 'LZ-Ł', 'DROGI L', 'RETEN',
)


def _sprawdz_whitelist(baza: Baza, tab_d: str, pole_d: str, whitelist: tuple):
    """Zwraca listę (adr_les, wartość) dla wartości spoza whitelisty.
    Pusta lista = brak błędów. False = nie udało się wykonać zapytania.
    """
    warunki = ' AND '.join(
        f"StrComp(RTrim(d.{pole_d}), '{w}', 0) <> 0" for w in whitelist
    )
    sql = (
        f"SELECT DISTINCT a.ADRESS_FOREST, d.{pole_d} "
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
    """Zwraca listę (adr_les, wartość) dla rekordów niezgodnych ze słownikiem.
    Pusta lista = brak błędów. False = nie udało się wykonać zapytania.
    """
    sql = (
        f"SELECT DISTINCT a.ADRESS_FOREST, d.{pole_d} "
        f"FROM (F_ARODES AS a "
        f"INNER JOIN {tab_d} AS d ON a.ARODES_INT_NUM = d.ARODES_INT_NUM) "
        f"LEFT JOIN {tab_sl} AS s ON "
        f"StrComp(RTrim(d.{pole_d}), RTrim(s.{pole_sl}), 0) = 0 "
        f"WHERE d.{pole_d} IS NOT NULL AND s.{pole_sl} IS NULL "
        f"ORDER BY a.ADRESS_FOREST;"
    )
    return baza.pobierz(sql)


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

    wyniki = []
    for tab_d, pole_d, tab_sl, pole_sl, opis in KONTROLE:
        bledy = _sprawdz(baza, tab_d, pole_d, tab_sl, pole_sl)
        wyniki.append((opis, bledy))
        if bledy is False:
            QgsMessageLog.logMessage(
                f'Kontrola słowników — pominięto: {opis}', 'Las-R', Qgis.Warning
            )

    opis_wl = 'F_SUBAREA.AREA_TYPE_CD — wartości spoza listy dopuszczalnych'
    bledy_wl = _sprawdz_whitelist(baza, 'F_SUBAREA', 'AREA_TYPE_CD', _WHITELIST_AREA_TYPE_CD)
    wyniki.append((opis_wl, bledy_wl))
    if bledy_wl is False:
        QgsMessageLog.logMessage(
            f'Kontrola słowników — pominięto: {opis_wl}', 'Las-R', Qgis.Warning
        )

    opis_param = 'F_PARAMETER.ObjectFullName — nazwa obiektu leśnego'
    bledy_param = _sprawdz_f_parameter(baza)
    wyniki.append((opis_param, bledy_param))
    if bledy_param is False:
        QgsMessageLog.logMessage(
            f'Kontrola słowników — pominięto: {opis_param}', 'Las-R', Qgis.Warning
        )

    czas = datetime.now().strftime('%d-%m-%Y_g%H-%M-%S')
    baza.zamknij()

    ile_blednych = sum(len(b) for _, b in wyniki if b is not False and len(b) > 0)
    ile_z_bledami = sum(1 for _, b in wyniki if b is not False and len(b) > 0)
    ile_ok = sum(1 for _, b in wyniki if b is not False and len(b) == 0)
    ile_pom = sum(1 for _, b in wyniki if b is False)

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

        for opis, bledy in wyniki:
            if bledy is False:
                plik.write(f'[POMINIĘTO]  {opis}{nl}')
            elif len(bledy) == 0:
                plik.write(f'[OK]         {opis}{nl}')
            else:
                plik.write(nl + l + nl)
                plik.write(f'[BŁĄD]       {opis}{nl}')
                plik.write(l + nl)
                for adr, wartosc in bledy:
                    plik.write(f'  {adr}\t{wartosc}{nl}')

        plik.write(nl + lp + nl)
        plik.write(
            f'OK: {ile_ok} | Z błędami: {ile_z_bledami} | '
            f'Pominięto: {ile_pom} | Błędnych wartości łącznie: {ile_blednych}{nl}'
        )

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
