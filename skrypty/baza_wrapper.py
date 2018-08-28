import pypyodbc as pyodbc
import sqlite3


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

        if self.baza[-3:] == 'mdb':
            MDB = self.baza
            DRV = '{Microsoft Access Driver (*.mdb, *.accdb)}'
            PWD = 'pw'
            # polacz
            self.con = pyodbc.connect('DRIVER={};DBQ={};PWD={}'.format(DRV, MDB, PWD))
            self.cur = self.con.cursor()
            self.ok = True
            return True

        elif self.baza[-6:] == 'sqlite':
            self.con = sqlite3.connect(self.baza)
            self.cur = self.con.cursor()
            self.ok = True
            return True

        return False

    def uzytki(self):
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
                , [COUNTY_CD] & [DISTRICT_CD] & [MUNICIPALITY_CD] & [COMMUNITY_CD] & \'.\' & [REG_SHEET_NR2] &
                  IIF (ISNULL(F_PARCEL.REG_SHEET_NR2),\'\', \'.\') & [PARCEL_NR] AS Wyr1
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
                                      V_PARCEL_PARTICIPATION.parcel_int_num = F_PARCEL_LAND_USE.PARCEL_INT_NUM)
                  ON
                            (
                                      V_PARCEL_PARTICIPATION.parcel_int_num = F_PARCEL.PARCEL_INT_NUM
                            )
                            AND
                            (
                                      F_PARCEL.PARCEL_INT_NUM = F_PARCEL_LAND_USE.PARCEL_INT_NUM
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

