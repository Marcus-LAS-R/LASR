class FK:
    """Klucz obcy w tabeli-dziecku wskazujący na słownik remapu budowany
    przez odpowiednią tabelę nadrzędną (np. sl_arodes/sl_parcel/sl_addr)."""

    def __init__(self, kolumna, slownik, wymagane=True):
        self.kolumna = kolumna    # nazwa kolumny w tabeli-dziecku
        self.slownik = slownik    # atrybut na Laczenie z dict remapu
        self.wymagane = wymagane  # False = NULL/0 przechodzi bez remapu


class TabelaNadrzedna:
    """Tabela z własnym surogatem budująca słownik remapu, którego
    używają tabele-dzieci (np. F_PARCEL -> sl_parcel, V_ADDRESS -> sl_addr).
    F_ARODES jest opisane tu tylko jako metadane do dialogu/zależności -
    jego właściwa logika łączenia zostaje w Laczenie.p_f_arodes()."""

    def __init__(self, klucz, nazwa, kolumny, indeks_klucza, slownik_docelowy,
                 funkcja_klucza_dedup=None, fk_wewnetrzne=None):
        self.klucz = klucz
        self.nazwa = nazwa
        self.kolumny = kolumny
        self.indeks_klucza = indeks_klucza
        self.slownik_docelowy = slownik_docelowy
        self.funkcja_klucza_dedup = funkcja_klucza_dedup
        self.fk_wewnetrzne = fk_wewnetrzne or []


class TabelaDziecko:
    """Tabela-dziecko z jedną lub dwiema kolumnami FK do zremapowania,
    opcjonalnie z własnym surogatem wymagającym sekwencyjnej renumeracji
    (wzorem dzisiejszego F_STOREY_SPECIES.SPEC_STOR_INT_NUM)."""

    def __init__(self, klucz, nazwa, kolumny, fk, wlasny_klucz=None,
                 wlasny_klucz_licznik=None):
        self.klucz = klucz
        self.nazwa = nazwa
        self.kolumny = kolumny
        self.fk = fk
        self.wlasny_klucz = wlasny_klucz
        self.wlasny_klucz_licznik = wlasny_klucz_licznik


class TabelaSlownikowa:
    """Grupa 1 (zawsze kopiowana): dedup po kluczu naturalnym, brak
    własnego surogatu, brak FK do innych tabel (np. F_COMMUNITY)."""

    def __init__(self, nazwa, kolumny, funkcja_klucza_dedup):
        self.nazwa = nazwa
        self.kolumny = kolumny
        self.funkcja_klucza_dedup = funkcja_klucza_dedup


# --- Grupa 1: zawsze kopiowana, brak checkboxa w dialogu ---
F_COMMUNITY = TabelaSlownikowa(
    'F_COMMUNITY',
    ['COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD', 'COMMUNITY_CD', 'COMMUNITY_NAME'],
    funkcja_klucza_dedup=lambda w: tuple(w[0:4]),
)

# Uwaga: F_ARODES nie ma tu odpowiednika TabelaNadrzedna - jego logika
# łączenia (w tym budowa sl_arodes) zostaje w Laczenie.p_f_arodes(), bo to
# najlepiej przetestowany kod w całym module. Klucz 'f_arodes' i checkbox
# 'checkBox_f_arodes' są mimo to częścią tego samego rejestru zależności w
# baza_polacz_dialog.py (_SLOWNIK_DO_CHECKBOXA).

# --- Grupa 2 "ewidencyjna": nadrzędne z własnym surogatem ---
F_PARCEL_NADRZEDNA = TabelaNadrzedna(
    'f_parcel', 'F_PARCEL',
    ['PARCEL_INT_NUM', 'PARCEL_NR', 'COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD',
     'COMMUNITY_CD', 'PARCEL_AREA', 'LAND_REGISTER_NR', 'REG_SHEET_NR1',
     'REG_SHEET_NR2', 'PARCEL_VALUE', 'VALUE_DAT', 'PARCEL_ADD_INFO',
     'DIST_COURT_REG_NR', 'DIST_COURT_REG_DAT', 'REGISTER_MON_NR', 'STAKE_1',
     'STAKE_2', 'OWNERSHIP_CD', 'LAND_USE_CD', 'INS_DAT', 'INS_LOGIN',
     'UPD_DAT', 'UPD_LOGIN'],
    indeks_klucza=0, slownik_docelowy='sl_parcel',
    funkcja_klucza_dedup=lambda w: (w[2], w[3], w[4], w[5], w[1]),
)

V_ADDRESS_NADRZEDNA = TabelaNadrzedna(
    'v_address', 'V_ADDRESS',
    ['ADDR_NR', 'NAME_1', 'NAME_2', 'PLACE', 'STREET', 'post_cd', 'POST',
     'stat_info', 'tax_nr', 'phone_nr', 'VIEW_ADDRESS_FL', 'LP_PRICE',
     'COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD', 'ADDRESS_ROLE_FL',
     'FR_ADDR_NR', 'addr_grp_fl'],
    indeks_klucza=0, slownik_docelowy='sl_addr',
    funkcja_klucza_dedup=None,  # brak dedup - zawsze nowy wiersz
    fk_wewnetrzne=[FK('FR_ADDR_NR', 'sl_addr', wymagane=False)],
)

# --- Grupa 3 "leśna": 8 dzisiejszych tabel, przeniesione 1:1 z Laczenie.tab ---
GRUPA3_DZIECI = [
    TabelaDziecko('f_subarea', 'f_subarea', [
        "ARODES_INT_NUM",
        "DAMAGE_DEGREE_CD",
        "CAUSE_CD",
        "AREA_TYPE_CD",
        "POSITION_CD",
        "RELIEF_CD",
        "SITE_TYPE_CD",
        "DEGRADATION_CD",
        "VEG_COVER_CD",
        "STAND_STRUCT_CD",
        "SLOPE_CD",
        "EXPOSURE_CD",
        "MOISTURE_CD",
        "SOIL_PEC_CD",
        "SOIL_SUBTYPE_CD",
        "PLANT_COMM_CD",
        "SUB_AREA",
        "FOREST_FUNC_CD",
        "ROTATION_AGE",
        "DEAD_WOOD",
        "SUBAREA_INFO",
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_arod_storey', 'f_arod_storey', [
        "ARODES_INT_NUM",
        "STOREY_CD",
        "STOREY_RANK_ORDER",
        "STANDDENSITY_INDEX",
        "MIXTURE_CD",
        "DENSITY_CD",
        "TREE_STOCK_CD",
        "SILV_QUALITY_CD",
        "LOCATION_CD",
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_storey_species', 'f_storey_species', [
        "SPEC_STOR_INT_NUM",
        "ARODES_INT_NUM",
        "STOREY_CD",
        "SPECIES_RANK_ORDER",
        "SPECIES_CD",
        "PART_CD",
        "SPECIES_AGE",
        "BHD",
        "HEIGHT",
        "VOLUME",
        "SITE_CLASS_CD",
        "TECHN_QUALITY_CD",
        "INCREMENT_CURRENT",
        "VOLUME_TEMP",
        "INCREMENT_CURRENT_AREA",
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')],
        wlasny_klucz='SPEC_STOR_INT_NUM', wlasny_klucz_licznik='maxspecstor'),

    TabelaDziecko('f_arod_stand_pec', 'f_arod_stand_pec', [
        "FOREST_PEC_CD",
        "ARODES_INT_NUM",
        "PEC_RANK_ORDER",
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_arod_goal', 'f_arod_goal', [
        "GOAL_TYPE_FL",
        "ARODES_INT_NUM",
        "SPECIES_CD",
        "GOAL_RANK_ORDER",
        "GOAL_SPECIES_PERC",
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_arod_spec_area', 'f_arod_spec_area', [
        "ARODES_INT_NUM",
        "AROD_SPAREA_ORDER",
        "SPECIAL_AREA_CD",
        "LOCATION_CD",
        "SPECIAL_AREA",
        "SPECIAL_AREA_YEAR",
        "SPECIAL_AREA_NUM",
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_species_sparea', 'f_species_sparea', [
        "ARODES_INT_NUM",
        "AROD_SPAREA_ORDER",
        "SP_RANK_ORDER",
        "SPECIES_CD",
        "SP_AGE",
        "SP_AGE_BEG",
        "SP_AGE_TEMP",
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_arod_phenomena', 'f_arod_phenomena', [
        "ARODES_INT_NUM",
        "PHEN_RANK_ORDER",
        "PHENOMENA_CD",
        "LOCATION_CD",
        "SPECIES_CD",
        "PLANT_CD",
        "PHEN_NUM",
        "PHEN_AREA",
        "NATURE_MON_FL",
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_arod_cue', 'F_AROD_CUE', [
        'ARODES_INT_NUM', 'MEASURE_CD', 'URGENCY', 'CUTTING_AREA',
        'LARGE_TIMBER_PERC', 'CUE_RANK_ORDER', 'SITE_NR', 'LARGE_TIMBER_VALUE',
        'LARGE_TIMBER_VALUE_NET', 'PROC_AREA',
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_arod_category', 'F_AROD_CATEGORY', [
        'PROT_CATEGORY_CD', 'ARODES_INT_NUM', 'PROT_RANK_ORDER',
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_arod_soil_spec', 'F_AROD_SOIL_SPEC', [
        'ARODES_INT_NUM', 'SOIL_RANK_ORDER', 'SOIL_SPECIES_CD', 'SOIL_LEVEL_CD',
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_compartment', 'F_COMPARTMENT', [
        'ARODES_INT_NUM', 'COMPARTMENT_CD', 'COMPARTMENT_NAME',
        'ALTITUDE_MAX', 'ALTITUDE_MIN',
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')]),

    TabelaDziecko('f_set', 'F_SET', [
        'ARODES_INT_NUM', 'SET_INT_NUM', 'SET_TYPE_FL', 'MY_INT_NUM',
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes')],
        wlasny_klucz='SET_INT_NUM', wlasny_klucz_licznik='maxset'),
        # MY_INT_NUM nie jest w fk ani wlasny_klucz -> kopiowane wprost
        # (zawsze 0 w dostepnych probkach, brak odpowiadajacej tabeli w
        # schemacie, wiec nie jest traktowane jako klucz obcy)

    TabelaDziecko('f_arod_damage', 'F_AROD_DAMAGE', [
        'arodes_int_num', 'damage_int_num', 'damage_grad_cd', 'damage_perc',
        'damage_area',
    ], fk=[FK('arodes_int_num', 'sl_arodes')],
        wlasny_klucz='damage_int_num', wlasny_klucz_licznik='maxdamage'),

    TabelaDziecko('f_arod_land_use', 'F_AROD_LAND_USE', [
        'PARCEL_INT_NUM', 'SHAPE_NR', 'ARODES_INT_NUM', 'AROD_LAND_USE_AREA',
        'LARGE_TIMBER_VALUE',
    ], fk=[FK('ARODES_INT_NUM', 'sl_arodes'), FK('PARCEL_INT_NUM', 'sl_parcel')]),
]

GRUPA2_DZIECI = [
    TabelaDziecko('f_parcel_land_use', 'F_PARCEL_LAND_USE',
        ['PARCEL_INT_NUM', 'SHAPE_NR', 'SOIL_QUALITY_CD', 'AREA_USE_CD',
         'LAND_USE_AREA', 'AFFORESTATION'],
        fk=[FK('PARCEL_INT_NUM', 'sl_parcel')]),

    TabelaDziecko('v_parcel_participation', 'V_PARCEL_PARTICIPATION',
        ['addr_nr', 'parcel_int_num', 'part_numerator', 'part_denominator',
         'second_addr_nr', 'cwd'],
        fk=[FK('addr_nr', 'sl_addr'), FK('parcel_int_num', 'sl_parcel'),
            FK('second_addr_nr', 'sl_addr', wymagane=False)]),
]


def rejestr_domyslny():
    """{'f_arodes': True, 'f_parcel': True, ...} - wszystko włączone
    (stan domyślny dialogu)."""
    klucze = ['f_arodes', 'f_parcel', 'v_address'] + \
        [t.klucz for t in GRUPA2_DZIECI] + [t.klucz for t in GRUPA3_DZIECI]
    return {k: True for k in klucze}
