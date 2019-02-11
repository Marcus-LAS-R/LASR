import os
import re
import glob
import platform
import shutil
from datetime import datetime
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QVariant
from qgis.core import QgsVectorLayer, QgsMessageLog, QgsField, \
    QgsProject, QgsSpatialIndex, QgsCoordinateReferenceSystem, \
    QgsVectorFileWriter, QgsFeature, Qgis
import processing
from collections import Counter, namedtuple
from .baza_wrapper import Baza
from .ui.ui_sprawdz_dzkat import Ui_Dialog
from .pw import PasekPostepu


class SprawdzDzKat(object):
    def __init__(self, iface):
        self.iface = iface
        self.lyr = False

        # sprawdz czy uzyszkodnik zaznaczyl warstwe
        try:
            self.lyr = self.iface.activeLayer()
        except:  # noqa
            pass

        analizuj = AnalizujDzKat(self.lyr, self.iface)
        analizuj.pobierz_dane_od_uzytkownika()
        if not analizuj.warunki_spenione():
            return
        self.iface.messageBar().pushMessage(
            'BŁĄD',
            'Warunki początkowe nie zostały spełnione',
            Qgis.Critical, 10
        )

        self.postep = PasekPostepu(self.iface).stworz_pasek(
            'Generowanie Dzkat'
        )
        analizuj.pobierz_dane()
        self.postep.setValue(20)
        analizuj.przetworz_dane()
        self.postep.setValue(40)
        analizuj.przygotuj_warstwe_wyjsciowa()

        if not analizuj.lyrw.isValid():
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Warstwa wyjściowa nie jest poprawna, podeślij dane do autora',
                Qgis.Critical, 10
            )
            return

        self.postep.setValue(60)
        analizuj.iteruj_dzialki()
        self.postep.setValue(70)
        analizuj.generuj_raport()
        self.postep.setValue(80)
        analizuj.skasuj_kolumny()
        self.postep.setValue(90)
        analizuj.dodaj_warstwy_do_mapy()
        self.postep.setValue(100)

        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage(
            'OK', 'Przetworzono warstwę DZKAT!', Qgis.Success, 10
        )


class AnalizujDzKat(object):
    def __init__(self, l, i):
        self.lyr = l
        self.iface = i
        self.indeks = False
        self.lyrw = False  # warstwa wyjsciowa
        self.bledy_topo = []  # lista feats, ktore przecinaja sie z innymi
        self.iatr = False  # indeks pól w warstwie wyjsciowej
        self.county = ''  # kod wojewodztwa
        self.district = ''  # kod powiatu
        self.dz_nieles = []  # lista dzialek nielesnych

        self.czas = datetime.now().isoformat().replace(":",
                                                       "")[:-7].replace('-',
                                                                        '')

        self.kolumny = [
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

        self.uzup_temp = namedtuple('uzuplenienie', [
            x.name() for x in self.kolumny
            # 'county', 'district', 'municip', 'community', 'nr',
            # 'parid', 'grp', 'ark', 'nieles', 'uw', 'powar', 'powgraf',
        ])

    def pobierz_dane_od_uzytkownika(self):
        self.dd = PobierzDane(self.lyr)
        self.dd.exec_()

    def warunki_spenione(self):
        if self.dd.ile_baz > 0 and self.lyr.isValid():
            return True
        return False

    def pobierz_dane(self):
        self.lyr = self.dd.lyr

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
        self.adradm = self.dd.ui.comboBox_kol_adradm.currentText()
        self.gm = self.dd.ui.comboBox_kol_gm.currentText()
        self.obr = self.dd.ui.comboBox_kol_obr.currentText()
        self.nrdz = self.dd.ui.comboBox_kol_nrdz.currentText()
        self.ark = self.dd.ui.comboBox_kol_ark.currentText()
        # PARCELID nie jest dodany, ale dialog sprawdza czy jest w wybranej
        # przez uzytkownika warstwie

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

    def przetworz_dane(self):
        # zbior unikalnych nazw dzialek lesnych
        self.dz_lesne = set([x[-1][4:] for x in self.uzytki if x[9] == "Ls"])
        # slownik z informacjami o uzytkach na dzialce
        # {GGOOOONRDZ: [WOJ, POWIAT, WYR1, PARCEL_AREA, PARCEL_INT_NUM]}
        self.dz_dict = {x[-1][4:]: [x[0], x[1], x[-1], x[7], x[6]] for x in self.uzytki}

        # dopisz kody woj i powiatu
        self.county = self.dz_dict[list(self.dz_dict.keys())[0]][0]
        self.district = self.dz_dict[list(self.dz_dict.keys())[0]][1]

        # slownik z kodami wlasciciel dla kazdej dzialki
        # {Wyr1: ['OP', 'OF' ...]}
        self.wl_dict = {}

        QgsMessageLog.logMessage("Pobrano użytków: "+str(len(self.uzytki)),
                                 "Las-R")
        QgsMessageLog.logMessage("Pobrano własności: " +
                                 str(len(self.wlasnosci)),
                                 "Las-R"
                                 )
        # lista wlascicieli z kodami OP
        # [[wlasciciel, wyr1], ...]
        self.lista_OP = []
        # slownik z wlasnosciami wlasciciela
        # {wlascieciel: [wyr1, ...]}
        self.sl_wlasnosci = {}

        for item in self.wlasnosci:
            wyr1 = item[-4] + item[-3] + '.'
            if item[-2] not in ["", " ", None]:
                wyr1 += item[-2] + "."
            wyr1 += item[-1]
            # oczysc nazwe wlasciciela z pustych znakow
            wlasciciel = item[1].rstrip(' \t\r\n')

            # dodaj wlasnosci danego wlasciciela do slownika
            if wlasciciel not in self.sl_wlasnosci:
                self.sl_wlasnosci[wlasciciel] = []
            self.sl_wlasnosci[wlasciciel].append(wyr1)

            if wyr1 not in self.wl_dict:
                self.wl_dict[wyr1] = []
            if item[2] != "":
                if re.search('NIEUSTAL', wlasciciel) or \
                        wlasciciel in ['???', ]:
                    self.wl_dict[wyr1].append("OF")
                else:
                    self.wl_dict[wyr1].append(item[2])
                    if item[2] == "OP":
                        self.lista_OP.append([wlasciciel, wyr1])

        # lista dzialek tylko z wlasnoscia OP
        self.dz_wlasnosci_op = [k for k, val in self.wl_dict.items()
                                if set(['OP']) == set(val)]

        # lista dzialek z wlasnosciami
        self.dz_wlasnosci_opif = [k for k, val in self.wl_dict.items()
                                  if set(['OP', 'OF']) == set(val)]

        # lista dzialek tylko z wlasnoscia OF
        self.dz_wlasnosci_of = [k for k, val in self.wl_dict.items()
                                if set(['OF']) == set(val)]

        # sprawdz czy liczba działek z poszczególnymi własnościami zgadza się z
        # suma wszystkich działek
        suma_dz_wlasn = len(self.dz_wlasnosci_of) + \
            len(self.dz_wlasnosci_op) + \
            len(self.dz_wlasnosci_opif)

        if suma_dz_wlasn != len(self.dz_dict.keys()):
            QgsMessageLog.logMessage(
                "Liczba działek z różnymi własnościami się nie zgadza",
                "Las-R"
            )
            QgsMessageLog.logMessage(
                "Liczba działek z kodami OP: "+str(len(self.dz_wlasnosci_op)),
                "Las-R"
            )
            QgsMessageLog.logMessage(
                "Liczba działek z kodami OF: "+str(len(self.dz_wlasnosci_of)),
                "Las-R"
            )
            QgsMessageLog.logMessage(
                "Liczba działek z współwłasnościami: " +
                str(len(self.dz_wlasnosci_opif)),
                "Las-R"
            )

    def przygotuj_warstwe_wyjsciowa(self):
        """Metoda przygotowuj warstwe wyjsciowa razem z ukladem atrybutow
        ale ich nie uzupełnia"""
        # jezeli uzytkownik wybral pole 'PARCELID' najpierw zrob dissolva
        sciezka = self.lyr.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        if self.typ == 'PAR':
            processing.run("native:dissolve", {
                'INPUT': self.lyr.name(),
                'FIELD': "PARCELID",
                'OUTPUT': sciezka+'__dissolve.shp'
            })

            # self.lyr = QgsVectorLayer(sciezka+'_dissolve.shp', "DZKAT_robocze", "ogr")
            shutil.copy(sciezka+"__dissolve.shp",
                        os.path.dirname(sciezka)+os.sep+"DZKAT_"+self.czas+".shp")
            shutil.copy(sciezka+"__dissolve.shx",
                        os.path.dirname(sciezka)+os.sep+"DZKAT_"+self.czas+".shx")
            shutil.copy(sciezka+"__dissolve.dbf",
                        os.path.dirname(sciezka)+os.sep+"DZKAT_"+self.czas+".dbf")
            shutil.copy(sciezka+"__dissolve.prj",
                        os.path.dirname(sciezka)+os.sep+"DZKAT_"+self.czas+".prj")
        else:
            shutil.copy(sciezka+".shp",
                        os.path.dirname(sciezka)+os.sep+"DZKAT_"+self.czas+".shp")
            shutil.copy(sciezka+".shx",
                        os.path.dirname(sciezka)+os.sep+"DZKAT_"+self.czas+".shx")
            shutil.copy(sciezka+".dbf",
                        os.path.dirname(sciezka)+os.sep+"DZKAT_"+self.czas+".dbf")
            shutil.copy(sciezka+".prj",
                        os.path.dirname(sciezka)+os.sep+"DZKAT_"+self.czas+".prj")

        # podmien warstwe na ostateczną
        self.lyrw = QgsVectorLayer(
            os.path.dirname(sciezka)+os.sep+"DZKAT_"+self.czas+".shp",
            "DZKAT_"+self.czas,
            "ogr"
        )
        self.lyrwp = self.lyrw.dataProvider()
        self.lyrwp.setEncoding(u'UTF-8')

        # dodaj brakujace kolumny do warstwy
        lista_kol = [x.name() for x in self.lyrwp.fields().toList()]
        self.lyrwp.addAttributes(
            [x for x in self.kolumny if x.name() not in lista_kol]
        )
        self.lyrw.updateFields()

    def dodaj_warstwy_do_mapy(self):
        """Metoda dodaje warstwy do TOC aktualnej instancji qgis-a"""
        QgsProject.instance().addMapLayer(self.lyrw)

        if len(self.bledy_topo) > 0:
            self.generuj_warstwe_bledow()
            QgsProject.instance().addMapLayer(self.lyrb)
        else:
            QgsMessageLog.logMessage("Brak błędów topologicznych",
                                     "Las-R")

        message = QMessageBox()
        message.setIcon(QMessageBox.Information)
        message.setWindowTitle('Raport')
        message.setText('Czy wyświetlić raport z generowania działek?')
        message.addButton(u"Zamknij", QMessageBox.ActionRole)
        message.addButton(u"Zamknij i pokaż raport", QMessageBox.ActionRole)
        pok_rap = message.exec_()

        if pok_rap == 1:
            if platform.system()[:3] == 'Win':
                os.startfile(self.rap_sc)
            else:
                import subprocess
                subprocess.call(['open-xdg', self.rap_sc])

    def generuj_warstwe_bledow(self):
        self.lyrb = QgsVectorLayer("Polygon?crs=epsg:2180&index=yes",
                                   "BLEDY_TOPO",
                                   "memory")
        self.lyrb.startEditing()
        self.lyrb.dataProvider().addAttributes([
            QgsField("MUNICIP", QVariant.String, len=3),
            QgsField("COMMUNITY", QVariant.String, len=4),
            QgsField("PARCELNR", QVariant.String, len=20),
        ])
        self.lyrb.updateFields()

        etykFeat = []
        for f in self.bledy_topo:
            feat = QgsFeature()
            feat.setGeometry(f.geometry())
            feat.setFields(self.lyrb.fields())
            uzupf = self.lyrw.getFeature(f.id())
            feat['PARCELNR'] = uzupf['PARCELNR']
            feat['MUNICIP'] = uzupf['MUNICIP']
            feat['COMMUNITY'] = uzupf['COMMUNITY']
            etykFeat.append(feat)

        self.lyrb.dataProvider().addFeatures(etykFeat)
        self.lyrb.commitChanges()

        crs = QgsCoordinateReferenceSystem("epsg:2180")
        error = QgsVectorFileWriter.writeAsVectorFormat(
            self.lyrb,
            os.path.join(self.kat, "BLEDY_TOPO_"+self.czas+".shp"),
            "UTF-8",
            crs,
            "ESRI Shapefile")
        QgsMessageLog.logMessage(os.path.join(self.kat,
                                              "BLEDY_TOPO_"+self.czas+".shp"),
                                 "Las-R")
        if error == QgsVectorFileWriter.NoError:
            QgsMessageLog.logMessage("Warstwa DZKAT_OPS zapisana!", "Las-R")
            self.lyrb = self.iface.addVectorLayer(
                os.path.join(self.kat, "BLEDY_TOPO_"+self.czas+".shp"),
                "BLEDY_TOPO",
                "ogr"
            )

    def zbuduj_indeks(self):
        self.indeks = QgsSpatialIndex()
        self.wszystkie_dzkat = {f.id(): f for f in self.lyrw.getFeatures()}
        for f in self.wszystkie_dzkat.values():
            self.indeks.insertFeature(f)

    def indeks_nazw_atryb(self, dz):
        """Zbuduj indeks nazw pół w warstwie wyjściowej"""
        self.iatr = {x.name(): dz.fieldNameIndex(x.name()) for x in
                     self.kolumny}

    def iteruj_dzialki(self):
        self.dzkat_nieles = []  # sprawdzone dzialki nielesne w shp
        self.dzkat_brak = []  # lista dz niewpisanych do bazy
        self.dz_les_spr = []  # lista sprawdzonych dz lesnych
        self.dzkat_les_pow = []  # lista dz lesnych z roznicami w pow
        self.dzkat_les_pow_zero = []  # lista dz lesnych z zerowymi pow w bazie
        self.ile_dzkat = 0  # liczba wszystkich dz w shp
        self.dz_sprawdzone = []  # lista sprawdzonych dzialek w shp
        self.tylko_op = []  # lista dz z kodem OP w shp

        if not self.lyrw.isValid():
            QgsMessageLog.logMessage(
                "Jednak warstwa nie jest Valid ?!?",
                "Las-R")
            return

        self.zbuduj_indeks()

        self.lyrw.startEditing()

        for dz in self.lyrw.getFeatures():
            self.uzupelnij_dzialke(dz)
            if self.ile_dzkat % 1000 == 0:
                print("Przetworzono działek: "+str(self.ile_dzkat))

        self.lyrw.commitChanges()

    def uzupelnij_dzialke(self, dz):  # noqa
        """Metoda uzupełnia pola atrybutów w warstwie ostatecznej oraz sprawdza
        zależności i zgodność z bazami taksatora"""

        # zbuduj indeks pól atrybutów do edycji, jezeli go jeszcze nie ma
        if not self.iatr:
            self.indeks_nazw_atryb(dz)

        # sformatuj uwage ktora zostanie dopisana do tej dzialki
        uwaga = ''

        self.ile_dzkat += 1
        u = self.dz_uzupelnij_adres(dz)
        lacznik = self.dz_lacznik(u)

        if lacznik in self.dz_wlasnosci_op:
            u = u._replace(GRP='99')
            uwaga += 'Dzialka tylko z wlasnoscia OP; '
            self.tylko_op.append(lacznik)
        elif lacznik in self.dz_wlasnosci_opif:
            u = u._replace(GRP='99')
        # gdy wlasnosc OF ustaw grupe na 10
        elif lacznik in self.dz_wlasnosci_of:
            u = u._replace(GRP='10')

        # sprawdz czy dzialka nie byla juz wczesniej sprawdzana, jesli tak
        # oznacz jako duplikat
        if lacznik in self.dz_sprawdzone:
            uwaga += 'Dzialka zdublowana; '
        else:
            self.dz_sprawdzone.append(lacznik)

        # dopisz parcel_id i powierzchnie rejestrowa o ile dzialka w bazie
        if lacznik in self.dz_dict:
            u = u._replace(PARCELID=u.COUNTY+u.DISTRICT+lacznik,
                           PARCEL_AR=self.dz_dict[lacznik][3],
                           )
            # dodaj laczniki do odpowiednich list i oznacz dzialke jako lesna
            # badz nie
            if lacznik not in self.dz_lesne:
                u = u._replace(NIELES='TAK')
                self.dz_nieles.append(lacznik)
            else:
                self.dz_les_spr.append(lacznik)

            # sprawdz czy powierzchnia dzialki nie ma za duzych odchylow
            pg = u.PARCEL_POW
            pr = u.PARCEL_AR
            if pg > 0.3 or pr > 0.3:
                if abs(pg - pr) > 0.1999:
                    self.dzkat_les_pow.append([lacznik, pg, pr])
                    uwaga += "Dzialka z duza rozbieznoscia pow; "
                if pr == 0:
                    self.dzkat_les_pow_zero.append(lacznik)

            # sprawdz czy dzialka nie przecina sie z inna
            topologia, lista = self.dz_sprawdz_topologie(dz)
            if topologia:
                uwaga += "Dzialka, nachodzi na inna, id:["+", ".join(lista)+"]"
                self.bledy_topo.append(dz)
        else:
            self.dzkat_brak.append(lacznik)

        u = u._replace(UWAGI=uwaga)

        # dopisz zebrane dane do feature'a w warstwie
        for key, val in u._asdict().items():
            self.lyrw.changeAttributeValue(dz.id(),
                                           self.iatr[key],
                                           val
                                           )

    def dz_sprawdz_topologie(self, dz):
        # jezeli nie ma zbudowanego indeksu zwracaj brak przeciecia
        if not isinstance(self.indeks, QgsSpatialIndex):
            return False, []

        ids = self.indeks.intersects(dz.geometry().boundingBox())
        lista = []
        for id in ids:
            f = self.wszystkie_dzkat[id]
            if dz.geometry().buffer(-0.005, 5).intersects(f.geometry()) and \
                    dz.id() != f.id():
                lista.append(str(f.id()))

        # jezeli dzialka pokrywa sie z inna dodaj opis w warstwie ostatecznej
        if len(lista) > 0:
            return True, lista
        return False, lista

    def dz_uzupelnij_adres(self, dz):
        """Metoda wymaga podania feature z warstwy na podstawie ktorego tworzy
        namedtuple z dodanymi kodami administracyjnymi i powierzchnia graf"""

        # stworz nowa nazwana krotke

        uzup = self.uzup_temp(' ', ' ', ' ', ' ', ' ',
                              ' ', ' ', ' ', ' ', ' ',
                              0.0000, 0.0000)

        # domyslnie grupa rejestrowa jest 99 (OP)
        uzup._replace(GRP=' ')

        # uzupełnij pola na podstawie metody identyfikujacej jaka wybral
        # uzytkownik
        ark = ' '
        county = ''
        district = ''
        municip = ''
        community = ''
        nr = ''
        powgraf = round(dz.geometry().area()/10000, 4)

        if self.typ == u'PAR':
            dzp = str(dz['PARCELID'])
            if len(dzp.split('.')) == 3:
                ark = dzp.split('.')[1]

            county = dzp[:2]
            district = dzp[2:4]
            municip = dzp[4:7]
            community = dzp[7:11]
            nr = dzp.split('.')[-1]

        elif self.typ == u'Adr':
            dzp = str(dz[self.adradm])
            if len(dzp.split('.')) == 4:
                ark = dzp.split('.')[-2]

            county = dzp[:2]
            district = dzp[2:4]
            municip = dzp.split('.')[0].replace('_', '')[-3:]
            community = dzp.split('.')[1]
            nr = dzp.split('.')[-1]

        elif self.typ == u'Kol':
            if self.ark != '---':
                ark = dz[self.ark]

            county = self.county
            district = self.district
            municip = dz[self.gm]
            community = dz[self.obr]
            nr = dz[self.nrdz]
            ark = ark
        else:
            QgsMessageLog.logMessage(
                'Nie udało się przyporzadkowac zadnego wyboru',
                "Las-R")

        uzup = uzup._replace(
            COUNTY=county,
            DISTRICT=district,
            MUNICIP=municip,
            COMMUNITY=community,
            PARCELNR=nr,
            ARK=ark,
            PARCEL_POW=powgraf,
        )

        return uzup

    def dz_lacznik(self, uzup):
        # stworz lacznik do danych z bazy
        if uzup.ARK not in ['', ' ']:
            lacznik = '.'.join([uzup.MUNICIP+uzup.COMMUNITY,
                                uzup.ARK,
                                uzup.PARCELNR,
                                ]
                               )
        else:
            lacznik = uzup.MUNICIP + uzup.COMMUNITY + "." + uzup.PARCELNR

        return lacznik

    def generuj_raport(self):  # noqa
        """Metoda generuje raport dla uzytkownika, zapisany w katalogu z warst.
        wyjsciowa w postaci pliku tekstowego z data i godzina w nazwie"""

        raport = '---RAPORT----------------------------\n\n'
        raport += 'Działek w shp: ' + str(self.ile_dzkat) + '\n'
        raport += 'Działek leśnych w bazie: ' + str(len(
            [x for x in self.dz_lesne if x not in self.tylko_op]
        )) + '\n'

        brakujace_dz_les = [x for x in list(self.dz_lesne)
                            if x not in self.dz_les_spr]
        raport += 'Brakujące działki leśne: ' + str(len(
            [x for x in brakujace_dz_les if x not in self.tylko_op]
        )) + '\n\n'

        raport += 'Działek leśnych w shp: ' + str(len(self.dz_les_spr)) + '\n'
        raport += 'Działek nieleśnych w shp: ' + str(len(self.dzkat_nieles)) + '\n'

        duble = [x[0] for x in Counter(self.dz_les_spr+self.dzkat_nieles).most_common()
                 if x[1] > 1]
        raport += 'Działki Zdublowane: ' + str(len(duble)) + '\n\n'

        if len(self.bledy_topo) > 0:
            raport += 'Działki z błędami topologicznymi: ' + str(len(self.bledy_topo)) \
                      + '\n\n\n'

        if len(self.dzkat_les_pow_zero) > 0:
            raport += 'Działek z zerowymi powierzchniami w bazie: ' + str(len(
                self.dzkat_les_pow_zero)) + '\n'

        if len(self.dzkat_brak) > 0:
            raport += 'Działek z brakiem opisu w bazie: ' + str(len(self.dzkat_brak)) + '\n'

        # wypisz do logu podstawowy raport
        QgsMessageLog.logMessage(raport, 'Las-R')

        if len(self.dzkat_brak) > 0:
            raport += '\n\n---BRAKUJACE DZIALKI LESNE--------------' + '\n'
            raport += 'Brakujace dzialki lesne w shp: ' + \
                str(len(self.dzkat_brak)) + '\n\n'
            raport += '\n'.join([
                '\t'.join([self.county+self.district+x,
                           str(self.wypiszPow(x, self.dz_dict))])
                for x in sorted(brakujace_dz_les) if x not in self.tylko_op
            ])
            raport += '\n' + 45 * '-' + '\n\n\n'

        if len(self.dzkat_nieles) > 0:
            raport += "---DZIALKI NIELESNE--------------------------\n"
            raport += "Dzialek nielesnych w shp: " + str(len(self.dzkat_nieles)) + '\n\n'
            if len(self.dzkat_nieles) < 200:
                raport += '\n'.join([self.county + self.district + x
                                    for x in sorted(self.dzkat_nieles)])
            else:
                raport += 'Liste dzialek pominieto'
            raport += '\n' + 45 * '-' + '\n\n\n'

        # sprawdz brakujace dzialki
        if len(self.dzkat_brak) > 0:
            raport += "---DZIALKI BEZ OPISU-------------------------\n"
            raport += "Dzialki z brakiem opisu w bazie: " + str(
                len(self.dzkat_brak)) + '\n\n'
            if len(self.dzkat_brak) < 200:
                raport += '\n'.join(
                    [self.county + self.district + x for x in sorted(self.dzkat_brak)])
            else:
                raport += 'liste dzialek pominieto'
            raport += '\n' + 45 * '-' + '\n\n\n'

        # sprawdz zdublowane dzialki i wypisz tylko w lesnych
        if len(duble) > 0:
            raport += "-----DZIALKI ZDUBLOWANE------------------------\n"
            raport += "Dzialki zdublowane: " + str(len(duble)) + '\n\n'
            raport += '\n'.join([self.county + self.district + x for x in sorted(duble)])
            raport += '\n' + 45 * '-' + '\n\n\n'

        if len(self.dzkat_les_pow_zero) > 0:
            raport += "--DZIALKI Z ZEROWA POWIERZCHNIA----------------\n"
            raport += "Dzialki z zerowa powierzchnia: "
            raport += str(len(self.dzkat_les_pow_zero)) + '\n\n'
            raport += '\n'.join([self.county + self.district + x for x in
                                sorted(self.dzkat_les_pow_zero)])
            raport += '\n' + 45 * '-' + '\n\n\n'

        if len(self.dzkat_les_pow) > 0:
            raport += "--DZIALKI ZE ZNACZNA ROZNICA POWIERZCHNI-------\n"
            raport += "Dzialki z duza rozbieznoscia powierzchni: " + str(
                len(self.dzkat_les_pow)) + '\n\n'
            raport += "Adres adm dzialki\tpow_graf\tpow_rej\troznica" + '\n'
            rr = sorted([[self.county + self.district + x[0], x[1], x[2],
                          round(abs(x[1] - x[2]), 4)]
                         for x in self.dzkat_les_pow],
                        key=lambda s: s[3], reverse=True)
            raport += '\n'.join(["\t".join(map(str, x)) for x in rr])
            raport += '\n' + 45 * '-' + '\n\n\n'

        if len(self.lista_OP) > 0:
            raport += "--LISTA WLASCICIELI Z KODEM OP-----------------\n"
            raport += "Liczba wlascicieli z kodem OP: " + str(len(set(
                [x[0] for x in self.lista_OP
                 if x[1] not in self.tylko_op and x[1] in self.dz_lesne]))) + '\n\n'

            sl_temp = {}
            for x in self.lista_OP:
                # przygotuj slownik wlascicieli z liczba dzialek ktorzy nie sa w tylkoOP
                # jezeli dopisujemy wszystkie wlasnosci, to raportze wszystkich
                if x[1] not in self.tylko_op and x[1] in self.dz_lesne:
                    if x[0] not in sl_temp:
                        sl_temp[x[0]] = []
                    sl_temp[x[0]].append(x[1])

            raport += '\n'.join([x + '\t' + str(len(sl_temp[x])) + " dzkat" for x in
                                sorted(list(sl_temp.keys()))])
            raport += '\n' + 45 * '-' + '\n\n\n'

        raport += "---KONIEC RAPORTU----------------------------------"

        # zapisz raport do pliku
        self.rap_sc = os.path.join(self.kat, 'dzkat_raport_'+self.czas+'.txt')
        open(self.rap_sc, 'wb').write(raport.encode('cp1250'))

    def wypiszPow(self, x, sl):
        if x in sl:
            return sl[x][3]
        else:
            return "---"

    def skasuj_kolumny(self):
        self.lyrw.startEditing()
        nadmiarowe = sorted([self.lyrw.dataProvider().fieldNameIndex(x.name())
                             for x in self.lyrw.fields().toList()
                             if x.name() not in
                             [y.name() for y in self.kolumny]],
                            reverse=True)
        self.lyrw.dataProvider().deleteAttributes(nadmiarowe)
        self.lyrw.updateFields()
        self.lyrw.commitChanges()


class PobierzDane(QDialog):
    def __init__(self, w):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.lyr = w
        self.pola = []
        self.ile_baz = 0

        # Jezeli jest warstwa, odczytaj jej dane
        if self.lyr:
            if self.lyr.isValid():
                self.ui.lineEdit_warstwa.setText(
                    self.lyr.dataProvider().dataSourceUri().split("|")[0])
                self.ui.comboBox_ident.setDisabled(False)
                self.wczytaj_pola()

        self.ui.pushButton_warstwa.clicked.connect(self.pobierz_warstwe)
        self.ui.pushButton_bazy.clicked.connect(self.pobierz_bazy)
        self.ui.comboBox_ident.currentTextChanged.connect(self.identyfikuj)
        self.ui.pushButton_ok.clicked.connect(self.ok)

    def ok(self):
        self.hide()

    def wczytaj_pola(self):
        """Metoda uzupelnia comboboxy na podstawie podanej warstwy"""
        # wybierz nazwy pol z warstwy, ktore nie sa numeryczne
        self.pola = ['---'] + [x.name() for x in self.lyr.dataProvider().fields().toList()
                               if not x.isNumeric()]

        # wyczysc wszystkie comboboxy z kolumnami
        comboboxy = [
            self.ui.comboBox_kol_adradm,
            self.ui.comboBox_kol_gm,
            self.ui.comboBox_kol_obr,
            self.ui.comboBox_kol_nrdz,
            self.ui.comboBox_kol_ark,
        ]

        # wyczysc i dodaj przetworzone pola do comboboxow
        for x in comboboxy:
            x.clear()
            x.addItems(self.pola)

    def pobierz_warstwe(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę i ją przetwarza"""
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę',
                                                '',
                                                "ESRI shp (*.shp)")[0]
        try:
            self.lyr = QgsVectorLayer(warstwa, "dz_ewid", "ogr")
            self.ui.lineEdit_warstwa.setText(
                self.lyr.dataProvider().dataSourceUri().split("|")[0])
            self.ui.comboBox_ident.setDisabled(False)
        except:  # nopep8
            msbx = QMessageBox('Nie udało się otworzyć podanej warstwy')
            msbx.exec_()
            self.lyr = False
            self.ui.comboBox_ident.setDisabled(True)

    def pobierz_bazy(self):
        """Metoda pobiera wskazany przez użytkownika katalog"""
        kat = ""
        if self.lyr:
            kat = os.path.dirname(
                self.lyr.dataProvider().dataSourceUri().split("|")[0]
            )
        bazy_kat = QFileDialog().getExistingDirectory(
            self,
            "Katalog z bazami danych",
            kat
        )
        self.ile_baz = len(glob.glob(os.path.join(bazy_kat, '*.mdb')))
        if self.ile_baz > 0:
            self.ui.label_bazy_wynik.setText("Znalazałem baz: " +
                                             str(self.ile_baz))
            self.ui.lineEdit_bazy.setText(bazy_kat)

        else:
            self.ui.label_bazy_wynik.setText("Nie znaleziono baz *.mdb")

    def identyfikuj(self):
        """ Metoda sprawdza wybór uzytkownika i
            udostepnia odpowiednie pola do wyboru"""
        if self.ui.comboBox_ident.currentText() == '---':
            self.ui.groupBox_adradm.setDisabled(True)
            self.ui.groupBox_kol.setDisabled(True)
            self.ui.pushButton_ok.setDisabled(True)
        elif self.ui.comboBox_ident.currentText()[:3] == 'Adr':
            self.ui.groupBox_adradm.setDisabled(False)
            self.ui.pushButton_ok.setDisabled(False)
            self.ui.groupBox_kol.setDisabled(True)
        elif self.ui.comboBox_ident.currentText()[:3] == 'Kol':
            self.ui.groupBox_adradm.setDisabled(True)
            self.ui.pushButton_ok.setDisabled(False)
            self.ui.groupBox_kol.setDisabled(False)
        elif self.ui.comboBox_ident.currentText()[:3] == 'PAR':
            self.ui.groupBox_adradm.setDisabled(True)
            if 'PARCELID' in self.pola:
                self.ui.pushButton_ok.setDisabled(False)
            else:
                self.ui.pushButton_ok.setDisabled(True)
            self.ui.groupBox_kol.setDisabled(True)
