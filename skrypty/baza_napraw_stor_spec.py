import os

from qgis.core import QgsProject
from .baza_wrapper import Baza, znajdz_baze_do_wydz

# docelowa kolejność warstw w wydzieleniu (STOREY_RANK_ORDER), od góry;
# zgodna z kontrolami: OT (DRZEW/IP = 1) i SULMN ID82 (na HAL/ZRĘB jako
# pierwsze tylko NAL/PODR/PODRII/PODSZ - stąd PRZES za PODSZ) oraz z
# kolejnością w bazach z TPU. Słownik F_STOREY_DIC.STOREY_NR stawia IP/IIP
# za PRZES - nie używać. Kody spoza listy na końcu.
KOLEJNOSC_PIETER = ['DRZEW', 'IP', 'IIP', 'PODRII', 'PODR', 'NAL', 'PODS',
                    'PODSZ', 'PRZES', 'ZADRZEW', 'PLANT', 'ZAKRZEW', 'SAMOS']

# kody udziału w kolejności sortowania gatunków (10 = 100% pierwsze)
KOLEJNOSC_UDZIALOW = [str(x) for x in range(10, 0, -1)] + ['MJS', 'PJD']


class NaprawFStorSpec:
    def __init__(self):
        self.baza = Baza('')
        self.sl = {}
        self.uwagi = {}           # arodes_int_num -> [opis błędu]
        self.nieznane_udzialy = []  # wiersze z PART_CD spoza słownika
        self.wpisanych = 0
        self.wydz_kol_pieter = 0  # wydzielenia z poprawioną kolejnością pięter
        self.usuniete_puste = []  # wiersze z SPECIES_CD = NULL (usunięte)
        self.inne_puste = []      # wiersze z pustym ARODES_INT_NUM/STOREY_CD

        # warstwy do poprawy sortowania
        # (ZADRZEW celowo pominięte - bez sortowania)
        self.lwar = ['DRZEW', 'PODR', 'PODRII', 'NAL', 'PODS', 'PODSZ', 'IP',
                     'IIP', 'PRZES', ]

    def pobierz_z_bazy(self):
        '''Pobiera z bazy tabele f_storey_species. Na wstępie kopia bazy
        i usunięcie pustych wierszy (SPECIES_CD = NULL) - przez nie skrypt
        się wywracał.'''
        if not self.baza.polacz():
            return False

        # kopia przed jakąkolwiek zmianą (także przed usunięciem pustych)
        self.baza.utworz_kopie(wpis='napraw_FStoreySpecies')
        if not self.usun_puste_wiersze():
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
        if self.raw is False:
            return False

        # pozostałe puste (bez wydzielenia albo piętra) - tylko do raportu,
        # z sortowania wyłączone
        self.inne_puste = [r for r in self.raw
                           if r[1] is None or r[2] is None]
        self.raw = [r for r in self.raw
                    if r[1] is not None and r[2] is not None]
        return True

    def usun_puste_wiersze(self):
        '''Usuwa z F_STOREY_SPECIES wiersze z SPECIES_CD = NULL, zapamiętując
        je do raportu.'''
        sql = '''select spec_stor_int_num, arodes_int_num, storey_cd,
                    species_rank_order, species_cd, part_cd, species_age,
                    volume
                from f_storey_species where species_cd is null;'''
        puste = self.baza.pobierz(sql)
        if puste is False:
            return False
        if not puste:
            return True
        if not self.baza.wpisz(
                'delete from f_storey_species where species_cd is null;'):
            return False
        self.usuniete_puste = puste
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

    def _uwaga(self, aid, opis):
        self.uwagi.setdefault(aid, []).append(opis)

    def _zapisz_kolejnosc(self, sql, wiersze):
        """Numeruje wiersze od 1 w dwóch przebiegach (najpierw +100 - bez
        chwilowych dubli numeru) w jednej transakcji. wiersze: [krotka
        klucza do where]. Zwraca None albo treść błędu (po wycofaniu)."""
        cur, con = self.baza.cur, self.baza.con
        try:
            for przes in (100, 1):
                for i, klucz in enumerate(wiersze):
                    cur.execute(sql, (i + przes,) + tuple(klucz))
            con.commit()
        except Exception as e:
            try:
                con.rollback()
            except Exception:
                pass
            return '%s: %s' % (type(e).__name__, e)
        return None

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
                except Exception as e:
                    self._uwaga(intnum, 'błąd sortowania gatunków - %s: %s'
                                % (type(e).__name__, e))

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

        # przestoje: bez udziału - masa, potem wiek, potem gatunek
        if pietro == 'PRZES':
            t2 = sorted(t1, key=lambda x: x[6], reverse=True)  # sort po wieku
            return sorted(t2, key=lambda x: x[7], reverse=True)  # po vol

        t2 = sorted(t1, key=lambda x: x[7], reverse=True)  # sort po vol
        t3 = sorted(t2, key=lambda x: x[6], reverse=True)  # sort po wieku
        # sort po udziale; kod spoza słownika na końcu + raport (pusty
        # udział też na końcu, bez raportu)
        for x in t3:
            if x[5] and x[5] not in KOLEJNOSC_UDZIALOW:
                self.nieznane_udzialy.append(x)
        return sorted(t3, key=lambda x: (
            KOLEJNOSC_UDZIALOW.index(x[5]) if x[5] in KOLEJNOSC_UDZIALOW
            else len(KOLEJNOSC_UDZIALOW)))

    def dopisz_poprawki(self):
        # kopia bazy powstaje już w pobierz_z_bazy
        for key, val in self.sl.items():
            self.d_wydz(key)

        self.popraw_kolejnosc_pieter()

    def popraw_kolejnosc_pieter(self):
        '''Ustawia STOREY_RANK_ORDER w F_AROD_STOREY wg KOLEJNOSC_PIETER,
        numeracja w wydzieleniu od 1 bez dziur. Piętra spoza listy na
        końcu, w dotychczasowej kolejności.'''
        wiersze = self.baza.pobierz(
            'select ARODES_INT_NUM, STOREY_CD, STOREY_RANK_ORDER '
            'from F_AROD_STOREY;')
        if not wiersze:
            return
        pietra = {}
        for aid, cd, rank in wiersze:
            pietra.setdefault(aid, []).append((cd, rank))

        def poz(cd):
            return (KOLEJNOSC_PIETER.index(cd) if cd in KOLEJNOSC_PIETER
                    else len(KOLEJNOSC_PIETER))

        sql = ('update F_AROD_STOREY set STOREY_RANK_ORDER = ? '
               'where ARODES_INT_NUM = ? and STOREY_CD = ?;')
        for aid, lista in pietra.items():
            nowa = sorted(lista, key=lambda x: (
                poz(x[0]), 999 if x[1] is None else x[1]))
            if [x[1] for x in nowa] == list(range(1, len(nowa) + 1)):
                continue
            blad = self._zapisz_kolejnosc(sql, [(aid, cd) for cd, _ in nowa])
            if blad is None:
                self.wydz_kol_pieter += 1
            else:
                self._uwaga(aid, 'kolejność pięter niezapisana - ' + blad)

    def _adres(self, sl_int, aid):
        if aid is None:
            return '(brak ARODES_INT_NUM)'
        return sl_int.get(aid, f'ARODES_INT_NUM={aid}')

    def _opis_wiersza(self, sl_int, r):
        # r = spec_stor_int_num, arodes_int_num, storey_cd, rank, species_cd,
        #     part_cd, species_age, volume
        return (f'{self._adres(sl_int, r[1])}  piętro: {r[2]}  '
                f'gatunek: {r[4]}  udział: {r[5]}  wiek: {r[6]}  '
                f'masa: {r[7]}  (SPEC_STOR_INT_NUM={r[0]})')

    def raport(self):
        uw = sorted(x for x in self.uwagi if x is not None)
        wyps = '------[ RAPORT ]--------\n\n'
        wyps += 'Wpisano poprawek do bazy: '+str(self.wpisanych) + '\n'
        wyps += 'Poprawiono kolejność pięter w wydzieleniach: ' + \
            str(self.wydz_kol_pieter) + '\n'
        wyps += 'Usunięto pustych wierszy (SPECIES_CD = NULL): ' + \
            str(len(self.usuniete_puste)) + '\n\n'

        # adresy wszystkich wierszy F_ARODES (nie tylko WYDZIEL) - żeby
        # raport nie wywracał się na numerze spoza wydzieleń
        sl_int = {}
        wiersze = self.baza.pobierz(
            'select ARODES_INT_NUM, ADRESS_FOREST from F_ARODES;')
        if wiersze:
            sl_int = {a: adr for a, adr in wiersze}

        if self.usuniete_puste:
            wyps += 'USUNIĘTE PUSTE WIERSZE (brak gatunku):\n'
            wyps += '\n'.join(self._opis_wiersza(sl_int, r)
                              for r in self.usuniete_puste) + '\n\n'

        if self.inne_puste:
            wyps += ('POZOSTAŁE PUSTE WIERSZE - brak wydzielenia albo '
                     'piętra (NIE usunięte, pominięte przy sortowaniu, '
                     'popraw ręcznie):\n')
            wyps += '\n'.join(self._opis_wiersza(sl_int, r)
                              for r in self.inne_puste) + '\n\n'

        if self.nieznane_udzialy:
            wyps += ('UDZIAŁ SPOZA SŁOWNIKA (gatunek ustawiony na końcu '
                     'warstwy):\n')
            wyps += '\n'.join(self._opis_wiersza(sl_int, r)
                              for r in self.nieznane_udzialy) + '\n\n'

        if len(uw) > 0:
            wyps += 'Znaleziono błędów krytycznych: ' + str(len(uw)) + '\n'
            wyps += ('(Należy sprawdzić poniższe wydzielenia - zmiany w nich '
                     'wycofane)\n\n')
            for x in uw:
                wyps += self._adres(sl_int, x) + '\n'
                wyps += ''.join('    ' + o + '\n' for o in self.uwagi[x])

        wyps += '\n\n\n----------[ KONIEC ]----------------'
        kat = os.path.dirname(self.baza.baza)
        open(os.path.join(
            kat,
            'raport_naprawa_FStoreySpecies_'+str(self.baza.czas)+'.txt'),
            'w', encoding='utf-8').write(wyps)

    def d_wydz(self, wydz):
        for key, val in self.sl[wydz].items():
            if key not in self.lwar:
                continue
            if len(self.sl[wydz][key]) == 0:
                continue

            if key in self.lwar and key+'_s' not in self.sl[wydz]:
                self._uwaga(wydz, '%s: brak posortowanej listy gatunków'
                            % key)
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
                self._uwaga(wydz, '%s: różna liczba gatunków przed i po '
                            'sortowaniu' % key)
                continue

            # jezeli tu dotarlismy to mozemy zmienic baze - cała warstwa
            # w jednej transakcji (błąd -> wycofanie, bez numerów 100+)
            blad = self._zapisz_kolejnosc(
                'update f_storey_species set species_rank_order = ? '
                'where spec_stor_int_num = ?;',
                [(it[0],) for it in self.sl[wydz][key+'_s']])
            if blad is None:
                self.wpisanych += len(self.sl[wydz][key+'_s'])
            else:
                self._uwaga(wydz, '%s: kolejność gatunków niezapisana - %s'
                            % (key, blad))


class WrapNaprawFStorSpec(NaprawFStorSpec):
    def __init__(self, iface):
        NaprawFStorSpec.__init__(self)
        self.iface = iface

    def pokaz_wyniki(self):
        if len(self.uwagi) == 0:
            self.iface.messageBar().pushSuccess(
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
        '''Ustala sciezke do bazy, w ktorej ma byc przeprowadzone sprawdzanie
        tabeli f_storey_species. Jeżeli w TOC jest dokładnie jedna warstwa
        WYDZ, baza jest szukana automatycznie katalog wyżej (okno wyboru
        tylko gdy nie ma tam dokładnie jednej bazy). W przeciwnym razie
        użytkownik wskazuje bazę - o warstwę nie pytamy, bo służy ona tylko
        do odnalezienia bazy.
        '''
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        wydz_kandydaci = [x for x in lyrs if x.name().upper() == 'WYDZ']

        if len(wydz_kandydaci) == 1:
            baza_sc = znajdz_baze_do_wydz(
                self.iface, wydz_kandydaci[0], poz=1)
        else:
            # przy kilku warstwach WYDZ okno startuje w katalogu pierwszej
            wydz = wydz_kandydaci[0] if wydz_kandydaci else None
            baza_sc = znajdz_baze_do_wydz(self.iface, wydz, poz=1, wskaz=True)
        if baza_sc is False:
            return False

        self.kat = os.path.dirname(baza_sc)
        self.baza.baza = baza_sc
        return True
