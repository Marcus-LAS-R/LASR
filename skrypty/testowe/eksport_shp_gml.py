# -*- coding: utf-8 -*-
r"""Eksport wybranych warstw EGiB z plikow GML (SWDE/EGiB) do SHP.

Skrypt testowy (menu Testowe wtyczki las_r.py).
Uzytkownik wskazuje dowolny folder startowy (np. "_Geodezja_oryginalna"
albo "__Geodezja_przerobiona" jakiegos obiektu) - skrypt rekurencyjnie
przechodzi cale drzewo pod nim. Kazdy folder, ktory BEZPOSREDNIO zawiera
>=1 plik .gml, jest jednostka przetwarzania: wszystkie .gml w nim sa
laczone w jeden zestaw per wybrana warstwa (dedup po polu identyfikatora,
np. idDzialki/idKonturu, a dla pozostalych warstw po gml_id), reprojekcja
do EPSG:2180 (uklad zrodlowy odczytywany automatycznie z kazdego GML -
moze byc rozny w roznych plikach/obiektach) i zapisane jako
<folder>/SHP/<NAZWA>.shp.

Opcja "Utworz warstwy polaczone": po przejsciu wszystkich folderow,
dodatkowo scala i dedupuje wyniki ze wszystkich folderow do jednego
<folder_startowy>/SHP_razem/<NAZWA>.shp per warstwa.

Lista warstw do wyboru budowana jest dynamicznie ze WSZYSTKICH plikow .gml
w drzewie (bezposrednio przez OGR): suma warstw ze wszystkich plikow, z
liczba obiektow i liczba plikow, w ktorych warstwa wystepuje. Rozne pliki
moga miec rozny zestaw warstw i rozny zapis nazwy (prefiks przestrzeni
nazw, wielkosc liter) - nazwy sa porownywane po normalizacji, a dla kazdego
pliku zapamietywana jest jego faktyczna nazwa warstwy, pod ktora eksport
ja otwiera. Warstwy z 0 obiektow nie sa pokazywane. Warstwy znane
(WARSTWY_ZNANE) dostaja czytelne etykiety/nazwy wyjsciowe; dzialki i
kontury sa domyslnie zaznaczone.

Uruchomienie w konsoli Python QGIS:
    exec(open(r'C:\Users\mmlyn\Lab\LASR\src\lasr\skrypty\testowe'
              r'\eksport_shp_gml.py', encoding='utf-8').read())
"""
import os
import re

from osgeo import ogr
from qgis.core import (
    Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature,
    QgsFields, QgsGeometry, QgsMessageLog, QgsProject,
    QgsVectorFileWriter, QgsVectorLayer, QgsWkbTypes,
)
from PyQt5.QtCore import QVariant, Qt
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QScrollArea, QVBoxLayout,
    QWidget,
)

_LOG = 'Las-R'
EPSG_DOCELOWY = 'EPSG:2180'
POLE_ID_DOMYSLNE = 'gml_id'

try:
    from lasr.skrypty.pw import PasekPostepu
except Exception:
    class _FikcyjnyPasek:
        def setValue(self, v):
            pass

        def setMaximum(self, v):
            pass

    class PasekPostepu:  # zapasowa wersja, gdy wtyczka nie jest zaladowana
        def __init__(self, iface):
            self.iface = iface
            self.progressBar = _FikcyjnyPasek()

        def stworz_pasek(self, tekst='', mini=0, maxi=100):
            self.progressBar.setMaximum(maxi)
            return self.progressBar

        def clear(self):
            pass


# nazwa podwarstwy GML -> (etykieta w GUI, nazwa wyjsciowa SHP, pole do
# deduplikacji, domyslnie zaznaczona). Dopasowanie po nazwie
# znormalizowanej (_klucz_nazwy). Pozostale wykryte warstwy dostaja surowa
# nazwe (bez prefiksu) jako etykiete/nazwe wyjsciowa i dedup po gml_id.
WARSTWY_ZNANE = {
    'EGB_DzialkaEwidencyjna': (
        'Dzialki ewidencyjne (EWID)', 'EWID', 'idDzialki', True),
    'EGB_KonturKlasyfikacyjny': (
        'Kontury klasyfikacyjne (KLU)', 'KLU', 'idKonturu', True),
    'EGB_PunktGraniczny': (
        'Punkty graniczne (PKT_GR)', 'PKT_GR', 'idPunktu', False),
    'EGB_OperatTechniczny': (
        'Operaty techniczne (OPERAT)', 'OPERAT', POLE_ID_DOMYSLNE, False),
    'PrezentacjaGraficzna': (
        'Prezentacja graficzna / etykiety (PREZENT)', 'PREZENT',
        POLE_ID_DOMYSLNE, False),
}


def _klucz_nazwy(nazwa):
    """Nazwa warstwy bez prefiksu przestrzeni nazw (np. 'egb:'), bez
    rozrozniania wielkosci liter - wspolny klucz dla tej samej warstwy
    zapisanej roznie w roznych plikach GML."""
    return nazwa.split(':')[-1].strip().lower()


_ZNANE_WG_KLUCZA = {_klucz_nazwy(n): n for n in WARSTWY_ZNANE}


def _bezpieczna_nazwa_pliku(nazwa):
    return re.sub(r'[^0-9A-Za-z_\-]+', '_', nazwa).strip('_') or 'warstwa'


def _opcje_zapisu():
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    return opcje


def znajdz_foldery_z_gml(katalog_startowy):
    """Zwraca liste (folder, [sciezki_gml]) dla kazdego folderu w drzewie
    pod katalog_startowy, ktory bezposrednio zawiera >=1 plik .gml."""
    wyniki = []
    for root, _dirs, files in os.walk(katalog_startowy):
        gmle = sorted(
            os.path.join(root, f) for f in files
            if f.lower().endswith('.gml'))
        if gmle:
            wyniki.append((root, gmle))
    return wyniki


def wykryj_warstwy_pliku(sciezka_gml):
    """Zwraca liste (nazwa_warstwy, liczba_obiektow, ma_geometrie) dla
    jednego pliku GML. Rzuca RuntimeError, gdy OGR nie otworzy pliku."""
    ds = ogr.Open(sciezka_gml, 0)
    if ds is None:
        raise RuntimeError('OGR nie otworzyl pliku')
    try:
        wynik = []
        for i in range(ds.GetLayerCount()):
            lyr = ds.GetLayerByIndex(i)
            liczba = lyr.GetFeatureCount()
            if liczba < 0:
                liczba = sum(1 for _ in lyr)
            ma_geom = lyr.GetGeomType() != ogr.wkbNone
            wynik.append((lyr.GetName(), liczba, ma_geom))
        return wynik
    finally:
        ds = None


def skanuj_warstwy(foldery, postep=None):
    """Skanuje wszystkie pliki .gml z listy foldery (wynik
    znajdz_foldery_z_gml) i zwraca (definicje, bledy):

    definicje = {klucz: {'etykieta', 'nazwa_wyj', 'pole_id', 'domyslnie',
                         'obiekty', 'ma_geom', 'pliki': {sciezka_gml:
                         nazwa_warstwy_w_tym_pliku}}}
    - tylko warstwy z >=1 obiektem, znane najpierw (kolejnosc
    WARSTWY_ZNANE), reszta alfabetycznie;
    bledy = [(sciezka_gml, komunikat)] dla plikow, ktorych nie dalo sie
    odczytac (skanowanie idzie dalej)."""
    pliki = [g for _f, gmle in foldery for g in gmle]
    zebrane = {}
    bledy = []
    for i, sciezka in enumerate(pliki):
        if postep is not None:
            postep(i, len(pliki), sciezka)
        try:
            warstwy_pliku = wykryj_warstwy_pliku(sciezka)
        except Exception as e:
            bledy.append((sciezka, str(e)))
            QgsMessageLog.logMessage(
                'Nie udalo sie odczytac warstw GML (%s): %s' % (sciezka, e),
                _LOG, Qgis.Warning)
            continue
        for nazwa, liczba, ma_geom in warstwy_pliku:
            if liczba <= 0:
                continue
            klucz = _klucz_nazwy(nazwa)
            dane = zebrane.setdefault(klucz, {
                'nazwa': nazwa.split(':')[-1].strip(),
                'obiekty': 0, 'ma_geom': False, 'pliki': {}})
            dane['obiekty'] += liczba
            dane['ma_geom'] = dane['ma_geom'] or ma_geom
            dane['pliki'][sciezka] = nazwa

    definicje = {}
    uzyte_nazwy_wyj = set()
    znane_klucze = [_klucz_nazwy(n) for n in WARSTWY_ZNANE]
    kolejnosc = [k for k in znane_klucze if k in zebrane] + sorted(
        (k for k in zebrane if k not in znane_klucze),
        key=lambda k: zebrane[k]['nazwa'].lower())
    for klucz in kolejnosc:
        dane = zebrane[klucz]
        if klucz in _ZNANE_WG_KLUCZA:
            etykieta, nazwa_wyj, pole_id, domyslnie = \
                WARSTWY_ZNANE[_ZNANE_WG_KLUCZA[klucz]]
        else:
            etykieta = dane['nazwa']
            nazwa_wyj = _bezpieczna_nazwa_pliku(dane['nazwa'])
            pole_id, domyslnie = POLE_ID_DOMYSLNE, False
        baza, nr = nazwa_wyj, 2
        while nazwa_wyj.lower() in uzyte_nazwy_wyj:
            nazwa_wyj = '%s_%d' % (baza, nr)
            nr += 1
        uzyte_nazwy_wyj.add(nazwa_wyj.lower())
        definicje[klucz] = {
            'etykieta': etykieta, 'nazwa_wyj': nazwa_wyj,
            'pole_id': pole_id, 'domyslnie': domyslnie,
            'obiekty': dane['obiekty'], 'ma_geom': dane['ma_geom'],
            'pliki': dane['pliki']}
    return definicje, bledy


def _otworz_podwarstwe(sciezka_gml, nazwa_podwarstwy):
    uri = '%s|layername=%s' % (sciezka_gml, nazwa_podwarstwy)
    lyr = QgsVectorLayer(uri, nazwa_podwarstwy, 'ogr')
    if not lyr.isValid() or lyr.featureCount() == 0:
        return None
    return lyr


def _pole_string(nazwa):
    from qgis.core import QgsField
    return QgsField(name=nazwa, type=QVariant.String, len=254)


_TYPY_LISTOWE = (QVariant.StringList, QVariant.List)


def _scal_schemat_pol(warstwy):
    """Zwraca QgsFields = suma pol wszystkich warstw (po nazwie). Rozne
    partie GML od roznych dostawcow/z roznych lat potrafia miec dla tej
    samej nazwy pola inny typ (np. raz String, raz Double, raz lista -
    gdy dzialka ma kilka klasouzytkow "wtopionych" w ten sam rekord bez
    osobnego obiektu EGB_KonturKlasyfikacyjny) i rozne dlugosci (np. OFU
    zwykle 2 znaki, ale w formie listy - "['Ls', 'Ps']" - dużo wiecej).
    Kazde pole typu string/lista dostaje od razu szeroki String(254),
    niezaleznie od zrodla - eliminuje to zarowno konflikt typu, jak i
    przycinanie do waskiej, "przypadkowej" dlugosci z pierwszego zrodla."""
    lista = []  # lista QgsField w kolejnosci pierwszego wystapienia
    indeks_wg_nazwy = {}
    for w in warstwy:
        for pole in w.fields():
            if pole.type() == QVariant.String or pole.type() in \
                    _TYPY_LISTOWE:
                docelowe = _pole_string(pole.name())
            else:
                docelowe = pole

            if pole.name() not in indeks_wg_nazwy:
                indeks_wg_nazwy[pole.name()] = len(lista)
                lista.append(docelowe)
            else:
                idx = indeks_wg_nazwy[pole.name()]
                if lista[idx].type() != docelowe.type():
                    lista[idx] = _pole_string(pole.name())

    pola_docelowe = QgsFields()
    for pole in lista:
        pola_docelowe.append(pole)
    return pola_docelowe


def _typ_geometrii(warstwy):
    """Typ geometrii (multi) do zapisu. Warstwa GML o mieszanej/nieznanej
    geometrii ma wkbType Unknown, z ktorym sterownik SHP nie utworzy pliku -
    wtedy typ brany jest z pierwszej niepustej geometrii."""
    for w in warstwy:
        typ = QgsWkbTypes.flatType(w.wkbType())
        if typ != QgsWkbTypes.Unknown:
            return QgsWkbTypes.multiType(typ)
    for w in warstwy:
        for f in w.getFeatures():
            g = f.geometry()
            if g is not None and not g.isEmpty():
                return QgsWkbTypes.multiType(QgsWkbTypes.flatType(g.wkbType()))
    return QgsWkbTypes.NoGeometry


def _zapisz_polaczone(warstwy, sciezka, pole_id):
    """Zapisuje polaczone i - jesli podano pole_id i warstwy je maja -
    zdedupowane obiekty ze wszystkich warstw wprost do pliku SHP
    (reprojekcja kazdego zrodla do EPSG:2180 w locie). Pisze bezposrednio
    przez QgsVectorFileWriter, a nie przez posrednia warstwe 'memory' -
    dostawca 'memory' okazal sie w testach na realnych danych (kilka .gml w
    jednym folderze, rozne partie EGiB) zbyt scisly przy niezgodnosciach
    typu atrybutu miedzy zrodlami i po cichu odrzucal wiekszosc obiektow
    (prov.addFeature() -> False bez wyjatku); QgsVectorFileWriter.addFeature()
    jest w tym tolerancyjny. Obiekty z pustym identyfikatorem nie sa
    deduplikowane. Zwraca liczbe zapisanych obiektow albo None, jesli nic
    nie zapisano."""
    crs_docelowy = QgsCoordinateReferenceSystem(EPSG_DOCELOWY)
    pola_docelowe = _scal_schemat_pol(warstwy)
    typ_geom = _typ_geometrii(warstwy)

    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    writer = QgsVectorFileWriter.create(
        sciezka, pola_docelowe, typ_geom, crs_docelowy,
        QgsProject.instance().transformContext(), _opcje_zapisu())
    if writer.hasError() != QgsVectorFileWriter.NoError:
        QgsMessageLog.logMessage(
            'Nie udalo sie utworzyc %s: %s' % (
                sciezka, writer.errorMessage()), _LOG, Qgis.Critical)
        return None

    idx_id = pola_docelowe.indexFromName(pole_id) if pole_id else -1
    widziane = set()
    zapisano = 0
    for w in warstwy:
        transform = None
        if w.crs().isValid() and w.crs() != crs_docelowy:
            transform = QgsCoordinateTransform(
                w.crs(), crs_docelowy,
                QgsProject.instance().transformContext())
        mapowanie = [
            pola_docelowe.indexFromName(p.name()) for p in w.fields()]

        for f in w.getFeatures():
            atrybuty = [None] * len(pola_docelowe)
            for src_idx, dst_idx in enumerate(mapowanie):
                if dst_idx < 0:
                    continue
                wartosc = f.attributes()[src_idx]
                typ_docelowy = pola_docelowe.at(dst_idx).type()
                if isinstance(wartosc, (list, tuple)):
                    # sterownik GML/OGR bywa niespojny - to samo pole raz
                    # zwraca skalar, raz liste (dzialka z kilkoma
                    # klasouzytkami "wtopionymi" w ten sam rekord); pole
                    # docelowe string ma miejsce (patrz _scal_schemat_pol),
                    # numeryczne nie da sie sensownie zrzutowac - puste
                    wartosc = str(wartosc) \
                        if typ_docelowy == QVariant.String else None
                elif wartosc is not None and \
                        typ_docelowy == QVariant.String and \
                        not isinstance(wartosc, str):
                    wartosc = str(wartosc)
                atrybuty[dst_idx] = wartosc

            if idx_id >= 0:
                klucz = atrybuty[idx_id]
                if klucz not in (None, ''):
                    if klucz in widziane:
                        continue
                    widziane.add(klucz)

            geom = f.geometry()
            if geom is not None and not geom.isEmpty():
                geom = QgsGeometry(geom)
                geom.convertToMultiType()
                if transform is not None:
                    geom.transform(transform)

            nf = QgsFeature(pola_docelowe)
            nf.setGeometry(geom)
            nf.setAttributes(atrybuty)
            if writer.addFeature(nf):
                zapisano += 1
            else:
                QgsMessageLog.logMessage(
                    'Pominieto obiekt z %s - blad zapisu: %s' % (
                        w.name(), writer.errorMessage()), _LOG,
                    Qgis.Warning)

    del writer
    return zapisano or None


def eksportuj_warstwe(gml_pliki, nazwy_w_plikach, pole_id,
                       sciezka_wyjsciowa):
    """Laczy dana warstwe ze wszystkich gml_pliki (kazdy plik otwierany pod
    swoja nazwa warstwy z nazwy_w_plikach; pliki bez tej warstwy sa
    pomijane), reprojekcja do EPSG:2180, dedup po pole_id i zapis do
    sciezka_wyjsciowa. Zwraca liczbe zapisanych obiektow albo None, jesli
    w tych plikach nie bylo takiej warstwy."""
    warstwy = []
    for g in gml_pliki:
        nazwa = nazwy_w_plikach.get(g)
        if nazwa is None:
            continue
        w = _otworz_podwarstwe(g, nazwa)
        if w is not None:
            warstwy.append(w)
    if not warstwy:
        return None
    return _zapisz_polaczone(warstwy, sciezka_wyjsciowa, pole_id)


def przetworz_folder(folder, gml_pliki, definicje_warstw, wybrane,
                      log=print):
    """Eksportuje wybrane warstwy dla jednego folderu do <folder>/SHP/.
    Zwraca slownik {klucz_warstwy: sciezka_shp} dla warstw faktycznie
    zapisanych (pomija te bez zrodlowych danych w tym folderze)."""
    kat_wyj = os.path.join(folder, 'SHP')
    zapisane = {}
    for klucz in wybrane:
        d = definicje_warstw[klucz]
        sciezka = os.path.join(kat_wyj, d['nazwa_wyj'] + '.shp')
        liczba = eksportuj_warstwe(
            gml_pliki, d['pliki'], d['pole_id'], sciezka)
        if liczba is None:
            log('  [%s] brak danych w tym folderze - pominieto'
                % d['etykieta'])
            continue
        log('  [%s] %d obiektow -> %s' % (d['etykieta'], liczba, sciezka))
        zapisane[klucz] = sciezka
    return zapisane


def polacz_wyniki(wszystkie_zapisane, definicje_warstw, wybrane,
                   katalog_startowy, log=print):
    """Dla kazdej wybranej warstwy scala i dedupuje SHP zapisane we
    wszystkich folderach do <katalog_startowy>/SHP_razem/."""
    kat_wyj = os.path.join(katalog_startowy, 'SHP_razem')
    for klucz in wybrane:
        d = definicje_warstw[klucz]
        sciezki = [z[klucz] for z in wszystkie_zapisane if klucz in z]
        if not sciezki:
            continue

        # warstwa bez geometrii zapisuje sie jako sam .dbf (bez .shp)
        sciezki = [
            s if os.path.exists(s) else os.path.splitext(s)[0] + '.dbf'
            for s in sciezki]
        warstwy = [
            QgsVectorLayer(s, os.path.basename(s), 'ogr') for s in sciezki]
        warstwy = [w for w in warstwy if w.isValid()]
        if not warstwy:
            continue

        sciezka_wyj = os.path.join(kat_wyj, d['nazwa_wyj'] + '.shp')
        liczba = _zapisz_polaczone(warstwy, sciezka_wyj, d['pole_id'])
        log('[SHP_razem] [%s] %s obiektow -> %s' % (
            d['etykieta'], liczba if liczba is not None else '?',
            sciezka_wyj))


class EksportSHPzGML(QDialog):
    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle('Wyeksportuj SHP z GML')
        self.definicje_warstw = {}
        self.checkboxy = {}
        self.skanowany_folder = None

        glowny = QVBoxLayout(self)

        wiersz_folder = QHBoxLayout()
        self.pole_folder = QLineEdit()
        przycisk_folder = QPushButton('Przegladaj...')
        przycisk_folder.clicked.connect(self._wybierz_folder)
        wiersz_folder.addWidget(QLabel('Folder startowy (geodezja):'))
        wiersz_folder.addWidget(self.pole_folder)
        wiersz_folder.addWidget(przycisk_folder)
        glowny.addLayout(wiersz_folder)

        self.grupa_warstw = QGroupBox('Warstwy do eksportu')
        layout_grupy = QVBoxLayout(self.grupa_warstw)
        przewijanie = QScrollArea()
        przewijanie.setWidgetResizable(True)
        kontener = QWidget()
        self.layout_warstw = QVBoxLayout(kontener)
        self.layout_warstw.setAlignment(Qt.AlignTop)
        przewijanie.setWidget(kontener)
        layout_grupy.addWidget(przewijanie)

        wiersz_zazn = QHBoxLayout()
        przycisk_wszystkie = QPushButton('Zaznacz wszystkie')
        przycisk_wszystkie.clicked.connect(lambda: self._zaznacz(True))
        przycisk_zadne = QPushButton('Odznacz wszystkie')
        przycisk_zadne.clicked.connect(lambda: self._zaznacz(False))
        wiersz_zazn.addWidget(przycisk_wszystkie)
        wiersz_zazn.addWidget(przycisk_zadne)
        wiersz_zazn.addStretch()
        layout_grupy.addLayout(wiersz_zazn)
        glowny.addWidget(self.grupa_warstw, 1)

        self.etykieta_pusta = QLabel(
            'Wskaz folder - lista warstw zostanie wczytana z plikow GML.')
        self.layout_warstw.addWidget(self.etykieta_pusta)

        self.checkbox_razem = QCheckBox(
            'Utworz warstwy polaczone (SHP_razem)')
        glowny.addWidget(self.checkbox_razem)

        self.etykieta_status = QLabel('')
        self.etykieta_status.setWordWrap(True)
        glowny.addWidget(self.etykieta_status)

        wiersz_przyciskow = QHBoxLayout()
        przycisk_uruchom = QPushButton('Uruchom')
        przycisk_uruchom.clicked.connect(self._uruchom_klik)
        przycisk_zamknij = QPushButton('Zamknij')
        przycisk_zamknij.clicked.connect(self.reject)
        wiersz_przyciskow.addWidget(przycisk_uruchom)
        wiersz_przyciskow.addWidget(przycisk_zamknij)
        glowny.addLayout(wiersz_przyciskow)

        self.resize(640, 520)

    def _zaznacz(self, stan):
        for cb in self.checkboxy.values():
            cb.setChecked(stan)

    def _zbuduj_checkboxy(self, definicje, liczba_plikow):
        for cb in self.checkboxy.values():
            cb.setParent(None)
        self.checkboxy = {}
        self.etykieta_pusta.setVisible(not definicje)
        if not definicje:
            self.etykieta_pusta.setText(
                'W plikach GML nie znaleziono zadnej niepustej warstwy.')
        for klucz, d in definicje.items():
            opis = '%s  —  %d ob., w %d z %d plik(ow)' % (
                d['etykieta'], d['obiekty'], len(d['pliki']), liczba_plikow)
            if not d['ma_geom']:
                opis += '  (bez geometrii - tylko DBF)'
            cb = QCheckBox(opis)
            cb.setChecked(d['domyslnie'])
            self.layout_warstw.addWidget(cb)
            self.checkboxy[klucz] = cb
        self.definicje_warstw = definicje

    def _skanuj(self, katalog):
        """Skanuje pliki GML pod katalog i przebudowuje liste warstw.
        Zwraca liste folderow z GML (pusta = brak plikow)."""
        foldery = znajdz_foldery_z_gml(katalog)
        if not foldery:
            self._zbuduj_checkboxy({}, 0)
            self.skanowany_folder = None
            QMessageBox.warning(
                self, 'Brak danych',
                'W wybranym folderze nie znaleziono zadnego pliku .gml.')
            return foldery

        def postep(i, n, sciezka):
            self.etykieta_status.setText(
                'Wczytywanie warstw: plik %d/%d - %s' % (
                    i + 1, n, os.path.basename(sciezka)))
            QApplication.processEvents()

        liczba_plikow = sum(len(g) for _f, g in foldery)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            definicje, bledy = skanuj_warstwy(foldery, postep)
        finally:
            QApplication.restoreOverrideCursor()

        self._zbuduj_checkboxy(definicje, liczba_plikow)
        self.skanowany_folder = os.path.normcase(os.path.abspath(katalog))
        status = ('Znaleziono %d folder(ow), %d plik(ow) .gml, %d warstw(y).'
                  % (len(foldery), liczba_plikow, len(definicje)))
        if bledy:
            status += ' Nie odczytano %d plik(ow) - szczegoly w Dzienniku ' \
                      'komunikatow (Las-R).' % len(bledy)
            QMessageBox.warning(
                self, 'Bledy odczytu GML',
                'Nie udalo sie odczytac %d plik(ow):\n%s' % (
                    len(bledy), '\n'.join(
                        '%s: %s' % (os.path.basename(s), k)
                        for s, k in bledy[:15])))
        self.etykieta_status.setText(status)
        return foldery

    def _wybierz_folder(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wybierz folder z geodezja')
        if not sc:
            return
        self.pole_folder.setText(sc)
        self._skanuj(sc)

    def _log(self, tekst):
        QgsMessageLog.logMessage(tekst, _LOG, Qgis.Info)
        self.etykieta_status.setText(tekst)
        QApplication.processEvents()

    def _uruchom_klik(self):
        katalog_startowy = self.pole_folder.text()
        if not os.path.isdir(katalog_startowy):
            QMessageBox.critical(
                self, 'Blad', 'Wskaz poprawny folder startowy.')
            return

        if os.path.normcase(os.path.abspath(katalog_startowy)) != \
                self.skanowany_folder:
            # folder wpisany recznie / zmieniony - lista warstw nieaktualna
            if self._skanuj(katalog_startowy):
                QMessageBox.information(
                    self, 'Lista warstw odswiezona',
                    'Wczytano warstwy z plikow GML we wskazanym folderze. '
                    'Sprawdz wybor warstw i uruchom ponownie.')
            return

        wybrane = [n for n, cb in self.checkboxy.items() if cb.isChecked()]
        if not wybrane:
            QMessageBox.critical(
                self, 'Blad',
                'Zaznacz co najmniej jedna warstwe do eksportu.')
            return

        foldery = znajdz_foldery_z_gml(katalog_startowy)
        if not foldery:
            QMessageBox.warning(
                self, 'Brak danych', 'Nie znaleziono zadnego pliku .gml.')
            return

        pasek = None
        if self.iface is not None:
            pasek = PasekPostepu(self.iface)
            pasek.stworz_pasek('Eksport SHP z GML...', 0, len(foldery))

        wszystkie_zapisane = []
        try:
            for i, (folder, gml_pliki) in enumerate(foldery):
                self._log('Folder %d/%d: %s (%d plik(ow) .gml)' % (
                    i + 1, len(foldery), folder, len(gml_pliki)))
                zapisane = przetworz_folder(
                    folder, gml_pliki, self.definicje_warstw, wybrane,
                    log=self._log)
                wszystkie_zapisane.append(zapisane)
                if pasek is not None:
                    pasek.progressBar.setValue(i + 1)

            if self.checkbox_razem.isChecked():
                self._log('Scalanie warstw do SHP_razem...')
                polacz_wyniki(
                    wszystkie_zapisane, self.definicje_warstw, wybrane,
                    katalog_startowy, log=self._log)
        except Exception as e:
            QgsMessageLog.logMessage(
                'Blad eksportu SHP z GML: %s' % e, _LOG, Qgis.Critical)
            QMessageBox.critical(
                self, 'Blad', 'Eksport przerwany bledem:\n%s' % e)
            return
        finally:
            if pasek is not None:
                pasek.clear()

        QMessageBox.information(
            self, 'Gotowe', 'Przetworzono %d folder(ow).' % len(foldery))


def uruchom(iface=None):
    dlg = EksportSHPzGML(iface)
    dlg.exec_()
