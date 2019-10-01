import os
import platform
from qgis.core import QgsMessageLog, Qgis
from PyQt5.QtWidgets import QFileDialog,  QDialog,  QMessageBox
from .ui.ui_baza_zabiegi import Ui_Dialog
from .baza_zabiegi_sl import ZabiegiSlownik
from .baza_wrapper import Baza


class Zabiegi():
    def __init__(self, iface):
        self.iface = iface
        self.wybor = ''
        self.baza = False
        self.kat = ''  # katalog z bazą danych

        # sl ze struktura przetrzymujaca obkiety dla wydzielen z zabiegami
        # {aid: obiekt, ...}
        self.sl = {}
        self.bledy = []  # tab z numerami aid w ktorych wystapily bledy przy
        #                  generowaniu zabiegów
        self.zmodyfikowano = 0
        self.dodano = 0

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
            self.kopiuj_baze()
            return True

        return False

    def przetworz(self):
        '''Metoda przetwarza podane dane do momentu gdzie uztykownik wybrał
        co dalej z nimi chce zrobić
        '''
        self.wydz = self.baza.pobierz_wydzielenia()
        self.wydz_id = {v: k for k, v in self.wydz.items()}
        wr = self.baza.pobierz_wiek_reb()
        self.iface.messageBar().pushMessage(
            'Przetwarzam', '..........', Qgis.Info, 0
        )

        for w in self.wydz.values():
            _wydz = Wydzielenie(w)
            _wydz.wczytaj_dane(self.baza.pobierz_do_zab(w))
            _wydz.wpisz_wiek_rebnosci(wr)

            try:
                if not _wydz.generuj_zabiegi():
                    self.bledy.append(w)

                else:
                    # w ponizszych zadaniach wymagana jest baza
                    _wydz.dodaj_baze(self.baza)

                    if self.wybor == 'Uzu':
                        _wydz.zmodyfikuj_zabiegi()

                    if self.wybor == 'Dop':
                        _wydz.zmodyfikuj_zabiegi()
                        _wydz.dopisz_zabiegi()

                    # jezeli cos dopisywalismy do baza musimy pobrac z bazyy
                    # jeszcze raz w celu sprawdzenia na istniejacych danych
                    if self.wybor in ['Dop', 'Uzu']:
                        # zmienne do zachowania
                        __uw_baza = _wydz.uw_baza
                        self.zmodyfikowano += _wydz.zmodyfikowano
                        self.dodano += _wydz.dodano

                        del _wydz
                        _wydz = Wydzielenie(w)
                        _wydz.wczytaj_dane(self.baza.pobierz_do_zab(w))
                        _wydz.wpisz_wiek_rebnosci(wr)
                        if not _wydz.generuj_zabiegi():
                            self.bledy.append(w)

                        _wydz.uw_baza += __uw_baza

                    _wydz.sprawdz_zabiegi()

                self.sl[w] = _wydz
            except:  # noqa
                self.bledy.append(w)

    def generuj_raport(self):
        '''Metoda generuje raport w katalogu z bazą danych'''
        rap = ''
        for k in sorted(self.wydz.keys()):
            w = self.sl[self.wydz[k]]
            if len(w.uw_raport+w.uw_baza) > 0:
                rap += '\n'.join([self.wydz_id[w.aid]+'#   '+x
                                  for x in w.uw_raport+w.uw_baza])
                rap += '\n'

        plik = open(os.path.join(self.kat,
                                 'raport_zabiegi_'+self.baza.czas+'.txt'),
                    'w',
                    encoding='cp1250')
        plik.write(rap)
        plik.close()

    def wyswietl_info(self):
        '''Wyswietla info dla uzytkownka w ramce okan oraz wypisuje do loga,
        wydzielenia z problemami podczas przetwarzania...'''
        self.iface.messageBar().clearWidgets()

        staty = ''
        if self.zmodyfikowano + self.dodano > 0:
            staty = '[dodano: '+str(self.dodano)+', zmodyfikowano: ' + \
                str(self.zmodyfikowano)+']'
        if len(self.bledy) > 0:
            QgsMessageLog.logMessage(
                'Wystąpiły błędy przy generowaniu zabiegów dla poniższych '
                'wydzieleń, (patrz plik raportu):\n' +
                '\n'.join([self.wydz_id[x] for x in self.bledy]),
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
                import subprocess
                subprocess.call(
                    ['kate',
                     os.path.join(self.kat,
                                  'raport_zabiegi_'+self.baza.czas+'.txt')])

    def kopiuj_baze(self):
        if self.wybor == 'Uzu':
            self.baza.utworz_kopie('modyfikacja_zabiegow')
        if self.wybor == 'Dop':
            self.baza.utworz_kopie('dopisanie_zabiegow')
        self.baza.polacz()


class GenerujZabiegi():
    def __init__(self):
        pass

    def generuj_rebnie(self, spr=True):
        if spr:
            if self.stl not in self.rebnieSl:
                return False
            if self.gat_gl_wiek < self.wiekReb - 9:
                return False
            if self.zadrzew < 0.5:
                return False
            if self.typ != 'D-STAN':
                return False

        if self.stl in self.rebnieSl:
            if len(self.rebnieSl[self.stl]) == 1:
                return [self.rebnieSl[self.stl][0]]
            else:
                if self.pow_wydz < 4:
                    return [self.rebnieSl[self.stl][0]]
                else:
                    return [self.rebnieSl[self.stl][1]]

        return False

    def generuj_rebnie_nowe(self, spr=True):  # noqa
        if spr:
            if self.stl not in self.rebnieSl:
                return False
            if self.gat_gl_wiek < self.wiekReb - 20:
                return False
            if self.wiekReb-9 > self.gat_gl_wiek:
                if self.zadrzew > 0.49:
                    return False
            if self.typ != 'D-STAN':
                return False

        # wyczysc zabiegi i trzebiez bo bedziemy generowac rebnie
        self.trzebierz = False
        self.zabiegi = []

        # ustaw rebnie podstawowa dla tego siedliska
        reb = self.rebnieSlnowy[self.stl][0]

        if self.pow_wydz < 0.5 or self.ile_dzkat < 2 and self.pow_wydz < 4:
            reb = self.rebnieSlnowy[self.stl][1]

        if self.struk == 'KO':
            if self.zadrzew >= 0.5:
                reb = self.rebnieSlnowy[self.stl][2]
            if self.zadrzew < 0.5:
                reb = self.rebnieSlnowy[self.stl][3]

        # jezeli jest forma ochrony przyrody to zwroc wariant 3
        if self.fop > 0:
            reb = self.rebnieSlnowy[self.stl][2]

        # dla wydzielen o powierzchi powyżej 10 ha
        if self.pow_wydz > 10 and self.ile_dzkat > 1:
            reb = ['IIB', 50]

        if self.zadrzew < 0.5 and self.gat_gl_wiek > self.wiekReb - 10:
            reb = self.rebnieSlnowy[self.stl][3]

        # dstan rozsypujacy sie przed wiekiem rebnosci
        if self.zadrzew < 0.5 and \
                self.wiekReb - 10 > self.gat_gl_wiek > self.wiekReb - 20:
            reb = ['IVDU', 100]

            self.uw_raport.append(
                'Wygenerowano zabiegi dla D-STANU na wydz. ' +
                'z zadrzew <0.5 ' +
                'i wiekiem rębności gat. gł. ' +
                str(self.gat_gl_wiek)+' lat (baza: '+str(self.wiekReb) +
                ' lat) # rębnia wygenerowana:(' + reb[0] + ', ' + str(reb[1])
                + '%); ' + 'baza: [' + ', '.join([x for x in self.cue]) + ']'
            )

            # dopisz info o przebudowie w uwagach
            if len(self.uwagi) + len(self.uw_sl['przebud']['c']) < 255:
                if self.uw_sl['przebud']['c'] not in self.uwagi:
                    self.uwagi += self.uw_sl['przebud']['c']
            elif len(self.uwagi) + len(self.uw_sl['przebud']['s']) < 255:
                if self.uw_sl['przebud']['s'] not in self.uwagi:
                    self.uwagi += self.uw_sl['przebud']['s']
            else:
                self.uw_raport.append(self.uw_sl['przebud']['r'])

            return [reb]

        if self.uszk == '3':
            reb = self.rebnieSlnowy[self.stl][1]
            # dodaj informacje o zmianie standardowego drylu
            if len(self.uwagi) + len(self.uw_sl['uszk']['c']) < 255:
                if self.uw_sl['uszk']['c'] not in self.uwagi:
                    self.uwagi += self.uw_sl['uszk']['c']
            elif len(self.uwagi) + len(self.uw_sl['uszk']['s']) < 255:
                if self.uw_sl['uszk']['s'] not in self.uwagi:
                    self.uwagi += self.uw_sl['uszk']['s']
            else:
                self.uw_raport.append(self.uw_sl['uszk']['r'])

        return [reb]

    def zab_plaz(self):
        if self.typ == 'PŁAZ':
            self.zabiegi.append(['PŁAZ', self.pow_wydz])
            self.zabiegi.append(['ODN-ZRB', self.pow_wydz])
        if self.typ == 'HAL':
            self.zabiegi.append(['ODN-HAL', self.pow_wydz])
        if self.typ == 'ZRĄB':
            self.zabiegi.append(['ODN-ZRB', self.pow_wydz])

        self.zabiegi.append(['AGROT', self.pow_wydz])
        self.zabiegi.append(['PIEL', self.pow_wydz])

    def zab_dstan_cp(self):
        if self.gat_gl_vol == 0:
            self.zabiegi.append(['CP', self.pow_wydz])
        elif self.gat_gl_vol > 0 and self.gat_gl_bhd < 10:
            if self.gat_gl[:2] in ['TP', 'BR', 'WB', 'OS']:
                self.zabiegi.append(['TW', self.pow_wydz])
                self.trzebierz = True
            else:
                self.zabiegi.append(['CP', self.pow_wydz])
        elif self.gat_gl_vol > 0 and self.gat_gl_bhd > 9.9999:
            self.zabiegi.append(['TW', self.pow_wydz])
            self.trzebierz = True

    def zab_dstan_trz(self):
        if self.gat_gl_bhd < 20:
            self.zabiegi.append(['TW', self.pow_wydz])
        else:
            self.zabiegi.append(['TP', self.pow_wydz])
        self.trzebierz = True

    def zab_dstan_nowe(self):  # noqa
        if self.struk == 'W PIĘTR':
            self.uw_raport.append(
                'Wydzielenie ze strukturą d-stanu wielopiętrowego'
            )
            return
        if self.struk == '2 PIĘTR':
            self.uw_raport.append(
                'Wydzielenie ze strukturą d-stanu dwupiętrowego'
            )
            return
        if self.struk == 'SP':
            self.uw_raport.append(
                'Wydzielenie ze strukturą przerębową'
            )
            return

        if self.gat_gl_wiek < 22:
            if 0.4 < self.zadrzew < 0.8:
                self.zabiegi.append([
                    'POPR', round((1-self.zadrzew)*self.pow_wydz, 4)])
                self.zabiegi.append([
                    'AGROT', round((1-self.zadrzew)*self.pow_wydz, 4)])
                self.zabiegi.append([
                    'PIEL', round((1-self.zadrzew)*self.pow_wydz, 4)])

        if self.gat_gl_wiek < 10:
            self.zabiegi.append(['CW', self.pow_wydz])
            return

        if 9 < self.gat_gl_wiek < 20:
            self.zab_dstan_cp()
            return

        if 19 < self.gat_gl_wiek < 40:
            self.gen_reb = ''
            self.gen_proc_reb = 0
            # generuj trzebierze tylko jesli uzytkownik nic nie wpisał
            if self.reb == '':
                self.zab_dstan_trz()
            return

        if self.wiekReb - 9 > self.gat_gl_wiek > 39:
            self.gen_reb = ''
            self.gen_proc_reb = 0
            if self.reb == '':
                self.zabiegi.append(['TP', self.pow_wydz])
                self.trzebierz = True

        genr = self.generuj_rebnie_nowe()
        # wygeneruj rebnie o ile jest taka mozliwość
        if genr is not False:
            self.gen_reb = genr[0][0]
            self.gen_proc_reb = genr[0][1]
            self.gen_pow_reb = self.pow_wydz * (self.gen_proc_reb/100)

            # generuj zabiegi dodatkowe dla rebni, o ile nie wygenerowano
            if len(self.zabiegi) == 0:
                self.zab_dstan_odn_reb()

        # jezeli mamy rebnie zupelna to i pow wydz powyzej 4ha dodaj uwage o
        # traktowaniu dzialek ewid jako zrebowe
        if self.gen_reb in ['IA', 'IB', 'IC', ]:
            if self.ile_dzkat > 1 and self.pow_wydz > 1:
                # dodaj informacje o zmianie standardowego drylu
                if len(self.uwagi) + len(self.uw_sl['reb_zup']['c']) < 255:
                    if self.uw_sl['reb_zup']['c'] not in self.uwagi:
                        self.uwagi += self.uw_sl['reb_zup']['c']
                elif len(self.uwagi) + len(self.uw_sl['reb_zup']['s']) < 255:
                    if self.uw_sl['reb_zup']['s'] not in self.uwagi:
                        self.uwagi += self.uw_sl['reb_zup']['s']
                else:
                    self.uw_raport.append(self.uw_sl['reb_zup']['r'])


    def zab_dstan(self):  # noqa
        if self.struk == 'W PIĘTR':
            self.uw_raport.append(
                'Wydzielenie ze strukturą d-stanu wielopiętrowego'
            )
            return
        if self.struk == '2 PIĘTR':
            self.uw_raport.append(
                'Wydzielenie ze strukturą d-stanu dwupiętrowego'
            )
            return
        if self.struk == 'SP':
            self.uw_raport.append(
                'Wydzielenie ze strukturą przerębową'
            )
            return

        genr = self.generuj_rebnie()
        # wygeneruj rebnie o ile jest taka mozliwość
        if genr is not False and self.gat_gl_wiek + 9 >= self.wiekReb:
            self.gen_reb = genr[0][0]
            self.gen_proc_reb = genr[0][1]
            self.gen_pow_reb = self.pow_wydz * (self.gen_proc_reb/100)

        # jezeli uszkodzenia z 2, 3 klasy usuwamy dstan rebnią
        if self.uszk in ('3', '4', ):
            _genr = self.generuj_rebnie(spr=False)
            if _genr is not False:
                self.gen_reb = _genr[0][0]
                self.gen_proc_reb = _genr[0][1]
                self.gen_pow_reb = self.pow_wydz * (self.gen_proc_reb/100)

                # dodaj informacje o zmianie standardowego drylu
                if len(self.uwagi) + len(self.uw_sl['uszk']['c']) < 255:
                    if self.uw_sl['uszk']['c'] not in self.uwagi:
                        self.uwagi += self.uw_sl['uszk']['c']
                elif len(self.uwagi) + len(self.uw_sl['uszk']['s']) < 255:
                    if self.uw_sl['uszk']['s'] not in self.uwagi:
                        self.uwagi += self.uw_sl['uszk']['s']
                else:
                    self.uw_raport.append(self.uw_sl['uszk']['r'])
                # dopisz odnowienie do rebni w zaleznosci od typu
                self.zab_dstan_odn_reb()
                return

        if self.struk == 'KO':
            _genr = self.generuj_rebnie(spr=False)
            if _genr is False:
                self.gen_reb = 'IIB'
                self.gen_proc_reb = 50
                self.gen_pow_reb = self.pow_wydz * (self.gen_proc_reb/100)

            # jezeli wygenerowane rebnie to I albo II to przerzucamy na IIB
            elif _genr[0] in self.rebnieSpis[:11]:
                self.gen_reb = 'IIB'
                self.gen_proc_reb = 50
                self.gen_pow_reb = self.pow_wydz * (self.gen_proc_reb/100)

            # jezeli co co innego to przezucamy ma IVDU
            else:
                self.gen_reb = 'IVDU'
                self.gen_proc_reb = 100
                self.gen_pow_reb = self.pow_wydz * (self.gen_proc_reb/100)

            # dopisz odnowienie do rebni w zaleznosci od typu
            self.zab_dstan_odn_reb()
            return

        # jezeli mamy rebnie zupelna to i pow wydz powyzej 4ha dodaj uwage o
        # traktowaniu dzialek ewid jako zrebowe
        if self.gen_reb in ['IA', 'IB', 'IC', ]:
            if self.ile_dzkat > 3 or self.pow_wydz > 3.9999:
                # dodaj informacje o zmianie standardowego drylu
                if len(self.uwagi) + len(self.uw_sl['reb_zup']['c']) < 255:
                    if self.uw_sl['reb_zup']['c'] not in self.uwagi:
                        self.uwagi += self.uw_sl['reb_zup']['c']
                elif len(self.uwagi) + len(self.uw_sl['reb_zup']['s']) < 255:
                    if self.uw_sl['reb_zup']['s'] not in self.uwagi:
                        self.uwagi += self.uw_sl['reb_zup']['s']
                else:
                    self.uw_raport.append(self.uw_sl['reb_zup']['r'])

        # dopisz odnowienie do rebni w zaleznosci od typu
        self.zab_dstan_odn_reb()

        if self.gat_gl_wiek < 22:
            if 0.4 < self.zadrzew < 0.8:
                self.zabiegi.append([
                    'POPR', round((1-self.zadrzew)*self.pow_wydz, 4)])
                self.zabiegi.append([
                    'AGROT', round((1-self.zadrzew)*self.pow_wydz, 4)])
                self.zabiegi.append([
                    'PIEL', round((1-self.zadrzew)*self.pow_wydz, 4)])

        if self.gat_gl_wiek < 10:
            self.zabiegi.append(['CW', self.pow_wydz])
            return

        if 9 < self.gat_gl_wiek < 20:
            self.zab_dstan_cp()
            return

        if 19 < self.gat_gl_wiek < 40:
            self.gen_reb = ''
            self.gen_proc_reb = 0
            # generuj trzebierze tylko jesli uzytkownik nic nie wpisał
            if self.reb == '':
                self.zab_dstan_trz()
            return

        if self.wiekReb - 9 > self.gat_gl_wiek > 39:
            self.gen_reb = ''
            self.gen_proc_reb = 0
            if self.reb == '':
                self.zabiegi.append(['TP', self.pow_wydz])
                self.trzebierz = True

        # d-stan rozsypuje sie 10 lat przed wiekiem rebnosci - przebudowa  IIB
        if 0.399 < self.zadrzew < 0.51 and (
                self.wiekReb-21 < self.gat_gl_wiek < self.wiekReb-9):
            # kasuj wszystko co zstało wygenerowane
            self.trzebierz = False
            self.zabiegi = []
            # ustaw rebnie i oblicz dane
            self.gen_reb = 'IIB'
            self.gen_proc_reb = 50
            self.gen_pow_reb = self.pow_wydz * (self.gen_proc_reb/100)
            # dopisz info o przebudowie w uwagach
            if len(self.uwagi) + len(self.uw_sl['przebud']['c']) < 255:
                if self.uw_sl['przebud']['c'] not in self.uwagi:
                    self.uwagi += self.uw_sl['przebud']['c']
            elif len(self.uwagi) + len(self.uw_sl['przebud']['s']) < 255:
                if self.uw_sl['przebud']['s'] not in self.uwagi:
                    self.uwagi += self.uw_sl['przebud']['s']
            else:
                self.uw_raport.append(self.uw_sl['przebud']['r'])
            # dopisz odnowienie do rebni w zaleznosci od typu
            self.zab_dstan_odn_reb()

        if self.zadrzew < 0.5 and len(self.zabiegi) == 0:
            genr = self.generuj_rebnie(spr=False)
            if genr is not False:
                if genr[0] not in ['IB']:
                    genr = [['IVDU', 100]]
                self.gen_reb = genr[0][0]
                self.gen_proc_reb = genr[0][1]
                self.gen_pow_reb = round(
                    self.pow_wydz * (self.gen_proc_reb/100), 4)
                self.zab_dstan_odn_reb()

                self.uw_raport.append(
                    'Wygenerowano zabiegi dla D-STANU na wydz. ' +
                    'z zadrzew <0.5 ' +
                    'i wiekiem rębności gat. gł. ' +
                    str(self.gat_gl_wiek)+' lat (baza: '+str(self.wiekReb) +
                    ' lat) # zabiegi wygenerowane:(' + self.gen_reb + ', ' +
                    ', '.join([x[0] for x in self.zabiegi]) + ')'
                )
            else:
                self.uw_raport.append(
                    'Niewygenerowano zabiegów dla D-STANU na wydz. ' +
                    'z zadrzew <0.5 ' +
                    'i wiekiem rębności gat. gł. ' +
                    str(self.gat_gl_wiek)+' lat (baza: '+str(self.wiekReb) +
                    ' lat) # BŁĄD GENEROWANIA ZABIEGÓW!!'
                )

    def zab_dstan_odn_reb(self):
        # jezeli użyszkodnik wpisał jakąś rębnie to zabiegi generujemy dla
        # podanej przez niego rebni, a jeżeli nic nie podał to jedziemy z
        # rębnią ze słownika
        # jezeli uzyszkodnik wpisal trzebiez to nie generu zabiegow dla rebni
        if len([x for x in ['TP', 'TW', 'CP-P'] if x in self.cue]) > 0:
            return

        if self.reb != '':
            rr = self.reb
            rr_proc = self.proc_reb
            if self.proc_reb > 100:
                rr_proc = 100
            rr_pow = round(self.pow_wydz * (rr_proc/100), 4)
        else:
            rr = self.gen_reb
            rr_pow = self.gen_pow_reb
            rr_proc = self.gen_proc_reb

        # rebnie zupełne
        if rr in ['IA', 'IB', 'IC']:
            self.zabiegi.append(['ODN-ZRB', rr_pow])
            self.zabiegi.append(['PIEL', rr_pow])
            self.zabiegi.append(['AGROT', rr_pow])
            return

        # inne rebnie cześciowe
        elif rr in self.rebnieSpis:
            odn_cz = 0
            np_sum = self.nal + self.podr + self.pods
            if np_sum > 0.1:
                odn_cz = np_sum - 0.1

            # oblicz pow odnowienia dla rebni cz
            pow_odn = round(
                (rr_proc/100)*self.pow_wydz*(1-odn_cz), 4
            )

            self.zabiegi.append(['ODN-ZŁOŻ', pow_odn])
            self.zabiegi.append(['PIEL', pow_odn])
            self.zabiegi.append(['AGROT', pow_odn])

    def generuj_zabiegi(self):
        """ Metoda generuje zabiegi w tablicy zab dla danego
        wydzelenia w tablicy w postaci: [['ZABIEG', POW],...]
        """

        # kolejność wpisanych zabieów wpisanych do bazy będzie taka jak w
        # tabeli, numeracja będie kontynuowana od największego wpisanego do
        # bazy zabiegu, o ile taki istnieje. Jak nie to zanie od zera
        if self.przes:
            self.zabiegi.append(['PRZEST', self.pow_wydz])

        if self.typ in ['PŁAZ', 'ZRĄB', 'HAL']:
            self.zab_plaz()

        if self.typ == 'D-STAN':
            self.zab_dstan_nowe()

            if self.trzebierz:
                if 0.4 < self.zadrzew < 0.9:
                    if self.luki > 0:
                        powluk = round(self.luki, 4)
                        self.zabiegi.append(['ODN-LUK', powluk])
                        self.zabiegi.append(['PIEL', powluk])
                        self.zabiegi.append(['AGROT', powluk])

        return True

    def oblicz_ciecie(self):  # noqa
        ''' zwraca % ciecia dla wydz oraz wartosc pozyskania grubizny
        '''
        # skroc nazwy do 2 lub 3 liter, tylko takie mamy dostepne w slowniku
        gat = ''
        if 'BRZ' in self.gat_gl:
            gat = 'BRZ'
        else:
            gat = self.gat_gl[:2].upper()

        # zagreguj nazwy gatunkow do 6 podstwowych gat ze sl cieć
        if gat in ['MD', 'LB']:
            gat = 'SO'
        if gat in ['JS', 'WZ', 'KL', 'GB', 'JW', ]:
            gat = 'DB'
        if gat in ['DG', ]:
            gat = 'ŚW'

        # jezeli dalej sa jakies wymyslone gatunki, policz jak dla BRZ
        if gat not in ['SO', 'DB', 'ŚW', 'BRZ', 'JD', 'BK', 'OL', ]:
            gat = 'BRZ'

        klWieku = sorted(self.cieciaSl[gat].keys())
        wiek = 0  # zmienna dla przedzialu wieku gatGl
        if self.gat_gl_wiek < klWieku[0] + 1:
            wiek = klWieku[0]
        elif self.gat_gl_wiek > klWieku[-1] - 1:
            wiek = klWieku[-1]
        else:
            for i in range(1, len(klWieku)):
                if klWieku[i-1] < self.gat_gl_wiek < klWieku[i]:
                    wiek = klWieku[i]

        if self.gat_gl_vol < 6:
            zas = 5
        elif 5 < self.gat_gl_vol < 11:
            zas = 10
        else:
            zas = round(self.gat_gl_vol/10, 0)*10

        # jezeli zasobnosc jest wieksza niz max w tablicach zwroc max tablicowe

        maxZas = max([x for x in self.cieciaSl[gat][wiek].keys()])

        if 199 < zas < 300:
            zas = 200
        if zas > maxZas - 1:
            zas = maxZas

        zw = {
              u'UM': 1,
              u'PRZ': 2,
              u'PEŁ': 0,
              u'LUŹ': 3,
              }

        if self.zwarcie in zw.keys():
            # zwracamy tablice [procent grub, m3 grub]
            proc = self.cieciaSl[gat][wiek][int(zas)][zw[self.zwarcie]]
            pow_ciecia = self.pow_wydz
            if self.gen_pow_reb > 0:
                pow_ciecia = self.gen_pow_reb
            return [
                proc,
                round(self.gat_gl_vol * (float(proc)/100) * pow_ciecia, 0)
            ]

        # jezeli nie udalo sie znalezc danych w slowniku zwroc 10% grubizny
        return [
                99,
                round(self.gat_gl_vol * self.pow_wydz, 0)
                ]


class SprawdzZabiegi():
    # def __init__(self):
        # pass

    def sprawdz_zabiegi(self):
        '''Metoda sprawdza wpisane do bazy zabiegi z tymi ktore zostały
        wygenerowane prze klase GenerujZabiegi i zapisuje raport sprawdzenia
        w katalogu z baza
        '''
        self.sprawdz_luki()
        self.sprawdz_halizne()
        self.sprawdz_ile_rebni()
        self.sprawdz_KO_KDO()
        self.sprawdz_dopasowanie_reb()
        self.sprawdz_dopasowanie_odn()
        self.sprawdz_pow_rebni()
        self.sprawdz_wiek_rebnosci()
        self.sprawdz_zadrzewienie()
        self.sprawdz_wpisanie_rebni()
        self.sprawdz_wpisanie_zabiegow()
        self.sprawdz_stopien_uszkodzen()

    def sprawdz_luki(self):
        ''' sprawdz czy w tym wydzieleniu nie powinno byc luk ze wzg na wiek,
        badź wpisana rebnie w zbiegach
        '''
        if self.luki > 0:
            if self.gat_gl_wiek < 20 or self.reb in self.rebnieSpis:
                self.uw_raport.append(
                    'Nie powinno być luk w tym wydzieleniu, '
                    'ze wzgl na wiek/rębnie'
                )

    def sprawdz_halizne(self):
        if self.zadrzew < 0.5 and self.typ == 'D-STAN':
            if self.gat_gl_vol == 0:
                self.uw_raport.append('Zadrzewienie poniżej 0.5 -> HAL')
            if self.brak_zad:
                self.uw_raport.append('Brak wpisanego zadrzewienia w bazie')

    def sprawdz_ile_rebni(self):
        if self.ile_reb > 1:
            self.uw_raport.append(
                'Stwierdzono wpisanie więcej niż jednej rębni w wydzieleniu'
            )

    def sprawdz_KO_KDO(self):
        ''' to sprawdzenie powinno byc puszczane tylko wtedy gdy mamy pewnosc
        ze w bazie mamy wpisana tylko 1 rebnie
        '''
        if self.ile_reb == 1:
            if self.pods + self.nal + self.podr > 0.49 and \
                    self.struk not in ['KO', 'KDO']:
                self.uw_raport.append(
                    'W strukturze powinno być KO/KDO '
                    '(ze zwzgl na pods+nal+podr>=0.5) (' +
                    str(self.pods) + ', ' +
                    str(self.nal)+", "+str(self.podr)+")")

    def sprawdz_dopasowanie_reb(self):
        if self.ile_reb == 1:
            _reb = self.reb.replace('U', '')
            if _reb not in [
                    x[0] for x in self.rebnieSl[self.stl]] + ['PŁAZ', 'IVD']:

                self.uw_raport.append(
                    'Rębnia niedostosowana do STL ('+self.stl +
                    '), jest: ' +
                    self.reb + ' (' + str(self.pow_reb) + 'ha)'
                    ', sugerowane: ' +
                    ', '.join([x[0] for x in self.rebnieSl[self.stl]])
                )

    def sprawdz_pow_rebni(self):
        if self.ile_reb == 1:
            if self.reb.replace('U', '') in self.rebnieSpis[:3] and \
                    self.pow_reb > 3.9999:
                self.uw_raport.append(
                    'Rębnia zupełna na powierzchni większej niż 4 ha (' +
                    str(self.ile_dzkat) + ' dz. ewid.)'
                )

                if self.pow_wydz > self.pow_reb:
                    self.uw_raport.append(
                        'Powierzchnia rębni mniejsza od powierzchni '
                        'wydzielenia  ' +
                        str(self.pow_reb) + ' / ' + str(self.pow_wydz) + ' ha'
                    )

            if self.pow_wydz < self.pow_reb:
                self.uw_raport.append(
                    'Powierzchnia rębni większa od powierzchni wydzielenia  ' +
                    str(self.pow_reb) + ' / ' + str(self.pow_wydz) + ' ha'
                )

    def sprawdz_dopasowanie_odn(self):
        if self.ile_reb == 1:
            if ('ODN-ZRB' in self.cue and self.reb not in
                    self.rebnieSpis[:3]+[self.rebnieSpis[24]]):
                self.uw_raport.append('Odnowienie zrębu na rębni częściowej')
            if ('ODN-ZŁOŻ' in self.cue and
                    self.reb not in self.rebnieSpis[3:24]):
                self.uw_raport.append('Odnowienie złożone na rębni zupełnej')

    def sprawdz_wiek_rebnosci(self):
        if self.gen_reb != '' or self.reb in self.rebnieSpis:
            if self.gat_gl == '' or self.gat_gl_wiek == 0:
                self.uw_raport.append('Nie wpisano gatunku głównego lub wieku')
                return

            if self.gat_gl_wiek < self.wiekReb - 11:
                if self.reb not in ['PŁAZ', 'IVD'] and \
                        self.uszk not in ['2', '3']:
                    self.uw_raport.append(
                        'Rębnia poniżej wieku rębności, ' +
                        self.reb +
                        ' w wieku: ' +
                        str(self.gat_gl_wiek) +
                        ', wiek rębności w bazie ustalono na: ' +
                        str(self.wiekReb) + '; opis w bazie: (' +
                        self.uwagi + ')'
                        )

    def sprawdz_stopien_uszkodzen(self):
        if self.reb == '' and self.uszk == '2':
            self.uw_raport.append(
                'Brak wpisanej rębni przy 2 stopniu' +
                ' uszkodzeń, do sprawdzenia')

    def sprawdz_zadrzewienie(self):
        if self.zadrzew > 1.4:
            self.uw_raport.append('Zadrzewienie większe niż 1.4')

    def sprawdz_wpisanie_zabiegow(self):
        for zab in self.zabiegi:
            if zab[0] in self.cue:
                if round(zab[1], 4) != round(self.cue[zab[0]], 4):
                    self.uw_raport.append(
                        'Zabieg: ' + zab[0] +
                        ", ma powierzchnię niezgodną z wygenerowaną: " +
                        str(zab[1]) + 'ha, (baza: ' + str(self.cue[zab[0]]) +
                        'ha)')
            else:
                self.uw_raport.append(
                    'Nie wpisano zabiegu: ' + zab[0] +
                    ", o powierzchni: " + str(zab[1])+u', # [' +
                    ', '.join(self.cue.keys()) + ']')

        if len(self.cue) == 0 and self.typ in [
                'PŁAZ', 'D-STAN', 'HAL', 'ZRĄB']:
            self.uw_raport.append('-->> Brak wpisanych zabiegów w bazie!!')

    def sprawdz_wpisanie_rebni(self):
        if self.reb == '' and self.gen_reb != '' and self.typ == 'D-STAN':
            self.uw_raport.append(
                'Nie dodano rebni do wydzielenia? ('+self.gen_reb+') # [' +
                ', '.join([x for x in self.cue.keys()]) + ']'
            )


class Wydzielenie(ZabiegiSlownik, GenerujZabiegi, SprawdzZabiegi):
    def __init__(self, aid):
        # wczytaj wpisy i slowniki
        self.spisy()

        # wskaznik do bazy w celu wpisywania danych, wykorzystywany w metodzie
        # dopisz_zabiegi
        self.baza = False

        self.dodano = 0  # ile rekordow dodano do bazy taksatora
        self.zmodyfikowano = 0  # ile rekordow zmodyfikowano/ powierzchnie
        self.fop = 0  # policz ile form ochrony przyrody jest na wydzieleniu

        self.aid = aid  # arodes_int_num
        self.adr = ''
        self.przes = False
        self.nal = 0
        self.podr = 0
        self.pods = 0

        # dane rebni wpisanej do bazy przez taksatora
        self.reb = ''
        self.ile_reb = 0
        self.pow_reb = 0
        self.proc_reb = 0

        # dane rebni wygeneowanej przez skrypt
        self.gen_reb = ''
        self.gen_pow_reb = 0
        self.gen_proc_reb = 0

        self.gat_gl = ''
        self.struk = ''
        self.zadrzew = 0
        self.luki = 0
        self.ile_dzkat = 0
        self.gat_gl_wiek = 0
        self.gat_gl_udz = 0
        self.gat_gl_vol = 0
        self.gat_gl_bhd = 0

        # ostatnia wartość z jaką coś jest wpisane do bazy
        self.max_cue = 0

        self.wiekRebSl = {}  # slownik z bazy z rokiem rebnosci dla poszcz gat.
        self.wiekReb = 120  # wiek rebności standardowo ustawiamy na 120 lat
        self.przest_vol = 0
        self.plaz_vol = 0
        self.brak_zad = False
        self.zwarcie = ''
        self.trzebierz = False  # flaga do sprawdzenia luk na trzebierzach
        self.uszk = ''  # stopien uszkodzenia d-stanu
        self.uw_dopisz = ''  # string z uwagami do dopisania do f_subarea
        self.uw_raport = []  # tablica z uwagami do raportu
        self.uw_baza = []  # tablica z uw. z wpisywana do bazy...
        self.uwagi = ''  # string z uwagami w bazie, max dł 255 znaków!!!

        # tabela z wygenerowanymi zabiegami w postaci:
        # [[zab: pow], ...] kolejnosc ma znaczenie!
        self.zabiegi = []

        # tab z wpisanymi zabiegami przez taksatorow, brak kolejnosci zabiegow
        self.cue = {}

    def isNone(self, it):
        if it is None:
            return 0
        else:
            return it

    def isNoneT(self, it):
        if it is None:
            return ''
        else:
            return it

    def dodaj_baze(self, baza):
        ''' jezeli bedzie potrzeba dodawania poprawek badz nowych wpisow do
        bazy nalezy poddac wskaznik do obiektu z podłączoną baza.
        '''
        try:
            if baza.polacz():
                self.baza = baza
                return True
        except:  # nopep8
            pass

        return False

    def wpisz_wiek_rebnosci(self, sl):
        self.wiekRebSl = sl
        # Pobierz wiek rebnosci dla gatunku głównego
        if self.gat_gl != '':
            _wiekReb = self.isNone(self.wiekRebSl[self.gat_gl])
            if _wiekReb > 0:
                self.wiekReb = _wiekReb

    def wpisz_pod_nal(self, tab):
        for t in tab:
            if t[1] == 'PODR':
                self.podr = round(self.isNone(t[2]), 1)
            if t[1] == 'NAL':
                self.nal = round(self.isNone(t[2]), 1)
            if t[1] == 'PODS':
                self.pods = round(self.isNone(t[2]), 1)

            if t[1] == 'DRZEW' and t[3] == 1:
                self.zadrzew = round(self.isNone(t[2]), 1)
                if t[4] is not None:
                    self.zwarcie = t[4]

                # ustaw flage jesli brak wpisanego zadrzewienia
                if t[2] is None:
                    self.brak_zad = True

    def wpisz_ist_zab(self, tab):
        for t in tab:
            # typ_zab: pow zab
            self.cue[t[1]] = t[2]
            if self.max_cue < t[3]:
                self.max_cue = t[3]
            if t[1] in self.rebnieSpis:
                self.proc_reb = float(self.isNone(t[5]))
                if self.proc_reb == 0:
                    self.proc_reb = float(self.isNone(t[4]))
                self.reb = t[1]
                self.pow_reb = self.isNone(t[2])
                self.ile_reb += 1

    def wpisz_przest(self, tab):
        if len(tab) > 0:
            self.przes = True

    def wpisz_gat_gl(self, tab):
        if not isinstance(tab, type([])):
            return
        if len(tab) > 0:
            self.gat_gl = tab[0][1]
            self.gat_gl_bhd = self.isNone(tab[0][4])
            self.gat_gl_wiek = self.isNone(tab[0][3])
            self.gat_gl_vol = self.isNone(tab[0][5])
            self.gat_gl_udz = self.isNone(tab[0][2])

        if self.gat_gl != '' and len(self.wiekRebSl.keys()) > 0:
            _wiekReb = self.isNone(self.wiekRebSl[self.gat_gl])
            if _wiekReb > 0:
                self.wiekReb = _wiekReb

    def wpisz_szczeg_wydz(self, tab):
        if len(tab) > 0:
            self.pow_wydz = round(self.isNone(tab[0][3]), 4)
            self.typ = tab[0][1]
            self.stl = tab[0][2]
            self.opis = tab[0][4]
            self.struk = tab[0][5]
            self.uszk = self.isNoneT(tab[0][6])
            self.uwagi = self.isNoneT(tab[0][7])

    def wpisz_luki(self, tab):
        if len(tab) > 0:
            self.luki = tab[0][2]

    def wpisz_przest_vol(self, tab):
        if len(tab) > 0:
            for t in tab:
                if t[6] == 'PRZES':
                    self.przest_vol += self.isNone(t[5])
                else:
                    self.plaz_vol += self.isNone(t[5])

    def wpisz_dzkat(self, tab):
        if not isinstance(tab, type([])):
            return
        self.ile_dzkat = tab[0][0]

    def wczytaj_dane(self, tab):
        """Metoda wczytuje podane przez użytkownika dane w postaci tablicy z
        bazy danych z metody pobierz do zab, i wczytuje wartości do zmiennych.
        """
        self.wpisz_pod_nal(tab[0])
        self.wpisz_ist_zab(tab[1])
        self.wpisz_gat_gl(tab[2])
        self.wpisz_przest(tab[3])
        self.wpisz_szczeg_wydz(tab[4])
        self.wpisz_przest_vol(tab[5])
        self.wpisz_luki(tab[6])
        self.wpisz_dzkat(tab[7])

        return True

    def dopisz_zabiegi(self, alter=True):  #noqa
        '''Metoda dopisuje lub poprawia juz wpisane zbiegi do bazy na podstawie
        wygenerowanych automatycznie

        alter - zmienna odpowiedzialna za dodawanie nowych rekordow w bazie,
        jezeli False w bazie zostaną zmodyfikowane tylko i wyłącznie powierzch.
        istniejacych zabiegów.
        '''

        # dopisz do bazy wygenerowana rebnie o ile nie jest juz w niej wpisana
        # jakaś inna
        if self.gen_reb != '' and len(self.cue) == 0 and alter:
            self.max_cue += 1
            wpis = self.baza.wpisz_tab([
                "insert into F_AROD_CUE "
                "(ARODES_INT_NUM, "
                "MEASURE_CD, "
                "URGENCY, "
                "CUTTING_AREA, "
                "LARGE_TIMBER_PERC, "
                "CUE_RANK_ORDER, "
                "SITE_NR, "
                "PROC_AREA) "
                "values(?, ?, 'N', ?, ?, ?, 0, 100);",
                (
                    self.aid,
                    self.gen_reb,
                    self.pow_wydz,
                    self.gen_proc_reb,
                    self.max_cue
                )
            ])

            # jeżeli nie udalo sie wpisac rebnie do baza dodaj to do uwag i
            # poinformuj o tym uzytkownika w raporcie
            if not wpis:
                self.uw_baza.append(
                    'Nie udało się wpisać wygenerowanej rębni do bazy [' +
                    self.gen_reb+']'
                )
            else:
                self.dodano += 1

        # uaktualnij w bazie powierzchnie wpisanej rebni o ile jest taka sama
        # jak wygenerowana w tym przebiegu
        if self.reb == self.gen_reb and self.pow_reb != self.gen_pow_reb and \
                self.reb != '':
            sql = 'update f_arod_cue set cutting_area=' + str(self.pow_wydz) +\
                ' where arodes_int_num=' + str(self.aid) + " and measure_cd='"\
                + self.reb + "';"
            wpis = self.baza.wpisz(sql)
            if not wpis:
                self.uw_baza.append('Nie udało się zmodyfikować pow. rębni '
                                    'na ['+str(self.gen_pow_reb)+']')
            else:
                self.zmodyfikowano += 1

        for it in self.zabiegi:
            # jezeli taki zabieg jest juz w bazie zmien powierzchnie na zgodna
            # z wygenerowana w tym przebiegu.
            if it[0] in self.cue:
                if it[1] != self.cue[it[0]]:
                    wpis = self.baza.wpisz_tab([
                        "UPDATE F_AROD_CUE SET CUTTING_AREA = ? "
                        "WHERE ARODES_INT_NUM = ? AND "
                        "MEASURE_CD = ?;",
                        (it[1], self.aid, it[0])
                    ])
                    if not wpis:
                        self.uw_baza.append(
                            'Nie udało sie poprawić w bazie zabiegu: ' +
                            it[0]+' '+str(it[1])
                        )
                    else:
                        self.zmodyfikowano += 1
            else:
                # jezeli jest juz wpisany jakis inny zabieg (ciecie) - pomijamy
                if it[0] in ['TP', 'TW', 'CP-P', 'CP', 'CW'] and \
                        len([x for x in self.cue.keys()
                             if x in ['TP', 'TW', 'CP-P', 'CP', 'CW']]) > 0:
                    continue

                if it[0] in ['TP', 'TW', 'CP-P'] and alter:
                    self.max_cue += 1
                    ciecie = self.oblicz_ciecie()
                    wpis = self.baza.wpisz_tab(
                        [
                            "insert into F_AROD_CUE ("
                            "ARODES_INT_NUM, "
                            "MEASURE_CD, "
                            "URGENCY, "
                            "CUTTING_AREA, "
                            "LARGE_TIMBER_PERC, "
                            "CUE_RANK_ORDER, "
                            "SITE_NR, "
                            "PROC_AREA, "
                            "LARGE_TIMBER_VALUE"
                            ") values(?, ?, 'N', ?, ?, ?, 0, ?, ?);",
                            (
                                self.aid,
                                it[0],
                                it[1],
                                ciecie[0],
                                self.max_cue,
                                round((it[1]*100)/self.pow_wydz, 0),
                                ciecie[1]
                            )
                        ]
                    )

                    if not wpis:
                        self.uw_baza.append(
                            'Nie udało sie wpisać do bazy zabiegu: ' +
                            it[0]+' '+str(it[1])
                        )
                    else:
                        self.dodano += 1

                elif it[0] not in \
                        ['TP', 'TW', 'CP-P', 'PŁAZ', 'PRZEST'] and alter:
                    self.max_cue += 1
                    wpis = self.baza.wpisz_tab([
                        "insert into F_AROD_CUE ("
                        "ARODES_INT_NUM, "
                        "MEASURE_CD, "
                        "URGENCY, "
                        "CUTTING_AREA, "
                        "CUE_RANK_ORDER, "
                        "SITE_NR, "
                        "PROC_AREA"
                        ") values(?, ?, 'N', ?, ?, 0, ?);",
                        (
                            self.aid,
                            it[0],
                            it[1],
                            self.max_cue,
                            round((it[1]*100)/self.pow_wydz, 0)
                        )
                    ])
                    if not wpis:
                        self.uw_baza.append(
                            'Nie udało sie wpisać do bazy zabiegu: ' +
                            it[0]+' '+str(it[1])
                        )
                    else:
                        self.dodano += 1

                if it[0] in ['PŁAZ', 'PRZEST'] and alter:
                    ciecie = 100
                    grub = 0
                    if it[0] == 'PRZEST':
                        grub = self.przest_vol
                    else:
                        grub = self.plaz_vol

                    self.max_cue += 1
                    wpis = self.baza.wpisz_tab([
                        "insert into F_AROD_CUE ("
                        "ARODES_INT_NUM, "
                        "MEASURE_CD, "
                        "URGENCY, "
                        "CUTTING_AREA, "
                        "LARGE_TIMBER_PERC, "
                        "CUE_RANK_ORDER, "
                        "SITE_NR, "
                        "PROC_AREA, "
                        "LARGE_TIMBER_VALUE"
                        ") values(?, ?, 'N', ?, 100, ?, 0, ?, ?);",
                        (
                            self.aid,
                            it[0],
                            it[1],
                            self.max_cue,
                            round((it[1]*100)/self.pow_wydz, 0),
                            round(grub, 0)
                        )
                    ])
                    if not wpis:
                        self.uw_baza.append(
                            'Nie udało sie wpisać do bazy zabiegu: ' +
                            it[0]+' '+str(it[1])
                        )
                    else:
                        self.dodano += 1

    def zmodyfikuj_zabiegi(self):
        ''' Metoda modyfikuj wpisane zabiegi tylko poprzez podmiane powierzchni
        na podstawie procentow podanych w glownym zabiegu. Jeśli czegoś takiego
        nie ma, sprawdza czy pow nie jest wieksza od pow wydzielenia'''

        reb_cz_tab = [z for z in self.cue.keys() if z in self.rebnieSpis[3:-1]]
        reb_cz = False
        if len(reb_cz_tab) > 0:
            reb_cz = reb_cz_tab[0]

        for zab in self.cue.keys():
            # olewamy poprawę zabiegów w wydzieleniach z tp,
            # njaprawdopodobniej sa to odnowienia luk i maja dobre pow
            if len([x for x in ['TP', 'TW'] if x in self.cue.keys()]) > 0 and\
                    zab not in ['TP', 'TW']:
                continue

            if zab in ['TP', 'TW', 'CP-P', 'PRZES', 'PRZEST'] + \
                    self.rebnieSpis or self.cue[zab] > self.pow_wydz:
                wpis = self.baza.wpisz_tab([
                    "UPDATE F_AROD_CUE SET CUTTING_AREA = ? "
                    "WHERE ARODES_INT_NUM = ? AND "
                    "MEASURE_CD = ?;",
                    (self.pow_wydz, self.aid, zab)
                ])
                if not wpis:
                    self.uw_baza.append(
                        'Nie udało sie poprawić pow. zabiegu: ' + zab
                    )
                else:
                    self.zmodyfikowano += 1

            else:
                # jezeli mamy procent rebni, to mnozymy akt pow_wydz i
                # wpisujemy do bazy
                if self.proc_reb > 0:
                    # inne rebnie cześciowe
                    odn_cz = 0
                    if reb_cz:
                        np_sum = self.nal + self.podr
                        if np_sum > 0.1:
                            odn_cz = np_sum - 0.1

                    wpis = self.baza.wpisz_tab([
                        "UPDATE F_AROD_CUE SET CUTTING_AREA = ? "
                        "WHERE ARODES_INT_NUM = ? AND "
                        "MEASURE_CD = ?;",
                        (
                            round((self.proc_reb/100)*self.pow_wydz*(1-odn_cz),
                                  4),
                            self.aid,
                            zab
                         )
                    ])
                    if not wpis:
                        self.uw_baza.append(
                            'Nie udało sie poprawić w bazie zabiegu: ' + zab
                        )
                    else:
                        self.zmodyfikowano += 1


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
