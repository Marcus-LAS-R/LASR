import os
from datetime import datetime
from shutil import copyfile

from PyQt5.QtWidgets import QDialog
from qgis.core import Qgis

from .baza_wrapper import Baza
from .baza_polacz_rejestr import F_COMMUNITY, GRUPA3_DZIECI
from .baza_polacz import _kontrola_duplikatow_wydzieln
from .baza_kontrola_slownikow_wgSULMN import KontrolaSlownikowWiele
from .baza_aktualizuj_strukture_dialog import WyborTrybuAktualizacjiDialog
from .baza_korekta_gmin_dialog import KorektaGminDialog
from .pw import PasekPostepu


# Tabele danych lesnych do migracji - GRUPA3_DZIECI bez f_arod_land_use,
# jedynej z FK do F_PARCEL (dana ewidencyjna, poza zakresem tego skryptu -
# reszta zalezy wylacznie od ARODES_INT_NUM, wiec F_PARCEL/V_ADDRESS nie sa
# tu w ogole potrzebne). F_COMMUNITY nie ma FK z danych lesnych, ale TPU
# wymaga jej obecnosci zeby w ogole otworzyc baze - kopiowana zawsze,
# analogicznie do Laczenie.p_f_community() w baza_polacz.py
TABELE_LESNE = [t for t in GRUPA3_DZIECI if t.klucz != 'f_arod_land_use']

# pelna lista kolumn F_ARODES w nowej strukturze - TEMP_RAPORT nie ma
# odpowiednika w starej strukturze, zostanie automatycznie pominieta przez
# przeciecie kolumn zrodlo/cel (i trafi do raportu jako "kolumna pominieta")
KOLUMNY_ARODES = [
    'ARODES_INT_NUM', 'ADRESS_FOREST', 'ARODES_TYP_CD', 'ORDER_KEY',
    'ADRESS_VALID', 'PROT_INT_NUM', 'TEMP_RAPORT',
]

# kolumny bez odpowiednika w starej strukturze, ktore mimo to maja dostac
# wartosc wyprowadzona z innej (istniejacej w starej strukturze) kolumny -
# patrz instrukcja: "wazne zeby wartosc z VOLUME przeniesc do VOLUME_TEMP"
# (bez korekty przyrostu wieku/pierśnicy/wysokosci - decyzja: zwykle
# kopiowanie, formula korekty w instrukcji oznaczona jako niepewna)
KOLUMNY_WYPROWADZONE = {
    'f_storey_species': [('VOLUME_TEMP', 'VOLUME')],
}


def _koryguj_forme_wlasnosci(adres):
    """Pozycje [11:13] starego ADRESS_FOREST (2 znaki zaraz po pierwszym
    myslniku) to nie GRP tylko 'forma wlasnosci' (04/10/99 w probkach) -
    w nowej strukturze ma zostac bezwarunkowo nadpisana na '10'. Puste
    (rekordy OBREB/L-CTWO bez oddzialu/wydzielenia) zostaja puste -
    weryfikowane na probkach realnych starych baz."""
    if not adres or len(adres) < 13:
        return adres
    if adres[11:13].strip() == '':
        return adres
    return adres[:11] + '10' + adres[13:]


# litera wojewodztwa (COUNTY_L, pierwszy znak ADRESS_FOREST) -> 2-cyfrowy
# kod TERYT wojewodztwa (COUNTY_CD) - ta sama tablica co w
# utworz_baze_z_BDL._SL_WOJ / shp_standard.SL_WOJ, zduplikowana tutaj
# (mala prywatna stala, zgodnie z konwencja projektu)
_SL_WOJ_ODWROTNA = {
    "D": "02", "C": "04", "L": "06", "F": "08", "E": "10", "K": "12",
    "W": "14", "O": "16", "R": "18", "B": "20", "G": "22", "S": "24",
    "T": "26", "N": "28", "P": "30", "Z": "32",
}


def _koryguj_municip(adres, korekty_gmin):
    """Pozycje [3:6] ADRESS_FOREST to MUNICIPALITY_CD (3 znaki) - jesli
    trojka (COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD) odczytana z adresu
    jest w korekty_gmin (recznie ustalone w sprawdz_gminy()), podmienia na
    poprawiony kod. COUNTY_CD wyliczany z litery na pozycji [0] przez
    _SL_WOJ_ODWROTNA."""
    if not adres or len(adres) < 6 or not korekty_gmin:
        return adres
    county = _SL_WOJ_ODWROTNA.get(adres[0:1])
    if county is None:
        return adres
    trojka = (county, adres[1:3], adres[3:6])
    nowy_municip = korekty_gmin.get(trojka)
    if nowy_municip is None:
        return adres
    return adres[:3] + nowy_municip + adres[6:]


class KopiaStrukturalna:
    """Kopiuje dane lesne (F_COMMUNITY + F_ARODES + TABELE_LESNE) z jednej
    bazy o starej strukturze do jednej juz istniejacej bazy o nowej strukturze,
    remapujac ARODES_INT_NUM zeby uniknac kolizji z tym, co juz jest w
    docelowej. Schema-aware: kopiowane sa tylko kolumny istniejace
    jednoczesnie w zrodle i w docelowej - kolumny nowe (bez odpowiednika w
    zrodle) zostaja NULL/domyslne w docelowej, chyba ze sa pokryte przez
    KOLUMNY_WYPROWADZONE."""

    def __init__(self, baza0, baza, korekty_gmin=None):
        self.baza0 = baza0  # baza docelowa (nowa struktura)
        self.baza = baza  # baza zrodlowa (stara struktura)
        # {(COUNTY_CD, DISTRICT_CD, stary_MUNICIPALITY_CD): nowy_MUNICIPALITY_CD}
        # - reczne korekty ustalone w AktualizujStruktureBazy.sprawdz_gminy()
        self.korekty_gmin = korekty_gmin or {}

        self.maxint = -1
        self.maxspecstor = -1
        self.maxset = -1
        self.maxdamage = -1

        self.sl_arodes = {}
        self.l_bledy_wpisu = []  # (tabela, opis_wiersza, blad)
        self.l_bledy_odczytu = []  # (baza_sc, tabela, blad)
        self.l_kolumny_pominiete = {}  # {tabela: [kolumna, ...]}

    def p_f_max(self):
        self.maxint = self._max('F_ARODES', 'ARODES_INT_NUM', self.maxint)
        self.maxspecstor = self._max(
            'F_STOREY_SPECIES', 'SPEC_STOR_INT_NUM', self.maxspecstor)
        self.maxset = self._max('F_SET', 'SET_INT_NUM', self.maxset)
        self.maxdamage = self._max(
            'F_AROD_DAMAGE', 'damage_int_num', self.maxdamage)

    def _max(self, tabela, pole, domyslnie):
        wynik = self.baza0.pobierz(
            'select max(' + pole + ') from ' + tabela + ';')
        if wynik is not False and wynik[0][0] is not None:
            return wynik[0][0]
        return domyslnie

    def _wspolne_kolumny(self, tabela, kolumny_docelowe):
        """Zwraca podzbior kolumny_docelowe realnie istniejacy w tabeli
        zrodlowej (zachowujac kolejnosc kolumny_docelowe), zapisujac
        brakujace do l_kolumny_pominiete."""
        dostepne = self.baza.kolumny_tabeli(tabela)
        if dostepne is False:
            self.l_bledy_odczytu.append(
                (self.baza.baza, tabela,
                 'Nie udalo sie odczytac struktury tabeli'))
            return []
        wspolne = [k for k in kolumny_docelowe if k in dostepne]
        pominiete = [k for k in kolumny_docelowe if k not in dostepne]
        if pominiete:
            self.l_kolumny_pominiete[tabela] = pominiete
        return wspolne

    def p_f_community(self):
        """Kopiuje F_COMMUNITY (slownik miejscowosci) - TPU wymaga jej
        obecnosci zeby w ogole otworzyc baze, mimo ze dane lesne nie maja
        do niej FK. Dedup po kluczu naturalnym (COUNTY_CD, DISTRICT_CD,
        MUNICIPALITY_CD, COMMUNITY_CD), analogicznie do
        Laczenie.p_f_community() w baza_polacz.py."""
        kolumny = self._wspolne_kolumny('F_COMMUNITY', F_COMMUNITY.kolumny)
        if not kolumny:
            return

        idx_klucz = [kolumny.index(k) for k in
                     ('COUNTY_CD', 'DISTRICT_CD', 'MUNICIPALITY_CD',
                      'COMMUNITY_CD') if k in kolumny]
        i_county = kolumny.index('COUNTY_CD') if 'COUNTY_CD' in kolumny else None
        i_district = kolumny.index('DISTRICT_CD') if 'DISTRICT_CD' in kolumny else None
        i_municip = kolumny.index('MUNICIPALITY_CD') if 'MUNICIPALITY_CD' in kolumny else None

        def klucz(w):
            return tuple(w[i] for i in idx_klucz)

        sql = 'select ' + ', '.join(kolumny) + ' from F_COMMUNITY;'
        org = self.baza0.pobierz(sql)
        zrd = self.baza.pobierz(sql)
        if org is False:
            self.l_bledy_odczytu.append(
                (self.baza0.baza, 'F_COMMUNITY',
                 'Nie udalo sie odczytac tabeli (baza docelowa)'))
            org = []
        if zrd is False:
            self.l_bledy_odczytu.append(
                (self.baza.baza, 'F_COMMUNITY',
                 'Nie udalo sie odczytac tabeli (baza zrodlowa)'))
            zrd = []

        istniejace = {klucz(w) for w in org}
        for w in zrd:
            w = list(w)
            if (self.korekty_gmin and i_county is not None and
                    i_district is not None and i_municip is not None):
                trojka = (w[i_county], w[i_district], w[i_municip])
                nowy_municip = self.korekty_gmin.get(trojka)
                if nowy_municip is not None:
                    w[i_municip] = nowy_municip

            if klucz(w) in istniejace:
                continue
            istniejace.add(klucz(w))

            nag = [k for k, v in zip(kolumny, w) if v is not None]
            its = [v for v in w if v is not None]
            sql_ins = ('insert into F_COMMUNITY (' + ','.join(nag) +
                       ') values (' + ','.join(['?'] * len(its)) + ');')
            opis = 'klucz=' + str(klucz(w))
            try:
                self.baza0.cur.execute(sql_ins, its)
                self.baza0.con.commit()
            except Exception as e:
                self.l_bledy_wpisu.append(('F_COMMUNITY', opis, str(e)))

    def p_f_arodes(self):
        kolumny = self._wspolne_kolumny('F_ARODES', KOLUMNY_ARODES)
        if not kolumny:
            return
        sql = ('select ' + ', '.join(kolumny) +
               ' from F_ARODES order by ARODES_INT_NUM asc;')
        wiersze = self.baza.pobierz(sql)
        if wiersze is False:
            self.l_bledy_odczytu.append(
                (self.baza.baza, 'F_ARODES', 'Nie udalo sie odczytac tabeli'))
            return

        i_arodes = kolumny.index('ARODES_INT_NUM')
        i_adres = kolumny.index('ADRESS_FOREST') if 'ADRESS_FOREST' in kolumny else None

        for w in wiersze:
            stary = w[i_arodes]
            self.maxint += 1
            nowy = self.maxint
            self.sl_arodes[stary] = nowy

            nag, its = [], []
            for i, kolumna in enumerate(kolumny):
                wartosc = w[i]
                if i == i_arodes:
                    wartosc = nowy
                elif i_adres is not None and i == i_adres and wartosc:
                    wartosc = _koryguj_municip(wartosc, self.korekty_gmin)
                    wartosc = _koryguj_forme_wlasnosci(wartosc)
                if wartosc is None:
                    continue
                nag.append(kolumna)
                its.append(wartosc)

            sql_ins = ('insert into F_ARODES (' + ','.join(nag) +
                       ') values (' + ','.join(['?'] * len(its)) + ');')
            opis = ('ADRESS_FOREST=' + str(w[i_adres]) if i_adres is not None
                    else 'ARODES_INT_NUM(stary)=' + str(stary))
            try:
                self.baza0.cur.execute(sql_ins, its)
                self.baza0.con.commit()
            except Exception as e:
                self.l_bledy_wpisu.append(('F_ARODES', opis, str(e)))

    def p_tabele(self):
        for t in TABELE_LESNE:
            self._kopiuj_dziecko(t)

    def _kopiuj_dziecko(self, t):
        kolumny = self._wspolne_kolumny(t.nazwa, t.kolumny)
        if not kolumny:
            return

        wyprowadzone = [
            (nowa, zrodlowa) for nowa, zrodlowa
            in KOLUMNY_WYPROWADZONE.get(t.klucz, [])
            if zrodlowa in kolumny and nowa not in kolumny
        ]
        if wyprowadzone and t.nazwa in self.l_kolumny_pominiete:
            pokryte = {nowa for nowa, _ in wyprowadzone}
            self.l_kolumny_pominiete[t.nazwa] = [
                k for k in self.l_kolumny_pominiete[t.nazwa]
                if k not in pokryte]
            if not self.l_kolumny_pominiete[t.nazwa]:
                del self.l_kolumny_pominiete[t.nazwa]

        sql = 'select ' + ', '.join(kolumny) + ' from ' + t.nazwa + ';'
        wiersze = self.baza.pobierz(sql)
        if wiersze is False:
            self.l_bledy_odczytu.append(
                (self.baza.baza, t.nazwa, 'Nie udalo sie odczytac tabeli'))
            return

        idx = {k: i for i, k in enumerate(kolumny)}
        fk_arodes = next(
            (f for f in t.fk if f.slownik == 'sl_arodes'), None)

        for row in wiersze:
            nag, its, pomin = [], [], False
            for kolumna, wartosc in zip(kolumny, row):
                if kolumna == t.wlasny_klucz:
                    continue
                if fk_arodes is not None and kolumna == fk_arodes.kolumna:
                    if wartosc not in self.sl_arodes:
                        pomin = True
                        break
                    nag.append(kolumna)
                    its.append(self.sl_arodes[wartosc])
                elif wartosc is not None:
                    nag.append(kolumna)
                    its.append(wartosc)

            if pomin:
                continue

            for nowa, zrodlowa in wyprowadzone:
                wartosc = row[idx[zrodlowa]]
                if wartosc is not None:
                    nag.append(nowa)
                    its.append(wartosc)

            if t.wlasny_klucz:
                nowy = getattr(self, t.wlasny_klucz_licznik) + 1
                setattr(self, t.wlasny_klucz_licznik, nowy)
                nag.append(t.wlasny_klucz)
                its.append(nowy)

            sql_ins = ('insert into ' + t.nazwa + ' (' + ','.join(nag) +
                       ') values (' + ','.join(['?'] * len(its)) + ');')
            opis = ','.join(n + '=' + str(v) for n, v in zip(nag, its))
            try:
                self.baza0.cur.execute(sql_ins, its)
                self.baza0.con.commit()
            except Exception as e:
                self.l_bledy_wpisu.append((t.nazwa, opis, str(e)))


class AktualizujStruktureBazy:
    def __init__(self, iface):
        self.iface = iface
        self.lista = []  # sciezki do starych baz w wybranym katalogu
        self.tryb = None  # 'polacz' | 'szablon'
        self.cel_lub_szablon = None
        self.folder_wyjsciowy = None  # tylko tryb 'szablon'
        # {(COUNTY_CD, DISTRICT_CD, stary_MUNICIPALITY_CD): nowy_MUNICIPALITY_CD}
        # - wypelniane przez sprawdz_gminy(), przekazywane do KopiaStrukturalna
        self.korekty_gmin = {}
        self.postep = PasekPostepu(self.iface).stworz_pasek(
            'Aktualizacja struktury bazy')
        self.postep.setValue(0)

    def wybierz_katalog_i_tryb(self):
        dlg = WyborTrybuAktualizacjiDialog(self.iface)
        if dlg.exec_() != QDialog.Accepted:
            return False
        self.lista, self.tryb, self.cel_lub_szablon, self.folder_wyjsciowy = \
            dlg.wybor()

        self.iface.messageBar().pushMessage(
            'Aktualizuj strukturę bazy',
            'Znaleziono ' + str(len(self.lista)) + ' starych baz.',
            Qgis.Info, 10)
        return True

    def sprawdz_gminy(self):
        """Sprawdza, czy trójki (COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD) z
        F_COMMUNITY starych baz istnieją w słowniku F_MUNICIPALITY bazy
        docelowej/szablonu (self.cel_lub_szablon). Jeśli nie - pokazuje
        dialog ręcznej korekty i zapisuje wybór w self.korekty_gmin. Zwraca
        False jeśli nie udało się odczytać słownika albo użytkownik
        zrezygnował z korekty."""
        slownik = Baza(self.cel_lub_szablon)
        if not slownik.polacz():
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się połączyć z bazą docelową/szablonem, żeby '
                'sprawdzić słownik gmin (F_MUNICIPALITY).',
                Qgis.Critical, 0)
            return False

        gminy_sql = slownik.pobierz(
            'select COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD '
            'from F_MUNICIPALITY;')
        slownik.zamknij()
        if gminy_sql is False:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się odczytać słownika F_MUNICIPALITY z bazy '
                'docelowej/szablonu.', Qgis.Critical, 0)
            return False
        gminy_valid = {tuple(w) for w in gminy_sql}

        niepasujace = {}
        for stara_sc in self.lista:
            stara = Baza(stara_sc)
            if not stara.polacz():
                continue
            wiersze = stara.pobierz(
                'select COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, '
                'COMMUNITY_NAME from F_COMMUNITY;')
            stara.zamknij()
            if wiersze is False:
                continue
            for county, district, municip, nazwa in wiersze:
                klucz = (county, district, municip)
                if klucz not in gminy_valid:
                    niepasujace.setdefault(klucz, set()).add(
                        nazwa or '(brak nazwy)')

        if not niepasujace:
            return True

        dlg = KorektaGminDialog(self.iface, niepasujace, gminy_valid)
        if dlg.exec_() != QDialog.Accepted:
            return False
        self.korekty_gmin = dlg.wybor()
        return True

    def uruchom(self):
        if self.tryb == 'polacz':
            return self._uruchom_polacz()
        return self._uruchom_szablon()

    def _uruchom_polacz(self):
        katalog = self.folder_wyjsciowy
        sciezki = self.lista + [self.cel_lub_szablon]
        duplikaty, rap_sc = _kontrola_duplikatow_wydzieln(katalog, sciezki)
        if duplikaty:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Znaleziono ' + str(len(duplikaty)) + ' zdublowanych '
                'wydzieleń (uwzględniając szablon) - aktualizacja '
                'przerwana. Raport: ' + rap_sc,
                Qgis.Critical, 0)
            return False

        czas = datetime.now().isoformat().replace(':', '')[:-7]
        plikn = ('baza_zaktualizowana_' + czas +
                 os.path.splitext(self.cel_lub_szablon)[1])
        docelowa_sc = os.path.join(katalog, plikn)
        try:
            copyfile(self.cel_lub_szablon, docelowa_sc)
        except Exception:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się skopiować szablonu do folderu eksportu, '
                'masz prawa dostępu do zapisu?', Qgis.Critical, 0)
            return False

        baza0 = Baza(docelowa_sc)
        if not baza0.polacz():
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się podłączyć do skopiowanego szablonu',
                Qgis.Critical, 0)
            return False

        bledy_wszystkie = []
        kolumny_pominiete = {}
        proc = int(90 / len(self.lista))
        ust = 5
        for stara_sc in self.lista:
            ust += proc
            self.postep.setValue(ust)
            stara = Baza(stara_sc)
            if stara.polacz():
                k = KopiaStrukturalna(baza0, stara, self.korekty_gmin)
                k.p_f_max()
                k.p_f_community()
                k.p_f_arodes()
                k.p_tabele()
                self._zbierz_wyniki(
                    k, stara_sc, bledy_wszystkie, kolumny_pominiete)
                stara.zamknij()
            else:
                bledy_wszystkie.append(
                    (stara_sc, '(połączenie)', '',
                     'Nie udało się połączyć ze starą bazą'))

        baza0.zamknij()
        self.postep.setValue(100)
        self._zakoncz(katalog, [docelowa_sc], bledy_wszystkie, kolumny_pominiete)
        return True

    def _uruchom_szablon(self):
        katalog = self.folder_wyjsciowy
        czas = datetime.now().isoformat().replace(':', '')[:-7]
        rozszerzenie = os.path.splitext(self.cel_lub_szablon)[1]

        wynikowe = []
        bledy_wszystkie = []
        kolumny_pominiete = {}
        proc = int(90 / len(self.lista))
        ust = 5
        for stara_sc in self.lista:
            ust += proc
            self.postep.setValue(ust)

            nazwa_bazowa = os.path.splitext(os.path.basename(stara_sc))[0]
            plikn = nazwa_bazowa + '_nowa_struktura_' + czas + rozszerzenie
            docelowa_sc = os.path.join(katalog, plikn)
            try:
                copyfile(self.cel_lub_szablon, docelowa_sc)
            except Exception:
                bledy_wszystkie.append(
                    (stara_sc, '(kopiowanie szablonu)', '',
                     'Nie udało się skopiować szablonu'))
                continue

            baza0 = Baza(docelowa_sc)
            if not baza0.polacz():
                bledy_wszystkie.append(
                    (stara_sc, '(połączenie)', '',
                     'Nie udało się podłączyć do skopiowanego szablonu'))
                continue

            stara = Baza(stara_sc)
            if stara.polacz():
                k = KopiaStrukturalna(baza0, stara, self.korekty_gmin)
                k.p_f_max()
                k.p_f_community()
                k.p_f_arodes()
                k.p_tabele()
                self._zbierz_wyniki(
                    k, stara_sc, bledy_wszystkie, kolumny_pominiete)
                stara.zamknij()
            else:
                bledy_wszystkie.append(
                    (stara_sc, '(połączenie)', '',
                     'Nie udało się połączyć ze starą bazą'))

            baza0.zamknij()
            wynikowe.append(docelowa_sc)

        self.postep.setValue(100)
        self._zakoncz(katalog, wynikowe, bledy_wszystkie, kolumny_pominiete)
        return True

    def _zbierz_wyniki(self, k, stara_sc, bledy_wszystkie, kolumny_pominiete):
        for tabela, opis_wiersza, blad in k.l_bledy_wpisu:
            bledy_wszystkie.append((stara_sc, tabela, opis_wiersza, blad))
        for baza_sc, tabela, blad in k.l_bledy_odczytu:
            bledy_wszystkie.append(
                (baza_sc, tabela, '(cała tabela - błąd odczytu)', blad))
        for tabela, kolumny in k.l_kolumny_pominiete.items():
            kolumny_pominiete.setdefault(tabela, set()).update(kolumny)

    def _zakoncz(self, katalog, pliki_wynikowe, bledy, kolumny_pominiete):
        self.iface.messageBar().clearWidgets()

        rap_sc = self._zapisz_raport(katalog, bledy, kolumny_pominiete)

        if bledy:
            self.iface.messageBar().pushMessage(
                'ZAKTUALIZOWANO Z BŁĘDAMI',
                'Zakończono, ale wystąpiło ' + str(len(bledy)) +
                ' błędów odczytu/zapisu. Raport: ' + rap_sc,
                Qgis.Warning, 0)
        else:
            self.iface.messageBar().pushMessage(
                'ZAKTUALIZOWANO',
                'Zaktualizowano strukturę ' + str(len(self.lista)) +
                ' baz(y) pomyślnie. Raport: ' + rap_sc,
                Qgis.Success, 0)

        if not pliki_wynikowe:
            return

        ile_blednych, rap_slow = KontrolaSlownikowWiele(katalog, pliki_wynikowe)
        if ile_blednych > 0:
            self.iface.messageBar().pushMessage(
                'Kontrola słownikowa',
                'W bazach wynikowych znaleziono ' + str(ile_blednych) +
                ' wartości spoza nowych słowników. Raport: ' + rap_slow,
                Qgis.Warning, 0)
        else:
            self.iface.messageBar().pushMessage(
                'Kontrola słownikowa',
                'Bazy wynikowe zgodne ze słownikiem, raport: ' + rap_slow,
                Qgis.Success, 10)

    def _zapisz_raport(self, katalog, bledy, kolumny_pominiete):
        czas = datetime.now().isoformat().replace(':', '')[:-7]
        rap_sc = os.path.join(
            katalog, 'raport_aktualizacji_struktury_' + czas + '.txt')

        with open(rap_sc, 'w', encoding='utf-8') as plik:
            plik.write('AKTUALIZACJA STRUKTURY BAZ - RAPORT\r\n')
            plik.write('=' * 72 + '\r\n\r\n')

            if kolumny_pominiete:
                plik.write(
                    'Kolumny bez odpowiednika w źródle (pozostały puste w '
                    'bazach wynikowych):\r\n')
                for tabela, kolumny in kolumny_pominiete.items():
                    plik.write(
                        '  ' + tabela + ': ' + ', '.join(sorted(kolumny)) +
                        '\r\n')
                plik.write('\r\n')

            if bledy:
                plik.write('BŁĘDY:\r\n\r\n')
                for baza_sc, tabela, opis_wiersza, blad in bledy:
                    plik.write('Baza źródłowa: ' + baza_sc + '\r\n')
                    plik.write('Tabela:        ' + tabela + '\r\n')
                    plik.write('Wiersz:        ' + opis_wiersza + '\r\n')
                    plik.write('Błąd:          ' + blad + '\r\n\r\n')

        return rap_sc


def uruchom(iface):
    p = AktualizujStruktureBazy(iface)
    if p.wybierz_katalog_i_tryb():
        if p.sprawdz_gminy():
            p.uruchom()
