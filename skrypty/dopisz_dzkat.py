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
from .baza_wrapper import znajdz_baze_do_wydz, Baza
from .baza_przetworz import Przetworz
from .ui.ui_sprawdz_dzkat import Ui_Dialog
from .pw import PasekPostepu


class DopiszDzKat(object):
    def __init__(self, iface):
        self.iface = iface
        self.lyr = False
        self.indeks = QgsSpatialIndex()

        self.dz_les_spr = []  # lista sprawdzonych dz lesnych
        self.dz_nieles = []  # lista dzialek nielesnych
        self.dz_sprawdzone = []  # lista sprawdzonych dzialek w shp
        self.dzkat_brak = []  # lista dz niewpisanych do bazy
        self.dzkat_les_pow = []  # lista dz lesnych z roznicami w pow
        self.dzkat_les_pow_zero = []  # lista dz lesnych z zerowymi pow w bazie
        self.dzkat_nieles = []  # sprawdzone dzialki nielesne w shp
        self.iatr = {}
        self.ile_dzkat = 0  # liczba wszystkich dz w shp
        self.tylko_op = []  # lista dz z kodem OP w shp

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

        self.postep = PasekPostepu(self.iface).stworz_pasek(
            'Dopisz Dzkat'
        )

    def dopisz_dane(self):
        if not self.sprawdz_dane():
            return

        # uaktulalnij pola
        self.dzkatp = self.dzkat.dataProvider()
        self.dzkatp.setEncoding('UTF-8')

        self.postep.setValue(20)
        # dodaj brakujace kolumny do warstwy
        lista_kol = [x.name() for x in self.dzkatp.fields().toList()]
        if len(lista_kol) > 0:
            self.dzkatp.addAttributes(
                [x for x in self.kolumny if x.name() not in lista_kol]
            )
            self.dzkat.updateFields()

        self.postep.setValue(40)
        self.przetworz_dane()
        self.dzkat.startEditing()
        self.zbuduj_indeks()

        for dz in self.dzkat.getFeatures():
            self.uzupelnij_dzialke(dz)
            if self.ile_dzkat % 1000 == 0:
                print("Przetworzono działek: "+str(self.ile_dzkat))

        self.dzkat.commitChanges()
        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage(
            'OK', 'Dopisano atrybuty w warstwie DZKAT!', Qgis.Success, 10
        )

    def sprawdz_dane(self):
        try:
            self.dzkat = self.iface.activeLayer()
        except:  # nopep8
            return False

        if 'PARCELID' not in [x.name() for x in
                             self.dzkat.dataProvider().fields().toList()]:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Brak kolumny PARCELID w zaznaczonej warstwie !',
                Qgis.Critical,
                0
            )
            return False

        baza_sc = znajdz_baze_do_wydz(self.iface, self.dzkat, poz=1)
        if baza_sc is not False:
            self.iface.messageBar().pushMessage(
                'Przetwarzam',
                'Dodaje dane do bazy, proszę czekać...',
                Qgis.Info,
                5
            )
            self.baza = Baza(baza_sc)
            self.baza.polacz()
            self.uzytki = self.baza.uzytki()
            self.wlasnosci = self.baza.wlasnosci()
            return True

        return False

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

        dzp = str(dz['PARCELID'])
        if len(dzp.split('.')) == 3:
            ark = dzp.split('.')[1]

        county = dzp[:2]
        district = dzp[2:4]
        municip = dzp[4:7]
        community = dzp[7:11]
        nr = dzp.split('.')[-1].rstrip('\r\n ')
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

    def przetworz_dane(self):
        # zbior unikalnych nazw dzialek lesnych
        self.dz_lesne = set([x[-1][4:] for x in self.uzytki if x[9] == "Ls"])
        # slownik z informacjami o uzytkach na dzialce
        # {GGOOOONRDZ: [WOJ, POWIAT, WYR1, PARCEL_AREA, PARCEL_INT_NUM]}
        self.dz_dict = {
            x[-1][4:]: [x[0], x[1], x[-1], x[7], x[6]]
            for x in self.uzytki}

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
                    if "OP" in item[2]:
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

    def indeks_nazw_atryb(self, dz):
        """Zbuduj indeks nazw pół w warstwie wyjściowej"""
        self.iatr = {x.name(): dz.fieldNameIndex(x.name()) for x in
                     self.kolumny}

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
            self.dzkat.changeAttributeValue(dz.id(),
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

    def zbuduj_indeks(self):
        self.indeks = QgsSpatialIndex()
        self.wszystkie_dzkat = {f.id(): f for f in self.dzkat.getFeatures()}
        for f in self.wszystkie_dzkat.values():
            self.indeks.insertFeature(f)

