from typing import Union


class Wpisz:
    def modyfikuj_zabiegi(self, alter='') -> None:
        """ Metoda dopisuje, badz uaktualnia zabiegi w bazie na podstawie
        wygenerowanych.

        Dostepne opcje:
            alter='' - aktualizuje wydzielenia o wygenerowane zabiegi, jeżli
                jakis zabieg jest juz wpisany i jest zgodny z wygenerowanym ale
                ma rózną powierzchnię albo co innego to zostanie zakutalizowany
            alter='alter' - tylko korekta powierzchni zabiegów JUŻ wpisanych
                do bazy (rębnia: % rębni x pow. wydzielenia). Nie dopisuje
                zabiegów i nie zmienia uwag w f_subarea - brakujące zabiegi
                trafiają wyłącznie do raportu.
        """
        if alter != '':
            if self._zmodyfikuj_pow_rebni() is False:
                self.uw_raport.append(
                    'Nie udało się zmodyfikować powierzchni rębni')
            self._popraw_pow_zabiegow()
            return

        # dopisz rebnie
        status, val = self._dopisz_nowa_rebnie()
        if not status:
            self.uw_raport.append(val)

        # metoda sama ogarnia czy zmienic powierzchnie czy nie
        self._dopisz_zabiegi()
        # zapisz uwagi niezależnie od tego czy jakiś zabieg był dopisywany
        # (wygeneruj_uwagi_do_dopisania mogło zmienić self.uwagi bez zapisu)
        self.uzupelnij_uwagi()

    def _dopisz_nowa_rebnie(self) -> Union[bool, str]:
        """Metoda dopisuje do bazy nowe rebnie, w bazie dla podanego wydz
        nie powinny być dopisane żadne zabiegi
        """
        if self.gen_reb in ['', False, None]:
            return True, ''  # Nie błąd tylko nie ma czego wypisać
        if self.max_cue != 0:
            return False,  'Rębnia powinna być dopisana jako pierwsza...'
        self.max_cue += 1  # zwiększ indeks zabiegu o 1
        sql = '''insert into f_arod_cue (
            ARODES_INT_NUM, MEASURE_CD,        URGENCY,
            CUTTING_AREA,   LARGE_TIMBER_PERC, CUE_RANK_ORDER,
            SITE_NR,        PROC_AREA)
            values(?, ?, 'N', ?, ?, ?, 0, 100);'''

        wpis = self.baza.wpisz_tab([
            sql, (self.aid,
                  self.gen_reb,
                  self.pow_wydz,
                  self.gen_proc_reb,
                  self.max_cue,
                  )
        ])
        if wpis:
            self.zmodyfikowano += 1
            return True, 'OK'
        return False, 'Nie udało się dopisać cięcia do bazy'

    def _zmodyfikuj_pow_rebni(self) -> Union[bool, None]:
        """Koryguje powierzchnię rębni wpisanej do bazy do % rębni x pow.
        wydzielenia (niezależnie od tego, jaką rębnię wygenerowałby skrypt).
        Zwraca None, gdy nie ma czego poprawiać.
        """
        if self.reb == '':
            return None
        proc = self.proc_reb if self.proc_reb > 0 else 100
        if proc > 100:
            proc = 100
        pow_reb = round(self.pow_wydz * (proc/100), 4)
        if round(float(self.pow_reb), 4) == pow_reb:
            return None
        # kod w bazie może być małymi literami (SQLite rozróżnia wielkość)
        kod = next((k for k in self.cue if k.upper() == self.reb), self.reb)
        return self._zmodyfikuj_powierzchnie([kod, pow_reb])

    def _popraw_pow_zabiegow(self) -> None:
        """Tryb korekty powierzchni: poprawia powierzchnię tylko tych
        wygenerowanych zabiegów, które są już wpisane do bazy. Brakujących
        nie dopisuje - wypisuje je do raportu.
        """
        brak = []
        kody = set()
        for zab in self.zabiegi:
            if zab[0] in kody:
                continue
            kody.add(zab[0])
            if zab[0] not in self.cue:
                brak.append(f'{zab[0]} {zab[1]} ha')
                continue
            if zab[1] != self.cue[zab[0]] or \
                    self._proc_niezgodny(zab[0], zab[1]):
                if not self._zmodyfikuj_powierzchnie(zab):
                    self.uw_baza.append(
                        'Nie udało się zmodyfikować powierzchni zabiegu: '
                        f'{zab[0]} {zab[1]}')
        if brak:
            self.uw_raport.append(
                'Brak w bazie: ' + ', '.join(brak) +
                ' - nie dopisano (tryb korekty powierzchni)')

    def _dopisz_zabiegi(self):
        """Metoda dopisuje zabiegi do bazy, lub uzupełnia powierzchnię juz
        wpisanych. Jeżeli użytkownik wpisał swoją rębnie, dopisane sa zabiegi
        na podstawie wskazanego cięcia.
        """
        # kod zabiegu może być w F_AROD_CUE tylko raz na wydzielenie (klucz
        # SULMN) - powtórzony na liście wygenerowanych jest pomijany
        kody = set()
        for it in self.zabiegi:
            if it[0] in kody:
                self.uw_raport.append(
                    f'Pominięto powtórzony wygenerowany zabieg ({it[0]})')
                continue
            kody.add(it[0])
            self.max_cue += 1
            self._dopisz_zabieg(it)

    def _dopisz_zabieg(self, zab: list) -> bool:
        """Dopisuje lub modyfikuje zabieg w bazie na podstawie listy.
            zab: ['TP', pow_zab]
        """
        zab_mlode = ['TP', 'TW', 'CP-P', 'CP', 'CW']
        # zabieg już jest wpisany do bazy
        if zab[0] in self.cue:
            # inna powierzchnia albo % pow. wydz. niezgodny z powierzchnią
            if zab[1] != self.cue[zab[0]] or \
                    self._proc_niezgodny(zab[0], zab[1]):
                return self._zmodyfikuj_powierzchnie(zab)
            else:
                return True  # jest i ma taka sama powierzchnie -> ok

        # czy zabieg już wpisany w bazie, jak tak pomijam
        # zabezpiecznie na wszelki wypadek...
        zab_wpisany = [x for x in self.cue.keys()
                       if x in zab_mlode and x != zab[0]]
        if zab[0] in zab_mlode and len(zab_wpisany) > 0:
            self.uw_raport.append(
                f'Pominięto wpisanie wygenerowanego zabiegu ({zab[0]})'
                ' znaleziono inny z grupy (CP-P, CP, CW, TW, TP)'
            )
            return False

        if zab[0] in ['TP', 'TW', 'CP-P']:
            self._dopisz_ciecie_mlodych(zab)
        elif zab[0] not in ['PRZEST', 'PŁAZ']:
            self._dopisz_inne_zabiegi(zab)
        elif zab[0] in ['PRZEST', 'PŁAZ']:
            self._dopisz_przest_plaz(zab)

        self.uzupelnij_uwagi()

    def uzupelnij_uwagi(self) -> bool:
        """Modyfikuje pole subarea_info w tabeli f_subarea dla aktualnego
        wydzielenia
        """
        if self.uwagi != self.uwagi_org:
            if len(self.uwagi) > 254:
                self.uw_baza.append(
                    'Nie udało się pisać opisu do f_subarea (za długi): ' +
                    f'{self.uwagi}'
                )
                return False

            sql = f'update f_subarea set subarea_info=\'{self.uwagi}\' ' + \
                f'where arodes_int_num={self.aid};'
            res = self.baza.wpisz(sql)
            if not res:
                self.uw_baza.append(
                    f'Nie udało się pisać opisu do f_subarea: {self.uwagi}'
                )
                return False
        else:
            return True

    def _dopisz_ciecie_mlodych(self, zab: list) -> bool:
        """dopisuje CP-P, TW, TP, CW, CP do bazy do konkretnego wydzielenia
        """
        sql = '''insert into f_arod_cue (
            ARODES_INT_NUM,
            MEASURE_CD,
            URGENCY,
            CUTTING_AREA,
            LARGE_TIMBER_PERC,
            CUE_RANK_ORDER,
            SITE_NR,
            PROC_AREA,
            LARGE_TIMBER_VALUE
            ) values(?, ?, 'N', ?, ?, ?, 0, ?, ?);
            '''
        ciecie = self._oblicz_ciecie(zab[0])
        wpis = self.baza.wpisz_tab([
            sql, (self.aid,
                  zab[0],
                  zab[1],
                  ciecie[0],
                  self.max_cue,
                  round(zab[1]*100/self.pow_wydz, 0),
                  ciecie[1]
                  )
        ])
        if wpis:
            self.dodano += 1
            return True
        self.uw_baza.append(
            f'Nie udało się wpisać zabiegu: {zab[0]} {zab[1]}'
        )
        return False

    def _dopisz_inne_zabiegi(self, zab: list) -> bool:
        """Dopisz wszystkie inne zabiegi"""
        sql = '''insert into F_AROD_CUE (
                ARODES_INT_NUM,
                MEASURE_CD,
                URGENCY,
                CUTTING_AREA,
                CUE_RANK_ORDER,
                SITE_NR,
                PROC_AREA
                ) values(?, ?, 'N', ?, ?, 0, ?);'''
        wpis = self.baza.wpisz_tab([sql, (self.aid,
                                          zab[0],
                                          zab[1],
                                          self.max_cue,
                                          round((zab[1]*100)/self.pow_wydz, 0)
                                          )
                                    ])
        if wpis:
            self.dodano += 1
            return True
        self.uw_baza.append(
            f'Nie udało się wpisać zabiegu: {zab[0]} {zab[1]}'
        )
        return False

    def _dopisz_przest_plaz(self, zab):
        """Dopisz PŁAZ, PRZES do bazy"""
        grub = self.przest_vol if zab[0] == 'PRZEST' else self.plaz_vol
        sql = '''insert into F_AROD_CUE (
                    ARODES_INT_NUM,
                    MEASURE_CD,
                    URGENCY,
                    CUTTING_AREA,
                    LARGE_TIMBER_PERC,
                    CUE_RANK_ORDER,
                    SITE_NR,
                    PROC_AREA,
                    LARGE_TIMBER_VALUE
                    ) values(?, ?, 'N', ?, 100, ?, 0, ?, ?);'''
        wpis = self.baza.wpisz_tab([sql, (self.aid,
                                          zab[0],
                                          zab[1],
                                          self.max_cue,
                                          round((zab[1]*100)/self.pow_wydz, 0),
                                          round(grub, 0)
                                          )
                                    ])
        if not wpis:
            self.uw_baza.append(
                f'Nie udało się wpisać zabiegu: {zab[0]} {zab[1]}'
            )
            return False
        self.dodano += 1
        return True

    def _proc_area(self, pow_zab):
        """% powierzchni wydzielenia dla powierzchni zabiegu (None, gdy
        powierzchnia wydzielenia nieznana)."""
        if not self.pow_wydz or pow_zab is None:
            return None
        return int(round(float(pow_zab) * 100 / self.pow_wydz, 0))

    def _proc_niezgodny(self, kod, pow_zab) -> bool:
        """PROC_AREA wpisanego zabiegu nie odpowiada jego powierzchni."""
        proc = self._proc_area(pow_zab)
        if proc is None or kod not in getattr(self, 'cue_proc', {}):
            return False
        wpisany = self.cue_proc[kod]
        return wpisany is None or int(round(float(wpisany), 0)) != proc

    def _zmodyfikuj_powierzchnie(self, zab: list) -> bool:
        """Zmodyfikuj pow zabiegu lub rebni - razem z % pow. wydz.
        (PROC_AREA = pow. zabiegu / pow. wydzielenia; wcześniej zostawał
        stary, np. 100% przy AGROT/PIEL skorygowanych do połowy wydz.)
            zab = [zabieg, powierzchnia]
        """
        proc = self._proc_area(zab[1])
        if proc is None:
            ok = self.baza.wpisz_tab([
                'update f_arod_cue set cutting_area = ? where '
                'arodes_int_num = ? and measure_cd = ?',
                (zab[1], self.aid, zab[0])])
        else:
            ok = self.baza.wpisz_tab([
                'update f_arod_cue set cutting_area = ?, proc_area = ? '
                'where arodes_int_num = ? and measure_cd = ?',
                (zab[1], proc, self.aid, zab[0])])
        if not ok:
            return False
        self.zmodyfikowano += 1
        return True

    def _oblicz_ciecie(self, modyf: str) -> Union[int, int]:
        ''' zwraca % ciecia dla wydz oraz wartosc pozyskania grubizny,
        odczytuje wartość z tablic
        modyf: zabieg z grupy mlodych ['TP', 'TW', 'CP-P']
        zwraca [procent, wartość pozyskania grubizny]
        '''
        # TODO: Zweryfikować tą metode czy dobrze liczy!!!!
        # WYNIKI INNE OD TYCH Z BAZY!!!!
        if not isinstance(modyf, str):
            modyf = ' '
        # zgeneralizuj gatunek drzewa
        gat = self._zgeneralizuj_gatunek()
        # ustaw klase wieku
        wiek = self._ustaw_klase_wieku(gat)
        # zgeneralizuj zasobnosc
        zas = self._zaokraglij_zasobnosc()
        # jezeli zasobnosc jest wieksza niz max w tablicach zwroc max tablicowe
        maxZas = max([x for x in self.cieciaSl[gat][wiek].keys()])
        if 199 < zas < 300:
            zas = 200
        if zas > maxZas - 1:
            zas = maxZas

        zw = {'PEŁ': 0, 'UM': 1, 'PRZ': 2, 'LUŹ': 3, }
        if self.zwarcie in zw.keys():
            # zwracamy tablice [procent grub, m3 grub]
            proc = self.cieciaSl[gat][wiek][int(zas)][zw[self.zwarcie]]

            # powieksz % pozyskania jezeli mniejszy od 20%
            if self.mod_trzeb > 0 and modyf in ['TW', 'TP', 'CP-P']:
                if proc + self.mod_trzeb < 21:
                    proc += self.mod_trzeb
                # a jak większy to ustaw na 20%
                else:
                    proc = 20

            pow_ciecia = self.pow_wydz
            if self.gen_pow_reb > 0:
                pow_ciecia = self.gen_pow_reb
            return [
                proc,
                int(round(self.gat_gl_vol*(float(proc)/100)*pow_ciecia, 0))
            ]

        # jezeli nie udalo sie znalezc danych w slowniku zwroc 20% grubizny
        self.uw_raport.append(
            f'Nie uzupełniono zwarcia [{gat}{wiek} - zas:{zas}m³] '
            '(Wielkość pozyskania na 20%)'
        )
        return [20, round(self.gat_gl_vol*0.2*self.pow_wydz, 0)]

    def _zaokraglij_zasobnosc(self):
        # zaokrąglij zasobność do wartości z tablic
        if self.gat_gl_vol < 6:
            zas = 5
        elif 5 < self.gat_gl_vol < 11:
            zas = 10
        else:
            zas = round(self.gat_gl_vol/10, 0)*10
        return zas

    def _zgeneralizuj_gatunek(self) -> str:
        # skroc nazwy do 2 lub 3 liter, tylko takie mamy dostepne w slowniku
        gat = ''
        if 'BRZ' in self.gat_gl.upper():
            return 'BRZ'
        else:
            gat = self.gat_gl[:2].upper()

        # zagreguj nazwy gatunkow do 6 podstwowych gat ze sl cieć
        if gat in ['MD', 'LB']:
            gat = 'SO'
        elif gat in ['JS', 'WZ', 'KL', 'GB', 'JW', ]:
            gat = 'DB'
        elif gat in ['DG', ]:
            gat = 'ŚW'

        # jezeli dalej sa jakies wymyslone gatunki, policz jak dla BRZ
        if gat not in ['SO', 'DB', 'ŚW', 'BRZ', 'JD', 'BK', 'OL', ]:
            gat = 'BRZ'
        return gat

    def _ustaw_klase_wieku(self, gat: str) -> int:
        """ Ustal klase wieku dla podanego gatunku """
        klWieku = sorted(self.cieciaSl[gat].keys())
        wiek = 0  # zmienna dla przedzialu wieku gatGl
        if self.gat_gl_wiek < klWieku[0] + 1:
            wiek = klWieku[0]
        elif self.gat_gl_wiek > klWieku[-1] - 1:
            wiek = klWieku[-1]
        else:
            for i in range(1, len(klWieku)):
                if klWieku[i-1] < self.gat_gl_wiek <= klWieku[i]:
                    wiek = klWieku[i]
                    break
        return wiek
