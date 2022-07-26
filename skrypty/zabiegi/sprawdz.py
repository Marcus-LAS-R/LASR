class Sprawdz:
    LESNE = [
        'ARBOR',
        'D-STAN',
        'DROGI L',
        'HAL',
        'INNE WYL',
        'LINIE',
        'PARKING L',
        'PAS GRAN',
        'PAS PPOŻ',
        'PLANT CH',
        'PLANT SZ',
        'PŁAZ',
        'RETENCJA',
        'ROWY',
        'SKŁAD DR',
        'SUKCECJA',
        'SZK LEŚ',
        'TURYST',
        'ZRĄB',
    ]

    POKRYWA_SL = [
        'MSZ',
        'NAGA',
        'SZAD',
        'ŚCIO',
        'ZAD',
        'ZIEL',
        'SZCH',
        'MSZC',
    ]

    def zbiorcze_sprawdzenie(self) -> None:
        """Zbiorczna metoda sprawdzająca wpisane do bazy zabiegi z tymi, które
        zostały wygenerowane przez skrypt. Wynikiem jest wygenerowany raport
        txt w katalogu z bazą (generowany w jednej z metod w klasie wydzielenie
        tutaj uwagi dopisywane są tylko do tablic.
        """
        self.sprawdz_luki()
        self.sprawdz_pow_rebni()
        self.sprawdz_halizne()
        self.sprawdz_zabiegi_na_haliznie()
        self.sprawdz_ile_rebni()
        self.sprawdz_dopasowanie_reb()
        self.sprawdz_pow_rebni()
        self.sprawdz_dopasowanie_odn()
        self.sprawdz_wiek_rebnosci()
        self.sprawdz_stopien_uszkodzen()
        self.sprawdz_zadrzewienie()
        self.sprawdz_wpisanie_rebni()
        self.sprawdz_tsl_td_pokr()
        self.sprawdz_bonitacje()
        self.sprawdz_pozyskanie_na_1ha()
        self.sprawdz_opis_panujacych()
        self.sprawdz_wpisana_rebnie()
        self.sprawdz_zdublowane_wskazowki()
        self.sprawdz_budowe_pionowa()
        self.sprawdz_gatunki_w_drzew()
        self.sprawdz_pozyskanie_przes()
        self.sprawdz_nadmiarowe_wskazowki()

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
        """Sprawdz czy zakodowany d-stan nie powinien byc halizna"""
        if self.zadrzew < 0.5 and self.typ == 'D-STAN':
            if self.gat_gl_vol == 0:
                self.uw_raport.append('Zadrzewienie poniżej 0.5 -> HAL')
            if self.brak_zad:
                self.uw_raport.append('Brak wpisanego zadrzewienia w bazie')

    def sprawdz_zabiegi_na_haliznie(self):
        if self.typ != 'HAL':
            return
        if 'ODN-HAL' not in self.cue:
            self.uw_raport.append('Brak ODN-HAL na haliznie')

        # sprawdz czy nie wystepują jakieś inne wskazówki
        ponad = [x for x in self.cue.keys()
                 if x not in ['ODN-HAL', 'PIEL', 'AGROT', 'CW', 'POPR',
                              'PRZEST']
                 ]
        if len(ponad) > 0:
            self.uw_raport.append(
                'Znaleziono nieporządane wskazówki na haliznie [' +
                ','.join(ponad) + ']'
                )

    def sprawdz_ile_rebni(self):
        if self.ile_reb > 1:
            self.uw_raport.append(
                'Stwierdzono wpisanie więcej niż jednej rębni w wydz.'
            )

    def sprawdz_zadrz_na_hal_zreb(self):
        if self.typ in ['HAL', 'ZRĄB'] and self.zadrzew > 0.5:
            self.uw_raport.append(
                f'Zadrzewienie większe niż 0.5 [{self.typ}]'
            )

    def sprawdz_dopasowanie_reb(self):
        if self.ile_reb == 1:
            _reb = self.reb.replace('U', '')
            if _reb not in [
                    x[0] for x in self.rebnieSl[self.stl]] + ['PŁAZ', 'IVD']:
                self.uw_raport.append(
                    'Rębnia niedostosowana do STL ('+self.stl +
                    '), jest: ' +
                    self.reb + ' (' + str(self.pow_reb) + 'ha)' +
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
                        'Powierzchnia rębni mniejsza od powierzchni ' +
                        'wydzielenia  ' +
                        str(self.pow_reb) + ' / ' + str(self.pow_wydz) + ' ha'
                    )

            if self.pow_wydz < self.pow_reb:
                self.uw_raport.append(
                    'Powierzchnia rębni większa od powierzchni wydzielenia  ' +
                    str(self.pow_reb) + ' / ' + str(self.pow_wydz) + ' ha'
                )

    def sprawdz_dopasowanie_odn(self):
        # TODO: dodać podmienienie tych odnowień
        if self.ile_reb == 1:
            if ('ODN-ZRB' in self.cue and self.reb not in
                    self.rebnieSpis[:3]+[self.rebnieSpis[24]]):
                self.uw_raport.append('Odnowienie zrębu na rębni częściowej')
            if ('ODN-ZŁOŻ' in self.cue and
                    self.reb not in self.rebnieSpis[3:24]):
                self.uw_raport.append('Odnowienie złożone na rębni zupełnej')

    def sprawdz_wiek_rebnosci(self):
        if self.gen_reb != '' or self.reb in self.rebnieSpis:
            if self.gat_gl == '':
                self.uw_raport.append('Nie wpisano gatunku głównego')
                return
            if self.gat_gl_wiek == 0:
                self.uw_raport.append('Nie wpisano wieku gatunku głównego ')
                return

            if self.gat_gl_wiek < self.wiekReb - 11:
                if self.reb not in ['PŁAZ', 'IVD'] and \
                        self.uszk not in ['2', '3']:
                    self.uw_raport.append(
                        f'Rębnia poniżej wieku rębności, {self.reb} w wieku:' +
                        f' {self.gat_gl_wiek}, wiek rębności w bazie ' +
                        f'ustalono na: {self.wiekReb}; ' +
                        f'opis w bazie: {self.uwagi}'
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
                zar = self.cue[zab[0]]
                try:
                    zar = float(zar)
                except TypeError:
                    zar = 0.0

                if round(zab[1], 4) != round(zar, 4):
                    self.uw_raport.append(
                        'Zabieg: ' + zab[0] +
                        ", ma powierzchnię niezgodną z wygenerowaną: " +
                        str(zab[1]) + 'ha, (baza: ' + str(zar) +
                        'ha)')
            else:
                self.uw_raport.append(
                    f'Nie wpisano zabiegu: {zab[0]}, '
                    f'o powierzchni: {zab[1]}, # [' +
                    ', '.join(self.cue.keys()) + ']')

        if len(self.cue) == 0 and self.typ in [
                'PŁAZ', 'D-STAN', 'HAL', 'ZRĄB']:
            self.uw_raport.append('-->> Brak wpisanych zabiegów w bazie!!')

    def sprawdz_wpisanie_rebni(self):
        if self.reb == '' and self.gen_reb != '' and self.typ == 'D-STAN':
            self.uw_raport.append(
                f'Nie dodano rebni do wydzielenia? ({self.gen_reb}) # [' +
                ', '.join([x for x in self.cue.keys()]) + ']'
            )

    def sprawdz_tsl_td_pokr(self):
        if self.typ in ['', 'None', None]:
            self.uw_raport.append(
                'Nie wpisano typu powierzchni w wydzieleniu!'
            )
            return

        if self.typ in self.LESNE:
            if self.stl == '':
                self.uw_raport.append('Brak wpisanego STL')
            if self.pokrywa == '':
                self.uw_raport.append('Brak wpisanej pokrywy')
            elif self.pokrywa not in self.POKRYWA_SL:
                self.uw_raport.append('cuda wpisane jako pokrywa roślinna')
            if self.struk == '' and self.typ == 'D-STAN':
                self.uw_raport.append('Brak wpisanej struktury d-stanu')
            if self.cel_hod == 0:
                self.uw_raport.append('Brak wpisanego TD')
        elif self.typ in ['L ENERG', 'L TELEK', 'LZ-Ł']:
            if self.stl not in ['', None, 'None']:
                self.uw_raport.append(
                    f'wpisany STL, a nie powinien byc [{self.typ}]'
                )
            if self.pokrywa not in ['', None, 'None']:
                self.uw_raport.append(
                    f'Wpisana pokrywa [{self.pokrywa}], ' +
                    f'a nie powinna [{self.typ}]'
                )
            if self.struk not in ['', None, 'None']:
                self.uw_raport.append(
                    f'wpisana struktura, a nie powinna [{self.typ}]'
                )
            if self.cel_hod > 0:
                self.uw_raport.append(f'Wpisano TD [{self.typ}]')
        else:
            if self.stl == '':
                self.uw_raport.append(
                    f'Niewpisany STL, a powinien byc [{self.typ}]'
                )
            if self.pokrywa == '':
                self.uw_raport.append(
                    f'Niewpisana pokrywa, a powinna być [{self.typ}]'
                )
            if self.struk != '':
                self.uw_raport.append(
                    f'wpisana struktura, a nie powinna [{self.typ}]'
                )
            if self.cel_hod == 0:
                self.uw_raport.append(f'Nie wpisano TD [{self.typ}]')

    def sprawdz_bonitacje(self):
        if self.bonitacja_flag:
            self.uw_raport.append(
                'Niepoprawna bonitacja - IA dla innego gatunku'
            )

    def sprawdz_opis_panujacych(self):  # noqa
        sumowanie = 0
        for row in self.drzew_gat:
            if not str(row[2]).isdigit():
                continue
            sumowanie += int(row[2])

            # wiek
            if not isinstance(row[3], int):
                self.uw_raport.append(
                    f'Brak wpisanego wieku [{row[2]}{row[0]}]'
                )
                return
            elif row[3] > 150:
                self.uw_raport.append(
                    f'Sprawdź wpisany wiek [{row[4]} lat]'
                )

            # piersnica
            if not isinstance(row[4], int):
                self.uw_raport.append(
                    f'Brak wpisanej pierśnicy [{row[2]}{row[0]}]'
                )
                return
            elif 120 < row[4] and row[4] < 8:
                self.uw_raport.append(
                    f'Sprawdź wpisaną pierśnicę [{row[2]}{row[0]} -'
                    f'{row[4]}cm]'
                )

            # wysokosc
            if not isinstance(row[5], int):
                self.uw_raport.append(
                    f'Brak wpisanej wysokości [{row[2]}{row[0]}]'
                )
                return
                if self.zwarcie != '':
                    self.uw_raport.append(
                        'Brak wpisanej wysokości, a jest zwarcie '
                        f'[{row[2]}{row[0]}]'
                    )

            elif 120 < row[5] and row[5] < 8:
                self.uw_raport.append(
                    f'Sprawdź wpisaną wysokość [{row[2]}{row[0]} -'
                    f'{row[5]}m]'
                )

            # sprawdzenie dużych odchyłek w danych
            # TODO: poprawić toto na coś sensowniejszego!!!
            if (row[4]/row[5]) > 1.45 or (row[4]/row[5]) < 0.55:
                self.uw_raport.append(
                    f'Duża odchyłka pierś/wys w {row[2]}{row[0]}{row[3]} ' +
                    f'( {row[4]}cm/{row[5]}m )'
                )

            if row[3] < 10 and row[4] > 10:
                self.uw_raport.append(
                    f'Sprawdź zależność wiek/pierśnica [{row[2]}{row[0]} -'
                    f' {row[3]}lat - {row[4]}cm]'
                )
        if sumowanie != 10 and sumowanie > 0:
            self.uw_raport.append('Suma udziałów nie wynosi 10')

    def sprawdz_wpisana_rebnie(self):
        if self.reb not in \
                ['IB', 'IIB', 'IIBU', 'IVD', 'IVDU', 'V', '', 'PŁAZ']:
            self.uw_raport.append(f'Wpisano do bazy rębnie [{self.reb}]')

    def sprawdz_zdublowane_wskazowki(self):
        if len(self.zdublowane_cue) == 0:
            return

        self.uw_raport.append(
            'Znaleziono zdublowane wskazówki w bazie ['
            ', '.join(self.zdublowane_cue) + ']'
        )

    def sprawdz_zabiegi_na_plaz(self):
        if self.typ != 'PŁAZ':
            return

        braki = [x for x in ['PŁAZ', 'ODN-ZRB', 'AGROT', 'PIEL']
                 if x not in self.cue]

        if len(braki) > 0:
            self.uw_raport.append(
                'Brakuje wskazówek przy PŁAZ [' + ','.join(braki) + ']'
            )

        ponad = [x for x in self.cue.keys()
                 if x not in ['ODN-ZRB', 'PIEL', 'AGROT', 'CW', 'POPR', 'PŁAZ']
                 ]
        if len(ponad) > 0:
            self.uw_raport.append(
                'Znaleziono nieporządane wskazówki na płazowinie [' +
                ','.join(ponad) + ']'
                )

        if self.zadrzew > 0:
            self.uw_raport.append(
                f'Wpisano zadrzewienie na płazowinie [{self.zadrzew}]'
                )

    def sprawdz_budowe_pionowa(self):
        if self.typ != 'D-STAN':
            return
        if self.struk not in ['DRZEW', 'IP', 'IIP', 'KO', 'SP', 'W PIĘTR']:
            self.uw_raport.append(
                'Nie dodano budowy pionowej w wydzieleniu z D-STANem'
            )

    def sprawdz_gatunki_w_drzew(self):
        if self.struk not in ['DRZEW', 'KO', 'IP', 'IIP', 'SP']:
            return
        if len(self.drzew_gat) == 0:
            self.uw_raport.append(
                'Brak wpisanych gatunków w piętrze DRZEW'
            )

    def sprawdz_czy_zerowa_pow_zabiegu(self):
        if self.zerowa_powierzchnia:
            self.uw_raport.append(
                'Zabieg ma wpisaną zerową powierzchnie [' +
                ','.join([f'{k}-{val}' for k, val in self.cue.items()]) +
                ']'
            )

    def sprawdz_pozyskanie_na_1ha(self):
        if self.typ != 'D-STAN':
            return
        if self.pow_wydz > 0:
            pozysk = round(self.sum_cue_volume, 0)
            pozysk += round(self.mlode_pozyskanie, 0)
            pozysk += round(self.przest_pozyskanie, 0)
            pozysk = int(pozysk)
            if 61 < pozysk:
                self.uw_raport.append(
                    f'Pozyskanie >61m³/ha [{pozysk} m³/ha], ' +
                    f'(pow. wydz: {self.pow_wydz})'
                )

            if pozysk > 500 and len(
                [1 for x in self.drzew_gat if x[0][:2] in ['SO', 'ŚW']]
            ) == 0:
                self.uw_raport.append('Pozyskanie >500m³/ha [{pozysk} m³/ha]')

    def sprawdz_pozyskanie_przes(self):
        if 'PRZEST' not in self.cue:
            return

        if self.przest_pozyskanie != self.przest_vol:
            self.uw_raport.append(
                'Pozyskanie PRZEST a miąższość PRZES niezgodne'
            )

    def sprawdz_nadmiarowe_wskazowki(self):
        if self.wybor != 'Uzu':
            return

        nadmiar = [x for x in self.cue if x not in
                   [y[0] for y in self.zabiegi]+[self.reb, self.gen_reb]]
        if len(nadmiar) > 0:
            self.uw_raport.append(
                'Znalazłem nadmiarowe wskazówki i nie wiem co z nimi zrobić!' +
                ' [' + ','.join(nadmiar) + ']'
            )
