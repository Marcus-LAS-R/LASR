import os
import platform
from PyQt5.QtWidgets import QMessageBox
from qgis.core import Qgis

from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .baza_przetworz import Przetworz
from .pw import PasekPostepu


class KontrolaLs:
    def __init__(self, iface):
        self.iface = iface
        self.ls = False
        self.baza = False
        self.kat = ''
        self.uzytki = []
        self.wlasnosci = []
        self.wl = 'OF'

        self.puste_lid = 0  # licz feat z pustymi landid
        self.zdublowane_lid = []  # poligony ze zdublowanym landid

        # slownik ls z warstwy w postaci landid: {pola wymagane w warstwie}
        self.d_ls = {}

        self.pola_ls = [
            'LANDID', 'PARCELID', 'AU', 'SQ', 'LAND_AR', 'LAND_POW',
            'COMMUNITY', 'MUNICIP', 'COUNTY', 'DISTRICT', 'PARCELNR', 'GRP',
            'NIELES', 'ARK', 'SPRAWDZ',
        ]

    def dane_wejsciowe(self):
        # sprawdz czy użyszkodnik zaznaczył warstwę Ls z odpowiednimi polami w
        # tabeli i czy w katalogu nadrzędnym jest jedna baza taks

        try:
            self.ls = self.iface.activeLayer()
            if self.ls is None:
                self.iface.messageBar().pushMessage(
                    'BŁĄD', 'Proszę zaznaczyć warstwę Ls', Qgis.Critical
                )
                return False
        except Exception:
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Proszę zaznaczyć warstwę Ls', Qgis.Critical
            )
            return False

        pola_braki = [
            y for y in self.pola_ls
            if y not in [x.name() for x in self.ls.fields()]]
        if len(pola_braki) > 0:
            self.iface.messageBar().pushMessage(
                'BRAK WYMAGANYCH PÓL',
                'Brakuje pól we wskazanej warstwie: [' +
                ', '.join(pola_braki)+']',
                Qgis.Critical
            )
            return False

        # znajdz baze
        self.kat = os.path.dirname(
            self.ls.dataProvider().dataSourceUri().split("|")[0])

        baza_sc = znajdz_baze_do_wydz(self.iface, self.ls, 1)
        if baza_sc is False:
            return False

        self.baza = Baza(baza_sc)
        if self.baza.polacz():
            self.uzytki = self.baza.uzytki()
            self.wlasnosci = self.baza.wlasnosci()
        else:
            self.iface.messageBar().pushMessage(
                'BAZA', 'Nie udało połączyć się z: ' + baza_sc, Qgis.Warning)
            return False

        message = QMessageBox()
        message.setIcon(QMessageBox.Information)
        message.setWindowTitle('Własności')
        message.setText('Wybierz własności do analizy')
        message.addButton("OF", QMessageBox.ActionRole)
        message.addButton("OPiF", QMessageBox.ActionRole)
        wl = message.exec_()

        if wl == 0:
            self.wl = 'OF'
        else:
            self.wl = 'OP'

        self.postep = PasekPostepu(self.iface).stworz_pasek(
            'Sprawdzanie Ls-ów'
        )
        return True

    def przetworz_dane(self):
        # przetworz dane z bazy danych
        self.postep.setValue(5)
        self.p = Przetworz()
        self.p.dodaj_uzytki(self.uzytki)
        self.p.dodaj_wlasnosci(self.wlasnosci)
        self.postep.setValue(15)
        self.p.przetworz_dzialki()
        self.p.przetworz_uzytkowanie()

        # uzup = {}  # TODO:sl z uzupelnieniami do dodania z bazy
        for ft in self.ls.getFeatures():
            if ft['LANDID'] in self.d_ls:
                self.zdublowane_lid.append(ft['LANDID'])

            if self.baza.isNone(ft['LANDID']) == '':
                self.puste_lid += 1

            self.d_ls[ft['LANDID']] = {
                x: self.baza.isNone(ft[x]) for x in self.pola_ls
            }
            self.d_ls[ft['LANDID']]['id'] = ft.id()
            self.d_ls[ft['LANDID']]['feat'] = ft

    def zestawienia(self):
        self.postep.setValue(20)
        # metoda zbiorcza do wygenerowania zestawien
        self.ls_w_shp = [k for k, v in self.d_ls.items()
                         if v['AU'].upper() == 'LS']
        self.ls_w_bazie = []
        self.brakujace_ls_w_shp = []
        self.brakujace_ls_w_bazie = []
        self.pow_zerowe_baza = []
        self.rozb_pow = []

        self.zestaw_dane()

    def zestaw_dane(self):
        """Metoda zbiorcza do zestawienia wszystkich niezbednych tablic
        """
        self.zestaw_ile_ls_bazie()
        self.postep.setValue(30)
        self.zestaw_liste_brakujacych_ls_w_shp()
        self.postep.setValue(40)
        self.zestaw_liste_brakujacych_ls_w_bazie()
        self.postep.setValue(50)
        self.zestaw_liste_zerowych_ls_w_bazie()
        self.postep.setValue(60)
        self.zestaw_rozb_pow()

    def zestaw_ile_ls_bazie(self):
        if self.wl == 'OF':
            self.ls_w_bazie = len(
                [k for k in self.p.ls
                 if self.p.uzytki[k][3][4:] not in self.p.dz_op]
            ) + len(self.p.ls_podwojne)

        else:
            self.ls_w_bazie = len(self.p.ls) + len(self.p.ls_podwojne)

    def zestaw_liste_brakujacych_ls_w_shp(self):
        if self.wl == 'OF':
            self.brakujace_ls_w_shp = [
                [k, self.p.uzytki[k][2]] for k in self.p.ls
                if k not in self.ls_w_shp and
                self.p.uzytki[k][3][4:] not in self.p.dz_op
            ]
        else:
            self.brakujace_ls_w_shp = [
                [k, self.p.uzytki[k][2]] for k in self.p.ls
                if k not in self.ls_w_shp
            ]

    def zestaw_liste_brakujacych_ls_w_bazie(self):
        if self.wl == 'OF':
            self.brakujace_ls_w_bazie = [
                x for x in self.ls_w_shp
                if x not in self.p.ls and
                self.d_ls[x]['PARCELID'][4:] not in self.p.dz_op
            ]

        else:
            self.brakujace_ls_w_bazie = [
                x for x in self.ls_w_shp if x not in self.p.ls]

    def zestaw_liste_zerowych_ls_w_bazie(self):
        if self.wl == 'OF':
            # zestaw liste landid z powierzchniami zerowymi w bazie
            self.pow_zerowe_baza = [k for k in self.p.ls
                                    if self.p.uzytki[k][2] < 0.0001 and
                                    self.p.uzytki[k][3][4:]
                                    not in self.p.dz_op]
        else:
            # zestaw liste landid z powierzchniami zerowymi w bazie
            self.pow_zerowe_baza = [k for k in self.p.ls
                                    if self.p.uzytki[k][2] < 0.0001]

    def zestaw_rozb_pow(self):
        for k, v in self.d_ls.items():
            if k not in self.p.uzytki:
                pass
            elif abs(v['feat'].geometry().area()/10000 -
                     self.p.uzytki[k][2]) > 0.15:
                self.rozb_pow.append([
                    k,
                    round(v['feat'].geometry().area()/10000, 4),
                    round(self.p.uzytki[k][2], 4),
                    round(abs(v['feat'].geometry().area()/10000 -
                              self.p.uzytki[k][2]), 4),
                ])

        self.rozb_pow = sorted(
            self.rozb_pow, key=lambda x: x[3], reverse=True
        )

    def generuj_raport(self):  # noqa
        """Metoda generuj raport zapisany w zmiennej self.wypis"""
        self.postep.setValue(80)
        self.wypis = '-----[ RAPORT ]------\n\n'
        self.wypis += 'Ls w shp: ' + str(len(self.ls_w_shp)) + '\n'
        self.wypis += 'Ls w bazie: ' + str(self.ls_w_bazie) + '\n\n'

        if len(self.p.ls_podwojne) > 0:
            self.wypis += '-->Dzkat ze zdublowanymi Ls w bazie: ' + \
                str(len(self.p.ls_podwojne)) + '\n'

        if len(self.pow_zerowe_baza) > 0:
            self.wypis += '-->Ls z zerową pow w bazie: ' + \
                str(len(self.pow_zerowe_baza)) + '\n'

        if self.puste_lid > 0:
            self.wypis += '\n-->Poligony z nieuzupełnionym LANDID: ' + \
                str(self.puste_lid) + '\n'

        if len(self.zdublowane_lid) > 0:
            self.wypis += '-->Poligony z powtórzonym LANDID: ' + \
                str(len(self.zdublowane_lid)) + '\n'

        self.wypis += '\nBrakujących Ls-ów w [w shp]: ' + \
            str(len(self.brakujace_ls_w_shp)) + '\n'

        self.wypis += 'Brakujących Ls-ów [w bazie]: ' + \
            str(len(self.brakujace_ls_w_bazie)) + '\n\n'

        self.wypis == '\n\n'

        if len(self.zdublowane_lid) > 0:
            self.wypis += '---NIEPOŁĄCZONE LANDID [SHP]----------\n'
            self.wypis += 'Niepołączone LANDID: ' + \
                str(len(self.zdublowane_lid)) + '\n\n'
            sort_temp = sorted(self.zdublowane_lid)
            self.wypis += '\n'.join(sort_temp)
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.p.ls_podwojne) > 0:
            self.wypis += '---POWÓJNE LS [BAZA]----------\n'
            self.wypis += 'Podwójne Ls-y: ' + \
                str(len(self.p.ls_podwojne)) + '\n\n'
            sort_temp = sorted(self.p.ls_podwojne)
            self.wypis += '\n'.join(sort_temp)
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.brakujace_ls_w_shp) > 0:
            self.wypis += '---BRAKUJĄCE LSy [W SHP]----------\n'
            self.wypis += 'Brakujących Ls-ów: ' + \
                str(len(self.brakujace_ls_w_shp)) + '\n\n'
            sort_temp = sorted(self.brakujace_ls_w_shp, key=lambda x: x[0])
            self.wypis += '\n'.join([
                '\t'.join([x[0], str(x[1])]) for x in
                sorted(sort_temp, key=lambda x: 0 if 'Ls' in x[0] else 1)
            ])
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.brakujace_ls_w_bazie) > 0:
            self.wypis += '---BRAKUJĄCE LSy [W BAZIE]--------\n'
            self.wypis += 'Brakujących Ls-ów: ' + \
                str(len(self.brakujace_ls_w_bazie)) + '\n\n'
            # sort_temp = sorted(self.brakujace_ls_w_bazie, key=lambda x: x[0])
            self.wypis += '\n'.join([
                x for x in self.brakujace_ls_w_bazie
            ])
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.pow_zerowe_baza) > 0:
            self.wypis += '---LSy z ZEROWĄ POW---------------\n'
            self.wypis += 'Ls z zerową pow w bazie: ' + \
                str(len(self.pow_zerowe_baza)) + '\n\n'
            self.wypis += '\n'.join(self.pow_zerowe_baza)
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.rozb_pow) > 0:
            self.wypis += '---LS ZE ZNACZNĄ RÓŻNICĄ POW.-----\n'
            self.wypis += 'Ls z dużą rozbieżnością powierzchni: ' + \
                str(len(self.rozb_pow)) + '\n\n'
            self.wypis += 'adr_adm\tpow_graf\tpow_rej\troznica\n'
            try:
                self.wypis += '\n'.join(
                    ["\t".join(map(str, x)) for x in self.rozb_pow])
            except Exception:  # nopep8
                self.wypis += 'Coś poszło nie tak jak powinno!'
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        self.wypis += '\n-----[ KONIEC RAPORTU ]------'

        self.postep.setValue(90)
        self.rap_sc = os.path.join(
            self.kat, '..', "ls_kontrola_"+self.baza.czas+".txt")

        plik = open(self.rap_sc, 'w', encoding='cp1250')
        plik.write(self.wypis)
        plik.close()

        self.iface.messageBar().clearWidgets()
        message = QMessageBox()
        message.setIcon(QMessageBox.Information)
        message.setWindowTitle('Raport')
        message.setText('Pokazać raport ze sprawdzania Ls?')
        message.addButton("Nie", QMessageBox.ActionRole)
        message.addButton("Tak", QMessageBox.ActionRole)
        pok_rap = message.exec_()

        if pok_rap == 1:
            if platform.system()[:3] == 'Win':
                os.startfile(
                    os.path.join(self.kat, '..',
                                 'ls_kontrola_'+self.baza.czas+'.txt'))
            else:
                import subprocess
                subprocess.call(
                    ['kate',
                     os.path.join(self.kat, '..',
                                  'ls_kontrola_'+self.baza.czas+'.txt')])
