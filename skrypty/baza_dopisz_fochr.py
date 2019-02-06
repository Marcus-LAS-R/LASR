import os
from qgis.core import QgsVectorLayer, Qgis, QgsMessageLog, QgsSpatialIndex, \
    QgsFeatureRequest
from PyQt5.QtWidgets import QFileDialog, QDialog, QMessageBox

from .baza_wrapper import Baza
from .sprawdzenia_warstw import SprawdzWydzielenia
from .ui.ui_baza_dopiszFO import Ui_Dialog


class DopiszFO(SprawdzWydzielenia):
    def __init__(self, iface):
        self.iface = iface
        super()

        # slownik z powierzchniami wydzielen przecinajacych sie z FO
        self.sl = {}
        self.fow = []  # features wybranych form ochrony przyrody
        self.fo_si = QgsSpatialIndex()  # SI wszystkich form ochrony przyrody
        self.wydz_si = QgsSpatialIndex()  # SI wszystkich wydzielen
        self.wydz_sl = {}  # slownik z feature'ami wydz
        self.wyb_fo_trig = False  # trigger dla metody wybierz_wydz

        QgsMessageLog.logMessage(
                '\n\n---[  Dopisanie form ochrony przyrody do bazy  ]---\n',
                'Las-R',
                Qgis.Info
        )

    def pobierz_dane_od_uzytkownika(self):
        """Pobierz dane przez formularz"""
        self.Dane = PobierzDane()
        self.Dane.exec_()

        if self.Dane.porzucone:
            return False

        # otworz potrzebne warstwy i i baze
        self.wydz = QgsVectorLayer(self.Dane.ui.lineEdit_wydz.text(),
                                   'wydz',
                                   'ogr'
                                   )
        self.fo = QgsVectorLayer(self.Dane.ui.lineEdit_fochr.text(),
                                 'fochr',
                                 'ogr'
                                 )
        self.baza = Baza(self.Dane.ui.lineEdit_baza.text())
        self.baza.utworz_kopie('kopia_formyOchrony')

    def poprawne_fo(self):
        """Metoda grupujaca wszystkie sprawdzenia danych i bazy dla fo"""
        spr = [
            self.spr_fo_popr,
            self.spr_fo_pola,
            self.spr_fo_typy,
            self.spr_fo_baza,
        ]

        for s in spr:
            tt = s
            if not tt():
                if self.baza.con:
                    self.baza.zamknij()
                QgsMessageLog.logMessage(
                        'Nic nie dopisano do bazy\n---[   Koniec   ]---\n\n\n',
                        'Las-R')
                return False

        QgsMessageLog.logMessage(
            'Dane w warstwie i w bazie są zgodne, dopisuję!',
            'Las-R',
            Qgis.Info
        )
        return True

    def wybierz_fo(self):
        """Metoda wybiera z warstwyw fo te ktore znajduja sie w zasiegu warstwy
        wydzieleń"""
        self.fo_si = QgsSpatialIndex(self.fo)
        ids = self.fo_si.intersects(self.wydz.extent())

        zapyt = QgsFeatureRequest().setFilterFids(ids)
        for f in self.fo.getFeatures(zapyt):
            self.fow.append(f)

        if len(self.fow) == 0:
            self.iface.messageBar().pushMessage(
                'formy ochrony',
                'Brak form ochrony na terenie obiektu',
                Qgis.Warning,
                10
            )
            return False
        else:
            self.wyb_fo_trig = True
            return True

    def wybierz_wydz(self):
        """Metoda wybiera na podstawie wybranych fo wydzielenia, ktore sie z
        nimi przecinaja majacych powierzchnie wieksza niz 50%"""

        if not self.wyb_fo_trig:
            return False
        self.wydz_si = QgsSpatialIndex(self.wydz.getFeatures())
        for fo_item in self.fow:
            ids = self.wydz_si.intersects(fo_item.geometry().boundingBox())
            req = QgsFeatureRequest().setFilterFids(ids)
            for f in self.wydz.getFeatures(req):
                if fo_item.geometry().intersects(f.geometry()):
                    inter = fo_item.geometry().intersection(f.geometry())

                    # jezeli pow przeciecia wieksza niz 50% dodajemy
                    if (inter.area()/f.geometry().area()) > 0.49999:
                        if fo_item.id() not in self.sl:
                            self.sl[fo_item.id()] = [f['ADR_LES']]
                        self.sl[fo_item.id()].append(f['ADR_LES'])

    def dopisz_do_bazy(self):
        """Metoda dopisuje do wskazanej bazy taksatora wybrane wydzielenia i
        formy ochrony przyrody"""

        sl_wydz_int = self.baza.pobierz_wydzielenia()
        akt_fo = ''
        num_fo = -1  # int_num (my_int_num) z tabeliF_LAND_PROTECT (F_SET)
        set_int = 0  # set_int_num z tabeli F_SET
        niedop_wydz = []  # lista adr_les niedopisanych do bazy
        for key in list(self.sl.keys()):
            if key != akt_fo:
                num_fo += 1
                fof = [x for x in self.fow if x.id() == key][0]
                sql = \
                    u'insert into F_LAND_PROTECT (PROTEC_AREA_CD, INT_NUM,' + \
                    'LAND_PROTECT_NAME, LAND_PROTECT_AREA) values ' + \
                    u'(\'{}\', {}, \'{}\', {})'.format(
                        fof['TYP'],
                        num_fo,
                        fof['NAZWA'],
                        int(fof.geometry().area()))
                try:
                    self.baza.wpisz(sql)
                except:  # nopep8
                    self.iface.messageBar().pushMessage(
                        'BAZA',
                        'Nie udało się dopisać form ochrony '
                        'do tabeli F_LAND_PROTECT',
                        Qgis.Critical,
                        10)
                    self.baza.zamknij()
                    return False

            for val in self.sl[key]:
                sql = u'insert into F_SET values ({}, {}, \'K\', {})'.format(
                    sl_wydz_int[val],
                    set_int,
                    num_fo
                )
                try:
                    self.baza.wpisz(sql)
                except:  # nopep8
                    niedop_wydz.append(val['ADR_LES'])
                set_int += 1

        if len(niedop_wydz) > 0:
            self.iface.messageBar().pushMessage(
                'BAZA',
                'Nie udało się dopisać form ochrony do tabeli F_LAND_PROTECT'
                ' (Patrz log)',
                Qgis.Warning,
                10)

            QgsMessageLog.logMessage(
                'Niedopisane wydzielenia w formach ochrony: \n'
                '\n'.join(niedop_wydz),
                'Las-R',
                Qgis.Warning
            )

        self.iface.messageBar().pushMessage(
            'OK',
            'Dopisano formy ochrony (Patrz log)',
            Qgis.Success,
            10)

        QgsMessageLog.logMessage(
            '\nDopisano form ochrony: ' + str(num_fo+1) + '\n'
            'Dopisano wydzieleń z formami ochrony: ' + str(set_int) +
            '\n---[ KONIEC ]---',
            'Las-R',
            Qgis.Info
        )

    def spr_fo_popr(self):
        if not self.wydz.isValid() or not self.fo.isValid():
            wyps = ''
            if not self.fo.isValid():
                wyps += 'formy ochrony'

            self.iface.messageBar().pushMessage(
                wyps,
                'Nie mogę otworzyć warstwy do odczytu',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_fo_pola(self):
        braki = []
        for x in ['TYP', 'NAZWA']:
            if x not in self.fo.dataProvider().fieldNameMap():
                braki.append(x)

        if len(braki) > 0:
            self.iface.messageBar().pushMessage(
                'formy ochrony',
                'Brak wymaganych kolumn w warstwie ['+', '.join(braki)+']',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_fo_baza(self):
        if self.baza.dopisane_fo():
            self.iface.messageBar().pushMessage(
                'BAZA',
                'W bazie znajdują się już dopisane formy ochrony!',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_fo_typy(self):
        """Metoda sprawdza czy typy form ochrony w warstwie sa zgodne z tymi
            ze słownika we wskazanej bazie"""
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                               ).setSubsetOfAttributes(
                                                   ['TYP'],
                                                   self.fo.fields()
                                               )
        typy_w = set([x['TYP'] for x in self.fo.getFeatures(request)])
        typy_b = set(list(self.baza.pobierz_sl_fo().keys()))

        if typy_w.issubset(typy_b):
            return True

        self.iface.messageBar().pushMessage(
            'formy ochrony',
            'Typy form ochrony w shp, nie są zgodne ze słownikiem w bazie',
            Qgis.Critical,
            10)
        return False


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
        self.ui.pushButton_fochr.clicked.connect(self.kat_fochr)

        # debug
        # self.ui.lineEdit_baza.setText(
        #   r'e:\UPUL\__szablon\RDOS\aleksandrow.mdb')
        # self.ui.lineEdit_fochr.setText(r'e:\UPUL\__szablon\RDOS\F_OCHRONY.shp')
        # self.ui.lineEdit_wydz.setText(r'e:\UPUL\__szablon\RDOS\WYDZ_POL.shp')

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if os.path.isfile(self.ui.lineEdit_wydz.text()) and \
                os.path.isfile(self.ui.lineEdit_baza.text()) and \
                os.path.isfile(self.ui.lineEdit_fochr.text()):
            self.valid = True
            self.porzucone = False
            self.hide()
        else:
            msbx = QMessageBox(
                'Nie udało się odnaleźć wszystkich podanych plików!')
            msbx.exec_()

    def kat_baza(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż baze Taksatora',
                                           self.kat,
                                           "Access MDB (*.mdb)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_baza.setText(sc)

    def kat_warstwa(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż warstwę wydzielen',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_wydz.setText(sc)

    def kat_fochr(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż warstwę form ochrony',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_fochr.setText(sc)


if __name__ == '__console__':
    a = DopiszFO()
    a.pobierz_dane_od_uzytkownika()
