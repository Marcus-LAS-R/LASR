"""Wersja "na chama" "Przygotuj Lsy" - prototyp do jednego zadania (warstwa
LS_zjebane, w której poligony Ls mają praktycznie samą geometrię, SQ prawie
zawsze puste). Rozszerza s_czy_jeden_ls o dopasowanie N-do-N: gdy liczba
kawałków Ls w grafice na działce równa się liczbie rekordów Ls w bazie,
sortuje oba zbiory po powierzchni i paruje je rosnąco (najmniejszy kawałek
<-> najmniejszy rekord, największy <-> największy) - bez progu odrzucenia,
w odróżnieniu od przygotuj_ls_test.py (tam dopasowanie jest odrzucane, gdy
różnica względna przekracza PROG_POW). Dodatkowo NIE rusza geometrii w
żaden sposób (bez v.dissolve, bez GRASS-owego v.overlay, bez
multiparttosingleparts) - każdy poligon LS_zjebane zostaje dokładnie taki,
jaki jest w warstwie źródłowej, dostaje tylko przypisaną działkę
(PARCELID), z którą ma największą część wspólną (patrz docstring
geop_przetworz). Oryginalny przygotuj_ls.py i przygotuj_ls_test.py zostają
bez zmian - to osobne, jednorazowe narzędzie."""

import os

from PyQt5.QtCore import QVariant
from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsField, \
    QgsFeature, QgsSpatialIndex, QgsVectorLayer

from .przygotuj_ls import PrzygotujLs, AnalizujKlus, PrzetworzKlu
from .funkcje import isNone


class PrzetworzKluNaChama(PrzetworzKlu):
    def s_dopasuj_ls_po_pow_chama(self):
        """Jeżeli liczba kawałków Ls w grafice (self.klus) równa się liczbie
        rekordów Ls w bazie na tej działce i dla każdego z nich znana jest
        powierzchnia rejestrowa, sortuje oba zbiory rosnąco po powierzchni
        i paruje je ranga-do-rangi (bez progu odrzucenia). Zwraca True,
        jeżeli dopasowano."""
        if self.pid not in self.p.sl_ls_na_dz:
            return False

        db_sq_lista = self.p.sl_ls_na_dz[self.pid]
        graf_idx = [i for i, k in enumerate(self.klus) if k['AU'] == 'Ls']

        if len(db_sq_lista) != len(graf_idx) or len(graf_idx) == 0:
            QgsMessageLog.logMessage(
                'NA CHAMA - pominięto ' + self.pid + ': liczba kawałków w '
                'grafice (' + str(len(graf_idx)) + ', pow: ' + str(
                    [round(self.klus[i].geometry().area() / 10000, 4)
                     for i in graf_idx]) + ') != liczbie rekordów Ls w '
                'bazie (' + str(len(db_sq_lista)) + ', sq: ' +
                str(db_sq_lista) + ')',
                'Las-R', Qgis.Warning
            )
            return False

        # kandydaci z bazy: (pow_rej, sq) - jeżeli któryś rekord nie ma
        # powierzchni rejestrowej, nie da się sensownie dopasować po
        # powierzchni, więc rezygnujemy z tej metody dla całej działki
        db_kandydaci = []
        for sq in db_sq_lista:
            landid = self.pid + '.Ls' + sq
            if landid not in self.p.uzytki:
                QgsMessageLog.logMessage(
                    'NA CHAMA - pominięto ' + self.pid + ': brak rekordu ' +
                    landid + ' w self.p.uzytki (baza)',
                    'Las-R', Qgis.Warning
                )
                return False
            db_kandydaci.append((self.p.uzytki[landid][2], sq))
        db_kandydaci.sort(key=lambda x: x[0])

        # kawałki graficzne, posortowane rosnąco po powierzchni graficznej
        graf_posort = sorted(
            graf_idx, key=lambda gi: self.klus[gi].geometry().area()
        )

        self.do_usun = []
        for gi, (pow_rej, sq) in zip(graf_posort, db_kandydaci):
            klu = self.klus[gi]
            landid = self.pid + '.Ls' + sq
            pow_graf = round(klu.geometry().area() / 10000, 4)

            uw = ''
            if self.isNone(klu['SQ']) != sq:
                self.uwagi['podmsq'][landid] = [
                    self.isNone(klu['SQ']), sq,
                    str(pow_rej), str(pow_graf)]
                uw = ('Podmieniono SQ na zgodny z bazą '
                      '(dopasowanie powierzchniowe - na chama); ')

            f = self.new_feat('Ls', sq, uw=uw)
            f.setGeometry(klu.geometry())
            self.klus_popr.append(f)
            self.do_usun.append(gi)

        self.s_do_usuniecia(self.do_usun, 'OK')
        return True


class AnalizujKlusNaChama(AnalizujKlus):
    def geop_przetworz(self):  # noqa
        """Jak AnalizujKlus.geop_przetworz, ale BEZ v.dissolve, BEZ
        GRASS-owego v.overlay i BEZ multiparttosingleparts - geometria
        LS_zjebane (self.klu) zostaje nietknięta, feature po feature, tak
        jak jest w warstwie źródłowej. Jedyna operacja to przypisanie
        każdemu poligonowi działki (PARCELID) z DZKAT, z którą ma
        największą część wspólną (samo pole powierzchni przecięcia liczone
        jest tylko do porównania kandydatów - nie zmienia zapisanej
        geometrii). Wcześniejsze wersje próbowały dissolve/rozbijania
        multipoligonów - nie pomogło (te same działki dalej się nie
        zgadzały), więc na wyraźne życzenie zrezygnowano z jakiejkolwiek
        ingerencji w geometrię."""
        sciezka = self.klu.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)

        # zaindeksuj dzialki do szybkiego wyszukiwania kandydatow
        indeks = QgsSpatialIndex()
        sl_dz = {}
        for f in self.dzkat.getFeatures():
            indeks.insertFeature(f)
            sl_dz[f.id()] = f

        self.singleparts = QgsVectorLayer(
            "MultiPolygon?crs=" + self.dzkat.crs().authid(),
            'Ls_singleparts',
            'memory')
        self.singleparts.dataProvider().addAttributes([
            QgsField('PARCELID', QVariant.String, len=50),
            QgsField('COMMUNITY', QVariant.String, len=4),
            QgsField('AU', QVariant.String, len=10),
            QgsField('SQ', QVariant.String, len=10),
        ])
        self.singleparts.updateFields()
        self.singleparts.startEditing()

        bez_dzialki = 0
        for f in self.klu.getFeatures():
            geom = f.geometry()
            kandydaci = indeks.intersects(geom.boundingBox())

            najlepszy_pid = None
            najlepsza_pow = 0.0
            for fid in kandydaci:
                dz = sl_dz[fid]
                if not geom.intersects(dz.geometry()):
                    continue
                pow_wsp = geom.intersection(dz.geometry()).area()
                if pow_wsp > najlepsza_pow:
                    najlepsza_pow = pow_wsp
                    najlepszy_pid = dz['PARCELID']

            if najlepszy_pid is None:
                bez_dzialki += 1
                continue

            nf = QgsFeature(self.singleparts.fields())
            nf.setGeometry(geom)
            nf.setAttributes([
                najlepszy_pid, isNone(najlepszy_pid)[7:10],
                f['AU'], f['SQ'],
            ])
            self.singleparts.dataProvider().addFeature(nf)

        self.singleparts.commitChanges()

        if bez_dzialki > 0:
            QgsMessageLog.logMessage(
                'NA CHAMA - ' + str(bez_dzialki) + ' poligonów Ls nie '
                'trafiło w żadną działkę z DZKAT (brak przecięcia '
                'geometrii)', 'Las-R', Qgis.Warning
            )

        return True

    def zaladuj_strukture(self):
        """Jak AnalizujKlus.zaladuj_strukture, ale buduje PrzetworzKluNaChama
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

            self.strukt[key] = PrzetworzKluNaChama(val, k, self.p, self.wl)

    def przetworz_strukture(self):
        """Jak AnalizujKlus.przetworz_strukture, z dodatkową próbą
        dopasowania N-do-N po powierzchni (s_dopasuj_ls_po_pow_chama) przed
        dotychczasowym s_czy_jeden_ls (który zostaje jako fallback, gdy
        liczby kawałków w grafice i bazie się nie zgadzają)."""
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
                if val.s_dopasuj_ls_po_pow_chama():
                    trig = 2
                elif val.s_czy_jeden_ls():
                    trig = 2

            if trig in [0, 2]:
                val.s_dopisz_uzyt()
                val.sprawdz_mikro()

            val.polacz_ostateczne()
            val.dopisz_uwagi_pow()


class PrzygotujLsNaChama(PrzygotujLs):
    """Jak PrzygotujLs, ale używa AnalizujKlusNaChama (dopasowanie Ls do
    bazy po powierzchni, bez progu odrzucenia). Prototyp jednorazowy."""

    def sprawdz_warstwy(self):
        k = False  # klasouzytki - warstwa
        d = False  # dzialki - warstwa

        QgsMessageLog.logMessage(
            '\n-----[ SPRAWDZENIE LS NA CHAMA ]-----', 'Las-R', Qgis.Info
        )

        for key, lyr in QgsProject.instance().mapLayers().items():
            if key[:5] == 'DZKAT':
                d = lyr
            if key[:3] == 'KLU':
                k = lyr

        self.a = AnalizujKlusNaChama(self.iface, k, d)
        return True
