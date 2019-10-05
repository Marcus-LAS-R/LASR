import os
from PyQt5.QtWidgets import QFileDialog, QDialog, QMessageBox
from qgis.core import QgsVectorLayer, QgsProject, Qgis, QgsSpatialIndex, \
    QgsMessageLog

from .baza_wrapper import znajdz_baze_do_wydz, Baza
from .sprawdzenia_warstw import SprawdzWydzielenia
from .ui.ui_baza_dopisz_pnsw import Ui_Ui_Dialog as Ui_Dialog
from .funkcje import isNone


class DopiszPnsw(SprawdzWydzielenia):
    def __init__(self, iface):
        self.iface = iface
        self.feat_do_spr = []  # tabela z featurkami przecinajacymi wydzielenia
        self.pnsw_podm = 0  # liczba pnsw z dociętą grafiką do wydzielen
        self.wpis = []  # tabela z rekordami do wpisania do bazy

        # tablica z wpisami których nie udało się dopisać do bazy danych
        self.bledy_wpisywania = []

        # sl z kodami w shp i przetłumaczonymi na kody w bazie
        self.sl_baza = {
            "Bg": "BAGNO",
            "dL": "D LUKA",
            "dP": "D PRZEZ",
            "G": "GNIA",
            "K": 'KĘPA',
            "L": "LUKA",
            "Pł": 'POL ŁOW',
            "Rm": "REMIZA",
            "Sz": "SZK",
            "Go": "OD GNIA",
            "Gcz": "GNIA CZ",
            "Gocz": "OD G CZ"
        }

        self.sl_woj = {
                "D": "02",
                "C": "04",
                "L": "06",
                "F": "08",
                "E": "10",
                "K": "12",
                "W": "14",
                "O": "16",
                "R": "18",
                "B": "20",
                "G": "22",
                "S": "24",
                "T": "26",
                "N": "28",
                "P": "30",
                "Z": "32",
                }

    def wczytaj_dane(self):
        """ metoda pobiera od użytkownika informacje na temat warstwy wydz i
        pnsw, oraz bazy taksatora, do której mają zostać dopisane dane o pnsw
        Na podstawie danych pobranych o użytkownika sprawdzamy czy w
        warstwie wydz jest jedna z kolumn ADR_LES, ADR_BDL a w PNSW:
            KOD_PNSW, NR_PNSW, POW_GRAF.
        Sprawdzenie dotyczy również bazy, wypełnienia tabeli F_AROD_SPEC_AREA
        ( ma być pusta )
        """

        # policz czy w TOC jest po jednej warstwie z LS i WYDZ
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        pnsw = [x for x in lyrs if x.name()[:4].upper() == 'PNSW']
        wydz = [x for x in lyrs if x.name()[:4].upper() == 'WYDZ']

        try:
            self.pnsw = pnsw[0]
            self.pnsw.dataProvider().setEncoding('UTF-8')
            pnsw_sc = self.pnsw.dataProvider().dataSourceUri().split("|")[0]
        except:  # nopep8
            pnsw_sc = False

        try:
            self.wydz = wydz[0]
            # self.wydz.dataProvider().setEncoding('UTF-8')
            wydz_sc = self.wydz.dataProvider().dataSourceUri().split("|")[0]

            # znajdz bazę do danych jeżeli wydzielenia są ok
            baza_sc = znajdz_baze_do_wydz(self.iface, wydzlyr=self.wydz)
        except:  # nopep8
            wydz_sc = False
            baza_sc = False

        self.pobierz_dane = PobierzDane(wydz_sc, pnsw_sc, baza_sc)
        self.pobierz_dane.exec_()

        if self.pobierz_dane.porzucone:
            return False

        self.wydz = QgsVectorLayer(self.pobierz_dane.ui.lineEdit_wydz.text(),
                                   'wydz', 'ogr')
        self.pnsw = QgsVectorLayer(self.pobierz_dane.ui.lineEdit_pnsw.text(),
                                   'pnsw', 'ogr')

        self.baza = Baza(self.pobierz_dane.ui.lineEdit_baza.text())

        # sprawdz niezbedne pola w poszczegolnych warstwach
        if 'ADR_LES' not in [x.name() for x in
                             self.wydz.dataProvider().fields().toList()]:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Brak kolumny ADR_LES w warstwie WYDZ - ',
                Qgis.Critical,
                0
            )
            return False

        self.fnm = self.pnsw.dataProvider().fieldNameMap()
        pnsw_niez_pola = [x for x in self.fnm.keys() if x in
                          ['NR_PNSW', 'KOD_PNSW', 'POW_GRAF', 'ADR_BDL']]
        if 4 != len(pnsw_niez_pola):
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'W warstwie PNSW brakuje którejś z kolumn: NR_PNSW, KOD_PNSW,'
                ' POW_GRAF, ADR_BDL. Odnaleziono: [' +
                ', '.join(pnsw_niez_pola)+']',
                Qgis.Critical,
                0
            )
            return False

        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Nie mogę się połączyć z bazą!',
                Qgis.Critical,
                0
            )
            return False
        # sprawdz czy w bazie nie ma juz dopisanych pnsw
        if len(self.baza.pobierz_pnsw()) > 0:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'W Bazie znajdują się już dopisane PNSW - proszę je usunąć.',
                Qgis.Critical,
                0
            )
            return False

        return True

    def sprawdz_pnsw(self):
        """Metoda sprawdza czy każdy PNSW leży przynajmniej w 95% na jednym
        wydzieleniu, jeżeli tak pozostawia dociętą największą część i zwraca
        True. Jeżeli PNSW leży na różnych wydz, to użytkownik musi zadecydować
        którą część zostawić i ponownie uruchomić skrypt
        """

        if not self.poprawne_wydz():
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błędy')
            message.setText(
                'Czy chcesz kontynuować pomimo odnalezionych błędów? \n'
                'Najprawdopodobniej coś się wysypie')
            message.addButton("Porzuć", QMessageBox.ActionRole)
            message.addButton("Kontynuuj", QMessageBox.ActionRole)
            kont = message.exec_()

            if kont != 1:
                return False

            self.baza.polacz()

        # spatial index dla wydzieleń
        self.si = QgsSpatialIndex()
        self.sl_wydz = {}  # sl z wydz {id: feat}
        self.sl_id = {}  # sl z wydz {adr_les: id}

        for fw in self.wydz.getFeatures():
            self.si.insertFeature(fw)
            self.sl_wydz[fw.id()] = fw

        # sprawdz nakładanie dla PNSW
        for pnsw in self.pnsw.getFeatures():

            if isNone(pnsw['KOD_PNSW']) not in self.sl_baza:
                self.iface.messageBar().pushMessage(
                    'BŁĄD', 'Źle zakodowane PNSW --> kody do poprawy',
                    Qgis.Critical)
                return False

            geom = pnsw.geometry()
            ids = self.si.intersects(geom.boundingBox())
            for id in ids:
                inter = self.sl_wydz[id].geometry().intersection(geom)
                if inter.area() / geom.area() >= 0.999:
                    # jeżeli podmieniamy geometrię wpisujemy też rozpoznany adr
                    self.pnsw.startEditing()
                    self.pnsw.dataProvider().changeAttributeValues({
                        pnsw.id(): {self.fnm['ADR_BDL']:
                                    self.sl_wydz[id]['ADR_LES']}
                    })
                    self.pnsw.commitChanges()
                    break

                elif inter.area() / geom.area() < 0.2:
                    pass

                elif 0.999 > (inter.area() / geom.area()) >= 0.2:
                    self.feat_do_spr.append(pnsw)

                else:
                    self.feat_do_spr.append(pnsw)

        if len(self.feat_do_spr) > 0:
            wyps = 'W warstwie PNSW znajdują się poligony przecinające ' + \
                'wydzielenia. Sprawdź błędy w dodanej warstwie!'
            if self.pnsw_podm > 0:
                wyps += ' PNSW z przyciętą grafiką do wydz: ' + \
                    str(self.pnsw_podm)
            self.iface.messageBar().pushMessage("BŁĄD", wyps, Qgis.Critical, 0)
            self.pokaz_bledy()
            return False

        return True

    def pokaz_bledy(self):
        bledy = QgsVectorLayer("MultiPolygon?crs=epsg:2180&index=yes",
                               "PNSW_błędy_przecinania",
                               "memory"
                               )

        bledy.startEditing()
        bledy.dataProvider().addAttributes(
            self.pnsw.dataProvider().fields().toList())
        bledy.updateFields()
        bledy.dataProvider().addFeatures(self.feat_do_spr)
        bledy.commitChanges()
        QgsProject.instance().addMapLayer(bledy)

    def przygotuj_wpis(self):
        """ Metoda uzupełnia w warstwie dla każdego PNSW adres leśny, nr_pnsw
        w bazie, pow pnsw i przygotowuje tablicę, która zostanie wpisana do
        bazy taksatora
        """

        f_arod = self.baza.pobierz_wydzielenia()
        nump = {}  # sl z numerem pnsw w każdym wydz od 1

        for p in self.pnsw.getFeatures():
            geom = p.geometry()
            ids = self.si.intersects(geom.boundingBox())
            wydz = False
            for id in ids:
                inter = self.sl_wydz[id].geometry().intersection(geom)
                if inter.area() / geom.area() >= 0.99:
                    wydz = self.sl_wydz[id]
                    break

            if wydz is not False:
                if wydz['ADR_LES'] not in nump:
                    nump[wydz['ADR_LES']] = 0
                nump[wydz['ADR_LES']] += 1

                # stworz wpis do bazy dla tego PNSW
                wpis = [
                    f_arod[wydz['ADR_LES']],
                    nump[wydz['ADR_LES']],
                    self.sl_baza[p['KOD_PNSW']],
                    self.polozenie_pnsw(p, wydz),
                    round(p.geometry().area()/10000, 4),
                ]

                # uzupełnij warstwę PNSW
                self.pnsw.dataProvider().changeAttributeValues({
                    p.id(): {
                        self.fnm['NR_PNSW']: nump[wydz['ADR_LES']],
                        self.fnm['POW_GRAF']:
                            round(p.geometry().area()/10000, 4),
                        self.fnm['ADR_ADM']: '-'.join(
                            [self.sl_woj[wydz['ADR_LES'][0]],
                             wydz['ADR_LES'][1:3],
                             wydz['ADR_LES'][3:6],
                             wydz['ADR_LES'][6:10],
                             ]),
                    }
                })

                self.wpis.append(wpis)

    def dopisz_do_bazy(self):
        """ Dopisanie do bazy tablicy pnsw """
        for wpis in self.wpis:
            sql = '''
                INSERT INTO F_AROD_SPEC_AREA
                    (ARODES_INT_NUM,
                     AROD_SPAREA_ORDER,
                     SPECIAL_AREA_CD,
                     LOCATION_CD,
                     SPECIAL_AREA,
                     SPECIAL_AREA_NUM)
                VALUES ( ''' + \
                str(wpis[0]) + ', ' + \
                str(wpis[1]) + ', \'' + \
                str(wpis[2]) + '\', \'' + \
                str(wpis[3]) + '\', ' + \
                str(wpis[4]) + \
                ''', 1);'''

            if not self.baza.wpisz(sql):
                self.bledy_wpisywania.append(wpis)

    def wyswietl_info(self):
        if len(self.bledy_wpisywania) > 0:
            self.iface.messageBar().pushMessage(
                'BŁĘDY',
                'Nie udało się wpisać do bazy: ' +
                str(len(self.bledy_wpisywania)) + ' PNSW, patrz log Las-R',
                Qgis.Warning,
                15
            )

            QgsMessageLog.logMessage(
                'Aaa coś niewyraźnie ta baza zeznaje, sprawdź jeszcze raz '
                'warstwę PNSW...',
                'Las-R'
            )
            return

        self.iface.messageBar().pushMessage(
            'OK',
            'Wpisałem do bazy: ' + str(len(self.wpis)) + ' / ' +
            str(self.pnsw.featureCount()) + ' PNSW',
            Qgis.Success,
            10
        )

    def polozenie_pnsw(self, pnsw, wydz):
        """ Metoda zwraca literki z położeniem pnsw w wydz """
        wys = wydz.geometry().boundingBox().height()
        szer = wydz.geometry().boundingBox().width()
        wys3 = wys / 3
        szer3 = szer / 3
        pb = pnsw.geometry().boundingBox()
        wb = wydz.geometry().boundingBox()

        # zachodnie kwadraty
        if pb.xMaximum() < wb.xMinimum() + szer3:
            if pb.yMaximum() < wb.yMinimum() + wys3:
                return 'SW'
            elif pb.yMinimum() > wb.yMaximum() - wys3:
                return 'NW'
            else:
                return 'W'

        # wschodnie kwadraty
        if pb.xMinimum() > wb.xMaximum() - szer3:
            if pb.yMaximum() < wb.yMinimum() + wys3:
                return 'SE'
            elif pb.yMinimum() > wb.yMaximum() - wys3:
                return 'NE'
            else:
                return 'E'

        if pb.yMinimum() > wb.yMaximum() - wys3:
            return 'N'
        if pb.yMaximum() < wb.yMinimum() + wys3:
            return 'S'

        return 'C'


class PobierzDane(QDialog):
    def __init__(self, wydz=False, pnsw=False, baza=False):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # katalog który będzie uzupełniony po pierwszym wskazaniu warstwy, bazy
        self.kat = ''

        # wartosc True jezeli uzytkownik zrezygnowal z przetwarzania
        self.porzucone = True

        # wpisz sciezki do przekazanych warstw i bazy
        if wydz:
            self.ui.lineEdit_wydz.setText(wydz)
        if pnsw:
            self.ui.lineEdit_pnsw.setText(pnsw)
        if baza:
            self.ui.lineEdit_baza.setText(baza)

        # trigger do sprawdzenia poprawnosci wpisanych danych przez
        # uzyszkodnika
        self.valid = False

        # sygnały
        self.ui.pushButton_ok.clicked.connect(self.sprawdz_ok)
        self.ui.pushButton_cancel.clicked.connect(self.porzuc)
        self.ui.pushButton_baza.clicked.connect(self.kat_baza)
        self.ui.pushButton_wydz.clicked.connect(self.kat_warstwa)
        self.ui.pushButton_pnsw.clicked.connect(self.kat_fochr)

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if os.path.isfile(self.ui.lineEdit_wydz.text()) and \
                os.path.isfile(self.ui.lineEdit_baza.text()) and \
                os.path.isfile(self.ui.lineEdit_pnsw.text()):
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
                                           'Wskaż warstwę wydzieleń',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_wydz.setText(sc)

    def kat_fochr(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż warstwę PNSW',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_pnsw.setText(sc)
