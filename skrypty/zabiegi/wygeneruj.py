from typing import Union, Tuple


class Generuj:
    def generuj_zabiegi(self):
        """ Metoda generuje zabiegi w tablicy zab dla danego
        wydzelenia w tablicy w postaci: [['ZABIEG', POW],...]

        kolejność wpisanych zabiegów wpisanych do bazy będzie taka jak w
        tabeli, numeracja będie kontynuowana od największego wpisanego do
        bazy zabiegu, o ile taki istnieje. Jak nie to zanie od zera
        """
        if self.przes:
            self.zabiegi.append(['PRZEST', self.pow_wydz])

        if self.typ in ['PŁAZ', 'ZRĄB', 'HAL']:
            self.zab_plaz()

        if self.typ == 'D-STAN':
            self.generuj_zab_dstan()

            if self.trzebiez:
                if 0.4 < self.zadrzew < 0.9:
                    if self.luki > 0:
                        powluk = round(self.luki, 4)
                        self.zabiegi.append(['ODN-LUK', powluk])
                        self.zabiegi.append(['PIEL', powluk])
                        self.zabiegi.append(['AGROT', powluk])

        return True

    def generuj_rebnie(self, spr: bool = True) -> Tuple[Union[str, int], bool]:
        """Generujemy rebnie dla wydzielenia, w przypadku poprawnym zwracana
        jest tablica ['IB', 50],
        jeżeli spr ustawione na tak i opis taksacyjny nie spełnia wymagan do
        wygenerowania rebnie, zwracany False.

        :spr: bool - czy dokonać sprawdzenia założeń początkowych do wygen reb.
        """
        # szybkie sprawdzenie założeń początkowych do rebni
        if self.czy_wpisana_reb_jest_poprawna():
            return [[self.gen_reb, self.gen_proc_reb]]

        if spr:
            if self.stl not in self.rebnieSlnowy:
                return False
            if self.gat_gl_wiek < self.wiekReb - 20:
                return False
            if self.wiekReb-9 > self.gat_gl_wiek:
                if self.zadrzew > 0.49:
                    return False
            if self.typ != 'D-STAN':
                return False

        # wyczysc zabiegi i trzebiez bo bedziemy generowac rebnie
        self.trzebiez = False
        self.zabiegi = []

        # ustaw rebnie podstawowa dla tego siedliska
        reb = self.rebnieSlnowy[self.stl][0]

        if self.pow_wydz < 0.5 or (self.ile_dzkat < 2 and self.pow_wydz < 4):
            reb = self.rebnieSlnowy[self.stl][1]

        # sprawdz czy nie powinno być ko
        if self.podr + self.nal > 0.49:
            self.zmien_na_ko = True

        if self.struk == 'KO' or self.zmien_na_ko:
            if self.zadrzew >= 0.5:
                reb = self.rebnieSlnowy[self.stl][2]
            if self.zadrzew < 0.5:
                reb = self.rebnieSlnowy[self.stl][3]

        # jezeli jest forma ochrony przyrody to zwroc wariant 3
        if self.fop > 0:
            reb = self.rebnieSlnowy[self.stl][2]

        if self.pow_wydz > 10 and self.ile_dzkat > 1:
            if self.stl not in [
                'LGŚW', 'LGW', 'LŁ', 'LŁG', 'LŁWYŻ', 'LMB',
                'LMGŚW', 'LMGW', 'LMŚW', 'LMW', 'LMWYŻŚW' 'LMWYŻW',
                'LŚW', 'LW', 'LWYŻŚW', 'LWYŻW',
            ]:
                reb = ['IIB', 50]

        # male zadrzewienie i chwile przed wiekiem rebnosci
        if self.zadrzew < 0.5 and self.gat_gl_wiek > self.wiekReb - 10:
            reb = self.rebnieSlnowy[self.stl][3]

        # dstan rozsypujacy sie przed wiekiem rebnosci
        if self.zadrzew < 0.5 and \
                self.wiekReb - 10 > self.gat_gl_wiek > self.wiekReb - 20:
            reb = ['IVDU', 100]

            self.uw_raport.append(
                'Wygenerowano zabiegi dla D-STANU na wydz. z zadrzew<0.5 '
                'i wiekiem rębności gat. gł. '
                f'{self.gat_gl_wiek} lat (baza: {self.wiekReb} lat) '
                f'# rębnia wygenerowana:({reb[0]},  {reb[1]}%); '
                'baza: [' + ', '.join([x for x in self.cue]) + ']'
            )
            # dopisz info o przebudowie w uwagach
            self.wygeneruj_uwagi_do_dopisania('przebud')
            return [reb]

        if self.uszk == '3':
            reb = self.rebnieSlnowy[self.stl][1]
            # dodaj informacje o zmianie standardowego drylu
            self.wygeneruj_uwagi_do_dopisania('uszk')
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
                self.trzebiez = True
            else:
                self.zabiegi.append(['CP', self.pow_wydz])
        elif self.gat_gl_vol > 0 and self.gat_gl_bhd > 9.9999:
            self.zabiegi.append(['TW', self.pow_wydz])
            self.trzebiez = True

    def zab_dstan_trz(self):
        if self.gat_gl_bhd < 20:
            self.zabiegi.append(['TW', self.pow_wydz])
        else:
            self.zabiegi.append(['TP', self.pow_wydz])
        self.trzebiez = True

    def generuj_zab_dstan(self):
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
            if self.gat_gl_wiek < 4:
                return

        if 3 < self.gat_gl_wiek < 20:
            self.zab_dstan_cp()
            return

        if 19 < self.gat_gl_wiek < 40:
            self.gen_reb = ''
            self.gen_proc_reb = 0
            # generuj trzebieze tylko jesli uzytkownik nic nie wpisał
            if self.reb == '':
                self.zab_dstan_trz()
            return

        if self.wiekReb - 9 > self.gat_gl_wiek > 39:
            self.gen_reb = ''
            self.gen_proc_reb = 0
            if self.reb == '':
                self.zabiegi.append(['TP', self.pow_wydz])
                self.trzebiez = True

        genr = self.generuj_rebnie()
        # wygeneruj rebnie o ile jest taka mozliwość
        if genr is not False:
            self.gen_reb = genr[0][0]
            self.gen_proc_reb = genr[0][1]
            self.gen_pow_reb = self.pow_wydz * (self.gen_proc_reb/100)

            # generuj zabiegi dodatkowe dla rebni, o ile nie wygenerowano
            if len(self.zabiegi) == 0 or self.zabiegi == ['PRZEST']:
                self.zab_dstan_odn_reb()

        # jezeli mamy rebnie zupelna to i pow wydz powyzej 1ha dodaj uwage o
        # traktowaniu dzialek ewid jako zrebowe
        if self.gen_reb in ['IA', 'IB', 'IC', ]:
            if self.ile_dzkat > 1 and self.pow_wydz > 1:
                # dodaj informacje o zmianie standardowego drylu
                self.wygeneruj_uwagi_do_dopisania('reb_zup')

    def wygeneruj_uwagi_do_dopisania(self, typ: str) -> None:
        """ Sprawdza czy uwagi do dopisania do bazy, które chce wygeneować
        użytkownik już się tam nie znajdują. Jeżeli nie, to dodaje odpowiedni
        string ze slownika do tablicy uwag
        typ in ['reb_zup', 'uszk', 'przebud', ]
        """

        if typ not in self.uw_sl:
            return

        dl_uwagi_baza = len(self.uwagi)
        # uwaga jest już wpisana, nie ma co dublować
        for key in ['c', 's']:
            if self.uw_sl[typ][key] in self.uwagi:
                return

        wpis = False
        for key in ['c', 's']:
            uw = self.uw_sl[typ][key]
            if dl_uwagi_baza + len(uw) < 255:
                self.uwagi += uw
                wpis = True

        if not wpis:
            self.uw_raport.append(self.uw_sl[typ]['r'])

    def zab_dstan_odn_reb(self):
        """Jezeli użyszkodnik wpisał jakąś rębnie to zabiegi generujemy dla
        podanej przez niego rebni, a jeżeli nic nie podał to jedziemy z
        rębnią ze słownika
        """
        # jezeli uzyszkodnik wpisal trzebiez to nie generuj zabiegow dla rebni
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

    def czy_wpisana_reb_jest_poprawna(self) -> bool:
        """Użytkownik wpisał już rębnie do bazy, sprawdź czy jest ona poprawna,
        czyli zgodna z tym co mamy w słowniku. Jeżeli tak to przyjmij ją jako
        wygenerowaną i kontynuuj obliczenia. Jeżeli niepoprawna to wpisz w
        uwagach że trzeba uzupełnić samemu
        """
        if self.reb.upper() not in self.rebnieSpis:
            return False

        self.gen_proc_reb = self.proc_reb if self.proc_reb > 0 else 100
        if self.gen_proc_reb > 100:
            self.gen_proc_reb = 100
        self.gen_reb = self.reb.upper()
        return True
