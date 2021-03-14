import os
from PyQt5.QtWidgets import QFileDialog, QDialog, QMessageBox, QDockWidget, \
    QAction
from qgis.core import Qgis, QgsMessageLog, QgsRectangle, QgsFeatureRequest
from qgis.gui import QgsMapToolEmitPoint

from .ui.ui_baza_klonuj import Ui_Ui_Dialog as Ui_Dialog
from .baza_wrapper import Baza
from .funkcje import isNone

from qgis.PyQt.uic import loadUiType

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui',  'ui_klonuj_dock.ui'))


class Klonuj():
    def __init__(self, iface):
        """ Konstruktor """
        self.iface = iface  # potrzebne do wyświetlania paska

        self.wydz = {}  # {adr_les: arodes_int_num}
        self.instr = []  # [[adr_les_org, adr_les_klon], ...] oba adr w bazie!!
        self.bledy = 0  # liczba bledów podczas klonowania
        self.sklonowano = 0  # liczba poprawnych operacji

    def dane_dock(self, baza, z, do):
        self.baza = Baza(baza)
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Nie mogłem połączyć się z bazą',
                Qgis.Critical,
                0
            )
            return False

        # wczytaj dane z docka
        self.instr = [[z, dd] for dd in do]

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

    def dane_konf(self, baza, plik):
        self.baza = Baza(baza)
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Nie mogłem połączyć się z bazą',
                Qgis.Critical,
                0
            )
            return False

        # wczytaj dane z pliku
        instr = open(plik, 'r').readlines()

        if len(instr) > 0:
            self.instr = [x.rstrip('\r\n ').split('\t') for x in instr]

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
            self.instr = [x.rstrip('\r\n ').split('\t') for x in instr]

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

            if not self.k_arod_stand_pec(kl[0], kl[1]):
                self.blad(kl, 'f_arod_stand_pec')
                continue

            if not self.k_arod_storey(kl[0], kl[1]):
                self.blad(kl, 'f_arod_storey')
                continue

            if not self.k_storey_spec(kl[0], kl[1]):
                self.blad(kl, 'f_storey_species')
                continue

            self.sklonowano += 1

    def wyswietl_info(self):
        if self.bledy > 0:
            self.iface.messageBar().pushMessage(
                'Sklonowano '+str(self.sklonowano)+' wydzieleń. '
                'Błędów podczas '
                'klonowania: '+str(self.bledy)+' (Szczegóły w logu Las-R)',
                Qgis.Warning,
                0
            )
            return

        self.iface.messageBar().pushMessage(
            'Sklonowano wydzieleń: '+str(self.sklonowano),
            Qgis.Success,
            10
        )

    def blad(self, kl, kwer):
        self.bledy += 1

        if self.bledy == 1:
            QgsMessageLog.logMessage(
                '--------------\n'
                'Kolejność modyfikowania tabel przy klonowaniu wydzielenia:\n'
                'f_subarea\nf_arod_goal\nf_arod_stand_spec\nf_arod_storey\n'
                'f_storey_spec\n-------------\n'
                '(w nawiasach podano ARODES_INT_NUM)\n',
                'Las-R'
            )

        QgsMessageLog.logMessage(
            'Błąd klonowania: ' + kl[0] + ' (' + str(self.wydz[kl[0]]) + ')' +
            ' --> ' + kl[1] + ' (' + str(self.wydz[kl[1]]) + ')' +
            ' | tabela: '+kwer,
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
            if len(item) == 0:
                return False
        except:  # nopep8
            return False

        sql = [
            """update f_subarea set
            DAMAGE_DEGREE_CD = ?,
            CAUSE_CD =  ?,
            AREA_TYPE_CD = ?,
            POSITION_CD= ?,
            RELIEF_CD= ?,
            SITE_TYPE_CD= ?,
            DEGRADATION_CD= ?,
            VEG_COVER_CD = ?,
            STAND_STRUCT_CD = ?,
            SLOPE_CD = ?,
            EXPOSURE_CD = ?,
            MOISTURE_CD = ?,
            SOIL_PEC_CD = ?,
            SOIL_SUBTYPE_CD = ?,
            PLANT_COMM_CD = ?,
            FOREST_FUNC_CD = ?,
            ROTATION_AGE = ?,
            DEAD_WOOD  = ?,
            SUBAREA_INFO  = ?
            where ARODES_INT_NUM = ?; """,
            (
                item[0],
                item[1],
                item[2],
                item[3],
                item[4],
                item[5],
                item[6],
                item[7],
                item[8],
                item[9],
                item[10],
                item[11],
                item[12],
                item[13],
                item[14],
                item[15],
                item[16],
                item[17],
                item[18],
                self.wydz[do]
            )
        ]
        if not self.baza.wpisz_tab(sql):
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
            item = self.baza.pobierz(sql)
            # wydzielenia nielesne lener, inne_wyl
            if len(item) == 0:
                return True
        except:  # nopep8
            return False

        # jezeli w bazie nie ma takich rekordow dodajemy kopie
        sql = 'select * from f_arod_goal where arodes_int_num = ' + \
            str(self.wydz[do]) + ";"

        spr = self.baza.pobierz(sql)

        if len(spr) > 0:
            return False

        blednie_wpisano = False
        for it in item:
            sql = '''insert into f_arod_goal (
                    GOAL_TYPE_FL,
                    ARODES_INT_NUM ,
                    SPECIES_CD ,
                    GOAL_RANK_ORDER
                    )
                    values (\'''' + \
                str(isNone(it[0])) + '\', ' + \
                str(self.wydz[do]) + ', \'' + \
                str(isNone(it[2])) + '\', ' +  \
                str(it[3]) + ');'

            tab = [
                '''insert into f_arod_goal (
                    GOAL_TYPE_FL,
                    ARODES_INT_NUM ,
                    SPECIES_CD ,
                    GOAL_RANK_ORDER
                    )
                    values (?,?,?,?);''',
                (
                    it[0],
                    self.wydz[do],
                    it[2],
                    it[3]
                )
            ]

            if not self.baza.wpisz_tab(tab):
                blednie_wpisano = True

        if blednie_wpisano:
            return False
        return True

    def k_arod_stand_pec(self, z, do):
        # F_AROD_STAND_PEC
        sql = '''
        SELECT
            FOREST_PEC_CD ,ARODES_INT_NUM ,PEC_RANK_ORDER
        FROM
            F_AROD_STAND_PEC
        WHERE
            ARODES_INT_NUM = '''
        sql += str(self.wydz[z]) + ";"
        item = self.baza.pobierz(sql)

        for it in item:
            sql = [
                '''insert into f_arod_stand_pec(
                    FOREST_PEC_CD,
                    ARODES_INT_NUM,
                    PEC_RANK_ORDER) values (?,?,?);''',
                (it[0], self.wydz[do], it[2])
            ]

            if not self.baza.wpisz_tab(sql):
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
        sql += str(self.wydz[z]) + ";"
        item = self.baza.pobierz(sql)

        for it in item:
            # sql = '''insert into f_arod_storey(
                        # ARODES_INT_NUM ,
                        # STOREY_CD ,
                        # STOREY_RANK_ORDER ,
                        # STANDDENSITY_INDEX ,
                        # MIXTURE_CD ,
                        # DENSITY_CD ,
                        # TREE_STOCK_CD ,
                        # SILV_QUALITY_CD ,
                        # LOCATION_CD) values ( \'''' + \
                # str(self.wydz[do]) + ', \'' + \
                # str(isNone(it[0])) + '\', ' + \
                # str(it[1]) + ', ' + \
                # str(round(float(str(isNone(it[2])), 1))) + ', ' + \
                # str(it[3]) + ', \'' + \
                # str(it[4]) + '\', \'' + \
                # str(it[5]) + '\', ' + \
                # str(it[6]) + ', \'' + \
                # str(it[7]) + '\', ' + \
                # ');'

            sql = [
                '''insert into f_arod_storey(
                        ARODES_INT_NUM ,
                        STOREY_CD ,
                        STOREY_RANK_ORDER ,
                        STANDDENSITY_INDEX ,
                        MIXTURE_CD ,
                        DENSITY_CD ,
                        TREE_STOCK_CD ,
                        SILV_QUALITY_CD ,
                        LOCATION_CD) values (?,?,?,?,?,?,?,?,?);''',
                (
                    self.wydz[do],
                    it[0],
                    it[1],
                    it[2],
                    it[3],
                    it[4],
                    it[5],
                    it[6],
                    it[7]
                )
            ]

            if not self.baza.wpisz_tab(sql):
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
        cur_ind = self.baza.pobierz(sql)[0][0]

        for it in item:
            cur_ind += 1
            sql = [
                '''insert into f_storey_species(
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
                    INCREMENT_CURRENT_AREA)
                values
                    (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?);''',
                (
                    cur_ind,
                    self.wydz[do],
                    it[0],
                    it[1],
                    it[2],
                    it[3],
                    it[4],
                    it[5],
                    it[6],
                    it[7],
                    it[8],
                    it[9],
                    it[10],
                    it[11],
                    it[12]
                )
            ]

            if not self.baza.wpisz_tab(sql):
                return False
        return True


class PobierzDaneDock(QDockWidget, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(PobierzDaneDock, self).__init__(parent)
        self.setupUi(self)
        self.valid = False
        self.porzucone = True
        self.iface = iface

        self.pushButton_anuluj.clicked.connect(self.porzuc)
        self.pushButton_baza.clicked.connect(self.kat_baza)
        self.pushButton_plik.clicked.connect(self.kat_warstwa)
        self.toolButton_usun.clicked.connect(self.skasuj)

        self.akcja_z = QAction('wskaż', self.iface.mainWindow())
        self.akcja_z.triggered.connect(self.klik_zrodlo)
        self.toolButton_z.setDefaultAction(self.akcja_z)

        self.akcja_do = QAction('wskaż', self.iface.mainWindow())
        self.akcja_do.triggered.connect(self.klik_do)
        self.toolButton_do.setDefaultAction(self.akcja_do)

        self.toolButton_usun.clicked.connect(self.usun)
        self.pushButton_uruchom.clicked.connect(self.klonuj)

    def usun(self):
        pass

    def kat_baza(self):
        sc = QFileDialog().getOpenFileName(
            self, 'Wskaż bazę Taksatora', self.kat, "Access MDB (*.mdb)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.lineEdit_baza.setText(sc)

    def kat_warstwa(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż plik z instrukcjami',
                                           self.kat,
                                           "instrukcje (*.txt)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.lineEdit_plik.setText(sc)

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if self.radioButton_k.isChecked():
            if os.path.isfile(self.lineEdit_plik.text()) and \
                    os.path.isfile(self.lineEdit_baza.text()):
                self.valid = True
                self.porzucone = False
            else:
                message = QMessageBox()
                message.setIcon(QMessageBox.Information)
                message.setWindowTitle('Błąd')
                message.setText(
                    'Nie udało się odnaleźć wszystkich podanych plików!')
                message.addButton(u"Zamknij", QMessageBox.ActionRole)
                message.exec_()
                return False
        else:
            if not os.path.isfile(self.lineEdit_baza.text()):
                return False
            if self.lineEdit_z.text() in ['', ' ']:
                return False
            if self.listWidget.count() == 0:
                return False

        return True

    def klik_zrodlo(self):
        self.tz = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.iface.mapCanvas().setMapTool(self.tz)
        self.tz.canvasClicked.connect(self.pobierz_z)

    def klik_do(self):
        self.ta = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.iface.mapCanvas().setMapTool(self.ta)
        self.ta.canvasClicked.connect(self.pobierz_do)

    def pobierz_z(self, koord):
        rec = QgsRectangle(koord[0]-0.1, koord[1]-0.1,
                           koord[0]+0.1, koord[1]+0.1)
        req = QgsFeatureRequest().setFilterRect(rec)
        f = ''
        for fd in self.iface.activeLayer().getFeatures(req):
            f = fd['ADR_LES']

        if f in ['', None, 'NULL']:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Na pewno wskazałeś warstwę z kolumną ADR_LES?',
                Qgis.Critical,
                0
            )
        self.lineEdit_z.setText(f)

    def pobierz_do(self, koord):
        rec = QgsRectangle(koord[0]-0.1, koord[1]-0.1,
                           koord[0]+0.1, koord[1]+0.1)
        req = QgsFeatureRequest().setFilterRect(rec)
        f = ''
        for fd in self.iface.activeLayer().getFeatures(req):
            f = fd['ADR_LES']

        if f == self.lineEdit_z.text():
            return

        if f not in ['', None, 'NULL']:
            self.listWidget.addItem(f)
        else:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Na pewno wskazałeś warstwę z kolumną ADR_LES?',
                Qgis.Critical,
                0
            )

    def skasuj(self):
        itms = self.listWidget.selectedItems()

        for i in range(self.listWidget.count()-1, -1, -1):
            if self.listWidget.item(i) in itms:
                self.listWidget.takeItem(i)

    def klonuj(self):
        klon = Klonuj(self.iface)
        if not self.sprawdz_ok:
            return
        if self.radioButton_k:
            wyn = klon.dane_konf(
                self.lineEdit_baza.text(), self.lineEdit_plik.text()
            )
        else:
            wyn = klon.dane_dock(
                self.lineEdit_baza.text(),
                self.lineEdit_z.text(),
                [self.listWidget.item(x).text()
                 for x in range(self.listWidget.count())]
            )
            self.listWidget.clear()

        if not wyn:
            return
        if klon.sprawdz_dane():
            klon.klonuj()
            klon.wyswietl_info()


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
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText(
                'Nie udało się odnaleźć wszystkich podanych plików!')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

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
