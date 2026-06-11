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

        self.wl = 'OF'
        self.dz_les_spr = []  # lista sprawdzonych dz lesnych
        self.dz_sprawdzone = []  # lista sprawdzonych dzialek w shp
        self.dzkat_brak = []  # lista dz niewpisanych do bazy
        self.dzkat_les_pow = []  # lista dz lesnych z roznicami w pow
        self.dzkat_les_pow_zero = []  # lista dz lesnych z zerowymi pow w bazie
        self.dzkat_nieles = []  # sprawdzone dzialki nielesne w shp
        self.bledy_topo = []
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

        message = QMessageBox()
        message.setIcon(QMessageBox.Information)
        message.setWindowTitle('Własności')
        message.setText('Wybierz własności do analizy')
        message.addButton("OF", QMessageBox.ActionRole)
        message.addButton("OPiF", QMessageBox.ActionRole)
        wl = message.exec_()
        self.wl = 'OF' if wl == 0 else 'OP'

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
        self.postep.setValue(80)
        self.generuj_raport()
        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage(
            'OK', 'Dopisano atrybuty w warstwie DZKAT!', Qgis.Success, 10
        )

    def sprawdz_dane(self):
        try:
            self.dzkat = self.iface.activeLayer()
            self.kat = os.path.dirname(
                self.dzkat.dataProvider().dataSourceUri().split("|")[0]
            )
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
            self.p = Przetworz()
            self.p.dodaj_uzytki(self.uzytki)
            self.p.dodaj_wlasnosci(self.wlasnosci)
            self.p.przetworz_dzialki()
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
        self.dz_lesne = set([x[-1][4:] for x in self.uzytki if x[9] == "Ls"])
        self.dz_dict = {
            x[-1][4:]: [x[0], x[1], x[-1], x[7], x[6]]
            for x in self.uzytki}

        self.county = self.dz_dict[list(self.dz_dict.keys())[0]][0]
        self.district = self.dz_dict[list(self.dz_dict.keys())[0]][1]

        QgsMessageLog.logMessage("Pobrano użytków: "+str(len(self.uzytki)), "Las-R")
        QgsMessageLog.logMessage("Pobrano własności: "+str(len(self.wlasnosci)), "Las-R")

        suma_dz_wlasn = len(self.p.dz_of) + len(self.p.dz_op) + len(self.p.dz_opif)
        if suma_dz_wlasn != len(self.dz_dict.keys()):
            QgsMessageLog.logMessage(
                "Liczba działek z różnymi własnościami się nie zgadza", "Las-R")
            QgsMessageLog.logMessage(
                "Liczba działek z kodami OP: "+str(len(self.p.dz_op)), "Las-R")
            QgsMessageLog.logMessage(
                "Liczba działek z kodami OF: "+str(len(self.p.dz_of)), "Las-R")
            QgsMessageLog.logMessage(
                "Liczba działek z współwłasnościami: "+str(len(self.p.dz_opif)), "Las-R")

    def indeks_nazw_atryb(self, dz):
        """Zbuduj indeks nazw pół w warstwie wyjściowej"""
        self.iatr = {x.name(): dz.fieldNameIndex(x.name()) for x in
                     self.kolumny}

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

        if lacznik in self.p.dz_op:
            u = u._replace(GRP='99')
            uwaga += 'Dzialka tylko z wlasnoscia OP; '
            self.tylko_op.append(lacznik)
        elif lacznik in self.p.dz_opif:
            u = u._replace(GRP='99')
        elif lacznik in self.p.dz_of:
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
                self.dzkat_nieles.append(lacznik)
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

    def generuj_raport(self):  # noqa
        """Metoda generuje raport dla uzytkownika, zapisany w katalogu z warst.
        wyjsciowa w postaci pliku tekstowego z data i godzina w nazwie"""

        raport = '---RAPORT----------------------------\n\n'
        raport += 'Działek w shp: ' + str(self.ile_dzkat) + '\n'
        if self.wl == 'OF':
            ile_dz_baza = [x for x in self.dz_lesne if x not in self.tylko_op]
        else:
            ile_dz_baza = [x for x in self.dz_lesne]
        raport += 'Działek leśnych w bazie: ' + str(len(ile_dz_baza)) + '\n'

        brakujace_dz_les = [x for x in list(self.dz_lesne)
                            if x not in self.dz_les_spr]
        if self.wl == 'OF':
            ile_brak = len([x for x in brakujace_dz_les
                            if x not in self.tylko_op])
        else:
            ile_brak = len(brakujace_dz_les)

        raport += 'Brakujące działki leśne: ' + str(ile_brak) + '\n\n'

        if self.wl == 'OF':
            dz_les = len([x for x in self.dz_les_spr
                          if x not in self.tylko_op])
        else:
            dz_les = len(self.dz_les_spr)

        raport += 'Działek leśnych w shp: ' + str(dz_les) + '\n'
        raport += 'Działek nieleśnych w shp: ' + \
            str(len(self.dzkat_nieles)) + '\n'

        duble = [x[0] for x in Counter(
            self.dz_les_spr+self.dzkat_nieles).most_common()
            if x[1] > 1]
        raport += 'Działki Zdublowane: ' + str(len(duble)) + '\n\n'

        if len(self.bledy_topo) > 0:
            raport += 'Działki z błędami topologicznymi: ' + \
                str(len(self.bledy_topo)) \
                + '\n\n\n'

        if len(self.dzkat_les_pow_zero) > 0:
            raport += 'Działek z zerowymi powierzchniami w bazie: ' + str(len(
                self.dzkat_les_pow_zero)) + '\n'

        if len(self.dzkat_brak) > 0:
            raport += 'Działek z brakiem opisu w bazie: ' + \
                str(len(self.dzkat_brak)) + '\n'

        # wypisz do logu podstawowy raport
        QgsMessageLog.logMessage(raport, 'Las-R')

        if ile_brak > 0:
            raport += '\n\n---BRAKUJACE DZIALKI LEŚNE--------------' + '\n'
            raport += 'Brakujace dzialki lesne w shp: ' + \
                str(ile_brak) + '\n\n'

            if self.wl == 'OF':
                braki = [x for x in sorted(brakujace_dz_les)
                         if x not in self.tylko_op]
            else:
                braki = [x for x in sorted(brakujace_dz_les)]

            raport += '\n'.join([
                '\t'.join([self.county+self.district+x,
                           str(self.wypiszPow(x, self.dz_dict))])
                for x in braki
            ])
            raport += '\n' + 45 * '-' + '\n\n\n'

        if len(self.dzkat_nieles) > 0:
            raport += "---DZIALKI NIELESNE--------------------------\n"
            raport += "Dzialek nielesnych w shp: " + \
                str(len(self.dzkat_nieles)) + '\n\n'
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
                    [self.county + self.district + x
                     for x in sorted(self.dzkat_brak)])
            else:
                raport += 'liste dzialek pominieto'
            raport += '\n' + 45 * '-' + '\n\n\n'

        # sprawdz zdublowane dzialki i wypisz tylko w lesnych
        if len(duble) > 0:
            raport += "-----DZIALKI ZDUBLOWANE------------------------\n"
            raport += "Dzialki zdublowane: " + str(len(duble)) + '\n\n'
            raport += '\n'.join([self.county + self.district + x for x in
                                 sorted(duble)])
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

        if len(self.p.listaOP) > 0:
            raport += "--LISTA WLASCICIELI Z KODEM OP-----------------\n"
            if self.wl == 'OF':
                wl = [x[0] for x in self.p.listaOP
                      if x[1] not in self.tylko_op and x[1] in self.dz_lesne]
            else:
                wl = [x[0] for x in self.p.listaOP if x[1] in self.dz_lesne]
            raport += "Liczba wlascicieli z kodem OP: " + str(len(set(wl))) + \
                '\n\n'

            sl_temp = {}
            for x in self.p.listaOP:
                if x[1] in self.dz_lesne:
                    if self.wl == 'OF' and x[1] in self.tylko_op:
                        pass
                    else:
                        if x[0] not in sl_temp:
                            sl_temp[x[0]] = []
                        sl_temp[x[0]].append(x[1])

            raport += '\n'.join([x + '\t' + str(len(sl_temp[x])) + " dzkat"
                                 for x in sorted(list(sl_temp.keys()))])
            raport += '\n' + 45 * '-' + '\n\n\n'

        raport += "---KONIEC RAPORTU----------------------------------"

        # zapisz raport do pliku
        self.czas = datetime.now().isoformat().replace(
            ":", "")[:-7].replace('-', '')
        self.rap_sc = os.path.join(self.kat, '..',
                                   'dzkat_dopisane_'+self.czas+'.txt')
        plik = open(self.rap_sc, 'w', encoding='cp1250')
        plik.write(raport)
        plik.close()

        message = QMessageBox()
        message.setIcon(QMessageBox.Information)
        message.setWindowTitle('Raport')
        message.setText('Czy wyświetlić raport z kontroli działek?')
        message.addButton(u"Zamknij", QMessageBox.ActionRole)
        message.addButton(u"Zamknij i pokaż raport", QMessageBox.ActionRole)
        pok_rap = message.exec_()

        if pok_rap == 1:
            if platform.system()[:3] == 'Win':
                os.startfile(self.rap_sc)
            else:
                import subprocess
                subprocess.call(['kate', self.rap_sc])
