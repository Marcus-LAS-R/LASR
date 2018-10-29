import os
import pypyodbc as pyodbc
import sqlite3
from datetime import datetime
from shutil import copyfile


class Baza(object):
    def __init__(self, b):
        # otworz podana baze danych
        self.con = False
        self.cur = False
        self.ok = False
        self.baza = b

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
        self.cur.close()
        self.con.close()

    def wpisz(self, sql):
        """Metoda dopisuje do bazy podanego sql"""
        self.cur.execute(sql)
        self.con.commit()

    def utworz_kopie(self, wpis=''):
        """Metoda tworzy w katalogu z podana baza kopie bezpieczenstwa ze
        znacznikiem czasu oraz ew podanym wpisem"""
        katalog, plik = os.path.split(self.baza)
        plikn = plik[:-4] + \
            '_' + wpis + '_' + \
            datetime.now().isoformat().replace(':', '')[:-7] + \
            '.mdb'
        copyfile(self.baza, os.path.join(katalog, plikn))

        # debug
        # self.baza = plikn

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
                , F_PARCEL_LAND_USE.SOIL_QUALITY_CD
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
