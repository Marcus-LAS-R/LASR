# -*- coding: utf-8 -*-
"""Połącz warstwy SHP.

Ze wskazanego folderu nadrzędnego (np. z folderami gmin albo obrębów)
bierze wybrane foldery, w każdym podfolder z warstwami (domyślnie SHP)
i łączy warstwy o tej samej nazwie (bez względu na wielkość liter) w jedną
warstwę w folderze docelowym (domyślnie <folder nadrzędny>\\SHP_razem).

- wynik ma tylko oryginalne atrybuty (suma pól ze wszystkich źródeł), bez
  kolumn ze ścieżką/nazwą folderu źródłowego,
- wszystko przeliczane do EPSG:2180,
- ta sama geometria (topologicznie równa albo różniąca się najwyżej
  o TOLERANCJA_DUPLIKATU) trafia do wyniku tylko raz - zostaje pierwszy
  napotkany obiekt (kolejność folderów jak na liście),
- każde nakładanie (wnętrza obiektów mają część wspólną o wymiarze warstwy:
  powierzchnię dla poligonów, odcinek dla linii) - między folderami
  i wewnątrz jednej warstwy, bez progu - trafia do warstwy pamięci
  <NAZWA>_nakładanie z samą geometrią części wspólnej,
- istniejące pliki w folderze docelowym nie są nadpisywane bez zgody.
"""

import os
from datetime import datetime

from PyQt5.QtCore import Qt, QVariant
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFileDialog, QProgressDialog,
    QApplication, QCheckBox,
)
from .przyciski import QDialogButtonBox, QMessageBox
from qgis.core import (
    Qgis, QgsProject, QgsVectorLayer, QgsFeature, QgsField, QgsFields,
    QgsGeometry, QgsPointXY, QgsWkbTypes, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsSpatialIndex)

from . import funkcje

_TYTUL = 'Połącz warstwy SHP'

DOMYSLNE_WARSTWY = ('DZKAT', 'LS', 'EWID', 'WYDZ', 'WYDZ_POL', 'PNSW',
                    'LIN', 'OBR', 'ODDZ', 'WYDZ_DOPISANE')
DOMYSLNY_PODFOLDER = 'SHP'
FOLDER_WYNIKOWY = 'SHP_razem'
EPSG_DOCELOWY = 'EPSG:2180'
# [m] - geometrie różniące się najwyżej o tyle (odległość Hausdorffa) to
# "ta sama geometria" (np. ten sam obiekt zapisany w dwóch folderach,
# z różnicami zaokrągleń po przeliczeniu układu)
TOLERANCJA_DUPLIKATU = 0.01

# wnętrza mają część wspólną wymiaru warstwy (DE-9IM, macierz wnętrze/wnętrze)
_WZORZEC_NAKLADANIA = {
    QgsWkbTypes.PolygonGeometry: '2********',
    QgsWkbTypes.LineGeometry: '1********',
    QgsWkbTypes.PointGeometry: '0********',
}


# ---------------------------------------------------------------- szukanie

def foldery_z_podfolderem(folder_nadrzedny, podfolder):
    """[(nazwa folderu, czy ma podfolder)] - foldery z folderu nadrzędnego
    (bez folderu wynikowego), alfabetycznie."""
    wyn = []
    try:
        nazwy = sorted(os.listdir(folder_nadrzedny), key=str.lower)
    except OSError:
        return wyn
    for n in nazwy:
        sciezka = os.path.join(folder_nadrzedny, n)
        if not os.path.isdir(sciezka) or n.lower() == FOLDER_WYNIKOWY.lower():
            continue
        wyn.append((n, os.path.isdir(os.path.join(sciezka, podfolder))))
    return wyn


def warstwy_w_folderze(katalog):
    """{NAZWA (wielkie litery): ścieżka .shp} w katalogu (bez podfolderów)."""
    wyn = {}
    try:
        pliki = os.listdir(katalog)
    except OSError:
        return wyn
    for p in pliki:
        nazwa, rozsz = os.path.splitext(p)
        if rozsz.lower() == '.shp':
            wyn[nazwa.upper()] = os.path.join(katalog, p)
    return wyn


def zbierz_zrodla(folder_nadrzedny, foldery, podfolder):
    """{NAZWA: [(folder, ścieżka .shp)]} w kolejności folderów."""
    wyn = {}
    for f in foldery:
        kat = os.path.join(folder_nadrzedny, f, podfolder)
        for nazwa, sciezka in sorted(warstwy_w_folderze(kat).items()):
            wyn.setdefault(nazwa, []).append((f, sciezka))
    return wyn


# ----------------------------------------------------------------- łączenie

def _suma_pol(warstwy):
    """Suma pól wszystkich źródeł (po nazwie, bez wielkości liter).
    Różne typy tego samego pola: liczby -> Double, inaczej tekst."""
    pola = []      # [QgsField]
    indeks = {}    # NAZWA -> pozycja w pola
    for wl in warstwy:
        for pole in wl.fields():
            klucz = pole.name().upper()
            if klucz not in indeks:
                indeks[klucz] = len(pola)
                pola.append(QgsField(pole))
                continue
            istn = pola[indeks[klucz]]
            if istn.type() == pole.type():
                if pole.length() > istn.length():
                    istn.setLength(pole.length())
                if pole.precision() > istn.precision():
                    istn.setPrecision(pole.precision())
                continue
            liczbowe = (QVariant.Int, QVariant.LongLong, QVariant.Double)
            if istn.type() in liczbowe and pole.type() in liczbowe:
                nowe = QgsField(istn.name(), QVariant.Double, 'Real', 20, 6)
            else:
                nowe = QgsField(istn.name(), QVariant.String, 'String', 254)
            pola[indeks[klucz]] = nowe
    qf = QgsFields()
    for p in pola:
        qf.append(p)
    return qf, indeks


def _geometria_2d_multi(geom):
    g = QgsGeometry(geom)
    if g.isNull() or g.isEmpty():
        return g
    abstr = g.get()
    abstr.dropZValue()
    abstr.dropMValue()
    g.convertToMultiType()
    return g


def _ten_sam_uklad(crs, crs_docelowy, kontekst):
    """.prj w wersji ESRI (np. "ETRS89 / Poland CS92" bez kodu EPSG) to
    często ten sam układ - sprawdzane przeliczeniem punktów kontrolnych."""
    try:
        tr = QgsCoordinateTransform(crs, crs_docelowy, kontekst)
        for x, y in ((200000, 150000), (500000, 500000), (800000, 750000)):
            p = tr.transform(QgsPointXY(x, y))
            if abs(p.x() - x) > 0.001 or abs(p.y() - y) > 0.001:
                return False
        return True
    except Exception:
        return False


def _wczytaj(nazwa, zrodla, crs_docelowy, uwagi):
    """Wczytuje źródła jednej warstwy. Zwraca (typ geometrii, QgsFields,
    [(folder, fid, geometria, atrybuty)]) albo None, gdy nie ma czego
    łączyć."""
    warstwy = []
    typ = None
    for folder, sciezka in zrodla:
        wl = QgsVectorLayer(sciezka, nazwa, 'ogr')
        if not wl.isValid():
            uwagi.append(f'{nazwa}: {folder} - nie da się otworzyć warstwy, '
                         'pominięta')
            continue
        t = wl.geometryType()
        if typ is None:
            typ = t
        elif t != typ:
            uwagi.append(
                f'{nazwa}: {folder} - inny typ geometrii '
                f'({QgsWkbTypes.geometryDisplayString(t)} zamiast '
                f'{QgsWkbTypes.geometryDisplayString(typ)}), pominięta')
            continue
        warstwy.append((folder, wl))
    if not warstwy:
        return None

    pola, indeks = _suma_pol([wl for _, wl in warstwy])
    kontekst = QgsProject.instance().transformContext()
    obiekty = []
    for folder, wl in warstwy:
        crs = wl.crs()
        transf = None
        if not crs.isValid():
            uwagi.append(f'{nazwa}: {folder} - brak układu współrzędnych, '
                         'przyjęto EPSG:2180')
        elif crs != crs_docelowy and \
                not _ten_sam_uklad(crs, crs_docelowy, kontekst):
            transf = QgsCoordinateTransform(crs, crs_docelowy, kontekst)
            uwagi.append(f'{nazwa}: {folder} - przeliczono z '
                         f'{crs.authid() or crs.description()} do EPSG:2180')
        mapa = [indeks[p.name().upper()] for p in wl.fields()]
        typy = [pola[i].type() for i in mapa]
        for f in wl.getFeatures():
            atr = [None] * pola.count()
            for i, (cel, typ_celu) in enumerate(zip(mapa, typy)):
                v = f.attribute(i)
                if v is None or (isinstance(v, QVariant) and v.isNull()):
                    continue
                if typ_celu == QVariant.String and not isinstance(v, str):
                    v = str(v)
                atr[cel] = v
            g = QgsGeometry(f.geometry())
            if transf is not None and not g.isNull():
                try:
                    g.transform(transf)
                except Exception:
                    uwagi.append(f'{nazwa}: {folder} fid {f.id()} - błąd '
                                 'przeliczenia układu, obiekt pominięty')
                    continue
            obiekty.append((folder, f.id(), _geometria_2d_multi(g), atr))
    return typ, pola, obiekty


def _czesc_wspolna(g1, g2, typ):
    """Część wspólna tylko z częściami o wymiarze warstwy (bez styków)."""
    try:
        wsp = g1.intersection(g2)
        if wsp.isNull() or wsp.isEmpty():
            wsp = g1.makeValid().intersection(g2.makeValid())
    except Exception:
        return None
    if wsp.isNull() or wsp.isEmpty():
        return None
    czesci = [c for c in wsp.asGeometryCollection() if c.type() == typ]
    if not czesci:
        return None
    wyn = QgsGeometry.collectGeometry(czesci)
    return wyn if not wyn.isEmpty() else None


def _bbox_zgodny(a, b, tol):
    return (abs(a.xMinimum() - b.xMinimum()) <= tol and
            abs(a.yMinimum() - b.yMinimum()) <= tol and
            abs(a.xMaximum() - b.xMaximum()) <= tol and
            abs(a.yMaximum() - b.yMaximum()) <= tol)


def analizuj(obiekty, typ, szukaj_nakladan=True, postep=None):
    """Zwraca (zbiór indeksów duplikatów, [(i_zostaje, j_duplikat)],
    [(i, j, geometria części wspólnej)], liczba błędów geometrii).
    Duplikat (j) nie jest dalej porównywany - jego nakładania są te same
    co obiektu, który zostaje (i). Nakładania tylko przy szukaj_nakladan."""
    si = QgsSpatialIndex()
    bboxy = {}
    for i, (_, _, g, _) in enumerate(obiekty):
        if g.isNull() or g.isEmpty():
            continue
        f = QgsFeature(i)
        f.setGeometry(g)
        si.addFeature(f)
        bboxy[i] = g.boundingBox()

    wzorzec = _WZORZEC_NAKLADANIA.get(typ)
    duplikaty = set()
    pary_dup = []
    nakladania = []
    bledy = 0
    n = max(len(bboxy), 1)
    for k, i in enumerate(sorted(bboxy)):
        if postep is not None and k % 200 == 0:
            if not postep(k, n):
                return None
        if i in duplikaty:
            continue
        gi = obiekty[i][2]
        silnik = QgsGeometry.createGeometryEngine(gi.constGet())
        silnik.prepareGeometry()
        for j in sorted(si.intersects(bboxy[i])):
            if j <= i or j in duplikaty:
                continue
            gj = obiekty[j][2]
            if gi.isGeosEqual(gj) or (
                    _bbox_zgodny(bboxy[i], bboxy[j], TOLERANCJA_DUPLIKATU) and
                    gi.hausdorffDistance(gj) <= TOLERANCJA_DUPLIKATU):
                duplikaty.add(j)
                pary_dup.append((i, j))
                continue
            if wzorzec is None or not szukaj_nakladan:
                continue
            if not silnik.relatePattern(gj.constGet(), wzorzec):
                continue
            wsp = _czesc_wspolna(gi, gj, typ)
            if wsp is None:
                # nachodzą, ale GEOS nie policzył części wspólnej
                # (zwykle nieprawidłowa geometria) - tylko do raportu
                bledy += 1
                continue
            nakladania.append((i, j, wsp))
    return duplikaty, pary_dup, nakladania, bledy


def _warstwa_pamieci(typ_wkb, nazwa, pola=None):
    uri = f'{QgsWkbTypes.displayString(typ_wkb)}?crs={EPSG_DOCELOWY}'
    wl = QgsVectorLayer(uri, nazwa, 'memory')
    if pola is not None:
        wl.dataProvider().addAttributes(pola.toList())
        wl.updateFields()
    return wl


_TYP_MULTI = {
    QgsWkbTypes.PolygonGeometry: QgsWkbTypes.MultiPolygon,
    QgsWkbTypes.LineGeometry: QgsWkbTypes.MultiLineString,
    QgsWkbTypes.PointGeometry: QgsWkbTypes.MultiPoint,
}


def polacz_warstwe(nazwa, zrodla, folder_docelowy, usun_duplikaty=True,
                   szukaj_nakladan=False, postep=None):
    """Łączy jedną warstwę. Zwraca słownik z wynikiem (do raportu) albo
    None, gdy przerwano.
    usun_duplikaty=False: duplikaty zostają w wyniku, a przy
    szukaj_nakladan trafiają też do <NAZWA>_nakładanie (cała geometria).
    Oba wyłączone - samo łączenie, bez analizy geometrii."""
    crs = QgsCoordinateReferenceSystem(EPSG_DOCELOWY)
    uwagi = []
    wynik = {'nazwa': nazwa, 'uwagi': uwagi, 'zrodla': [], 'zapisano': 0,
             'duplikaty': 0, 'dup_rozne_atr': [], 'nakladania': 0,
             'bledy_geom': 0, 'blad_zapisu': '', 'warstwa_nakl': None,
             'usun_duplikaty': usun_duplikaty,
             'szukaj_nakladan': szukaj_nakladan, 'nakl_duplikaty': 0}
    wczytane = _wczytaj(nazwa, zrodla, crs, uwagi)
    if wczytane is None:
        uwagi.append(f'{nazwa}: brak warstw do połączenia')
        return wynik
    typ, pola, obiekty = wczytane
    licz = {}
    for folder, _, _, _ in obiekty:
        licz[folder] = licz.get(folder, 0) + 1
    wynik['zrodla'] = [(f, licz.get(f, 0)) for f, _ in zrodla]

    if not obiekty:
        uwagi.append(f'{nazwa}: brak obiektów w źródłach - zapisano pustą '
                     'warstwę')

    if usun_duplikaty or szukaj_nakladan:
        analiza = analizuj(obiekty, typ, szukaj_nakladan, postep)
        if analiza is None:
            return None
    else:
        analiza = (set(), [], [], 0)
    duplikaty, pary_dup, nakladania, bledy = analiza
    if not usun_duplikaty and szukaj_nakladan:
        nakladania = [(i, j, QgsGeometry(obiekty[j][2]))
                      for i, j in pary_dup] + nakladania
        wynik['nakl_duplikaty'] = len(pary_dup)
    wynik['duplikaty'] = len(duplikaty)
    wynik['nakladania'] = len(nakladania)
    wynik['bledy_geom'] = bledy
    for i, j in pary_dup:
        if obiekty[i][3] != obiekty[j][3]:
            wynik['dup_rozne_atr'].append(
                (obiekty[i][0], obiekty[i][1], obiekty[j][0], obiekty[j][1]))

    typ_wkb = _TYP_MULTI.get(typ, QgsWkbTypes.NoGeometry)
    wl = _warstwa_pamieci(typ_wkb, nazwa, pola)
    feats = []
    for i, (_, _, g, atr) in enumerate(obiekty):
        if usun_duplikaty and i in duplikaty:
            continue
        f = QgsFeature(pola)
        f.setGeometry(g)
        f.setAttributes(atr)
        feats.append(f)
    wl.dataProvider().addFeatures(feats)
    ok, kom = funkcje.zapisz_shp_utf8(
        wl, os.path.join(folder_docelowy, nazwa + '.shp'))
    if ok:
        wynik['zapisano'] = len(feats)
    else:
        wynik['blad_zapisu'] = kom

    if nakladania:
        pola_nakl = QgsFields()
        pola_nakl.append(QgsField('ID', QVariant.Int, 'Integer', 10))
        pola_nakl.append(QgsField('FOLDER_A', QVariant.String, 'String', 254))
        pola_nakl.append(QgsField('FOLDER_B', QVariant.String, 'String', 254))
        wn = _warstwa_pamieci(typ_wkb, f'{nazwa}_nakładanie', pola_nakl)
        nf = []
        for nr, (i, j, g) in enumerate(nakladania, 1):
            f = QgsFeature(pola_nakl)
            f.setGeometry(_geometria_2d_multi(g))
            f.setAttributes([nr, obiekty[i][0], obiekty[j][0]])
            nf.append(f)
        wn.dataProvider().addFeatures(nf)
        wn.updateExtents()
        wynik['warstwa_nakl'] = wn
    return wynik


# ------------------------------------------------------------------ raport

def zapisz_raport(folder_docelowy, wyniki):
    kat = os.path.join(folder_docelowy, 'Raporty')
    os.makedirs(kat, exist_ok=True)
    teraz = datetime.now()
    sciezka = os.path.join(
        kat, f'raport_polacz_warstwy_{teraz.strftime("%Y%m%dT%H%M%S")}.txt')
    w = [f'{_TYTUL} - {teraz.strftime("%Y-%m-%d %H:%M")}',
         f'Układ wynikowy: {EPSG_DOCELOWY}', '']
    for r in wyniki:
        w.append(f'=== {r["nazwa"]} ===')
        for f, n in r['zrodla']:
            w.append(f'  {f}: {n} obiektów')
        if r['blad_zapisu']:
            w.append(f'  BŁĄD ZAPISU: {r["blad_zapisu"]}')
        else:
            w.append(f'  zapisano: {r["zapisano"]} obiektów')
        if r['usun_duplikaty']:
            w.append(f'  usunięte duplikaty geometrii: {r["duplikaty"]}')
        elif r['szukaj_nakladan']:
            w.append(f'  duplikaty geometrii (zostawione w wyniku): '
                     f'{r["duplikaty"]}')
        else:
            w.append('  duplikaty geometrii: nie sprawdzano')
        if r['dup_rozne_atr']:
            w.append('  w tym z innymi atrybutami'
                     + (' (zostaje pierwszy):' if r['usun_duplikaty']
                        else ':'))
            for f1, id1, f2, id2 in r['dup_rozne_atr']:
                w.append(f'    {f2} fid {id2} = {f1} fid {id1}')
        if not r['szukaj_nakladan']:
            w.append('  nakładania: nie sprawdzano')
        else:
            w.append(f'  nakładania: {r["nakladania"]}'
                     + (f' (w tym duplikaty: {r["nakl_duplikaty"]})'
                        if r['nakl_duplikaty'] else '')
                     + (f' - warstwa {r["nazwa"]}_nakładanie'
                        if r['nakladania'] else ''))
        if r['bledy_geom']:
            w.append(f'  par nachodzących bez policzonej części wspólnej '
                     f'(błędna geometria): {r["bledy_geom"]}')
        for u in r['uwagi']:
            w.append(f'  uwaga: {u}')
        w.append('')
    with open(sciezka, 'w', encoding='utf-8') as f:
        f.write('\n'.join(w))
    return sciezka


# ------------------------------------------------------------------ dialog

class PolaczWarstwyDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(_TYTUL)
        self.resize(560, 640)
        self._docelowy_reczny = False

        uklad = QVBoxLayout(self)
        siatka = QGridLayout()
        siatka.addWidget(QLabel('Folder nadrzędny:'), 0, 0)
        self.le_nadrz = QLineEdit()
        siatka.addWidget(self.le_nadrz, 0, 1)
        b = QPushButton('...')
        b.clicked.connect(self._wybierz_nadrzedny)
        siatka.addWidget(b, 0, 2)

        siatka.addWidget(QLabel('Podfolder z warstwami:'), 1, 0)
        self.le_podf = QLineEdit(DOMYSLNY_PODFOLDER)
        siatka.addWidget(self.le_podf, 1, 1)
        b = QPushButton('...')
        b.clicked.connect(self._wybierz_podfolder)
        siatka.addWidget(b, 1, 2)

        siatka.setColumnStretch(1, 1)
        uklad.addLayout(siatka)

        uklad.addWidget(QLabel('Foldery do połączenia:'))
        self.lw_foldery = QListWidget()
        uklad.addWidget(self.lw_foldery, 1)
        uklad.addLayout(self._przyciski_zaznaczania(self.lw_foldery))

        uklad.addWidget(QLabel('Warstwy do połączenia:'))
        self.lw_warstwy = QListWidget()
        uklad.addWidget(self.lw_warstwy, 1)
        uklad.addLayout(self._przyciski_zaznaczania(self.lw_warstwy))

        self.cb_nakladania = QCheckBox('Wskaż błędy nakładania')
        self.cb_nakladania.setToolTip(
            'Części wspólne nachodzących obiektów na warstwach pamięci '
            '<NAZWA>_nakładanie (pola ID, FOLDER_A, FOLDER_B).')
        uklad.addWidget(self.cb_nakladania)
        self.cb_duplikaty = QCheckBox('Usuń duplikaty geometrii')
        self.cb_duplikaty.setChecked(True)
        self.cb_duplikaty.setToolTip(
            'Ta sama geometria trafia do wyniku raz. Wyłączone - duplikaty '
            'zostają, a przy wskazywaniu nakładań trafiają też do warstwy '
            '<NAZWA>_nakładanie.')
        uklad.addWidget(self.cb_duplikaty)

        docel = QHBoxLayout()
        docel.addWidget(QLabel('Folder docelowy:'))
        self.le_docel = QLineEdit()
        docel.addWidget(self.le_docel, 1)
        b = QPushButton('...')
        b.clicked.connect(self._wybierz_docelowy)
        docel.addWidget(b)
        uklad.addLayout(docel)

        self.bb = QDialogButtonBox(QDialogButtonBox.Ok |
                                   QDialogButtonBox.Cancel)
        self.bb.button(QDialogButtonBox.Ok).setText('Połącz')
        self.bb.accepted.connect(self._akceptuj)
        self.bb.rejected.connect(self.reject)
        uklad.addWidget(self.bb)

        self.le_nadrz.editingFinished.connect(self._odswiez_foldery)
        self.le_podf.editingFinished.connect(self._odswiez_foldery)
        self.le_docel.textEdited.connect(self._docelowy_edytowany)
        self.lw_foldery.itemChanged.connect(self._odswiez_warstwy)

    def _przyciski_zaznaczania(self, lista):
        h = QHBoxLayout()
        for tekst, stan in (('Zaznacz wszystkie', Qt.Checked),
                            ('Odznacz wszystkie', Qt.Unchecked)):
            b = QPushButton(tekst)
            b.clicked.connect(
                lambda _, l=lista, s=stan: self._zaznacz(l, s))
            h.addWidget(b)
        h.addStretch()
        return h

    def _zaznacz(self, lista, stan):
        lista.blockSignals(True)
        for i in range(lista.count()):
            it = lista.item(i)
            if it.flags() & Qt.ItemIsEnabled:
                it.setCheckState(stan)
        lista.blockSignals(False)
        if lista is self.lw_foldery:
            self._odswiez_warstwy()

    def _wybierz_nadrzedny(self):
        kat = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder nadrzędny', self.le_nadrz.text())
        if kat:
            self.le_nadrz.setText(os.path.normpath(kat))
            self._odswiez_foldery()

    def _wybierz_podfolder(self):
        # start w pierwszym folderze z listy - wskazuje się jego podfolder,
        # a do pola trafia sama nazwa (ta sama we wszystkich folderach)
        start = self.le_nadrz.text().strip()
        if self.lw_foldery.count():
            start = os.path.join(
                start, self.lw_foldery.item(0).data(Qt.UserRole))
        kat = QFileDialog.getExistingDirectory(
            self, 'Wskaż podfolder z warstwami', start)
        if kat:
            self.le_podf.setText(os.path.basename(os.path.normpath(kat)))
            self._odswiez_foldery()

    def _wybierz_docelowy(self):
        kat = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder docelowy',
            self.le_docel.text() or self.le_nadrz.text())
        if kat:
            self.le_docel.setText(os.path.normpath(kat))
            self._docelowy_reczny = True

    def _docelowy_edytowany(self, _):
        self._docelowy_reczny = True

    def _odswiez_foldery(self):
        nadrz = self.le_nadrz.text().strip()
        if not self._docelowy_reczny and nadrz:
            self.le_docel.setText(os.path.join(nadrz, FOLDER_WYNIKOWY))
        podf = self.le_podf.text().strip() or DOMYSLNY_PODFOLDER
        self.lw_foldery.blockSignals(True)
        self.lw_foldery.clear()
        for nazwa, ma_podf in foldery_z_podfolderem(nadrz, podf):
            it = QListWidgetItem(nazwa if ma_podf
                                 else f'{nazwa}  (brak podfolderu {podf})')
            it.setData(Qt.UserRole, nazwa)
            if ma_podf:
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked)
            else:
                it.setFlags(Qt.NoItemFlags)
            self.lw_foldery.addItem(it)
        self.lw_foldery.blockSignals(False)
        self._odswiez_warstwy()

    def wybrane(self, lista):
        return [lista.item(i).data(Qt.UserRole) for i in range(lista.count())
                if lista.item(i).checkState() == Qt.Checked]

    def _odswiez_warstwy(self, *_):
        poprzednie = {self.lw_warstwy.item(i).data(Qt.UserRole):
                      self.lw_warstwy.item(i).checkState()
                      for i in range(self.lw_warstwy.count())}
        zrodla = zbierz_zrodla(self.le_nadrz.text().strip(),
                               self.wybrane(self.lw_foldery),
                               self.le_podf.text().strip()
                               or DOMYSLNY_PODFOLDER)
        kolejnosc = [n for n in DOMYSLNE_WARSTWY if n in zrodla] + \
            sorted(n for n in zrodla if n not in DOMYSLNE_WARSTWY)
        self.lw_warstwy.clear()
        for n in kolejnosc:
            it = QListWidgetItem(f'{n}  ({len(zrodla[n])} fold.)')
            it.setData(Qt.UserRole, n)
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            it.setCheckState(poprzednie.get(
                n, Qt.Checked if n in DOMYSLNE_WARSTWY else Qt.Unchecked))
            self.lw_warstwy.addItem(it)

    def _akceptuj(self):
        if not os.path.isdir(self.le_nadrz.text().strip()):
            QMessageBox.warning(self, _TYTUL, 'Wskaż istniejący folder '
                                'nadrzędny.')
            return
        if not self.wybrane(self.lw_foldery):
            QMessageBox.warning(self, _TYTUL, 'Zaznacz co najmniej jeden '
                                'folder.')
            return
        if not self.wybrane(self.lw_warstwy):
            QMessageBox.warning(self, _TYTUL, 'Zaznacz co najmniej jedną '
                                'warstwę.')
            return
        if not self.le_docel.text().strip():
            QMessageBox.warning(self, _TYTUL, 'Wskaż folder docelowy.')
            return
        self.accept()


def _istniejace_pliki(folder_docelowy, nazwy):
    if not os.path.isdir(folder_docelowy):
        return []
    obecne = warstwy_w_folderze(folder_docelowy)
    return [n for n in nazwy if n in obecne]


def uruchom(iface):
    dlg = PolaczWarstwyDialog(iface.mainWindow())
    if dlg.exec_() != QDialog.Accepted:
        return
    nadrz = dlg.le_nadrz.text().strip()
    podf = dlg.le_podf.text().strip() or DOMYSLNY_PODFOLDER
    docel = dlg.le_docel.text().strip()
    foldery = dlg.wybrane(dlg.lw_foldery)
    nazwy = dlg.wybrane(dlg.lw_warstwy)
    usun_dup = dlg.cb_duplikaty.isChecked()
    szukaj_nakl = dlg.cb_nakladania.isChecked()

    istn = _istniejace_pliki(docel, nazwy)
    if istn:
        odp = QMessageBox.warning(
            iface.mainWindow(), _TYTUL,
            f'W folderze docelowym\n{docel}\nsą już warstwy:\n'
            f'{", ".join(istn)}\n\nNadpisać je?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if odp != QMessageBox.Yes:
            return
    os.makedirs(docel, exist_ok=True)

    zrodla = zbierz_zrodla(nadrz, foldery, podf)
    pd = QProgressDialog('', 'Przerwij', 0, 100, iface.mainWindow())
    pd.setWindowTitle(_TYTUL)
    pd.setWindowModality(Qt.WindowModal)
    pd.setMinimumDuration(0)

    wyniki = []
    for nr, nazwa in enumerate(nazwy, 1):
        etykieta = f'{nazwa} ({nr}/{len(nazwy)})'
        pd.setLabelText(f'{etykieta} - wczytywanie...')
        pd.setValue(0)
        QApplication.processEvents()

        def postep(k, n, et=etykieta):
            pd.setLabelText(f'{et} - analiza geometrii {k}/{n}')
            pd.setValue(int(100 * k / n))
            QApplication.processEvents()
            return not pd.wasCanceled()

        r = polacz_warstwe(nazwa, zrodla.get(nazwa, []), docel, usun_dup,
                           szukaj_nakl, postep)
        if r is None or pd.wasCanceled():
            pd.close()
            iface.messageBar().pushMessage(
                _TYTUL, f'Przerwano na warstwie {nazwa}.', Qgis.Warning, 0)
            if wyniki:
                zapisz_raport(docel, wyniki)
            return
        wyniki.append(r)
    pd.close()

    raport = zapisz_raport(docel, wyniki)

    projekt = QgsProject.instance()
    grupa = projekt.layerTreeRoot().insertGroup(0, FOLDER_WYNIKOWY)
    for r in wyniki:
        if r['warstwa_nakl'] is not None:
            projekt.addMapLayer(r['warstwa_nakl'], False)
            grupa.addLayer(r['warstwa_nakl'])
        sciezka = os.path.join(docel, r['nazwa'] + '.shp')
        if r['zapisano'] and os.path.exists(sciezka):
            wl = QgsVectorLayer(sciezka, r['nazwa'], 'ogr')
            if wl.isValid():
                projekt.addMapLayer(wl, False)
                grupa.addLayer(wl)

    bledy = [r['nazwa'] for r in wyniki if r['blad_zapisu']]
    nakl = [r['nazwa'] for r in wyniki if r['nakladania']]
    tekst = f'Połączono {len(wyniki) - len(bledy)} warstw w {docel}.'
    if nakl:
        tekst += f' Nakładania: {", ".join(nakl)}.'
    if bledy:
        tekst += f' BŁĄD zapisu: {", ".join(bledy)}.'
    tekst += f' Raport: {raport}'
    iface.messageBar().pushMessage(
        _TYTUL, tekst, Qgis.Warning if (bledy or nakl) else Qgis.Success, 0)
