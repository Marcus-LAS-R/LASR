# -*- coding: utf-8 -*-
r"""Eksport wybranych warstw EGiB z plikow GML (SWDE/EGiB) do SHP.

Skrypt testowy/samodzielny (NIE wpiety do menu wtyczki las_r.py).
Uzytkownik wskazuje dowolny folder startowy (np. "_Geodezja_oryginalna"
albo "__Geodezja_przerobiona" jakiegos obiektu) - skrypt rekurencyjnie
przechodzi cale drzewo pod nim. Kazdy folder, ktory BEZPOSREDNIO zawiera
>=1 plik .gml, jest jednostka przetwarzania: wszystkie .gml w nim sa
laczone w jeden zestaw per wybrana warstwa (dedup po polu identyfikatora
GML, np. idDzialki/idKonturu), reprojekcja do EPSG:2180 (uklad zrodlowy
odczytywany automatycznie z kazdego GML - moze byc rozny w roznych
plikach/obiektach) i zapisane jako <folder>/SHP/<NAZWA>.shp.

Opcja "Utworz warstwy polaczone": po przejsciu wszystkich folderow,
dodatkowo scala i dedupuje wyniki ze wszystkich folderow do jednego
<folder_startowy>/SHP_razem/<NAZWA>.shp per warstwa.

Lista warstw do wyboru budowana jest dynamicznie z pierwszego napotkanego
pliku .gml (QgsProviderRegistry.querySublayers) - dziala wiec z kazdym
obiektem EGiB GML, nie tylko z ukladem widocznym w Nowym Targu, przy
czym dwie warstwy najczesciej potrzebne (dzialki ewidencyjne, kontury
klasyfikacyjne) maja przygotowane czytelne etykiety/nazwy wyjsciowe i sa
domyslnie zaznaczone - pozostale wykryte podwarstwy pojawiaja sie z
surowa nazwa GML i sa domyslnie odznaczone.

Uruchomienie w konsoli Python QGIS:
    exec(open(r'C:\Users\mmlyn\Lab\LASR\src\lasr\skrypty\testowe'
              r'\eksport_shp_gml.py', encoding='utf-8').read())
"""
import os

from qgis.core import (
    Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature,
    QgsFields, QgsGeometry, QgsMessageLog, QgsProject, QgsProviderRegistry,
    QgsVectorFileWriter, QgsVectorLayer, QgsWkbTypes,
)
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (
    QApplication, QCheckBox, QDialog, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

_LOG = 'Las-R'
EPSG_DOCELOWY = 'EPSG:2180'

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
# deduplikacji, domyslnie zaznaczona). Podwarstwy wykryte w konkretnym
# pliku, a nieujete tutaj, doklejane sa dynamicznie (patrz
# zbuduj_definicje_warstw) z surowa nazwa GML jako etykieta/nazwa
# wyjsciowa i bez deduplikacji (dedup tylko tam, gdzie znane jest pole
# identyfikatora).
WARSTWY_ZNANE = {
    'EGB_DzialkaEwidencyjna': (
        'Dzialki ewidencyjne (EWID)', 'EWID', 'idDzialki', True),
    'EGB_KonturKlasyfikacyjny': (
        'Kontury klasyfikacyjne (KLU)', 'KLU', 'idKonturu', True),
    'EGB_PunktGraniczny': (
        'Punkty graniczne (PKT_GR)', 'PKT_GR', 'idPunktu', False),
    'EGB_OperatTechniczny': (
        'Operaty techniczne (OPERAT)', 'OPERAT', None, False),
    'PrezentacjaGraficzna': (
        'Prezentacja graficzna / etykiety (PREZENT)', 'PREZENT', None,
        False),
}


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


def wykryj_podwarstwy(sciezka_gml):
    """Zwraca liste nazw podwarstw dostepnych w pliku GML, albo None,
    jesli wykrycie sie nie powiodlo (nie blokuje dzialania skryptu -
    wywolujacy spada wtedy na WARSTWY_ZNANE)."""
    try:
        szczegoly = QgsProviderRegistry.instance().querySublayers(
            sciezka_gml)
        nazwy = sorted({s.name() for s in szczegoly if s.name()})
        return nazwy or None
    except Exception as e:
        QgsMessageLog.logMessage(
            'Nie udalo sie wykryc podwarstw GML (%s): %s' % (
                sciezka_gml, e), _LOG, Qgis.Warning)
        return None


def zbuduj_definicje_warstw(sciezka_gml_probka):
    """Zwraca slownik {nazwa_podwarstwy: (etykieta, nazwa_wyjsciowa,
    pole_id, domyslnie)} - znane warstwy z WARSTWY_ZNANE (jesli obecne w
    probce) + reszta wykrytych podwarstw z surowa nazwa GML, bez dedupu,
    domyslnie odznaczone."""
    wykryte = wykryj_podwarstwy(sciezka_gml_probka)
    if wykryte is None:
        return dict(WARSTWY_ZNANE)

    definicje = {}
    for nazwa in wykryte:
        definicje[nazwa] = WARSTWY_ZNANE.get(
            nazwa, (nazwa, nazwa, None, False))
    return definicje


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


def _zapisz_polaczone(warstwy, sciezka, pole_id):
    """Zapisuje polaczone i - jesli podano pole_id - zdedupowane obiekty ze
    wszystkich warstw wprost do pliku SHP (reprojekcja kazdego zrodla do
    EPSG:2180 w locie). Pisze bezposrednio przez QgsVectorFileWriter, a nie
    przez posrednia warstwe 'memory' - dostawca 'memory' okazal sie w
    testach na realnych danych (kilka .gml w jednym folderze, rozne partie
    EGiB) zbyt scisly przy niezgodnosciach typu atrybutu miedzy zrodlami i
    po cichu odrzucal wiekszosc obiektow (prov.addFeature() -> False bez
    wyjatku); QgsVectorFileWriter.addFeature() jest w tym tolerancyjny.
    Zwraca liczbe zapisanych obiektow albo None, jesli nic nie zapisano."""
    crs_docelowy = QgsCoordinateReferenceSystem(EPSG_DOCELOWY)
    pola_docelowe = _scal_schemat_pol(warstwy)
    typ_bazowy = QgsWkbTypes.flatType(warstwy[0].wkbType())
    typ_geom = QgsWkbTypes.multiType(typ_bazowy)

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


def eksportuj_warstwe(gml_pliki, nazwa_podwarstwy, pole_id,
                       sciezka_wyjsciowa):
    """Laczy dana podwarstwe ze wszystkich gml_pliki (reprojekcja do
    EPSG:2180), dedupuje po pole_id (jesli podane i obecne w wynikowych
    polach) i zapisuje do sciezka_wyjsciowa. Zwraca liczbe zapisanych
    obiektow albo None, jesli w tych plikach nie bylo takiej podwarstwy."""
    warstwy = [w for w in (
        _otworz_podwarstwe(g, nazwa_podwarstwy) for g in gml_pliki)
        if w is not None]
    if not warstwy:
        return None
    return _zapisz_polaczone(warstwy, sciezka_wyjsciowa, pole_id)


def przetworz_folder(folder, gml_pliki, definicje_warstw, wybrane,
                      log=print):
    """Eksportuje wybrane warstwy dla jednego folderu do <folder>/SHP/.
    Zwraca slownik {nazwa_podwarstwy: sciezka_shp} dla warstw faktycznie
    zapisanych (pomija te bez zrodlowych danych w tym folderze)."""
    kat_wyj = os.path.join(folder, 'SHP')
    zapisane = {}
    for nazwa_podwarstwy in wybrane:
        etykieta, nazwa_wyj, pole_id, _ = definicje_warstw[nazwa_podwarstwy]
        sciezka = os.path.join(kat_wyj, nazwa_wyj + '.shp')
        liczba = eksportuj_warstwe(
            gml_pliki, nazwa_podwarstwy, pole_id, sciezka)
        if liczba is None:
            log('  [%s] brak danych w tym folderze - pominieto' % etykieta)
            continue
        log('  [%s] %d obiektow -> %s' % (etykieta, liczba, sciezka))
        zapisane[nazwa_podwarstwy] = sciezka
    return zapisane


def polacz_wyniki(wszystkie_zapisane, definicje_warstw, wybrane,
                   katalog_startowy, log=print):
    """Dla kazdej wybranej warstwy scala i dedupuje SHP zapisane we
    wszystkich folderach do <katalog_startowy>/SHP_razem/."""
    kat_wyj = os.path.join(katalog_startowy, 'SHP_razem')
    for nazwa_podwarstwy in wybrane:
        etykieta, nazwa_wyj, pole_id, _ = definicje_warstw[nazwa_podwarstwy]
        sciezki = [
            z[nazwa_podwarstwy] for z in wszystkie_zapisane
            if nazwa_podwarstwy in z]
        if not sciezki:
            continue

        warstwy = [
            QgsVectorLayer(s, os.path.basename(s), 'ogr') for s in sciezki]
        warstwy = [w for w in warstwy if w.isValid()]
        if not warstwy:
            continue

        sciezka_wyj = os.path.join(kat_wyj, nazwa_wyj + '.shp')
        liczba = _zapisz_polaczone(warstwy, sciezka_wyj, pole_id)
        log('[SHP_razem] [%s] %s obiektow -> %s' % (
            etykieta, liczba if liczba is not None else '?', sciezka_wyj))


class EksportSHPzGML(QDialog):
    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle('Wyeksportuj SHP z GML')
        self.definicje_warstw = dict(WARSTWY_ZNANE)
        self.checkboxy = {}

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
        self.layout_warstw = QVBoxLayout(self.grupa_warstw)
        glowny.addWidget(self.grupa_warstw)
        self._zbuduj_checkboxy(WARSTWY_ZNANE)

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

        self.resize(560, 360)

    def _zbuduj_checkboxy(self, definicje):
        for cb in self.checkboxy.values():
            cb.setParent(None)
        self.checkboxy = {}
        for nazwa_podwarstwy, dane in definicje.items():
            etykieta, _nazwa_wyj, _pole_id, domyslnie = dane
            cb = QCheckBox(etykieta)
            cb.setChecked(domyslnie)
            self.layout_warstw.addWidget(cb)
            self.checkboxy[nazwa_podwarstwy] = cb
        self.definicje_warstw = definicje

    def _wybierz_folder(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wybierz folder z geodezja')
        if not sc:
            return
        self.pole_folder.setText(sc)

        foldery = znajdz_foldery_z_gml(sc)
        if not foldery:
            QMessageBox.warning(
                self, 'Brak danych',
                'W wybranym folderze nie znaleziono zadnego pliku .gml.')
            return

        probka = foldery[0][1][0]
        definicje = zbuduj_definicje_warstw(probka)
        self._zbuduj_checkboxy(definicje)
        self.etykieta_status.setText(
            'Znaleziono %d folder(ow) z plikami .gml (probka: %s).' % (
                len(foldery), os.path.basename(probka)))

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
