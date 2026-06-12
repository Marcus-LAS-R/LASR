from typing import Union


class Wpisz:
    def modyfikuj_zabiegi(self, alter='') -> None:
        """ Metoda dopisuje, badz uaktualnia zabiegi w bazie na podstawie
        wygenerowanych.

        Dostepne opcje:
            alter='' - aktualizuje wydzielenia o wygenerowane zabiegi, jeżli
                jakis zabieg jest juz wpisany i jest zgodny z wygenerowanym ale
                ma rózną powierzchnię albo co innego to zostanie zakutalizowany
            alter='update' - aktualizuje powierzchnie przy zabiegach na takie
                które są zgodne z powierzchnią wydzielenia, o ile w rebniach
                wpisane sa procenty.
        """
        # dopisz rebnie
        if alter == '':
            status, val = self._dopisz_nowa_rebnie()
            if not status:
                self.uw_raport.append(val)
        else:
            if not self._zmodyfikuj_pow_rebni():
                self.uw_raport.append('Nie udało się zmodyfikować powierzchni')

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

    def _zmodyfikuj_pow_rebni(self) -> bool:
        """Metoda modyfikuje rebnie, w bazie dla podanego wydz
        """
        trig = False
        if self.reb == self.gen_reb and self.reb != '':
            if self.pow_reb != self.gen_pow_reb:
                trig = True
        if not trig:
            return
        return self._zmodyfikuj_powierzchnie([self.gen_reb, self.gen_pow_reb])

    def _dopisz_zabiegi(self):
        """Metoda dopisuje zabiegi do bazy, lub uzupełnia powierzchnię juz
        wpisanych. Jeżeli użytkownik wpisał swoją rębnie, dopisane sa zabiegi
        na podstawie wskazanego cięcia.
        """
        for it in self.zabiegi:
            self.max_cue += 1
            self._dopisz_zabieg(it)

    def _dopisz_zabieg(self, zab: list) -> bool:
        """Dopisuje lub modyfikuje zabieg w bazie na podstawie listy.
            zab: ['TP', pow_zab]
        """
        zab_mlode = ['TP', 'TW', 'CP-P', 'CP', 'CW']
        # zabieg już jest wpisany do bazy
        if zab[0] in self.cue:
            if zab[1] != self.cue[zab[0]]:  # i ma inna powierzchnie
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

    def _zmodyfikuj_powierzchnie(self, zab: list) -> bool:
        """Zmodyfikuj pow zabiegu lub rebni
            zab = [zabieg, powierzchnia]
        """
        sql = f'''
            update f_arod_cue set cutting_area={zab[1]} where
            arodes_int_num={self.aid} and measure_cd='{zab[0]}';'''
        if not self.baza.wpisz(sql):
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
