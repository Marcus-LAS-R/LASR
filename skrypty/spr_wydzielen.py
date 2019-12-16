import os
import platform
import glob
from qgis.core import Qgis, QgsMessageLog, QgsVectorLayer
from PyQt5.QtWidgets import QMessageBox

from .sprawdzenia_warstw import SprawdzWydzielenia, sprawdz_odl_wydz, \
    sprawdz_odl_lz, sprawdz_pnsw, sprawdz_linie, sprawdz_powierzchnie_wydz
from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .shp_sprWydzOddz import spr_wydz_oddz


class KontrolaWydzielen(SprawdzWydzielenia):
    def __init__(self, iface):
        self.iface = iface
        super()

        QgsMessageLog.logMessage(
                '\n--- SPRAWDZENIE WYDZIELEŃ ---\n',
                'Las-R',
                Qgis.Info
        )

        self.wydz = self.iface.activeLayer()
        sciezka = self.wydz.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.sl_wydz = {}  # sl z wydz w postaci {id: feat}
        self.sl_adr = {}  # sl z adr_les oraz id (adr_les: id)
        self.sl_lz = {}  # slownik z lz dla calego obiektu
        self.wydz_przek_odl = []  # lista z featurami z przekr odl w wydz
        self.baza = False  # zmienna z bazą

        self.wypis = '--- SPRAWDZENIE WYDZIELEŃ ---\n\n'

    def wczytaj_wydz(self):
        self.wydz = self.iface.activeLayer()
        if self.wydz is None:
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie odnaleziono warstwy wydzieleń',
                Qgis.Critical,
                10)
            return False

        if len([x.name() for x in self.wydz.dataProvider().fields().toList()
                if x.name() in ['ADR_LES', 'WYDZ', 'ODDZ', ]]) != 3:

            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie odnaleziono wymaganych pól w warstwie wydzieleń'
                '   [ADR_LES, ODDZ, WYDZ]',
                Qgis.Critical,
                10)
            return False
        return True

    def wczytaj_baze(self):
        baza_sc = znajdz_baze_do_wydz(self.iface, poz=1)
        if baza_sc:
            self.baza = Baza(baza_sc)
            if self.baza.polacz():
                return True
        self.iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie odnaleziono bazy!',
            Qgis.Critical,
            10)
        return False

    def zapisz_raport(self, prefix=''):
        """ Zapisuje raport do katalogu z wydzieleniami i daje uzytkownikow
        możliwość natychmiastowego jego otwarcia
        """
        if prefix == '':
            prefix = 'raport_spr_wydzielen_'

        czas = ''
        if self.baza is not False:
            czas = self.baza.czas

        sc = os.path.join(
            self.kat, '..', prefix+czas+'.txt')
        plik = open(sc, 'w')
        plik.write(str(self.wypis))
        plik.close()

        QgsMessageLog.logMessage(
                '\n\n----[ KONIEC SPRAWDZENIA WYDZIELEŃ]----\n',
                'Las-R',
                Qgis.Info
        )

        message = QMessageBox()
        message.setIcon(QMessageBox.Information)
        message.setWindowTitle('Raport')
        message.setText('Czy pokazać raport ze sprawdzania wydzieleń?')
        message.addButton(u"Zamknij", QMessageBox.ActionRole)
        message.addButton(u"Zamknij i pokaż raport", QMessageBox.ActionRole)
        pok_rap = message.exec_()

        if pok_rap == 1:
            if platform.system()[:3] == 'Win':
                os.startfile(sc)
            else:
                import subprocess
                subprocess.call(['kate', sc])

    def podst_spr(self):
        """ Wrapper do odziedziczonej metody poprawne_wydz, w celu dodania
        wypisu do raportu """

        if self.poprawne_wydz():
            self.wypis += self.wypis_sprawdzenia_wydz + '\n\n'
            return True

        self.wypis += self.wypis_sprawdzenia_wydz + '\n\n'
        self.wypis += '\n\n\nPrzerwano sprawdzanie wydzieleń, napraw ' + \
            'powyższe niedoskonałości!'
        return False

    def kontrola_odl(self):
        """ Metoda sprawdza odległości w wydz oraz odległości od Lz """

        l_odl_wydz, wyps = sprawdz_odl_wydz(self.iface, self.wydz)
        self.wypis += wyps

        l_odl_lz, wyps = sprawdz_odl_lz(self.iface, self.wydz)
        self.wypis += wyps

    def kontrola_powierzchni(self):
        wyn, wyps = sprawdz_powierzchnie_wydz(self.wydz, self.baza)
        self.wypis += wyps

    def znajdz_warstwe(self, nazwa=''):
        """ Metoda sprawdza czy w katalogu z wydz znajduje sie warstwa z podana
        nazwa (bez rozszerzenia), jeżeli tak zwraca wskaznik do QgsVectorLayer
        """
        warstwa = glob.glob(os.path.join(self.kat, nazwa + '.shp'))
        if len(warstwa) == 1:
            war = QgsVectorLayer(warstwa[0], 'warstwa', 'ogr')
            if war.isValid():
                return war

        return False

    def spr_pnsw(self):
        """ Meotoda sprwdza czy PNSW znajdują się w katalogu z wydz, jeżeli tak
        sprawdz układ wsp., sprawdz czy zawieraja sie w wydzieleniach,
        dopisz odpowiednie adr les.
        """
        war = self.znajdz_warstwe('PNSW')
        if war is not False:
            wyn, wyps = sprawdz_pnsw(self.wydz, war, self.baza)
        else:
            wyps = '\n----[ SPRAWDZENIE PNSW ]----\n' + \
                'Nie odnaleziono warstwy w katalogu z wydzieleniami' + \
                '\n----[ KONIEC SPRAWDZENIA PNSW ]----\n\n'

        self.wypis += wyps

    def spr_line(self):
        """Metoda sprawdza czy w katalogu z wydz znajduje sie warstwa linii,
        jezeli tak, sprawdza układ wsp. oraz czy wszystkie pola w warstwie sa
        wypełnione, oraz czy odpowiednie pola są w warstwie """

        war = self.znajdz_warstwe('LINIE')
        if war is not False:
            wyn, wyps = sprawdz_linie(war)
        else:
            wyps = '\n\n----[ SPRAWDZENIE LINI ]----\n' + \
                'Nie odnaleziono warstwy w katalogu z wydzieleniami' + \
                '\n----[ KONIEC SPRAWDZENIA LINI ]----\n\n'

        self.wypis += wyps

    def spr_oddz(self):
        """Metoda sprawdza czy w katalogu jest warstwa oddz, czy ma dobry
        układ odniesienia, i czy wydzielenia mają odpowiednie kody
        """
        war = self.znajdz_warstwe('ODDZ')
        if war is not False:
            wyn, lprzec, lniezg = spr_wydz_oddz(self.iface, self.wydz, war)
        else:
            self.wypis += '\n\n----[ SPRAWDZENIE ODDZ ]----\n' + \
                'Nie odnaleziono warstwy w katalogu z wydzieleniami' + \
                '\n----[ KONIEC SPRAWDZENIA ODDZ ]----\n\n'
            return

        self.wypis += '\n\n----[ SPRAWDZENIE ODDZIAŁÓW ]----\n'
        if lprzec > 0:
            self.wypis += 'Znaleziono wydzieleń przecinających oddziały: ' +\
                str(lprzec)
            self.wypis += '\n(Patrz warstwa błędów dodana do TOC)\n\n'

        if lniezg > 0:
            self.wypis += 'Znaleziono wydzieleń z niezgodnymi ' + \
                'kodami oddziałów: ' + str(lprzec)
            self.wypis += '\n(Patrz warstwa błędów dodana do TOC)\n\n'

        if lniezg == 0 and lprzec == 0:
            self.wypis += 'Brak uwag do położenia wydz na oddziałach\n'
        self.wypis += '----[ KONIEC SPRAWDZANIA ODDZIAŁÓW ]----\n\n'
