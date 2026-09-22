# -*- coding: utf-8 -*-
"""Rozdziela zbiorcze warstwy DZKAT/LS/LZ_potencjalne/OBR na poszczegolne
foldery wg baz danych (.mdb).

Uzytkownik wskazuje folder nadrzedny, w ktorym bezposrednio leza zbiorcze
warstwy (DZKAT.shp/LS.shp/LZ_potencjalne.shp/OBR.shp - te, ktore akurat
istnieja) i obok - podfoldery (np. po wlasnosci/wspolnocie), kazdy z
wlasna baza .mdb (tabela F_PARCEL: COUNTY_CD/DISTRICT_CD/MUNICIPALITY_CD/
COMMUNITY_CD/PARCEL_NR - lista dzialek nalezacych do tej bazy).

Dla kazdego podfolderu:
  - DZKAT/LS/LZ_potencjalne: obiekty, ktorych krotka (COUNTY, DISTRICT,
    MUNICIP, COMMUNITY, PARCELNR) jest w liscie dzialek z bazy.
  - OBR (granica obrebu, bez numeru dzialki): caly poligon obrebu, jesli
    baza ma choc jedna dzialke z tego (MUNICIP, COMMUNITY) - dopasowanie
    przez pole G5NRO (rozbij_adres_gmina_obreb).
  - dotaks: pominiety (to poziom wydzielen, nie dzialek - inny sposob
    dopasowania, poza zakresem na razie).

Wynik: <podfolder>/SHP/<NAZWA>.shp per warstwa.

Skrypt testowy/samodzielny - wpiety w menu Testowe w las_r.py.
"""
import os

from qgis.core import (
    Qgis, QgsMessageLog, QgsProject, QgsVectorFileWriter, QgsVectorLayer,
)
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout,
)

from ..baza_wrapper import Baza
from ..funkcje import rozbij_adres_gmina_obreb

_LOG = 'Las-R'

# nazwa warstwy zbiorczej (plik <nazwa>.shp w folderze nadrzednym) -> pola
# tworzace klucz dopasowania, w kolejnosci odpowiadajacej krotce z bazy
# (COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD, PARCEL_NR)
WARSTWY_PO_DZIALCE = {
    'DZKAT': ('COUNTY', 'DISTRICT', 'MUNICIP', 'COMMUNITY', 'PARCELNR'),
    'LS': ('COUNTY', 'DISTRICT', 'MUNICIP', 'COMMUNITY', 'PARCELNR'),
    'LZ_potencjalne': (
        'COUNTY', 'DISTRICT', 'MUNICIP', 'COMMUNITY', 'PARCELNR'),
}
WARSTWA_OBR = 'OBR'
WSZYSTKIE_WARSTWY = list(WARSTWY_PO_DZIALCE.keys()) + [WARSTWA_OBR]


def _opcje_zapisu():
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    return opcje


def znajdz_warstwe_zbiorcza(folder_nadrzedny, nazwa):
    """Zwraca sciezke do <nazwa>.shp w folder_nadrzedny (dopuszczajac inna
    wielkosc liter w nazwie pliku) albo None, jesli nie ma takiego pliku."""
    sciezka = os.path.join(folder_nadrzedny, nazwa + '.shp')
    if os.path.isfile(sciezka):
        return sciezka
    docelowa = (nazwa + '.shp').lower()
    for f in os.listdir(folder_nadrzedny):
        if f.lower() == docelowa:
            return os.path.join(folder_nadrzedny, f)
    return None


def znajdz_foldery_z_baza(folder_nadrzedny):
    """Zwraca liste (folder, [sciezki_mdb]) dla kazdego podfolderu w
    drzewie pod folder_nadrzedny (z wylaczeniem samego folder_nadrzedny),
    ktory bezposrednio zawiera >=1 plik .mdb."""
    wyniki = []
    korzen = os.path.normpath(folder_nadrzedny)
    for root, _dirs, files in os.walk(folder_nadrzedny):
        if os.path.normpath(root) == korzen:
            continue
        mdby = sorted(
            os.path.join(root, f) for f in files
            if f.lower().endswith('.mdb'))
        if mdby:
            wyniki.append((root, mdby))
    return wyniki


def pobierz_klucze(sciezki_mdb, log=print):
    """Laczy sie kolejno z kazda baza .mdb (tylko do odczytu) i zwraca
    zbior krotek (COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD,
    PARCEL_NR) z F_PARCEL, zsumowany ze wszystkich podanych baz."""
    klucze = set()
    for sc in sciezki_mdb:
        baza = Baza(sc)
        if not baza.polacz():
            log('  BLAD polaczenia z baza: %s' % sc)
            continue
        try:
            dz = baza.pobierz_klucze_dzialek()
        finally:
            baza.zamknij()
        if not dz:
            log('  Baza %s: brak dzialek (F_PARCEL puste?)' % sc)
            continue
        klucze.update(dz)
    return klucze


def _filtruj_po_dzialkach(sciezka_zbiorcza, pola, klucze, sciezka_wyjsciowa):
    """Zapisuje do sciezka_wyjsciowa obiekty ze sciezka_zbiorcza, ktorych
    krotka wartosci z `pola` (rzutowanych na string) jest w zbiorze
    `klucze`. Zwraca liczbe zapisanych obiektow albo None (brak
    dopasowan/blad)."""
    lyr = QgsVectorLayer(sciezka_zbiorcza, 'zbiorcza', 'ogr')
    if not lyr.isValid():
        QgsMessageLog.logMessage(
            'Nie udalo sie otworzyc %s' % sciezka_zbiorcza, _LOG,
            Qgis.Warning)
        return None

    idxy = [lyr.fields().indexFromName(p) for p in pola]
    if any(i < 0 for i in idxy):
        brakujace = [p for p, i in zip(pola, idxy) if i < 0]
        QgsMessageLog.logMessage(
            'Warstwa %s nie ma pol %s' % (sciezka_zbiorcza, brakujace),
            _LOG, Qgis.Warning)
        return None

    dopasowane = [
        f for f in lyr.getFeatures()
        if tuple(str(f.attributes()[i] or '') for i in idxy) in klucze]
    if not dopasowane:
        return None

    os.makedirs(os.path.dirname(sciezka_wyjsciowa), exist_ok=True)
    writer = QgsVectorFileWriter.create(
        sciezka_wyjsciowa, lyr.fields(), lyr.wkbType(), lyr.crs(),
        QgsProject.instance().transformContext(), _opcje_zapisu())
    for f in dopasowane:
        writer.addFeature(f)
    del writer
    return len(dopasowane)


def _filtruj_obr(sciezka_obr, community_pary, sciezka_wyjsciowa):
    """Zapisuje poligony OBR, ktorych (MUNICIP, COMMUNITY) wyciagniete z
    pola G5NRO (przez rozbij_adres_gmina_obreb) sa w community_pary -
    zbiorze krotek (MUNICIPALITY_CD, COMMUNITY_CD) z bazy."""
    lyr = QgsVectorLayer(sciezka_obr, 'obr', 'ogr')
    if not lyr.isValid():
        QgsMessageLog.logMessage(
            'Nie udalo sie otworzyc %s' % sciezka_obr, _LOG, Qgis.Warning)
        return None

    idx = lyr.fields().indexFromName('G5NRO')
    if idx < 0:
        QgsMessageLog.logMessage(
            'OBR (%s) nie ma pola G5NRO' % sciezka_obr, _LOG, Qgis.Warning)
        return None

    dopasowane = []
    for f in lyr.getFeatures():
        wynik = rozbij_adres_gmina_obreb(str(f.attributes()[idx] or ''))
        if wynik is None:
            continue
        gmina, obreb, _span = wynik
        if (gmina.replace('_', ''), obreb) in community_pary:
            dopasowane.append(f)
    if not dopasowane:
        return None

    os.makedirs(os.path.dirname(sciezka_wyjsciowa), exist_ok=True)
    writer = QgsVectorFileWriter.create(
        sciezka_wyjsciowa, lyr.fields(), lyr.wkbType(), lyr.crs(),
        QgsProject.instance().transformContext(), _opcje_zapisu())
    for f in dopasowane:
        writer.addFeature(f)
    del writer
    return len(dopasowane)


def przetworz_folder(folder, sciezki_mdb, warstwy_zbiorcze, log=print):
    """Rozdziela wszystkie znalezione warstwy_zbiorcze (dict {nazwa:
    sciezka_shp}) do <folder>/SHP/ wg dzialek z baz w sciezki_mdb. Zwraca
    dict {nazwa: sciezka_wynikowa} warstw faktycznie zapisanych."""
    klucze = pobierz_klucze(sciezki_mdb, log=log)
    if not klucze:
        log('  Brak kluczy dzialek z baz - pomijam folder')
        return {}

    zapisane = {}
    kat_wyj = os.path.join(folder, 'SHP')
    for nazwa, pola in WARSTWY_PO_DZIALCE.items():
        if nazwa not in warstwy_zbiorcze:
            continue
        sciezka_wyj = os.path.join(kat_wyj, nazwa + '.shp')
        liczba = _filtruj_po_dzialkach(
            warstwy_zbiorcze[nazwa], pola, klucze, sciezka_wyj)
        if liczba is None:
            log('  [%s] brak dopasowan - pominieto' % nazwa)
            continue
        log('  [%s] %d obiektow -> %s' % (nazwa, liczba, sciezka_wyj))
        zapisane[nazwa] = sciezka_wyj

    if WARSTWA_OBR in warstwy_zbiorcze:
        community_pary = {(k[2], k[3]) for k in klucze}
        sciezka_wyj = os.path.join(kat_wyj, WARSTWA_OBR + '.shp')
        liczba = _filtruj_obr(
            warstwy_zbiorcze[WARSTWA_OBR], community_pary, sciezka_wyj)
        if liczba is None:
            log('  [OBR] brak dopasowan - pominieto')
        else:
            log('  [OBR] %d obiektow -> %s' % (liczba, sciezka_wyj))
            zapisane[WARSTWA_OBR] = sciezka_wyj

    return zapisane


class RozdzielWgBaz(QDialog):
    def __init__(self, iface=None, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle('Rozdziel warstwy wg baz')

        glowny = QVBoxLayout(self)

        wiersz = QHBoxLayout()
        self.pole_folder = QLineEdit()
        przycisk = QPushButton('Przegladaj...')
        przycisk.clicked.connect(self._wybierz_folder)
        wiersz.addWidget(QLabel(
            'Folder nadrzędny (zbiorcze SHP + podfoldery z bazami):'))
        wiersz.addWidget(self.pole_folder)
        wiersz.addWidget(przycisk)
        glowny.addLayout(wiersz)

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

        self.resize(600, 180)

    def _wybierz_folder(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wybierz folder nadrzędny')
        if sc:
            self.pole_folder.setText(sc)

    def _log(self, tekst):
        QgsMessageLog.logMessage(tekst, _LOG, Qgis.Info)
        self.etykieta_status.setText(tekst)
        QApplication.processEvents()

    def _uruchom_klik(self):
        folder = self.pole_folder.text()
        if not os.path.isdir(folder):
            QMessageBox.critical(
                self, 'Błąd', 'Wskaż poprawny folder nadrzędny.')
            return

        warstwy_zbiorcze = {}
        for nazwa in WSZYSTKIE_WARSTWY:
            sc = znajdz_warstwe_zbiorcza(folder, nazwa)
            if sc:
                warstwy_zbiorcze[nazwa] = sc
        if not warstwy_zbiorcze:
            QMessageBox.warning(
                self, 'Brak warstw',
                'Nie znaleziono żadnej ze zbiorczych warstw '
                '(DZKAT/LS/LZ_potencjalne/OBR) w tym folderze.')
            return

        foldery = znajdz_foldery_z_baza(folder)
        if not foldery:
            QMessageBox.warning(
                self, 'Brak baz',
                'Nie znaleziono żadnego pliku .mdb w podfolderach.')
            return

        try:
            for i, (podfolder, mdby) in enumerate(foldery):
                self._log('Folder %d/%d: %s (%d baz(y))' % (
                    i + 1, len(foldery), podfolder, len(mdby)))
                przetworz_folder(
                    podfolder, mdby, warstwy_zbiorcze, log=self._log)
        except Exception as e:
            QgsMessageLog.logMessage(
                'Błąd rozdzielania wg baz: %s' % e, _LOG, Qgis.Critical)
            QMessageBox.critical(
                self, 'Błąd', 'Przerwano błędem:\n%s' % e)
            return

        QMessageBox.information(
            self, 'Gotowe', 'Przetworzono %d folder(ów).' % len(foldery))


def uruchom(iface=None):
    dlg = RozdzielWgBaz(iface)
    dlg.exec_()
