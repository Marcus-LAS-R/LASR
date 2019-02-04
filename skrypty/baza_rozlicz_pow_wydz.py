import os
from qgis.core import QgsVectorLayer, QgsMessageLog, QgsProject, Qgis
# import processing  # import przeniesiony do metody - ulatwienie testowania
from PyQt5.QtCore import QVariant
from collections import defaultdict

from sprawdzenia_warstw import SprawdzWydzielenia
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

        # sl z informacjami dla kazde uzytku na ktorym lezy jakiekolwiek
        # wydzielenie, dane z bazy taksatora
        # { landid: [
        #             0 parcel_int_num
        #             1 shape_nr,
        #             2 pow rej,
        #             3 pow. graf. calego uzytku,
        #           ], }
        self.sl_uz_baza = {}

        # sl z danymi z intersecta ls z wydz w postaci:
        # { landid: {adr_les: pow_graf, ... }
        self.sl_uz_shp = recursivedefaultdict()

        # slownik z adr_les: arodes_int_num
        self.ls_adrles = {}

        QgsMessageLog.logMessage(
            '\n-----[ ROZLICZENIE POW WYDZIELEŃ ]-----', 'Las-R', Qgis.Info
        )

    def sprawdz_dane(self):
        """Metoda sprawdza czy w TOC znajdują się niezbędne warstwy, oraz czy
        są łatwo identyfikowalne, jeżeli tak zwraca True
        """
        # policz czy w TOC jest po jednej warstwie z LS i WYDZ
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        ls = len([x for x in lyrs if x.name()[:2].upper() == 'LS'])
        wydz = len([x for x in lyrs if x.name()[:4].upper() == 'WYDZ'])

        # Jeżeli jest więcej warstw które się tak nazywają zwróć użytkownikowi
        if len(ls) != 1 or len(wydz) != 1:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Zbyt wiele warstw LS lub WYDZ w TOCu!',
                Qgis.Warning,
                10
            )

        self.ls = ls[0]
        self.wydz = wydz[0]

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

        if 3 == len([x for x in self.ls.dataProvider().fields().toList()
                     if x.name() in ['LANDID', 'LAND_AR', 'LAND_POW', ]]):
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'W warstwie LS brakuje którejś z kolumn: LANDID, LAND_AR,'
                ' LAND_POW',
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

        processing.run(
            "saga:intersect",
            {
                'A': self.wydz,
                'B': self.ls,
                'SPLIT': False,
                'RESULT': os.path.join(self.tempkat,
                                       '__ls_wydz_inter.shp')
            }
        )

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
        """ metoda pobiera dane z bazy i shp i buduje niezbedne slowniki i
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
            if uz['LANDID'] not in self.sl_uz_shp:
                self.sl_uz_shp[uz['LANDID']][uz['ADR_LES']] = \
                    round(uz.geometry().area() / 10000, 4)
            else:
                if uz['ADR_LES'] not in uz['LANDID']:
                    self.sl_uz_shp[uz['LANDID']][uz['ADR_LES']] = \
                        round(uz.geometry().area() / 10000, 4)
                else:
                    self.sl_uz_shp[uz['LANDID']][uz['ADR_LES']] += \
                        round(uz.geometry().area() / 10000, 4)

        # pobierz sl wydzielen
        self.ls_adrles = self.baza.pobierz_wydzielenia()

        return True
