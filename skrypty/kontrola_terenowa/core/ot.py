"""Zestawienie tabeli opisu taksacyjnego (OT) dla wybranych wydzieleń.

Port kwerend i algorytmu z materialy/Skladadcz/src/Skladacz3/OT.py oraz
kwerendy.py (Kwerendy.OT_*). Oryginał liczy opis taksacyjny dla całego
obrębu naraz (filtr `mid(adress_forest, 4, 3)` / `mid(..., 7, 4)` po
kodzie gminy/obrębu, uruchamiany raz na obręb w PrzetworzObreb).

Na potrzeby "Materiałów do kontroli terenowej" wejściem jest gotowa lista
ARODES_INT_NUM wydzieleń zaznaczonych ręcznie w warstwie WYDZ_kontrola
(mogą to być pojedyncze wydzielenia rozsiane po całym obrębie), więc
kwerendy filtrują wprost po `ARODES_INT_NUM IN (...)` zamiast po adresie
administracyjnym. Reszta algorytmu (klasa Wydzielenie, sumowanie "Razem"
na koniec każdego oddziału) jest przeniesiona bez zmian.

Zakłada się, że wszystkie ARODES_INT_NUM podane do GeneratorOT pochodzą z
jednej bazy (jednego obrębu) — sortowanie po ORDER_KEY z bazy poprawnie
grupuje wydzielenia oddziałami tylko wtedy, gdy nie miesza się kolejności
z kilku różnych obrębów.
"""

KWERENDY_OT = {
    'OT_podst': '''
    SELECT
        F_ARODES.ADRESS_FOREST,
        F_SUBAREA.SUB_AREA,
        F_SUBAREA.SITE_TYPE_CD,
        F_SUBAREA.STAND_STRUCT_CD,
        F_SUBAREA.AREA_TYPE_CD,
        F_ARODES.arodes_int_num,
        F_SUBAREA.SUBAREA_INFO
    FROM
        F_ARODES INNER JOIN F_SUBAREA ON
        F_ARODES.ARODES_INT_NUM = F_SUBAREA.ARODES_INT_NUM
    where
        F_ARODES.ARODES_INT_NUM in ({})
    order by
        f_arodes.order_key asc
    ;
    ''',

    'OT_ops_zmies': '''
    SELECT
        F_AROD_STOREY.ARODES_INT_NUM,
        F_AROD_STOREY.MIXTURE_CD,
        F_AROD_STOREY.DENSITY_CD
    FROM
        F_AROD_STOREY left join f_arodes on
        f_arodes.arodes_int_num=F_AROD_STOREY.arodes_int_num
    WHERE
        STOREY_CD in ('DRZEW', 'IP')
        and f_arodes.arodes_int_num in ({})
        and storey_rank_order = 1 ;
    ''',

    'OT_ochr': '''
    SELECT
        F_SET.ARODES_INT_NUM,
        F_PROT_AREA_DIC.PROTEC_AREA_CD,
        F_LAND_PROTECT.LAND_PROTECT_NAME
    FROM
        (F_SET INNER JOIN
        (F_PROT_AREA_DIC INNER JOIN F_LAND_PROTECT
        ON
        F_PROT_AREA_DIC.PROTEC_AREA_CD=F_LAND_PROTECT.PROTEC_AREA_CD)
        ON F_SET.MY_INT_NUM = F_LAND_PROTECT.INT_NUM)
        left join f_arodes on
        f_set.arodes_int_num=f_arodes.arodes_int_num
    where
        f_arodes.arodes_int_num in ({})
        ;
    ''',

    'OT_register': '''
    SELECT distinct
        F_AROD_LAND_USE.ARODES_INT_NUM,
        F_PARCEL.LAND_REGISTER_NR
    FROM
        (F_AROD_LAND_USE INNER JOIN F_PARCEL ON
        F_AROD_LAND_USE.PARCEL_INT_NUM = F_PARCEL.PARCEL_INT_NUM)
        left join f_arodes on
        F_AROD_LAND_USE.ARODES_INT_NUM=f_arodes.ARODES_INT_NUM
    where
        f_arodes.arodes_int_num in ({})
    order by
        F_PARCEL.LAND_REGISTER_NR asc
    ;
    ''',

    'OT_taksacja': '''
    SELECT
        F_STOREY_SPECIES.ARODES_INT_NUM,
        F_STOREY_SPECIES.STOREY_CD,
        F_STOREY_SPECIES.SPECIES_CD,
        F_STOREY_SPECIES.PART_CD,
        F_STOREY_SPECIES.SPECIES_AGE,
        F_AROD_STOREY.STANDDENSITY_INDEX,
        F_STOREY_SPECIES.BHD,
        F_STOREY_SPECIES.HEIGHT,
        F_STOREY_SPECIES.SITE_CLASS_CD,
        F_STOREY_SPECIES.VOLUME,
        F_STOREY_SPECIES.INCREMENT_CURRENT,
        F_STOREY_SPECIES.INCREMENT_CURRENT_AREA,
        F_STOREY_SPECIES.VOLUME_TEMP
    FROM
        (F_AROD_STOREY right JOIN F_STOREY_SPECIES ON
        (F_AROD_STOREY.ARODES_INT_NUM=F_STOREY_SPECIES.ARODES_INT_NUM)
        AND (F_AROD_STOREY.STOREY_CD = F_STOREY_SPECIES.STOREY_CD)
        )
        left join f_arodes on
        f_arod_storey.ARODES_INT_NUM=f_arodes.ARODES_INT_NUM
    where
        f_arodes.arodes_int_num in ({})
    ORDER BY
        F_STOREY_SPECIES.ARODES_INT_NUM asc,
        F_STOREY_SPECIES.STOREY_CD asc,
        F_STOREY_SPECIES.species_rank_order asc;
    ''',

    'OT_ciecie': '''
    SELECT
        F_ARODES.ARODES_INT_NUM,
        F_AROD_CUE.CUE_RANK_ORDER,
        F_AROD_CUE.MEASURE_CD,
        F_AROD_CUE.CUTTING_AREA,
        F_AROD_CUE.LARGE_TIMBER_VALUE,
        F_AROD_CUE.LARGE_TIMBER_VALUE_NET
    FROM
        F_AROD_CUE inner join f_arodes on
        F_AROD_CUE.ARODES_INT_NUM=f_arodes.ARODES_INT_NUM
    where
        f_arodes.arodes_int_num in ({})
    order by
        f_arod_cue.cue_rank_order asc
    ;
    ''',

    'OT_cele_hod': '''
    SELECT
        F_arodes.arodes_int_num,
        F_AROD_GOAL.SPECIES_CD
    FROM
        F_ARODES INNER JOIN F_AROD_GOAL ON
        F_ARODES.ARODES_INT_NUM = F_AROD_GOAL.ARODES_INT_NUM
    WHERE
        F_arodes.arodes_int_num in ({})
    ORDER BY
        F_arodes.arodes_int_num asc,
        F_AROD_GOAL.goal_rank_order asc;
    ''',

    'OT_pnsw': '''
    SELECT
        F_AROD_SPEC_AREA.ARODES_INT_NUM,
        F_AROD_SPEC_AREA.AROD_SPAREA_ORDER,
        F_AROD_SPEC_AREA.SPECIAL_AREA_CD,
        F_AROD_SPEC_AREA.LOCATION_CD,
        F_AROD_SPEC_AREA.SPECIAL_AREA,
        F_AROD_SPEC_AREA.SPECIAL_AREA_NUM
    FROM
        F_AROD_SPEC_AREA LEFT JOIN F_ARODES ON
        F_AROD_SPEC_AREA.ARODES_INT_NUM = F_ARODES.ARODES_INT_NUM
    WHERE
        F_ARODES.arodes_int_num in ({})
    ORDER BY
        F_AROD_SPEC_AREA.ARODES_INT_NUM asc,
        F_AROD_SPEC_AREA.AROD_SPAREA_ORDER asc;
    ''',

    'OT_gatunki_pnsw': '''
    SELECT
        F_SPECIES_SPAREA.ARODES_INT_NUM,
        F_SPECIES_SPAREA.AROD_SPAREA_ORDER,
        F_SPECIES_SPAREA.SPECIES_CD,
        F_SPECIES_SPAREA.SP_AGE
    FROM
        F_SPECIES_SPAREA LEFT JOIN F_ARODES ON
        F_SPECIES_SPAREA.ARODES_INT_NUM = F_ARODES.ARODES_INT_NUM
    WHERE
        F_ARODES.arodes_int_num in ({})
    ORDER BY
        F_SPECIES_SPAREA.ARODES_INT_NUM asc,
        F_SPECIES_SPAREA.AROD_SPAREA_ORDER asc,
        F_SPECIES_SPAREA.SP_RANK_ORDER asc;
    ''',

    'OT_uszkodzenia': '''
    SELECT
        F_SUBAREA.ARODES_INT_NUM,
        F_SUBAREA.DAMAGE_DEGREE_CD,
        F_SUBAREA.CAUSE_CD
    FROM
        F_SUBAREA INNER JOIN F_ARODES ON
        F_SUBAREA.ARODES_INT_NUM = F_ARODES.ARODES_INT_NUM
    WHERE
        F_SUBAREA.DAMAGE_DEGREE_CD IS NOT NULL
        and F_ARODES.arodes_int_num in ({})
    ORDER BY
        F_SUBAREA.ARODES_INT_NUM asc;
    ''',
}


class Wydzielenie:
    def __init__(self):
        self.adr = ''
        self.area = 0.0
        self.sied = ''
        self.typ = ''
        self.struk = ''
        self.zmiesz = 0
        self.zwar = ''
        self.ochr = []  # tabela z formami ochr w postaci ['PARK KRAJ-Nazwa', ]
        self.adr_les = ''
        self.reg = []  # tabela z numerami reg
        self.cele = []
        self.ciecie = []  # tabela z cieciami [ciecie, pow, Vbrutto, Vnetto]
        self.info = ''  # informacje opisowe dla wydzielenia
        self.pnsw = []  # lista PNSW: [{'order':, 'location':, 'kod':, 'num':, 'area':, 'gatunki': []}]
        self.uszkodzenia = []  # tabela uszkodzeń [(przyczyna, stopień)]

        # Razem dla wydzielenia
        self.pow_ha = []  # lista z wartosciami do sumowania miaz na ha
        self.pow_pow = []  # lista z wartosciami do sumowania miaz dla pow

        # tabela z danymi z taksacji
        # [warstwa, gat, udz, wiek, zadrz warstwy, bhd, H, bonit, vol, vol/ha,
        # przyr/ha, przyr na pow]
        self.taks = []

        self.razem = {'pow': 0, 'vol': 0, 'vnet': 0, 'vbrut': 0}

    def dodaj_opis(self, op):
        """Przetwarza wiersz z kwerendy OT_podst"""
        self.adr_les = op[0]
        self.adr = self.adr_les[13:17] + '-' + self.adr_les[18:22]
        self.adr = self.adr.replace(' ', '')
        self.area = op[1]
        self.razem['pow'] = self._round(self.area)
        self.typ = op[4] if op[4] is not None else ''
        self.struk = op[3] if op[3] is not None else ''
        self.sied = op[2] if op[2] is not None else ''
        self.info = op[6] if op[6] is not None else ''

    def dodaj_ochr(self, op):
        """Przetwarza wiersz z kwerendy OT_ochr"""
        if op[1] + '-' + op[2] not in self.ochr:
            self.ochr.append(op[1] + '-' + op[2])

    def dodaj_zmieszanie(self, op):
        """przetwarza wiesz z kwerendy OT_ops_zmies"""
        self.zmiesz = op[1] if op[1] is not None else ''
        self.zwar = op[2] if op[2] is not None else ''

    def dodaj_rejestry(self, op):
        """Przetwarza wiersz z kwerendy OT_register"""
        if op[1] not in self.reg:
            self.reg.append(op[1])

    def dodaj_cele_hod(self, op):
        """przetwarza wiersz z kwerendy OT_cele_hod,
        UWAGA kolejność dodawania gatunków ma znaczenie i jest regulowana przez
        kwerende!
        """
        if op[1] not in self.cele:
            self.cele.append(op[1])

    def dodaj_pnsw(self, op):
        """Przetwarza wiersz z kwerendy OT_pnsw
        op: [ARODES_INT_NUM, AROD_SPAREA_ORDER, SPECIAL_AREA_CD, LOCATION_CD, SPECIAL_AREA, SPECIAL_AREA_NUM]
        """
        order = op[1] if op[1] is not None else 0
        kod = op[2] if op[2] is not None else ''
        location = op[3] if op[3] is not None else ''
        area = self._round(op[4]) if op[4] is not None else ''
        num = str(int(op[5])) if op[5] is not None else ''
        self.pnsw.append({'order': order, 'location': location, 'kod': kod,
                          'num': num, 'area': area, 'gatunki': []})

    def dodaj_gatunek_pnsw(self, op):
        """Przetwarza wiersz z kwerendy OT_gatunki_pnsw
        op: [ARODES_INT_NUM, AROD_SPAREA_ORDER, SPECIES_CD, SP_AGE]
        """
        order = op[1]
        species_cd = op[2] if op[2] is not None else ''
        sp_age = str(int(op[3])) if op[3] is not None else ''
        for p in self.pnsw:
            if p['order'] == order:
                p['gatunki'].append((species_cd, sp_age))
                break

    def dodaj_uszkodzenie(self, op):
        """Przetwarza wiersz z kwerendy OT_uszkodzenia (op[1]=DAMAGE_DEGREE_CD, op[2]=CAUSE_CD)"""
        stopien = op[1] if op[1] is not None else ''
        przyczyna = op[2] if op[2] is not None else ''
        self.uszkodzenia.append((stopien, przyczyna))

    def dodaj_taksacje(self, op):
        """Przetwarza wiersz z kwerendy OT_taksacja
        Uwaga kolejność dodawanych gatunków i warstw ma znacznie
        """
        ost_war = '-111'
        zad = '-111'

        # znajdz ostatnia wartosc do porownania, jeżeli nie będzie taka sama to
        # zostanie oznaczona jako do wpisania w tabeli
        if len(self.taks) > 0:
            tab = [x[0] for x in self.taks]
            if op[1] in tab:
                ost_war = op[1]
                zad = self.taks[tab.index(op[1])][4]

        vol = op[9]
        if vol is None and op[1] == 'PRZES':
            vol = op[12]

        self.taks.append([
            '' if op[1] == ost_war else op[1],
            op[2],
            op[3] if op[3] is not None else ' ',
            self._round(op[4], calk='T'),
            op[5] if op[5] != zad else ' ',
            self._round(op[6], calk='T'),
            self._round(op[7], calk='T'),
            op[8] if op[8] is not None else ' ',
            vol,
            self._round(op[10], rr=2),
            self._round(op[11]/10 if op[11] is not None else None, rr=2),
            op[1],
        ])

        if op[10] not in ['', ' ', None]:
            self.razem['vol'] += op[10]

    def dodaj_ciecie(self, op):
        """Przetwarza wiersz z kwerendy OT_ciecie"""
        netto = op[5]
        if netto is None and op[2] == 'PRZEST':
            netto = op[4]

        self.ciecie.append([
            op[2],
            self._round(op[3]),
            self._round(op[4], calk='T'),
            self._round(netto, calk='T'),
        ])

        if op[4] not in ['', ' ', None]:
            self.razem['vbrut'] += op[4]
        if netto not in ['', ' ', None]:
            self.razem['vnet'] += netto

    def oblicz_razem(self):
        """Zwraca wiersz razem sumując powierzchnie i masy"""
        return self.razem

    def wypis(self):
        """Zwraca gotowy wypis do szablonu"""
        wyps = []
        maxi = max(len(self.ciecie), len(self.taks), 1)

        for i in range(maxi):
            wyps.append(self._wiersz(i))

        suma = self._zestawienie_wydz()
        if suma is not False:
            wyps.append(suma)

        return {'opis': wyps, 'razem': [{
            'pow': self.area,
            'vol': self.razem['vol'],
            'vnet': self.razem['vnet'],
            'vbrut': self.razem['vbrut'],
        }]
        }

    def _wiersz(self, wi):
        """Generuj slownik dla wiersza o podanym nr wiersza"""
        sl = {'adr': '',
              'pow': '',
              'ops': '',
              'war': '',
              'gat': '',
              'udz': '',
              'wiek': '',
              'zad': '',
              'bhd': '',
              'wys': '',
              'bon': '',
              'vha': '',
              'vpow': '',
              'przyr': '',
              'cue': '',
              'cuep': '',
              'cueb': '',
              'cuen': '',
              }

        if wi == 0:
            sl['adr'] = self.adr
            sl['pow'] = self._round(self.area)
            sl['ops'] = self._zestaw_opis()

        if wi < len(self.taks):
            sl['war'] = self.taks[wi][0]
            sl['gat'] = self.taks[wi][1]
            sl['udz'] = self.taks[wi][2]
            sl['wiek'] = self.taks[wi][3]
            sl['zad'] = str(
                round(self.taks[wi][4], 1)
            ).replace('.', ',') if self.taks[wi][4] not in [None, ' '] else ' '
            sl['bhd'] = self.taks[wi][5]
            sl['wys'] = self.taks[wi][6]
            sl['bon'] = self.taks[wi][7]
            przestoj = self.taks[wi][11] == 'PRZES'
            if przestoj:
                # dla przestoji wartosc z bazy to miazszosc na calej
                # powierzchni wydzielenia, nie przeliczamy na ha
                vol_pow = self.taks[wi][8]
                sl['vha'] = '-'
            else:
                vol_ha = self.taks[wi][8]
                try:
                    vol_pow = vol_ha * self.area
                except TypeError:
                    vol_pow = None
                sl['vha'] = self._round(vol_ha, calk='T')

            sl['vpow'] = self._round(vol_pow, calk='T') if vol_pow is not None else ''

            # obliczenia dla razem
            if not przestoj and sl['vha'] not in [' ', '', None]:
                self.pow_ha.append(round(vol_ha))
            if sl['vpow'] not in [' ', '', None]:
                self.pow_pow.append(round(vol_pow))

            sl['przyr'] = str(self.taks[wi][9]) + '/' + str(self.taks[wi][10])

        if wi < len(self.ciecie):
            sl['cue'] = self.ciecie[wi][0]
            sl['cuep'] = self.ciecie[wi][1]
            sl['cueb'] = self.ciecie[wi][2]
            sl['cuen'] = self.ciecie[wi][3]

        return sl

    def _zestawienie_wydz(self):
        """Oblicza czy należy dodać wiersz razem na końcu każdego wydzielenia,
        musi być wiecej niz jedna wartość dla miazszosci w bazie"""

        if len(self.pow_ha) > 1 and len(self.pow_pow) > 1:
            try:
                sl = {
                    'war': 'Razem',
                    'vha': self._round(sum(self.pow_ha), calk='T'),
                    'vpow': self._round(sum(self.pow_pow), calk='T'),
                }
                return sl
            except Exception:
                pass
        return False

    def _zestaw_opis(self):
        """Zestawia opis taksacyjny dla wydzielenia
            Zwraca str
        """
        ops = ''
        if len(self.ochr) > 0:
            ops += 'OC: ' + ', '.join(self.ochr) + ', '

        ops += 'RP: ' + self.typ
        ops += ', BP: ' + self.struk
        ops += ', S: ' + self.sied

        if len(self.cele) > 0:
            ops += ', TD: ' + ', '.join(self.cele)

        ops += ', ZW: ' + self.zwar
        ops += ', ZM: ' + str(self.zmiesz)

        if len(self.uszkodzenia) > 0:
            czesci = [st + '-' + pr for st, pr in self.uszkodzenia]
            ops += ', USZ: ' + '; '.join(czesci)

        if len(self.reg) > 0:
            ops += ', NR REJ: ' + ', '.join(sorted(self.reg))

        if self.info != '':
            ops += ', INFO: ' + self.info

        if len(self.pnsw) > 0:
            linii_pnsw = []
            for p in self.pnsw:
                linia = 'w części ' + p['location'] + ' ' + p['kod']
                if p['num']:
                    linia += '(' + p['num'] + ')'
                linia += ' ' + p['area']
                for gat_cd, sp_age in p['gatunki']:
                    linia += ' ' + gat_cd + ' ' + sp_age
                linii_pnsw.append(linia)
            ops += '\n' + '-' * 20 + '\n' + '\n'.join(linii_pnsw)

        return ops

    def _round(self, val, calk='', rr=4):
        """ustawia wartosc liczby do rr miejsc po przecinku włącznie z zerami,
        lub w przypadku null -> ' '
        """

        try:
            b = round(val, rr)
            if calk == 'T':
                return str(int(round(b, 0)))
            podz = str(b).split('.')
            if len(podz) == 1:
                podz.append(rr*'0')
            if b == 0:
                return ' '
            return podz[0] + ',' + podz[1] + (rr-len(podz[1])) * '0'
        except Exception:
            return ' '


class GeneratorOT:
    """Zestawia tabelę opisu taksacyjnego dla podanej listy ARODES_INT_NUM,
    wszystkich pobranych z jednej otwartej bazy (jeden obiekt = jedno
    wywołanie kwerend OT_* dla jednej bazy .mdb/.sqlite)."""

    def __init__(self, baza, arodes_ids):
        self.baza = baza
        self.arodes_ids = list(arodes_ids)
        self._ids_sql = ','.join(str(int(a)) for a in self.arodes_ids)

    def generuj(self):
        """Zbiorcza metoda, zwraca listę gotową do wstawienia w docxtpl
        jako `tabela_ot` (jak w SZABLON_OPERAT_OT.docx)."""

        self.ot = {}  # arodes_int_num: Wydzielenie
        self.ot_kolej = []  # kolejnosc wydzielen w tabeli na podst bazy

        self._ot_pocz()
        self._ot_zmieszanie()
        self._ot_rejestr()
        self._ot_f_ochrony()
        self._ot_takacja()
        self._ot_cele_hodowlane()
        self._ot_ciecia()
        self._ot_pnsw()
        self._ot_gatunki_pnsw()
        self._ot_uszkodzenia()

        wyps = []
        # zmienna trzymajaca nr oddzialu, w przypadku zmiany
        # zmiany oddz generuj wiersz razem dla oddz
        oddz = 'pocz'
        sum_all = {
            'pow': 0, 'vol': 0, 'vnet': 0, 'vbrut': 0, 'adr': 'Ogółem',
        }
        for tt in self.ot_kolej:
            ww = self.ot[tt].wypis()

            aoddz = ww['opis'][0]['adr'].split('-')[0]

            if oddz == 'pocz':
                oddz = aoddz
                sum_o = {
                    'pow': 0,
                    'vol': 0,
                    'vnet': 0,
                    'vbrut': 0,
                    'adr': 'Razem',
                }

            if oddz != aoddz:
                wyps.append({'opis': [{
                    'adr': 'Razem',
                    'pow': self.ot[tt]._round(sum_o['pow']),
                    'vol': self.ot[tt]._round(sum_o['vol'], calk='T'),
                    'cuen': self.ot[tt]._round(sum_o['vnet'], calk='T'),
                    'cueb': self.ot[tt]._round(sum_o['vbrut'], calk='T'),
                    }], 'razem': [{}]})

                # suma ogolna
                sum_all['pow'] += sum_o['pow']
                sum_all['vol'] += sum_o['vol']
                sum_all['vnet'] += sum_o['vnet']
                sum_all['vbrut'] += sum_o['vbrut']

                # zeruj zbiorcze  dla oddz
                sum_o = {
                    'pow': 0,
                    'vol': 0,
                    'vnet': 0,
                    'vbrut': 0,
                    'adr': 'Razem',
                }
                oddz = aoddz

            sum_o['pow'] += ww['razem'][0]['pow']
            if ww['razem'][0]['vol'] not in [None, '', ' ']:
                sum_o['vol'] += ww['razem'][0]['vol']
            if ww['razem'][0]['vnet'] not in [None, '', ' ']:
                sum_o['vnet'] += ww['razem'][0]['vnet']
            if ww['razem'][0]['vbrut'] not in [None, '', ' ']:
                sum_o['vbrut'] += ww['razem'][0]['vbrut']

            wyps.append(ww)

        # Razem dla ostatniego oddzialu
        wyps.append({'opis': [{
            'pow': self.ot[tt]._round(sum_o['pow']),
            'vol': self.ot[tt]._round(sum_o['vol'], calk='T'),
            'cuen': self.ot[tt]._round(sum_o['vnet'], calk='T'),
            'cueb': self.ot[tt]._round(sum_o['vbrut'], calk='T'),
            'adr': 'Razem',
        }],
            'razem': [{}]})

        # suma ogolna
        sum_all['pow'] += sum_o['pow']
        sum_all['vol'] += sum_o['vol']
        sum_all['vnet'] += sum_o['vnet']
        sum_all['vbrut'] += sum_o['vbrut']

        wyps.append({'opis': [{
                    'pow': self.ot[tt]._round(sum_all['pow']),
                    'vol': self.ot[tt]._round(sum_all['vol'], calk='T'),
                    'cuen': self.ot[tt]._round(sum_all['vnet'], calk='T'),
                    'cueb': self.ot[tt]._round(sum_all['vbrut'], calk='T'),
                    'adr': 'Ogółem',
                    }], 'razem': [{}]})

        return wyps

    def _ot_pocz(self):
        """Zbuduj strukture do dalszego przetwarzania tabeli OT"""

        sql = KWERENDY_OT['OT_podst'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)

        for pi in pob:
            self.ot[pi[5]] = Wydzielenie()
            self.ot[pi[5]].dodaj_opis(pi)
            self.ot_kolej.append(pi[5])

    def _ot_zmieszanie(self):
        """Dodaj zmieszanie i udział"""

        sql = KWERENDY_OT['OT_ops_zmies'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)

        for pi in pob:
            self.ot[pi[0]].dodaj_zmieszanie(pi)

    def _ot_f_ochrony(self):
        """Dodaj formy ochrony w wydzieleniach"""

        sql = KWERENDY_OT['OT_ochr'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)

        for pi in pob:
            self.ot[pi[0]].dodaj_ochr(pi)

    def _ot_rejestr(self):
        """Dodaj nr rejestrowe do wydzielen"""
        sql = KWERENDY_OT['OT_register'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)

        for pi in pob:
            self.ot[pi[0]].dodaj_rejestry(pi)

    def _ot_cele_hodowlane(self):
        """Dodaj cele hodowlane do wydzielen"""
        sql = KWERENDY_OT['OT_cele_hod'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)

        for pi in pob:
            self.ot[pi[0]].dodaj_cele_hod(pi)

    def _ot_takacja(self):
        """Dodaj taksacje do wydzielen"""
        sql = KWERENDY_OT['OT_taksacja'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)

        for pi in pob:
            self.ot[pi[0]].dodaj_taksacje(pi)

    def _ot_ciecia(self):
        """Dodaj ciecia do wydzielen"""
        sql = KWERENDY_OT['OT_ciecie'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)

        for pi in pob:
            self.ot[pi[0]].dodaj_ciecie(pi)

    def _ot_pnsw(self):
        """Dodaj PNSW do wydzielen"""
        sql = KWERENDY_OT['OT_pnsw'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)

        for pi in pob:
            if pi[0] in self.ot:
                self.ot[pi[0]].dodaj_pnsw(pi)

    def _ot_gatunki_pnsw(self):
        """Dodaj gatunki PNSW do wydzielen"""
        sql = KWERENDY_OT['OT_gatunki_pnsw'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)
        for pi in pob:
            if pi[0] in self.ot:
                self.ot[pi[0]].dodaj_gatunek_pnsw(pi)

    def _ot_uszkodzenia(self):
        """Dodaj uszkodzenia do wydzielen"""
        sql = KWERENDY_OT['OT_uszkodzenia'].format(self._ids_sql)
        pob = self.baza.pobierz(sql)

        for pi in pob:
            if pi[0] in self.ot:
                self.ot[pi[0]].dodaj_uszkodzenie(pi)
