import os
import glob
import platform
from PyQt5.QtWidgets import QFileDialog
from datetime import datetime
from shutil import copyfile
from qgis.core import Qgis, QgsMessageLog

from .pw import PasekPostepu
from .baza_wrapper import Baza


class PolaczBazy():
    def __init__(self, iface):
        self.iface = iface

        self.baza0 = False  # baza do ktorej kopiujemy reszte danych
        self.lista = []  # lista ze sciezkami do baz w katalogu
        self.postep = PasekPostepu(self.iface).stworz_pasek(
            'Kopiowanie baz TPU')
        self.postep.setValue(0)

    def pobierz_katalog(self):
        bazy_kat = QFileDialog().getExistingDirectory(
            self.iface.mainWindow(),
            "Katalog z bazami danych",
            ''
        )

        if platform.system()[:3] == 'Win':
            bTemp = glob.glob(os.path.join(bazy_kat, "*.mdb"))
        else:
            bTemp = glob.glob(os.path.join(bazy_kat, "*.sqlite"))

        mess = ''
        if len(bTemp) == 0:
            mess = 'Nie odnalazłem żadnej bazy we wskazanym katalogu!'
        elif len(bTemp) == 1:
            mess = 'Do łącznia wymagane są przynajmniej ' + \
                'dwie bazy drogi użyszkodniku ;)'

        self.lista = bTemp

        if mess != '':
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                mess,
                Qgis.Critical,
                0)
            return False

        return True

    def stworz_docelowa(self):
        katalog, plik = os.path.split(self.lista[0])
        self.czas = \
            datetime.now().isoformat().replace(':', '')[:-7]

        if platform.system()[:3] == 'Win':
            plikn = 'baza_polaczona_' + self.czas + '.mdb'
        else:
            plikn = 'baza_polaczona_' + self.czas + '.sqlite'

        try:
            copyfile(self.lista[0], os.path.join(katalog, plikn))
        except Exception:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się skopiować bazy, masz prawa dostępu do zapisu?',
                Qgis.Critical, 0)
            return False

        self.baza0 = Baza(os.path.join(katalog, plikn))

        if self.baza0.polacz():
            self.postep.setValue(5)
            return True
        else:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się podłączyć do skopiowanej bazy',
                Qgis.Critical, 0)
            return False

    def przygotuj_kopiowanie(self):
        if not self.stworz_docelowa():
            return False
        return True

    def kopiuj(self):
        proc = int(90/len(self.lista))
        ust = 10
        for bsc in self.lista[1:]:
            ust = ust + proc
            self.postep.setValue(ust)
            baza_zrodlowa = Baza(bsc)
            if baza_zrodlowa.polacz():
                lacz = Laczenie(self.baza0, baza_zrodlowa)
                lacz.p_f_max()
                lacz.p_f_arodes()
                lacz.p_tabele()
                lacz.d_tabele()
                baza_zrodlowa.zamknij()
                self.postep.setValue(10+proc)

        self.baza0.zamknij()
        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage(
            'POŁĄCZONE',
            'Łączenie ' + str(len(self.lista)) + ' baz zakończone powodzeniem',
            Qgis.Success,
            0
        )


class Laczenie():
    def __init__(self, baza0, baza):
        self.baza0 = baza0  # baza docelowa
        self.baza = baza  # baza z ktorej kopiujemy

        # pola ktorych wartosci maksymalne musimy znac
        self.maxint = -1  # max arodes_intnum w bazie0
        self.maxspecstor = -1  # spec_stor_int_num

        # lista zdublowanych wydzielen w f_arodes -> nie laczymy baz
        self.l_zdublowanych_f_arodes = []
        self.l_wpisanych_innych = []  # lista wpisanych adress_forest do bazy

        self.sl_arodes = {}  # slownik z starym arodes: nowy arodes
        self.f_arodes = []

        self.tab = [
            [[], 'f_subarea', [
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
            ]],
            [[], 'f_arod_storey', [
                "ARODES_INT_NUM",
                "STOREY_CD",
                "STOREY_RANK_ORDER",
                "STANDDENSITY_INDEX",
                "MIXTURE_CD",
                "DENSITY_CD",
                "TREE_STOCK_CD",
                "SILV_QUALITY_CD",
                "LOCATION_CD",
            ]],
            [[], 'f_storey_species', [
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
            ]],
            [[], 'f_arod_stand_pec', [
                "FOREST_PEC_CD",
                "ARODES_INT_NUM",
                "PEC_RANK_ORDER",
            ]],
            [[], 'f_arod_goal', [
                "GOAL_TYPE_FL",
                "ARODES_INT_NUM",
                "SPECIES_CD",
                "GOAL_RANK_ORDER",
                "GOAL_SPECIES_PERC",
            ]],
            [[], 'f_arod_spec_area', [
                "ARODES_INT_NUM",
                "AROD_SPAREA_ORDER",
                "SPECIAL_AREA_CD",
                "LOCATION_CD",
                "SPECIAL_AREA",
                "SPECIAL_AREA_YEAR",
                "SPECIAL_AREA_NUM",
            ]],
            [[], 'f_species_sparea', [
                "ARODES_INT_NUM",
                "AROD_SPAREA_ORDER",
                "SP_RANK_ORDER",
                "SPECIES_CD",
                "SP_AGE",
                "SP_AGE_BEG",
                "SP_AGE_TEMP",
            ]],
            [[], 'f_arod_phenomena', [
                "ARODES_INT_NUM",
                "PHEN_RANK_ORDER",
                "PHENOMENA_CD",
                "LOCATION_CD",
                "SPECIES_CD",
                "PLANT_CD",
                "PHEN_NUM",
                "PHEN_AREA",
                "NATURE_MON_FL",
            ]],
        ]

        # self.f_subarea = []
        # self.f_arod_storey = []
        # self.f_storey_species = []  # int_num na 2 miejscu
        # self.f_arod_stand_pec = []  # int_num na 2 miejscu
        # self.f_arod_spec_area = []
        # self.f_species_sparea = []
        # self.f_arod_goal = []
        # self.f_arod_phenomena = []

    def zdublowany_f_arodes(self):
        # sprawdz czy w bazie z ktorej bierzemy wydzielenia nie ma powtorzen w
        # stosunku do bazy orginalnej
        wydz0 = self.baza0.pobierz_wydzielenia()
        wydz1 = self.baza.pobierz_wydzielenia()

        # nie laczymy pustych baz - same problemy i brak sensu
        if wydz0 is False or wydz1 is False:
            return False

        self.l_zdublowanych_f_arodes = [
            x for x in wydz1.keys() if x not in wydz0.keys()]

        if len(self.l_zdublowanych_f_arodes) > 0:
            QgsMessageLog.logMessage(
                'Lista rekordów z F_ARODES już wpisana do bazy (' +
                self.baza.baza + ')\n' +
                '\n'.join(self.l_zdublowanych_f_arodes),
                'Las-R'
            )

            return True
        return False

    def p_f_arodes(self):
        # pobierz arodesy z obu baz i sprawdz co sie powtarza aby nie dublowac
        # danych w bazie

        sql = 'select * from f_arodes order by arodes_int_num asc;'
        arod_org = self.baza0.pobierz(sql)
        arod_zrd = self.baza.pobierz(sql)

        sl_org_baza = {x[1] for x in arod_org}
        # tutaj napewno nie bedzie Wydzielen ale moga zdarzyc sie oddzialy,
        # obreby lub lesnictwa
        for it in arod_zrd:
            if it[1] not in sl_org_baza:
                self.maxint += 1
                self.f_arodes.append([self.maxint] + list(it[1:]))
                self.sl_arodes[it[0]] = self.maxint
            else:
                self.l_wpisanych_innych.append(it[1])

    def p_tabele(self):
        for t in self.tab:
            sql = 'select '+','.join(t[2]) + ' from ' + t[1] + ';'
            t[0] = self.baza.pobierz(sql)

    def p_f_max(self):
        # metoda pobiera nawieksza wartos arodes_int_num i spec_stor_int_num
        # w bazie docelowej
        sql = 'select max(arodes_int_num) from f_arodes;'
        maxint = self.baza0.pobierz(sql)
        if maxint is not False:
            self.maxint = maxint[0][0]

        sql = 'select max(spec_stor_int_num) from f_storey_species;'
        maxint = self.baza0.pobierz(sql)
        if maxint is not False:
            self.maxspecstor = maxint[0][0]

    def d_tabele(self):
        # dopisz do bazy zrodlowej info z bazy wyjsciowej
        for row in self.f_arodes:
            sql = 'insert into f_arodes (ARODES_INT_NUM, ADRESS_FOREST, ' + \
                ' ARODES_TYP_CD, ORDER_KEY, ADRESS_VALID, PROT_INT_NUM, ' + \
                'TEMP_RAPORT) values (' + '?,'*(len(row)-1) + '?);'

            self.baza0.cur.execute(sql, row)
            self.baza0.con.commit()

        for id in range(8):
            for row in self.tab[id][0]:

                nag = []
                its = []
                intnum = -1
                for i, r in enumerate(row):
                    if r is not None:
                        nag.append(self.tab[id][2][i])
                        if id in [0, 1, 5, 6, 7] and i == 0:
                            its.append(self.sl_arodes[r])
                            intnum = r
                        elif id == 2 and i == 0:
                            self.maxspecstor += 1
                            its.append(self.maxspecstor)
                        elif id in [2, 4] and i == 1:
                            its.append(self.sl_arodes[r])
                            intnum = r
                        elif id == 3 and i == 1:
                            its.append(self.sl_arodes[r])
                            intnum = r
                        else:
                            its.append(r)

                sql = 'insert into ' + self.tab[id][1] + ' (' + \
                    ','.join(nag) + ') values (' + \
                    ','.join(['?' for x in its]) + ');'

                if intnum in self.sl_arodes:
                    self.baza0.cur.execute(sql, its)
                    self.baza0.con.commit()
