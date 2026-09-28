"""Wersja testowa "Przygotuj Lsy" - rozszerza krok s_czy_jeden_ls o
dopasowanie N-do-N: gdy liczba kawalkow Ls w grafice na dzialce rowna sie
liczbie rekordow Ls w bazie, dopasowuje je parami po powierzchni (najlepsze
pary najpierw) i koryguje SQ w granicach progu PROG_POW, zamiast zglaszac
"Brak w bazie" przy niezgodnym SQ. Oryginalny przygotuj_ls.py zostaje bez
zmian - to osobne narzedzie do rownoleglych testow (analogicznie do
"Przysnapuj do dzialek (nowy)")."""

from qgis.core import Qgis, QgsMessageLog, QgsProject

from .przygotuj_ls import PrzygotujLs, AnalizujKlus, PrzetworzKlu

# prog wzglednej roznicy pow. graficznej i rejestrowej, ponizej ktorego
# dopasowanie graf<->baza jest akceptowane
PROG_POW = 0.20


UW_NIEJEDNOZNACZNE = 'Niejednoznaczne dopasowanie klas Ls do bazy - sprawdź; '


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

    def s_dopasuj_ls_po_pow(self):  # noqa
        """Rozszerzenie s_czy_jeden_ls na N-do-N: jesli liczba kawalkow Ls
        w grafice (self.klus) rowna sie liczbie rekordow Ls w bazie na tej
        dzialce:
        1. kawalki, ktorych SQ z KLU jest w bazie na tej dzialce, zachowuja
           go (przy kilku kawalkach o tym samym SQ - najblizsze
           powierzchniowo); dopasowanie po powierzchni NIE nadpisuje
           zgodnych klas,
        2. pozostale kawalki paruje z pozostalymi rekordami bazy po
           powierzchni (globalnie najlepsze pary pierwsze), porownujac
           udzialy w dzialce (_udzial_w_dzialce), i koryguje SQ w
           granicach progu PROG_POW,
        3. kawalek bez dopasowania, ktorego wlasne SQ zdublowaloby LANDID
           juz przypisany innemu kawalkowi, podczas gdy jakis rekord bazy
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

        if len(db_sq_lista) != len(graf_idx) or len(graf_idx) == 0:
            return False

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
            gi: round(self.klus[gi].geometry().area() / 10000, 4)
            for gi in graf_idx}

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
            sq_klu = self.isNone(self.klus[gi]['SQ'])
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
                sq_klu = self.isNone(self.klus[gi]['SQ'])
                for gj, (sq, _pg, _pr) in dopasowania.items():
                    if sq == sq_klu:
                        niejednoznaczne.update([gi, gj])

        if not dopasowania and not niejednoznaczne:
            return False

        self.do_usun = []
        for gi in graf_idx:
            klu = self.klus[gi]
            sq_klu = self.isNone(klu['SQ'])
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

            f = self.new_feat('Ls', sq, uw=uw)
            f.setGeometry(klu.geometry())
            self.klus_popr.append(f)
            self.do_usun.append(gi)

        self.s_do_usuniecia(self.do_usun, 'OK')
        return True


class AnalizujKlusTest(AnalizujKlus):
    def zaladuj_strukture(self):
        """Jak AnalizujKlus.zaladuj_strukture, ale buduje PrzetworzKluTest
        zamiast PrzetworzKlu."""
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

            self.strukt[key] = PrzetworzKluTest(val, k, self.p, self.wl)

    def przetworz_strukture(self):
        """Jak AnalizujKlus.przetworz_strukture, z dodatkowa probą
        dopasowania N-do-N po powierzchni (s_dopasuj_ls_po_pow) przed
        dotychczasowym s_czy_jeden_ls (ktory zostaje jako fallback dla
        przypadku 'jeden uzytek w ogole na dzialce, przemianuj na Ls')."""
        for key, val in self.strukt.items():
            if not val.is_valid():
                self.bledne.append(key)
                continue

            trig = 0
            val.przetworz()
            val.sprawdz_topologie()
            if not val.s_czy_dz_w_bazie():
                continue

            if val.s_czy_ls_na_calosci():
                trig = 1

            if trig == 0:
                if val.s_dopasuj_ls_po_pow():
                    trig = 2
                elif val.s_czy_jeden_ls():
                    trig = 2

            if trig in [0, 2]:
                val.s_dopisz_uzyt()
                val.sprawdz_mikro()

            val.polacz_ostateczne()
            val.dopisz_uwagi_pow()


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
