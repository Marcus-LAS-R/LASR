import os
import glob
from qgis.core import QgsVectorLayer, QgsMessageLog, QgsProject, Qgis
# import processing  # import przeniesiony do metody - ulatwienie testowania
from PyQt5.QtCore import QVariant
from collections import defaultdict

from .sprawdzenia_warstw import SprawdzWydzielenia
from .baza_wrapper import Baza, znajdz_baze_do_wydz


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

        QgsMessageLog.logMessage(
            '\n-----[ ROZLICZENIE POW WYDZIELEŃ ]-----', 'Las-R', Qgis.Info
        )

    def sprawdz_dane(self):
        """Metoda sprawdza czy w TOC znajdują się niezbędne warstwy, oraz czy
        są łatwo identyfikowalne, jeżeli tak zwraca True
        """
        # policz czy w TOC jest po jednej warstwie z LS i WYDZ
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        ls = [x for x in lyrs if x.name()[:2].upper() == 'LS']
        wydz = [x for x in lyrs if x.name()[:4].upper() == 'WYDZ']

        # brak dodanych warstw do TOC
        if len(lyrs) == 0:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Najpierw dodaj warstwę WYDZ i Ls do TOC!',
                Qgis.Critical,
                10
            )
            return False

        # Jeżeli jest więcej warstw które się tak nazywają zwróć użytkownikowi
        if len(ls) != 1 or len(wydz) != 1:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Zbyt wiele warstw LS lub WYDZ w TOCu!',
                Qgis.Warning,
                10
            )

        self.ls = ls[0]
        # self.ls.dataProvider().setEncoding('UTF-8')
        self.wydz = wydz[0]
        # self.wydz.dataProvider().setEncoding('UTF-8')

        # sprawdz niezbedne pola w poszczegolnych warstwach
        if 'ADR_LES' not in [x.name() for x in
                             self.wydz.dataProvider().fields().toList()]:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Brak kolumny ADR_LES w warstwie WYDZ - '
                'piłeś coś dzisiaj, drogi użytkowniku?',
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

        # znajdz bazę do danych
        baza_sc = znajdz_baze_do_wydz(self.iface, wydzlyr=self.wydz)
        if baza_sc is False:
            return False

        self.baza = Baza(baza_sc)

        # sprawdz poprawnosc wydz, uklad, polaczenie z baza itp
        if not self.poprawne_wydz():
            return False

        # utworz strukture katalogów do obsługi danych tymczasowych
        sciezka = self.wydz.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)

        return True

    def przetnij_wydz_ls(self):
        import processing  # import przeniesiony do metody, ulatwienie testow

        processing.run("native:multiparttosingleparts", {
                        'OUTPUT': os.path.join(
                            self.tempkat,
                            '__WYDZ_singleparts.shp'),
                        'INPUT': self.wydz
                        })

    #   processing.run(
    #       "saga:intersect",
    #       {
    #           'A': os.path.join(self.tempkat, '__WYDZ_singleparts.shp'),
    #           'B': self.ls,
    #           'SPLIT': False,
    #           'RESULT': os.path.join(self.tempkat,
    #                                  '__ls_wydz_inter.shp')
    #       }
    #   )

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
                braki_uzytkow.append(uz['LANDID'])
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
                'Użytki nie występujące w bazie:\n'
                '\n'.join(braki_uzytkow),
                'Las-R'
            )
            return False

        # stworz slownik pow wydzielen w uzytkach
        for uz in self.inter.getFeatures():
            # Jeżeli przecięcie ma powi mniejszą od 1 m2 pomijamy
            if uz.geometry().area() < 1:
                continue

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
                        poprzedni + round(uz.geometry().area() / 10000, 4)

        # pobierz sl wydzielen
        self.adr_les = self.baza.pobierz_wydzielenia()

        return True

    def skasuj_robocze(self):
        """ Metoda kasuje robocze warstwy katalogu temp """
        del self.inter

        for ll in glob.glob(os.path.join(self.tempkat, '__ls_wydz_inter.*')):
            os.remove(ll)

        for ll in glob.glob(os.path.join(self.tempkat,
                                         '__WYDZ_singleparts.*')):
            os.remove(ll)

        QgsMessageLog.logMessage(
            '\n\nRozliczono uzytków: ' +
            str(len(self.uz_cale+self.uz_czesciowe)) + '\n'
            '   z pełnym pokryciem przez wydzielenia: ' +
            str(len(self.uz_cale)) +
            '\n   (w tym Ls-ów: ' +
            str(len([x for x in self.uz_cale if 'Ls' in x])) +
            '\n   z częściowym pokryciem przez wydz: ' +
            str(len(self.uz_czesciowe)) + '\n\n',
            'Las-R',
            Qgis.Info
        )

        # skasuj jeżeli katalog jest pusty
        try:
            os.removedirs(self.tempkat)
            QgsMessageLog.logMessage(
                'Sprzątam po skrypcie... OK\n-----[ KONIEC ]-----',
                'Las-R',
                Qgis.Info
            )
        except:  # nopep8
            QgsMessageLog.logMessage(
                'Nie udało się posprzątać po skrypcie, zostawiam temp_pow'
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

        for key, uz in self.sl_uz_shp.items():
            roz = self.oblicz_rozl_uzytku(key, uz)

            if len(roz) < 1:
                QgsMessageLog.logMessage(
                    'Źle skalsyfikowane użytki: ' + key,
                    'Las-R',
                    Qgis.Critical
                )

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

    def oblicz_rozl_uzytku(self, key, uz):
        """ Oblicza rozliczenie rejestrowe dla wszystkich wydzielenie na
        wskazanym uzytku """

        # oblicz pow graf i rej uzytku, czy caly jest brany do rozliczenia czy
        # tylko fragment (np dodano kawałek wydz na Ps)
        pow_uz_rej, pow_uz_graf = self.o_czy_caly_uz(key, uz)

        # tabela z roliczonymi pow wydzielen na uzytku
        temp_pow = self.o_tabele_pow_rej(uz, pow_uz_rej, pow_uz_graf)

        # oblicz poprawkę jaką trzeba dodać aby pow się zgadzała z rej. w bazie
        if pow_uz_rej != sum([x[1] for x in temp_pow]):
            poprawka = round(pow_uz_rej - sum([x[1] for x in temp_pow]), 4)

            # dodaj do największego wydzielenia na uzytku
            temp_pow[0][1] = round(temp_pow[0][1] + poprawka, 4)

        return [self.sl_uz_baza[key][:2] + [self.adr_les[tt[0]]] + [tt[1]]
                for tt in temp_pow]

    def o_czy_caly_uz(self, key, uz):
        # suma wszystkich uzytkow na pow - GRAFICZNA
        suma_graf = sum([x for x in uz.values()])
        # pow rej calego uzytku
        pow_uz_rej = self.sl_uz_baza[key][2]
        pow_uz_graf = self.sl_uz_baza[key][3]

        # jezeli pow graf intersecta i calego uzytku nie zgadza sie w 99%,
        # , przelicz pow rej z proporcji na
        # część wspólną i na jej podstawie licz pow rej
        if abs(suma_graf - self.sl_uz_baza[key][3]) < 1:
            self.uz_cale.append(key)

            pow_uz_graf = suma_graf
            pow_uz_rej = round(
                (pow_uz_rej*suma_graf) / self.sl_uz_baza[key][3],
                4
            )

        else:
            self.uz_czesciowe.append(key)

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
        wypis = ''
        for v in self.rozlicz.values():
            wypis += '\n'.join(['\t'.join(map(str, x)) for x in v]) + '\n'

        plik = open(os.path.join(self.kat, 'wypis_do_spr.csv'), 'w')
        plik.write(wypis)
        plik.close()
