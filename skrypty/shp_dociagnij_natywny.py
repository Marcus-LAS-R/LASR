# -*- coding: utf-8 -*-
import os
from qgis.core import (
    QgsVectorLayer, QgsSpatialIndex, Qgis, QgsProject, QgsVectorFileWriter,
    QgsProcessingContext, QgsFeatureRequest, QgsField, QgsFeature,
)
from PyQt5.QtCore import QVariant
import processing

from .shp_dociagnij_poly import PobierzDane
from .pw import PasekPostepu
from .funkcje import wyczysc_katalog_temp


def _opcje_zapisu(atrybuty=None):
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    if atrybuty is not None:
        opcje.attributes = atrybuty
    return opcje


def _kontekst():
    """Kontekst processing bez filtrowania błędnych geometrii - wynik nie
    może zależeć od ustawienia "Invalid features filtering" na danym
    komputerze ("pomijaj" gubił po cichu obiekty, "przerwij" wywracał
    skrypt). Błędne geometrie naprawia sam skrypt (fixgeometries po każdym
    kroku, który może je zepsuć)."""
    ctx = QgsProcessingContext()
    ctx.setProject(QgsProject.instance())
    ctx.setInvalidGeometryCheck(QgsFeatureRequest.GeometryNoCheck)
    return ctx


def _run(alg, parametry):
    return processing.run(alg, parametry, context=_kontekst())


def _pusta(geom):
    return geom is None or geom.isNull() or geom.isEmpty()


class DociagnijNatywny:
    """Dociąganie warstwy podrzędnej (np. Ls) do granic warstwy nadrzędnej
    (działki ewidencyjne) natywnymi algorytmami GEOS (fixgeometries +
    snapgeometries) zamiast własnego pipeline'u bufor/różnica/polygonize/
    dopasowanie powierzchniowe (Przyciagnij w shp_dociagnij_poly.py).

    Kluczowa różnica: każdy obiekt wejściowy zawsze zostaje osobnym
    obiektem wyjściowym - bez łączenia po zniknięciu "wąsa" i bez
    fallbacku do oryginalnej (niedociągniętej) geometrii dla niepewnych
    dopasowań. To właśnie cięcie na fragmenty + niezależne snapowanie
    każdego z nich w starym skrypcie było głównym źródłem "prawie ale nie
    dokładnie" pokrywających się wierzchołków, które "Sprawdź topologię"
    zgłasza jako "Niedokładna koincydencja"/"Błąd stykania". Potwierdzone
    empirycznie na materialy/dociaganie_LS/: stary skrypt 2->1255 takich
    błędów, nowy 2->0.

    Metody nazwane tak samo jak w Przyciagnij (_przetworz/podociagaj/
    stworz_poligony/pokaz_warstwy), żeby dało się tę klasę później podstawić
    w orkiestratorze napraw_topologie_hierarchii.py bez zmiany wywołań.
    """

    POLE_NR = 'LASR_NR'  # techniczny numer obiektu wejsciowego (fid),
                         # do wykrycia zgubionych - nie trafia do wyniku
    PROG_ZDEGENEROWANY = 1.0  # m2 - ponizej tego trafia do _DO_PRZEGLADU
    PROG_WELD = 0.02  # m - self-weld, zgodny z prog_koincydencji w kontroli
                      # topologii (sprawdzenia_topo.spr_dokladnosc_koincydencji)
    PROG_DUPLIKAT = 0.0001  # m - usuwanie zdublowanych wierzcholkow w obrebie
                            # tego samego obiektu (insert extra vertices
                            # przy snapie do granicy dzialki czasem dodaje
                            # wierzcholek tuz obok juz istniejacego), zgodny
                            # z zaokragleniem w spr_wstepne (round(..., 4))

    def __init__(self, iface):
        # iface moze byc None (uzycie headless/wsadowe) - wtedy pomijamy
        # pasek postepu i komunikaty w messageBar
        self.iface = iface
        self.dz = False
        self.snap = False
        self.snap_dist = 0.1  # w metrach

        self.kat = ''
        self.tempkat = ''
        self.wyjscie_path = None  # None = domyslnie <kat>/LS_dociagnieta.shp

        self.postep = None
        self.pd = None

        self.ls_fixed = None
        self.dzkat_lines = None
        self.ls_snapped = None
        self.wynik_path = None
        self.przeglad_lyr = None

        self.b_poly = 0  # liczba zdegenerowanych obiektow (do przegladu)
        self.b_zgubione = 0  # obiekty wejscia, ktorych brak w wyniku
        self.b_puste_we = 0  # obiekty wejscia bez geometrii
        self.pole_nr = self.POLE_NR
        self.b_inter = 0  # liczba par nakladajacych sie obiektow wynikowych

    def _postep(self, wartosc):
        if self.postep is not None:
            self.postep.setValue(wartosc)

    def ustaw_dane_bezposrednio(self, dz_path, snap_path, snap_dist=0.1,
                                wyjscie_path=None, tempkat=None):
        """Programowe (bez GUI) ustawienie danych wejsciowych - odpowiednik
        pobierz_dane()+sprawdz_dane(), do uzycia z poziomu orkiestratora
        naprawy hierarchii warstw.

        Przy wielokrotnym wywolywaniu w petli KAZDE wywolanie powinno
        dostac inny tempkat - QGIS/OGR trzyma uchwyty do plikow posrednich
        nawet po zakonczeniu przetwarzania, a Windows blokuje nadpisywanie
        otwartych plikow.
        """
        self.snap_dist = snap_dist
        self.wyjscie_path = wyjscie_path

        self.dz = QgsVectorLayer(dz_path, 'dzewid', 'ogr')
        if not self.dz.isValid():
            print('BŁĄD: niepoprawna warstwa nadrzędna: ' + dz_path)
            return False

        self.snap = QgsVectorLayer(snap_path, 'snap', 'ogr')
        if not self.snap.isValid():
            print('BŁĄD: niepoprawna warstwa do dociągnięcia: ' + snap_path)
            return False

        sciezka = self.dz.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = tempkat or os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.makedirs(self.tempkat)

        return True

    def pobierz_dane(self):
        # ten sam dialog co stary Przyciagnij - pola sa generyczne (dowolna
        # warstwa nadrzedna/podrzedna + tolerancja), nie ma potrzeby
        # duplikowania UI
        self.pd = PobierzDane()
        self.pd.exec_()
        if self.pd.porzucone:
            return False
        return True

    def sprawdz_dane(self):
        if self.pd.ui.lineEdit_cm.text().isdigit():
            self.snap_dist = int(self.pd.ui.lineEdit_cm.text()) / 100

        self.dz = QgsVectorLayer(self.pd.ui.lineEdit_dz.text(),
                                 'dzewid', 'ogr')
        if not self.dz.isValid():
            self.iface.messageBar().pushMessage(
                "BŁĄD", 'Niepoprawna warstwa działek', Qgis.Critical, 10)
            return False

        self.snap = QgsVectorLayer(self.pd.ui.lineEdit_snap.text(),
                                   'snap', 'ogr')
        if not self.snap.isValid():
            self.iface.messageBar().pushMessage(
                "BŁĄD", 'Niepoprawna warstwa do dosnapowania',
                Qgis.Critical, 10)
            return False

        sciezka = self.dz.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)

        if self.iface is not None:
            self.postep = PasekPostepu(self.iface).stworz_pasek(
                'Dociąganie (natywne)...')
        return True

    def _przetworz(self):
        """Krok 1: napraw geometrie wejsciowe (fixgeometries) i przygotuj
        linie graniczne warstwy nadrzednej do snapowania."""
        self._postep(10)
        self.b_puste_we = sum(1 for f in self.snap.getFeatures()
                              if _pusta(f.geometry()))
        nazwy = self.snap.fields().names()
        while self.pole_nr in nazwy:
            self.pole_nr = self.pole_nr[:-1] + '_'
        ls_nr = os.path.join(self.tempkat, '__ls_nr.shp')
        _run('native:fieldcalculator', {
            'INPUT': self.snap,
            'FIELD_NAME': self.pole_nr,
            'FIELD_TYPE': 1,  # integer
            'FIELD_LENGTH': 10,
            'FORMULA': '$id',
            'OUTPUT': ls_nr,
        })
        self.ls_fixed = os.path.join(self.tempkat, '__ls_fixed.shp')
        _run('native:fixgeometries', {
            'INPUT': ls_nr,
            'OUTPUT': self.ls_fixed,
        })
        if not os.path.exists(self.ls_fixed):
            return False

        self._postep(25)
        self.dzkat_lines = os.path.join(self.tempkat, '__dzkat_lines.shp')
        _run('native:polygonstolines', {
            'INPUT': self.dz,
            'OUTPUT': self.dzkat_lines,
        })
        if not os.path.exists(self.dzkat_lines):
            return False

        return True

    def podociagaj(self):
        """Krok 2: self-weld (sklej niemal-identyczne wierzcholki w obrebie
        warstwy dociąganej - zeby sasiadujace obiekty naprawde dzielily
        wspolny wierzcholek ZANIM dotkniemy granicy dzialki), a potem snap
        calej warstwy do granic dzialki jednym wywolaniem (bez ciecia na
        fragmenty)."""
        self._postep(40)
        ls_weld1 = os.path.join(self.tempkat, '__ls_weld1.shp')
        _run('native:snapgeometries', {
            'INPUT': self.ls_fixed,
            'REFERENCE_LAYER': self.ls_fixed,
            'TOLERANCE': self.PROG_WELD,
            'BEHAVIOR': 7,  # snap to anchor nodes (single layer only)
            'OUTPUT': ls_weld1,
        })
        # self-weld potrafi zostawic w obiekcie zdublowany wierzcholek
        # (Myslenice: 5 z 8211) - taka geometria jest bledna i dalszy
        # processing ja gubil albo przerywal skrypt; napraw przed snapem
        ls_weld1_fixed = self._napraw_po_weld(ls_weld1, '__ls_weld1')

        self._postep(60)
        self.ls_snapped = os.path.join(self.tempkat, '__ls_snapped.shp')
        _run('native:snapgeometries', {
            'INPUT': ls_weld1_fixed,
            'REFERENCE_LAYER': self.dzkat_lines,
            'TOLERANCE': self.snap_dist,
            'BEHAVIOR': 0,  # prefer aligning nodes, insert extra vertices
            'OUTPUT': self.ls_snapped,
        })
        return os.path.exists(self.ls_snapped)

    def _napraw_po_weld(self, sciezka, rdzen):
        """Usun zdublowane wierzcholki i napraw geometrie po self-weld."""
        bez_dubli = os.path.join(self.tempkat, rdzen + '_bez_dubli.shp')
        _run('native:removeduplicatevertices', {
            'INPUT': sciezka,
            'TOLERANCE': self.PROG_DUPLIKAT,
            'OUTPUT': bez_dubli,
        })
        naprawiona = os.path.join(self.tempkat, rdzen + '_fixed.shp')
        _run('native:fixgeometries', {
            'INPUT': bez_dubli,
            'OUTPUT': naprawiona,
        })
        return naprawiona

    def stworz_poligony(self):
        """Krok 3: napraw geometrie ktore snap mogl popsuc, drugi self-weld
        (siatka bezpieczenstwa na ewentualne nowe mikroniezgodnosci z kroku
        2), finalna naprawa geometrii. Wykryj zdegenerowane (prawie zerowej
        powierzchni - odpowiednik dawnego "znikniecia wasa") obiekty do
        recznego przegladu, oraz obiekty ktore po snapowaniu zaczely sie
        nakladac (nie powinno sie zdarzac, ale sprawdzane dla pewnosci)."""
        self._postep(75)
        fixed1 = os.path.join(self.tempkat, '__ls_snapped_fixed.shp')
        _run('native:fixgeometries', {
            'INPUT': self.ls_snapped,
            'OUTPUT': fixed1,
        })

        weld2 = os.path.join(self.tempkat, '__ls_weld2.shp')
        _run('native:snapgeometries', {
            'INPUT': fixed1,
            'REFERENCE_LAYER': fixed1,
            'TOLERANCE': self.PROG_WELD,
            'BEHAVIOR': 7,
            'OUTPUT': weld2,
        })

        # snap z BEHAVIOR=0 czasem wstawia w obiekcie dodatkowy wierzcholek
        # tuz obok juz istniejacego (insert extra vertices where required) -
        # usun takie zdublowane wierzcholki w obrebie tego samego obiektu
        bez_dubli = os.path.join(self.tempkat, '__ls_bez_dubli.shp')
        _run('native:removeduplicatevertices', {
            'INPUT': weld2,
            'TOLERANCE': self.PROG_DUPLIKAT,
            'OUTPUT': bez_dubli,
        })

        self._postep(90)
        self.wynik_path = os.path.join(self.tempkat, '__ls_finalny.shp')
        _run('native:fixgeometries', {
            'INPUT': bez_dubli,
            'OUTPUT': self.wynik_path,
        })

        wlyr = QgsVectorLayer(self.wynik_path, 'wynik', 'ogr')
        feats = {f.id(): f for f in wlyr.getFeatures()}

        zdegenerowane = [f for f in feats.values()
                         if _pusta(f.geometry())
                         or f.geometry().area() < self.PROG_ZDEGENEROWANY]
        self.b_poly = len(zdegenerowane)

        # obiekty wejscia, ktorych nie ma w wyniku (zaden krok nie powinien
        # gubic, ale gdyby - do przegladu z ORYGINALNA geometria; wynik nie
        # moze miec po cichu mniej obiektow niz wejscie)
        w_wyniku = {f[self.pole_nr] for f in feats.values()}
        zgubione = [f for f in self.snap.getFeatures()
                    if f.id() not in w_wyniku]
        self.b_zgubione = len(zgubione)

        if zdegenerowane or zgubione:
            self.przeglad_lyr = QgsVectorLayer(
                'Polygon?crs=' + wlyr.crs().authid(), '__DO_PRZEGLADU',
                'memory')
            pola = [p for p in wlyr.fields() if p.name() != self.pole_nr]
            pola.append(QgsField('PRZEGLAD', QVariant.String, len=40))
            self.przeglad_lyr.dataProvider().addAttributes(pola)
            self.przeglad_lyr.updateFields()
            nazwy = [p.name() for p in pola[:-1]]
            nowe = []
            for f, powod in ([(f, 'zdegenerowany po dociagnieciu')
                              for f in zdegenerowane] +
                             [(f, 'brak w wyniku - geometria oryginalna')
                              for f in zgubione]):
                g = QgsFeature(self.przeglad_lyr.fields())
                g.setGeometry(f.geometry())
                g.setAttributes([f[n] if n in f.fields().names() else None
                                 for n in nazwy] + [powod])
                nowe.append(g)
            self.przeglad_lyr.dataProvider().addFeatures(nowe)
        else:
            self.przeglad_lyr = None

        si = QgsSpatialIndex()
        for f in feats.values():
            si.addFeature(f)
        pary = set()
        for fid, f in feats.items():
            geom = f.geometry()
            if geom is None or geom.isEmpty():
                continue
            for inny_id in si.intersects(geom.boundingBox()):
                if inny_id == fid:
                    continue
                klucz = tuple(sorted((fid, inny_id)))
                if klucz in pary:
                    continue
                inter = geom.intersection(feats[inny_id].geometry())
                if inter and inter.area() > 0.01:
                    pary.add(klucz)
        self.b_inter = len(pary)

        return True

    def pokaz_warstwy(self):
        """Krok 4: zapisz wynik koncowy, dodaj do TOC, pokaz podsumowanie."""
        self._postep(95)
        wyjscie = self.wyjscie_path or os.path.join(
            self.kat, 'LS_dociagnieta.shp')
        os.makedirs(os.path.dirname(wyjscie), exist_ok=True)

        wlyr = QgsVectorLayer(self.wynik_path, 'wynik', 'ogr')
        atrybuty = [i for i, p in enumerate(wlyr.fields())
                    if p.name() != self.pole_nr]
        QgsVectorFileWriter.writeAsVectorFormatV3(
            wlyr, wyjscie, QgsProject.instance().transformContext(),
            _opcje_zapisu(atrybuty))
        self.dociag = QgsVectorLayer(wyjscie, 'LS_dociagnieta', 'ogr')

        przeglad_path = None
        if self.przeglad_lyr is not None:
            przeglad_path = wyjscie[:-4] + '_DO_PRZEGLADU.shp'
            QgsVectorFileWriter.writeAsVectorFormatV3(
                self.przeglad_lyr, przeglad_path,
                QgsProject.instance().transformContext(), _opcje_zapisu())

        if self.iface is not None:
            QgsProject.instance().addMapLayer(self.dociag)
            if przeglad_path is not None:
                QgsProject.instance().addMapLayer(
                    QgsVectorLayer(przeglad_path, 'DO_PRZEGLADU', 'ogr'))
            self.iface.messageBar().clearWidgets()
            if self.b_zgubione:
                self.iface.messageBar().pushMessage(
                    'UWAGA',
                    'W wyniku brakuje %d obiektów warstwy wejściowej - są w '
                    'DO_PRZEGLADU (PRZEGLAD = "brak w wyniku"), z oryginalną '
                    'geometrią.' % self.b_zgubione, Qgis.Critical, 0)
            if self.b_puste_we:
                self.iface.messageBar().pushMessage(
                    'UWAGA',
                    'Obiektów bez geometrii w warstwie wejściowej: %d '
                    '(są w DO_PRZEGLADU).' % self.b_puste_we,
                    Qgis.Warning, 0)
            if self.b_poly == 0 and self.b_inter == 0:
                self.iface.messageBar().pushMessage(
                    'OK', 'Dociąganie zakończone sukcesem, brak uwag!',
                    Qgis.Success, 0)
            else:
                self.iface.messageBar().pushMessage(
                    'OK z uwagami',
                    'Dociąganie zakończone, obiektów do przeglądu: %d, '
                    'nakładania: %d' % (self.b_poly, self.b_inter),
                    Qgis.Warning, 0)
        else:
            print('Dociągnięto (natywnie) -> %s (do przeglądu: %d, '
                  'nakładania: %d, zgubione: %d, puste na wejściu: %d)' %
                  (wyjscie, self.b_poly, self.b_inter, self.b_zgubione,
                   self.b_puste_we))

        wyczysc_katalog_temp(self.tempkat)
