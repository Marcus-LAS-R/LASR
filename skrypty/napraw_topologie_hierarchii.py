# -*- coding: utf-8 -*-
"""Automatyczna naprawa i kontrola topologii hierarchii warstw:
a_dzew_pol (dzialki, najwazniejsza) > a_uzyt_pol > a_wydz_pol > a_oddz_pol
(oddzialy, dociagane jako ostatnie).

Kazda warstwa podrzedna jest dociagana do juz poprawionej warstwy nadrzednej
(nigdy odwrotnie), a nastepnie sprawdzana wewnetrznie i wzgledem rodzica.
Nic nie jest tracone po cichu: niepewne dopasowania i niezgodnosci powyzej
progu trafiaja do warstw '..._BLEDY_*' / '..._DO_WERYFIKACJI' do recznej
oceny.
"""
import os
from qgis.core import (
    QgsVectorLayer, QgsGeometry, QgsFeature, QgsField, Qgis,
    QgsVectorFileWriter, QgsCoordinateReferenceSystem, QgsProject,
)
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QFormLayout, QHBoxLayout,
    QVBoxLayout, QLineEdit, QPushButton, QLabel, QDialogButtonBox,
)

from .shp_dociagnij_poly import Przyciagnij
from .sprawdzenia_topo import SprawdzTopo
from .pw import PasekPostepu

NAZWY_WARSTW = ['a_dzew_pol', 'a_uzyt_pol', 'a_wydz_pol', 'a_oddz_pol']
CRS = QgsCoordinateReferenceSystem('EPSG:2180')


def _opcje_zapisu():
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    return opcje


def _unia(lyr):
    geoms = [f.geometry() for f in lyr.getFeatures()
             if f.geometry() and not f.geometry().isEmpty()]
    if not geoms:
        return QgsGeometry()
    return QgsGeometry.unaryUnion(geoms)


def _rozbij(geom):
    if geom is None or geom.isEmpty():
        return []
    try:
        czesci = geom.asGeometryCollection()
    except Exception:
        czesci = [geom]
    return [c for c in czesci if not c.isEmpty()]


def kontrola_miedzywarstwowa(parent_lyr, child_lyr, prog_pow=20.0,
                             prog_szer=0.15):
    """Klasyfikuje niezgodnosci miedzy warstwa nadrzedna a podrzedna:
    luki (obszar rodzica niepokryty przez dziecko) i nadmiar (dziecko
    wystaje poza rodzica), kazde podzielone na 'szum' (ponizej progu,
    pomijane) i 'do_weryfikacji' (powyzej progu, wymaga recznej oceny).

    prog_pow [m2], prog_szer [m] - fragment jest szumem tylko jesli jest
    ponizej OBU progow jednoczesnie.
    """
    pu = _unia(parent_lyr)
    cu = _unia(child_lyr)

    def klasyfikuj(geom):
        wynik = {'szum': [], 'do_weryfikacji': []}
        for czesc in _rozbij(geom):
            a = czesc.area()
            peri = czesc.length()
            szer = 2 * a / peri if peri > 0 else 0
            if a < prog_pow and szer < prog_szer:
                wynik['szum'].append(czesc)
            else:
                wynik['do_weryfikacji'].append(czesc)
        return wynik

    return {
        'luki': klasyfikuj(pu.difference(cu)),
        'nadmiar': klasyfikuj(cu.difference(pu)),
    }


def _zapisz_poligony(geoms_z_typem, sciezka):
    """geoms_z_typem - lista (QgsGeometry, etykieta_typu)"""
    if not geoms_z_typem:
        return None
    lyr = QgsVectorLayer('MultiPolygon?crs=epsg:2180', 'tmp', 'memory')
    dp = lyr.dataProvider()
    lyr.startEditing()
    dp.addAttributes([
        QgsField('ID', QVariant.Int),
        QgsField('TYP', QVariant.String, len=35),
        QgsField('POW_M2', QVariant.Double, 'double', 12, 2),
    ])
    lyr.updateFields()
    feats = []
    for i, (geom, typ) in enumerate(geoms_z_typem):
        f = QgsFeature()
        f.setGeometry(geom)
        f.setFields(lyr.fields())
        f['ID'] = i
        f['TYP'] = typ
        f['POW_M2'] = round(geom.area(), 2)
        feats.append(f)
    dp.addFeatures(feats)
    lyr.commitChanges()

    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    QgsVectorFileWriter.writeAsVectorFormatV3(
        lyr, sciezka, QgsProject.instance().transformContext(),
        _opcje_zapisu())
    return QgsVectorLayer(sciezka, os.path.basename(sciezka)[:-4], 'ogr')


class NaprawaHierarchii:
    def __init__(self, iface=None):
        self.iface = iface
        self.postep = None
        self.raport = []  # lista linii tekstowych z podsumowaniem przebiegu

    def _log(self, tekst):
        self.raport.append(tekst)
        print(tekst)

    def _self_check(self, sciezka, nazwa, folder_wyjsciowy, prog_szer):
        lyr = QgsVectorLayer(sciezka, nazwa, 'ogr')
        if not lyr.isValid():
            self._log('  BŁĄD: nie można wczytać ' + sciezka)
            return
        b = SprawdzTopo(None, lyr=lyr)
        b.pobierz_feat()
        b.spr_wstepne()
        b.spr_styki()
        b.spr_wasy(prog_szer=prog_szer)
        b.spr_luki(prog_szer=prog_szer)
        b.spr_nakladanie()

        n_pkt = len(b.bl_pkt)
        n_poly = len(b.bl_poly)
        self._log('  kontrola wewnętrzna: %d błędów punktowych, '
                  '%d błędów powierzchniowych' % (n_pkt, n_poly))

        if n_pkt > 0:
            plyr = QgsVectorLayer('Point?crs=epsg:2180', 'tmp', 'memory')
            dp = plyr.dataProvider()
            plyr.startEditing()
            dp.addAttributes([QgsField('TYP', QVariant.String, len=35)])
            plyr.updateFields()
            from qgis.core import QgsPointXY
            feats = []
            for it in b.bl_pkt.values():
                f = QgsFeature()
                f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(it[0], it[1])))
                f.setFields(plyr.fields())
                f['TYP'] = it[2]
                feats.append(f)
            dp.addFeatures(feats)
            plyr.commitChanges()
            sciezka_out = os.path.join(folder_wyjsciowy,
                                       nazwa + '_BLEDY_pkt.shp')
            QgsVectorFileWriter.writeAsVectorFormatV3(
                plyr, sciezka_out, QgsProject.instance().transformContext(),
                _opcje_zapisu())
            if self.iface is not None:
                QgsProject.instance().addMapLayer(
                    QgsVectorLayer(sciezka_out, nazwa + '_BLEDY_pkt', 'ogr'))

        if n_poly > 0:
            _zapisz_poligony(
                [(g, t) for g, t in b.bl_poly],
                os.path.join(folder_wyjsciowy, nazwa + '_BLEDY_poly.shp'))
            if self.iface is not None:
                lyr2 = QgsVectorLayer(
                    os.path.join(folder_wyjsciowy, nazwa + '_BLEDY_poly.shp'),
                    nazwa + '_BLEDY_poly', 'ogr')
                QgsProject.instance().addMapLayer(lyr2)

    def _cross_check(self, rodzic_path, dziecko_path, nazwa,
                     folder_wyjsciowy, prog_pow, prog_szer):
        rodzic = QgsVectorLayer(rodzic_path, 'rodzic', 'ogr')
        dziecko = QgsVectorLayer(dziecko_path, 'dziecko', 'ogr')
        wynik = kontrola_miedzywarstwowa(rodzic, dziecko, prog_pow, prog_szer)

        geoms_z_typem = []
        for etyk, dane in wynik.items():
            for g in dane['do_weryfikacji']:
                geoms_z_typem.append((g, etyk))

        n_szum = (len(wynik['luki']['szum']) +
                  len(wynik['nadmiar']['szum']))
        n_wer = len(geoms_z_typem)
        self._log('  kontrola międzywarstwowa: %d drobnych niezgodności '
                  '(uznane za szum, bez akcji), %d do weryfikacji' %
                  (n_szum, n_wer))

        if geoms_z_typem:
            lyr = _zapisz_poligony(
                geoms_z_typem,
                os.path.join(folder_wyjsciowy,
                             nazwa + '_DO_WERYFIKACJI.shp'))
            if self.iface is not None and lyr is not None:
                QgsProject.instance().addMapLayer(lyr)

    def _kopiuj(self, sciezka, folder_wyjsciowy, nazwa_pliku):
        lyr = QgsVectorLayer(sciezka, 'src', 'ogr')
        wyjscie = os.path.join(folder_wyjsciowy, nazwa_pliku)
        os.makedirs(folder_wyjsciowy, exist_ok=True)
        QgsVectorFileWriter.writeAsVectorFormatV3(
            lyr, wyjscie, QgsProject.instance().transformContext(),
            _opcje_zapisu())
        return wyjscie

    def uruchom(self, folder_wejsciowy, folder_wyjsciowy, snap_dist=0.15,
               prog_pow=20.0, prog_szer=0.15):
        """Uruchamia caly lancuch: kontrola dzew (bez zmian) -> dociagniecie
        i kontrola uzyt -> dociagniecie i kontrola wydz -> dociagniecie
        i kontrola oddz. Zwraca True/False.
        """
        os.makedirs(folder_wyjsciowy, exist_ok=True)
        if self.iface is not None:
            self.postep = PasekPostepu(self.iface).stworz_pasek(
                'Naprawa topologii hierarchii...')

        sciezki = {n: os.path.join(folder_wejsciowy, n + '.shp')
                  for n in NAZWY_WARSTW}
        for n, s in sciezki.items():
            if not os.path.isfile(s):
                self._log('BŁĄD: brak pliku ' + s)
                return False

        etapy = len(NAZWY_WARSTW)
        krok = 0

        self._log('=== a_dzew_pol: warstwa bazowa (bez zmian geometrii) ===')
        self._self_check(sciezki['a_dzew_pol'], 'a_dzew_pol',
                         folder_wyjsciowy, prog_szer)
        rodzic_path = self._kopiuj(sciezki['a_dzew_pol'], folder_wyjsciowy,
                                   'a_dzew_pol_d.shp')
        krok += 1
        if self.postep:
            self.postep.setValue(int(100 * krok / etapy))

        for nazwa in ['a_uzyt_pol', 'a_wydz_pol', 'a_oddz_pol']:
            dziecko_path = sciezki[nazwa]
            self._log('=== %s: dociąganie do %s ===' %
                      (nazwa, os.path.basename(rodzic_path)))

            wyjscie = os.path.join(folder_wyjsciowy, nazwa + '_d.shp')
            tempkat_pary = os.path.join(folder_wyjsciowy, 'temp_' + nazwa)
            p = Przyciagnij(self.iface)
            ok = p.ustaw_dane_bezposrednio(rodzic_path, dziecko_path,
                                           snap_dist, wyjscie, tempkat_pary)
            if not ok:
                self._log('  BŁĄD dociągania ' + nazwa)
                return False
            if not p._przetworz():
                self._log('  BŁĄD przetwarzania linii dla ' + nazwa)
                return False
            p.podociagaj()
            p.stworz_poligony()
            p.pokaz_warstwy()
            self._log('  do weryfikacji (niepewne dopasowanie): %d, '
                      'nakładania: %d' % (p.b_poly, p.b_inter))

            self._self_check(wyjscie, nazwa, folder_wyjsciowy, prog_szer)
            self._cross_check(rodzic_path, wyjscie, nazwa, folder_wyjsciowy,
                              prog_pow, prog_szer)

            rodzic_path = wyjscie
            krok += 1
            if self.postep:
                self.postep.setValue(int(100 * krok / etapy))

        self._log('=== Zakończono naprawę hierarchii warstw ===')

        if self.iface is not None:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'OK', 'Naprawa topologii hierarchii zakończona - '
                'zobacz raport w logu.', Qgis.Success, 0)

        return True


class PobierzDaneHierarchii(QDialog):
    """Prosty dialog do wskazania folderu z warstwami wejsciowymi (musza
    sie w nim znajdowac a_dzew_pol.shp, a_uzyt_pol.shp, a_wydz_pol.shp,
    a_oddz_pol.shp), folderu wyjsciowego oraz progow tolerancji."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Napraw topologię hierarchii warstw')
        self.porzucone = True

        self.le_wejscie = QLineEdit()
        self.le_wyjscie = QLineEdit()
        self.le_snap = QLineEdit('15')
        self.le_prog_pow = QLineEdit('20')
        self.le_prog_szer = QLineEdit('15')

        btn_wejscie = QPushButton('...')
        btn_wejscie.clicked.connect(self._wybierz_wejscie)
        btn_wyjscie = QPushButton('...')
        btn_wyjscie.clicked.connect(self._wybierz_wyjscie)

        wiersz_wejscie = QHBoxLayout()
        wiersz_wejscie.addWidget(self.le_wejscie)
        wiersz_wejscie.addWidget(btn_wejscie)
        wiersz_wyjscie = QHBoxLayout()
        wiersz_wyjscie.addWidget(self.le_wyjscie)
        wiersz_wyjscie.addWidget(btn_wyjscie)

        form = QFormLayout()
        form.addRow('Folder z warstwami wejściowymi\n'
                    '(a_dzew_pol, a_uzyt_pol, a_wydz_pol, a_oddz_pol):',
                    wiersz_wejscie)
        form.addRow('Folder wyjściowy (kopie _d, nigdy nie nadpisuje\n'
                    'oryginałów):', wiersz_wyjscie)
        form.addRow('Odległość dociągania granic [cm]:', self.le_snap)
        form.addRow('Próg powierzchni "szumu" [m²]\n'
                    '(poniżej = ciche zamknięcie, powyżej = do '
                    'weryfikacji):', self.le_prog_pow)
        form.addRow('Próg szerokości "szumu" [cm]:', self.le_prog_szer)

        info = QLabel(
            'Warstwy dociągane są w kolejności ważności: uzyt→dzew, '
            'wydz→uzyt, oddz→wydz. Warstwa nadrzędna nigdy nie jest '
            'modyfikowana. Wynik i wszystkie błędy/niezgodności trafiają '
            'do folderu wyjściowego jako osobne warstwy - nic nie jest '
            'tracone po cichu.')
        info.setWordWrap(True)

        przyciski = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        przyciski.accepted.connect(self._zatwierdz)
        przyciski.rejected.connect(self.reject)

        glowny = QVBoxLayout()
        glowny.addWidget(info)
        glowny.addLayout(form)
        glowny.addWidget(przyciski)
        self.setLayout(glowny)
        self.resize(480, 260)

    def _wybierz_wejscie(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder z warstwami wejściowymi')
        if sc:
            self.le_wejscie.setText(sc)
            if not self.le_wyjscie.text():
                self.le_wyjscie.setText(sc + '_d')

    def _wybierz_wyjscie(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder wyjściowy')
        if sc:
            self.le_wyjscie.setText(sc)

    def _zatwierdz(self):
        if not os.path.isdir(self.le_wejscie.text()):
            QMessageBox.warning(self, 'Błąd',
                                'Wskaż istniejący folder wejściowy.')
            return
        brakujace = [n for n in NAZWY_WARSTW
                    if not os.path.isfile(os.path.join(
                        self.le_wejscie.text(), n + '.shp'))]
        if brakujace:
            QMessageBox.warning(
                self, 'Błąd',
                'W folderze wejściowym brakuje warstw: ' +
                ', '.join(brakujace))
            return
        if not self.le_wyjscie.text():
            QMessageBox.warning(self, 'Błąd', 'Wskaż folder wyjściowy.')
            return
        for le, etykieta in [(self.le_snap, 'odległość dociągania'),
                             (self.le_prog_pow, 'próg powierzchni'),
                             (self.le_prog_szer, 'próg szerokości')]:
            try:
                float(le.text().replace(',', '.'))
            except ValueError:
                QMessageBox.warning(self, 'Błąd',
                                    'Niepoprawna wartość: ' + etykieta)
                return

        self.porzucone = False
        self.accept()

    def pobierz_parametry(self):
        return {
            'folder_wejsciowy': self.le_wejscie.text(),
            'folder_wyjsciowy': self.le_wyjscie.text(),
            'snap_dist': float(self.le_snap.text().replace(',', '.')) / 100,
            'prog_pow': float(self.le_prog_pow.text().replace(',', '.')),
            'prog_szer': float(self.le_prog_szer.text().replace(',', '.')) / 100,
        }

