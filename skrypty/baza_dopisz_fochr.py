import os
from qgis.core import QgsVectorLayer, Qgis, QgsMessageLog, QgsSpatialIndex, \
    QgsFeatureRequest
from PyQt5.QtWidgets import QFileDialog, QDialog, QMessageBox

from .baza_wrapper import Baza
from ..ui.ui_baza_dopiszFO import Ui_Dialog


class DopiszFO(object):
    def __init__(self, iface):
        self.iface = iface

        # slownik z powierzchniami wydzielen przecinajacych sie z FO
        self.sl = {}
        self.fow = []  # features wybranych form ochrony przyrody
        self.fo_si = QgsSpatialIndex()  # SI wszystkich form ochrony przyrody
        self.wydz_si = QgsSpatialIndex()  # SI wszystkich wydzielen

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

    def sprawdz_all(self):
        """Metoda grupujaca wszystkie sprawdzenia danych i bazy"""
        spr = [
            self.spr_warstwy,
            self.spr_pola,
            self.spr_baza_polacz,
            self.spr_baza_fo,
            self.spr_wydz_baza,
            self.spr_typy_fo,
        ]

        for s in spr:
            tt = s
            if not tt():
                self.baza.zamknij()
                return False

        QgsMessageLog.logMessage(
            'Dane w warstwie i w bazie są zgodne, dopisuję!',
            'LasR',
            Qgis.Info
        )
        return True

    def wybierz_fo(self):
        """Metoda wybiera z warstwyw fo te ktore znajduja sie w zasiegu warstwy
        wydzieleń"""
        self.fo_si = QgsSpatialIndex(self.fo)
        ids = self.fo_si.intersects(self.wydz.extent())

        zapyt = QgsFeatureRequest().setFilter(ids)
        for f in self.wydz.getFeatures(zapyt):
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
            return True

    def spr_warstwy(self):
        if not self.wydz.isValid() or not self.fo.isValid():
            wyps = ''
            if not self.wydz.isValid():
                wyps = 'wydzielenia, '
            if not self.fo.isValid():
                wyps += 'formy ochrony'

            self.iface.messageBar().pushMessage(
                wyps,
                'Nie mogę otworzyć warstwy do odczytu',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_pola(self):
        if 'ADR_LES' not in self.wydz.dataProvider().fieldNameMap():
            self.iface.messageBar().pushMessage(
                'Wydzielenia',
                'Brak kolumny ADR_LES w warstwie',
                Qgis.Critical,
                10)
            return False

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

    def spr_baza_polacz(self):
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                'BAZA',
                'Nie udało się połączyć ze wskazaną bazą!',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_baza_fo(self):
        if self.baza.dopisane_fo():
            self.iface.messageBar().pushMessage(
                'BAZA',
                'W bazie znajdują się już dopisane formy ochrony!',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_wydz_baza(self):
        adr_w = [x['ADR_LES'] for x in self.wydz.getFeatures()]
        adr_b = self.baza.pobierz_wydzielenia()
        braki = [x for x in adr_w if x not in adr_b]

        QgsMessageLog.logMessage(
            'Znaleziono poligonów w shp: ' + str(len(adr_w)),
            'LasR',
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            'Znaleziono wydzieleń w shp: ' + str(len(set(adr_w))),
            'LasR',
            Qgis.Info
        )
        QgsMessageLog.logMessage(
            'Znaleziono wydzieleń w bazie: ' + str(len(adr_b)),
            'LasR',
            Qgis.Info
        )

        if len(braki) > 0:
            self.iface.messageBar().pushMessage(
                'BAZA',
                'W shp znajdują się wydzielenia, które nie są dopisane do ' +
                'Bazy! Patrz log LasR',
                Qgis.Critical,
                10)

            QgsMessageLog.logMessage('Brakujące wydzielenia w bazie:',
                                     'LasR',
                                     Qgis.Critical)
            for b in braki:
                QgsMessageLog.logMessage(b, 'LasR', Qgis.Critical)
            return False
        return True

    def spr_typy_fo(self):
        """Metoda sprawdza czy typy form ochrony w warstwie sa zgodne z tymi
            ze słownika we wskazanej bazie"""
        typy_w = set([x['TYP'] for x in self.fo.getFeatures()])
        typy_b = set(list(self.baza.pobierz_sl_fo().keys()))

        if typy_w.issubset(typy_b):
            return True

        self.iface.messageBar().pushMessage(
            'BAZA',
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
        self.porzucone = False

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
        self.ui.lineEdit_baza.setText(
            r'e:\UPUL\__szablon\RDOS\aleksandrow.mdb')
        self.ui.lineEdit_fochr.setText(r'e:\UPUL\__szablon\RDOS\F_OCHRONY.shp')
        self.ui.lineEdit_wydz.setText(r'e:\UPUL\__szablon\RDOS\WYDZ_POL.shp')

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if os.path.isfile(self.ui.lineEdit_wydz.text()) and \
                os.path.isfile(self.ui.lineEdit_baza.text()) and \
                os.path.isfile(self.ui.lineEdit_fochr.text()):
            self.valid = True
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
        self.kat = os.path.dirname(sc)
        self.ui.lineEdit_baza.setText(sc)

    def kat_warstwa(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż warstwę wydzielen',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        self.kat = os.path.dirname(sc)
        self.ui.lineEdit_wydz.setText(sc)

    def kat_fochr(self):
            sc = QFileDialog().getOpenFileName(self,
                                               'Wskaż warstwę form ochrony',
                                               self.kat,
                                               "ESRI Shapefile (*.shp)")[0]
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_wydz.setText(sc)


if __name__ == '__console__':
    a = DopiszFO()
    a.pobierz_dane_od_uzytkownika()
    a.testuj()
