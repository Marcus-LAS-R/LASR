import os
import glob
import platform
from datetime import datetime
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QVariant
from qgis.core import QgsSpatialIndex, QgsField, QgsFeature, Qgis, \
    QgsVectorLayer, QgsMessageLog, QgsProject, QgsWkbTypes
from collections import Counter, namedtuple, defaultdict  # noqa
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
            QgsMessageLog.logMessage('Nie zaznaczono warstwy w TOC!', 'LasR')

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


class PrzetworzKlu(object):
    def __init__(self, d, k, p):
        # d-feature z analizowana dzialka i struktura pol zgodna ze skryptem
        # k-tablica z featurami klu na tej dzialce, wszystkie musza byc
        # przykryte przez poligon dzialki, oraz byc singlepart
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
        # pow - rozbieznosc powierzchni miedzy baza a grafika
        # podmsq - podmieniony SQ w Ls, dostosowany do bazy
        # podmau - podmieniony AU, dostosowany do bazy
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

        if len(y for y in ['PARCELID', self.sq, self.au] if y in
                [x.name() for x in self.klus[0].fields().toList()]) != 3:
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

        self.sl_klus_pow = {self.stworz_landid(x): 0
                            for x in self.klus}
        self.sl_klus_grupy = {self.stworz_landid(x): [] for x in self.klus}
        for f in self.klus:
            self.sl_klus_pow[self.stworz_landid(f)] += \
                round(f.geometry().area()/10000, 4)
            self.sl_klus_grupy[self.stworz_landid(f)].append(f)

        return True

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
                    inter = round(self.klus[i].geometry().intersection(
                        self.klus[j].geometry()), 3)
                    if inter.area() < 0.01:
                        pass
                    else:
                        du, ds = self.s_topo_inter(i, j, inter)
                        self.do_usun += du
                        self.klus_do_spr.append(ds)

        self.s_do_usuniecia(self.do_usun)

    def s_do_usuniecia(self, do_usun, uw='przecina się z innym'):
        """Metoda usuwa z tabeli klus przekazane w tabeli f.id() i kopiuje
        je z odpowiednia struktura do tabeli klus_bledy, o ile uwaga nie
        jest rowna OK, wtedy dany featurek jest tylko usuwany z tabeli klus
        """

        # usun z listy klus featurki sklasyfikowane jako bledy
        self.do_usun = list(set(do_usun)).sort(reverse=True)
        for i in self.do_usun:
            if uw != 'OK':
                f = self.new_feat(au=self.klus[i][self.au],
                                  sq=self.klus[i][self.sq],
                                  uw='przecina się z innym')
                f.setGeometry(self.klus[i].geometry())
                self.klus_bledy.append(f)
            self.klus.remove(i)

    def s_topo_inter(self, i, j, inter):
        """Metoda sprawdza, ktorego z idealnie nakladajacych sie poligonow
        wybrac do usuniecia z przyszlych analiz"""

        self.do_usun = []  # tabela z id klu do usuniecia
        feat_do_spr = []  # tabela z przecieciem jako featurem do sprawdzenia

        landid_i = self.pid + '.' + \
            self.klus[i][self.au] + \
            self.isNone(self.klus[i][self.sq])
        landid_j = self.pid + '.' + \
            self.klus[j][self.au] + \
            self.isNone(self.klus[j][self.sq])

        # powierzchnia przeciecia jest taka sama jak
        # powierzchnia obu klu
        if round(self.klus[i].geometry().area(), 3) == \
                inter.area() and \
                round(self.klus[j].geometry().area(), 3) == \
                inter.area():

            # jezeli oba sa w bazie wybieramy nielesnego
            if landid_i in self.p.uzytki and landid_j in \
                    self.p.uzytki:

                # jezeli tylko jeden z klu jest w bazie, to go
                # zostawiamy
                if self.klus[i][self.au] != 'Ls':
                    self.do_usun.append(i)
                elif self.klus[j][self.au] != 'Ls':
                    self.do_usun.append(j)

                # jezeli oba powyzsze sa ls-ami wybierz tego
                # ktory ma wiecej poligonow w swojej klasie
                elif len(self.sl_klus_grupy[landid_i]) > \
                        len(self.sl_klus_grupy[landid_j]) and \
                        len(self.sl_klus_grupy[landid_i]) > 1:
                    self.do_usun.append(i)
                else:
                    f = self.new_feat(
                        uw='nałożone identyczne poligony')
                    f.setGeometry(inter)
                    feat_do_spr.append(f)

        # powierzchnia jednego badz drugiego jest taka sama jak przeciecia
        elif round(self.klus[i].geometry().area(), 3) == inter.area():
            # jezeli uzytek jest w bazie to usuwamy albo do sprawdzenia
            if landid_i in self.p.uzytki:
                if len(self.sl_klus_grupy[landid_i]) > 1:
                    self.do_usun.append(i)
                else:
                    f = self.new_feat(
                        uw='nałożona część poligonu, do spr')
                    f.setGeometry(inter)
                    feat_do_spr.append(f)

            # jak uzytku nie ma w bazie to do usuniecia
            else:
                self.do_usun.append(i)

        elif round(self.klus[j].geometry().area(), 3) == inter.area():
            # jezeli uzytek jest w bazie to usuwamy albo do sprawdzenia
            if landid_j in self.p.uzytki:
                if len(self.sl_klus_grupy[landid_j]) > 1:
                    self.do_usun.append(j)
                else:
                    f = self.new_feat(
                        uw='nałożona część poligonu, do spr')
                    f.setGeometry(inter)
                    feat_do_spr.append(f)

            # jak uzytku nie ma w bazie to do usuniecia
            else:
                self.do_usun.append(j)

        else:
            f = self.new_feat(
                uw='nałożona część poligonu, do spr')
            f.setGeometry(inter)
            feat_do_spr.append(f)

        return self.do_usun, feat_do_spr

    def s_czy_dz_w_bazie(self):
        if self.dz['PARCELID'] in self.p.sl_kody_wlasciceli_na_dzialce:
            return True

        # jezeli brak w bazie dopisz co trzeba do klu i zostaw jako poprawne
        # self.braki_warstwa['brakb'] = {self.stworz_landid(x):
        #                               self.p.uzytki[self.stworz_landid(x)][2]
        #                               for x in self.klus}
        # for x in self.klus:
        #    f = self.new_feat(au=x[self.au], sq=x[self.sq], uw='Brak w bazie')
        #    f.setGeometry(x.geometry())
        #    self.klus_popr.append(f)
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
            landid = self.pid + klu[self.au] + \
                self.p.sl_ls_na_dz[self.pid][0]

            if len(set([x for x in self.sl_klus_pow.keys()
                        if x.split('.')[-1][:2] == 'Ls'])) == 1:
                # jezeli jest Ls ale ma inna klase - podmien SQ i dodaj do
                # raportu rozbieznosci
                if klu[self.au] == 'Ls' and \
                        klu[self.sq] != self.p.sl_ls_na_dz[self.pid][0]:

                    self.uwagi['podmsq'][landid] = [
                        klu[self.sq],
                        self.isNone(klu[self.sq])
                    ]
                    uw = 'Podmieniono SQ na zgodny z bazą, '

            # jezeli na dzialce jest tylko jeden inny uzytek, podmien na
            # brakujacy ls, o ile nie jest bledem topo
            elif len(set([x for x in self.sl_klus_pow.keys()])) == 1:
                self.uwagi['podmau'][landid] = [
                    klu[self.au] + self.isNone(klu[self.sq]),
                    'Ls' + self.p.sl_ls_na_dz[self.pid][0]
                ]
                uw = 'Podmieniono AU i SQ na zgodny z bazą, '

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
                self.klus[self.au] + \
                self.isNone(self.klus[self.sq])

            uw = ''
            if landid not in self.p.uzytki:
                uw = 'Brak w bazie, '

            f = self.new_feat(self.p.uzytki[landid][0],
                              self.p.uzytki[landid][1],
                              uw=uw)
            f.setGeometry(klu.geometry())
            self.klus_popr.append(f)
            self.do_usun.append(ii)

        # usun dopisane uzytki z poli klu
        self.s_do_usuniecia(self.do_usun, 'OK')

    def new_feat(self, au=False, sq=False, uw=False):
        f = QgsFeature(self.fid)
        self.fid += 1
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
            if 'Brak w bazie, ' not in k['UWAGI']:
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
                    self.feat_do_spr.append(self.slk[it[0]])

            else:
                feat_baza = self.slk[it[1]]
                g_bazy = self.slk[it[1]].geometry()
                g_lacz = self.slk[it[0]].geometry()

                # geometria po union
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
