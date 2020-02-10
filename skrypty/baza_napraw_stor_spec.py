import os

from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDialog
from .baza_wrapper import Baza


class NaprawFStorSpec:
    def __init__(self):
        self.baza = Baza('')
        self.sl = {}
        self.uwagi = []
        self.wpisanych = 0

        # warstwy do poprawy sortowania
        self.lwar = ['DRZEW', 'PODR', 'DODRII', 'NAL', 'PODSZ', 'IP', 'IIP', ]

    def pobierz_z_bazy(self):
        '''Pobiera z bazy tabele f_storey_species '''
        if not self.baza.polacz():
            return False

        sql = '''select
                    spec_stor_int_num,
                    arodes_int_num,
                    storey_cd,
                    species_rank_order,
                    species_cd,
                    part_cd,
                    species_age,
                    volume
                from f_storey_species
                order by arodes_int_num asc, storey_cd asc,
                species_rank_order asc;
        '''
        self.raw = self.baza.pobierz(sql)
        return True

    def zbuduj_strukture(self):
        '''Zestawia ją w strukture do dalszych obliczen:
            sl={arodes_int_num:{
            'raw': [[row], ... ],

            # sortowane po rank_ord z bazy
            'drzew': [[row], ],

            # sortowane po kolejności wg: 1)part_cd, 2)wiek, 3) vol 4) gat
            'drzew_s': [[row nie zmieniony ], ...],
            ...
            }
            '''
        for row in self.raw:
            # stworz poczatkowa strukture dla slownika
            if row[1] not in self.sl:
                self.sl[row[1]] = {}
                # self.sl[row[1]]['raw'] = []
                for war in self.lwar:
                    self.sl[row[1]][war] = []

            # self.sl[row[1]]['raw'].append(row)  # tabela raw
            # tabela z sortowaniem z bazy, wybieramy tylko istotne z self.lwar
            if row[2] in self.lwar:
                self.sl[row[1]][row[2]].append(row)

    def popraw(self):
        '''Sortuje na nowo poszczegolne tablice w slowniku, o ile w listach
        jest przynajmniej 1 rekord i tworzy nowe tabele z dodatkiem
        '_s'. nowe tabele mają tylko nowe sortowanie, dane nie są
        zmieniane
        '''
        wydz_int = list(self.sl.keys())
        for intnum in wydz_int:
            if sum([len(x) for k, x in self.sl[intnum].items()
                    if k != 'raw']) > 0:
                try:
                    self.p_pietro(intnum)
                except Exception:
                    self.uwagi.append(intnum)

    def p_pietro(self, key_wydz):
        '''obliczenia dla pietra'''
        klucze = list(self.sl[key_wydz].keys())
        # klucze.remove('raw')
        for key in klucze:
            if len(self.sl[key_wydz][key]) > 0:
                self.sl[key_wydz][key+'_s'] = self.p_tabela(key_wydz, key)

    def p_tabela(self, wydz, pietro):
        '''sortowanie dla tabeli, czyszczenie None'''
        tab = []
        val = self.sl[wydz][pietro]
        for x in val:
            tab.append(list(x[:5]) +
                       ['' if x[5] is None else x[5]] +
                       [0 if x[6] is None else x[6]] +
                       [0 if x[7] is None else x[7]]
                       )

        t1 = sorted(tab, key=lambda x: x[4])  # sort po gat
        t2 = sorted(t1, key=lambda x: x[7], reverse=True)  # sort po vol
        t3 = sorted(t2, key=lambda x: x[6], reverse=True)  # sort po wieku
        # sort po udziale
        t4 = sorted(
            t3,
            key=lambda x: (
                10 - int(x[5]) if x[5].isdigit() else (
                    11 if x[5] == 'MJS' else
                    12 if x[5] == 'PJD' else 13)
            ))

        return t4

    def dopisz_poprawki(self):
        self.baza.utworz_kopie(wpis='napraw_FStoreySpecies')

        for key, val in self.sl.items():
            self.d_wydz(key)

    def raport(self):
        uw = sorted(list(set(self.uwagi)))
        wyps = '------[ RAPORT ]--------\n\n'
        wyps += 'Wpisano poprawek do bazy: '+str(self.wpisanych) + '\n\n'

        if len(uw) > 0:
            sl_wydz = self.baza.pobierz_wydzielenia()
            sl_int = {v: k for k, v in sl_wydz.items()}

            wyps += 'Znaleziono błędów krytycznych: ' + str(len(uw)) + '\n'
            wyps += '(Należy sprawdzić poniższe wydzielenia)\n\n'
            wyps += '\n'.join([sl_int[int(x)] for x in uw])

        wyps += '\n\n\n----------[ KONIEC ]----------------'
        kat = os.path.dirname(self.baza.baza)
        open(os.path.join(
            kat,
            'raport_naprawa_FStoreySpecies_'+str(self.baza.czas)+'.txt'),
            'w').write(wyps)

    def d_wydz(self, wydz):
        for key, val in self.sl[wydz].items():
            if key not in self.lwar:
                continue
            if len(self.sl[wydz][key]) == 0:
                continue

            if key in self.lwar and key+'_s' not in self.sl[wydz]:
                self.uwagi.append(wydz)
                continue

            # sprawdz czy sortowanie zmienilo liste z bazy
            # x_org = [x[0] for x in val]
            y_org = [True if y[3] == i+1 else False for i, y in
                     enumerate(self.sl[wydz][key+'_s'])]

            if False not in y_org:
                continue

            # czy listy maja taka sama dlugosc, - raczej tak ale dla swietego
            # spokoju sprawdzmy
            if len(self.sl[wydz][key]) != len(self.sl[wydz][key+'_s']):
                self.uwagi.append(wydz)
                continue

            # jezeli tu dotarlismy to mozemy zmienic baze
            for i, it in enumerate(self.sl[wydz][key+'_s']):
                sql = 'update f_storey_species set ' + \
                    'species_rank_order='+str(i+100) + \
                    ' where spec_stor_int_num='+str(it[0])+';'
                wyn = self.baza.wpisz(sql)

            for i, it in enumerate(self.sl[wydz][key+'_s']):
                sql = 'update f_storey_species set ' + \
                    'species_rank_order='+str(i+1) + \
                    ' where spec_stor_int_num='+str(it[0])+';'
                wyn = self.baza.wpisz(sql)
                if not wyn:
                    self.uwagi.append(wydz)
                else:
                    self.wpisanych += 1


class WrapNaprawFStorSpec(NaprawFStorSpec):
    def __init__(self, iface):
        NaprawFStorSpec.__init__(self)
        self.iface = iface

    def pokaz_wyniki(self):
        if len(self.uwagi) == 0:
            self.iface.messageBar().pushSucces(
                'OK',
                'Brak uwag, poprawiono rekordów: '+str(self.wpisanych),
            )
        else:
            self.iface.messageBar().pushWarning(
                'BŁĘDY KRYTCZNE',
                'Poprawiono rekordów: '+str(self.wpisanych) +
                '; Znaleziono błędów krytycznych: ' +
                str(len(set(self.uwagi))) + ' '
                ' (Sprawdź plik raportu)'
            )

    def pobierz_sciezke(self):
        '''Pobiera od użytkownika sciezke do bazy, w ktorej ma byc
        przeprowadzone sprawdanie tabeli f_storey_species
        '''
        sc = QFileDialog().getOpenFileName(self.iface.mainWindow(),
                                           'Wskaż bazę TPU',
                                           '',
                                           "Access MDB (*.mdb)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.baza.baza = sc
            return True
        return False

