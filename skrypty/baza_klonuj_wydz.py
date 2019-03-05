import os
from PyQt5.QtWidgets import QFileDialog, QDialog, QMessageBox
from qgis.core import Qgis, QgsMessageLog

from .ui.ui_baza_klonuj import Ui_Ui_Dialog as Ui_Dialog
from .baza_wrapper import Baza
from .funkcje import isNone


class Klonuj():
    def __init__(self, iface):
        """ Konstruktor """
        self.iface = iface  # potrzebne do wyświetlania paska

        self.wydz = {}  # {adr_les: arodes_int_num}
        self.instr = []  # [[adr_les_org, adr_les_klon], ...] oba adr w bazie!!
        self.bledy = 0  # liczba bledów podczas klonowania
        self.sklonowano = 0  # liczba poprawnych operacji

    def pobierz_dane(self):
        """ Metoda pobiera od użyszkodnia ścieżkę do bazy oraz ścieżkę do pliku
        tekstowego z instrukcjami do klonownia """
        self.pobierz_dane = PobierzDane()
        self.pobierz_dane.exec_()

        if self.pobierz_dane.porzucone:
            return False

        self.baza = Baza(self.pobierz_dane.ui.lineEdit_baza.text())
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Nie mogłem połączyć się z bazą',
                Qgis.Critical,
                0
            )
            return False

        # wczytaj dane z pliku
        instr = open(
            self.pobierz_dane.ui.lineEdit_wydz.text(), 'r').readlines()

        if len(instr) > 0:
            self.instr = [x.split('\t') for x in instr]

        # jeżeli nie odnaleziono żadnych instrukcji
        if len(self.instr) == 0:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'w pliku z instrukcjami nie odnaleziono żadnych adresów.',
                Qgis.Critical,
                0
            )
            return False

        # jezeli odnaleziono niepoprawna strukturę...
        if set([len(x) for x in self.instr]) != set([2]):
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'w pliku z instrukcjami odnaleziono niepoprawną strukturę '
                'danych. Sprawdź czy wszystkie adresy oddzielone są tab-ami i'
                ' na końcu nie ma pustej linii!',
                Qgis.Critical,
                0
            )
            return False

        return True

    def sprawdz_dane(self):
        """ Metoda sprawdza czy wskazana baza i plik tekstowy jest
        kompatybilny, jeżeli tak zwraca True
        """
        self.wydz = self.baza.pobierz_wydzielenia()

        # sprawdz czy wszystkie adresy lesne sa w bazie
        nieobecne = []  # tab z adresami lesnymi nieobecnymi w bazie
        for x in self.instr:
            if x[0] not in self.wydz:
                nieobecne.append(x[0])
            if x[1] not in self.wydz:
                nieobecne.append(x[1])

        if len(nieobecne) > 0:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Brak w bazie adr les: ' +
                ', '.join(nieobecne),
                Qgis.Critical,
                0
            )
            return False

        self.baza.utworz_kopie('klonowanie_wydz')
        return True

    def klonuj(self):
        """ Metoda zbiorcza dla klonowania danych z bazy """

        for kl in self.instr:

            if not self.k_subarea(kl[0], kl[1]):
                self.blad(kl, 'f_subarea')
                continue

            if not self.k_arod_goal(kl[0], kl[1]):
                self.blad(kl, 'f_arod_goal')
                continue

            if not self.k_arod_stand_spec(kl[0], kl[1]):
                self.blad(kl, 'f_arod_stand_spec')
                continue

            if not self.k_arod_storey(kl[0], kl[1]):
                self.blad(kl, 'f_arod_storey')
                continue

            if not self.k_storey_spec(kl[0], kl[1]):
                self.blad(kl, 'f_storey_spec')
                continue

            self.sklonowano += 1

    def wyswietl_info(self):
        if self.blad > 1:
            self.iface.messageBar().pushMessage(
                'Sklonowano '+str(self.sklonowano)+'wydzieleń. Błędów podczas '
                'klonowania: '+str(self.blad)+' (Szczegóły w logu Las-R)',
                Qgis.Warning,
                0
            )
            return

        self.iface.messageBar().pushMessage(
            'Sklonowano '+str(self.sklonowano)+'wydzieleń.',
            Qgis.Success,
            10
        )

    def blad(self, kl, kwer):
        self.blad += 1

        if self.blad == 1:
            QgsMessageLog.logMessage(
                '--------------'
                'Kolejność modyfikowania tabel przy klonowaniu wydzielenia:\n'
                'f_subarea\nf_arod_goal\nf_arod_stand_spec\nf_arod_storey\n'
                'f_storey_spec\n-------------',
                'Las-R'
            )

        QgsMessageLog.logMessage(
            'Błąd klonowania: ' + kl[0] + ' --> ' + kl[1] + ' | tabela: '+kwer,
            'Las-R'
        )

    def k_subarea(self, z, do):  # noqa
        # z - z jakiego adresy kopiujemy
        # do - do jakiego adresu kopiujemy ...

        sql = '''
        SELECT
            DAMAGE_DEGREE_CD,
            CAUSE_CD,
            AREA_TYPE_CD,
            POSITION_CD ,
            RELIEF_CD ,
            SITE_TYPE_CD ,
            DEGRADATION_CD ,
            VEG_COVER_CD ,
            STAND_STRUCT_CD ,
            SLOPE_CD ,
            EXPOSURE_CD ,
            MOISTURE_CD ,
            SOIL_PEC_CD ,
            SOIL_SUBTYPE_CD ,
            PLANT_COMM_CD ,
            FOREST_FUNC_CD ,
            ROTATION_AGE ,
            DEAD_WOOD,
            SUBAREA_INFO
        FROM
            F_SUBAREA
        WHERE
            F_SUBAREA.ARODES_INT_NUM = '''

        sql += str(self.wydz[z]) + ';'

        try:
            item = self.baza.pobierz(sql)[0]
            if len(item) != 1:
                return False
        except:  # nopep8
            return False

        sql = "update f_subarea set "
        sql += 'DAMAGE_DEGREE_CD = ' + isNone(item[0], True)
        if item[1] is not None:
            sql += ',CAUSE_CD = ' + "'" + isNone(item[1]) + "'"
        sql += ',AREA_TYPE_CD = ' + "'" + isNone(item[2]) + "'"
        if item[3] is not None:
            sql += ',POSITION_CD= ' + "'" + isNone(item[3]) + "'"
        if item[4] is not None:
            sql += ',RELIEF_CD= ' + "'" + isNone(item[4]) + "'"
        if item[5] is not None:
            sql += ',SITE_TYPE_CD= ' + "'" + isNone(item[5]) + "'"
        if item[6] is not None:
            sql += ',DEGRADATION_CD= ' + "'" + isNone(item[6]) + "'"
        if item[7] is not None:
            sql += ',VEG_COVER_CD = ' + "'" + isNone(item[7]) + "'"
        if item[8] is not None:
            sql += ',STAND_STRUCT_CD = ' + "'" + isNone(item[8]) + "'"
        if item[9] is not None:
            sql += ',SLOPE_CD = ' + "'" + isNone(item[9]) + "'"
        if item[10] is not None:
            sql += ',EXPOSURE_CD = ' + "'" + isNone(item[10]) + "'"
        if item[11] is not None:
            sql += ',MOISTURE_CD = ' + "'" + isNone(item[11]) + "'"
        if item[12] is not None:
            sql += ',SOIL_PEC_CD = ' + "'" + isNone(item[12]) + "'"
        if item[13] is not None:
            sql += ',SOIL_SUBTYPE_CD = ' + "'" + isNone(item[13]) + "'"
        if item[14] is not None:
            sql += ',PLANT_COMM_CD = ' + "'" + isNone(item[14]) + "'"
        if item[15] is not None:
            sql += ',FOREST_FUNC_CD = ' + "'" + isNone(item[15]) + "'"
        if item[16] is not None:
            sql += ',ROTATION_AGE = ' + isNone(item[16], True)
        if item[17] is not None:
            sql += ',DEAD_WOOD  = ' + isNone(item[17], True)
        if item[18] is not None:
            sql += ',SUBAREA_INFO  = ' + "'" + isNone(item[18]) + "'"
        sql += ' where ARODES_INT_NUM = ' + str(self.wydz[do]) + ';'

        if not self.baza.wpisz(sql):
            return False

        return True

    def k_arod_goal(self, z, do):
        sql = '''
        SELECT
            GOAL_TYPE_FL,
            ARODES_INT_NUM ,
            SPECIES_CD ,
            GOAL_RANK_ORDER ,
            GOAL_SPECIES_PERC
        FROM
            F_AROD_GOAL
        WHERE
            ARODES_INT_NUM = '''

        sql += str(self.wydz[z]) + ';'

        try:
            item = self.baza.pobierz(sql)[0]
            if len(item) != 1:
                return False
        except:  # nopep8
            return False

        # jezeli w bazie nie ma takich rekordow dodajemy kopie
        sql = 'select * from f_arod_goal where arodes_int_num = ' + \
            str(self.wydz[do]) + ";"

        spr = self.baza.pobierz(sql)

        if len(spr) > 0:
            return False

        for it in item:
            sql = '''insert into f_arod_goal (
                GOAL_TYPE_FL,
                ARODES_INT_NUM ,
                SPECIES_CD ,
                GOAL_RANK_ORDER
                )
                values (\'''' + \
                isNone(it[0]) + '\', ' + \
                str(self.wydz[do]) + ', \'' + \
                isNone(it[2]) + '\', ' +  \
                str(it[3]) + ');'

            if not self.baza.wpisz(sql):
                return False

        return True

    def k_arod_stand_spec(self, z, do):
        # F_AROD_STAND_PEC
        sql = '''
        SELECT
            FOREST_PEC_CD ,ARODES_INT_NUM ,PEC_RANK_ORDER
        FROM
            F_AROD_STAND_PEC
        WHERE
            ARODES_INT_NUM = '''
        sql += str(self.wydz[do]) + ";"
        item = self.baza.pobierz(sql)

        for it in item:
            sql = '''insert into f_arod_stand_pec(
                FOREST_PEC_CD,
                ARODES_INT_NUM ,
                PEC_RANK_ORDER) values (
                \'''' + \
                isNone(it[0]) + '\', ' + \
                str(self.wydz[do]) + ', ' + \
                str(it[2]) + ');'

            if not self.baza.wpisz(sql):
                return False

        return True

    def k_arod_storey(self, z, do):

        # F_AROD_STOREY
        sql = '''
        SELECT
            STOREY_CD ,
            STOREY_RANK_ORDER ,
            STANDDENSITY_INDEX ,
            MIXTURE_CD ,
            DENSITY_CD ,
            TREE_STOCK_CD ,
            SILV_QUALITY_CD ,
            LOCATION_CD
        FROM
            F_AROD_STOREY
        WHERE
            ARODES_INT_NUM = '''
        sql += str(self.wydz[do]) + ";"
        item = self.baza.pobierz(sql)

        for it in item:
            sql = '''insert into f_arod_storey(
                        ARODES_INT_NUM ,
                        STOREY_CD ,
                        STOREY_RANK_ORDER ,
                        STANDDENSITY_INDEX ,
                        MIXTURE_CD ,
                        DENSITY_CD ,
                        TREE_STOCK_CD ,
                        SILV_QUALITY_CD ,
                        LOCATION_CD) values ( \'''' + \
                str(self.wydz[do]) + ', \'' + \
                isNone(it[0]) + '\', ' + \
                str(it[1]) + ', ' + \
                str(round(float(isNone(it[2]), 1))) + ', ' + \
                str(it[3]) + ', \'' + \
                str(it[4]) + '\', \'' + \
                str(it[5]) + '\', ' + \
                str(it[6]) + ', \'' + \
                str(it[7]) + '\', ' + \
                ');'

            if not self.baza.wpisz(sql):
                return False
        return True

    def k_storey_spec(self, z, do):

        # F_STORE_SPEC
        sql = '''
        SELECT
            STOREY_CD,
            SPECIES_RANK_ORDER,
            SPECIES_CD,
            PART_CD,
            SPECIES_AGE,
            BHD,
            HEIGHT,
            VOLUME,
            SITE_CLASS_CD,
            TECHN_QUALITY_CD,
            INCREMENT_CURRENT,
            VOLUME_TEMP,
            INCREMENT_CURRENT_AREA
        FROM
            F_STOREY_SPECIES
        WHERE
            ARODES_INT_NUM = '''
        sql += str(self.wydz[z]) + ';'

        item = self.baza.pobierz(sql)
        sql = 'select max(f.spec_stor_int_num) from f_storey_species as f;'
        cur_ind = self.baza.pobierz(sql)[0]

        for it in item:
            cur_ind += 1
            sql = '''insert into f_storey_species(
                        SPEC_STOR_INT_NUM,
                        ARODES_INT_NUM,
                        STOREY_CD,
                        SPECIES_RANK_ORDER,
                        SPECIES_CD,
                        PART_CD,
                        SPECIES_AGE,
                        BHD,
                        HEIGHT,
                        VOLUME,
                        SITE_CLASS_CD,
                        TECHN_QUALITY_CD,
                        INCREMENT_CURRENT,
                        VOLUME_TEMP,
                        INCREMENT_CURRENT_AREA) values (''' + \
                str(cur_ind) + ', ' + \
                str(self.wydz[do]) + ', \'' + \
                str(it[0]) + '\', ' + \
                str(it[1]) + \
                str(it[2]) + ', \'' + \
                str(it[3]) + '\', ' + \
                str(it[4]) + ', ' + \
                str(it[5]) + ', ' + \
                str(it[6]) + ', ' + \
                str(it[7]) + ', \'' + \
                str(it[8]) + '\', \'' + \
                str(it[9]) + '\', ' + \
                str(it[10]) + ', ' + \
                str(it[11]) + ', ' + \
                str(it[12]) + ');'

            if not self.baza.wpisz(sql):
                return False
        return True


class PobierzDane(QDialog):
    def __init__(self):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # katalog który będzie uzupełniony po pierwszym wskazaniu warstwy, bazy
        self.kat = ''

        # wartosc True jezeli uzytkownik zrezygnowal z przetwarzania
        self.porzucone = True

        # trigger do sprawdzenia poprawnosci wpisanych danych przez
        # uzyszkodnika
        self.valid = False

        # sygnały
        self.ui.pushButton_ok.clicked.connect(self.sprawdz_ok)
        self.ui.pushButton_cancel.clicked.connect(self.porzuc)
        self.ui.pushButton_baza.clicked.connect(self.kat_baza)
        self.ui.pushButton_wydz.clicked.connect(self.kat_warstwa)

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if os.path.isfile(self.ui.lineEdit_wydz.text()) and \
                os.path.isfile(self.ui.lineEdit_baza.text()):
            self.valid = True
            self.porzucone = False
            self.hide()
        else:
            msbx = QMessageBox(
                'Nie udało się odnaleźć wszystkich podanych plików!')
            msbx.exec_()

    def kat_baza(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż bazę Taksatora',
                                           self.kat,
                                           "Access MDB (*.mdb)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_baza.setText(sc)

    def kat_warstwa(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż plik z instrukcjami',
                                           self.kat,
                                           "instrukcje (*.txt)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_wydz.setText(sc)
