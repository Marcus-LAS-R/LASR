"""Silnik konwersji PUL -> UPUL.

Reużywa Laczenie (baza_polacz.py) do kopiowania F_PARCEL/V_ADDRESS/
GRUPA2_DZIECI/GRUPA3_DZIECI - schemat tych tabel jest niemal identyczny w
PUL i UPUL i nie dotyczy ich problem RDLP-vs-TERYT (kody TERYT w F_PARCEL
źródła PUL są już poprawne). Jedyny naprawdę nowy element to F_ARODES/
F_COMMUNITY, budowane tu wprost z adresu wyznaczonego geometrycznie
(core/spatial_match.py), zamiast kopiowania ADRESS_FOREST/F_COMMUNITY
wprost ze źródła PUL.

Wypełnia bezpośrednio wewnętrzne bufory obiektu Laczenie (f_arodes,
sl_arodes, f_community_nowe) w formacie, którego oczekuje jej już
istniejąca, przetestowana Laczenie.d_tabele() - dzięki temu zapis do bazy
wynikowej (F_ARODES/F_COMMUNITY/F_PARCEL/V_ADDRESS/wszystkie tabele-dzieci
z remapem FK) korzysta w całości z tego samego, sprawdzonego kodu co
"Połącz bazy TPU", bez duplikowania go.
"""

import copy

from ...baza_polacz import Laczenie
from ...baza_polacz_rejestr import (
    F_COMMUNITY, F_PARCEL_NADRZEDNA, V_ADDRESS_NADRZEDNA)
from ...baza_dopisz_wydz import DopiszWydzielenia
from ...aktualizacja_upul.core.shp_standard import SL_WOJ

from .adres import zbuduj_adres_upul

# forma wlasnosci (GRP, pozycje [11:13] adresu UPUL) - zawsze "10",
# niezaleznie od zrodla; ten sam nieuwarunkowany domyslny wybor co
# baza_aktualizuj_strukture._koryguj_forme_wlasnosci przy migracji
# starej struktury UPUL na nowa (brak innego wiarygodnego zrodla tej
# wartosci z bazy PUL)
_GRP_DOMYSLNE = '10'

# PUL nie prowadzi V_ADDRESS/V_PARCEL_PARTICIPATION (dane właściciela
# prywatnego) - właścicielem lasów zarządzanych przez Lasy Państwowe jest
# zawsze Skarb Państwa, więc wpisywany jest na sztywno, ze 100% udziałem
# (part_numerator=1/part_denominator=1) w każdej skopiowanej działce -
# patrz _wpisz_wlasciciela()
_WLASCICIEL = 'Skarb Państwa'

# tabele bez odpowiednika w PUL, obsłużone poza generycznym mechanizmem
# kopiowania (V_ADDRESS/V_PARCEL_PARTICIPATION - syntetyzowane, patrz
# _wpisz_wlasciciela; F_AROD_DAMAGE - świadomie pominięte, brak
# odpowiednika 1:1 w PUL, dane o uszkodzeniach są tam rozproszone
# inaczej - decyzja użytkownika 2026-08-24) - generyczny odczyt
# (_wspolne_kolumny) je pomija BEZ zgłaszania błędu, żeby raport nie
# sugerował awarii tam, gdzie nic się nie zepsuło; raport.py opisuje je
# osobno, informacyjnie
_TABELE_ZNANE_BRAKI = {'V_ADDRESS', 'V_PARCEL_PARTICIPATION', 'F_AROD_DAMAGE'}

# indeksy w .kolumny, na ktorych opieraja sie indeks_klucza/
# funkcja_klucza_dedup tych dwoch definicji (patrz _definicja_filtrowana) -
# musza przetrwac filtrowanie kolumn do przeciecia ze schematem PUL na
# swoich oryginalnych pozycjach, inaczej dedup/remap zaczalby po cichu
# porownywac/indeksowac zle kolumny
_KRYTYCZNE_F_PARCEL = range(6)   # PARCEL_INT_NUM..COMMUNITY_CD
_KRYTYCZNE_V_ADDRESS = range(1)  # ADDR_NR

# {nazwa_docelowa_UPUL: nazwa_zrodlowa_PUL} - tabele o innej nazwie w PUL
# niz w szablonie UPUL (GRUPA2_DZIECI/GRUPA3_DZIECI/*_NADRZEDNA sa
# zdefiniowane pod nazwami UPUL) - insert zawsze pod nazwa_docelowa (nie
# wolno zmieniac struktury szablonu), tylko ODCZYT ze zrodla idzie pod
# ta alternatywna nazwa. Zweryfikowane na materialy/PUL: F_AROD_SPECIALAREA
# (PUL) ma dokladnie ten sam zestaw kolumn co f_arod_spec_area (UPUL).
_ALIASY_TABEL_PUL = {
    'f_arod_spec_area': 'F_AROD_SPECIALAREA',
}


def _nazwa_zrodlowa(nazwa_docelowa):
    return _ALIASY_TABEL_PUL.get(nazwa_docelowa, nazwa_docelowa)


class KopiaPULdoUPUL:
    def __init__(self, baza0, baza_pul):
        self.baza0 = baza0        # baza docelowa UPUL (kopia szablonu/istniejąca)
        self.baza_pul = baza_pul  # baza źródłowa PUL

        self.laczenie = Laczenie(baza0, baza_pul)

        # helper wyłącznie po to, żeby reużyć stworz_ops_obrebu/lctwa/oddz/
        # wydz (budują wiersze OBRĘB/L-CTWO/ODDZ/WYDZIEL z gotowego
        # 25-znakowego adresu WYDZIEL) - te metody nie dotykają iface/
        # wydz/baza, tylko self.sl_woj (litera województwa -> kod TERYT)
        self._hierarchia = DopiszWydzielenia(iface=None)
        self._adresy_juz_wpisane = set()

        self.l_bez_adresu = []  # (oddz, wydz, powod) - PUL nie do sparsowania
        self.l_kolumny_pominiete = {}  # {tabela: {kolumna, ...}}

        # definicje F_PARCEL_NADRZEDNA/V_ADDRESS_NADRZEDNA przefiltrowane
        # do schematu źródła PUL - ustawiane w p_pozostale_nadrzedne(),
        # używane też w d_tabele() (muszą być te same przy odczycie i
        # zapisie, patrz komentarz w p_pozostale_nadrzedne())
        self._f_parcel = None
        self._v_address = None

        # wynik _wpisz_wlasciciela(), do jasnego opisu w raporcie (patrz
        # _TABELE_ZNANE_BRAKI) zamiast cichego domysu z sl_arodes/pustych list
        self.wlasciciel_wpisany = False
        self.l_wlasciciel_udzialy = 0

    # --- properties: przekierowanie do stanu Laczenie, żeby wywołujący
    # (raport, orkiestrator) nie musiał znać wewnętrznej kompozycji ---

    @property
    def sl_arodes(self):
        return self.laczenie.sl_arodes

    @property
    def l_bledy_wpisu(self):
        return self.laczenie.l_bledy_wpisu

    @property
    def l_bledy_odczytu(self):
        return self.laczenie.l_bledy_odczytu

    def p_f_max(self):
        self.laczenie.p_f_max()

    def p_f_arodes(self, slownik_arodes_pul, dopasowanie_administracji):
        """Dla każdej pary (oddz,wydz) źródła PUL (slownik_arodes_pul,
        patrz dopasuj_arodes.zbuduj_slownik_arodes_pul - już bez kolizji,
        precheck to zagwarantował) buduje wiersze F_ARODES (OBRĘB/L-CTWO/
        ODDZ/WYDZIEL, z dedupem wierszy nadrzędnych po adresie), łącząc
        JEDEN wspólny adres administracyjny (dopasowanie_administracji -
        ta sama warstwa wydzieleń leży w jednym obrębie ewidencyjnym,
        patrz spatial_match.dopasuj_administracje) z ODDZ/WYDZ wziętym
        wprost z adresu PUL (nie z żadnej warstwy SHP). Wypełnia
        self.laczenie.sl_arodes (stary ARODES_INT_NUM źródła PUL -> nowy)
        tylko dla poziomu WYDZIEL - jedynego z danymi-dziećmi przez FK."""
        # orkiestrator blokuje konwersję wcześniej, gdy dopasowanie się nie
        # powiedzie (patrz __init__.uruchom) - te dwa warunki to tylko
        # zabezpieczenie przed wywołaniem w złej kolejności
        if dopasowanie_administracji.klucz_teryt is None:
            self.l_bez_adresu.append(
                (None, None, 'brak dopasowania warstwy wydzieleń do '
                 'żadnego obrębu ewidencyjnego'))
            return

        county, district, municip, community = \
            dopasowanie_administracji.klucz_teryt
        county_l = SL_WOJ.get(county)
        if county_l is None:
            self.l_bez_adresu.append(
                (None, None, 'nieznany kod województwa: ' + str(county)))
            return

        for (oddz, wydz), stary_arodes in slownik_arodes_pul.items():
            adres_wydziel = zbuduj_adres_upul(
                county_l, district, municip, community, _GRP_DOMYSLNE,
                oddz, wydz)

            for budownik in (self._hierarchia.stworz_ops_obrebu,
                              self._hierarchia.stworz_ops_lctwa,
                              self._hierarchia.stworz_ops_oddz):
                adres_poziomu, typ_cd, order_key, valid = budownik(
                    adres_wydziel)
                if adres_poziomu in self._adresy_juz_wpisane:
                    continue
                self._adresy_juz_wpisane.add(adres_poziomu)
                self._dodaj_arodes(adres_poziomu, typ_cd, order_key, valid)

            _, typ_cd, order_key, valid = self._hierarchia.stworz_ops_wydz(
                adres_wydziel)
            nowy = self._dodaj_arodes(adres_wydziel, typ_cd, order_key, valid)
            self.laczenie.sl_arodes[stary_arodes] = nowy

    def _dodaj_arodes(self, adres, typ_cd, order_key, valid):
        self.laczenie.maxint += 1
        nowy = self.laczenie.maxint
        # kolejność zgodna z insertem w Laczenie.d_tabele(): ARODES_INT_NUM,
        # ADRESS_FOREST, ARODES_TYP_CD, ORDER_KEY, ADRESS_VALID, PROT_INT_NUM,
        # TEMP_RAPORT - dwie ostatnie NULL (brak odpowiednika w źródle PUL,
        # nowo wyliczony adres nie ma jeszcze protokołu/flagi raportu)
        self.laczenie.f_arodes.append(
            [nowy, adres, typ_cd, order_key, valid, None, None])
        return nowy

    def p_f_community(self, dopasowanie_administracji):
        """Grupa 1: JEDEN nowy wiersz F_COMMUNITY (o ile jeszcze nie
        istnieje) dla TERYT-u z dopasowania geometrycznego całej warstwy
        wydzieleń (nie z F_COMMUNITY źródła PUL - to właśnie ta błędna
        administracja, którą naprawiamy). COMMUNITY_NAME bierze się z
        warstwy obrębów (dopasowanie_administracji.nazwa_obrebu, patrz
        spatial_match.klucz_teryt_z_obreb) - wzorem przygotuj_baze_z_ewid.py,
        które też bierze nazwę wprost z warstwy ewidencyjnej zamiast
        zostawiać NULL (COMMUNITY_NAME jest NOT NULL w Access - NULL
        powodował ciche niepowodzenie insertu)."""
        klucz = dopasowanie_administracji.klucz_teryt
        if klucz is None:
            return

        kolumny = F_COMMUNITY.kolumny
        org = self.baza0.pobierz(
            'select ' + ', '.join(kolumny) + ' from F_COMMUNITY;')
        if org is False:
            self.laczenie.l_bledy_odczytu.append(
                (self.baza0.baza, 'F_COMMUNITY',
                 'Nie udało się odczytać tabeli'))
            org = []
        istniejace = {tuple(w[0:4]) for w in org}

        if klucz in istniejace:
            return
        self.laczenie.f_community_nowe.append(
            list(klucz) + [(dopasowanie_administracji.nazwa_obrebu or '')[:30]])

    def _wspolne_kolumny(self, tabela, kolumny_docelowe):
        """Filtruje kolumny_docelowe (zestaw zdefiniowany dla formatu
        UPUL w baza_polacz_rejestr.py) do przecięcia z realnym schematem
        tej tabeli w źródłowej bazie PUL - GRUPA2_DZIECI/GRUPA3_DZIECI/
        F_PARCEL_NADRZEDNA/V_ADDRESS_NADRZEDNA są zaprojektowane dla
        Laczenie (baza_polacz.py), które łączy dwie bazy TEGO SAMEGO
        formatu i nie potrzebuje tej ochrony. W PUL część kolumn ma inną
        nazwę (np. F_SUBAREA.DAMAGE_DEGREE zamiast DAMAGE_DEGREE_CD) albo
        nie istnieje wcale (np. F_PARCEL.STAKE zamiast STAKE_1+STAKE_2) -
        bez filtrowania Access ODBC na nieznaną kolumnę w SELECT zgłasza
        mylące "Too few parameters" zamiast błędu o brakującej kolumnie,
        i CAŁA tabela przestaje się wczytywać zamiast pominąć tylko
        brakujące kolumny. Zachowuje kolejność oryginalnej listy.

        `tabela` to nazwa DOCELOWA (UPUL) - jeśli PUL trzyma te same dane
        pod inną nazwą tabeli (_ALIASY_TABEL_PUL), sprawdzana jest
        struktura tej alternatywnej nazwy, a nie `tabela` wprost."""
        if tabela.upper() in _TABELE_ZNANE_BRAKI:
            return []
        nazwa_zrodlowa = _nazwa_zrodlowa(tabela)
        realne = self.baza_pul.kolumny_tabeli(nazwa_zrodlowa)
        if realne is False:
            self.laczenie.l_bledy_odczytu.append(
                (self.baza_pul.baza, tabela,
                 'Nie udało się odczytać struktury tabeli (źródło PUL)'))
            return []
        wspolne = [k for k in kolumny_docelowe if k in realne]
        pominiete = [k for k in kolumny_docelowe if k not in wspolne]
        if pominiete:
            self.l_kolumny_pominiete.setdefault(tabela, set()).update(pominiete)
        return wspolne

    def _definicja_filtrowana(self, definicja, indeksy_krytyczne):
        """Jak _wspolne_kolumny, ale zwraca kopię definicji (TabelaNadrzedna)
        z podmienionym .kolumny - do użycia z Laczenie._polacz_nadrzedna(),
        która (w przeciwieństwie do _polacz_dziecko) indeksuje .kolumny
        pozycyjnie (indeks_klucza/funkcja_klucza_dedup). Jeśli którakolwiek
        z indeksy_krytyczne (pozycje używane przez tę logikę) zostałaby
        odfiltrowana, zwraca None zamiast ryzykować ciche przesunięcie
        indeksów - tabela trafia do błędów jak dziś, bez próby kopiowania."""
        wspolne = self._wspolne_kolumny(definicja.nazwa, definicja.kolumny)
        if not wspolne:
            return None
        prefiks_oryg = [definicja.kolumny[i] for i in indeksy_krytyczne]
        if wspolne[:len(prefiks_oryg)] != prefiks_oryg:
            self.laczenie.l_bledy_odczytu.append(
                (self.baza_pul.baza, definicja.nazwa,
                 'Brakuje w źródle kolumny kluczowej dla dopasowania '
                 '(dedup/klucz surogatu) - tabela pominięta'))
            return None
        nowa = copy.copy(definicja)
        nowa.kolumny = wspolne
        return nowa

    def p_pozostale_nadrzedne(self):
        """F_PARCEL/V_ADDRESS - kody TERYT źródła PUL są już poprawne
        (nie dotyczy ich problem RDLP-vs-TERYT), ale schemat kolumn bywa
        lekko inny niż UPUL - stąd filtrowanie przez
        _definicja_filtrowana() zamiast Laczenie.p_pozostale_nadrzedne()
        wprost (patrz _wspolne_kolumny). Przefiltrowane definicje trzeba
        zapamiętać (self._f_parcel/_v_address) i użyć ich też w d_tabele()
        przy zapisie - inaczej Laczenie.d_tabele() budowałby INSERT z
        pełną (niefiltrowaną) listą kolumn przeciwko wierszom o mniejszej
        liczbie wartości (błąd Access "Number of query values and
        destination fields are not the same")."""
        self._f_parcel = self._definicja_filtrowana(
            F_PARCEL_NADRZEDNA, _KRYTYCZNE_F_PARCEL)
        if self._f_parcel is not None:
            self.laczenie.f_parcel_nowe, self.laczenie.maxparcel = \
                self.laczenie._polacz_nadrzedna(
                    self._f_parcel, self.laczenie.maxparcel)

        self._v_address = self._definicja_filtrowana(
            V_ADDRESS_NADRZEDNA, _KRYTYCZNE_V_ADDRESS)
        if self._v_address is not None:
            self.laczenie.v_address_nowe, self.laczenie.maxaddr = \
                self.laczenie._polacz_nadrzedna(
                    self._v_address, self.laczenie.maxaddr)

    def p_tabele(self):
        """GRUPA2_DZIECI + GRUPA3_DZIECI, ze schematem kolumn dopasowanym
        do źródła PUL (patrz _wspolne_kolumny) - bezpieczne, bo
        Laczenie._polacz_dziecko() adresuje kolumny wyłącznie po nazwie
        (zip + porównania), nie pozycyjnie, więc filtrowanie nie wymaga
        zapamiętywania definicji osobno dla d_tabele() jak przy
        p_pozostale_nadrzedne() - self.laczenie.dzieci już jest
        podmienione na przefiltrowane kopie.

        Odczyt NIE może iść przez Laczenie.p_tabele() wprost - ta zawsze
        czyta pod t.nazwa (nazwa docelowa UPUL), a część tabel PUL ma
        inną nazwę źródłową (patrz _ALIASY_TABEL_PUL, np.
        F_AROD_SPECIALAREA w PUL = f_arod_spec_area w UPUL). Zapis
        (_polacz_dziecko w d_tabele()) zawsze idzie pod t.nazwa
        niezmienione - szablon docelowy nie jest modyfikowany."""
        dzieci_filtrowane = []
        for t in self.laczenie.dzieci:
            wspolne = self._wspolne_kolumny(t.nazwa, t.kolumny)
            if not wspolne:
                continue
            t2 = copy.copy(t)
            t2.kolumny = wspolne
            dzieci_filtrowane.append(t2)
        self.laczenie.dzieci = dzieci_filtrowane

        for t in self.laczenie.dzieci:
            nazwa_zrodlowa = _nazwa_zrodlowa(t.nazwa)
            sql = 'select ' + ', '.join(t.kolumny) + ' from ' + nazwa_zrodlowa + ';'
            pob = self.baza_pul.pobierz(sql)
            if pob is False:
                self.laczenie.l_bledy_odczytu.append(
                    (self.baza_pul.baza, t.nazwa,
                     'Nie udało się odczytać tabeli'))
                pob = []
            self.laczenie._wiersze[t.klucz] = pob

    def d_tabele(self):
        """Odpowiednik Laczenie.d_tabele(), ale F_PARCEL/V_ADDRESS zapisuje
        przez przefiltrowane definicje (self._f_parcel/_v_address) zamiast
        globalnych F_PARCEL_NADRZEDNA/V_ADDRESS_NADRZEDNA - patrz
        p_pozostale_nadrzedne(). F_COMMUNITY/F_ARODES/dzieci kopiowane
        identycznie jak w Laczenie.d_tabele() (te bufory już mają spójny,
        jednolity kształt niezależnie od filtrowania).

        Dodatkowo zawsze tworzy jeden wiersz V_ADDRESS (_WLASCICIEL =
        "Skarb Państwa") i łączy go ze 100% udziałem
        (part_numerator=1/part_denominator=1) do każdej skopiowanej
        działki - PUL nie ma V_ADDRESS/V_PARCEL_PARTICIPATION (dane
        właściciela prywatnego, nie dotyczy Skarbu Państwa), tym samym
        wzorcem co przygotuj_baze_z_ewid.PrzygotujBazeZEWID."""
        l = self.laczenie
        for row in l.f_community_nowe:
            sql = ('insert into F_COMMUNITY (' + ', '.join(F_COMMUNITY.kolumny) +
                   ') values (' + '?,' * (len(row) - 1) + '?);')
            l._wpisz(sql, row, 'F_COMMUNITY', 'klucz=' + str(tuple(row[:4])))

        for row in l.f_arodes:
            sql = ('insert into f_arodes (ARODES_INT_NUM, ADRESS_FOREST, '
                   'ARODES_TYP_CD, ORDER_KEY, ADRESS_VALID, PROT_INT_NUM, '
                   'TEMP_RAPORT) values (' + '?,' * (len(row) - 1) + '?);')
            l._wpisz(sql, row, 'f_arodes', 'ADRESS_FOREST=' + str(row[1]))

        if self._f_parcel is not None:
            l._wpisz_wiersze(self._f_parcel, l.f_parcel_nowe)
            self._wpisz_wlasciciela(l.f_parcel_nowe)
        if self._v_address is not None:
            l._wpisz_wiersze(self._v_address, l.v_address_nowe)

        for t in l.dzieci:
            l._polacz_dziecko(t)

    def _wpisz_wlasciciela(self, f_parcel_nowe):
        """Skarb Państwa (V_ADDRESS) jako jedyny właściciel wszystkich
        działek skopiowanych z PUL w tym przebiegu, ze 100% udziałem w
        każdej (V_PARCEL_PARTICIPATION) - patrz d_tabele()."""
        if not f_parcel_nowe:
            return
        try:
            self.baza0.cur.execute(
                'insert into V_ADDRESS (NAME_1, VIEW_ADDRESS_FL, LP_PRICE) '
                'values (?,?,?);', (_WLASCICIEL, False, False))
            addr_nr = int(self.baza0.cur.execute('SELECT @@IDENTITY').fetchval())
            self.baza0.con.commit()
            self.wlasciciel_wpisany = True
        except Exception as e:
            self.laczenie.l_bledy_wpisu.append(
                ('V_ADDRESS', 'NAME_1=' + _WLASCICIEL, str(e)))
            return

        i_parcel = self._f_parcel.indeks_klucza
        sql = ('insert into V_PARCEL_PARTICIPATION (addr_nr, parcel_int_num, '
               'part_numerator, part_denominator) values (?,?,?,?);')
        for row in f_parcel_nowe:
            parcel_int_num = row[i_parcel]
            if self.laczenie._wpisz(
                    sql, [addr_nr, parcel_int_num, 1, 1],
                    'V_PARCEL_PARTICIPATION',
                    'parcel_int_num=' + str(parcel_int_num)):
                self.l_wlasciciel_udzialy += 1
