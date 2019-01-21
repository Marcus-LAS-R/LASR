from collections import Counter
import re


class Przetworz(object):
    def __init__(self):
        # tabele z bazy podane przez uzytkownika
        self.baza_wlasnosci = []
        self.baza_uzytki = []

        # lista wlascicieli z kodami OP
        # [[wlasciciel, wyr1], ...]
        self.listaOP = []

        # zbior z nazwami dzialek lesnych
        self.dz_lesne = set([])

        # slownik z wszystkimi dzialkami w postaci:
        # {GGOOOONRDZ: [WOJ, POWIAT, WYR1, PARCEL_AREA, PARCEL_INT_NUM]}
        self.dzialki = {}  # dz_dict

        # slownik z wlasnosciami wlasciciela = {"wlascieciel": [wyr1, ...]}
        # nalezy sotosowac tylko dla firm, prywatni moga zostac pogrupowani,
        # jezeli sie tak samo nazywaja
        self.sl_wlasnosc = {}

        # slownik z kodami wlascicieli dla kazdej dzialki
        # {Wyr1: ['OP', 'OF' ...]}
        self.sl_kody_wlasciceli_na_dzialce = {}  # wl_dict

        # listy działek z pogrupowanymi własnościami
        self.dz_op = []
        self.dz_opif = []
        self.dz_of = []

        # Zbior wszystkich ls
        # (landid, landid, ...)
        self.ls = set([])

        # lista lsów w bazie, które występują wiecej niz raz - blad zasobu
        # [LANDID, LANDIID, ... ]
        self.ls_podwojne = []

        # Slownik ze wszystkimi uzytkami z bazy w postaci:
        # {LANDID: [
        #     0  AREA_USE,
        #     1  SOIL_QUALITY,
        #     2  LAND_USE_AREA,
        #     3  Wyr1,
        #     4  PARCEL_INT_NUM,
        # ]}
        self.uzytki = {}  # uzytki_sl

        # slownik z klasami Ls na dzialce w formie:
        # {Wyr1: ['V', 'VI', ... ]
        self.sl_ls_na_dz = {}  # ile_ls_baza

        # slownik z pow rej ls i dzialek ale tylko dla takich gdzie jest jeden
        # ls, do sprawdzenia czy grafiki ls nie nalezy podmienic na graf dz
        # {PARCELID: [LAND_USE_AREA, PARECEL_AREA],}
        self.sl_pow_ls_dzkat = {}

        # slownik z liczba uzytkow na kadzej dzialce w bazie
        # {Wyr1: 2, }
        self.sl_ile_uzytkow_na_dzialce = {}  # ile_uzytkow_baza

    def dane_z_bazy(metoda):
        def wrap(*args):
            self = args[0]
            if len(self.baza_wlasnosci) > 0 and len(self.baza_uzytki) > 0:
                metoda(self)
            else:
                print('Brak zaimportowanych wlasnosci albo uzytkow!')
        return wrap

    def dodaj_wlasnosci(self, tab):
        self.baza_wlasnosci = tab

    def dodaj_uzytki(self, tab):
        self.baza_uzytki = tab

    def przetworz_uzytkowanie(self):
        # metoda zbiorcza dla uzytkowania

        self.przetworz_wszystkie_ls()
        self.przetworz_ls_podwojne()
        self.przetworz_uzytki()
        self.przetworz_ile_uzytow_na_dzialce()
        self.przetworz_ile_ls_na_dzialce()
        self.przetworz_sl_pow_dla_ls()

    @dane_z_bazy
    def przetworz_wszystkie_ls(self):
        # set(LANDID, LANDID), ...
        self.ls = set([x[12]+'.'+self.isNone(x[9])+self.isNone(x[10])
                       for x in self.baza_uzytki if x[9] == 'Ls'])

    @dane_z_bazy
    def przetworz_ls_podwojne(self):
        # [ LANDID, LANDID, ...] w tablicy znajduja sie tylko ls ktore w bazie
        # wystepuja wiecej niz raz na dzialce
        try:
            self.ls_podwojne = [y[0] for y in Counter(
                [x[12]+'.'+self.isNone(x[9])+self.isNone(x[10])
                 for x in self.baza_uzytki if x[9] == 'Ls']).most_common()
                if y[1] > 1]
            return True
        except:  # noqa
            self.ls_podwojne = []
            return False

    @dane_z_bazy
    def przetworz_uzytki(self):
        # {LANDID: [AU, SQ, LANDUSE_AREA, PARCELID, PARCEL_INT_NUM], ...}
        self.uzytki = {x[12]+'.'+self.isNone(x[9])+self.isNone(x[10]):
                       [x[9], self.isNone(x[10]), x[11], x[12], x[6]]
                       for x in self.baza_uzytki}

    @dane_z_bazy
    def przetworz_ile_uzytow_na_dzialce(self):
        # {PARCELID: 1, PARCELID: 2, ...}
        try:
            self.sl_ile_uzytkow_na_dzialce = {x[12]: 0
                                              for x in self.baza_uzytki}
            for x in self.baza_uzytki:
                self.sl_ile_uzytkow_na_dzialce[x[12]] += 1
        except:  # noqa
            self.sl_ile_uzytkow_na_dzialce = {}
            return False

    @dane_z_bazy
    def przetworz_ile_ls_na_dzialce(self):
        # {PARCELID: [V, VI], ...]
        try:
            for x in self.baza_uzytki:
                if x[9] == 'Ls':
                    if x[12] not in self.sl_ls_na_dz:
                        self.sl_ls_na_dz[x[12]] = []
                    self.sl_ls_na_dz[x[12]].append(self.isNone(x[10]))
            return True
        except:  # noqa
            self.sl_ls_na_dz = {}
            return False

    @dane_z_bazy
    def przetworz_sl_pow_dla_ls(self):
        try:
            if len(self.sl_ls_na_dz.keys()) > 0:
                for x in self.baza_uzytki:
                    if x[12] in self.sl_ls_na_dz:
                        if len(self.sl_ls_na_dz[x[12]]) == 1:
                            self.sl_pow_ls_dzkat[x[12]] = [x[11], x[7]]
            return True
        except:  # noqa
            self.sl_pow_ls_dzkat = {}
            return False

    @dane_z_bazy
    def przetworz_dzialki(self):
        self.dz_lesne = set([x[-1] for x in
                             self.baza_uzytki if x[9] == "Ls"])

        self.dzialki = {x[-1]: [x[0], x[1], x[-1], x[7], x[6]]
                        for x in self.baza_uzytki}

        for item in self.baza_wlasnosci:
            wyr1 = item[5] + item[6] + '.'
            if item[7] not in ["", " ", None]:
                wyr1 += item[7] + "."
            wyr1 += item[8]
            # oczysc nazwe wlasciciela z pustych znakow na kocu wiersza
            wlasciciel = item[1].rstrip(' \t\n')

            # dodaj wlasnosci danego wlasciciela do slownika
            if wlasciciel not in self.sl_wlasnosc:
                self.sl_wlasnosc[wlasciciel] = []
            self.sl_wlasnosc[wlasciciel].append(wyr1)

            if wyr1 not in self.sl_kody_wlasciceli_na_dzialce:
                self.sl_kody_wlasciceli_na_dzialce[wyr1] = []
            if item[2] != "":
                if re.search("NIEUSTAL", wlasciciel) or \
                        wlasciciel in ['???', ]:
                    self.sl_kody_wlasciceli_na_dzialce[wyr1].append("OF")
                else:
                    self.sl_kody_wlasciceli_na_dzialce[wyr1].append(item[2])
                    if item[2] == "OP":
                        self.listaOP.append([wlasciciel, wyr1])

        # lista dzialek tylko z wlasnoscia OP
        self.dz_op = [k for k, val in
                      self.sl_kody_wlasciceli_na_dzialce.items()
                      if set(['OP']) == set(val)]

        # lista dzialek ze wlasnosciami
        self.dz_opif = [k for k, val in
                        self.sl_kody_wlasciceli_na_dzialce.items()
                        if set(['OP', 'OF']) == set(val)]

        # lista dzialek tylko z wlasnoscia OF
        self.dz_of = [k for k, val in
                      self.sl_kody_wlasciceli_na_dzialce.items()
                      if set(['OF']) == set(val)]

    def isNone(self, a):
        if a is None:
            return ''
        else:
            return a
