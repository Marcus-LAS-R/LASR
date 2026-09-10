"""Sprawdza, czy warstwa WYDZ_PKT_stare i warstwy "grupy opis"
(opis_klon/opis_pkt/opis_notatki, patrz warstwa_opisow_dock.py) oraz
adr_upul (karty adresowe scalone z pomiarów taksatorów w terenie, patrz
shp_polacz_teren.py) leżą na wydzieleniach z warstwy WYDZ - na wzór
shp_sprawdz_ciecie.py (kontrola "Pkt_poza_wydz"/sprawdz_pnsw). Dla każdej
sprawdzanej warstwy, która jest akurat wczytana w projekcie, wierzchołki
leżące poza WYDZ trafiają jako osobna, czerwono podświetlona warstwa
"<źródło>_poza_WYDZ" - do ręcznej korekty w QGIS. Warstwy, których nie ma
w projekcie, są pomijane bez błędu (nie każdy projekt ma je wszystkie na
raz).

Dodatkowo, dla trzech warstw "adresowych" (WYDZ_PKT_stare, opis_pkt,
adr_upul - patrz _WARSTWY_ADRESOWE) akurat wczytanych w projekcie, jedna
łączna kontrola liczby punktów adresowych na każdym poligonie WYDZ (sumując
punkty ze wszystkich trzech warstw naraz - nie tylko parami), wynik jako
warstwa poligonowa WYDZ:
1. "WYDZ_sieroty" (styl WYDZ_bez_kart.qml) - poligony z zerem punktów
   adresowych łącznie ze wszystkich trzech warstw.
2. "WYDZ_wiele_opisow" (styl WYDZ_z_wieloma_kartami.qml) - poligony z
   więcej niż jednym punktem adresowym łącznie (niezależnie, czy z jednej
   warstwy, czy z kilku naraz - poligon jest "ok" tylko przy dokładnie
   jednym punkcie w sumie). Wyjątek: multipoligon WYDZ, na którym WSZYSTKIE
   punkty opis_pkt mają GRUPA='LZ-Ł' (osobny znacznik na każdej części
   kompleksu Lz), liczy się jako jeden logiczny adres, nie jako duplikat.

Obie kontrole uruchamiane, gdy przynajmniej jedna z trzech warstw
adresowych jest wczytana (brakująca liczy się jako zbiór pusty).

Dodatkowo, kontrola wrysowania PNSW - na wzór
shp_sprawdz_ciecie.SprawdzCiecie.sprawdz_pnsw: dla każdej geometrii pnsw
wrysowanej przez taksatora w terenie (pomiary/pnsw.shp, obok WYDZ na
dysku) sprawdza, czy operator przeniósł ją do docelowej warstwy
SHP/PNSW.shp (test punkt-na-powierzchni, bo ręcznie przerysowana
geometria nie musi być identyczna). Braki trafiają do warstwy
"PNSW_niewrysowane_w_SHP". Działa na plikach na dysku (folder WYDZ), nie
na warstwach wczytanych w TOC - pomijana bez błędu, gdy pomiary/pnsw.shp
nie istnieje."""
import os

from qgis.core import (
    Qgis, QgsFeature, QgsGeometry, QgsProject, QgsSpatialIndex,
    QgsVectorLayer, QgsWkbTypes,
)

from .funkcje import wybierz_warstwe_z_kandydatow
from . import warstwa_opisow_dock as opis

GRUPA_LZ = 'LZ-Ł'

_WARSTWY_DO_SPRAWDZENIA = [
    'WYDZ_PKT_stare',
    opis.NAZWA_KLON,
    opis.NAZWA_PUNKTY,
    opis.NAZWA_NOTATKI,
    'adr_upul',
]

# Warstwy "adresowe" - biorą udział w kontroli duplikatów/współwystępowania
# na jednym poligonie WYDZ i w wyznaczaniu WYDZ_sieroty. opis_klon (linia)
# i opis_notatki są sprawdzane tylko pod kątem poza_WYDZ (wyżej), bo nie
# reprezentują adresu wydzielenia.
_WARSTWY_ADRESOWE = ['WYDZ_PKT_stare', opis.NAZWA_PUNKTY, 'adr_upul']


class SprawdzPolozenieOpisow:
    def __init__(self, iface):
        self.iface = iface

    def uruchom(self):
        lyrs = list(QgsProject.instance().mapLayers().values())
        kandydaci_wydz = [x for x in lyrs if x.name().upper() == 'WYDZ']
        wydz = wybierz_warstwe_z_kandydatow(self.iface, kandydaci_wydz, 'WYDZ')
        if wydz is None:
            self.iface.messageBar().pushWarning(
                'Wydzielenia',
                'Tylko jedna warstwa w TOC powinna nazywać się WYDZ')
            return

        kat = os.path.dirname(
            wydz.dataProvider().dataSourceUri().split('|')[0])

        si = QgsSpatialIndex()
        sl_wydz = {}
        for feat in wydz.getFeatures():
            si.insertFeature(feat)
            sl_wydz[feat.id()] = feat

        podsumowanie = []
        sprawdzono = 0
        zrodla = {}
        for nazwa in _WARSTWY_DO_SPRAWDZENIA:
            kandydaci = [x for x in lyrs if x.name().upper() == nazwa.upper()]
            zrodlo = wybierz_warstwe_z_kandydatow(self.iface, kandydaci, nazwa)
            if zrodlo is None:
                continue
            sprawdzono += 1
            zrodla[nazwa] = zrodlo

            poza = self._szukaj_poza_wydz(zrodlo, si, sl_wydz)
            if poza:
                self._utworz_warstwe_poza(zrodlo, poza, nazwa)
            podsumowanie.append(f'{nazwa}: {len(poza)} poza WYDZ')

        # kontrola liczby punktow adresowych na poligon WYDZ - laczna suma
        # ze wszystkich trzech warstw adresowych naraz (nie tylko parami),
        # tylko dla tych akurat sprawdzonych wyzej (obecnych w projekcie)
        per_poligon = {}
        for nazwa in _WARSTWY_ADRESOWE:
            zrodlo = zrodla.get(nazwa)
            if zrodlo is None:
                continue
            per_poligon[nazwa] = self._zlicz_pkt_na_poligonach(
                zrodlo, si, sl_wydz)

        if per_poligon:
            ma_grupa_pkt = False
            if opis.NAZWA_PUNKTY in per_poligon:
                zrodlo_pkt = zrodla[opis.NAZWA_PUNKTY]
                ma_grupa_pkt = 'GRUPA' in [f.name() for f in zrodlo_pkt.fields()]

            sieroty = []
            wiele = []
            for wfid in sl_wydz:
                licz = 0
                for nazwa, mapa in per_poligon.items():
                    feats = mapa.get(wfid, [])
                    if not feats:
                        continue
                    # wyjatek: na multipoligonie WYDZ dopuszczalne jest
                    # wiecej niz jeden punkt opis_pkt, jesli WSZYSTKIE sa
                    # LZ-Ł (osobny znacznik na kazdej czesci kompleksu Lz)
                    # - caly taki klaster liczy sie jako jeden logiczny
                    # adres. Inna mieszanka (np. LZ-Ł + inna grupa, albo
                    # >1 punkt innej grupy) nadal liczy sie punkt po punkcie
                    if (nazwa == opis.NAZWA_PUNKTY and len(feats) > 1 and
                            ma_grupa_pkt and
                            sl_wydz[wfid].geometry().isMultipart() and
                            all(str(f['GRUPA']).strip() == GRUPA_LZ
                                for f in feats)):
                        licz += 1
                    else:
                        licz += len(feats)
                if licz == 0:
                    sieroty.append(wfid)
                elif licz > 1:
                    wiele.append(wfid)

            if wiele:
                self._utworz_warstwe_poligonow(
                    wydz, sl_wydz, sorted(wiele), 'WYDZ_wiele_opisow',
                    'WYDZ_z_wieloma_kartami.qml')
            podsumowanie.append(
                f'WYDZ_wiele_opisow: {len(wiele)} poligonów z >1 punktem')

            if sieroty:
                self._utworz_warstwe_poligonow(
                    wydz, sl_wydz, sorted(sieroty), 'WYDZ_sieroty',
                    'WYDZ_bez_kart.qml')
            podsumowanie.append(
                f'WYDZ_sieroty: {len(sieroty)} poligonów bez punktu')

        komunikat_pnsw = self._sprawdz_pnsw(kat)
        if komunikat_pnsw:
            podsumowanie.append(komunikat_pnsw)

        if sprawdzono == 0 and komunikat_pnsw is None:
            self.iface.messageBar().pushWarning(
                'Brak warstw',
                'W projekcie nie znalazłem żadnej z warstw do sprawdzenia '
                '(' + ', '.join(_WARSTWY_DO_SPRAWDZENIA) + '), ani plików '
                'pomiary\\pnsw.shp do kontroli PNSW')
            return

        self.iface.messageBar().pushMessage(
            'OK', 'Sprawdzanie położenia zakończone: ' +
            '; '.join(podsumowanie), Qgis.Success, 10)

    def _sprawdz_pnsw(self, kat):
        """Kontrola wrysowania pnsw: dla każdej geometrii pnsw wrysowanej
        przez taksatora (pomiary/pnsw.shp, obok folderu WYDZ na dysku)
        sprawdza, czy operator przeniósł ją do docelowej warstwy
        SHP/PNSW.shp - na wzór
        shp_sprawdz_ciecie.SprawdzCiecie.sprawdz_pnsw. Geometrie nie muszą
        być idealnie zgodne (ręcznie przerysowywane), więc test to
        punkt-na-powierzchni w wielokącie docelowym, zamiast porównania
        geometrii. Zwraca komunikat do podsumowania albo None, gdy nie ma
        czego sprawdzać (brak pomiary/pnsw.shp)."""
        pnsw_pomiary_path = os.path.join(kat, '..', 'pomiary', 'pnsw.shp')
        if not os.path.exists(pnsw_pomiary_path):
            return None

        pnsw_pomiary = QgsVectorLayer(pnsw_pomiary_path, 'pnsw_pomiary', 'ogr')
        if not pnsw_pomiary.isValid():
            self.iface.messageBar().pushWarning(
                'PNSW', 'Nie udało się wczytać ' + pnsw_pomiary_path)
            return None

        pnsw_shp = QgsVectorLayer(
            os.path.join(kat, 'PNSW.shp'), 'PNSW', 'ogr')

        si_pnsw = QgsSpatialIndex()
        sl_pnsw = {}
        if pnsw_shp.isValid():
            for feat in pnsw_shp.getFeatures():
                si_pnsw.insertFeature(feat)
                sl_pnsw[feat.id()] = feat

        brak = []
        for feat in pnsw_pomiary.getFeatures():
            pkt = feat.geometry().pointOnSurface()
            ids = si_pnsw.intersects(pkt.boundingBox())
            if not any(sl_pnsw[it].geometry().intersects(pkt) for it in ids):
                brak.append(feat)

        if brak:
            plug = os.path.dirname(__file__)
            lyr = QgsVectorLayer(
                f'MultiPoint?crs={pnsw_pomiary.crs().authid()}',
                'PNSW_niewrysowane_w_SHP', 'memory')
            dp = lyr.dataProvider()
            lyr.startEditing()
            dp.addAttributes(pnsw_pomiary.dataProvider().fields().toList())
            lyr.updateFields()
            nowe = []
            for feat in brak:
                nf = QgsFeature(lyr.fields())
                nf.setGeometry(feat.geometry().pointOnSurface())
                nf.setAttributes(feat.attributes())
                nowe.append(nf)
            dp.addFeatures(nowe)
            lyr.commitChanges()
            dodana = QgsProject.instance().addMapLayer(lyr)
            dodana.loadNamedStyle(os.path.join(
                plug, '..', 'qml', 'point_drop_shadow_red.qml'))

        return (
            f'PNSW: {len(brak)} niewrysowane w SHP z '
            f'{pnsw_pomiary.featureCount()}'
        )

    def _szukaj_poza_wydz(self, zrodlo, si, sl_wydz):
        """Zwraca listę (feature, punkt) dla wierzchołków źródła, które nie
        leżą na żadnym wydzieleniu z WYDZ. Dla warstw punktowych to sam
        punkt obiektu, dla linii (opis_klon) - oba jej końce (początek =
        wydzielenie źródłowe, koniec = docelowe)."""
        wynik = []
        for feat in zrodlo.getFeatures():
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue

            if geom.type() == QgsWkbTypes.PointGeometry:
                if geom.isMultipart():
                    punkty = [QgsGeometry.fromPointXY(p)
                              for p in geom.asMultiPoint()]
                else:
                    punkty = [geom]
            elif geom.type() == QgsWkbTypes.LineGeometry:
                if geom.isMultipart():
                    punkty = [QgsGeometry.fromPointXY(p)
                              for linia in geom.asMultiPolyline()
                              for p in linia]
                else:
                    punkty = [QgsGeometry.fromPointXY(p)
                              for p in geom.asPolyline()]
            else:
                continue

            for pkt in punkty:
                ids = si.intersects(pkt.boundingBox())
                if not any(sl_wydz[it].geometry().intersects(pkt)
                           for it in ids):
                    wynik.append((feat, pkt))
        return wynik

    def _zlicz_pkt_na_poligonach(self, zrodlo, si, sl_wydz):
        """Zwraca słownik {wydz_fid: [pkt_feat, ...]} - punkty z warstwy
        punktowej `zrodlo` przypisane do każdego poligonu WYDZ, na którym
        leżą (na wzór dopasowania punkt->wydzielenie z
        baza_dopisz_opisy_taks.waliduj_geometrie, ale przez intersects -
        tak jak reszta tego pliku - zamiast contains, żeby zachować
        spójność z _szukaj_poza_wydz)."""
        wynik = {}
        for feat in zrodlo.getFeatures():
            geom = feat.geometry()
            if geom is None or geom.isEmpty():
                continue
            for wfid in si.intersects(geom.boundingBox()):
                if sl_wydz[wfid].geometry().intersects(geom):
                    wynik.setdefault(wfid, []).append(feat)
        return wynik

    def _utworz_warstwe_poligonow(self, wydz, sl_wydz, fidy, nazwa, qml):
        plug = os.path.dirname(__file__)
        lyr = QgsVectorLayer(
            f'MultiPolygon?crs={wydz.crs().authid()}', nazwa, 'memory')
        dp = lyr.dataProvider()
        lyr.startEditing()
        dp.addAttributes(wydz.fields().toList())
        lyr.updateFields()
        dp.addFeatures([sl_wydz[fid] for fid in fidy])
        lyr.commitChanges()

        dodana = QgsProject.instance().addMapLayer(lyr)
        dodana.loadNamedStyle(os.path.join(plug, '..', 'qml', qml))
        return dodana

    def _utworz_warstwe_poza(self, zrodlo, wynik, nazwa):
        plug = os.path.dirname(__file__)
        lyr = QgsVectorLayer(
            f'MultiPoint?crs={zrodlo.crs().authid()}',
            nazwa + '_poza_WYDZ', 'memory')
        dp = lyr.dataProvider()
        lyr.startEditing()
        dp.addAttributes(zrodlo.fields().toList())
        lyr.updateFields()

        nowe = []
        for feat, pkt in wynik:
            nf = QgsFeature(lyr.fields())
            nf.setGeometry(pkt)
            nf.setAttributes(feat.attributes())
            nowe.append(nf)
        dp.addFeatures(nowe)
        lyr.commitChanges()

        dodana = QgsProject.instance().addMapLayer(lyr)
        dodana.loadNamedStyle(os.path.join(
            plug, '..', 'qml', 'point_drop_shadow_red.qml'))
