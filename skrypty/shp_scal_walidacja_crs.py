# -*- coding: utf-8 -*-
"""Scalanie warstw zewnętrznych (działki/wydz/użytki/klasoużytki) z wielu
podfolderów w jedną warstwę na grupę, z automatyczną walidacją/naprawą CRS.

Dane od zewnętrznych dostawców bywają rozbite na dziesiątki podfolderów
(po obrębie/wsi), z niespójnie i czasem błędnie zadeklarowanym układem
współrzędnych w .prj (etykieta CRS potrafi kłamać - same współrzędne są
dobre, tylko podpisane pod złą strefą). Zamiast ufać .prj, każdy plik jest
testowany empirycznie: jego surowe współrzędne są "przymierzane" pod kilka
kandydujących CRS (zebranych z faktycznie występujących .prj w zbiorze) i
wybierany jest ten, który po transformacji do CRS docelowego ląduje w
obrębie wskazanej warstwy referencyjnej (np. granicy powiatu).

Dwie fazy:
    Faza 1 (analiza)  - nic nie zapisuje, tylko klasyfikuje pliki i
                         wykrywa właściwy CRS każdego z nich.
    Faza 2 (wykonanie) - scala per grupa (native:mergevectorlayers),
                         usuwa zduplikowane geometrie, zapisuje SHP.
"""
import os
import re

import processing
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsField,
    QgsGeometry,
    QgsMessageLog,
    QgsProject,
    QgsSpatialIndex,
    QgsVectorLayer,
)
from qgis.PyQt.uic import loadUiType
from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QTableWidgetItem,
)

from .pw import PasekPostepu

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'ui_scal_walidacja_crs.ui'))

_LOG = 'Las-R'

# nazwa (po normalizacji, bez sufiksu POLYGON i bez numeru fragmentu) -> grupa
_ALIASY_GRUP = {
    'dzialki': 'dzialki', 'działki': 'dzialki',
    'wydz': 'wydz', 'wydzielenia': 'wydz',
    'uzytki': 'uzytki', 'użytki': 'uzytki',
    'klasouzytki': 'klasouzytki', 'klasoużytki': 'klasouzytki',
}
_NAZWA_WYNIKU = {
    'dzialki': 'dzialki_POLYGON.shp',
    'wydz': 'wydz_POLYGON.shp',
    'uzytki': 'uzytki_POLYGON.shp',
    'klasouzytki': 'klasouzytki_POLYGON.shp',
}

# "działki 1_POLYGON" / "działki_POLYGON" / "grranica_POLYGON" (poza zakresem)
_RE_POLYGON = re.compile(r'^(?P<baza>.+?)[\s_]*polygon$', re.IGNORECASE)
_RE_FRAGMENT = re.compile(r'^(?P<rdzen>.+?)[\s_]+\d+$')

PROG_BUFOR_M = 5000  # tolerancja przy teście "czy warstwa leży w referencji"
PROG_DUPLIKATU = 0.9  # część wspólna / mniejszy poligon -> traktuj jak duplikat


def rozpoznaj_grupe(nazwa_bez_rozszerzenia):
    """Zwraca klucz grupy ('dzialki'/'wydz'/'uzytki'/'klasouzytki') albo None,
    jeśli plik jest poza zakresem (nie ma sufiksu POLYGON albo to nie jedna
    z 4 obsługiwanych warstw)."""
    m = _RE_POLYGON.match(nazwa_bez_rozszerzenia.strip())
    if not m:
        return None
    baza = m.group('baza').strip()
    mf = _RE_FRAGMENT.match(baza)
    if mf:
        baza = mf.group('rdzen').strip()
    return _ALIASY_GRUP.get(baza.lower())


def _znajdz_pliki_shp(katalog):
    wyniki = []
    for root, _dirs, files in os.walk(katalog):
        for f in files:
            if f.lower().endswith('.shp'):
                wyniki.append(os.path.join(root, f))
    return wyniki


def _wczytaj_wkt_prj(sciezka_shp):
    prj = os.path.splitext(sciezka_shp)[0] + '.prj'
    if not os.path.isfile(prj):
        return ''
    try:
        with open(prj, 'r', encoding='utf-8', errors='ignore') as fh:
            return fh.read().strip()
    except OSError:
        return ''


def sklasyfikuj_pliki(katalog_zrodlowy):
    """Zwraca (rekordy, pominiete) - rekordy to lista dictów
    {sciezka, grupa, wkt_zadeklarowany}, pominiete to lista ścieżek plików
    spoza zakresu (nie POLYGON albo nie jedna z 4 grup)."""
    rekordy = []
    pominiete = []
    for sciezka in _znajdz_pliki_shp(katalog_zrodlowy):
        nazwa = os.path.splitext(os.path.basename(sciezka))[0]
        grupa = rozpoznaj_grupe(nazwa)
        if grupa is None:
            pominiete.append(sciezka)
            continue
        rekordy.append({
            'sciezka': sciezka,
            'grupa': grupa,
            'wkt_zadeklarowany': _wczytaj_wkt_prj(sciezka),
        })
    return rekordy, pominiete


def _zbierz_kandydatow_crs(rekordy):
    """Pula kandydatów = unikalne CRS-y faktycznie zadeklarowane w .prj
    zbioru (zwykle kilka wariantów), a nie z góry narzucona lista stref.
    Zwraca listę (oryginalny_wkt, crs) - oryginalny tekst jest trzymany
    osobno, bo crs.toWkt() po przejściu przez silnik QGIS bywa
    przeformatowany i nie da się go już porównać tekstowo z .prj."""
    widziane = set()
    kandydaci = []
    for rek in rekordy:
        wkt = rek['wkt_zadeklarowany']
        if not wkt or wkt in widziane:
            continue
        widziane.add(wkt)
        crs = QgsCoordinateReferenceSystem.fromWkt(wkt)
        if crs.isValid():
            kandydaci.append((wkt, crs))
    return kandydaci


def _przygotuj_bufor_referencji(sciezka_ref, crs_docelowy):
    ref_lyr = QgsVectorLayer(sciezka_ref, 'ref', 'ogr')
    if not ref_lyr.isValid():
        raise RuntimeError(
            'Nie można wczytać warstwy referencyjnej: ' + sciezka_ref)

    transform = None
    if ref_lyr.crs().isValid() and ref_lyr.crs() != crs_docelowy:
        transform = QgsCoordinateTransform(
            ref_lyr.crs(), crs_docelowy, QgsProject.instance().transformContext())

    geoms = []
    for f in ref_lyr.getFeatures():
        g = f.geometry()
        if g is None or g.isEmpty():
            continue
        if transform is not None:
            g = QgsGeometry(g)
            g.transform(transform)
        geoms.append(g)
    if not geoms:
        raise RuntimeError(
            'Warstwa referencyjna nie zawiera geometrii: ' + sciezka_ref)

    return QgsGeometry.unaryUnion(geoms).buffer(PROG_BUFOR_M, 8)


def opisz_crs(crs):
    if crs is None:
        return '-'
    return crs.authid() or crs.description() or crs.toWkt()[:40]


def _wykryj_crs(rekord, kandydaci, bufor_ref, crs_docelowy):
    """Testuje surowy środek bboxa pliku pod każdym kandydującym CRS i
    wybiera ten, po którym środek ląduje w buforowanej referencji.
    Współrzędne w pliku są brane wprost (niezależnie od deklaracji .prj) -
    tylko tak można wykryć błędnie podpisany układ."""
    lyr = QgsVectorLayer(rekord['sciezka'], 'tmp', 'ogr')
    if not lyr.isValid() or lyr.featureCount() == 0:
        return None, 'PUSTA_LUB_NIEWALIDNA'

    srodek_surowy = lyr.extent().center()
    zadeklarowany_wkt = rekord['wkt_zadeklarowany']

    dopasowani = []
    for wkt_kandydata, crs in kandydaci:
        try:
            transform = QgsCoordinateTransform(
                crs, crs_docelowy, QgsProject.instance().transformContext())
            pkt = transform.transform(srodek_surowy)
        except Exception:
            continue
        if bufor_ref.contains(QgsGeometry.fromPointXY(pkt)):
            dopasowani.append((wkt_kandydata, crs))

    if not dopasowani:
        return None, 'DO_WERYFIKACJI'

    for wkt_kandydata, crs in dopasowani:
        if wkt_kandydata == zadeklarowany_wkt:
            return crs, 'OK_ZGODNY'

    return dopasowani[0][1], 'OK_POPRAWIONY'


def analizuj(katalog_zrodlowy, sciezka_referencji, postep=None):
    """Faza 1: klasyfikacja + wykrycie CRS. Niczego nie zapisuje.
    Zwraca (rekordy, pominiete) - rekordy mają dopisane 'crs_wykryty'
    (QgsCoordinateReferenceSystem albo None) i 'status'."""
    crs_docelowy = QgsCoordinateReferenceSystem('EPSG:2180')
    rekordy, pominiete = sklasyfikuj_pliki(katalog_zrodlowy)
    kandydaci = _zbierz_kandydatow_crs(rekordy)
    bufor_ref = _przygotuj_bufor_referencji(sciezka_referencji, crs_docelowy)

    n = max(len(rekordy), 1)
    for i, rek in enumerate(rekordy):
        crs, status = _wykryj_crs(rek, kandydaci, bufor_ref, crs_docelowy)
        rek['crs_wykryty'] = crs
        rek['status'] = status
        if postep is not None:
            postep.setValue(int(100 * i / n))

    return rekordy, pominiete


def _znajdz_duplikaty_geometryczne(layer, prog=PROG_DUPLIKATU, postep=None):
    """Self-join po indeksie przestrzennym: para poligonów jest duplikatem,
    jeśli część wspólna stanowi >= prog powierzchni mniejszego z nich.
    Zwraca fid-y do usunięcia (z każdej pary zostaje ten o niższym fid,
    czyli napotkany wcześniej przy scalaniu)."""
    si = QgsSpatialIndex()
    geoms = {}
    for f in layer.getFeatures():
        geoms[f.id()] = f.geometry()
        si.addFeature(f)

    usuniete = set()
    n = max(len(geoms), 1)
    for i, (fid, geom) in enumerate(geoms.items()):
        if fid in usuniete:
            continue
        for inny_fid in si.intersects(geom.boundingBox()):
            if inny_fid <= fid or inny_fid in usuniete:
                continue
            inny_geom = geoms[inny_fid]
            if not geom.intersects(inny_geom):
                continue
            try:
                wspolna = geom.intersection(inny_geom).area()
            except Exception:
                continue
            mniejsza = min(geom.area(), inny_geom.area())
            if mniejsza > 0 and wspolna / mniejsza >= prog:
                usuniete.add(inny_fid)
        if postep is not None and i % 200 == 0:
            postep.setValue(int(100 * i / n))

    return list(usuniete)


# Ta sama treść (TERYT działki: gmina.obręb.nr_działki) jest w dwóch polach
# pod różnymi nazwami zależnie od partii źródłowej: 'ID_DZ' (upul 12) i
# 'G5IDD' (upul 13/14) - inna konwencja nazewnictwa u dostawcy, nie różne
# dane. Pozostałe pola (NR_DZIALKI/NUMER, POW_EW/G5PEW, ...) mają ten sam
# problem, ale scalamy tu tylko to, o co poproszono - TERYT.
_POLA_TERYT_DZIALKI = ('ID_DZ', 'G5IDD')
_NAZWA_POLA_TERYT = 'TERYT'


def scal_teryt_dzialek(sciezka_shp):
    """W warstwie działek: scala ID_DZ/G5IDD do jednego pola TERYT (bierze
    pierwszą niepustą wartość) i usuwa wszystkie pozostałe atrybuty -
    w warstwie zostaje tylko geometria + TERYT."""
    lyr = QgsVectorLayer(sciezka_shp, 'x', 'ogr')
    nazwy_pol = lyr.fields().names()
    zrodlowe = [n for n in _POLA_TERYT_DZIALKI if n in nazwy_pol]
    if not zrodlowe:
        return

    lyr.startEditing()
    lyr.addAttribute(QgsField(_NAZWA_POLA_TERYT, QVariant.String, len=40))
    lyr.updateFields()

    idx_teryt = lyr.fields().indexFromName(_NAZWA_POLA_TERYT)
    idx_zrodlowe = [lyr.fields().indexFromName(n) for n in zrodlowe]
    for f in lyr.getFeatures():
        wartosc = next(
            (f.attributes()[i] for i in idx_zrodlowe
             if f.attributes()[i] not in (None, '')),
            None,
        )
        lyr.changeAttributeValue(f.id(), idx_teryt, wartosc)

    do_usuniecia = [
        i for i, n in enumerate(lyr.fields().names())
        if n != _NAZWA_POLA_TERYT
    ]
    lyr.deleteAttributes(do_usuniecia)
    lyr.updateFields()
    lyr.commitChanges()


# Pole z identyfikatorem "gmina.obręb.reszta" per grupa - to samo co scala
# scal_teryt_dzialek() dla działek; wydz nie ma żadnych atrybutów (patrz
# raport), więc nie da się jej podzielić wg gminy.
_POLE_IDENTYFIKATORA = {
    'dzialki': _NAZWA_POLA_TERYT,
    'uzytki': 'G5IDT',
    'klasouzytki': 'G5IDK',
}

# Znane błędne kody gminy w tych danych (rodzaj gminy podpisany źle u
# dostawcy) - "15_2"/"08_2" jako takie gminy nie istnieją, poprawne kody
# to "15_5"/"08_5".
_KOREKTY_GMINY = {
    '15_2': '15_5',
    '08_2': '08_5',
}


def dodaj_municip_community(sciezka_shp, pole_identyfikatora):
    """Dopisuje pola MUNICIP (gmina+rodzaj, 3 znaki) i COMMUNITY (obręb,
    4 znaki), wycięte z identyfikatora wg tej samej konwencji co
    shp_uzup_adradm.DopiszAdres: adr[4:8] to gmina (z podkreślnikiem do
    usunięcia), adr[9:13] to obręb. Po drodze poprawia znane błędne kody
    gminy (patrz _KOREKTY_GMINY) - zarówno w MUNICIP, jak i w samym
    identyfikatorze, żeby nie rozjechały się między sobą."""
    lyr = QgsVectorLayer(sciezka_shp, 'x', 'ogr')
    nazwy_pol = lyr.fields().names()
    if pole_identyfikatora not in nazwy_pol:
        return

    lyr.startEditing()
    for nazwa, dlugosc in (('MUNICIP', 3), ('COMMUNITY', 4)):
        if nazwa not in lyr.fields().names():
            lyr.addAttribute(QgsField(nazwa, QVariant.String, len=dlugosc))
    lyr.updateFields()

    idx_id = lyr.fields().indexFromName(pole_identyfikatora)
    idx_municip = lyr.fields().indexFromName('MUNICIP')
    idx_community = lyr.fields().indexFromName('COMMUNITY')

    for f in lyr.getFeatures():
        adr = f.attributes()[idx_id]
        if not adr or len(adr) < 14:
            continue

        gmina = adr[4:8]
        if gmina in _KOREKTY_GMINY:
            poprawiona = _KOREKTY_GMINY[gmina]
            adr = adr[:4] + poprawiona + adr[8:]
            lyr.changeAttributeValue(f.id(), idx_id, adr)
            gmina = poprawiona

        lyr.changeAttributeValue(f.id(), idx_municip, gmina.replace('_', ''))
        lyr.changeAttributeValue(f.id(), idx_community, adr[9:13])

    lyr.commitChanges()


def podziel_wg_municip(sciezka_shp, katalog_wyjsciowy):
    """Dzieli warstwę na osobne pliki wg pola MUNICIP - nazwa pliku dostaje
    sufiks = wartość MUNICIP, np. dzialki_POLYGON_155.shp.

    native:splitvectorlayer sam nazywa pliki wyjściowe wyłącznie wartością
    pola (np. "155.shp", bez nazwy warstwy) - trzeba je przenieść/
    przemianować do osobnego katalogu tymczasowego, inaczej wywołanie tej
    funkcji dla kolejnej grupy nadpisałoby pliki poprzedniej (ta sama
    gmina "155" wychodzi i w działkach, i w użytkach)."""
    bazowa_nazwa = os.path.splitext(os.path.basename(sciezka_shp))[0]
    tymczasowy = os.path.join(katalog_wyjsciowy, '_tmp_' + bazowa_nazwa)
    os.makedirs(tymczasowy, exist_ok=True)

    processing.run('native:splitvectorlayer', {
        'INPUT': sciezka_shp,
        'FIELD': 'MUNICIP',
        'PREFIX_FIELD': False,
        'FILE_TYPE': 1,  # shp
        'OUTPUT': tymczasowy,
    })

    wynikowe = []
    for plik in os.listdir(tymczasowy):
        wartosc, rozszerzenie = os.path.splitext(plik)
        docelowy = os.path.join(
            katalog_wyjsciowy, '%s_%s%s' % (bazowa_nazwa, wartosc, rozszerzenie))
        os.replace(os.path.join(tymczasowy, plik), docelowy)
        if rozszerzenie.lower() == '.shp':
            wynikowe.append(docelowy)
    os.rmdir(tymczasowy)
    return sorted(wynikowe)


def wykonaj(rekordy, katalog_wyjsciowy, postep=None):
    """Faza 2: dla każdej grupy - scal zakwalifikowane pliki (z wykrytym
    CRS wymuszonym przed scaleniem), usuń duplikaty geometrii, zapisz SHP.
    Zwraca słownik {grupa: {'sciezka', 'obiektow', 'duplikatow'}}."""
    crs_docelowy = QgsCoordinateReferenceSystem('EPSG:2180')
    os.makedirs(katalog_wyjsciowy, exist_ok=True)

    wg_grupy = {}
    for rek in rekordy:
        if rek.get('crs_wykryty') is None:
            continue
        wg_grupy.setdefault(rek['grupa'], []).append(rek)

    wynik = {}
    for grupa, rekordy_grupy in wg_grupy.items():
        warstwy = []
        for rek in rekordy_grupy:
            lyr = QgsVectorLayer(
                rek['sciezka'], os.path.basename(rek['sciezka'])[:-4], 'ogr')
            if not lyr.isValid():
                QgsMessageLog.logMessage(
                    'Pomijam nieprawidłową warstwę: ' + rek['sciezka'],
                    _LOG, Qgis.Warning)
                continue
            lyr.setCrs(rek['crs_wykryty'])
            warstwy.append(lyr)

        if not warstwy:
            continue

        sciezka_wyjsciowa = os.path.join(
            katalog_wyjsciowy, _NAZWA_WYNIKU[grupa])
        processing.run('native:mergevectorlayers', {
            'LAYERS': warstwy,
            'CRS': crs_docelowy,
            'OUTPUT': sciezka_wyjsciowa,
        })

        polaczona = QgsVectorLayer(sciezka_wyjsciowa, grupa, 'ogr')
        do_usuniecia = _znajdz_duplikaty_geometryczne(polaczona, postep=postep)
        if do_usuniecia:
            polaczona.startEditing()
            polaczona.deleteFeatures(do_usuniecia)
            polaczona.commitChanges()

        if grupa == 'dzialki':
            scal_teryt_dzialek(sciezka_wyjsciowa)
            polaczona = QgsVectorLayer(sciezka_wyjsciowa, grupa, 'ogr')

        pliki_wg_gminy = []
        if grupa in _POLE_IDENTYFIKATORA:
            dodaj_municip_community(
                sciezka_wyjsciowa, _POLE_IDENTYFIKATORA[grupa])
            pliki_wg_gminy = podziel_wg_municip(
                sciezka_wyjsciowa,
                os.path.join(katalog_wyjsciowy, 'wg_gminy'))

        wynik[grupa] = {
            'sciezka': sciezka_wyjsciowa,
            'obiektow': polaczona.featureCount(),
            'duplikatow': len(do_usuniecia),
            'zrodel': len(warstwy),
            'pliki_wg_gminy': pliki_wg_gminy,
        }
        QgsMessageLog.logMessage(
            'Grupa "%s": %d plików źródłowych -> %d obiektów '
            '(usunięto %d duplikatów) -> %s' % (
                grupa, len(warstwy), wynik[grupa]['obiektow'],
                len(do_usuniecia), sciezka_wyjsciowa),
            _LOG, Qgis.Info)

    return wynik


def zapisz_raport(sciezka, rekordy, pominiete, wynik_wykonania=None):
    linie = ['RAPORT SCALANIA WARSTW ZEWNĘTRZNYCH', '=' * 40, '']

    for grupa in ('dzialki', 'wydz', 'uzytki', 'klasouzytki'):
        z_grupy = [r for r in rekordy if r['grupa'] == grupa]
        if not z_grupy:
            continue
        linie.append('--- GRUPA: %s (%d plików) ---' % (grupa, len(z_grupy)))
        for r in z_grupy:
            crs_txt = opisz_crs(r['crs_wykryty'])
            linie.append('  [%s] %s -> %s' % (
                r['status'], r['sciezka'], crs_txt))
        linie.append('')

    if pominiete:
        linie.append('--- POMINIĘTE (poza zakresem, %d) ---' % len(pominiete))
        linie.extend('  ' + p for p in pominiete)
        linie.append('')

    if wynik_wykonania:
        linie.append('--- WYNIK SCALANIA ---')
        for grupa, info in wynik_wykonania.items():
            linie.append(
                '  %s: %d plików -> %d obiektów (usunięto %d duplikatów) '
                '-> %s' % (
                    grupa, info['zrodel'], info['obiektow'],
                    info['duplikatow'], info['sciezka']))
            if info.get('pliki_wg_gminy'):
                linie.append(
                    '    podzielono wg MUNICIP na %d plików w %s' % (
                        len(info['pliki_wg_gminy']),
                        os.path.dirname(info['pliki_wg_gminy'][0])))

    with open(sciezka, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(linie))


class ScalWalidacjaCRS(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(ScalWalidacjaCRS, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        self.rekordy = []
        self.pominiete = []

        self.pushButton_in.clicked.connect(
            lambda: self._wybierz_katalog(self.lineEdit_in))
        self.pushButton_out.clicked.connect(
            lambda: self._wybierz_katalog(self.lineEdit_out))
        self.pushButton_ref.clicked.connect(self._wybierz_referencje)
        self.pushButton_analizuj.clicked.connect(self.analizuj_klik)
        self.pushButton_wykonaj.clicked.connect(self.wykonaj_klik)

    def _wybierz_katalog(self, docelowy_lineedit):
        sc = QFileDialog.getExistingDirectory(self, 'Wybierz katalog')
        if not sc:
            return
        docelowy_lineedit.setText(sc)
        if docelowy_lineedit is self.lineEdit_in and \
                not self.lineEdit_out.text():
            self.lineEdit_out.setText(os.path.join(sc, '_scalone'))

    def _wybierz_referencje(self):
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wybierz warstwę referencyjną', '', 'Shapefile (*.shp)')
        if sc:
            self.lineEdit_ref.setText(sc)

    def _blad(self, tresc):
        QMessageBox.critical(self, 'Błąd', tresc)

    def analizuj_klik(self):
        katalog_in = self.lineEdit_in.text()
        sciezka_ref = self.lineEdit_ref.text()
        if not os.path.isdir(katalog_in):
            self._blad('Wskaż poprawny katalog źródłowy.')
            return
        if not os.path.isfile(sciezka_ref):
            self._blad('Wskaż poprawną warstwę referencyjną (.shp).')
            return

        pasek = PasekPostepu(self.iface)
        pasek.stworz_pasek('Analiza warstw...', 0, 100)
        try:
            self.rekordy, self.pominiete = analizuj(
                katalog_in, sciezka_ref, postep=pasek.progressBar)
        except Exception as e:
            self._blad('Analiza nie powiodła się: ' + str(e))
            QgsMessageLog.logMessage(
                'Błąd analizy: ' + str(e), _LOG, Qgis.Critical)
            return
        finally:
            pasek.clear()

        self._pokaz_wyniki()
        self.pushButton_wykonaj.setEnabled(bool(self.rekordy))

    def _pokaz_wyniki(self):
        table = self.tableWidget
        table.clear()
        headers = ['Grupa', 'Plik', 'Status', 'CRS wykryty']
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(self.rekordy))

        for row, r in enumerate(self.rekordy):
            crs_txt = opisz_crs(r['crs_wykryty'])
            for col, val in enumerate(
                    (r['grupa'], r['sciezka'], r['status'], crs_txt)):
                table.setItem(row, col, QTableWidgetItem(str(val)))
        table.resizeColumnsToContents()

        ile_ok = sum(1 for r in self.rekordy if r['crs_wykryty'] is not None)
        ile_popraw = sum(
            1 for r in self.rekordy if r['status'] == 'OK_POPRAWIONY')
        ile_weryf = sum(
            1 for r in self.rekordy if r['status'] == 'DO_WERYFIKACJI')
        self.label_podsumowanie.setText(
            'Znaleziono %d plików w zakresie (%d gotowych do scalenia, '
            'w tym %d z naprawionym CRS; %d do ręcznej weryfikacji; '
            '%d pominiętych poza zakresem).' % (
                len(self.rekordy), ile_ok, ile_popraw, ile_weryf,
                len(self.pominiete)))

    def wykonaj_klik(self):
        katalog_out = self.lineEdit_out.text()
        if not katalog_out:
            self._blad('Wskaż katalog wyjściowy.')
            return

        do_weryfikacji = [
            r for r in self.rekordy if r['status'] == 'DO_WERYFIKACJI']
        if do_weryfikacji:
            odp = QMessageBox.question(
                self, 'Pliki do weryfikacji',
                '%d plik(ów) nie udało się jednoznacznie dopasować do '
                'żadnego CRS i zostaną pominięte w scalaniu (patrz raport).'
                '\n\nKontynuować?' % len(do_weryfikacji),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if odp != QMessageBox.Yes:
                return

        pasek = PasekPostepu(self.iface)
        pasek.stworz_pasek('Scalanie warstw...', 0, 100)
        try:
            wynik = wykonaj(self.rekordy, katalog_out, postep=pasek.progressBar)
        except Exception as e:
            self._blad('Scalanie nie powiodło się: ' + str(e))
            QgsMessageLog.logMessage(
                'Błąd scalania: ' + str(e), _LOG, Qgis.Critical)
            return
        finally:
            pasek.clear()

        raport_sc = os.path.join(katalog_out, 'raport_scalania.txt')
        zapisz_raport(raport_sc, self.rekordy, self.pominiete, wynik)

        if wynik:
            self.iface.messageBar().pushSuccess(
                'Scalanie zakończone',
                'Zapisano %d grup(y) do "%s" (raport: %s)' % (
                    len(wynik), katalog_out, raport_sc))
        else:
            self.iface.messageBar().pushWarning(
                'Scalanie', 'Brak grup do zapisania — sprawdź raport.')

        QgsMessageLog.logMessage(
            'Zapisano raport: ' + raport_sc, _LOG, Qgis.Info)


def uruchom(iface):
    dlg = ScalWalidacjaCRS(iface)
    dlg.exec_()
