import os
import glob
from datetime import datetime
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QVariant
from qgis.core import QgsSpatialIndex, QgsField, QgsFeature, \
    QgsCoordinateReferenceSystem, QgsVectorLayer, \
    QgsMessageLog, QgsProject, QgsWkbTypes
import processing
from collections import Counter, namedtuple, defaultdict
from .baza_wrapper import Baza
from .baza_przetworz import Przetworz
from ..ui.ui_sprawdz_ls import Ui_Dialog


class recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)


class SprawdzLs(object):
    def __init__(self, i):
        self.iface = i
        k = False
        d = False

        # sprawdz czy uzyszkodnik zaznaczyl warstwe
        try:
            k = self.iface.activeLayer()
        except:  # nopep8
            QgsMessageLog.logMessage('Nie zaznaczono warstwy w TOC!', 'LasR')

        for key, lyr in QgsProject.instance().mapLayers().items():
            if key[:5] == 'DZKAT':
                d = lyr

        self.a = AnalizujKlus(self.iface, k, d)

    def wczytaj(self):
        self.a.pobierz_dane_od_uzytkownika()
        self.a.przetworz()

    def sprawdz(self):
        if self.a.sprawdz_warunki():
            return False

    def przygotuj(self):
        self.a.przygotuj_tabele()
        self.a.przygotuj_do_analizy()


class AnalizujKlus(object):
    def __init__(self, i, k, d):
        self.iface = i
        self.klu = k
        self.dzkat = d

        self.indeks = False
        self.lyrw = False  # warstwa wyjsciowa
        self.bledy_topo = []  # lista feats, ktore przecinaja sie z innymi
        self.iatr = False  # indeks pól w warstwie wyjsciowej
        self.county = ''  # kod wojewodztwa
        self.district = ''  # kod powiatu
        self.dz_nieles = []  # lista dzialek nielesnych

        self.indeks = QgsSpatialIndex()
        self.sf = {}  # slownik z singleparts features w postaci{id: feature, }
        self.sl_sf_na_dzkat = {}  # slownik {PARCELID: [id1, id2, ..]}

        self.czas = datetime.now().isoformat(
                        ).replace(":", "")[:-7].replace('-', '')

        self.kolumny_dz = [
            QgsField("COUNTY", QVariant.String, len=2),
            QgsField("DISTRICT", QVariant.String, len=2),
            QgsField("MUNICIP", QVariant.String, len=3),
            QgsField("COMMUNITY", QVariant.String, len=4),
            QgsField("PARCELNR", QVariant.String, len=20),
            QgsField("PARCELID", QVariant.String, len=50),
            QgsField("GRP", QVariant.String, len=2),
            QgsField("ARK", QVariant.String, len=12),
            QgsField("NIELES", QVariant.String, len=3),
            QgsField("UWAGI", QVariant.String, len=150),
            QgsField("PARCEL_AR", QVariant.Double, "double", 10, 4),
            QgsField("PARCEL_POW", QVariant.Double, "double", 10, 4),
        ]

        self.kolumny_ls = [
            QgsField("AU", QVariant.String, len=10),
            QgsField("SQ", QVariant.String, len=10),
            QgsField("SPRAWDZ", QVariant.String, len=150),
            QgsField("LANDID", QVariant.String, len=50),
            QgsField("LAND_AR", QVariant.Double, "double", 10, 4),
            QgsField("LAND_POW", QVariant.Double, "double", 10, 4),
        ]

    def pobierz_dane_od_uzytkownika(self):
        self.dd = PobierzDane(self.lyr)
        self.dd.exec_()

    def przetworz(self):
        if not self.klu.isValid():
            self.klu = QgsVectorLayer(self.dd.lineEdit_klu, 'klu', 'ogr')
        if not self.dzkat.isValid():
            self.dzkat = QgsVectorLayer(self.dd.lineEdit_dz, 'dz', 'ogr')

        self.bazy = glob.glob(
            os.path.join(self.dd.ui.lineEdit_bazy.text(),
                         '*.mdb'))
        self.typ = self.dd.ui.comboBox_ident.currentText()[:3]
        self.wl = self.dd.ui.comboBox_wlas.currentText()[:2]
        self.landid = self.dd.ui.comboBox_landid.currentText()
        self.sq = self.dd.ui.comboBox_sq.currentText()
        self.au = self.dd.ui.comboBox_au.currentText()

        # Pobierz dane z baz danych
        self.uzytki = []
        self.wlasnosci = []

        QgsMessageLog.logMessage(
            'Znaleziono bazy: '+', '.join(self.bazy),
            "Las-R"
        )
        for baza in self.bazy:
            b = Baza(baza)
            if b.polacz():
                self.uzytki += b.uzytki()
                self.wlasnosci += b.wlasnosci()
            else:
                QgsMessageLog.logMessage(
                    'Nie udało połączyć się z: ' + baza,
                    "Las-R"
                )
                self.iface.messageBar.pushWarning(
                    'Uwaga',
                    'Nie udało się odczytać bazy: ' +
                    baza
                )

    def przygotuj_tabele(self):
        self.p = Przetworz()
        self.p.dodaj_uzytki(self.uzytki)
        self.p.dodaj_wlasnosci(self.wlasnosci)
        self.p.przetworz_dzialki()
        self.p.przetworz_uzytkowanie()

    def sprawdz_warunki(self):
        """Sprawdz czy warstwy maja odpowiednie struktury"""
        if not self.klu.isValid() or not self.dzkat.isValid():
            return False

        if [x.name() for x in self.dzkat.dataProvider().fields()] not in \
                self.kolumny_dz:
            return False

        return True

    def przygotuj_do_analizy(self):
        """ W zaleznosci od wyboru uzytkownika robimy dissolve po au i sq albo
        LANDID. W drugim przypadku dodajemy brakujace pola sq i au,
        uzupelniamy je ze slownika i kontynuujemy sciezke programu"""

        # jezeli wybrano LANDID
        if self.typ == 'LAN':
            pola = [x.name() for x in self.klu.dataProvider().fields()]
            pola_dodaj = []
            if 'SQ' not in pola:
                pola_dodaj.append(QgsField("SQ", QVariant.String, len=10))
            if 'AU' not in pola:
                pola_dodaj.append(QgsField("AU", QVariant.String, len=10))

            self.sq = 'SQ'
            self.au = 'AU'

            if len(pola_dodaj) > 0:
                self.klu.startEditing()
                attr = self.klu.dataProvider().fields().toList()
                self.klu.addAttributes(attr+pola_dodaj)
                self.klu.updateFields()
                self.klu.commitChanges()

            self.klu.startEditing()
            iau = self.klu.fieldNameIndex('AU')
            isq = self.klu.fieldNameIndex('SQ')
            for f in self.klu.getFeatures():
                if f['LANDID'] in self.p.uzytki:
                    zsq = self.p.uzytki[f['LANDID']][1]
                    zau = self.p.uzytki[f['LANDID']][0]
                else:
                    zsq = 'xxx'
                    zau = 'xxx'
                self.klu.changeAttributeValue(f.id(), iau, zau)
                self.klu.changeAttributeValue(f.id(), isq, zsq)
            self.klu.commitChanges()

        sciezka = self.klu.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        processing.run("native:dissolve", {
                        'INPUT': self.klu.name(),
                        'FIELD': [self.au, self.sq],
                        'OUTPUT': os.path.join(self.kat, 'klu_dissolve.shp')
        })

        processing.run("native:intersection", {
                        'INPUT': self.klu,
                        'OVERLAY': self.dzkat,
                        'INPUT_FIELDS': "",
                        'OVERLAY_FILEDS': "",
                        'OUTPUT': os.path.join(
                            self.kat, 'LS_multiparts_'+self.czas+'.shp'
                        )
        })

        processing.run("native:multiparttosingleparts", {
                        'OUTPUT': os.path.join(
                            self.kat, 'LS_singleparts_'+self.czas+'.shp'),
                        'INPUT': os.path.join(
                            self.kat, 'LS_multiparts_'+self.czas+'.shp')
                        })

        # Rozbij uzytki na single parts
        self.singleparts = QgsVectorLayer(os.path.join(
            self.kat, 'LS_singleparts'+self.czas+'.shp'),
            'Ls_singleparts_'+self.czas+'.shp',
            'ogr')


class PrzetworzKlu(object):
    def __init__(self, d, k, p):
        # d-feature z analizowana dzialka i struktura pol zgodna ze skryptem
        # k-tablica z featurami klu na tej dzialce, wszystkie musza byc
        # przykryte przez poligon dzialki, oraz byc singlepart
        self.dz = d
        self.klus = k
        # wskaznik do slownikow na podstawie bazy
        self.p = p

        # nazwy pol przetrzymujacych uzytki
        self.sq = 'SQ'
        self.au = 'AU'

        # PARCELID wyciagniety z dzialki w metodzie przetworz
        self.pid = ''

        # slownik z uzytkami na dzialce i zsumowanymi powierzchniami, obliczany
        # w metodzie przetworz
        # sl = {LANDID: 4,3222, LANDID: 0.0002, ....}
        self.klus_pow = {}

        # slownik z featurami pogrupowanymi po LANDID, w postaci:
        # obliczany w metodzie przetworz
        # sl = {LANDID: [f1, f2, f3], LANDID2: [f4, f5,...],}
        self.klus_grupy = {}

        # poprawne klu
        self.klus_popr = []
        self.klus_bledy = []  # tabel z featurami sklasyfikowanymi jako bledy
        self.klus_do_spr = []  # lista z featurami do sprawdzenia

        # tabela z rozbieznosciam powierzchniowymi, w postaci [LANDID, LANDID]
        self.rozb_pow = []

        # tabela z brakujacymi ls na dzialce, wg bazy,
        # w postaci [LANDID, LANDID]
        self.braki = []

        # tablica z uwagami do raportu, grupowana wg skrotow ponizej:
        # pow - rozbieznosc powierzchni miedzy baza a grafika
        # brakb - brak uzytku w bazie, jest w grafice
        # brakg - brak uzytku w grafice, jest w bazie
        # brakdzb - brak dzkat w bazie, jest w grafice
        # topo - bledy topologiczne do rozwiazania przez uzytkownika
        # mikro - mikrolsy do usuniecia przez uzytkownika
        # dubb - zdublowane ls, klu w bazie
        # dubg - zdublowane ls, klu w grafice
        # podm - ls z podmieniona grafika na kontur z dzialki (tylko przy 1 ls)
        # op - dzialka tylko z wlasnoscia OP
        # opif - dzialka tylko z wlasnoscia OPiF
        #
        # postac zapisu:
        # {'mikro': {landid: [0.0001], landid: [0.0021]},
        #  'podm': {landid: [0.5894, 0.7842], ....},
        #  }
        self.uwagi = recursivedefaultdict()

        # True jezeli na dzialce nie ma zadnych klu
        self.bez_uzytkow = False

    def nazwa_sq_au(self, s, a):
        self.sq = s
        self.au = a

    def is_valid(self):
        if self.dz.geometry().wkbType() not in [QgsWkbTypes.Polygon,
                                                QgsWkbTypes.Multipolygon]:
            return False

        if 'PARCELID' not in [x.name() for x in
                              self.dz.dataProvider().fields().toList()]:
            return False

        if ['PARCELID', self.sq, self.au] not in \
                [x.name() for x in self.klus[0].fields().toList()]:
            return False

        # jezeli na dzialce znajduja sie uzytki z innej dzialki
        if set(self.dz['PARCELID']) != set([x['PARCELID'] for x in self.klus]):
            return False

        return True

    def przetworz(self):
        self.pid = self.dz['PARCELID']

        # oblicz sumaryczna powierzchnie dla uzytku na dzialce, sumujac
        # wszystkie multipoligony
        if len(self.klus) == 0:
            self.bez_uzytkow = True
            return False

        self.klus_pow = {self.stworz_landid(x): 0
                         for x in self.klus}
        self.klus_grupy = {self.stworz_landid(x): [] for x in self.klus}
        for f in self.klus:
            self.klus_pow[self.stworz_landid(f)] += \
                round(f.geometry().area()/10000, 4)
            self.klus_grupy[self.stworz_landid(f)].append(f)

        return True

    def sprawdz_topologie(self):
        """Metoda sprawdza czy klu nakladaja sie na siebie, w przypadku gdy
        jeden z poligonow jest przykryty przez inny wiekszy, ten mniejszy
        jest klasyfikowany jako blad i przerzucany do warstwy bledow i pomijany
        w dalszej obrobce. Jezeli dwa poligony nachodza na siebie tylko troche
        ich czesc wspolna jest dodana do warstwy bledow jako do sprawdzenia"""

        if len(self.klus) < 2:
            return

        do_usuniecia = []
        for i in range(len(self.klus)-1):
            for j in range(i+1, len(self.klus)):
                if self.klus[i].geometry().intersects(self.klus[j].geometry()):
                    inter = self.klus[i].geometry().intersection(
                        self.klus[j].geometry())
                    if inter.area() == 0:
                        pass
                    else:
                        # powierzchnia przeciecie jest taka sama jak
                        # powierzchnia jednego z klu -> idzie do bledow
                        if inter.area() == self.klus[i].geometry().area() or \
                                inter.area() == self.klus[j].geometry().area():
                            if inter.area() == self.klus[i].geometry().area():
                                do_usuniecia.append(i)
                            if inter.area() == self.klus[j].geometry().area():
                                do_usuniecia.append(j)
                    # powierzchnia przeciecia jest taka sama jak powierzchnia
                    # obu klu
                        elif self.klus[i].geometry().area() == \
                                inter.area() and \
                                self.klus[j].geometry().area() == inter.area():
                            f = self.new_feat(
                                uw='nałożone identyczne poligony')
                            f.setGeometry(inter)
                            self.klus_do_spr(f)

        # usun z listy klus featurki sklasyfikowane jako bledy
        do_usuniecia = list(set(do_usuniecia)).sort(reverse=True)
        for i in do_usuniecia:
            f = self.new_feat(au=self.au, sq=self.sq,
                              uw='przykryty przez wiekszy')
            f.setGeometry(self.klus[i].geometry())
            self.klus_bledy.append(f)
            self.klus.remove(i)

    def s_wasy(self, f):
        """Metoda sprawdza czy w geometrii podanego featurka znajduja sie
        charakterystyczne 'wasy' ktore sa bledem topologicznym.
        Sprawdza czy pomiedzy dwoma lub trzema segmentami (krotki segm w srod.)
        odcinkiem nie wystepuje kat bliski 360 stopni +-5 stopni, jezeli tak,
        dodaj do warstwy wonsow"""
        if f.geometry().wkbType() == QgsWkbTypes.Polygon:
            linia = f.geometry().asPolygon()[0][0]
        if f.geometry().wkbType() == QgsWkbTypes.Multipolygon:
            linia = f.geometry().asMultiPolygon()[0][0]

        for i, pkt in enumerate(linia):
            if i == 0:
                pocz = linia[-3]
                sr = linia[-2]
                pocz1 = linia[-1]
            elif i == 1:
                pass
                # dodac sprawdzenie kata miedzy pierwszymi 2 pkt
            else:
                # sprawdzic kat miedzy
                pocz = linia[i-2]
                sr = linia[i-1]



    def s_czy_dz_w_bazie(self):
        if self.dz['PARCELID'] in self.p.sl_kody_wlasciceli_na_dzialce:
            return True

        # jezeli brak w bazie dopisz co trzeba do klu i zostaw jako poprawne
        self.braki['brakb'] = {self.stworz_landid(x):
                               self.p.uzytki[self.stworz_landid(x)][2]
                               for x in self.klus}
        for x in self.klus:
            f = self.new_feat(au=x[self.au], sq=x[self.sq], uw='Brak w bazie')
            f.setGeometry(x.geometry())
            self.klus_popr.append(f)
        return False

    def s_czy_ls_na_calosci(self):
        """Metoda sprawdza czy uzytek znajduje sie na calej dzialce, jest jeden
        w zbiorze uzytkow w bazie, jezeli tak to podmienia jego grafike na
        kontur dzialki"""

        if self.pid in self.p.sl_pow_ls_dzkat:
            if self.p[self.pid][0] == self.p[self.pid][1]:
                f = self.new_feat('Ls', self.p.sl_ls_na_dz[self.pid][0])
                f.setGeometry(self.dz.geometry())
                self.klus_popr.append(f)
                return True
        return False

    def s_czy_jeden_ls(self):
        """Metoda sprawdza czy w bazie jest jeden ls, jezeli tak, sprawdza czy
        na dzialce znajduje sie jeden ls o tej samej klasie"""
        if len(self.p.sl_ls_na_dz[self.pid]) == 1:
            # jezeli na dzialce jest tylko jedna klasa Ls dopisz i sparwdz topo
            if len([x for x in self.klus_pow.keys()
                    if x.split('.')[-1][:2] == 'Ls']) == 1:
                for k, val in self.klus.items():
                    pass

    def new_feat(self, au=False, sq=False, uw=False):
        f = QgsFeature()
        f.setFields([
            QgsField('PARCELID', QVariant.String, len=30),
            QgsField('AU', QVariant.String, len=10),
            QgsField('SQ', QVariant.String, len=10),
            QgsField('UWAGI', QVariant.String, len=230),
        ])
        f.setAttribure(f.fieldNameIndex('PARCELID'), self.pid)
        if au:
            f.setAttribure(f.fieldNameIndex('AU'), au)
        if sq:
            f.setAttribure(f.fieldNameIndex('SQ'), sq)
        if uw:
            f.setAttribure(f.fieldNameIndex('UWAGI'), uw)
        return f

    def stworz_landid(self, f):
        """metoda tworzy LANDID na podstawie danych podanego feature'a"""
        return f['PARCELID'] + '.' + f[self.au] + self.isNone(f[self.sq])

    def isNone(self, a):
        if a is None:
            return ''
        else:
            return a


class PobierzDane(QDialog):
    def __init__(self, k=False, d=False):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.lyrk = k
        self.lyrd = d
        self.pola = []
        self.ile_baz = 0
        self.ui.comboBox_ident.setDisabled(True)

        # Jezeli jest warstwa klu, odczytaj jej dane
        if self.lyrk:
            if self.lyrk.isValid():
                self.ui.lineEdit_klu.setText(
                    self.lyrk.dataProvider().dataSourceUri().split("|")[0])
                self.ui.comboBox_ident.setDisabled(False)
                self.wczytaj_pola()

        # Jezeli jest warstwa dzkat, odczytaj jej dane
        if self.lyrd:
            if self.lyrd.isValid():
                self.ui.lineEdit_klu.setText(
                    self.lyrd.dataProvider().dataSourceUri().split("|")[0])

        self.ui.pushButton_klu.clicked.connect(self.pobierz_klu)
        self.ui.pushButton_dzkat.clicked.connect(self.pobierz_dzkat)
        self.ui.pushButton_bazy.clicked.connect(self.pobierz_bazy)
        self.ui.comboBox_ident.currentTextChanged.connect(self.identyfikuj)

    def wczytaj_pola(self):
        """Metoda uzupelnia comboboxy na podstawie podanej warstwy"""
        # wybierz nazwy pol z warstwy, ktore nie sa numeryczne
        self.pola = ['---'] + [x.name() for x in self.lyrk.dataProvider(
                                    ).fields().toList() if not x.isNumeric()]

        # wyczysc wszystkie comboboxy z kolumnami
        comboboxy = [
            self.ui.comboBox_sq,
            self.ui.comboBox_au,
            self.ui.comboBox_landid,
        ]

        # wyczysc i dodaj przetworzone pola do comboboxow
        for x in comboboxy:
            x.clear()
            x.addItems(self.pola)

    def pobierz_klu(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę i ją przetwarza"""
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę',
                                                '',
                                                "ESRI shp (*.shp)")[0]
        try:
            self.lyrk = QgsVectorLayer(warstwa, "klu", "ogr")
            self.ui.lineEdit_klu.setText(
                self.lyrk.dataProvider().dataSourceUri().split("|")[0])
            self.ui.comboBox_ident.setDisabled(False)
        except:  # nopep8
            msbx = QMessageBox('Nie udało się otworzyć podanej warstwy')
            msbx.exec_()
            self.lyrk = False
            self.ui.comboBox_ident.setDisabled(True)

    def pobierz_dzkat(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę i ją przetwarza"""
        if self.lyrk:
            kat = os.path.dirname(
                self.lyrk.dataProvider().dataSourceUri().split("|")[0])
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę',
                                                kat,
                                                "ESRI shp (*.shp)")[0]
        try:
            self.lyrd = QgsVectorLayer(warstwa, "dz", "ogr")
            self.ui.lineEdit_dz.setText(
                self.lyrd.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            msbx = QMessageBox('Nie udało się otworzyć podanej warstwy')
            msbx.exec_()
            self.lyrd = False

    def pobierz_bazy(self):
        """Metoda pobiera wskazany przez użytkownika katalog"""
        kat = ""
        if self.lyrk:
            kat = os.path.dirname(self.lyrk.dataProvider().dataSourceUri(
                                                            ).split("|")[0])
        bazy_kat = QFileDialog().getExistingDirectory(
            self,
            "Katalog z bazami danych",
            kat)
        self.ile_baz = len(glob.glob(os.path.join(bazy_kat, '*.mdb')))
        if self.ile_baz > 0:
            self.ui.label_bazy.setText("Znalazałem baz: "+str(self.ile_baz))
            self.ui.lineEdit_bazy.setText(bazy_kat)

        else:
            self.ui.label_bazy.setText("Nie znaleziono baz *.mdb")

    def identyfikuj(self):
        """ Metoda sprawdza wybór uzytkownika i
            udostepnia odpowiednie pola do wyboru"""
        if self.ui.comboBox_ident.currentText() == '---':
            self.ui.groupBox_adradm.setDisabled(True)
            self.ui.groupBox_kol.setDisabled(True)
            self.ui.pushButton_ok.setDisabled(True)
        elif self.ui.comboBox_ident.currentText()[:3] == 'AU ':
            self.ui.groupBox_adradm.setDisabled(False)
            self.ui.pushButton_ok.setDisabled(False)
            self.ui.groupBox_kol.setDisabled(True)
        elif self.ui.comboBox_ident.currentText()[:3] == 'LAN':
            self.ui.groupBox_adradm.setDisabled(True)
            self.ui.pushButton_ok.setDisabled(False)
            self.ui.groupBox_kol.setDisabled(False)
