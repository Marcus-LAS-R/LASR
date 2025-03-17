import os
import platform

from qgis.PyQt.QtWidgets import QFileDialog,  QDialog,  QMessageBox, \
    QApplication
from ..ui.ui_baza_zabiegi2 import Ui_Dialog
from qgis.utils import iface
from qgis.core import Qgis, QgsMessageLog

from .wydzielenie import Wydzielenie
from ..baza_wrapper import Baza


class Zabiegi():
    def __init__(self):
        self.iface = iface
        self.wybor = ''
        self.baza = False
        self.mod_trzeb = 0
        self.kat = ''  # katalog z bazą danych

        # sl ze struktura przetrzymujaca obkiety dla wydzielen z zabiegami
        # {adr_les: obiekt, ...}
        self.sl = {}
        self.bledy = []  # tab z numerami aid w ktorych wystapily bledy przy
        #                  generowaniu zabiegów
        self.zmodyfikowano = 0
        self.dodano = 0

        self.wydz = {}  # dict z {adr_les: arodes_int_num}
        self.wydz_id = {}  # {arodes_int_num: adr_les}
        self.wr = {}  # {species_cd: wiek_reb}
        self.janczulewicz_flag = False

    def pobierz_dane(self):
        self.dd = PobierzDane()
        self.dd.exec_()

        if self.dd.porzuc:
            return False

        if self.dd.ui.lineEdit_baza.text() not in ['', ' ', None, 'None']:
            self.baza = Baza(self.dd.ui.lineEdit_baza.text())
            if not self.baza.polacz():
                return False
            self.kat = os.path.dirname(self.dd.ui.lineEdit_baza.text())

            if self.dd.ui.radioButton_sprawdz.isChecked():
                self.wybor = 'Spr'
            if self.dd.ui.radioButton_uzpelnij.isChecked():
                self.wybor = 'Uzu'
            if self.dd.ui.radioButton_dopisz.isChecked():
                self.wybor = 'Dop'

            if self.dd.ui.checkBox_janczulewicz.isChecked():
                self.janczulewicz_flag = True

            self.kopiuj_baze()
            self.mod_trzeb = self.dd.ui.spinBox_trz.value()

            self.iface.messageBar().pushMessage(
                'Przetwarzam', f'Baza: {self.baza.baza}',
                Qgis.Info, 0
            )
            QApplication.processEvents()
            return True

        return False

    def kopiuj_baze(self) -> bool:
        if self.wybor == 'Uzu':
            self.baza.utworz_kopie('modyfikacja_zabiegow')
        if self.wybor == 'Dop':
            self.baza.utworz_kopie('dopisanie_zabiegow')
        return self.baza.polacz()

    def przetworz(self):
        """Metoda zbiorcza dla całego procesu"""
        self.wydz = self.baza.pobierz_wydzielenia()  # {adr_les: arodes_int}
        self.wydz_id = {v: k for k, v in self.wydz.items()}
        self.wr = self.baza.pobierz_wiek_reb()

        if self.wybor in ['Dop', 'Uzu']:
            self.baza.usun_zadrzew_w_przes()
            self.baza.usun_mase_z_podr_podsz_nal()

        for adr_les in self.wydz.keys():
            self._process_wydzielenie(adr_les)

        if self.iface:
            self.iface.messageBar().clearWidgets()
            QApplication.processEvents()

    def _process_wydzielenie(self, adr_les) -> None:
        ok, _wydz = self.przetworz_wydzielenie(adr_les)
        if not ok:
            # nie ma potrzeby dodawania info o błędzie, już poszło przy
            # wczytywaniu wydzielenia.
            return

        # wprowadziliśmy modyfikacje do bazy, trzeba jeszcze raz wszystko
        # odczytac i na nowo wygenerowac zabiegi
        if self.wybor in ['Dop', 'Uzu']:
            # if self.wybor == 'Dop':
            alt = '' if self.wybor == 'Dop' else 'alter'
            _wydz.modyfikuj_zabiegi(alt)

            # do raportu dla uzytkownika
            __uw_baza = _wydz.uw_baza
            self.zmodyfikowano += _wydz.zmodyfikowano
            self.dodano += _wydz.dodano
            del _wydz
            ok, _wydz = self.przetworz_wydzielenie(adr_les)
            if not ok:
                return
            _wydz.uw_baza += __uw_baza
            _wydz.wybor = self.wybor

        _wydz.zbiorcze_sprawdzenie()
        self.sl[adr_les] = _wydz

    def generuj_raport(self) -> None:
        '''Metoda generuje raport w katalogu z bazą danych'''
        if self.iface:  # pytest purposes
            self.iface.messageBar().pushMessage(
                'Generuje raport', '..........', Qgis.Info, 0
            )
            QApplication.processEvents()
        rap = ''
        for k in sorted(self.wydz.keys()):
            try:
                w = self.sl[k]
                if len(w.uw_raport+w.uw_baza) > 0:
                    rap += '\n'.join([
                        f'{k}#   '+x for x in w.uw_raport+w.uw_baza])
                    rap += '\n'
                if k in self.bledy:
                    rap += 'Coś się wysypało przy generowaniu, ' + \
                        'ale kto to wie? ¯\\_( ͡° ͜ʖ ͡°)_/¯\n'
            except Exception:
                rap += '\n'.join([
                    self.wydz_id[self.wydz[k]]+'#   ' +
                    'Cos poszlo nie tak w wypisaniu uwag do raport - ' +
                    'zonk!? - SPRAWDZIC!!!'
                ])
                rap += '\n'

        plik = open(
            os.path.join(self.kat, 'raport_zabiegi_'+self.baza.czas+'.txt'),
            'w',
        )
        plik.write(rap)
        plik.close()

        if self.iface:
            self.iface.messageBar().clearWidgets()
            QApplication.processEvents()

    def wyswietl_info(self):
        '''Wyswietla info dla uzytkownka w ramce okan oraz wypisuje do loga,
        wydzielenia z problemami podczas przetwarzania...'''
        self.iface.messageBar().clearWidgets()

        staty = ''
        if self.zmodyfikowano + self.dodano > 0:
            staty = \
                f'[dodano: {self.dodano}, zmodyfikowano: {self.zmodyfikowano}'
        if len(self.bledy) > 0:
            QgsMessageLog.logMessage(
                'Wystąpiły błędy przy generowaniu zabiegów dla poniższych '
                'wydzieleń, (patrz plik raportu):\n' +
                '\n'.join(self.bledy),
                'Las-R'
            )
            self.iface.messageBar().pushMessage(
                'Problemy',
                'Napotkano problemy przy generowaniu zabiegów, patrz log '
                + staty,
                Qgis.Warning,
                10
            )
        else:
            self.iface.messageBar().pushMessage(
                'OK',
                'Proces zakończony pomyślnie! '+staty,
                Qgis.Success,
                10
            )

        message = QMessageBox()
        message.setIcon(QMessageBox.Information)
        message.setWindowTitle('Raport')
        message.setText('Czy wyświetlić raport z generowania zabiegów?')
        message.addButton(u"Zamknij", QMessageBox.ActionRole)
        message.addButton(u"Zamknij i pokaż raport", QMessageBox.ActionRole)
        pok_rap = message.exec_()

        if pok_rap == 1:
            if platform.system()[:3] == 'Win':
                os.startfile(
                    os.path.join(self.kat,
                                 'raport_zabiegi_'+self.baza.czas+'.txt'))
            else:
                try:
                    import subprocess
                    subprocess.call(
                        ['kate',
                         os.path.join(
                             self.kat,
                             f'raport_zabiegi_{self.baza.czas}.txt')])
                except Exception:
                    self.iface.messageBar().pushMessage(
                        'Problemy',
                        'Nie znalazłem edytora Kate, proszę obsłużyć '
                        'się samemu'
                    )

    def przetworz_wydzielenie(self, adr: str) -> bool:
        """
            Wczytuje dane z bazy do struktury wydzielenia oraz generuje
            zabiegi, na podstawie ktorych potem moze zostac przeprowadzone
            sprawdzenie
            adr - adres lesny
        """
        if adr not in self.wydz:
            self.bledy.append(adr)
            return False, None

        try:
            _wydz = Wydzielenie()
            _aid = self.wydz[adr]
            _wydz.przygotuj_strukture(_aid)
            _wydz.dodaj_mod_trzeb(self.mod_trzeb)
            if self.janczulewicz_flag:
                _wydz.janczulewicz = True
            _wydz.baza = self.baza
            _wydz.o_wiek_rebnosci(self.wr)
            _wydz.odczytaj_dane_z_bazy(self.baza.pobierz_do_zab(_aid))

            if not _wydz.generuj_zabiegi():
                self.bledy.append(adr)
                return False, 'Nie wygenerowały się wskazówki, powinny?'
        except Exception:
            self.bledy.append(adr)
            return False, 'Cos się wysypało'
        return True, _wydz


class PobierzDane(QDialog):
    def __init__(self):
        super(PobierzDane, self).__init__()

        self.porzuc = True
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.pushButton_ok.clicked.connect(self.zatwierdz)
        self.ui.pushButton_porzuc.clicked.connect(self.porzucone)
        self.ui.pushButton_baza.clicked.connect(self.znajdz_baze)

    def porzucone(self):
        self.hide()

    def zatwierdz(self):
        if self.ui.lineEdit_baza.text() != '':
            self.porzuc = False
            self.hide()

    def znajdz_baze(self):
        sc = QFileDialog().getOpenFileName(
            self,
            'Wskaż baze Taksatora',
            '',
            "Access MDB (*.mdb);;SQLite (*.sqlite)")[0]
        if sc != '':
            self.ui.lineEdit_baza.setText(sc)
