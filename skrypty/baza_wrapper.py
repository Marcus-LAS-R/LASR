import os
import glob
import platform
import pyodbc
import sqlite3
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtCore import QVariant
from qgis.core import Qgis
from datetime import datetime
from shutil import copyfile
from collections import Counter


def znajdz_baze_do_wydz(iface, wydzlyr=False, poz=2, wskaz=False):
    if wydzlyr is not False:
        wydz = wydzlyr
    else:
        wydz = iface.activeLayer()

    bTemp = []
    kat = ""

    # ma byc wskazana baza przez uzytkownika
    if wskaz:
        bTemp = [
            QFileDialog().getOpenFileName(
                iface.mainWindow(),
                "Wskaż baze Taksatora",
                kat,
                "Access MDB (*.mdb);;SQLite (*.sqlite)",
            )[0]
        ]
        print(bTemp)

        if len(bTemp) == 1 and bTemp[0] != "":
            baza = Baza(bTemp[0])
            if baza.polacz():
                baza.zamknij()
                return os.path.abspath(bTemp[0])
        else:
            iface.messageBar().pushMessage(
                "Baza", "Nie udało się pobrać danych z bazy", Qgis.Critical, 10
            )
            return False

    if wydz is not None:
        wydz_sc = wydz.dataProvider().dataSourceUri().split("|")[0]
        kat = os.path.dirname(wydz_sc)

        if wydz.name() == "ODDZ" or poz == 1:
            poziom = ".."
        else:
            poziom = "../.."

        try:
            if platform.system()[:3] == "Win":
                bTemp = glob.glob(os.path.join(kat, poziom, "*.mdb"))
            else:
                bTemp = glob.glob(os.path.join(kat, poziom, "*.sqlite"))
        except:  # nopep8
            iface.messageBar().pushMessage(
                "BŁĄD", "Nie udało się odnaleźć bazy!", Qgis.Critical, 10
            )
            return False

    if len(bTemp) != 1:
        bTemp = [
            QFileDialog().getOpenFileName(
                iface.mainWindow(),
                "Wskaż baze Taksatora",
                kat,
                "Access MDB (*.mdb);;SQLite (*.sqlite)",
            )[0]
        ]

    if len(bTemp) == 1:
        baza = Baza(bTemp[0])
        if baza.polacz():
            baza.zamknij()
            return os.path.abspath(bTemp[0])
        else:
            iface.messageBar().pushMessage(
                "Baza", "Nie udało się pobrać danych z bazy", Qgis.Critical, 10
            )
    else:
        iface.messageBar().pushMessage(
            "Baza", "Nie udało się pobrać danych z bazy", Qgis.Critical, 10
        )
    return False


class Baza(object):
    def __init__(self, b):
        # otworz podana baze danych
        self.con = False
        self.cur = False
        self.ok = False
        self.baza = b  # sciezka do bazy, bez normalizacji sciezki...

        self.czas = datetime.now().isoformat().replace(":", "")[:-7]

        # sprawdź czy baza jest poprawna i mozna sie do niej podlaczyc
        # self.polacz(b)

    def polacz(self):
        """Metoda sprawdzajaca i laczaca sie z bazą"""

        # jezeli juz jestesmy polaczeni, nic ni rob
        if self.con and self.cur:
            return True

        if self.baza[-3:] == "mdb":
            MDB = self.baza
            DRV = "{Microsoft Access Driver (*.mdb, *.accdb)}"
            PWD = "pw"
            # polacz
            self.con = pyodbc.connect("DRIVER={};DBQ={};PWD={}".format(DRV, MDB, PWD))
            self.cur = self.con.cursor()
            self.ok = True
            return True

        elif self.baza[-6:] == "sqlite":
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

    def utworz_kopie(self, wpis="", debug=False):
        """Metoda tworzy w katalogu z podana baza kopie bezpieczenstwa ze
        znacznikiem czasu oraz ew podanym wpisem"""
        katalog, plik = os.path.split(self.baza)

        if self.baza[-3:].upper() == "MDB":
            plikn = plik[:-4] + "_" + wpis + "_" + self.czas + ".mdb"
        else:
            plikn = plik[:-7] + "_" + wpis + "_" + self.czas + ".sqlite"

        copyfile(self.baza, os.path.join(katalog, plikn))

        # debug
        if debug:
            self.baza = os.path.join(katalog, plikn)

        self.zamknij()
        self.polacz()

    def isNone(self, a):
        if a in [
            None,
            "NULL",
            "",
        ]:
            return ""
        elif isinstance(a, QVariant):
            if a.isNull():
                return ""
            else:
                return str(a)
        else:
            return a

    def uzytki(self):
        # kwer1
        sql = """
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
        """
        if self.baza[-6:] == "sqlite":
            sql += """, UPPER(F_PARCEL_LAND_USE.SOIL_QUALITY_CD) """
        else:
            sql += """, UCASE(F_PARCEL_LAND_USE.SOIL_QUALITY_CD) """

        sql += """
                , F_PARCEL_LAND_USE.LAND_USE_AREA
        """
        if self.baza[-6:] == "sqlite":
            sql += """
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
                F_PARCEL.PARCEL_NR AS Wyr1 """
        else:
            sql += """
            , [COUNTY_CD] &
            [DISTRICT_CD] &
            [MUNICIPALITY_CD] &
            [COMMUNITY_CD] & \'.\' &
            [REG_SHEET_NR2] &
            IIF (ISNULL(F_PARCEL.REG_SHEET_NR2),\'\', \'.\') &
            [PARCEL_NR] AS Wyr1"""

        sql += """
        FROM
                  F_PARCEL
                  INNER JOIN
                    F_PARCEL_LAND_USE
                  ON
                    F_PARCEL.PARCEL_INT_NUM = F_PARCEL_LAND_USE.PARCEL_INT_NUM
        ;
        """
        return self.cur.execute(sql).fetchall()

    def wlasnosci(self):
        # kwer2
        sql = """
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
        """
        return self.cur.execute(sql).fetchall()

    def dopisane_fo(self):
        """Metoda sprawdza czy w bazie są wpisane jakiekolwiek formy ochrony,
        jeżeli tak, zwraca True"""

        sql = "select count(*) from F_SET;"
        ile_wydz = self.cur.execute(sql).fetchall()

        sql = "select count(*) from F_LAND_PROTECT;"
        ile_obsz = self.cur.execute(sql).fetchall()

        if ile_wydz[0][0] == 0 and ile_obsz[0][0] == 0:
            return False
        return True

    def pobierz_sl_fo(self):
        """Metoda pobiera słownik form ochrony z bazy i zwraca je w postaci
        słownika typ formy: id"""

        sql = """select
                    PROTEC_AREA_CD,
                    PROTEC_AREA_NR
                from
                    F_PROT_AREA_DIC
                ;
                """
        pob = self.cur.execute(sql).fetchall()
        if len(pob) > 0:
            return {x[0]: x[1] for x in pob}
        return False

    def pobierz_wydzielenia(self):
        """Metoda pobiera z bazy wsystkie wpisane wydzielenia wraz z
        odpowiadającymi im arodes_int_num'ami i zwraca je w postaci slownika"""

        sql = """select
                    ADRESS_FOREST,
                    ARODES_INT_NUM
                from
                    F_ARODES
                where
                    ARODES_TYP_CD = 'WYDZIEL'
                ;
                """
        wydz = self.cur.execute(sql).fetchall()
        if len(wydz) > 0:
            return {x[0]: x[1] for x in wydz}
        return False

    def pobierz_do_mapy(self):
        """Metoda pobiera z bazy tabele na podstawie ktorej generowane beda
        odpowiednie kody i opisy na mapach"""

        sql = """
        SELECT
        rodz_pow.ADRESS_FOREST,
        rodz_pow.AREA_TYPE_CD,
        rodz_pow.SITE_TYPE_CD,
        rodz_pow.SUB_AREA,
        do_lacz.PART_CD,
        """

        if self.baza[-3:] == "mdb":
            sql += """
        do_lacz.SPECIES_CD & hal.gtd AS SPECIES_CD,
            """
        elif self.baza[-6:] == "sqlite":
            sql += """
        IFNULL(do_lacz.SPECIES_CD, '') || IFNULL(hal.gtd, '') AS SPECIES_CD,
            """

        sql += """
        do_lacz.SPECIES_AGE,
        do_lacz.STANDDENSITY_INDEX,
        do_lacz.STOREY_CD,
        do_lacz.STAND_STRUCT_CD,
        rodz_pow.veg_cover_cd

        FROM

        (
        (SELECT
        F_ARODES.ADRESS_FOREST,
        F_SUBAREA.SUB_AREA,
        F_SUBAREA.AREA_TYPE_CD,
        F_SUBAREA.SITE_TYPE_CD,
        F_SUBAREA.veg_cover_cd
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

        if self.baza[-3:] == "mdb":
            sql += """
            FIRST(F_ARODES.ADRESS_FOREST) as adr_first,
            """
        elif self.baza[-6:] == "sqlite":
            sql += """
            F_ARODES.ADRESS_FOREST as adr_first,
            """

        sql += """
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
        """Metoda pobiera tabele z pnsw"""
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

        if self.baza[-3:] == "mdb":
            sql = """
            select * from [TABELA 1 POW z pkt 1 , 3 i 4_POW_LS_WPISANE];"""
            return self.cur.execute(sql).fetchall()

        elif self.baza[-6:] == "sqlite":
            sql = "select * from POW_suma;"
            tab = self.cur.execute(sql).fetchall()
            return [list(t) + [sum(t[2:4]) - t[4]] for t in tab]

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
        """Metoda pobiera zawartość tabeli F_ARDOD_LAND_USE i zwraca tabele"""
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
        """Metoda wpisuje do tabeli F_AROD_LAND_USE  podany wiersz i zwraca
        True/False w zależności od powodzenia"""

        try:
            self.cur.execute(
                "insert into F_AROD_LAND_USE " + "(PARCEL_INT_NUM, SHAPE_NR, "
                "ARODES_INT_NUM, "
                "AROD_LAND_USE_AREA, "
                "LARGE_TIMBER_VALUE) values("
                + str(tab[0])
                + ", "
                + str(tab[1])
                + ", "
                + str(tab[2])
                + ", "
                + str(tab[3])
                + ", 0);"
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
        sql = (
            """
        SELECT
            fs.arodes_int_num,
            fs.storey_cd,
            fs.standdensity_index,
            fs.storey_rank_order,
            fs.density_cd
        FROM
            f_arod_storey AS fs
        WHERE
            fs.arodes_int_num = """
            + str(aid)
            + ";"
        )

        podNal_kwer = self.cur.execute(sql).fetchall()

        # dane dotyczace rebni wpisanych przez taksatorow
        SQL = (
            """
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
            f.arodes_int_num = """
            + str(aid)
            + ";"
        )
        reb_kwer = self.cur.execute(SQL).fetchall()

        SQL = (
            """
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
            f.ARODES_INT_NUM = """
            + str(aid)
            + ";"
        )
        gatGl_kwer = self.cur.execute(SQL).fetchall()

        # dane dotyczace przest i plaz
        sql = """
        select
            f.ARODES_INT_NUM,
            sum(f.VOLUME_TEMP),"""
        if self.baza[-6:] == "sqlite":
            sql += """f.storey_cd """
        else:
            sql += """first(f.storey_cd) """

        sql += (
            """
        FROM
            F_STOREY_SPECIES AS f
        WHERE
            f.STOREY_CD in ('PŁAZ', 'PRZES') and
            f.ARODES_INT_NUM = """
            + str(aid)
            + """
        GROUP BY
            f.ARODES_INT_NUM;"""
        )
        pp_kwer = self.cur.execute(sql).fetchall()

        # sprawdzenie gatunków w wydzieleniu
        sql = (
            "select species_cd, site_class_cd, part_cd, species_age, "
            + "bhd, height, volume_temp from F_STOREY_SPECIES "
            + f"where arodes_int_num = {aid} and STOREY_CD in "
            + "('DRZEW', 'IP', 'IIP');"
        )
        gat_opisy = self.cur.execute(sql).fetchall()

        # szczegolowe dane o wydzieleniach
        SQL = (
            """
        select
            f.ARODES_INT_NUM,
            f.AREA_TYPE_CD,
            f.SITE_TYPE_CD,
            f.SUB_AREA,
            f.SUBAREA_INFO,
            f.STAND_STRUCT_CD,
            f.DAMAGE_DEGREE_CD,
            f.SUBAREA_INFO,
            f.VEG_COVER_CD
        FROM
            F_SUBAREA AS f
        WHERE
            f.ARODES_INT_NUM = """
            + str(aid)
            + ";"
        )
        wydzSzczeg_kwer = self.cur.execute(SQL).fetchall()

        # dane o przestojach
        SQL = (
            """
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
            f.ARODES_INT_NUM = """
            + str(aid)
            + ";"
        )
        przest_kwer = self.cur.execute(SQL).fetchall()

        # pobierz dane dotyczace luk
        if self.baza[-6:] == "sqlite":
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

        sql += (
            """
            sum(f.special_area)
        from
            f_arod_spec_area as f
        where
            f.special_area_cd = 'LUKA' and
            f.ARODES_INT_NUM = """
            + str(aid)
            + """
        group by
            f.special_area_cd ;
        """
        )
        luki_kwer = self.cur.execute(sql).fetchall()

        # dzialki na ktorych lezy wydzielenie
        sql = (
            "select count(parcel_int_num) from F_AROD_LAND_USE where "
            + f"arodes_int_num = {aid};"
        )
        wydz_dzkat = self.cur.execute(sql).fetchall()

        sql = (
            "select count(goal_type_fl) from f_arod_goal where "
            + f"arodes_int_num={aid}"
        )
        cel_hod = self.cur.execute(sql).fetchall()

        tab = [
            podNal_kwer,
            reb_kwer,
            gatGl_kwer,
            pp_kwer,
            wydzSzczeg_kwer,
            przest_kwer,
            luki_kwer,
            wydz_dzkat,
            cel_hod,
            gat_opisy,
        ]

        return tab

    def anonimizuj_vaddress(self):
        sql = (
            "update v_address set name_1='NAZWISKO', name_2='IMIE', "
            + "place='MIEJSCOWOSC', street='ULICA d:0 l:0', "
            + "post_cd='00-000', post='POCZTA', stat_info='00000000000'"
            + ", tax_nr='000-000-00-00';"
        )

        self.cur.execute(sql)
        self.con.commit()

    def usun_kwerendy(self):
        pass
        # nietestowane - trzeba zrobic liste wszystkich nazw kwerend do
        # usuniecia

        # cxn = pyodbc.connect('DRIVER={Microsoft Access Driver (*.mdb,
        # *.accdb)};DBQ=C:\\__tmp\\dropTest.accdb;')
        # cursor = cxn.cursor()
        # cursor2 = cxn.cursor()
        # for table in cursor.tables():
        # if table.table_type == "TABLE":
        # drop = "DROP TABLE [{0}]".format(table.table_name)
        # print drop
        # cursor2.execute(drop)
        # cxn.commit()
        # cxn.close()

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

    def kapitaliki_w_klasach(self):
        """Metoda uaktualnia użytki w klasach IVa, IVb, VIz do dużych liter,
        należy uruchomić przy przygotowaniu Lsów
        """
        tab = [
            ["IVb", "IVB"],
            ["IVa", "IVA"],
            ["VIz", "VIZ"],
        ]

        for tt in tab:
            sql = (
                "update f_parcel_land_use set soil_quality_cd='"
                + tt[1]
                + "' where soil_quality_cd='"
                + tt[0]
                + "';"
            )

            self.cur.execute(sql)
            self.con.commit()

    def pobierz_wyk_wlasc(self):
        """Zwraca slownik wszystkich wlascicieli wpisanych do planu w postaci:
        sl = {addr_nr: {'opis': { tutaj nazwy kolumn z v_address},
                       'grej':  [lista grej dla tego wlasciciela],
                       'udzial': {gggoooo.grej: '12/212',},
                       }}
        sl_grej = {
        gggoooo: {'grej': {'pint': [parcel_int_num, …],
                           'wl': [addr, …],
                           }
                 }
        }
        sl_pint = {pint: 'gggoooo.ark.dznr', 'gggoooo.dznr', …}

        """

        sl = {}
        sl_grej = {}
        sl_pint = {}

        sql = """
        SELECT distinct V_ADDRESS.ADDR_NR,
            V_ADDRESS.NAME_1,
            V_ADDRESS.NAME_2,
            V_ADDRESS.PLACE,
            V_ADDRESS.STREET,
            V_ADDRESS.POST,
            V_ADDRESS.post_cd,
            V_ADDRESS.addr_grp_fl,
            v_parcel_participation.second_addr_nr
        FROM
            (F_AROD_LAND_USE
            INNER JOIN F_PARCEL ON
                F_AROD_LAND_USE.PARCEL_INT_NUM = F_PARCEL.PARCEL_INT_NUM)
        INNER JOIN
            (V_ADDRESS
            INNER JOIN
                V_PARCEL_PARTICIPATION ON
                V_ADDRESS.ADDR_NR = V_PARCEL_PARTICIPATION.addr_nr)
        ON F_PARCEL.PARCEL_INT_NUM = V_PARCEL_PARTICIPATION.parcel_int_num;
            """

        dw = self.cur.execute(sql).fetchall()

        sl = {
            x[0]: {
                "opis": {
                    "nazwisko": x[1] if x[1] is not None else "",
                    "imie": x[2] if x[2] is not None else "",
                    "miejscowosc": x[3] if x[3] is not None else "",
                    "ulica": x[4] if x[4] is not None else "",
                    "poczta": x[5] if x[5] is not None else "",
                    "kod": x[6] if x[6] is not None else "",
                    "wspl": x[8] if x[8] is not None else "",
                },
                "grej": [],
                "udzial": {},
            }
            for x in dw
        }

        sql = """
        SELECT V_ADDRESS.ADDR_NR,
        F_PARCEL.MUNICIPALITY_CD,
        F_PARCEL.COMMUNITY_CD,
        F_PARCEL.REG_SHEET_NR2,
        F_PARCEL.PARCEL_NR,
        F_PARCEL.LAND_REGISTER_NR,
        F_PARCEL.PARCEL_INT_NUM,
        v_parcel_participation.part_numerator,
        v_parcel_participation.part_denominator
        FROM
            ((V_PARCEL_PARTICIPATION
                    INNER JOIN V_ADDRESS ON
                    V_PARCEL_PARTICIPATION.addr_nr = V_ADDRESS.ADDR_NR)
            INNER JOIN F_PARCEL ON
                V_PARCEL_PARTICIPATION.parcel_int_num=F_PARCEL.PARCEL_INT_NUM)
            INNER JOIN F_AROD_LAND_USE ON
                F_PARCEL.PARCEL_INT_NUM = F_AROD_LAND_USE.PARCEL_INT_NUM;
        """
        dd = self.cur.execute(sql).fetchall()

        for di in dd:
            if di[0] not in sl:
                continue

            # dodaj grej do slownika wlasc
            if di[1] + di[2] + "." + di[5] not in sl[di[0]]["grej"]:
                sl[di[0]]["grej"].append(di[1] + di[2] + "." + di[5])
                sl[di[0]]["udzial"][di[1] + di[2] + "." + di[5]] = (
                    str(int(di[7])) + "/" + str(int(di[8]))
                )

            # sprawdz czy mamy strukture w sl_grej dla obrebu
            if di[1] + di[2] not in sl_grej:
                sl_grej[di[1] + di[2]] = {}

            # sprawdz czy jest struktura dla grej
            if di[5] not in sl_grej[di[1] + di[2]]:
                sl_grej[di[1] + di[2]][di[5]] = {"dz": [di[6]], "wl": [di[0]]}
            else:
                if di[6] not in sl_grej[di[1] + di[2]][di[5]]["dz"]:
                    sl_grej[di[1] + di[2]][di[5]]["dz"].append(di[6])
                if di[0] not in sl_grej[di[1] + di[2]][di[5]]["wl"]:
                    sl_grej[di[1] + di[2]][di[5]]["wl"].append(di[0])

            if di[6] not in sl_pint:
                adr = di[1] + di[2]
                adr += "." if di[3] is None else "." + di[3] + "."
                adr += di[4]
                sl_pint[di[6]] = adr

        return sl, sl_grej, sl_pint

    def pobierz_obr_w_gm(self):
        """Zwraca slowniki
        sl = {'obreb nazwa': 'nazwa gminy'}
        {'GGGOOOO': 'nazwa obrebu'}
        """
        sql = """
        SELECT F_COMMUNITY.COMMUNITY_NAME,
            F_MUNICIPALITY.MUNICIPALITY_NAME,
            F_MUNICIPALITY.MUNICIPALITY_CD,
            F_COMMUNITY.COMMUNITY_CD
        FROM F_MUNICIPALITY
        INNER JOIN
        F_COMMUNITY ON
        (F_MUNICIPALITY.MUNICIPALITY_CD = F_COMMUNITY.MUNICIPALITY_CD)
        AND (F_MUNICIPALITY.DISTRICT_CD = F_COMMUNITY.DISTRICT_CD)
        AND (F_MUNICIPALITY.COUNTY_CD = F_COMMUNITY.COUNTY_CD);
        """

        obr = self.cur.execute(sql).fetchall()
        return {x[0].upper(): x[1].upper() for x in obr}, {
            x[2] + x[3]: x[0] for x in obr
        }

    def pobierz_wyk_zalec(self):
        """Pobiera zalecenia zabiegow dla wszystkich wydzielen
        zwraca slownik w postaci
        {aint: {'rpow': 'DSTAN',
                'gat': 'xx',
                'wiek': 22,
                'bhd': 'x',
                'pow': 2.22, # (powierzchnia całego wydzielenia)
                'miazsz': 333, # (dla calego wydzielenia)
                'zab': [['zab', %pow, %timber, brutto, netto], …]
                        # (dla calego wydz)
                }
        """

        sql = """
        SELECT
            f_subarea.ARODES_INT_NUM,
            F_SUBAREA.AREA_TYPE_CD,
            F_SUBAREA.SUB_AREA,
            g.SPECIES_CD,
            g.SPECIES_AGE,
            g.site_class_cd,
            h.sum_vol
        FROM ((F_SUBAREA
        LEFT JOIN
        (SELECT F_STOREY_SPECIES.ARODES_INT_NUM,
                F_STOREY_SPECIES.SPECIES_CD,
                F_STOREY_SPECIES.SPECIES_AGE,
                F_STOREY_SPECIES.site_class_cd,
                F_STOREY_SPECIES.VOLUME
        FROM F_STOREY_SPECIES
        WHERE (((F_STOREY_SPECIES.[STOREY_CD])='DRZEW')
                AND ((F_STOREY_SPECIES.[species_rank_order])=1)) ) AS g
        ON F_SUBAREA.ARODES_INT_NUM = g.ARODES_INT_NUM)
        left join
        (select arodes_int_num, sum(volume) as sum_vol
        from f_storey_species
        group by arodes_int_num) as h
        on f_subarea.arodes_int_num = h.arodes_int_num
        )
        ;
        """
        sarea = self.cur.execute(sql).fetchall()

        sql = """
        SELECT
            F_AROD_CUE.ARODES_INT_NUM,
            F_AROD_CUE.MEASURE_CD,
            F_AROD_CUE.PROC_AREA,
            F_AROD_CUE.LARGE_TIMBER_PERC,
            F_AROD_CUE.LARGE_TIMBER_VALUE,
            F_AROD_CUE.LARGE_TIMBER_VALUE_NET
        FROM F_AROD_CUE
        order by arodes_int_num asc, cue_rank_order asc;
        """
        scue = self.cur.execute(sql).fetchall()

        sl = {
            x[0]: {
                "rpow": x[1],
                "pow": x[2],
                "gat": x[3] if x[3] not in [None, ""] else "",
                "wiek": x[4] if x[4] not in [None, ""] else "",
                "bhd": x[5] if x[5] not in [None, ""] else "",
                "miazsz": x[6] if x[6] not in [None, ""] else "",
                "zab": [],
            }
            for x in sarea
        }

        for si in scue:
            if si[0] not in sl:
                continue
            sl[si[0]]["zab"].append(si[1:])

        return sl

    def pobierz_wlascicieli_all(self):
        """pobiera wszystkich wlascicieli z tabeli v_address"""
        sql = "select addr_nr, name_1, name_2 from v_address;"
        return self.cur.execute(sql).fetchall()

    def pobierz_wyk_slowniki(self):
        """Zwraca 2 slowniki z gatunkami i zabiegami"""

        sql = "select measure_cd, measure_name from f_measure;"
        slz = {x[0]: x[1] for x in self.cur.execute(sql).fetchall()}

        sql = "select species_cd, species_name from f_tree_species;"
        slg = {x[0]: x[1] for x in self.cur.execute(sql).fetchall()}

        return slg, slz

    def usun_zadrzew_w_przes(self):
        """Usuwa z wszystkich warstw PRZES w tabeli f_arod_storey zadrzewienie"""
        sql = """
        update f_arod_storey set standdensity_index = NULL where
        storey_cd='PRZES';
        """
        return self.wpisz(sql)

    def usun_mase_z_podr_podsz_nal(self):
        """Usuwa z wszystkich warstw PODR, PODSZ, NAL w tabeli f_storey_species
        miazszosc
        """
        sql = """
        update f_storey_species set volume = NULL, volume_temp=NULL where
        storey_cd in ('PODSZ', 'PODR', 'NAL');
        """
        return self.wpisz(sql)

    def dopisz_ownership(self):
        """Dopisuje 7.1 w kolumniw ownership_cd w tabeli f_parcel o ile pole
        puste
        """
        sql = "update f_parcel set ownership_cd='7.1' " + "where isnull(ownership_cd);"
        return self.wpisz(sql)

    def pobierz_wydzielenia_nielesne(self):
        """Pobierz adr_les z wydzieleniami nielesnymi"""

        sql = """
            SELECT distinct F_ARODES.ADRESS_FOREST
            FROM F_PARCEL_LAND_USE INNER JOIN
            (F_ARODES INNER JOIN F_AROD_LAND_USE ON
            F_ARODES.ARODES_INT_NUM = F_AROD_LAND_USE.ARODES_INT_NUM) ON
            (F_PARCEL_LAND_USE.SHAPE_NR = F_AROD_LAND_USE.SHAPE_NR) AND
            (F_PARCEL_LAND_USE.PARCEL_INT_NUM = F_AROD_LAND_USE.PARCEL_INT_NUM)
            GROUP BY F_ARODES.ADRESS_FOREST, F_PARCEL_LAND_USE.AREA_USE_CD
            HAVING (((F_PARCEL_LAND_USE.AREA_USE_CD) Not Like "Ls"));
        """
        return self.pobierz(sql)

    def usun_rekordy(self, do_usun: list) -> bool:
        try:
            # Pobierz numery ARODES_INT_NUM do usunięcia
            wyniki = do_usun
            if not wyniki:
                print("Brak rekordów do usunięcia.")
                return False

            numery = wyniki
            if not numery:
                print("Lista numerów do usunięcia jest pusta.")
                return False

            tabele = [
                "F_STOREY_SPECIES",
                "F_AROD_CUE",
                "F_AROD_STOREY",
                "F_SUBAREA",
                "F_ERROR_HEAD",
                "F_SET",
                "F_ARODES",
            ]

            for tabela in tabele:
                sql_usun = f"DELETE FROM {tabela} WHERE ARODES_INT_NUM = ?"
                for numer in numery:
                    self.cur.execute(sql_usun, (numer,))
                    self.con.commit()
            print(f"Usunięto rekordy z tabeli {tabela}.")
            # return True
        except Exception as e:
            print(f"Błąd: {e}")
            return False

        # usun oddzialy puste
        sql = """select
                    ADRESS_FOREST,
                    ARODES_INT_NUM
                from
                    F_ARODES
              where ARODES_TYP_CD = 'ODDZ' or ARODES_TYP_CD = 'WYDZIEL';
                    """
        tab = self.cur.execute(sql).fetchall()
        oddz = Counter([x[0][:16] for x in tab])
        oddz_poj = [kk for kk, vv in oddz.items() if vv == 1]
        usun_oddz = [vi for ki, vi in tab if len([x for x in oddz_poj if x in ki]) > 0]

        sql_usun = f"DELETE FROM F_ARODES WHERE ARODES_INT_NUM = ?"
        tabele = [
            "F_ERROR_HEAD",
            "F_SET",
            "F_ARODES",
        ]
        for tabela in tabele:
            sql_usun = f"DELETE FROM {tabela} WHERE ARODES_INT_NUM = ? ;"
            for ki in usun_oddz:
                self.cur.execute(sql_usun, (ki,))
                self.con.commit()

        # usun lesnictwa
        sql = """select
                    ADRESS_FOREST,
                    ARODES_INT_NUM
                from
                    F_ARODES
                    """
        tab = self.cur.execute(sql).fetchall()
        les = Counter([x[0][:10] for x in tab])
        les_poj = [kk for kk, vv in les.items() if vv == 1]
        print(les_poj)
        usun_les = [vi for ki, vi in tab if len([x for x in les_poj if x in ki]) == 1]

        for tabela in tabele:
            sql_usun = f"DELETE FROM {tabela} WHERE ARODES_INT_NUM = ?"
            for ki in usun_les:
                self.cur.execute(sql_usun, (ki,))
                self.con.commit()

        return True
