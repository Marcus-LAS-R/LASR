"""Wersja testowa "Przygotuj Lsy" - rozszerza krok s_czy_jeden_ls o
dopasowanie N-do-N: gdy liczba kawalkow Ls w grafice na dzialce rowna sie
liczbie rekordow Ls w bazie, dopasowuje je parami po powierzchni (najlepsze
pary najpierw) i koryguje SQ w granicach progu PROG_POW, zamiast zglaszac
"Brak w bazie" przy niezgodnym SQ. Oryginalny przygotuj_ls.py zostaje bez
zmian - to osobne narzedzie do rownoleglych testow (analogicznie do
"Przysnapuj do dzialek (nowy)")."""

import os

from qgis.core import Qgis, QgsMessageLog, QgsProject

from . import raporty, waypointy
from .przygotuj_ls import PrzygotujLs, AnalizujKlus, PrzetworzKlu, \
    GenerujRaport, TYP_UZYTKI
from .przygotuj_ls_z_wydzielen import PrzetworzWydzielenia, \
    AnalizujWydzielenia

# prog wzglednej roznicy pow. graficznej i rejestrowej, ponizej ktorego
# dopasowanie graf<->baza jest akceptowane
PROG_POW = 0.20


UW_NIEJEDNOZNACZNE = 'Niejednoznaczne dopasowanie klas Ls do bazy - sprawdź; '

# ponizej tej powierzchni [m2] kawalek Ls nie liczy sie przy porownaniu z
# liczba rekordow w bazie (odlamki z przeciecia KLU z granicami dzialek)
PROG_MIKRO = 21


class PrzetworzKluTest(PrzetworzKlu):
    def _udzial_w_dzialce(self):
        """Zwraca funkcje (pow_graf, pow_rej) -> roznica wzgledna udzialow
        w dzialce: pow_graf / pow. graf. dzialki wobec pow_rej / pow. rej.
        dzialki (PARCEL_AR). Odporne na dzialki, ktorych grafika jest w
        calosci przeskalowana wzgledem rejestru (np. +41% na
        24070620003.5821) - wtedy porownanie powierzchni bezwzglednych
        paruje kawalki z cudzymi klasami. Bez pow. rejestrowej dzialki -
        porownanie bezwzgledne jak dotychczas."""
        dz_graf = self.dz.geometry().area() / 10000
        try:
            dz_rej = float(self.dz['PARCEL_AR'])
        except (TypeError, ValueError, KeyError):
            dz_rej = 0
        if not dz_rej and self.pid in self.p.dzialki:
            dz_rej = self.p.dzialki[self.pid][3] or 0
        if not dz_rej or not dz_graf:
            dz_rej = dz_graf = 1

        def roznica(pow_graf, pow_rej):
            udz_rej = pow_rej / dz_rej
            return abs(pow_graf / dz_graf - udz_rej) / udz_rej
        return roznica

    def _jednostki_ls(self, graf_idx, ile_w_bazie):
        """Dzieli kawalki Ls na jednostki dopasowania (listy indeksow), ktorych
        jest tyle, ile rekordow Ls w bazie. Kolejno:
        - kazdy kawalek osobno,
        - kazdy kawalek osobno, bez odlamkow < PROG_MIKRO (odlamek nie moze
          zablokowac dopasowania calej dzialki; zostaje w self.klus i idzie
          zwykla sciezka, czyli s_dopisz_uzyt i sprawdz_mikro),
        - cale klasy z KLU, bez odlamkow (klasa bywa w kilku kawalkach).
        None, gdy zaden podzial nie daje wlasciwej liczby jednostek."""
        if len(graf_idx) == ile_w_bazie:
            return [[gi] for gi in graf_idx]

        glowne = [gi for gi in graf_idx
                  if self.klus[gi].geometry().area() >= PROG_MIKRO]
        if len(glowne) == ile_w_bazie:
            return [[gi] for gi in glowne]

        klasy = {}
        for gi in glowne:
            klasy.setdefault(self.isNone(self.klus[gi]['SQ']), []).append(gi)
        if len(klasy) == ile_w_bazie:
            return list(klasy.values())
        return None

    def s_dopasuj_ls_po_pow(self):  # noqa
        """Rozszerzenie s_czy_jeden_ls na N-do-N: jesli kawalki Ls w grafice
        (self.klus) da sie podzielic na tyle jednostek, ile rekordow Ls jest
        w bazie na tej dzialce (_jednostki_ls):
        1. jednostki, ktorych SQ z KLU jest w bazie na tej dzialce, zachowuja
           go (przy kilku jednostkach o tym samym SQ - najblizsze
           powierzchniowo); dopasowanie po powierzchni NIE nadpisuje
           zgodnych klas,
        2. pozostale jednostki paruje z pozostalymi rekordami bazy po
           powierzchni (globalnie najlepsze pary pierwsze), porownujac
           udzialy w dzialce (_udzial_w_dzialce), i koryguje SQ w
           granicach progu PROG_POW,
        3. jednostka bez dopasowania, ktorej wlasne SQ zdublowaloby LANDID
           juz przypisany innej jednostce, podczas gdy jakis rekord bazy
           zostal bez grafiki, dostaje uwage UW_NIEJEDNOZNACZNE (wczesniej
           polacz_ostateczne po cichu scalal oba kawalki w jeden LANDID,
           a brakujacy trafial do raportu jako "brakujacy").
        Pozostale kawalki bez dopasowania wracaja do zwyklej sciezki
        (s_dopisz_uzyt -> ew. "Brak w bazie", jak dotychczas).
        Zwraca True jesli cokolwiek dopasowano (choc niekoniecznie
        wszystko)."""
        if self.pid not in self.p.sl_ls_na_dz:
            return False

        db_sq_lista = self.p.sl_ls_na_dz[self.pid]
        graf_idx = [i for i, k in enumerate(self.klus) if k['AU'] == 'Ls']
        if not graf_idx:
            return False

        jednostki = self._jednostki_ls(graf_idx, len(db_sq_lista))
        if jednostki is None:
            return False
        graf_idx = list(range(len(jednostki)))  # dalej: indeksy jednostek

        # kandydaci z bazy: (sq, pow_rej) - pow_rej None, gdy brak pow.
        # rejestrowej (nie da sie ich dopasowac po powierzchni)
        db_kandydaci = []
        for sq in db_sq_lista:
            landid = self.pid + '.Ls' + sq
            pow_rej = None
            if landid in self.p.uzytki:
                pow_rej = self.p.uzytki[landid][2]
            db_kandydaci.append((sq, pow_rej))

        roznica_udz = self._udzial_w_dzialce()
        pow_graf = {
            gi: round(sum(self.klus[k].geometry().area()
                          for k in jednostki[gi]) / 10000, 4)
            for gi in graf_idx}

        def sq_jednostki(gi):
            return self.isNone(self.klus[jednostki[gi][0]]['SQ'])

        def roznica(gi, di):
            pow_rej = db_kandydaci[di][1]
            if pow_rej in (None, 0):
                return None
            return roznica_udz(pow_graf[gi], pow_rej)

        graf_uzyte = set()
        db_uzyte = set()
        dopasowania = {}  # gi -> (sq, pow_graf, pow_rej)

        # 1. zgodne klasy - SQ z KLU obecne w bazie na dzialce zostaje
        pary_zgodne = []
        for gi in graf_idx:
            sq_klu = sq_jednostki(gi)
            for di, (sq, _pow_rej) in enumerate(db_kandydaci):
                if sq == sq_klu:
                    r = roznica(gi, di)
                    pary_zgodne.append((r if r is not None else 0, gi, di))
        for _r, gi, di in sorted(pary_zgodne, key=lambda x: x[0]):
            if gi in graf_uzyte or di in db_uzyte:
                continue
            graf_uzyte.add(gi)
            db_uzyte.add(di)
            dopasowania[gi] = (db_kandydaci[di][0], pow_graf[gi],
                               db_kandydaci[di][1])

        # 2. pozostale - po udziale w dzialce, w progu PROG_POW
        pary = []
        for gi in graf_idx:
            if gi in graf_uzyte:
                continue
            for di, (sq, pow_rej) in enumerate(db_kandydaci):
                if di in db_uzyte:
                    continue
                r = roznica(gi, di)
                if r is None:
                    continue
                pary.append((r, gi, di))

        for r, gi, di in sorted(pary, key=lambda x: x[0]):
            if gi in graf_uzyte or di in db_uzyte:
                continue
            if r >= PROG_POW:
                continue
            graf_uzyte.add(gi)
            db_uzyte.add(di)
            dopasowania[gi] = (db_kandydaci[di][0], pow_graf[gi],
                               db_kandydaci[di][1])

        # 3. kawalki bez dopasowania dublujace przypisany LANDID przy
        # nieprzypisanym rekordzie bazy - uwaga zamiast cichego scalenia
        niejednoznaczne = set()
        if len(db_uzyte) < len(db_kandydaci):
            for gi in graf_idx:
                if gi in graf_uzyte:
                    continue
                sq_klu = sq_jednostki(gi)
                for gj, (sq, _pg, _pr) in dopasowania.items():
                    if sq == sq_klu:
                        niejednoznaczne.update([gi, gj])

        if not dopasowania and not niejednoznaczne:
            return False

        self.do_usun = []
        for gi in graf_idx:
            sq_klu = sq_jednostki(gi)
            uw = ''
            if gi in dopasowania:
                sq, pg, pr = dopasowania[gi]
                if sq_klu != sq:
                    landid = self.pid + '.Ls' + sq
                    self.uwagi['podmsq'][landid] = [
                        sq_klu, sq, str(pr), str(pg)]
                    uw = ('Podmieniono SQ na zgodny z bazą '
                          '(dopasowanie powierzchniowe); ')
            elif gi in niejednoznaczne:
                sq = sq_klu
            else:
                continue  # zwykla sciezka (s_dopisz_uzyt)

            if gi in niejednoznaczne:
                uw += UW_NIEJEDNOZNACZNE

            for k in jednostki[gi]:
                f = self.new_feat('Ls', sq, uw=uw)
                f.setGeometry(self.klus[k].geometry())
                self.klus_popr.append(f)
                self.do_usun.append(k)

        self.s_do_usuniecia(self.do_usun, 'OK')
        return True


class PrzetworzUzytki(PrzetworzWydzielenia, PrzetworzKluTest):
    """Dzialka w trybie "Tylko AU - warstwa UZYTKI": kontury uzytkow nie
    maja klasy, SQ bierzemy z bazy (uzupelnij_sq_z_bazy). Dzialka z kilkoma
    klasami Ls w bazie - kontur Ls do LS_DO_PRZECIECIA, jak w "Przygotuj Lsy
    z wydzieleń" (polacz_ostateczne/dopisz_uwagi_pow z
    PrzetworzWydzielenia), reszta uzytkow zwykla sciezka."""

    def uzupelnij_sq_z_bazy(self, sq_na_dz):
        """sq_na_dz: {AU: [SQ, ...]} z bazy dla tej dzialki. Uzytek z jedna
        klasa w bazie dostaje ja w grafice; z kilkoma klasami zostaje bez
        klasy (Ls - do przeciecia, s_ma_wiele_sq; inne uzytki - "Brak w
        bazie" w SPRAWDZ)."""
        for klu in self.klus:
            klasy = sq_na_dz.get(klu['AU'], [])
            if len(klasy) == 1:
                klu['SQ'] = klasy[0]

    def _ls_idx(self):
        return [i for i, k in enumerate(self.klus) if k['AU'] == 'Ls']

    def s_ma_wiele_sq(self):
        """Kontur Ls w grafice, a w bazie kilka klas Ls na dzialce. Liczone
        na biezacym self.klus (sprawdz_topologie moze z niego usuwac)."""
        ile_w_bazie = len(self.p.sl_ls_na_dz.get(self.pid, []))
        return bool(self._ls_idx()) and ile_w_bazie > 1

    def s_dopisz_do_przeciecia(self):
        """Jak PrzetworzWydzielenia.s_dopisz_do_przeciecia, ale tylko
        kontury Ls - zdejmuje je z self.klus (inne uzytki ida dalej
        zwykla sciezka)."""
        idx = self._ls_idx()
        geom = self.klus[idx[0]].geometry()
        for i in idx[1:]:
            geom = geom.combine(self.klus[i].geometry())
        geom.convertToMultiType()
        f = self.new_feat(
            au='Ls',
            uw='Kilka klas Ls w bazie - wymaga ręcznego przecięcia; ')
        f.setGeometry(geom)
        self.klus_do_przeciecia.append(f)
        self.s_do_usuniecia(idx, 'OK')


class AnalizujKlusTest(AnalizujKlus):
    def zaladuj_strukture(self):
        """Jak AnalizujKlus.zaladuj_strukture, ale buduje PrzetworzKluTest
        zamiast PrzetworzKlu (w trybie UZYTKI - PrzetworzUzytki)."""
        klasa = PrzetworzUzytki if self.typ == TYP_UZYTKI else \
            PrzetworzKluTest
        sl_dzkat = {}
        for feat in self.dzkat.getFeatures():
            sl_dzkat[feat['PARCELID']] = feat

        sl_single = {}
        for feat in self.singleparts.getFeatures():
            if feat['PARCELID'] not in sl_single:
                sl_single[feat['PARCELID']] = []
            sl_single[feat['PARCELID']].append(feat)

        for key, val in sl_dzkat.items():
            k = []
            if key in sl_single:
                k = sl_single[key]

            self.strukt[key] = klasa(val, k, self.p, self.wl)

    def przetworz_strukture(self):
        """Jak AnalizujKlus.przetworz_strukture, z dodatkowa probą
        dopasowania N-do-N po powierzchni (s_dopasuj_ls_po_pow) przed
        dotychczasowym s_czy_jeden_ls (ktory zostaje jako fallback dla
        przypadku 'jeden uzytek w ogole na dzialce, przemianuj na Ls').
        W trybie UZYTKI: najpierw klasy z bazy (uzupelnij_sq_z_bazy), bez
        dopasowania po powierzchni (kontury nie niosa klasy, wiec kawalki
        nie wyznaczaja granic klas); kilka klas Ls - do przeciecia."""
        uzytki = self.typ == TYP_UZYTKI
        if uzytki:
            sq_na_dz = {}  # {PARCELID: {AU: [SQ, ...]}} z bazy
            for au, sq, _pow, pid in (v[:4] for v in self.p.uzytki.values()):
                sq_na_dz.setdefault(pid, {}).setdefault(au, []).append(
                    sq or '')

        for key, val in self.strukt.items():
            if not val.is_valid():
                self.bledne.append(key)
                continue

            if uzytki:
                val.uzupelnij_sq_z_bazy(sq_na_dz.get(key, {}))

            trig = 0
            val.przetworz()
            val.sprawdz_topologie()
            if not val.s_czy_dz_w_bazie():
                continue

            if val.s_czy_ls_na_calosci():
                trig = 1

            if trig == 0:
                if uzytki:
                    if val.s_ma_wiele_sq():
                        val.s_dopisz_do_przeciecia()
                    if val.s_czy_jeden_ls():
                        trig = 2
                elif val.s_dopasuj_ls_po_pow():
                    trig = 2
                elif val.s_czy_jeden_ls():
                    trig = 2

            if trig in [0, 2]:
                val.s_dopisz_uzyt()
                val.sprawdz_mikro()

            val.polacz_ostateczne()
            val.dopisz_uwagi_pow()

    def generuj_warstwy(self):
        super().generuj_warstwy()
        if self.typ == TYP_UZYTKI:
            # ta sama warstwa LS_DO_PRZECIECIA co w "z wydzieleń"
            AnalizujWydzielenia._generuj_warstwe_do_przeciecia(self)

    def generuj_raport(self):
        """Jak AnalizujKlus.generuj_raport (ta sama treść TXT). Raport obok
        baz (katalog z bazami z dialogu) - starsze raporty Ls (przygotowanie
        i kontrola) do Raporty/Archiwum; waypointy dla Nawigatora błędów
        (jak w Kontroli Ls z bazą) do Raporty."""
        raport = GenerujRaport(self.strukt, self.wl, self.p, self.bledne)
        raport.zestaw_dane()
        raport.dolacz_ls_bez_klasy(self.ls_bk)
        rap_out = raport.generuj_raport()

        kat_bazy = os.path.abspath(
            self.dd.ui.lineEdit_bazy.text() or os.path.join(self.kat, '..'))
        self.rap_sc = os.path.join(kat_bazy, 'ls_raport_' + self.czas + '.txt')
        with open(self.rap_sc, 'w', encoding='cp1250') as plik:
            plik.write(rap_out)
        raporty.archiwizuj_starsze(self.rap_sc, 'LS', self.iface)
        kat_rap = waypointy.katalog_raportow(kat_bazy)

        self.waypointy_sc = None
        wiersze = self._zbierz_waypointy(raport)
        if wiersze:
            self.waypointy_sc = os.path.join(
                kat_rap, 'ls_waypointy_' + self.czas + '.csv')
            waypointy.zapisz(self.waypointy_sc, wiersze)

    def _zbierz_waypointy(self, r):
        """Waypointy z sekcji raportu (obiekt GenerujRaport po
        zestaw_dane) - klucze jak w Kontroli Ls z bazą: PARCELID dla Ls
        brakujących w grafice (dorysowanie, LANDID do wklejenia), LANDID
        dla Ls z nowej warstwy LS_<czas>."""
        zr = 'Przygotuj Lsy'
        wiersze = []

        def wp(sekcja, typ, klucz, blad, obiekt, opis='', kopiuj=''):
            wiersze.append(waypointy.wiersz(
                zr, sekcja, typ, klucz, opis, do_skopiowania=kopiuj,
                obiekt=obiekt, blad=blad))

        for pid in r.ls_poza_baza:
            wp('LSy Z KLU NA DZIAŁKACH SPOZA BAZY', 'PARCELID', pid,
               'Działka spoza bazy - Ls nie trafił do warstwy',
               f'działka {pid}')
        for pid in r.bledne:
            wp('DZIAŁKI Z NIEPOPRAWNYMI DANYMI', 'PARCELID', pid,
               'Niepoprawne dane działki - pominięta', f'działka {pid}')
        for landid, pow_rej in r.brakujace_ls_w_shp:
            wp('BRAKUJĄCE LSy [W SHP]', 'PARCELID',
               '.'.join(landid.split('.')[:-1]),
               'Brak Ls w grafice (jest w bazie)', f'Ls {landid}',
               f'pow. rejestrowa {pow_rej}', landid)
        for landid, pow_graf, pow_rej in r.ls_bk_dodane or []:
            wp('LS BEZ KLASY Z UZYTKI [DOPISANE]', 'LANDID', landid,
               'Ls bez klasy dopisany z UZYTKI - sprawdź geometrię',
               f'Ls {landid}',
               f'pow. graficzna {pow_graf}, rejestrowa {pow_rej}')
        for landid, powod, pow_rej in r.ls_bk_nieudane:
            wp('LS BEZ KLASY Z UZYTKI [NIEPRZYGOTOWANE]', 'PARCELID',
               '.'.join(landid.split('.')[:-1]),
               powod, f'Ls {landid}', f'pow. rejestrowa {pow_rej}', landid)
        for landid, pow_graf in r.brakujace_ls_w_bazie:
            wp('BRAKUJĄCE LSy [W BAZIE]', 'LANDID', landid,
               'Brak Ls w bazie (jest w grafice)', f'Ls {landid}',
               f'pow. graficzna {pow_graf}')
        for pid, pow_graf, klasy in r.do_przeciecia:
            wp('LSy DO RĘCZNEGO PRZECIĘCIA', 'PARCELID', pid,
               'Kilka klas Ls w bazie - przetnij kontur Ls na klasy',
               f'działka {pid}',
               f'klasy w bazie: {klasy}, pow. graficzna {pow_graf}')
        for landid in sorted(self.p.ls_podwojne):
            wp('POWÓJNE LS [BAZA]', 'LANDID', landid,
               'Ls podwójny w bazie', f'Ls {landid}',
               'Ls występuje w bazie więcej niż raz na tej działce')
        for landid, stary, nowy, pow_rej, pow_graf in sorted(r.lista_zm_sq):
            wp('PODMIENIONE KLASY LS [W SHP]', 'LANDID', landid,
               f'Podmieniona klasa {stary} -> {nowy}', f'Ls {landid}',
               f'pow. rejestrowa {pow_rej}, graficzna {pow_graf}')
        for landid, stary, nowy, pow_rej, pow_graf in sorted(r.lista_zm_au):
            wp('PRZEMIANOWANE NA LS [W SHP]', 'LANDID', landid,
               f'Użytek {stary} -> {nowy}', f'Ls {landid}',
               f'pow. rejestrowa {pow_rej}, graficzna {pow_graf}')
        niejedn = sorted({
            landid for ob in self.strukt.values()
            for landid, f in ob.zwroc_ostateczne()[0].items()
            if UW_NIEJEDNOZNACZNE in str(f['SPRAWDZ'] or '')})
        for landid in niejedn:
            wp('NIEJEDNOZNACZNE DOPASOWANIE KLAS', 'LANDID', landid,
               'Niejednoznaczne dopasowanie klas', f'Ls {landid}',
               'Kilka kawałków z tą samą klasą, a rekord bazy bez grafiki')
        for landid in sorted(r.pow_zerowe_baza):
            wp('LSy z ZEROWĄ POW', 'LANDID', landid,
               'Zerowa powierzchnia Ls w bazie', f'Ls {landid}')
        for landid in sorted(set(r.lista_mikro)):
            wp('MIKRO LSy (<21 m2)', 'LANDID', landid,
               'Mikro Ls (< 21 m2) po rozbiciu na poligony', f'Ls {landid}')
        for landid, pow_graf, pow_rej in sorted(r.rozb_pow):
            wp('LS ZE ZNACZNĄ RÓŻNICĄ POW.', 'LANDID', landid,
               'Duża różnica pow. graficznej i rejestrowej', f'Ls {landid}',
               f'pow. graficzna {pow_graf}, rejestrowa {pow_rej}, '
               f'różnica {round(pow_graf - pow_rej, 4)}')
        return wiersze


class PrzygotujLsTest(PrzygotujLs):
    """Jak PrzygotujLs, ale uzywa AnalizujKlusTest (dopasowanie Ls po
    powierzchni N-do-N). wczytaj/sprawdz/przygotuj/przetworz dziedziczone
    bez zmian - cala roznica siedzi w self.a."""

    def sprawdz_warstwy(self):
        k = False  # klasouzytki - warstwa
        d = False  # dzialki - warstwa

        QgsMessageLog.logMessage(
            '\n-----[ SPRAWDZENIE LS TEST ]-----', 'Las-R', Qgis.Info
        )

        for key, lyr in QgsProject.instance().mapLayers().items():
            if key[:5] == 'DZKAT':
                d = lyr
            if key[:3] == 'KLU':
                k = lyr

        self.a = AnalizujKlusTest(self.iface, k, d)
        return True
