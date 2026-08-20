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


class PrzetworzKluTest(PrzetworzKlu):
    def s_dopasuj_ls_po_pow(self):
        """Rozszerzenie s_czy_jeden_ls na N-do-N: jesli liczba kawalkow Ls
        w grafice (self.klus) rowna sie liczbie rekordow Ls w bazie na tej
        dzialce, dopasowuje je parami po powierzchni (globalnie najlepsze
        pary pierwsze) i koryguje SQ dopasowanych par w granicach progu
        PROG_POW wzgledem pow. rejestrowej. Kawalki bez dopasowania w
        progu (albo gdy liczby sie nie zgadzaja) wracaja do zwyklej
        sciezki (s_dopisz_uzyt -> ew. "Brak w bazie", jak dotychczas).
        Zwraca True jesli cokolwiek dopasowano (choc niekoniecznie
        wszystko)."""
        if self.pid not in self.p.sl_ls_na_dz:
            return False

        db_sq_lista = self.p.sl_ls_na_dz[self.pid]
        graf_idx = [i for i, k in enumerate(self.klus) if k['AU'] == 'Ls']

        if len(db_sq_lista) != len(graf_idx) or len(graf_idx) == 0:
            return False

        # kandydaci z bazy: (sq, pow_rej) - pomijamy rekordy bez pow.
        # rejestrowej, nie da sie ich sensownie dopasowac po powierzchni
        db_kandydaci = []
        for sq in db_sq_lista:
            landid = self.pid + '.Ls' + sq
            pow_rej = None
            if landid in self.p.uzytki:
                pow_rej = self.p.uzytki[landid][2]
            db_kandydaci.append((sq, pow_rej))

        # wszystkie mozliwe pary (kawalek graf. x rekord bazy) z roznica
        # wzgledna powierzchni - globalnie najlepsze pary dopasowywane
        # pierwsze (a nie w kolejnosci wystepowania)
        pary = []
        for gi in graf_idx:
            pow_graf = round(self.klus[gi].geometry().area() / 10000, 4)
            for di, (sq, pow_rej) in enumerate(db_kandydaci):
                if pow_rej in (None, 0):
                    continue
                roznica = abs(pow_graf - pow_rej) / pow_rej
                pary.append((roznica, gi, di, sq, pow_graf, pow_rej))

        pary.sort(key=lambda x: x[0])

        graf_uzyte = set()
        db_uzyte = set()
        dopasowania = {}  # gi -> (sq, pow_graf, pow_rej)

        for roznica, gi, di, sq, pow_graf, pow_rej in pary:
            if gi in graf_uzyte or di in db_uzyte:
                continue
            if roznica >= PROG_POW:
                continue
            graf_uzyte.add(gi)
            db_uzyte.add(di)
            dopasowania[gi] = (sq, pow_graf, pow_rej)

        if not dopasowania:
            return False

        self.do_usun = []
        for gi, (sq, pow_graf, pow_rej) in dopasowania.items():
            klu = self.klus[gi]
            landid = self.pid + '.Ls' + sq

            uw = ''
            if self.isNone(klu['SQ']) != sq:
                self.uwagi['podmsq'][landid] = [
                    self.isNone(klu['SQ']), sq,
                    str(pow_rej), str(pow_graf)]
                uw = ('Podmieniono SQ na zgodny z bazą '
                      '(dopasowanie powierzchniowe); ')

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
