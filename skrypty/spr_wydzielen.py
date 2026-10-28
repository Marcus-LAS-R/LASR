import os
import platform
import glob
from datetime import datetime
from qgis.core import Qgis, QgsMessageLog, QgsVectorLayer
from .przyciski import QMessageBox

from .sprawdzenia_warstw import SprawdzWydzielenia, sprawdz_odl_wydz, \
    sprawdz_odl_lz, sprawdz_pnsw, sprawdz_linie, sprawdz_powierzchnie_wydz
from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .shp_sprWydzOddz import spr_wydz_oddz
from .shp_pokaz_puste_wydz import (
    NAZWA_PUSTY_OPIS, rozbij_adres, warstwa_pusty_opis, zbierz_waypointy,
    znajdz_puste)
from . import waypointy


NAGLOWEK = '--- SPRAWDZENIE WYDZIELEŃ ---\n\n'


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
        self.kat = ''
        if isinstance(self.wydz, QgsVectorLayer) and \
                self.wydz.isValid():
            sciezka = self.wydz.dataProvider().dataSourceUri().split("|")[0][:-4]
            self.kat = os.path.dirname(sciezka)
        self.sl_wydz = {}  # sl z wydz w postaci {id: feat}
        self.sl_adr = {}  # sl z adr_les oraz id (adr_les: id)
        self.sl_lz = {}  # slownik z lz dla calego obiektu
        self.wydz_przek_odl = []  # lista z featurami z przekr odl w wydz
        self.baza = False  # zmienna z bazą
        self.waypointy_sc = None  # puste wydzielenia -> Nawigator błędów

        self.wypis = NAGLOWEK

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
        # baza_sc = znajdz_baze_do_wydz(self.iface, poz=1)
        baza_sc = znajdz_baze_do_wydz(self.iface, poz=1,  wskaz=True)
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

    def spr_puste(self):
        """Wydzielenia warstwy z pustym opisem w bazie (brak F_SUBAREA albo
        brak rodzaju powierzchni) - jak w "Pokaż puste wydzielenia";
        wydzieleń bez F_ARODES pilnuje już spr_wydz_baza."""
        wyps = '\n\n----[ SPRAWDZENIE PUSTYCH WYDZIELEŃ ]----\n'
        if not self.baza.polacz():
            self._na_poczatek(wyps + 'Brak połączenia z bazą\n' +
                              '----[ KONIEC SPRAWDZENIA PUSTYCH WYDZIELEŃ '
                              ']----\n\n')
            return
        # połączenie zostaje otwarte - korzystają z niego kolejne kontrole
        # (spr_pnsw -> baza.pobierz_pnsw)
        wynik = znajdz_puste(self.wydz, self.baza.cur)

        puste = wynik['pusty_opis']
        if puste:
            wyps += 'Wydzieleń bez rodzaju powierzchni: ' + str(len(puste)) + \
                '\n(Patrz warstwa "' + NAZWA_PUSTY_OPIS + '" dodana do TOC)\n'
            wyps += 'ADR_LES\tADRES\tPRZYCZYNA\n'
            wyps += '\n'.join(adr + '\t' + rozbij_adres(adr) + '\t' + prz
                              for adr, prz, _ in puste) + '\n'
            warstwa_pusty_opis(wynik, self.wydz.crs())
            # Nawigator błędów (las_r.sprawdzenie_wydzielen) - te same
            # waypointy co w "Pokaż puste wydzielenia", obok bazy
            kat = waypointy.katalog_raportow(
                os.path.dirname(os.path.abspath(self.baza.baza)))
            nazwa = os.path.splitext(os.path.basename(self.baza.baza))[0]
            self.waypointy_sc = os.path.join(
                kat, 'sprawdz_wydzielenia_waypointy_' + nazwa + '_' +
                datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '.csv')
            waypointy.zapisz(self.waypointy_sc, zbierz_waypointy(
                {'bez_opisu': [], 'pusty_opis': puste}))
            wyps += 'Waypointy (Nawigator błędów): ' + self.waypointy_sc + '\n'
        else:
            wyps += 'Brak pustych wydzieleń - OK\n'
        if wynik['pusty_bez_poligonu']:
            wyps += '\nPuste opisy w bazie bez poligonu na warstwie: ' + \
                str(len(wynik['pusty_bez_poligonu'])) + '\n'
            wyps += '\n'.join(adr + '\t' + rozbij_adres(adr) + '\t' + prz
                              for adr, prz in wynik['pusty_bez_poligonu']) + \
                '\n'
        self._na_poczatek(
            wyps + '----[ KONIEC SPRAWDZENIA PUSTYCH WYDZIELEŃ ]----\n\n')

    def _na_poczatek(self, tekst):
        """Sekcja zaraz po nagłówku raportu (puste wydzielenia - pierwsze,
        choć kontrola biegnie po sprawdzeniach podstawowych)."""
        if self.wypis.startswith(NAGLOWEK):
            self.wypis = NAGLOWEK + tekst.lstrip('\n') + \
                self.wypis[len(NAGLOWEK):]
        else:
            self.wypis = tekst + self.wypis

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
                'kodami oddziałów: ' + str(lniezg)
            self.wypis += '\n(Patrz warstwa błędów dodana do TOC)\n\n'

        if lniezg == 0 and lprzec == 0:
            self.wypis += 'Brak uwag do położenia wydz na oddziałach\n'
        self.wypis += '----[ KONIEC SPRAWDZANIA ODDZIAŁÓW ]----\n\n'
