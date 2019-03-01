import os
import platform
import glob
from collections import Counter
from qgis.core import QgsVectorLayer, QgsMessageLog, QgsProject, Qgis, \
    QgsFeatureRequest
# import processing  # import przeniesiony do metody - ulatwienie testowania
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog
from collections import defaultdict

from .sprawdzenia_warstw import SprawdzWydzielenia
from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .baza_przetworz import Przetworz
from .pw import PasekPostepu

from .ui.ui_baza_rozlicz_pow import Ui_Ui_Dialog


class recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)


class RozliczPowierzchnieWydz(SprawdzWydzielenia):
    def __init__(self, iface):
        super()
        self.iface = iface
        self.kat = ''  # katalog z warstwa wydz
        self.tempkat = ''  # katalog temp w katalogu z warstwa wydz - dane temp
        self.uz_cale = []  # tablica z LANDID, ktorych pow cala poszla do rozl.
        self.uz_czesciowe = []  # tab z LANDID, z pow częściową w rozliczeniu
        self.postep = PasekPostepu(self.iface).stworz_pasek(
            'Rozliczanie powierzchni wydzieleń'
        )

        # tekst który będzie wypisany do pliku raportu w katalogu z bazą
        self.wypis = ''

        # sl z informacjami dla kazde uzytku na ktorym lezy jakiekolwiek
        # wydzielenie, dane z bazy taksatora
        # { landid: [
        #             0 parcel_int_num
        #             1 shape_nr,
        #             2 pow rej,
        #             3 pow. graf. calego uzytku,
        #             4 pow. rej do rozliczenia - obliczana w o_czy_caly_uz
        #             5 pow. graf. do rozliczenia - obliczana w o_czy_caly_uz
        #           ], }
        self.sl_uz_baza = {}

        # sl z danymi z intersecta ls z wydz w postaci:
        # { landid: {adr_les: pow_graf, ... }
        self.sl_uz_shp = recursivedefaultdict()

        # slownik z adr_les: arodes_int_num
        self.adr_les = {}

        # sl z poprawnym rozliczeniem pow, do wpisania do bazy
        # {landid: [[PARCEL_INT_NUM,
        #           SHAPE_NR,
        #           ARODES_INT_NUM,
        #           AROD_LAND_USE_AREA,
        #           ], ... ]
        self.rozlicz = {}

        # sl z pow graficzna dla wydzielen - na koncu jest sprawdzenie czy cala
        # powierzchnia zostala rozliczona. Ma znaczenie gdy uzytki albo ls maja
        # błedy topologiczne i qgis pominie jakies  poligony. Poniższa tablica
        # umożliwi wyświetlenie zlokalizowanych błędów rozliczeń
        # {adr_les: pow_graf }
        self.sl_wydz_graf = {}
        self.sl_wydz_diff = {}  # od sl odejmujemy pow kazdego uzytku do zera

        # tab z ADR_LES nierozliczonych w całości wydzieleń, GRAFIKA
        self.wydz_nierozliczone = []

        # tab z błędami podczas dopisywania do bazy taksatora
        self.bledy_rozliczania_baza = []

        QgsMessageLog.logMessage(
            '\n-----[ ROZLICZENIE POW WYDZIELEŃ ]-----', 'Las-R', Qgis.Info
        )
        self.wypis = '-----[ ROZLICZENIE POW WYDZIELEŃ ]-----\n\n'

    def sprawdz_dane(self):
        """Metoda sprawdza czy w TOC znajdują się niezbędne warstwy, oraz czy
        są łatwo identyfikowalne, jeżeli tak zwraca True
        """
        # policz czy w TOC jest po jednej warstwie z LS i WYDZ
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        ls = [x for x in lyrs if x.name()[:2].upper() == 'LS']
        wydz = [x for x in lyrs if x.name()[:4].upper() == 'WYDZ']

        try:
            self.ls = ls[0]
            self.ls.dataProvider().setEncoding('UTF-8')
            ls_sc = self.ls.dataProvider().dataSourceUri().split("|")[0]
        except:  # nopep8
            ls_sc = False

        try:
            self.wydz = wydz[0]
            # self.wydz.dataProvider().setEncoding('UTF-8')
            wydz_sc = self.wydz.dataProvider().dataSourceUri().split("|")[0]

            # znajdz bazę do danych jeżeli wydzielenia są ok
            baza_sc = znajdz_baze_do_wydz(self.iface, wydzlyr=self.wydz)
        except:  # nopep8
            wydz_sc = False
            baza_sc = False

        self.pobierz_dane = PobierzDane(wydz_sc, ls_sc, baza_sc)
        self.pobierz_dane.exec_()

        if self.pobierz_dane.porzucone:
            return False

        self.wydz = QgsVectorLayer(self.pobierz_dane.ui.lineEdit_wydz.text(),
                                   'wydz', 'ogr')
        self.ls = QgsVectorLayer(self.pobierz_dane.ui.lineEdit_ls.text(),
                                 'ls', 'ogr')

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

        ls_niez_pola = [x.name() for x in
                        self.ls.dataProvider().fields().toList()
                        if x.name() in ['LANDID', 'LAND_AR', 'LAND_POW', ]]
        if 3 != len(ls_niez_pola):
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'W warstwie LS brakuje którejś z kolumn: LANDID, LAND_AR,'
                ' LAND_POW. Odnaleziono: ['+', '.join(ls_niez_pola)+']',
                Qgis.Critical,
                0
            )
            return False

        request = QgsFeatureRequest().setFlags(
            QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
                ['LANDID'],
                self.ls.fields()
            )
        duble_raw = Counter([self.isNone(x['LANDID']) for x in
                             self.ls.getFeatures(request)])
        duble = [str(x[0])+'('+str(x[1])+')' for x in duble_raw.most_common()
                 if x[1] > 1]

        if '' in duble_raw:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'W warstwie LS, kolumna LANDID nie powinna być pusta',
                Qgis.Critical,
                0
            )
            return False

        if len(duble) > 1:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'W warstwie LS znajdują się zdublowane użytki: [' +
                ', '.join(duble)+']',
                Qgis.Critical,
                0
            )
            return False

        # sprawdz poprawnosc wydz, uklad, polaczenie z baza itp
        if not self.poprawne_wydz():
            return False

        # utworz strukture katalogów do obsługi danych tymczasowych
        sciezka = self.wydz.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)

        # wpisz do raportu nazwy plików i ich lokalizacje dla potnomności
        self.wypis += 'Wydz:\n  ' + sciezka + '.shp\n'
        sc_ls = self.ls.dataProvider().dataSourceUri().split("|")[0]
        self.wypis += 'Ls:\n  ' + sc_ls + '\n'
        self.wypis += \
            'Baza:\n  ' + os.path.abspath(baza_sc) + '\n\n'

        self.postep.setValue(15)
        return True

    def przetnij_wydz_ls(self):
        import processing  # import przeniesiony do metody, ulatwienie testow

        processing.run("native:multiparttosingleparts", {
                        'OUTPUT': os.path.join(
                            self.tempkat,
                            '__WYDZ_singleparts.shp'),
                        'INPUT': self.wydz
                        })

        # na win saga generuje mnie bledow i zawsze zapisuje jako utf-8
        if platform.system()[:3] == 'Win':
            processing.run(
                "saga:intersect",
                {
                    'A': os.path.join(self.tempkat, '__WYDZ_singleparts.shp'),
                    'B': self.ls,
                    'SPLIT': False,
                    'RESULT': os.path.join(self.tempkat,
                                           '__ls_wydz_inter.shp')
                }
            )

        # na linuksie nie wiadomo jakie jest kodowanie, wiec stosujemy native'a
        # który generuje wiecej problemów - ale w produkcji nikt tego nie
        # bedzie używał, tylko dev
        else:
            processing.run("native:intersection", {
                            'INPUT': os.path.join(self.tempkat,
                                                  '__WYDZ_singleparts.shp'),
                            'OVERLAY': self.ls,
                            'INPUT_FIELDS': "",
                            'OVERLAY_FILEDS': "",
                            'OUTPUT': os.path.join(
                                self.tempkat, '__ls_wydz_inter.shp'
                            )
            })

        self.inter = QgsVectorLayer(
            os.path.join(self.tempkat, '__ls_wydz_inter.shp'),
            'interek',
            'ogr'
        )

        if platform.system()[:3] == 'Win':
            self.inter.dataProvider().setEncoding('UTF-8')
            # self.inter.dataProvider().setEncoding('cp1250')

        self.postep.setValue(35)

    def isNone(self, a):
        if a in [None, 'NULL', '', ]:
            return ''
        elif isinstance(a, QVariant):
            if a.isNull():
                return ''
        else:
            return a

    def zbuduj_strukture(self):
        """ metoda pobiera dane z bazy i shp oraz buduje niezbedne slowniki i
        tablice w celu poprawnego zastosowania poprawek do rozliczenia pow.
        uzytkow.
        """

        if not self.baza.polacz():
            return False

        self.sl_uz_baza = {
            x[12]+'.'+x[9]+self.isNone(x[10]): [x[6], x[8], x[11]]
            for x in self.baza.uzytki()
        }

        braki_uzytkow = []  # tablica z uzytkami nie wystepujacymi w bazie
        for uz in self.ls.getFeatures():
            if uz['LANDID'] not in self.sl_uz_baza.keys():
                braki_uzytkow.append(self.isNone(uz['LANDID']))
            else:
                self.sl_uz_baza[uz['LANDID']].append(
                    round(uz.geometry().area() / 10000, 4)
                )

        # jeżeli jakiegoś użtyku nie ma w bazie kończymy zabawę...
        if len(braki_uzytkow) > 0:
            self.iface.messageBar().pushMessage(
                'BRAK UŻYTKU W BAZIE',
                'Odnaleziono użytki w shp, które nie są wprowadzone w bazie'
                ', sprawdź log Las-R',
                Qgis.Critical,
                15
            )
            QgsMessageLog.logMessage(
                'Użytki nie występujące w bazie:\n' +
                '\n'.join(braki_uzytkow),
                'Las-R'
            )

            self.wypis += 'Użytki nie występujące w bazie: ' + \
                str(len(braki_uzytkow)) + '\n' + \
                '(Puste wiersze oznaczają poligony z pustym LANDID)\n' + \
                20 * '-' + '\n' + \
                '\n'.join(braki_uzytkow) + '\n' + 20 * '-' + '\n\n\n'

            # return False

        # przygotuj pow graficzna dla wszystkich wydz, wiemy ze sa poprawne bo
        # przeszły sprawdzanie na samym początku
        for wydz in self.wydz.getFeatures():
            self.sl_wydz_graf[wydz['ADR_LES']] = \
                round(wydz.geometry().area() / 10000, 4)
            self.sl_wydz_diff[wydz['ADR_LES']] = \
                round(wydz.geometry().area() / 10000, 4)

        # stworz slownik pow wydzielen w uzytkach
        for uz in self.inter.getFeatures():
            # Jeżeli przecięcie ma powi mniejszą od 1 m2 pomijamy
            if uz.geometry().area() < 1:
                continue

            pp = round(self.sl_wydz_diff[uz['ADR_LES']] -
                       uz.geometry().area() / 10000, 4)
            self.sl_wydz_diff[uz['ADR_LES']] = pp

            if uz['LANDID'] not in self.sl_uz_shp:
                self.sl_uz_shp[uz['LANDID']][uz['ADR_LES']] = \
                    round(uz.geometry().area() / 10000, 4)
            else:
                if uz['ADR_LES'] not in self.sl_uz_shp[uz['LANDID']]:
                    self.sl_uz_shp[uz['LANDID']][uz['ADR_LES']] = \
                        round(uz.geometry().area() / 10000, 4)
                else:
                    poprzedni = self.sl_uz_shp[uz['LANDID']][uz['ADR_LES']]
                    self.sl_uz_shp[uz['LANDID']][uz['ADR_LES']] = \
                        round(poprzedni + uz.geometry().area() / 10000, 4)

        # pobierz sl wydzielen
        self.adr_les = self.baza.pobierz_wydzielenia()

        self.postep.setValue(45)
        return True

    def sprawdz_rozlicz_graf(self):
        """ Metoda sprawdza czy pow wydz przed i po intersect nie odbiega od
        siebie o wiecej niż o metr. Jeżeli tak, zaraportuj użyszkodnikowi, że
        coś nie gra
        """

        # import pdb; from PyQt5.QtCore import pyqtRemoveInputHook
        # pyqtRemoveInputHook()
        # pdb.set_trace()

        # sprawdz czy pow graf interu jest taka sama jak pow graf wydzielen,
        # jeżeli nie przygotuj raport czego brakuje
        for key in self.sl_wydz_graf.keys():
            if self.sl_wydz_diff[key] > 0.0005:
                self.wydz_nierozliczone.append(key)

        # sformatuj wypis nirozliczonych wydz w grafice i dodaj stosowne uwagi
        if len(self.wydz_nierozliczone) > 0:
            form_wyps = [
                [x,
                 str(round(self.sl_wydz_diff[x], 4)),
                 str(round(self.sl_wydz_graf[x], 4))
                 ]
                for x in sorted(self.wydz_nierozliczone,
                                reverse=True, key=lambda x: x[1])
            ]
            for xx in form_wyps:
                if xx[1] == xx[2]:
                    xx.append('\t<<--- NIEROZLICZONE WYDZ W BAZIE')
                else:
                    xx.append('')

            # adnotacja o miejscu sprawdzenia błędów
            form_wyps += [
                ['', ''],
                ['(Błędy przecięcia można sprawdzić na warstwie :\n' +
                 os.path.join(self.tempkat, '__ls_wydz_inter.shp'),
                 ]
            ]

            QgsMessageLog.logMessage(
                '\n\nWydzielenia z nierozliczoną częścią pow. \n'
                '(Błędy najprawdopodobniej wynikają z błędów topologicznych)\n'
                'ADR_LES  \tpow graf nierozliczona/pow graf wydz\n' +
                '\n'.join([' '.join(x) for x in form_wyps]),
                'Las-R',
                Qgis.Warning
            )

            self.wypis += 'Wydzielenia z nierozliczoną częścią pow. \n' + \
                '(Błędy najprawdopodobniej wynikają z błędów ' + \
                'topologicznych)\n' + \
                'ADR_LES  \tpow graf NIEROZLICZONA/pow graf wydz [ha]\n' + \
                '\n'.join([' '.join(x) for x in form_wyps]) + '\n\n\n'
        else:
            QgsMessageLog.logMessage(
                '\nSprawdzenie pow graf wydzeleń przed i po intersect - OK',
                'Las-R',
                Qgis.Info
            )
            self.wypis += \
                'Sprawdzenie pow graf wydzeleń przed i po intersect - OK\n\n\n'

        self.postep.setValue(55)

    def skasuj_robocze(self):
        """ Metoda kasuje robocze warstwy katalogu temp """

        del self.inter

        if len(self.wydz_nierozliczone) == 0:
            for ll in glob.glob(os.path.join(self.tempkat,
                                             '__ls_wydz_inter.*')):
                os.remove(ll)

        for ll in glob.glob(os.path.join(self.tempkat,
                                         '__WYDZ_singleparts.*')):
            os.remove(ll)

        QgsMessageLog.logMessage(
            '\nINFORMACJE LICZBOWE O ROZLICZENIU'
            '\nRozliczono uzytków: ' +
            str(len(self.uz_cale+self.uz_czesciowe)) + '\n'
            '   z pełnym pokryciem przez wydzielenia: ' +
            str(len(self.uz_cale)) +
            '\n       (w tym Ls-ów: ' +
            str(len([x for x in self.uz_cale if 'Ls' in x])) + ')'
            '\n   z częściowym pokryciem przez wydz: ' +
            str(len(self.uz_czesciowe)) + '\n',
            'Las-R',
            Qgis.Info
        )

        # skasuj jeżeli katalog jest pusty
        try:
            os.removedirs(self.tempkat)
            QgsMessageLog.logMessage(
                '\nSprzątam po skrypcie... OK\n-----[ KONIEC ]-----',
                'Las-R',
                Qgis.Info
            )
        except:  # nopep8
            QgsMessageLog.logMessage(
                '\nNie udało się posprzątać po skrypcie, '
                'zostawiam katalog temp'
                '\n-----[ KONIEC ]-----',
                'Las-R',
                Qgis.Info
            )

        self.iface.messageBar().pushMessage(
            'OK',
            'Skrypt zakończony bez błędów',
            Qgis.Success,
            10
        )

    def zestaw_rozliczenie(self):
        """ Metoda na podstawie wcześniej wczytanych danych z shp w metodzie
        zbuduj_strukture oblicza poprawki do rozliczenia uzytku w bazie,
        sprawdzajac czy wydzielenie jest rozrysowane na calym uzytku (Ls) czy
        tylko na części (inne użytki)
        """

        self.wypis += '----[ log z rozliczania ]----\n'
        for key, uz in self.sl_uz_shp.items():
            roz = self.oblicz_rozl_uzytku(key, uz)

            if len(roz) < 1:
                QgsMessageLog.logMessage(
                    'Użytku nie ma w bazie: ' + key,
                    'Las-R',
                    Qgis.Critical
                )
                self.wypis += 'Przeciętych uż. nie ma w bazie: ' + key + '\n'

            elif key not in self.rozlicz:
                self.rozlicz[key] = roz

            else:
                self.iface.messageBar().pushMessage(
                    "BŁĄD",
                    'Źle skalsyfikowane użytki, o co lotto???',
                    Qgis.Warning,
                    10
                )
                QgsMessageLog.logMessage(
                    'Źle skalsyfikowane użytki: ' + key,
                    'Las-R',
                    Qgis.Critical
                )
                self.wypis += 'Źle skalsyfikowane użytki (brak przecięcia' + \
                    '??? - tak może być??? błąd nieznany :/  "PNR"): ' + \
                    key + '\n'

        self.wypis += '----[ koniec logu z rozliczania ]----\n\n'
        self.postep.setValue(65)

    def oblicz_rozl_uzytku(self, key, uz):
        """ Oblicza rozliczenie rejestrowe dla wszystkich wydzielenie na
        wskazanym uzytku """

        # jezeli nie ma uzytku w bazie uz, pomijamy.
        if key not in self.sl_uz_baza:
            return []

        # oblicz pow graf i rej uzytku, czy caly jest brany do rozliczenia czy
        # tylko fragment (np dodano kawałek wydz na Ps)
        pow_uz_rej, pow_uz_graf = self.o_czy_caly_uz(key, uz)

        # tabela z roliczonymi pow wydzielen na uzytku
        temp_pow = self.o_tabele_pow_rej(uz, pow_uz_rej, pow_uz_graf)

        # oblicz poprawkę jaką trzeba dodać aby pow się zgadzała z rej. w bazie
        if round(pow_uz_rej, 4) != round(sum([x[1] for x in temp_pow]), 4):
            poprawka = round(pow_uz_rej - sum([x[1] for x in temp_pow]), 4)

            # dodaj do największego wydzielenia na uzytku
            temp_pow[0][1] = round(temp_pow[0][1] + poprawka, 4)

            if -0.01 > poprawka or poprawka > 0.01:
                self.wypis += key + ' wyliczona poprawka to:\t' + \
                    str(poprawka) + '\n'

        return [self.sl_uz_baza[key][:2] + [self.adr_les[tt[0]]] + [tt[1]]
                for tt in temp_pow]

    def o_czy_caly_uz(self, key, uz):
        # suma wszystkich uzytkow na pow - GRAFICZNA
        suma_graf = round(sum([x for x in uz.values()]), 4)
        # pow rej calego uzytku
        pow_uz_rej = self.sl_uz_baza[key][2]
        pow_uz_graf = self.sl_uz_baza[key][3]

        # jezeli pow graf intersecta i calego uzytku nie zgadza sie w 99%,
        # , przelicz pow rej z proporcji na
        # część wspólną i na jej podstawie licz pow rej
        if abs(suma_graf - self.sl_uz_baza[key][3]) > 0.0005:
            self.uz_czesciowe.append(key)

            pow_uz_graf = suma_graf
            if self.sl_uz_baza[key][3] > 0:
                pow_uz_rej = round(
                    (pow_uz_rej*suma_graf) / self.sl_uz_baza[key][3],
                    4
                )
            else:
                QgsMessageLog.logMessage('---> SPRAWDŹ: '+key, 'Las-R')
                self.wypis += '---> DO SPRAWDZENIA: ' + key + '\n'
                pow_uz_rej = 0.0

        else:
            self.uz_cale.append(key)

        self.sl_uz_baza[key] += [pow_uz_rej, pow_uz_graf]
        return pow_uz_rej, pow_uz_graf

    def o_tabele_pow_rej(self, uz, pow_uz_rej, pow_uz_graf):
        """ Metoda składowa obliczeń, oblicza pow. rejestrowe każdego frg. wydz
        na użytku i zwraca je w postaci posortowanej od największego tabeli w
        postaci:
            [[ADR_LES, POW], ... ]
        """

        # oblicz pow rej dla każdego z wydzieleń
        temp_pow = sorted(
            [[k, round((v*pow_uz_rej)/pow_uz_graf, 4)]
                for k, v in uz.items()],
            reverse=True,
            key=lambda x: x[1]
        )

        return temp_pow

    def zapisz_rozliczenie(self):
        """ Metoda wypisuje rozliczenie do pliku w celu porównania z rozlicz.
        wykonanym przez człowiek """

        wypis = ''
        for v in self.rozlicz.values():
            wypis += '\n'.join(['\t'.join(map(str, x)) for x in v]) + '\n'

        plik = open(os.path.join(self.kat, 'wypis_do_spr.csv'), 'w')
        plik.write(wypis)
        plik.close()

    def dopisz_rozliczenie(self):
        """Metoda tworzy kopie zapasową bazy danych a następnie
        dopisuje do bazy wygenerowane rozliczenie """

        if len(self.baza.pobierz_rozliczenie_wydz()) > 0:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Proszę skasować wszystkie rekordy w tabeli F_AROD_LAND_USE',
                Qgis.Critical,
                10
            )
            return False

        self.baza.zamknij()
        self.baza.utworz_kopie('kopia_rozliczPow')
        self.baza.polacz()

        # sl tworzony w petli, sumuje pow uz dla wydzielen - wymagane do
        # wpisania wartosci do tabeli F_SUBAREA
        rozlicz_wydz = {}

        # slownik odwrotny F_AROD_INT_NUM: ADR_LES
        odwr_wydz = {v: k for k, v in self.adr_les.items()}

        self.wypis += '----[ log z wpisywania rozl do bazy ]----\n'
        problemy = False  # trig jeżeli nie ma problemów wypisze że poszło ok

        for key, val in self.rozlicz.items():
            # rozlicz to tabele dla każdego landid w postaci:
            # [parcelid, shapenr, arodes_intnum, pow_rej]
            for v in val:
                # zsumuj pow dla wydzielen do wpisania do f_subarea
                if v[2] not in rozlicz_wydz:
                    rozlicz_wydz[v[2]] = v[3]
                else:
                    rozlicz_wydz[v[2]] += v[3]

                if not self.baza.wpisz_rozliczenie_wydz(v):
                    self.bledy_rozliczania_baza.append([key] + v)

        for k, v in rozlicz_wydz.items():
            sql = "update f_subarea set sub_area = " + str(v) + \
                " where arodes_int_num = " + str(k) + ";"
            if not self.baza.wpisz(sql):
                QgsMessageLog.logMessage(
                    'Błąd wpisania pow w F_SUBAREA dla wydzielenia: ' +
                    odwr_wydz[k] + ', ' + str(v),
                    'Las-R',
                )
                problemy = True
                self.wypis += \
                    'Błąd wpisania pow w F_SUBAREA dla wydzielenia: ' + \
                    odwr_wydz[k] + ' (id=' + str(k) + '), ' + str(v),

        if len(self.bledy_rozliczania_baza) > 0:
            QgsMessageLog.logMessage(
                '\nNie udało się dopisać wszystkich wygenerowanych pow. rej. '
                'do bazy taksatora!\nPominięte wartości:\n' +
                '\n'.join([' '.join([
                    line[0]+'('+str(line[1])+':'+str(line[2])+')',  # landid
                    odwr_wydz[line[3]]+'('+str(line[3])+')'
                ]) for line in self.bledy_rozliczania_baza]),
                'Las-R'
            )

            self.wypis += '\n\n' + \
                '\n'.join(['\t'.join([
                    line[0]+'('+str(line[1])+':'+str(line[2])+')',  # landid
                    odwr_wydz[line[3]]+' ('+str(line[3])+')'
                ]) for line in self.bledy_rozliczania_baza]),
            problemy = True

        if not problemy:
            self.wypis += 'Wszystko ładnie się wpisało - OK!'

        self.wypis += '\n----[ koniec logu z wpisywania rozl do bazy ]----\n\n'

        # nie że dobrze, tylko doszliśmy do końca, ale dobrze w sumie też
        self.postep.setValue(75)
        return True

    def sprawdz_rozlicz_rej(self):  # noqa
        """Metoda sprawdza czy wszystkie ls z baza zostały rozliczone,
        uwzględniając podział na własności OP, OPiF, OF. W tym sprawdzeniu
        pomiajane sa lasy pozaewidencyjne, których powierzchnia nie jest
        możliwa do sprawdzenia...
        Ta metoda pownna być uruchamiana po dopisaniu rozliczenia do bazy
        """
        oroz = SprawdzRozliczenie(self.postep, self.baza)
        oroz.przetworz_baze()
        oroz.przelicz_rozliczenie()
        oroz.oblicz_staty()
        oroz.zestaw_staty()

        self.wypis += oroz.zwroc_wypis()

    def zapisz_raport(self):
        """ Metoda zbiera dane z kolejnych sprawdzeń i zapisuje je do pliku,
        tekstowego w katalogu z bazą.
        """
        sc = os.path.join(
            os.path.dirname(os.path.abspath(self.baza.baza)),
            'raport_rozliczPow_'+self.baza.czas+'.txt')

        plik = open(sc, 'w')

        self.iface.messageBar().clearWidgets()

        self.wypis += '\n\n----[ KONIEC RAPORTU ]----'
        plik.write(self.wypis)
        plik.close()

        message = QMessageBox()
        message.setIcon(QMessageBox.Information)
        message.setWindowTitle('Raport')
        message.setText('Czy pokazać raport z rozliczenia powierzchni?')
        message.addButton(u"Zamknij", QMessageBox.ActionRole)
        message.addButton(u"Zamknij i pokaż raport", QMessageBox.ActionRole)
        pok_rap = message.exec_()

        if pok_rap == 1:
            if platform.system()[:3] == 'Win':
                os.startfile(sc)
            else:
                import subprocess
                subprocess.call(['kate', sc])

        self.iface.messageBar().pushMessage(
            'OK', 'Rozliczenie powierzchni zakończone!', Qgis.Success, 10)


class SprawdzRozliczenie():
    def __init__(self, progress, baza):
        self.baza = baza
        self.postep = progress

        # tesktowy zwrot sprawdzenia
        self.wypis = ''

        # slowniki rozliczonych ls z podzialem na wl każdy w postaci:
        # {LANDID: [pow rozlicz z F_AROD_LAND_USE, pow uz z F_PARCEL_LAND_USE]}
        self.sl_rozl_rej_op = {}
        self.sl_rozl_rej_of = {}
        self.sl_rozl_rej_opif = {}
        self.sl_rozl_rej_nielas = {}

        # tablice z bledami rozliczeniowymi w postaci:
        # [[LANDID, POW_ROZL, POW_REJ], ]
        self.op_bl = []
        self.of_bl = []
        self.opif_bl = []

    def przetworz_baze(self):
        p = Przetworz()
        p.dodaj_uzytki(self.baza.uzytki())
        p.dodaj_wlasnosci(self.baza.wlasnosci())
        p.przetworz_dzialki()
        p.przetworz_uzytkowanie()
        self.p = p

    def przelicz_rozliczenie(self):  # noqa
        """ Metoda pobiera i przetwarza rozliczenie z bazy do sl w postaci,
        {parcelid: {shapenr: zsumowana_pow}, {shapenr: zsumowana_pow} }
        """

        rozliczenie = self.baza.pobierz_rozliczenie_wydz()
        _uz_rozl = recursivedefaultdict()
        # zbuduj sl z suma pow w wydz dla uzytkow w postaci:
        # {parcelid: {shapenr: zsumowana_pow}, {shapenr: zsumowana_pow} }
        for r in rozliczenie:
            if r[1] not in _uz_rozl:
                _uz_rozl[r[1]][r[2]] = r[3]
            else:
                if r[2] not in _uz_rozl[r[1]]:
                    _uz_rozl[r[1]][r[2]] = r[3]
                else:
                    poprzed = _uz_rozl[r[1]][r[2]]
                    _uz_rozl[r[1]][r[2]] = round(poprzed + r[3], 4)

        # zbuduj slownik dla uzytkow w postaci :
        # sl[PACEL_ID][SHAPE_NR] = [PARCELID, LAND_USE_AREA, AU+SQ]
        # tylko dla ls i innych użytków, które zostały przecięte z wydz
        _uz_sl = recursivedefaultdict()
        for u in self.baza.uzytki():
            if u[9] == 'Ls':
                _uz_sl[u[6]][u[8]] = [u[12], u[11], u[9]+self.isNone(u[10])]
            elif u[6] in _uz_rozl:
                if u[8] in _uz_rozl[u[6]]:
                    _uz_sl[u[6]][u[8]] = [
                        u[12], u[11], u[9]+self.isNone(u[10])
                    ]

        # przygotuj slownik ze sprawdzeniem rozliczenia powierzchni z podziałem
        # na własności w lasach i nieleśnych (tutaj grupujemy własności)
        for dzid in _uz_sl.keys():
            for shpnr in _uz_sl[dzid].keys():
                landid = '.'.join(_uz_sl[dzid][shpnr][0:3:2])
                wp = False

                if 'Ls' not in landid:
                    wp = self.sl_rozl_rej_nielas
                else:
                    if _uz_sl[dzid][shpnr][0][4:] in self.p.dz_of:
                        wp = self.sl_rozl_rej_of
                    elif _uz_sl[dzid][shpnr][0][4:] in self.p.dz_op:
                        wp = self.sl_rozl_rej_op
                    elif _uz_sl[dzid][shpnr][0][4:] in self.p.dz_opif:
                        wp = self.sl_rozl_rej_opif

                if wp is not False:
                    # sprawdz czy uzytek jest w sl, jezeli nie, ustaw pow na
                    # zero, nie zaburzy to wyniku ostatecznego
                    if isinstance(_uz_rozl[dzid][shpnr],
                                  recursivedefaultdict):
                        rozp = 0.0000
                    else:
                        rozp = _uz_rozl[dzid][shpnr]

                    if landid in wp:
                        # jezeli uzytek jest juz w sl dodaj pow
                        wp[landid][0] += rozp
                    else:
                        wp[landid] = [rozp, _uz_sl[dzid][shpnr][1]]
        self.postep.setValue(85)

    def isNone(self, a):
        if a in [None, 'NULL', '', ]:
            return ''
        elif isinstance(a, QVariant):
            if a.isNull():
                return ''
        else:
            return a

    def oblicz_staty(self):
        # policz powierzchnię rozliczenia
        self.op_pow = [v for v in self.sl_rozl_rej_op.values()]
        self.of_pow = [v for v in self.sl_rozl_rej_of.values()]
        self.opif_pow = [v for v in self.sl_rozl_rej_opif.values()]
        self.nielas_pow = [v for v in self.sl_rozl_rej_nielas.values()]

        # policz sumy pow dla rozliczen i bazy
        self.sum_op_pow_ = round(sum([x[0] for x in self.op_pow]), 4)
        self.sum_op_pow_b = round(sum([x[1] for x in self.op_pow]), 4)
        self.sum_of_pow_ = round(sum([x[0] for x in self.of_pow]), 4)
        self.sum_of_pow_b = round(sum([x[1] for x in self.of_pow]), 4)
        self.sum_opif_pow_ = round(sum([x[0] for x in self.opif_pow]), 4)
        self.sum_opif_pow_b = round(sum([x[1] for x in self.opif_pow]), 4)
        self.sum_nielas_pow_ = round(sum([x[0] for x in self.nielas_pow]), 4)
        self.sum_nielas_pow_b = round(sum([x[1] for x in self.nielas_pow]), 4)

    def zestaw_staty(self):
        """ Metoda zestawia statystyki dla poszczegółnych własności w ls i
        poza, przygotowuje treść do wypisu dla użytkownika
        """

        # suma wszystkich użytków z wydzieleniami
        rozlicz_uz = sum([
            len(self.sl_rozl_rej_nielas.keys()),
            len(self.sl_rozl_rej_of),
            len(self.sl_rozl_rej_op),
            len(self.sl_rozl_rej_opif),
        ])

        suma_cala_roz = round(
            self.sum_of_pow_ +
            self.sum_op_pow_ +
            self.sum_opif_pow_ +
            self.sum_nielas_pow_,
            4)
        suma_cala_rej = round(
            self.sum_of_pow_b +
            self.sum_op_pow_b +
            self.sum_opif_pow_b +
            self.sum_nielas_pow_b,
            4)

        QgsMessageLog.logMessage(
            '\nSPRAWDZENIE ROZLICZENIA wg REJESTRU\n'
            'Rozliczono użytków: '+str(rozlicz_uz)+'\n'
            'Nieleśnych: ' + str(len(self.sl_rozl_rej_nielas.keys())) +
            '\nLeśnych: ' + str(
                len(self.sl_rozl_rej_of) +
                len(self.sl_rozl_rej_op) +
                len(self.sl_rozl_rej_opif)
            ) +
            '\n__w tym:\n____OF: ' + str(len(self.sl_rozl_rej_of)) +
            '\n____OPiF: ' + str(len(self.sl_rozl_rej_opif)) +
            '\n____OP: ' + str(len(self.sl_rozl_rej_op)),
            'Las-R',
            Qgis.Info
        )

        self.wypis += '----[ SPRAWDZENIE ROZLICZENIA wg REJESTRU ]----\n' + \
            'Rozliczono użytków: '+str(rozlicz_uz)+'\n' + \
            'Nieleśnych: ' + str(len(self.sl_rozl_rej_nielas.keys())) + \
            '\nLeśnych: ' + str(
                len(self.sl_rozl_rej_of) +
                len(self.sl_rozl_rej_op) +
                len(self.sl_rozl_rej_opif)
            ) + \
            '\n  w tym:\n    OF: ' + str(len(self.sl_rozl_rej_of)) + \
            '\n    OPiF: ' + str(len(self.sl_rozl_rej_opif)) + \
            '\n    OP: ' + str(len(self.sl_rozl_rej_op)) + '\n\n'

        self.wypis += 'Zestawienie powierzchniowe:\n' + \
            'Całkowita pow:\t' + str(suma_cala_roz) + '  /  ' + \
            str(suma_cala_rej) + '  [ha]\t\t'

        if suma_cala_roz - suma_cala_rej != 0:
            self.wypis += '[ ' + str(round(suma_cala_roz - suma_cala_rej, 4)
                                     ) + ' ]\n'
        else:
            self.wypis += '\n'

        self.wypis += '  OF:\t' + str(self.sum_of_pow_) + ' / ' + \
            str(self.sum_of_pow_b) + ' [ha]\t\t'

        if self.sum_of_pow_ - self.sum_of_pow_b != 0:
            self.wypis += '[ ' + str(
                round(self.sum_of_pow_-self.sum_of_pow_b, 4)) + ' ]\n'
        else:
            self.wypis += '\n'

        self.wypis += '  OPiF:\t' + str(self.sum_opif_pow_) + ' / ' + \
            str(self.sum_opif_pow_b) + ' [ha]\t\t'

        if self.sum_opif_pow_ - self.sum_opif_pow_b != 0:
            self.wypis += '[ ' + str(
                round(self.sum_opif_pow_-self.sum_opif_pow_b, 4)) + ' ]\n'
        else:
            self.wypis += '\n'

        self.wypis += '  OP:\t' + str(self.sum_op_pow_) + ' / ' + \
            str(self.sum_op_pow_b) + ' [ha]\t\t'

        if self.sum_op_pow_ - self.sum_op_pow_b != 0:
            self.wypis += '[ ' + str(
                round(self.sum_op_pow_-self.sum_op_pow_b, 4)) + ' ]\n'
        else:
            self.wypis += '\n'

        self.wypis += '  nielas:\t' + str(self.sum_nielas_pow_) + ' / ' + \
            str(self.sum_nielas_pow_b) + \
            ' [ha] \n\n(przy pozaewidencyjnych, ' + \
            'powierzchnie mogą się nie zgadzać)\n\n'

        # wyszukaj bledy rozliczenia
        self.op_bl = [[k]+v for k, v in self.sl_rozl_rej_op.items()
                      if round(v[0], 4) != round(v[1], 4)]
        self.of_bl = [[k]+v for k, v in self.sl_rozl_rej_of.items()
                      if round(v[0], 4) != round(v[1], 4)]
        self.opif_bl = [[k]+v for k, v in self.sl_rozl_rej_opif.items()
                        if round(v[0], 4) != round(v[1], 4)]

        ttt = [
            [self.of_bl, 'Błędy rozliczenia Ls w włas OF: '],
            [self.opif_bl, 'Błędy rozliczenia Ls w włas OPiF: '],
            [self.op_bl, 'Błędy rozliczenia Ls w włas OP: '],
        ]
        bbledow = True

        for t in ttt:
            if len(t[0]) > 0:
                bbledow = False
                QgsMessageLog.logMessage(
                    '\n' + t[1] + str(len(t[0])) + '\n' +
                    '\n'.join(['\t'.join([line[0], str(line[1]), str(line[2])])
                               for line in t[0]]),
                    'Las-R',
                    Qgis.Warning
                )

                self.wypis += '\n\n' + t[1] + str(len(t[0])) + '\n' + \
                    '\n'.join([' '.join([line[0], str(line[1]), str(line[2])])
                               for line in t[0]])

        if bbledow:
            QgsMessageLog.logMessage(
                '\nNie odnaleziono rozbiezności w rozliczeniu i rejestrze... '
                'OK\nPamiętaj, że pozaewidencyjnych nie mam jak sprawdzić...',
                'Las-R',
                Qgis.Info
            )

            self.wypis +=  \
                '\nNie odnaleziono rozbiezności w rozliczeniu i rejestrze-' +\
                'OK\nPamiętaj, że pozaewidencyjnych nie mam jak sprawdzić...'

        self.wypis += '\n----[ KONIEC SPRAWDZENIA ROZLICZENIA wg REJESTRU ' + \
            ']----\n\n'
        self.postep.setValue(95)

    def zwroc_wypis(self):
        return self.wypis


class PobierzDane(QDialog):
    def __init__(self, wydz=False, ls=False, baza=False):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Ui_Dialog()
        self.ui.setupUi(self)

        # katalog który będzie uzupełniony po pierwszym wskazaniu warstwy, bazy
        self.kat = ''

        # wartosc True jezeli uzytkownik zrezygnowal z przetwarzania
        self.porzucone = True

        # wpisz sciezki do przekazanych warstw i bazy
        if wydz:
            self.ui.lineEdit_wydz.setText(wydz)
        if ls:
            self.ui.lineEdit_ls.setText(ls)
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
        self.ui.pushButton_ls.clicked.connect(self.kat_fochr)

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if os.path.isfile(self.ui.lineEdit_wydz.text()) and \
                os.path.isfile(self.ui.lineEdit_baza.text()) and \
                os.path.isfile(self.ui.lineEdit_ls.text()):
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
                                           'Wskaż warstwę ls',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_ls.setText(sc)
