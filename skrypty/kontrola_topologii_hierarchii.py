# -*- coding: utf-8 -*-
"""Kontrola topologii hierarchii warstw (dzew-uzyt-wydz-oddz) - wylacznie
do odczytu, zadna geometria nie jest modyfikowana ani nadpisywana. Sluzy do
powtorzenia kontroli po recznej lub automatycznej poprawie topologii przez
'Napraw topologie hierarchii warstw'.

Sprawdzane sa:
- bledy wewnatrz kazdej warstwy z osobna (styki, wasy, nakladanie, luki -
  logika SprawdzTopo z sprawdzenia_topo.py),
- pokrycie dziecko-w-rodzicu miedzy kolejnymi warstwami hierarchii (uzyt w
  dzew, wydz w uzyt, oddz w wydz - logika kontrola_miedzywarstwowa z
  napraw_topologie_hierarchii.py).

Wyniki eksportowane sa jako pliki shp do wskazanego folderu wyjsciowego
(nigdy jako warstwy tylko-w-pamieci) z kolumna NR_BLEDU (kolejne liczby
naturalne od 1), co ulatwia przegladanie blad-po-bledzie (np. "Zoom to
next feature" w tabeli atrybutow QGIS).
"""
import os
from qgis.core import (
    QgsVectorLayer, QgsGeometry, QgsPointXY, QgsFeature, QgsField,
    QgsVectorFileWriter, QgsCoordinateReferenceSystem, QgsProject, Qgis,
)
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import (
    QDialog, QFileDialog, QMessageBox, QFormLayout, QHBoxLayout,
    QVBoxLayout, QLineEdit, QPushButton, QLabel, QDialogButtonBox,
)

from .sprawdzenia_topo import SprawdzTopo
from .napraw_topologie_hierarchii import kontrola_miedzywarstwowa, NAZWY_WARSTW

CRS = QgsCoordinateReferenceSystem('EPSG:2180')

# Kontrola wewnatrz pojedynczej warstwy nie ma tolerowac zadnego "szumu
# biznesowego" - warstwa sama w sobie ma byc idealna. Ten prog sluzy
# WYLACZNIE do odfiltrowania prawdziwego szumu numerycznego buforowania
# GEOS (rzedu pojedynczych cm2), NIE jest tozsamy z prog_pow_szum uzywanym
# w kontroli pokrycia miedzywarstwowego (tam akceptowalna jest realna,
# wieksza tolerancja rzedu m2 - patrz rozmowa o roznicy miedzy "szum
# naprawy" a "szum kontroli").
PROG_SZUM_WEWNETRZNY = 0.0001  # m2 (1 cm2)

# To samo dotyczy kontroli pokrycia dziecko-w-rodzicu - zero tolerancji
# biznesowej, tylko techniczny szum numeryczny roznicy geometrii (GEOS
# potrafi zostawic mikroskopijne artefakty przy difference() nawet na
# idealnie zgodnych granicach).
PROG_SZUM_POKRYCIA_POW = 0.0001  # m2 (1 cm2)
PROG_SZUM_POKRYCIA_SZER = 0.001  # m (1 mm)


def _opcje_zapisu():
    opcje = QgsVectorFileWriter.SaveVectorOptions()
    opcje.driverName = 'ESRI Shapefile'
    opcje.fileEncoding = 'UTF-8'
    return opcje


def _zapisz_pkt(bledy, sciezka):
    """bledy - lista [x, y, typ]. Zwraca True jesli plik zostal zapisany."""
    if not bledy:
        return False
    lyr = QgsVectorLayer('Point?crs=epsg:2180', 'tmp', 'memory')
    dp = lyr.dataProvider()
    lyr.startEditing()
    dp.addAttributes([
        QgsField('NR_BLEDU', QVariant.Int),
        QgsField('TYP', QVariant.String, len=35),
        QgsField('X', QVariant.Double, 'double', 10, 4),
        QgsField('Y', QVariant.Double, 'double', 10, 4),
    ])
    lyr.updateFields()
    feats = []
    for i, it in enumerate(bledy, start=1):
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(it[0], it[1])))
        f.setFields(lyr.fields())
        f['NR_BLEDU'] = i
        f['TYP'] = it[2]
        f['X'] = it[0]
        f['Y'] = it[1]
        feats.append(f)
    dp.addFeatures(feats)
    lyr.commitChanges()

    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    QgsVectorFileWriter.writeAsVectorFormatV3(
        lyr, sciezka, QgsProject.instance().transformContext(), _opcje_zapisu())
    return True


def _zapisz_poly(geoms_z_typem, sciezka):
    """geoms_z_typem - lista (QgsGeometry, etykieta_typu)."""
    if not geoms_z_typem:
        return False
    lyr = QgsVectorLayer('MultiPolygon?crs=epsg:2180', 'tmp', 'memory')
    dp = lyr.dataProvider()
    lyr.startEditing()
    dp.addAttributes([
        QgsField('NR_BLEDU', QVariant.Int),
        QgsField('TYP', QVariant.String, len=35),
        QgsField('POW_M2', QVariant.Double, 'double', 12, 2),
    ])
    lyr.updateFields()
    feats = []
    for i, (geom, typ) in enumerate(geoms_z_typem, start=1):
        f = QgsFeature()
        f.setGeometry(geom)
        f.setFields(lyr.fields())
        f['NR_BLEDU'] = i
        f['TYP'] = typ
        f['POW_M2'] = round(geom.area(), 2)
        feats.append(f)
    dp.addFeatures(feats)
    lyr.commitChanges()

    os.makedirs(os.path.dirname(sciezka), exist_ok=True)
    QgsVectorFileWriter.writeAsVectorFormatV3(
        lyr, sciezka, QgsProject.instance().transformContext(), _opcje_zapisu())
    return True


class KontrolaHierarchii:
    def __init__(self, iface=None):
        self.iface = iface
        self.raport = []

    def _log(self, tekst):
        self.raport.append(tekst)
        print(tekst)

    def _dodaj_do_toc(self, sciezka, nazwa):
        if self.iface is not None:
            QgsProject.instance().addMapLayer(
                QgsVectorLayer(sciezka, nazwa, 'ogr'))

    def _kontrola_wewnetrzna(self, sciezka, nazwa, folder_wyjsciowy,
                             prog_koincydencji, prog_szer):
        lyr = QgsVectorLayer(sciezka, nazwa, 'ogr')
        if not lyr.isValid():
            self._log('BŁĄD: nie można wczytać ' + sciezka)
            return

        b = SprawdzTopo(None, lyr=lyr)
        b.pobierz_feat()
        b.spr_wstepne(prog_koincydencji=prog_koincydencji)
        b.spr_styki()
        b.spr_wasy(prog_szer=prog_szer)
        b.spr_luki(prog_szer=prog_szer, prog_pow_szum=PROG_SZUM_WEWNETRZNY)
        b.spr_nakladanie()

        self._log('%s: kontrola wewnętrzna - %d błędów punktowych, '
                  '%d błędów powierzchniowych, %d obiektów bez geometrii '
                  '(pominiętych w kontroli)' %
                  (nazwa, len(b.bl_pkt), len(b.bl_poly),
                   len(b.bl_brak_geom)))

        sc_pkt = os.path.join(folder_wyjsciowy, nazwa + '_BLEDY_PKT.shp')
        if _zapisz_pkt(list(b.bl_pkt.values()), sc_pkt):
            self._dodaj_do_toc(sc_pkt, nazwa + '_BLEDY_PKT')

        sc_poly = os.path.join(folder_wyjsciowy, nazwa + '_BLEDY_POLY.shp')
        if _zapisz_poly(b.bl_poly, sc_poly):
            self._dodaj_do_toc(sc_poly, nazwa + '_BLEDY_POLY')

        if b.bl_brak_geom:
            sc_txt = os.path.join(folder_wyjsciowy,
                                  nazwa + '_BRAK_GEOMETRII.txt')
            os.makedirs(folder_wyjsciowy, exist_ok=True)
            with open(sc_txt, 'w', encoding='utf-8') as fp:
                fp.write('ID obiektów w %s bez geometrii (pominiętych w '
                        'kontroli, nie da się ich pokazać na mapie):\n' %
                        nazwa)
                for fid in b.bl_brak_geom:
                    fp.write(str(fid) + '\n')

    def _kontrola_pokrycia(self, rodzic_path, dziecko_path, rodzic_nazwa,
                           dziecko_nazwa, folder_wyjsciowy):
        rodzic = QgsVectorLayer(rodzic_path, 'rodzic', 'ogr')
        dziecko = QgsVectorLayer(dziecko_path, 'dziecko', 'ogr')
        if not rodzic.isValid() or not dziecko.isValid():
            self._log('BŁĄD: nie można wczytać warstw do kontroli pokrycia '
                      '%s w %s' % (dziecko_nazwa, rodzic_nazwa))
            return

        wynik = kontrola_miedzywarstwowa(rodzic, dziecko,
                                         PROG_SZUM_POKRYCIA_POW,
                                         PROG_SZUM_POKRYCIA_SZER)
        geoms_z_typem = []
        for etyk, dane in wynik.items():
            for g in dane['do_weryfikacji']:
                geoms_z_typem.append((g, etyk))

        n_szum = (len(wynik['luki']['szum']) +
                 len(wynik['nadmiar']['szum']))
        self._log('%s w %s: kontrola pokrycia - %d niezgodności do '
                  'weryfikacji, %d uznanych za szum' %
                  (dziecko_nazwa, rodzic_nazwa, len(geoms_z_typem), n_szum))

        sc = os.path.join(
            folder_wyjsciowy,
            '%s_W_%s_NIEZGODNOSC.shp' % (dziecko_nazwa, rodzic_nazwa))
        if _zapisz_poly(geoms_z_typem, sc):
            self._dodaj_do_toc(sc, os.path.basename(sc)[:-4])

    def uruchom(self, sciezki, folder_wyjsciowy, prog_koincydencji=0.02,
               prog_szer=0.15):
        """sciezki - slownik {'a_dzew_pol': sciezka_shp, 'a_uzyt_pol': ...,
        'a_wydz_pol': ..., 'a_oddz_pol': ...}. Zero tolerancji biznesowej -
        prog_koincydencji/prog_szer steruja tylko czuloscia/zdolnoscia
        wykrywania, nie tym co zostanie ukryte jako "akceptowalne"."""
        os.makedirs(folder_wyjsciowy, exist_ok=True)

        for nazwa in NAZWY_WARSTW:
            self._kontrola_wewnetrzna(
                sciezki[nazwa], nazwa, folder_wyjsciowy,
                prog_koincydencji, prog_szer)

        for rodzic_nazwa, dziecko_nazwa in zip(NAZWY_WARSTW[:-1],
                                               NAZWY_WARSTW[1:]):
            self._kontrola_pokrycia(
                sciezki[rodzic_nazwa], sciezki[dziecko_nazwa],
                rodzic_nazwa, dziecko_nazwa, folder_wyjsciowy)

        self._log('=== Kontrola topologii hierarchii zakończona ===')
        if self.iface is not None:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'OK', 'Kontrola topologii hierarchii zakończona - zobacz '
                'raport w logu i warstwy w folderze wyjściowym.',
                Qgis.Success, 0)
        return True


class PobierzDaneKontroli(QDialog):
    """Dialog do wskazania 4 plikow shp warstw hierarchii (dowolne nazwy -
    np. z folderu wyjsciowego naprawy, z przyrostkiem '_d'), folderu
    wyjsciowego na warstwy z bledami oraz progow tolerancji."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Kontrola topologii hierarchii warstw')
        self.porzucone = True

        self.le_dzew = QLineEdit()
        self.le_uzyt = QLineEdit()
        self.le_wydz = QLineEdit()
        self.le_oddz = QLineEdit()
        self.le_wyjscie = QLineEdit()
        self.le_prog_koinc = QLineEdit('2')
        self.le_prog_szer = QLineEdit('15')

        form = QFormLayout()
        pola = [
            ('a_dzew_pol (najważniejsza):', self.le_dzew),
            ('a_uzyt_pol:', self.le_uzyt),
            ('a_wydz_pol:', self.le_wydz),
            ('a_oddz_pol:', self.le_oddz),
        ]
        for etykieta, le in pola:
            wiersz = QHBoxLayout()
            wiersz.addWidget(le)
            btn = QPushButton('...')
            btn.clicked.connect(lambda _, le=le: self._wybierz_plik(le))
            wiersz.addWidget(btn)
            form.addRow(etykieta, wiersz)

        wiersz_wyj = QHBoxLayout()
        wiersz_wyj.addWidget(self.le_wyjscie)
        btn_wyj = QPushButton('...')
        btn_wyj.clicked.connect(self._wybierz_wyjscie)
        wiersz_wyj.addWidget(btn_wyj)
        form.addRow('Folder wyjściowy na warstwy z błędami:', wiersz_wyj)

        form.addRow('Próg koincydencji wierzchołków [cm]:',
                    self.le_prog_koinc)
        form.addRow('Maks. szerokość wykrywanych wąsów/luk\n'
                    '(czułość wykrywania, nie tolerancja) [cm]:',
                    self.le_prog_szer)

        info = QLabel(
            'Kontrola wyłącznie do odczytu - żadna geometria nie jest '
            'zmieniana ani nadpisywana. Zero tolerancji biznesowej: '
            'warstwy mają być idealne, jedyne co jest pomijane to '
            'techniczny szum numeryczny GEOS rzędu pojedynczych cm² '
            '(nie podlega konfiguracji). Sprawdzane są błędy wewnątrz '
            'każdej warstwy (styki, wąsy, nakładanie, luki) oraz pokrycie '
            'dziecko-w-rodzicu (uzyt w dzew, wydz w uzyt, oddz w wydz). '
            'Wyniki trafiają do folderu wyjściowego jako pliki shp z '
            'kolumną NR_BLEDU.')
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
        self.resize(520, 380)

    def _wybierz_plik(self, le):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż plik shp', '', 'ESRI Shapefile (*.shp)')[0]
        if sc:
            le.setText(sc)

    def _wybierz_wyjscie(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder wyjściowy')
        if sc:
            self.le_wyjscie.setText(sc)

    def _zatwierdz(self):
        pola = [
            (self.le_dzew, 'a_dzew_pol'), (self.le_uzyt, 'a_uzyt_pol'),
            (self.le_wydz, 'a_wydz_pol'), (self.le_oddz, 'a_oddz_pol'),
        ]
        for le, etykieta in pola:
            if not os.path.isfile(le.text()):
                QMessageBox.warning(self, 'Błąd',
                                    'Wskaż poprawny plik: ' + etykieta)
                return
        if not self.le_wyjscie.text():
            QMessageBox.warning(self, 'Błąd', 'Wskaż folder wyjściowy.')
            return
        for le, etykieta in [
            (self.le_prog_koinc, 'próg koincydencji'),
            (self.le_prog_szer, 'próg szerokości'),
        ]:
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
            'sciezki': {
                'a_dzew_pol': self.le_dzew.text(),
                'a_uzyt_pol': self.le_uzyt.text(),
                'a_wydz_pol': self.le_wydz.text(),
                'a_oddz_pol': self.le_oddz.text(),
            },
            'folder_wyjsciowy': self.le_wyjscie.text(),
            'prog_koincydencji':
                float(self.le_prog_koinc.text().replace(',', '.')) / 100,
            'prog_szer':
                float(self.le_prog_szer.text().replace(',', '.')) / 100,
        }
