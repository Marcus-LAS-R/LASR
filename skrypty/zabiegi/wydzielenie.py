from typing import Union
from .baza_zabiegi_sl import ZabiegiSlownik
from .wpisz import Wpisz
from .wygeneruj import Generuj
from .sprawdz import Sprawdz


class Wydzielenie(ZabiegiSlownik, Wpisz, Generuj, Sprawdz):
    def __init__(self):
        # wczytaj wpisy i slowniki
        self.spisy()

    def przygotuj_strukture(self, aid: int) -> None:
        # modyfikator dodawany przy obliczaniu % trzebiezy (int)
        self.mod_trzeb = 0
        self.wybor = 'Spr'  # przeazanie z klasy głównej

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
        self.cel_hod = 0  # ile jest wpisanych celów hodowl w wydzieleniu

        # czy poprawna bonitacja, jeżeli IA wpisane gdzie indziej niz przy
        # sosnie to wtedy True
        self.bonitacja_flag = False

        # dane rebni wpisanej do bazy przez taksatora
        self.reb = ''
        self.ile_reb = 0
        self.pow_reb = 0
        self.proc_reb = 0

        # dane rebni wygeneowanej przez skrypt
        self.gen_reb = ''
        self.gen_pow_reb = 0
        self.gen_proc_reb = 0

        # wersja dla janczulewicza - tylko rebnia IB
        self.janczulewicz = False

        self.gat_gl = ''
        self.struk = ''
        self.zadrzew = 0
        self.luki = 0
        self.ile_dzkat = 0
        self.gat_gl_wiek = 0
        self.gat_gl_udz = 0
        self.gat_gl_vol = 0
        self.gat_gl_bhd = 0
        # opisy dla poszczególnych gat z piętra drzew, IP, IIP
        self.drzew_gat = []

        # ostatnia wartość z jaką coś jest wpisane do bazy
        self.max_cue = 0
        # ile w wydz jest przeznaczone do wyciecia, nie przeliczona na 1 ha!!!
        self.sum_cue_volume = 0

        self.pow_wydz = 0.0
        # sprawdz czy wpisany zabieg nie ma zerowerj powierzchni...
        self.zerowa_powierzchnia = False

        self.wiekRebSl = {}  # slownik z bazy z rokiem rebnosci dla poszcz gat.
        self.wiekReb = 120  # wiek rebności standardowo ustawiamy na 120 lat
        self.przest_vol = 0
        self.przest_pozyskanie = 0  # ile przeznaczone jest do pozyskania
        self.mlode_pozyskanie = 0  # pozyskanie z TP, TW, CPP
        self.plaz_vol = 0
        self.brak_zad = False
        self.zwarcie = ''
        self.trzebiez = False  # flaga do sprawdzenia luk na trzebiezach
        self.uszk = ''  # stopien uszkodzenia d-stanu
        self.pokrywa = ''
        self.uw_dopisz = ''  # string z uwagami do dopisania do f_subarea
        self.uw_raport = []  # tablica z uwagami do raportu
        self.uw_baza = []  # tablica z uw. z wpisywana do bazy...
        self.uwagi = ''  # strz uwagami w bazie+uzup, max dł 255 znaków!!!
        self.uwagi_org = ''  # strz uwagami w bazie, max dł 255 znaków!!!

        # tabela z wygenerowanymi zabiegami w postaci:
        # [[zab: pow], ...] kolejnosc ma znaczenie!
        self.zabiegi = []

        # tab z wpisanymi zabiegami przez taksatorow, brak kolejnosci zabiegow
        self.cue = {}
        self.zdublowane_cue = []  # lista podwojnych wskazowek w bazie
        # potrzebna jest zmiana str na KO bo podr+nalot>0.49
        self.zmien_na_ko = False

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

    def dodaj_mod_trzeb(self, mod):
        """dodaje modyfikator trzebiezy"""
        if isinstance(mod, int):
            self.mod_trzeb = mod

    def dodaj_baze(self, baza):
        ''' jezeli bedzie potrzeba dodawania poprawek badz nowych wpisow do
        bazy nalezy poddac wskaznik do obiektu z podłączoną baza.
        '''
        try:
            if baza.polacz():
                self.baza = baza
                return True
        except Exception:
            return False

    def o_wiek_rebnosci(self, sl: dict) -> None:
        """ Odczytaj wiek rebności z pobranego sl
            Wynik działania Baza.pobierz_wiek_reb()
        """
        if sl:
            self.wiekRebSl = sl
        else:
            try:
                self.wiekRebSl = self.baza.pobierz_wiek_reb()
            except Exception:
                return

        # Pobierz wiek rebnosci dla gatunku głównego
        if self.gat_gl != '':
            _wiekReb = self.isNone(self.wiekRebSl[self.gat_gl])
            if _wiekReb > 0:
                self.wiekReb = _wiekReb

    def o_pod_nal(self, tab: list) -> None:
        """Odczytaj podrost i nalot z bazy
        Szczegóły w Baza.pobierz_do_zab()
        """
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

    def o_ist_zab(self, tab: list) -> None:
        for t in tab:
            if t[1] in self.cue:
                self.zdublowane_cue.append(t[1])
            else:
                # typ_zab: pow zab
                self.cue[t[1]] = t[2]

            if self.max_cue < t[3]:
                self.max_cue = t[3]

            if t[1].upper() in self.rebnieSpis:
                if t[1] != t[1].upper():
                    self.popraw_rebnie
                self.proc_reb = float(self.isNone(t[5]))
                if self.proc_reb == 0:
                    self.proc_reb = float(self.isNone(t[4]))
                self.reb = t[1].upper()
                self.pow_reb = self.isNone(t[2])
                self.ile_reb += 1
                if t[2] == 0:
                    self.zerowa_powierzchnia = True
                if isinstance(t[6], int):
                    self.sum_cue_volume += t[6]

            if t[1].upper() == 'PRZEST':
                if isinstance(t[6], int):
                    self.przest_pozyskanie += t[6]

            if t[1].upper() == 'ZADRZEW':
                if isinstance(t[6], int):
                    self.przest_pozyskanie += t[6]

            if t[1].upper() in ['TP', 'TW', 'CP-P']:
                if str(t[6]).isdigit():
                    self.mlode_pozyskanie += t[6]

    def o_przest(self, tab: list) -> None:
        if len(tab) > 0:
            self.przes = True

    def o_gat_gl(self, tab: list) -> None:
        if not isinstance(tab, list):
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

    def o_szczeg_wydz(self, tab: list) -> None:
        if len(tab) > 0:
            self.pow_wydz = round(self.isNone(tab[0][3]), 4)
            self.typ = tab[0][1]
            self.stl = tab[0][2]
            self.opis = tab[0][4]
            self.struk = self.isNoneT(tab[0][5])
            self.uszk = self.isNoneT(tab[0][6])
            self.uwagi = self.isNoneT(tab[0][7])
            self.uwagi_org = self.isNoneT(tab[0][7])
            self.pokrywa = self.isNoneT(tab[0][8])

    def o_luki(self, tab: list) -> None:
        if len(tab) > 0:
            self.luki = tab[0][2]

    def o_przest_vol(self, tab: list) -> None:
        if len(tab) > 0:
            for t in tab:
                if t[6] == 'PRZES':
                    self.przest_vol += self.isNone(t[5])
                else:
                    self.plaz_vol += self.isNone(t[5])

    def o_dzkat(self, tab: list) -> None:
        if not isinstance(tab, type([])):
            return
        self.ile_dzkat = tab[0][0]

    def o_cel_hod(self, tab):
        if not isinstance(tab, type([])):
            return
        self.cel_hod = tab[0][0]

    def o_opis_drzew(self, tab):
        if not isinstance(tab, list):
            return
        for row in tab:
            # row = [species_cd, bonintacja, udzial, wiek, piers, wys, vol]
            # sprawdz czy wpisana bon IA jest poprawna
            if row[0] != 'SO' and row[1] in ['IA', 'IB']:
                self.bonitacja_flag = True
            self.drzew_gat.append(list(row))

    def odczytaj_dane_z_bazy(self, tab: list) -> bool:
        """Metoda wczytuje podane przez użytkownika dane w postaci tablicy z
        bazy danych z metody pobierz do zab, i wczytuje wartości do zmiennych.
        """
        try:
            self.o_pod_nal(tab[0])
            self.o_ist_zab(tab[1])
            self.o_gat_gl(tab[2])
            self.o_przest(tab[3])
            self.o_szczeg_wydz(tab[4])
            self.o_przest_vol(tab[5])
            self.o_luki(tab[6])
            self.o_dzkat(tab[7])
            self.o_cel_hod(tab[8])
            self.o_opis_drzew(tab[9])
            return True
        except Exception:
            self.uw_raport.append(
                'Problem przy wczytywaniu wydzielenia! (o co lotto?)'
            )
            return False

    def oblicz_wpisane_zab(self, tab: list) -> Union[list, list]:
        # Potrzebne toto jest wogóle???
        zwrot = []
        niewiadomo = []
        for it in tab:
            if 'ODN-ZRB' in tab and it in ['PIEL', 'ODN-ZRB', 'AGROT']:
                zwrot.append([it, self.pow_wydz])
            elif 'ODN-ZŁOŻ' in tab and it in ['PIEL', 'ODN-ZŁOŻ', 'AGROT']:
                np_sum = self.nal + self.podr + self.pods
                odn_cz = 0
                if np_sum > 0.1:
                    odn_cz = np_sum - 0.1
                # oblicz pow odnowienia dla rebni cz
                pow_odn = round(
                    (self.proc_reb/100)*self.pow_wydz*(1-odn_cz), 4)
                zwrot.append([it, pow_odn])
            else:
                niewiadomo.append(it)
        return niewiadomo, zwrot
