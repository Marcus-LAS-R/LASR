import os
import glob
import platform
import pypyodbc as pyodbc
import sqlite3
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QVariant
from qgis.core import Qgis
from datetime import datetime
from shutil import copyfile


def znajdz_baze_do_wydz(iface, wydzlyr=False, poz=2):
    if wydzlyr is not False:
        wydz = wydzlyr
    else:
        wydz = iface.activeLayer()

    bTemp = []
    kat = ''
    if wydz is not None:
        wydz_sc = wydz.dataProvider().dataSourceUri().split("|")[0]
        kat = os.path.dirname(wydz_sc)

        if wydz.name() == 'ODDZ' or poz == 1:
            poziom = '..'
        else:
            poziom = '../..'

        try:
            if platform.system()[:3] == 'Win':
                bTemp = glob.glob(os.path.join(kat, poziom, "*.mdb"))
            else:
                bTemp = glob.glob(os.path.join(kat, poziom, "*.sqlite"))
        except:  # nopep8
            iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się odnaleźć bazy - wysyp',
                Qgis.Critical,
                10)
            return False

    if len(bTemp) != 1:
        bTemp = [QFileDialog().getOpenFileName(
            iface.mainWindow(),
            'Wskaż baze Taksatora',
            kat,
            "Access MDB (*.mdb);;SQLite (*.sqlite)")[0]
        ]

    if len(bTemp) == 1:
        baza = Baza(bTemp[0])
        if baza.polacz():
            baza.zamknij()
            return os.path.abspath(bTemp[0])
        else:
            iface.messageBar().pushMessage(
                'Baza',
                'Nie udało się pobrać danych z bazy',
                Qgis.Critical,
                10)
    else:
        iface.messageBar().pushMessage(
            'Baza',
            'Nie udało się pobrać danych z bazy',
            Qgis.Critical,
            10)
    return False


class Baza(object):
    def __init__(self, b):
        # otworz podana baze danych
        self.con = False
        self.cur = False
        self.ok = False
        self.baza = b

        self.czas = \
            datetime.now().isoformat().replace(':', '')[:-7]

        # sprawdź czy baza jest poprawna i mozna sie do niej podlaczyc
        # self.polacz(b)

    def polacz(self):
        '''Metoda sprawdzajaca i laczaca sie z bazą'''

        # jezeli juz jestesmy polaczeni, nic ni rob
        if self.con and self.cur:
            return True

        if self.baza[-3:] == 'mdb':
            MDB = self.baza
            DRV = '{Microsoft Access Driver (*.mdb, *.accdb)}'
            PWD = 'pw'
            # polacz
            self.con = pyodbc.connect('DRIVER={};DBQ={};PWD={}'.format(DRV,
                                                                       MDB,
                                                                       PWD))
            self.cur = self.con.cursor()
            self.ok = True
            return True

        elif self.baza[-6:] == 'sqlite':
            self.con = sqlite3.connect(self.baza)
            self.cur = self.con.cursor()
            self.ok = True
            return True

        return False

    def zamknij(self):
        try:
            self.cur.close()
            self.con.close()
            self.con = False
            self.cur = False
        except Exception:
            pass

    def wpisz(self, sql):
        """Metoda dopisuje do bazy podanego sql"""
        try:
            self.cur.execute(sql)
            self.con.commit()
        except Exception:
            return False
        return True

    def wpisz_tab(self, tab):
        """Metoda dopisuje do bazy podaną tabele, uprzednio ja rozpakowujac"""
        try:
            self.cur.execute(*tab)
            self.con.commit()
        except:  # nopep8
            return False
        return True

    def pobierz(self, sql):
        """Metoda pobiera z bazy podanego sql"""
        try:
            return self.cur.execute(sql).fetchall()
        except:  # nopep8
            return False

    def utworz_kopie(self, wpis='', debug=False):
        """Metoda tworzy w katalogu z podana baza kopie bezpieczenstwa ze
        znacznikiem czasu oraz ew podanym wpisem"""
        katalog, plik = os.path.split(self.baza)

        if self.baza[-3:].upper() == 'MDB':
            plikn = plik[:-4] + '_' + wpis + '_' + self.czas + '.mdb'
        else:
            plikn = plik[:-7] + '_' + wpis + '_' + self.czas + '.sqlite'

        copyfile(self.baza, os.path.join(katalog, plikn))

        # debug
        if debug:
            self.baza = os.path.join(katalog, plikn)

        self.zamknij()
        self.polacz()

    def isNone(self, a):
        if a in [None, 'NULL', '', ]:
            return ''
        elif isinstance(a, QVariant):
            if a.isNull():
                return ''
            else:
                return str(a)
        else:
            return a

    def uzytki(self):
        # kwer1
        sql = '''
        SELECT
                  F_PARCEL.COUNTY_CD
                , F_PARCEL.DISTRICT_CD
                , F_PARCEL.MUNICIPALITY_CD
                , F_PARCEL.COMMUNITY_CD
                , F_PARCEL.REG_SHEET_NR2
                , F_PARCEL.PARCEL_NR
                , F_PARCEL.PARCEL_INT_NUM
                , F_PARCEL.PARCEL_AREA
                , F_PARCEL_LAND_USE.SHAPE_NR
                , F_PARCEL_LAND_USE.AREA_USE_CD
        '''
        if self.baza[-6:] == 'sqlite':
            sql += ''', UPPER(F_PARCEL_LAND_USE.SOIL_QUALITY_CD) '''
        else:
            sql += ''', UCASE(F_PARCEL_LAND_USE.SOIL_QUALITY_CD) '''

        sql += '''
                , F_PARCEL_LAND_USE.LAND_USE_AREA
        '''
        if self.baza[-6:] == 'sqlite':
            sql += '''
                , F_PARCEL.COUNTY_CD ||
                F_PARCEL.DISTRICT_CD ||
                F_PARCEL.MUNICIPALITY_CD ||
                F_PARCEL.COMMUNITY_CD ||
                '.' || coalesce(F_PARCEL.REG_SHEET_NR2, '') ||
                CASE WHEN
                coalesce(F_PARCEL.REG_SHEET_NR2, '')  = ''
                then ''
                ELSE '.'
                END  ||
                F_PARCEL.PARCEL_NR AS Wyr1 '''
        else:
            sql += '''
            , [COUNTY_CD] &
            [DISTRICT_CD] &
            [MUNICIPALITY_CD] &
            [COMMUNITY_CD] & \'.\' &
            [REG_SHEET_NR2] &
            IIF (ISNULL(F_PARCEL.REG_SHEET_NR2),\'\', \'.\') &
            [PARCEL_NR] AS Wyr1'''

        sql += '''
        FROM
                  F_PARCEL
                  INNER JOIN
                    F_PARCEL_LAND_USE
                  ON
                    F_PARCEL.PARCEL_INT_NUM = F_PARCEL_LAND_USE.PARCEL_INT_NUM
        ;
        '''
        return self.cur.execute(sql).fetchall()

    def wlasnosci(self):
        # kwer2
        sql = '''
        SELECT
                  F_PARCEL_LAND_USE.PARCEL_INT_NUM
                , V_ADDRESS.name_1
                , V_ADDRESS.addr_grp_fl
                , F_PARCEL.COUNTY_CD
                , F_PARCEL.DISTRICT_CD
                , F_PARCEL.MUNICIPALITY_CD
                , F_PARCEL.COMMUNITY_CD
                , F_PARCEL.REG_SHEET_NR2
                , F_PARCEL.PARCEL_NR
        FROM
                  F_PARCEL
                  INNER JOIN
                    ((V_ADDRESS
                    INNER JOIN
                        V_PARCEL_PARTICIPATION
                    ON
                        V_ADDRESS.ADDR_NR = V_PARCEL_PARTICIPATION.addr_nr)
                    INNER JOIN
                        F_PARCEL_LAND_USE
                    ON
                        V_PARCEL_PARTICIPATION.parcel_int_num =
                        F_PARCEL_LAND_USE.PARCEL_INT_NUM)
                  ON
                    (
                        V_PARCEL_PARTICIPATION.parcel_int_num =
                        F_PARCEL.PARCEL_INT_NUM
                    )
                    AND
                    (
                        F_PARCEL.PARCEL_INT_NUM =
                        F_PARCEL_LAND_USE.PARCEL_INT_NUM
                    )
        GROUP BY
                  F_PARCEL_LAND_USE.PARCEL_INT_NUM
                , V_ADDRESS.name_1
                , V_ADDRESS.addr_grp_fl
                , F_PARCEL_LAND_USE.AREA_USE_CD
                , F_PARCEL.COUNTY_CD
                , F_PARCEL.DISTRICT_CD
                , F_PARCEL.MUNICIPALITY_CD
                , F_PARCEL.COMMUNITY_CD
                , F_PARCEL.REG_SHEET_NR2
                , F_PARCEL.PARCEL_NR
                ;
        '''
        return self.cur.execute(sql).fetchall()

    def dopisane_fo(self):
        """Metoda sprawdza czy w bazie są wpisane jakiekolwiek formy ochrony,
           jeżeli tak, zwraca True"""

        sql = 'select count(*) from F_SET;'
        ile_wydz = self.cur.execute(sql).fetchall()

        sql = 'select count(*) from F_LAND_PROTECT;'
        ile_obsz = self.cur.execute(sql).fetchall()

        if ile_wydz[0][0] == 0 and ile_obsz[0][0] == 0:
            return False
        return True

    def pobierz_sl_fo(self):
        """Metoda pobiera słownik form ochrony z bazy i zwraca je w postaci
        słownika typ formy: id"""

        sql = '''select
                    PROTEC_AREA_CD,
                    PROTEC_AREA_NR
                from
                    F_PROT_AREA_DIC
                ;
                '''
        pob = self.cur.execute(sql).fetchall()
        if len(pob) > 0:
            return {x[0]: x[1] for x in pob}
        return False

    def pobierz_wydzielenia(self):
        """Metoda pobiera z bazy wsystkie wpisane wydzielenia wraz z
        odpowiadającymi im arodes_int_num'ami i zwraca je w postaci slownika"""

        sql = '''select
                    ADRESS_FOREST,
                    ARODES_INT_NUM
                from
                    F_ARODES
                where
                    ARODES_TYP_CD = 'WYDZIEL'
                ;
                '''
        wydz = self.cur.execute(sql).fetchall()
        if len(wydz) > 0:
            return {x[0]: x[1] for x in wydz}
        return False

    def pobierz_do_mapy(self):
        """ Metoda pobiera z bazy tabele na podstawie ktorej generowane beda
        odpowiednie kody i opisy na mapach"""

        sql = """
        SELECT
        rodz_pow.ADRESS_FOREST,
        rodz_pow.AREA_TYPE_CD,
        rodz_pow.SITE_TYPE_CD,
        rodz_pow.SUB_AREA,
        do_lacz.PART_CD,
        """

        if self.baza[-3:] == 'mdb':
            sql += """
        do_lacz.SPECIES_CD & hal.gtd AS SPECIES_CD,
            """
        elif self.baza[-6:] == 'sqlite':
            sql += """
        IFNULL(do_lacz.SPECIES_CD, '') || IFNULL(hal.gtd, '') AS SPECIES_CD,
            """

        sql += \
            """
        do_lacz.SPECIES_AGE,
        do_lacz.STANDDENSITY_INDEX,
        do_lacz.STOREY_CD,
        do_lacz.STAND_STRUCT_CD

        FROM

        (
        (SELECT
        F_ARODES.ADRESS_FOREST,
        F_SUBAREA.SUB_AREA,
        F_SUBAREA.AREA_TYPE_CD,
        F_SUBAREA.SITE_TYPE_CD
        FROM
        F_ARODES
        INNER JOIN F_SUBAREA
        ON
        F_ARODES.ARODES_INT_NUM = F_SUBAREA.ARODES_INT_NUM) as rodz_pow

        LEFT JOIN

        (SELECT
        F_ARODES.ADRESS_FOREST,
        F_STOREY_SPECIES.SPECIES_RANK_ORDER,
        F_STOREY_SPECIES.PART_CD,
        F_STOREY_SPECIES.SPECIES_CD,
        F_STOREY_SPECIES.SPECIES_AGE,
        F_STOREY_SPECIES.SITE_CLASS_CD,
        F_STOREY_SPECIES.STOREY_CD,
        F_SUBAREA.AREA_TYPE_CD,
        F_SUBAREA.STAND_STRUCT_CD,
        F_AROD_STOREY.STANDDENSITY_INDEX
        FROM
        (F_ARODES
        INNER JOIN
        (F_STOREY_SPECIES
        INNER JOIN
        F_SUBAREA
        ON F_STOREY_SPECIES.ARODES_INT_NUM = F_SUBAREA.ARODES_INT_NUM)
        ON F_ARODES.ARODES_INT_NUM = F_SUBAREA.ARODES_INT_NUM)
        INNER JOIN
        F_AROD_STOREY
        ON F_SUBAREA.ARODES_INT_NUM = F_AROD_STOREY.ARODES_INT_NUM

        WHERE
        (((F_STOREY_SPECIES.SPECIES_RANK_ORDER)=1) AND
        ((F_STOREY_SPECIES.STOREY_CD)=\'DRZEW\' Or
        (F_STOREY_SPECIES.STOREY_CD)=\'IP\') AND
        ((F_AROD_STOREY.STOREY_CD)=\'DRZEW\' Or
        (F_AROD_STOREY.STOREY_CD)=\'IP\'))
        ) as do_lacz

        ON

        rodz_pow.ADRESS_FOREST = do_lacz.ADRESS_FOREST)

        LEFT JOIN

        (SELECT
        wyb.adr_first,
        wyb.kol_max,
        sel.gtd

        FROM

        (SELECT
        F_ARODES.ADRESS_FOREST as adr,
        F_AROD_GOAL.GOAL_RANK_ORDER as kol,
        F_AROD_GOAL.SPECIES_CD as gtd

        FROM
        (F_ARODES INNER JOIN F_SUBAREA
        ON
        F_ARODES.ARODES_INT_NUM=F_SUBAREA.ARODES_INT_NUM)
        LEFT JOIN F_AROD_GOAL
        ON F_AROD_GOAL.ARODES_INT_NUM=F_ARODES.ARODES_INT_NUM

        GROUP BY
        F_ARODES.ADRESS_FOREST,
        F_SUBAREA.SUB_AREA,
        F_SUBAREA.AREA_TYPE_CD,
        F_AROD_GOAL.GOAL_RANK_ORDER,
        F_AROD_GOAL.SPECIES_CD

        HAVING
        (((F_SUBAREA.AREA_TYPE_CD)=\'HAL\'))
        ) as sel

        inner JOIN

        (SELECT
        """

        if self.baza[-3:] == 'mdb':
            sql += """
            FIRST(F_ARODES.ADRESS_FOREST) as adr_first,
            """
        elif self.baza[-6:] == 'sqlite':
            sql += """
            F_ARODES.ADRESS_FOREST as adr_first,
            """

        sql += \
            """
        MAX(F_AROD_GOAL.GOAL_RANK_ORDER) as kol_max

        FROM
        (F_ARODES
        INNER JOIN
        F_SUBAREA
        ON F_ARODES.ARODES_INT_NUM=F_SUBAREA.ARODES_INT_NUM)
        LEFT JOIN F_AROD_GOAL
        ON F_AROD_GOAL.ARODES_INT_NUM=F_ARODES.ARODES_INT_NUM

        GROUP BY
        F_ARODES.ADRESS_FOREST,
        F_SUBAREA.AREA_TYPE_CD

        HAVING
        (((F_SUBAREA.AREA_TYPE_CD)=\'HAL\'))

        ) as wyb

        ON

        (sel.adr = wyb.adr_first and sel.kol >= wyb.kol_max)

        ) as hal

        ON

        rodz_pow.ADRESS_FOREST = hal.adr_first
        ;

        """
        return self.cur.execute(sql).fetchall()

    def pobierz_zab_do_mapy(self):
        sql = """
            SELECT
                F_ARODES.ADRESS_FOREST,
                F_AROD_CUE.MEASURE_CD,
                F_AROD_CUE.CUTTING_AREA
            FROM
                F_AROD_CUE INNER JOIN F_ARODES
                ON F_AROD_CUE.ARODES_INT_NUM=F_ARODES.ARODES_INT_NUM
                ORDER BY F_ARODES.ADRESS_FOREST, F_AROD_CUE.CUE_RANK_ORDER;
        """
        return self.cur.execute(sql).fetchall()

    def pobierz_pnsw(self):
        """ Metoda pobiera tabele z pnsw """
        sql = """
            SELECT
                ARODES_INT_NUM,
                AROD_SPAREA_ORDER,
                SPECIAL_AREA_CD,
                LOCATION_CD
            FROM
                F_AROD_SPEC_AREA;
        """
        return self.cur.execute(sql).fetchall()

    def pobierz_naglowek(self):
        """Metoda pobiera dane naglowkowe, nazwy i kody administracyjne, dla
        wpisanych obrebow w bazie"""

        sql = """
            SELECT
                F_COUNTY.COUNTY_NAME,
                F_DISTRICT.DISTRICT_NAME,
                F_MUNICIPALITY.MUNICIPALITY_NAME,
                F_COMMUNITY.COMMUNITY_NAME,
                F_COMMUNITY.MUNICIPALITY_CD,
                F_COMMUNITY.COMMUNITY_CD
            FROM
                F_COUNTY INNER JOIN
                ((F_DISTRICT INNER JOIN F_MUNICIPALITY
                ON (F_DISTRICT.DISTRICT_CD = F_MUNICIPALITY.DISTRICT_CD)
                AND (F_DISTRICT.COUNTY_CD = F_MUNICIPALITY.COUNTY_CD))
                INNER JOIN F_COMMUNITY ON
                (F_MUNICIPALITY.MUNICIPALITY_CD = F_COMMUNITY.MUNICIPALITY_CD)
                AND (F_MUNICIPALITY.DISTRICT_CD = F_COMMUNITY.DISTRICT_CD)
                AND
                (F_MUNICIPALITY.COUNTY_CD = F_COMMUNITY.COUNTY_CD))
                ON F_COUNTY.COUNTY_CD = F_DISTRICT.COUNTY_CD
                ;
            """
        return self.cur.execute(sql).fetchall()

    def pobierz_pow_oprac(self):
        """Metoda pobiera powierzchnie opracowania z rozbiciem dla kazdego
        obrebu ewid"""

        if self.baza[-3:] == 'mdb':
            sql = """
            select * from [TABELA 1 POW z pkt 1 , 3 i 4_POW_LS_WPISANE];"""
            return self.cur.execute(sql).fetchall()

        elif self.baza[-6:] == 'sqlite':
            sql = "select * from POW_suma;"
            tab = self.cur.execute(sql).fetchall()
            return [list(t) + [sum(t[2:4])-t[4]]
                    for t in tab]

        return False

    def pobierz_daty_waznosci(self):
        """Metoda pobiera datę ostatniej modyfikacji geodezji oraz okres
        obowiązywania planu z tabeli F_PARAMETER"""

        sql = """
            select
                DbValidityYearFrom,
                DbValidityYearTo,
                EWID_STATE
            from F_PARAMETER;
        """
        return self.cur.execute(sql).fetchall()

    def pobierz_wydz_na_innych_uz(self):
        """Metoda pobiera z bazy adresy les z wydzielen które nie są D-STANami
        a występują na użytkacj innych niż Ls.
        Zwracana tabela ma kształt :
            adr_les,
            area_type_cd,
            land_use_cd,

        """

        sql = """
        SELECT
            F_ARODES.ADRESS_FOREST,
            F_SUBAREA.AREA_TYPE_CD,
            F_PARCEL_LAND_USE.AREA_USE_CD,
            F_PARCEL_LAND_USE.LAND_USE_AREA
        FROM F_PARCEL_LAND_USE
        INNER JOIN ((F_ARODES
                    INNER JOIN F_SUBAREA ON
                        F_ARODES.ARODES_INT_NUM = F_SUBAREA.ARODES_INT_NUM)
                    INNER JOIN F_AROD_LAND_USE ON
                    F_ARODES.ARODES_INT_NUM = F_AROD_LAND_USE.ARODES_INT_NUM)
            ON (F_PARCEL_LAND_USE.SHAPE_NR = F_AROD_LAND_USE.SHAPE_NR)
        AND (F_PARCEL_LAND_USE.PARCEL_INT_NUM = F_AROD_LAND_USE.PARCEL_INT_NUM)
        WHERE (((F_PARCEL_LAND_USE.AREA_USE_CD) NOT LIKE \'Ls\')
            AND ((F_SUBAREA.AREA_TYPE_CD) NOT LIKE \'D-STAN\'));
        """

        return self.cur.execute(sql).fetchall()

    def pobierz_rozliczenie_wydz(self):
        """Metoda pobiera zawartość tabeli F_ARDOD_LAND_USE i zwraca tabele
        """
        sql = """
            select
                arodes_int_num,
                parcel_int_num,
                shape_nr,
                arod_land_use_area
            from F_AROD_LAND_USE;
        """
        return self.cur.execute(sql).fetchall()

    def wpisz_rozliczenie_wydz(self, tab):
        """ Metoda wpisuje do tabeli F_AROD_LAND_USE  podany wiersz i zwraca
        True/False w zależności od powodzenia"""

        try:
            self.cur.execute(
                "insert into F_AROD_LAND_USE " +
                "(PARCEL_INT_NUM, SHAPE_NR, "
                "ARODES_INT_NUM, "
                "AROD_LAND_USE_AREA, "
                "LARGE_TIMBER_VALUE) values(" +
                str(tab[0]) + ", " +
                str(tab[1]) + ", " +
                str(tab[2]) + ", " +
                str(tab[3]) + ", 0);"
            )
            self.con.commit()
            return True
        except:  # nopep8
            return False

    def pobierz_do_zab(self, aid):
        """Metoda pobiera z bazy z rozynych tabel niezbedne dane do obliczenia
        zabiegów dla konkretnego wydzielenia.
        """
        # sprawdz czy posadany aid(arodes_int_num) jest w bazie, jezeli nie
        # zwroc false
        if aid not in self.pobierz_wydzielenia().values():
            return False

        # wyciagamy dane na temat podrostu i nalotu wraz z udzialem
        sql = """
        SELECT
            fs.arodes_int_num,
            fs.storey_cd,
            fs.standdensity_index,
            fs.storey_rank_order,
            fs.density_cd
        FROM
            f_arod_storey AS fs
        WHERE
            fs.arodes_int_num = """ + str(aid) + ';'

        podNal_kwer = self.cur.execute(sql).fetchall()

        # dane dotyczace rebni wpisanych przez taksatorow
        SQL = """
        select
            f.arodes_int_num,
            f.measure_cd,
            f.cutting_area,
            f.cue_rank_order,
            f.proc_area,
            f.large_timber_perc,
            f.large_timber_value
        from
            f_arod_cue as f
        where
            f.arodes_int_num = """ + str(aid) + ';'
        reb_kwer = self.cur.execute(SQL).fetchall()

        SQL = """
        select
            f.ARODES_INT_NUM,
            f.SPECIES_CD,
            f.SPECIES_RANK_ORDER,
            f.SPECIES_AGE,
            f.BHD,
            f.VOLUME_TEMP
        FROM
            F_STOREY_SPECIES AS f
        WHERE
            f.STOREY_CD = 'DRZEW' AND f.SPECIES_RANK_ORDER = 1 AND
            f.ARODES_INT_NUM = """ + str(aid) + ';'
        gatGl_kwer = self.cur.execute(SQL).fetchall()

        # dane dotyczace przest i plaz
        sql = '''
        select
            f.ARODES_INT_NUM,
            sum(f.VOLUME_TEMP),'''
        if self.baza[-6:] == 'sqlite':
            sql += '''f.storey_cd '''
        else:
            sql += '''first(f.storey_cd) '''

        sql += '''
        FROM
            F_STOREY_SPECIES AS f
        WHERE
            f.STOREY_CD in ('PŁAZ', 'PRZES') and
            f.ARODES_INT_NUM = ''' + str(aid) + '''
        GROUP BY
            f.ARODES_INT_NUM;'''
        pp_kwer = self.cur.execute(sql).fetchall()

        # szczegolowe dane o wydzieleniach
        SQL = """
        select
            f.ARODES_INT_NUM,
            f.AREA_TYPE_CD,
            f.SITE_TYPE_CD,
            f.SUB_AREA,
            f.SUBAREA_INFO,
            f.STAND_STRUCT_CD,
            f.DAMAGE_DEGREE_CD,
            f.SUBAREA_INFO
        FROM
            F_SUBAREA AS f
        WHERE
            f.ARODES_INT_NUM = """ + str(aid) + ';'
        wydzSzczeg_kwer = self.cur.execute(SQL).fetchall()

        # dane o przestojach
        SQL = """
        select
            f.ARODES_INT_NUM,
            f.SPECIES_CD,
            f.PART_CD,
            f.SPECIES_AGE,
            f.BHD,
            f.VOLUME,
            f.storey_cd
        FROM
            F_STOREY_SPECIES AS f
        WHERE
            f.STOREY_CD = 'PRZES' AND
            f.ARODES_INT_NUM = """ + str(aid) + ';'
        przest_kwer = self.cur.execute(SQL).fetchall()

        # pobierz dane dotyczace luk
        if self.baza[-6:] == 'sqlite':
            sql = """
            SELECT
                f.arodes_int_num,
                f.special_area_cd,
                """
        else:
            sql = """
            SELECT
                first(f.arodes_int_num),
                first(f.special_area_cd),
                """

        sql += """
            sum(f.special_area)
        from
            f_arod_spec_area as f
        where
            f.special_area_cd = 'LUKA' and
            f.ARODES_INT_NUM = """ + str(aid) + """
        group by
            f.special_area_cd ;
        """
        luki_kwer = self.cur.execute(sql).fetchall()

        # dzialki na ktorych lezy wydzielenie
        sql = 'select count(parcel_int_num) from F_AROD_LAND_USE where ' + \
            'arodes_int_num = ' + str(aid) + ';'
        wydz_dzkat = self.cur.execute(sql).fetchall()

        tab = [
            podNal_kwer,
            reb_kwer,
            gatGl_kwer,
            pp_kwer,
            wydzSzczeg_kwer,
            przest_kwer,
            luki_kwer,
            wydz_dzkat,
        ]

        return tab

    def anonimizuj_vaddress(self):
        sql = 'update v_address set name_1=\'NAZWISKO\', name_2=\'IMIE\', ' + \
            'place=\'MIEJSCOWOSC\', street=\'ULICA d:0 l:0\', ' +\
            'post_cd=\'00-000\', post=\'POCZTA\', stat_info=\'00000000000\'' +\
            ', tax_nr=\'000-000-00-00\';'

        self.cur.execute(sql)
        self.con.commit()

    def pobierz_wiek_reb(self):
        # dane o wieku rebnosci pobranych z bazy
        SQL = """
        select
            f.SPECIES_CD,
            f.AVG_CUT_AGE
        FROM
            F_TREE_SPECIES AS f;
        """
        wr = {x[0]: x[1] for x in self.cur.execute(SQL).fetchall()}
        return wr
