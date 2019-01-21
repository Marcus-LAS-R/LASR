import os
import glob
import platform
from datetime import datetime
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QVariant
from qgis.core import QgsSpatialIndex, QgsField, QgsFeature, Qgis, \
    QgsVectorLayer, QgsMessageLog, QgsProject, QgsWkbTypes, QgsFields, \
    QgsFeatureRequest, QgsVectorFileWriter, QgsCoordinateReferenceSystem
from collections import Counter, defaultdict
# import processing  # import przeniesiony do metody - pytest probemy!
from baza_wrapper import Baza
from baza_przetworz import Przetworz
from ui.ui_sprawdz_ls import Ui_Dialog


class recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)


class SprawdzLs(object):
    def __init__(self, i):
        self.iface = i
        k = False  # klasouzytki - warstwa
        d = False  # dzialki - warstwa

        # sprawdz czy uzyszkodnik zaznaczyl warstwe
        try:
            k = self.iface.activeLayer()
        except:  # nopep8
            QgsMessageLog.logMessage('Nie zaznaczono warstwy KLU w TOC!',
                                     'LasR')

        for key, lyr in QgsProject.instance().mapLayers().items():
            if key[:5] == 'DZKAT':
                d = lyr
            else:
                QgsMessageLog.logMessage(
                    'Nie znaleziono warstwy działek w TOC!',
                    'LasR'
                )
                return

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

        # slownik z obiektami PrzetworzKlu dla każdego parcelid z warswy
        # działek, całość zestawiana jest w metodzie zaladuj_strukture
        self.strukt = {}

        # lista parcelid, dla ktorych PrzetworzKlu zwróciło False w metodzie
        # is_valid() - raportowanie dla użytkownia, brak przetworzenia
        self.bledne = []

        self.lyrw = False  # warstwa wyjsciowa
        self.bledy_topo = []  # lista feats, ktore przecinaja sie z innymi
        self.iatr = False  # indeks pól w warstwie wyjsciowej
        self.county = ''  # kod wojewodztwa
        self.district = ''  # kod powiatu
        self.dz_nieles = []  # lista dzialek nielesnych

        # self.indeks = QgsSpatialIndex()
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
        # sprawdzenie czy warstwy sa poprawne znajduje sie w metodzie
        # sprawdz_warunki ponizej, ktora powinna byc uruchomiona po tej.

        # w zaleznosci od platformy znajdz odpowiednie bazy taksatora
        if platform.system()[:3] == 'Win':
            self.bazy = glob.glob(
                os.path.join(self.dd.ui.lineEdit_bazy.text(),
                             '*.mdb'))
        else:
            self.bazy = glob.glob(
                os.path.join(self.dd.ui.lineEdit_bazy.text(),
                             '*.sqlite'))

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
                    "Las-R",
                    Qgis.Warning
                )
                self.iface.messageBar.pushWarning(
                    'Uwaga',
                    'Nie udało się odczytać bazy: ' +
                    baza,
                    Qgis.Warning
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

        if len([x.name() for x in self.kolumny_dz
                if x.name() in self.dzkat.dataProvider().fields()]) == 12:
            return False

        # sprawdz czy w dzkat nie ma zdublowanych wartosci w parcelid
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                               ).setSubsetOfAttributes(
                                                   ['PARCELID'],
                                                   self.dzkat.fields()
                                               )
        policz = Counter([x['PARCELID'] for x in
                          self.dzkat.getFeatures(request)]).most_common()
        nad = [x[0] for x in policz if x[1] > 2]

        if len(nad) > 0:
            QgsMessageLog.logMessage(
                '   Znaleziono zdublowanych działek w shp: \n' +
                '\n'.join(nad),
                'LasR',
                Qgis.Critical
            )
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
                self.klu.dataProvider().addAttributes(pola_dodaj)
                self.klu.updateFields()
                self.klu.commitChanges()

            self.klu.startEditing()
            klu_fnm = self.klu.dataProvider().fieldNameMap()
            iau = klu_fnm['AU']
            isq = klu_fnm['SQ']
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

        # self.geop_przetworz()

    def geop_przetworz(self):
        """metoda wykonuje dissolve na warstwie klu nastepnie intersect z
        dzialkami, a potem rozbija wynik na singleparts, gotowe do analizy
        porownawczej z baza. Nie zwraca żadnej wartości"""

        # import modulu umieszony w metodzie czasowo, inaczej bruzdzil przy
        # tesowaniu.
        # TODO: przeniesc jako import na poczatek pliku po zakonczeniu
        # testowania
        import processing

        sciezka = self.klu.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        processing.run("native:dissolve", {
                        'INPUT': self.klu.name(),
                        'FIELD': [self.au, self.sq],
                        'OUTPUT': os.path.join(self.kat, '__klu_dissolve.shp')
        })

        processing.run("native:intersection", {
                        'INPUT': self.klu,
                        'OVERLAY': self.dzkat,
                        'INPUT_FIELDS': "",
                        'OVERLAY_FILEDS': "",
                        'OUTPUT': os.path.join(
                            self.kat, '__LS_multiparts_'+self.czas+'.shp'
                        )
        })

        processing.run("native:multiparttosingleparts", {
                        'OUTPUT': os.path.join(
                            self.kat, '__LS_singleparts_'+self.czas+'.shp'),
                        'INPUT': os.path.join(
                            self.kat, '__LS_multiparts_'+self.czas+'.shp')
                        })

        # Rozbij uzytki na single parts
        self.singleparts = QgsVectorLayer(os.path.join(
            self.kat, 'LS_singleparts'+self.czas+'.shp'),
            '__Ls_singleparts_'+self.czas+'.shp',
            'ogr')

    def zaladuj_strukture(self):
        """Metoda zestawia do słownika obiekty PrzetworzKlu dla każdej z
        działek, podmieniając SQ na duże litery.
        """
        sl_dzkat = {}
        for feat in self.dzkat.getFeatures():
            sl_dzkat[feat['PARCELID']] = feat

        sl_single = {}
        for feat in self.singleparts.getFeatures():
            if feat['PARCELID'] not in sl_single:
                sl_single[feat['PARCELID']] = []
            sl_single[feat['PARCELID']].append(feat)

        for key, val in sl_dzkat.items():
            k = []
            if key in sl_single:
                k = sl_single[key]

            self.strukt[key] = PrzetworzKlu(val, k, self.p)

    def przetworz_strukture(self):
        """ Metoda przetwarza strukturę wg ścieżki dla każdej z działki
        generując niezbędne dane do raportów oraz wynikowe klu do ostatecznych
        warstw.
        """
        for val in self.strukt.values():
            # jezeli uzytki nie sa valid - pomijamy raportujemy uzyszkodnikowi
            if not val.is_valid():
                self.bledne.append(val['PARCELID'])
                continue

            trig = 0  # trig, jezeli jest jeden ls na calosci, badz juz dopis.
            val.przetworz()
            val.sprawdz_topologie()
            if not val.s_czy_dz_w_bazie():
                continue

            if val.s_czy_ls_na_calosci():
                trig = 1  # jeden ls na calosci dzialki, skopiowany z geom dz.

            if trig == 0:
                if val.s_czy_jeden_ls():
                    trig = 2  # jeden ls na calej dzialce - zlokalizowany

            if trig in [0, 2]:
                val.s_dopisz_uzyt()
                val.sprawdz_mikro()

            val.polacz_ostateczne()
            val.dopisz_uwagi_pow()

    def generuj_warstwy(self):
        """Generuje 3 ostateczne warstwy: ostateczne, do sprawdzenia, bledy i
        dodaje je do mapy
        """
        sciezka = self.dzkat.dataProvider().dataSourceUri().split("|")[0][:-4]
        kat = os.path.dirname(sciezka)

        # tablice z odpowiednimi featurami
        poprawne = []
        do_spr = []
        bledne = []

        # przygotuj warstwe poprawnych LS
        self.lyrls = QgsVectorLayer("Polygon?crs=epsg:2180&index=yes",
                                    "LS_"+self.czas,
                                    "memory"
                                    )

        self.lyrls.startEditing()
        self.lyrls.dataProvider().addAttributes(
            self.kolumny_dz + self.kolumny_ls
        )
        self.lyrls.updateFields()

        # przygotuj warstwe do_spr
        self.lyrspr = QgsVectorLayer("Polygon?crs=epsg:2180&index=yes",
                                     "DO_SPRAWDZENIA__"+self.czas,
                                     "memory"
                                     )
        self.lyrspr.startEditing()
        self.lyrspr.dataProvider().addAttributes(
            self.kolumny_dz + self.kolumny_ls
        )
        self.lyrspr.updateFields()

        # przygotuj warstwe bledow
        self.lyrbl = QgsVectorLayer("Polygon?crs=epsg:2180&index=yes",
                                    "BLEDY_"+self.czas,
                                    "memory"
                                    )
        self.lyrbl.startEditing()
        self.lyrbl.dataProvider().addAttributes(
            self.kolumny_dz + self.kolumny_ls)
        self.lyrbl.updateFields()

        # wyciagnij ostateczne featurki
        for sit in self.strukt.values():
            p, s, b = sit.zwroc_ostateczne()
            poprawne += p
            bledne += b
            do_spr = s

        # dodaj do warstw
        self.lyrbl.dataProvider().addFeatures(bledne)
        self.lyrspr.dataProvider().addFeatures(do_spr)
        self.lyrls.dataProvider().addFeatures(poprawne)

        # zapisz zmiany do warstw w pamieci
        self.lyrbl.commitChanges()
        self.lyrspr.commitChanges()
        self.lyrls.commitChanges()

        crs = QgsCoordinateReferenceSystem("epsg:2180")

        error = QgsVectorFileWriter.writeAsVectorFormat(
            self.lyrbl,
            os.path.join(kat, "BLEDY_"+self.czas+".shp"),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        if error == QgsVectorFileWriter.NoError:
            QgsMessageLog.logMessage("Warstwa błędów ls zapisana!", "Las-R")
            self.lyrbl = self.iface.addVectorLayer(
                os.path.join(kat,
                             "BLEDY_"+self.czas+".shp"),
                "BLEDY_"+self.czas,
                "ogr"
            )

        error = QgsVectorFileWriter.writeAsVectorFormat(
            self.lyrspr,
            os.path.join(kat, "DO_SPRAWDZENIA_"+self.czas+".shp"),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        if error == QgsVectorFileWriter.NoError:
            QgsMessageLog.logMessage("Warstwa do sprawdzenia zapisana!",
                                     "Las-R")
            self.lyrspr = self.iface.addVectorLayer(
                os.path.join(kat,
                             "DO_SPRAWDZENIA_"+self.czas+".shp"),
                "DO_SPRAWDZENIA_"+self.czas,
                "ogr"
            )

        error = QgsVectorFileWriter.writeAsVectorFormat(
            self.lyrls,
            os.path.join(kat, "LS_"+self.czas+".shp"),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        if error == QgsVectorFileWriter.NoError:
            QgsMessageLog.logMessage("Warstwa Ls zapisana!",
                                     "Las-R")
            self.lyrls = self.iface.addVectorLayer(
                os.path.join(kat,
                             "LS_"+self.czas+".shp"),
                "LS_"+self.czas,
                "ogr"
            )

    def generuj_raport(self):
        """Generuje raport na podstawie danych zebranych ze słowników uwagi
        dla każdej z działek, zapisuje go na dysku i pyta użytkownika czy chce
        go wyświetlić w jego edytorze tekstu.
        """


class PrzetworzKlu(object):
    def __init__(self, d, k, p, wl='OF'):
        # d-feature z analizowana dzialka i struktura pol zgodna ze skryptem
        # k-tablica z featurami klu na tej dzialce, wszystkie musza byc
        # przykryte przez poligon dzialki, oraz byc singlepart
        # p - przetworzona baza przez klase Przetworz
        # wl - typ własności działek jaki interesuje uzytkownika ('OF', 'Ws')
        self.dz = d
        self.klus = k
        # wskaznik do slownikow na podstawie bazy
        self.p = p

        # kolejnosc id w poszczegolnych warstwach w celu zapewnienia spojnosci
        # danych, wymagane przy tworzeniu nowych featurow
        self.fid = 0

        # nazwy pol przetrzymujacych uzytki
        self.sq = 'SQ'
        self.au = 'AU'

        # tablica z polami, ktore maja znajdowac sie w ostatecznych danych
        # zwracanych uzytkownikowi, dodaje sie je metodą add_fields
        self.fields_def = [
            # QgsField('PARCELID', QVariant.String, len=30),
            # QgsField('AU', QVariant.String, len=10),
            # QgsField('SQ', QVariant.String, len=10),
            # QgsField('SPRAWDZ', QVariant.String, len=230),
            QgsField("COUNTY", QVariant.String, len=2),
            QgsField("DISTRICT", QVariant.String, len=2),
            QgsField("MUNICIP", QVariant.String, len=3),
            QgsField("COMMUNITY", QVariant.String, len=4),
            QgsField("PARCELNR", QVariant.String, len=20),
            QgsField("PARCELID", QVariant.String, len=50),
            QgsField("GRP", QVariant.String, len=2),
            QgsField("ARK", QVariant.String, len=12),
            QgsField("NIELES", QVariant.String, len=3),
            QgsField("SPRAWDZ", QVariant.String, len=150),
            QgsField("PARCEL_AR", QVariant.Double, "double", 10, 4),
            QgsField("PARCEL_POW", QVariant.Double, "double", 10, 4),
            QgsField("AU", QVariant.String, len=10),
            QgsField("SQ", QVariant.String, len=10),
            QgsField("SPRAWDZ", QVariant.String, len=150),
            QgsField("LANDID", QVariant.String, len=50),
            QgsField("LAND_AR", QVariant.Double, "double", 10, 4),
            QgsField("LAND_POW", QVariant.Double, "double", 10, 4),
        ]

        # PARCELID wyciagniety z dzialki w metodzie przetworz
        self.pid = ''

        # slownik z uzytkami na dzialce i zsumowanymi powierzchniami, obliczany
        # w metodzie przetworz
        # sl = {LANDID: 4,3222, LANDID: 0.0002, ....}
        self.sl_klus_pow = {}

        # slownik z featurami pogrupowanymi po LANDID, w postaci:
        # obliczany w metodzie przetworz
        # sl = {LANDID: [f1, f2, f3], LANDID2: [f4, f5,...],}
        self.sl_klus_grupy = {}

        # poprawne klu
        self.klus_popr = []
        self.klus_bledy = []  # tabel z featurami sklasyfikowanymi jako bledy
        self.klus_do_spr = []  # lista z featurami do sprawdzenia

        # tabela z rozbieznosciam powierzchniowymi, w postaci [LANDID, LANDID]
        self.rozb_pow = []

        # tabela z brakujacymi ls na dzialce, wg bazy,
        # w postaci [LANDID, LANDID]
        self.braki_warstwa = []

        # tabela z przetworzonymi id klu
        # w postaci [1, 22, 11, ...]
        self.klus_id_przetworzone = []

        # tablica z uwagami do raportu, grupowana wg skrotow ponizej:
        # pow - rozbieznosc powierzchni miedzy baza a grafika   OK
        #       landid: [pow graf, pow bazy],
        # podmsq - podmieniony SQ w Ls, dostosowany do bazy     OK
        #       {landid: [sq przed, sq po], ...}
        # podmau - podmieniony AU, dostosowany do bazy          OK
        #       landid: [au przed, au po]
        # brakb - brak uzytku w bazie, jest w grafice           OK
        #       [landid, landid]
        # brakg - brak uzytku w grafice, jest w bazie
        #       [landid, landid]
        # brakdzb - brak dzkat w bazie, jest w grafice          OK
        #       True/False
        # mikro - mikroluz do usuniecia przez uzytkownika,      OK
        #       generowane jako nowa warstwa z uwagami
        #       [landid, landid, ... ]
        # dubb - zdublowane ls, klu w bazie                     OK
        #       [landid, landid, ...]
        # podm - ls z podmieniona grafika na kontur z dzialki   OK
        #       (tylko przy 1 ls)
        #       True/False
        # op - dzialka z wlasnoscia OP                          OK
        #       True/False
        # opif - dzialka z wlasnoscia OPiF                      OK
        #       True/False
        #
        self.uwagi = recursivedefaultdict()

        # ustaw najistotniejsze tablic i wartości w uwagach
        self.uwagi['mikro'] = []
        self.uwagi['dubb'] = []
        self.uwagi['brakdzb'] = []
        self.uwagi['brakb'] = []
        self.uwagi['op'] = False
        self.uwagi['opif'] = False

        # True jezeli na dzialce nie ma zadnych klu
        self.bez_uzytkow = False

    def nazwa_sq_au(self, s, a):
        self.sq = s
        self.au = a

    def is_valid(self):
        if self.dz.geometry().wkbType() not in [QgsWkbTypes.Polygon,
                                                QgsWkbTypes.MultiPolygon]:
            return False

        if 'PARCELID' not in [x.name() for x in
                              self.dz.fields().toList()]:
            return False

        # jezeli na dzialce sa zadeklarowane klus, sprawdz poprawnosc
        if len(self.klus) > 0:
            if len([y for y in ['PARCELID', self.sq, self.au] if y in
                    [x.name() for x in self.klus[0].fields().toList()]]) != 3:
                return False

            # jezeli na dzialce znajduja sie uzytki z innej dzialki
            if set([self.dz['PARCELID']]) != set([x['PARCELID']
                                                  for x in self.klus]):
                return False

        return True

    def przetworz(self):
        """ Ustawia self.pid w obiekcie oraz oblicza slwoniki dla powierzchni i
        liczby uzytkow na dzialce, wykorzystywane potem w analizie mikro oraz
        usuwaniu niepotrzebnych urzytkow"""
        self.pid = self.dz['PARCELID']

        # oblicz sumaryczna powierzchnie dla uzytku na dzialce, sumujac
        # wszystkie multipoligony
        if len(self.klus) == 0:
            self.bez_uzytkow = True
            return False

        self.sl_klus_pow = {self.stworz_landid(x): 0 for x in self.klus}
        self.sl_klus_grupy = {self.stworz_landid(x): [] for x in self.klus}
        for f in self.klus:
            self.sl_klus_pow[self.stworz_landid(f)] += \
                round(f.geometry().area()/10000, 4)
            self.sl_klus_grupy[self.stworz_landid(f)].append(f)

        if self.pid in self.p.dz_op:
            self.uwagi['op'] = True

        if self.pid in self.p.dz_opif:
            self.uwagi['opif'] = True
        return True

        # lista zdublowanych ls w bazie na tej dzialce
        self.uwagi['dubb'] = [x for x in self.p.ls_podwojne
                              if '.'.join(x.split('.')[:2]) == self.pid]

    def sprawdz_topologie(self):
        """Metoda sprawdza czy klu nakladaja sie na siebie, w przypadku gdy
        jeden z poligonow jest przykryty przez inny wiekszy, ten mniejszy
        jest klasyfikowany jako blad i przerzucany do warstwy bledow i pomijany
        w dalszej obrobce. Jezeli dwa poligony nachodza na siebie tylko troche
        ich czesc wspolna jest dodana do warstwy bledow jako do sprawdzenia"""

        if len(self.klus) < 2:
            return

        self.do_usun = []
        for i in range(len(self.klus)-1):
            for j in range(i+1, len(self.klus)):
                if self.klus[i].geometry().intersects(self.klus[j].geometry()):
                    inter = self.klus[i].geometry().intersection(
                        self.klus[j].geometry())
                    if round(inter.area(), 3) < 0.001:
                        pass
                    else:
                        du, ds = self.s_topo_inter(i, j, inter)
                        self.klus_do_spr += ds

        self.s_do_usuniecia(self.do_usun)

    def s_do_usuniecia(self, do_usun, uw='przecina się z innym'):
        """Metoda usuwa z tabeli klus przekazane w tabeli f.id() i kopiuje
        je z odpowiednia struktura do tabeli klus_bledy, o ile uwaga nie
        jest rowna OK, wtedy dany featurek jest tylko usuwany z tabeli klus
        """

        # usun z listy klus featurki sklasyfikowane jako bledy
        self.do_usun = sorted(list(set(do_usun)), reverse=True)
        for i in self.do_usun:
            if uw != 'OK':
                f = self.new_feat(au=self.klus[i]['AU'],
                                  sq=self.klus[i]['SQ'],
                                  uw='nakłada się z innym')
                f.setGeometry(self.klus[i].geometry())
                self.klus_bledy.append(f)

            del self.klus[i]

    def s_topo_inter(self, i, j, inter):  # noqa
        """Metoda sprawdza, ktorego z idealnie nakladajacych sie poligonow
        wybrac do usuniecia z przyszlych analiz"""

        feat_do_spr = []  # tabela z przecieciem jako featurem do sprawdzenia
        inter_area = round(inter.area(), 3)

        # jezeli ktory z klus ma powierzchnie mniejsza niz 21 m2 zostawiamy
        # sprawdzanie nakladan, zajmie sie tym klasa sprawdzania mikrouzytkow
        if min([round(self.klus[i].geometry().area(), 3),
                round(self.klus[j].geometry().area(), 3)]) < 21:
            return

        landid_i = self.pid + '.' + \
            self.klus[i][self.au] + \
            self.isNone(self.klus[i][self.sq])
        landid_j = self.pid + '.' + \
            self.klus[j][self.au] + \
            self.isNone(self.klus[j][self.sq])

        # powierzchnia przeciecia jest taka sama jak
        # powierzchnia obu klu
        if round(self.klus[i].geometry().area(), 3) == \
                inter_area and \
                round(self.klus[j].geometry().area(), 3) == \
                inter_area:

            # jezeli oba sa w bazie wybieramy nielesnego
            if landid_i in self.p.uzytki and landid_j in \
                    self.p.uzytki:

                # jezeli tylko jeden z klu jest w bazie, to go
                # zostawiamy
                if self.klus[i][self.au] != 'Ls' and \
                        self.klus[j][self.au] == 'Ls':
                    self.do_usun.append(i)
                elif self.klus[j][self.au] != 'Ls' and \
                        self.klus[i][self.au] == 'Ls':
                    self.do_usun.append(j)

                # jezeli oba powyzsze sa ls-ami, niech uzytkownik zdecyduje
                else:
                    f = self.new_feat(
                        uw='nałożone poligony o tym samym kształcie')
                    f.setGeometry(inter)
                    feat_do_spr.append(f)

            elif landid_i in self.p.uzytki and landid_j not in \
                    self.p.uzytki:
                self.do_usun.append(j)

            elif landid_i not in self.p.uzytki and landid_j in \
                    self.p.uzytki:
                self.do_usun.append(i)

        # powierzchnia jednego badz drugiego jest taka sama jak przeciecia
        elif round(self.klus[i].geometry().area(), 3) == inter_area:
            # jezeli uzytek jest w bazie to usuwamy albo do sprawdzenia
            if landid_i in self.p.uzytki:
                if len(self.sl_klus_grupy[landid_i]) > 1:
                    self.do_usun.append(i)
                else:
                    f = self.new_feat(
                        uw='nałożona część poligonu, na inny cały')
                    f.setGeometry(inter)
                    feat_do_spr.append(f)

            # jak uzytku nie ma w bazie to do usuniecia
            else:
                self.do_usun.append(i)

        elif round(self.klus[j].geometry().area(), 3) == inter_area:
            # jezeli uzytek jest w bazie to usuwamy albo do sprawdzenia
            if landid_j in self.p.uzytki:
                if len(self.sl_klus_grupy[landid_j]) > 1:
                    self.do_usun.append(j)
                else:
                    f = self.new_feat(
                        uw='nałożona część poligonu, na inny cały')
                    f.setGeometry(inter)
                    feat_do_spr.append(f)

            # jak uzytku nie ma w bazie to do usuniecia
            else:
                self.do_usun.append(j)

        # oba poligony przecinaja sie na czesci swoich powierzchni, uzytkownik
        # musi zdecydowac ktora granica przebiegu jest właściwa
        else:
            f = self.new_feat(
                uw='nałożona część poligonów')
            f.setGeometry(inter)
            feat_do_spr.append(f)

        return self.do_usun, feat_do_spr

    def s_czy_dz_w_bazie(self):
        self.uwagi['brakdzb'] = False
        if self.pid in self.p.dzialki.keys():
            return True

        return False

    def s_czy_ls_na_calosci(self):
        """Metoda sprawdza czy uzytek znajduje sie na calej dzialce, jest jeden
        w zbiorze uzytkow w bazie, jezeli tak to podmienia jego grafike na
        kontur dzialki"""

        self.uwagi['podm'] = False
        if self.pid in self.p.sl_pow_ls_dzkat:
            if self.p.sl_pow_ls_dzkat[self.pid][0] == \
                    self.p.sl_pow_ls_dzkat[self.pid][1]:
                f = self.new_feat(au='Ls', sq=self.p.sl_ls_na_dz[self.pid][0])
                f.setGeometry(self.dz.geometry())
                self.klus_popr.append(f)
                self.uwagi['podm'] = True
                return True
        return False

    def s_czy_jeden_ls(self):
        """Metoda sprawdza czy w bazie jest jeden ls, jezeli tak, sprawdza czy
        na dzialce znajduje sie jeden ls o tej samej klasie"""
        # sprawdz czy w bazie znajduje sie tylko jeden ls na dzewid
        if len(self.p.sl_ls_na_dz[self.pid]) > 1:
            return False

        # jeżeli na dzialce jest wiecej niz jedna klasa uzytkow w graf
        if len(self.sl_klus_grupy.keys()) > 1:
            return False

        self.do_usun = []
        for ii, klu in enumerate(self.klus):
            uw = ''  # uwagi do wpisania do warstwy

            # stworz landid poprawny i zgodny z baza
            landid = self.pid + 'Ls' + self.p.sl_ls_na_dz[self.pid][0]

            if len(set([x for x in self.sl_klus_pow.keys()
                        if x.split('.')[-1][:2] == 'Ls'])) == 1:
                # jezeli jest Ls ale ma inna klase - podmien SQ i dodaj do
                # raportu rozbieznosci
                if klu[self.au] == 'Ls' and \
                        klu[self.sq] != self.p.sl_ls_na_dz[self.pid][0]:

                    self.uwagi['podmsq'][landid] = [
                        klu['AU'],
                        self.isNone(klu['SQ'])
                    ]
                    uw = 'Podmieniono SQ na zgodny z bazą; '

            # jezeli na dzialce jest tylko jeden inny uzytek, podmien na
            # brakujacy ls, o ile nie jest bledem topo
            elif len(set([x for x in self.sl_klus_pow.keys()])) == 1:
                self.uwagi['podmau'][landid] = [
                    klu[self.au] + self.isNone(klu[self.sq]),
                    'Ls' + self.p.sl_ls_na_dz[self.pid][0]
                ]
                uw = 'Podmieniono AU i SQ na zgodny z bazą; '

            f = self.new_feat('Ls',
                              self.p.sl_ls_na_dz[self.pid][0],
                              uw=uw)
            f.setGeometry(klu.geometry())
            self.klus_popr.append(f)
            self.do_usun.append(ii)

        self.s_do_usuniecia(self.do_usun)
        return True

    def s_dopisz_uzyt(self):
        """Metoda dopisuje do wszystkich klu w tablicy klus, dane z bazy i
        uwagi, i przerzuca je do tablicy klus_popr, z odpowiednimi adnotacjami
        """

        self.do_usun = []
        for ii, klu in enumerate(self.klus):
            landid = self.pid + '.' + \
                klu['AU'] + \
                self.isNone(klu['SQ'])

            uw = ''
            dop1 = klu['AU']
            dop2 = klu['SQ']
            if landid not in self.p.uzytki:
                uw = 'Brak w bazie; '

                # dopisz landid do tablicy uwag
                if 'brakb' not in self.uwagi:
                    self.uwagi['brakb'] = []
                if landid not in self.uwagi['brakb']:
                    self.uwagi['brakb'].append(landid)

            else:
                dop1 = self.p.uzytki[landid][0]
                dop2 = self.p.uzytki[landid][1]

            f = self.new_feat(au=dop1, sq=dop2, uw=uw)
            f.setGeometry(klu.geometry())
            self.klus_popr.append(f)
            self.do_usun.append(ii)

        # usun dopisane uzytki z poli klu
        self.s_do_usuniecia(self.do_usun, 'OK')

    def add_fields(self, new_fields):
        """ Metoda dodająca pola, które mają się znaleźć w ostatecznej wersji
        każdego feat, zwracanego użytkownikowi. Jeżeli pola nie zostaną podane
        klasa będzie korzystała ze zdefiniowanych na początku niezbędnych pól,
        które są wymagane do działania: [AU, SQ, PARCELID, SPRAWDZ].

        Przekazywana tabela powinna wyglądać: [QgsField(), QgsField(), ...]
        """
        # sprawdz czy podne pola zawieraja niezbędne minimum:
        policz_niezb = len([x.name() for x in new_fields if x.name() in
                            [y.name() for y in self.fields_def]
                            ])

        if policz_niezb != 4:
            return False

        self.fields_def = new_fields

    def new_feat(self, au=False, sq=False, uw=False):
        f = QgsFeature(self.fid)
        self.fid += 1
        fds = QgsFields()
        for fi in self.fields_def:
            fds.append(fi)

        f.setFields(fds)
        f.setAttribute(f.fieldNameIndex('PARCELID'), self.pid)
        if au:
            f.setAttribute(f.fieldNameIndex('AU'), au)
        if sq:
            f.setAttribute(f.fieldNameIndex('SQ'), sq)
        if uw:
            f.setAttribute(f.fieldNameIndex('SPRAWDZ'), uw)
        return f

    def stworz_landid(self, f):
        """metoda tworzy LANDID na podstawie danych podanego feature'a"""
        return f['PARCELID'] + '.' + f['AU'] + self.isNone(f['SQ'])

    def isNone(self, a):
        if a in [None, 'NULL', '', ]:
            return ''
        else:
            return a

    def sprawdz_mikro(self):
        """ Metoda sprawdza czy w uzupełnionej tabeli klus_popr znajdują się
        jakieś mikroużytki a następnie sprawdza czy da się je usunąć automaty-
        cznie. Jeżeli nie zwracana jest tabela z featurami do sprawdzenia przez
        użytkownika.
        """
        d = SprawdzMikro(self.klus_popr)
        d.przetworz()
        popr, spr, usun = d.zwroc_wyn()

        if len(popr) < len(self.klus_popr):
            self.klus_popr = popr

        self.klus_do_spr += spr
        self.klus_bledy += usun

    def polacz_ostateczne(self):  # noqa
        """Metoda zestawia klu z tablic z poprawnymi, blednymi i do sprawdzenia
        poligonami, łączy je na podstawie landid, uzupełnia tablice uwagi o
        info na temat obecnosci użytków w bazie, podwojnych użytkow w bazie,
        rozbieżności powierzchni międz bazą a grafiką, obecności mikrusów.
        """
        spis_klu = [self.stworz_landid(x) for x in self.klus_popr]
        ile_klu = [x[0] for x in Counter(spis_klu).most_common() if x[1] > 1]

        # tablica z poprawnymi klu połącznymi w multipoly i posiadajace juz
        # poprawne, i niezdublowane uwagi
        self.poprawne = {}

        for i, y in enumerate(spis_klu):
            # jezeli uzytek jest mikrusem dodaj uwage do slownika
            if self.klus_popr[i].geometry().area() < 21:

                if y not in self.uwagi['mikro']:
                    self.uwagi['mikro'].append(y)

            if y not in self.poprawne:
                self.poprawne[y] = self.klus_popr[i]

            elif y in ile_klu:
                # dodaj nowa geometrie do bazy
                geom_baza = self.poprawne[y].geometry()
                geom_dolacz = self.klus_popr[i].geometry()

                # jezeli czesci sie stykaja - union, niestykaja - dodaj part
                if geom_baza.intersects(geom_dolacz):
                    new_geom = geom_baza.combine(geom_dolacz)
                else:
                    new_geom = geom_baza.addPart(geom_dolacz)

                self.poprawne[y].clearGeometry()
                self.poprawne[y].setGeometry(new_geom)

                # sprawdz czy w tej czesci nie ma jakichs nowych uwag, jezeli
                # sa dodaj do wczesniejszych na koncu
                u_nowe = self.klus_popr['SPRAWDZ'].split('; ')
                u_stare = self.poprawne[y]['SPRAWDZ']

                # sprawdz czy sa jakies nowe uwagi, jezeli tak, dodaj
                trig_dopisz = False
                for u in u_nowe:
                    if u not in u_stare:
                        u_stare += u + '; '
                        trig_dopisz = True

                if trig_dopisz:
                    self.poprawne[y].setAttribute(
                        self.poprawne[y].fieldNameIndex('SPRAWDZ'),
                        u_stare)

    def dopisz_uwagi_pow(self):
        """Metoda sprawdza czy połączone klu w słowniku poprawne, nie odbiegają
        za bardzo od powierzchni rejestrowych zapisanych w bazie, oraz czy Ls
        na działce są napewno wycięte, a nie tylko skopiowane z kontury działki
        """

        # sprawdzenie czy powierzchnie nie roznia sie za bardzo
        for landid, item in self.poprawne.items():

            # jezeli nie ma uzytku w bazie nie ma co sprawdzac
            if landid not in self.p.uzytki:
                continue

            # jezeli obie powierzchnie sa ponizej 20 ar - pomijamy uwagi
            if max(item.geometry().area(), self.p.uzytki[landid][2]) < 0.2:
                continue

            # sprawdzamy tylko i wyłącznie Ls
            if item['AU'] != 'Ls':
                continue

            if abs(item.geometry().area()-self.p.uzytki[landid][2]) > 0.15:

                if 'pow' not in self.uwagi:
                    self.uwagi['pow'] = {}

                if landid not in self.uwagi['pow']:
                    self.uwagi['pow'][landid] = [item.geometry().area(),
                                                 self.p.uzytki[landid][2]]
                    uw = str(item['SPRAWDZ'])
                    if 'None' in uw:
                        uw = ''

                    item.setAttribute(
                        item.fieldNameIndex('SPRAWDZ'),
                        uw+'Duża rozbieżność pow. rej/graf; ')

                    # sprawdz czy pow graf uz==pow graf dz, a w bazie nie
                    if (round(self.dz.geometry().area(), 3) ==
                        round(item.geometry().area(), 3)) and (
                            self.p.uzytki[landid][2] <
                            self.p.uzytki[landid][0]):

                        uw = str(item['SPRAWDZ'])
                        item.setAttribute(
                            item.fieldNameIndex('SPRAWDZ'),
                            uw+'Prawdopodobnie niewycięty Ls; ')

            # dopisz wszystkie dane z warstwy dzialek oraz z bazy
            for nazwa in [x.name() for x in self.dz.fields() if
                          x.name in [y.name() for y in item.fields()]]:
                item.setAttribute(item.fieldNameIndex(nazwa),
                                  self.dz[nazwa])

            # dopisz dane z bazy
            item.setAttribute(item.fieldNameIndex('LANDID'), landid)
            item.setAttribute(item.fieldNameIndex('LAND_AR'),
                              self.p.uzytki[landid][2])
            item.setAttribute(item.fieldNameIndex('LAND_POW'),
                              round(item.geometry().area(), 4))
            if self.pid not in self.p.dz_lesne:
                item.setAttribute(item.fieldNameIndex('NIELES'), 'TAK')

    def zwroc_ostateczne(self):
        """Metoda zwraca ostateczne wersje przetworzonych uzytków w postaci
        jednego słownika i dwóch tabel:
        1) poprawnych klu, (dict)
        2) poligonów oznaczających miejsca do sprawdzenia,
        3) blędne klu/mikro/inne, które zostały zakwalifikowane jako błędy i
        usunięte z warstwy poprawnych klu.
        """
        return self.poprawne, self.klus_do_spr, self.klus_bledy


class SprawdzMikro(object):
    def __init__(self, tab, baza_uz=[]):
        # tablica ze wszystkimi poprawnymi klu (duze i male razem, nieposort.)
        self.klus_popr = tab
        # tablica z uztykami wpisanymi do bazy
        self.baza_klu = baza_uz

        # tablica z przetworzonymi klu po poprawkach mikro
        self.feat_popr = []

        self.pid = ''
        if len(tab) > 0:
            self.pid = tab[0]['PARCELID']

        self.do_usun = []  # f.id() do usuniecia z klus_popr
        # [[f.id(), f.id()], ...] id laczonego, id bazowego
        self.do_polacz = []

        # tabele z przetworzonymi feat zwracanymi uzytkownikowi
        self.feat_do_usun = []
        self.feat_popr = []
        self.feat_do_spr = []

        # sl z sasiadami dla kazdego klu
        self.sl_sasiadow = {}

    def is_valid(self):  # noqa
        """Metoda sprawdza mikrouzytki i o ile takie istnieją w tablicy
        zwraca True"""

        # sprawdz czy na dzialce sa klu mniejsze niz 21 m2 jezeli nie, pomin
        # sprawdzanie mikrouzytkow na dzialce
        self.p_min_klu_pow = sorted([f.geometry().area()
                                     for f in self.klus_popr
                                     if f.geometry().area() < 21])
        if len(self.p_min_klu_pow) < 1:
            return False
        else:
            self.p_min_klu = [f for f in self.klus_popr
                              if f.geometry().area() < 21]

        # jeżeli na dzialce jest tylko jeden uzytek, poniechaj
        if len(self.klus_popr) < 2:
            return False

        return True

    def zbuduj_strukture(self):
        # Jezeli na dzialce sa mikrouzytki zbuduj indeks przestrzenny
        # poprawnych klus
        self.si = QgsSpatialIndex()
        self.slk = {}
        for k in self.klus_popr:
            if k.id() not in self.slk:
                self.slk[k.id()] = k
                self.si.addFeature(k)
            else:
                print('---BLAD---|powtorzony id:'+self.pid+str(k.id()))

        # oblicz powierzchnie sumaryczna dla wszystkich klu
        # {landid: 2.223, landid: 9.332, ...}
        self.sl_pow_popr_klu = {}
        # slownik z liczba poprawnych klu na dzialce
        # {landid: 2, landid: 6, ... }
        self.sl_ile_popr_klu = {}

        for klu in self.klus_popr:
            landid = self.pid + '.' + klu['AU'] + klu['SQ']

            if landid not in self.sl_pow_popr_klu:
                self.sl_pow_popr_klu[landid] = 0.0
            self.sl_pow_popr_klu[landid] += klu.geometry().area() / 10000

            if landid not in self.sl_ile_popr_klu:
                self.sl_ile_popr_klu[landid] = 0
            self.sl_ile_popr_klu[landid] += 1

            self.sl_sasiadow[klu.id()] = []

    def przetworz_mikro(self):
        # sprawdz sasiedztwa wszystkich malych klus na dzialce
        for k in self.p_min_klu:
            landid = self.pid + '.' + k['AU'] + k['SQ']
            polacz = False  # flaga do polaczenia lub usuniecia

            # jezeli uzytek jest w bazie
            if 'Brak w bazie; ' not in k['SPRAWDZ']:
                # jezeli uzytek ma mala pow w bazie - zostaw
                if self.sl_ile_popr_klu[landid] < 2 and \
                        self.sl_pow_popr_klu[landid] < 0.006:
                    # na dzialce jest zlokalizowany maly uzytek, olac
                    self.feat_popr.append(k)

                elif self.sl_ile_popr_klu[landid] > 1 and \
                        self.sl_pow_popr_klu[landid] > 0.006:
                    # jezeli mikrus jest < 5% pow calego uzytku - skasuj
                    if (k.geometry().area()/10000) / \
                            self.sl_pow_popr_klu[landid] < 0.05:
                        polacz = True

            # jezeli mikrusa nie ma w bazie, skasuj/polacz
            else:
                polacz = True

            # jezeli oznaczony do usuniecia z poprawnej warstwy - usun
            if polacz:
                self.polacz_klu(k)

    def polacz_klu(self, k):  # noqa
        ids = self.si.intersects(k.geometry().boundingBox())

        # znajdz sasiadow z ktorymi dzieli najwiecej miejsca
        p_area = []  # tablica z przecieciami powierzchniowymi[[id, pow], ...]
        p_line = []  # tablica z przecieciami liniowymi [[id, len], ...]
        for id in ids:
            if id == k.id():
                pass
            else:
                geom = self.slk[id].geometry()
                if geom.intersects(k.geometry()):
                    # informacje o przecieciu
                    inter = geom.intersection(k.geometry())
                    self.sl_sasiadow[k.id()].append(id)

                    # jezeli przeciecie jest powierzchniowe i nie calkowite do
                    # sprawdzenia przez uzyszkodnika
                    # jezeli przeciecie jest powierzchniowe
                    if round(inter.area(), 3) > 0.000:
                        p_area.append([id, round(inter.area(), 3)])

                    # jezeli tylko liniowe
                    else:
                        p_line.append([id, inter.length()])

        # jezeli przecina sie z jednym  dolacz do niego, niezaleznie od tego
        # czy stylka sie na wiekszej dlugosci z czym innym
        if len(p_area) == 1:
            # jezeli powierzchnia przeciecia jest taka sama jak pow
            # sprawdzanego klu, a pow 2 przecinajacego sie uzytku jest wieksza
            # to usun analizowany klu
            if round(k.geometry().area(), 3) == p_area[0][1] and \
                    round(self.slk[p_area[0][0]].geometry().area(), 3) > \
                    p_area[0][1]:
                self.do_usun.append(k.id())

            # jezeli powierzchnia jest taka sama jak innego klu tzn ze jest to
            # blad nachodzenia 2 klu na siebie - do wyjasnienia!
            if round(self.slk[p_area[0][0]].geometry().area(), 3) >= \
                    p_area[0][1]:
                self.do_polacz.append([k.id(), p_area[0][0]])
            else:
                uw = k['SPRAWDZ']
                k.setAttribute(k.fieldNameIndex('SPRAWDZ'),
                               uw+'Mikro do spr; ')
                self.feat_do_spr.append(k)

        # jezeli mikrus pokrywa sie z innymi uzytkami w 100%, usuwamy -
        # sprawdzilismy wczesniej czy aby nie jest niezbedny
        elif len(p_area) > 1:
            if sum([x[1] for x in p_area]) == round(k.geometry().area(), 3):
                self.do_usun.append(k.id())

        # jezeli mikrus z niczym sie nie przecina, dolacz do sasiada z ktorym
        # dzieli najwiecej wspolnego miejsca
        else:
            if len(p_line) > 0:
                p_line = sorted(p_line, key=lambda x: x[1], reverse=True)
                znikajace = self.do_usun + [x[0] for x in self.do_polacz]

                if p_line[0][0] not in znikajace:
                    # jezeli mikrus styka sie z innym uzytkiem na obwodzie
                    # mniejszym niz 5% usuwamy
                    if (p_line[0][1]/k.geometry().length()) < 0.05:
                        self.do_usun.append(k.id())
                    else:
                        self.do_polacz.append([k.id(), p_line[0][0]])

                else:
                    if len(p_line) == 2 and p_line[1][0] not in znikajace:
                        self.do_polacz.append([k.id(), p_line[1][0]])
                    elif len(p_line) == 1 and p_line[0][0] in znikajace:
                        self.do_usun.append(k.id())
                    else:
                        uw = k['SPRAWDZ']
                        k.setAttribute(k.fieldNameIndex('SPRAWDZ'),
                                       uw+'Mikro do spr; ')
                        self.feat_do_spr.append(k)

        # jezeli z niczym nie sasiaduje - usuwamy
        if len(ids) == 1:
            self.do_usun.append(k.id())

    def process(self):
        """Metoda usuwa, bądź łączy mikrouzytki z warstwy klus_popr wg podanych
        tabel (generowanych w s_mikro). """

        poprawione = []
        # polacz geom featurow przeznaczonych do laczenia
        for it in self.do_polacz:
            # jezeli feature do laczenia znalazl sie jednak na liscie do
            # usuniecia przesun mikrusa na warstwe do sprawdzenia
            if it[1] in self.do_usun:
                # sprawdz czy wszyscy sasiedzi sa mikro, jezeli tak, usun.
                sas = [x for x in self.sl_sasiadow[it[0]]
                       if x not in [y.id() for y in self.p_min_klu]]
                if len(sas) == 0:
                    self.do_usun.append(it[0])
                else:
                    uw = self.slk[it[0]]['SPRAWDZ']
                    self.slk[it[0]].setAttribute(
                        self.slk[it[0]].fieldNameIndex('SPRAWDZ'),
                        uw+'Mikro do spr; ')
                    self.feat_do_spr.append(self.slk[it[0]])

            else:
                feat_baza = self.slk[it[1]]
                g_bazy = self.slk[it[1]].geometry()
                g_lacz = self.slk[it[0]].geometry()

                # geometria po union
                try:
                    g_union = g_bazy.combine(g_lacz)

                    # wyczyść a potem ustaw nowa geometrie
                    feat_baza.clearGeometry()
                    feat_baza.setGeometry(g_union)

                    self.slk[it[1]].clearGeometry()
                    self.slk[it[1]].setGeometry(g_union)

                    if it[1] not in poprawione:
                        poprawione.append(it[1])

                    # jezeli laczonego uzytku jeszcze nia ma w usunietych dodaj
                    if it[0] not in self.do_usun:
                        self.do_usun.append(it[0])

                except:  # noqa
                    # jezeli nie udało się przeprowadzić combine, zostawiamy
                    # baze nietknieta a laczony mikrus dodajemy do sprawdzenia
                    g_union = g_bazy

                    if it[1] not in poprawione:
                        poprawione.append(it[1])

                    uw = self.slk[it[0]]['SPRAWDZ']
                    self.slk[it[0]].setAttribute(
                        self.slk[it[0]].fieldNameIndex('SPRAWDZ'),
                        uw+'Mikro do spr; ')
                    self.feat_do_spr.append(self.slk[it[0]])

        for id in poprawione:
            self.feat_popr.append(self.slk[id])

    def zestaw_tablice(self):
        """Metoda ustawia ostateczne tablice ktore zostana zwrocone jako wynik
        z juz poprawionymi geometriami i pogrupowanymi danymi"""

        # id featurow juz dopisanych do poprawnej tabeli klu
        obecne = [f.id() for f in self.feat_popr]
        id_do_spr = [f.id() for f in self.feat_do_spr]
        id_mikrusow = [f.id() for f in self.p_min_klu]

        for feat in self.klus_popr:
            # jezeli feat jest juz w obecnych lub do spr - pomin
            if feat.id() in obecne + id_do_spr:
                pass

            elif feat.id() in self.do_usun:

                uw = feat['SPRAWDZ']
                feat.setAttribute(feat.fieldNameIndex('SPRAWDZ'),
                                  uw+'Mikro do spr; ')
                self.feat_do_usun.append(feat)

            elif feat.id() not in id_mikrusow:
                self.feat_popr.append(feat)

    def przetworz(self):
        """ Metoda zbiorcza przetwarza wczytane klu wg poprawnej kolejnosci
        zdarzen"""

        if not self.is_valid():
            return True

        self.zbuduj_strukture()
        self.przetworz_mikro()
        self.process()
        self.zestaw_tablice()

    def zwroc_wyn(self):
        """ Metoda zwraca 3 listy: poprawne klu, do sprawdzenia, i usuniete"""

        return self.feat_popr, self.feat_do_spr, self.feat_do_usun


class GenerujRaport():
    def __init__(self, struk, wl, p):
        """ konstruktor pobiera słownik z obiektami PrzetworzKlu w postaci:
            {parcelid: PrzetworzKlu, ...} już z przetworzonymi i ostatecznymi
            klu oraz uwagami do powyższych, oraz typ wlasnosci działek jaki
            wybrał użytkownik (OF - pryw i współwłasności, lub cokolwiek innego
            ). p - obiekt przetworzonej bazy danych.
            Klasa generuj wypis do pliku txt na podstawie danych z bazy i shp
            """

        self.s = struk
        self.wl = wl
        self.p = p

        self.wypis = 'RAPORT\n\n'

        # tablica ze wszystkimi poprawnymi uzytkami, z warstwy LS
        self.uzytki = []

        self.ls_w_shp = []
        self.ls_w_bazie = []
        self.brakujace_ls_w_shp = []
        self.brakujace_ls_w_bazie = []
        self.pow_zerowe_baza = []
        self.lista_mikro = []

    def zestaw_dane(self):
        """Metoda zbiorcza do zestawienia wszystkich niezbednych tablic
        """
        pass

    def zestaw_uzytki(self):
        for ob in self.struk.values():
            oki, do_spr, bl = ob.zwroc_ostateczne()
            self.uzytki += oki

    def zestaw_liste_ls_w_shp(self):
        if self.wl == 'OF':
            # ile ls w shp
            self.ls_w_shp = [x for x in self.uzytki
                             if x['AU'] == 'Ls' and
                             x['PARCELID'] not in self.p.dz_op]

        else:
            # ile ls w shp
            self.ls_w_shp = [x for x in self.uzytki
                             if x['AU'] == 'Ls']

    def zestaw_ile_ls_bazie(self):
        if self.wl == 'OF':
            self.ls_w_bazie = len(
                [k for k in self.p.ls
                 if self.p.uzytki[k][0] == 'Ls' and
                 self.p.uzytki[k][3] not in self.p.dz_op]
            )

        else:
            self.ls_w_bazie = len(self.p.ls) + len(self.p.ls_podwojne)

    def zestaw_liste_brakujacych_ls_w_shp(self):
        if self.wl == 'OF':
            self.brakujace_ls_w_shp = [
                [k, self.p.uzytki[k][2]] for k in self.p.ls
                if k not in [x['LANDID'] for x in self.ls_w_shp] and
                self.p.uzytki[k][3] not in self.p.dz_op
            ]
        else:
            self.brakujace_ls_w_shp = [
                [k, v[2]] for k, v in self.p.uzytki.items()
                if k not in self.p.ls
            ]

    def zestaw_liste_brakujacych_ls_w_bazie(self):
        if self.wl == 'OF':
            self.brakujace_ls_w_bazie = [
                [x['LANDID'], str(round(x.geometry().area()/10000, 4))]
                for x in self.ls_w_shp
                if x['LANDID'] not in self.p.ls and
                x['PARCELID'] not in self.p.dz_op
            ]

        else:
            self.brakujace_ls_w_bazie = [
                [x['LANDID'], str(round(x.geometry().area()/10000, 4))]
                for x in self.ls_w_shp
                if x['LANDID'] not in self.p.ls
            ]

    def zestaw_liste_zerowych_ls_w_bazie(self):
        if self.wl == 'OF':
            # zestaw liste landid z powierzchniami zerowymi w bazie
            self.pow_zerowe_baza = [k for k in self.p.ls
                                    if self.p.uzytki[k][2] < 0.0001 and
                                    self.p.uzytki[k][3] not in self.p.dz_op]

        else:
            # zestaw liste landid z powierzchniami zerowymi w bazie
            self.pow_zerowe_baza = [k for k in self.p.ls
                                    if self.p.uzytki[k][2] < 0.0001]

    def zestaw_liste_mikro(self):
        if self.wl == 'OF':
            mikro = [
                x['uwagi']['mikro'] for x in self.struk.values()
                if len(x['uwagi']['mikro']) > 0 and
                x['uwagi']['op'] is False
            ]
        else:
            mikro = [
                x['uwagi']['mikro'] for x in self.struk.values()
                if len(x['uwagi']['mikro']) > 0
            ]

        for xx in mikro:
            if len(xx) > 0:
                self.lista_mikro += xx


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
        if self.lyrk is not False:
            if self.lyrk.isValid():
                self.ui.lineEdit_klu.setText(
                    self.lyrk.dataProvider().dataSourceUri().split("|")[0])
                self.ui.comboBox_ident.setDisabled(False)
                self.wczytaj_pola()

        # Jezeli jest warstwa dzkat, odczytaj jej dane
        if self.lyrd is not False:
            if self.lyrd.isValid():
                self.ui.lineEdit_dzkat.setText(
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
            self.wczytaj_pola()
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
