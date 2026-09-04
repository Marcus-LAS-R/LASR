"""Sprawdza, czy warstwa WYDZ_PKT_stare i warstwy "grupy opis"
(opis_klon/opis_pkt/opis_notatki, patrz warstwa_opisow_dock.py) leżą na
wydzieleniach z warstwy WYDZ - na wzór shp_sprawdz_ciecie.py (kontrola
"Pkt_poza_wydz"/sprawdz_pnsw). Dla każdej sprawdzanej warstwy, która jest
akurat wczytana w projekcie, wierzchołki leżące poza WYDZ trafiają jako
osobna, czerwono podświetlona warstwa "<źródło>_poza_WYDZ" - do ręcznej
korekty w QGIS. Warstwy, których nie ma w projekcie, są pomijane bez
błędu (nie każdy projekt ma je wszystkie na raz).

Dodatkowo, jeśli WYDZ_PKT_stare i/lub opis_pkt są akurat wczytane, cztery
dodatkowe kontrole - wynik jako warstwa poligonowa WYDZ:
1. "WYDZ_PKT_stare_duplikaty" - poligony WYDZ z więcej niż jednym punktem
   WYDZ_PKT_stare (styl WYDZ_z_wieloma_kartami.qml).
2. "opis_pkt_duplikaty" - poligony WYDZ z więcej niż jednym punktem
   opis_pkt (styl WYDZ_z_wieloma_kartami.qml). Wyjątek: multipoligon WYDZ
   może mieć więcej niż jeden punkt opis_pkt, jeśli wszystkie mają
   GRUPA='LZ-Ł' (osobny znacznik na każdej części kompleksu Lz).
3. "WYDZ_PKT_stare_x_opis_pkt" - poligony WYDZ, na których jednocześnie
   leży co najmniej jeden punkt WYDZ_PKT_stare i co najmniej jeden
   opis_pkt (styl WYDZ_z_wieloma_kartami.qml).
4. "WYDZ_sieroty" - poligony WYDZ, na których nie leży żaden punkt ani z
   WYDZ_PKT_stare, ani z opis_pkt (styl WYDZ_bez_kart.qml). Uruchamiana,
   gdy przynajmniej jedna z tych dwóch warstw jest wczytana (brakująca
   liczy się jako zbiór pusty)."""
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
]


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

        # kontrole duplikatow/wspolwystepowania WYDZ_PKT_stare <-> opis_pkt
        # na jednym poligonie WYDZ - tylko dla warstw akurat sprawdzonych
        # wyzej (obecnych w projekcie)
        pkt_stare = zrodla.get('WYDZ_PKT_stare')
        pkt_opis = zrodla.get(opis.NAZWA_PUNKTY)
        per_poligon_stare = {}
        per_poligon_opis = {}

        if pkt_stare is not None:
            per_poligon_stare = self._zlicz_pkt_na_poligonach(
                pkt_stare, si, sl_wydz)
            duplikaty_stare = [
                w for w, f in per_poligon_stare.items() if len(f) > 1]
            if duplikaty_stare:
                self._utworz_warstwe_poligonow(
                    wydz, sl_wydz, duplikaty_stare,
                    'WYDZ_PKT_stare_duplikaty', 'WYDZ_z_wieloma_kartami.qml')
            podsumowanie.append(
                f'WYDZ_PKT_stare: {len(duplikaty_stare)} poligonów z >1 '
                'punktem')

        if pkt_opis is not None:
            per_poligon_opis = self._zlicz_pkt_na_poligonach(
                pkt_opis, si, sl_wydz)
            ma_grupa = 'GRUPA' in [f.name() for f in pkt_opis.fields()]
            duplikaty_opis = []
            for w, feats in per_poligon_opis.items():
                if len(feats) <= 1:
                    continue
                # wyjatek: na multipoligonie WYDZ dopuszczalne jest wiecej
                # niz jeden punkt opis_pkt, jesli WSZYSTKIE sa LZ-Ł (osobny
                # znacznik na kazdej czesci kompleksu Lz) - inna mieszanka
                # (np. LZ-Ł + inna grupa, albo >1 punkt innej grupy) nadal
                # jest duplikatem/konfliktem
                if ma_grupa and sl_wydz[w].geometry().isMultipart() and all(
                        str(f['GRUPA']).strip() == GRUPA_LZ for f in feats):
                    continue
                duplikaty_opis.append(w)
            if duplikaty_opis:
                self._utworz_warstwe_poligonow(
                    wydz, sl_wydz, duplikaty_opis, 'opis_pkt_duplikaty',
                    'WYDZ_z_wieloma_kartami.qml')
            podsumowanie.append(
                f'{opis.NAZWA_PUNKTY}: {len(duplikaty_opis)} poligonów z '
                '>1 punktem')

        if pkt_stare is not None and pkt_opis is not None:
            wspolne = sorted(set(per_poligon_stare) & set(per_poligon_opis))
            if wspolne:
                self._utworz_warstwe_poligonow(
                    wydz, sl_wydz, wspolne, 'WYDZ_PKT_stare_x_opis_pkt',
                    'WYDZ_z_wieloma_kartami.qml')
            podsumowanie.append(
                f'WYDZ_PKT_stare × {opis.NAZWA_PUNKTY}: {len(wspolne)} '
                'poligonów z obydwoma')

        if pkt_stare is not None or pkt_opis is not None:
            sieroty = sorted(
                set(sl_wydz) - set(per_poligon_stare) - set(per_poligon_opis))
            if sieroty:
                self._utworz_warstwe_poligonow(
                    wydz, sl_wydz, sieroty, 'WYDZ_sieroty',
                    'WYDZ_bez_kart.qml')
            podsumowanie.append(
                f'WYDZ_sieroty: {len(sieroty)} poligonów bez punktu')

        if sprawdzono == 0:
            self.iface.messageBar().pushWarning(
                'Brak warstw',
                'W projekcie nie znalazłem żadnej z warstw do sprawdzenia '
                '(WYDZ_PKT_stare, ' + opis.NAZWA_KLON + ', ' +
                opis.NAZWA_PUNKTY + ', ' + opis.NAZWA_NOTATKI + ')')
            return

        self.iface.messageBar().pushMessage(
            'OK', 'Sprawdzanie położenia zakończone: ' +
            '; '.join(podsumowanie), Qgis.Success, 10)

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
