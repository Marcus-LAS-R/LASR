import os

from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QDialog, QFileDialog
from qgis.core import (
    Qgis, QgsMessageLog, QgsVectorLayer, QgsVectorFileWriter,
    QgsField, QgsFeature, QgsGeometry, QgsSpatialIndex, QgsProject,
    QgsCoordinateTransform, QgsWkbTypes,
)

from .ui.ui_aktualizuj_ewidencje import Ui_Dialog
from .pw import PasekPostepu

# pola przepisywane z ORYG do wynikowej warstwy - w tej kolejności dopisywane
# jako nowe kolumny (szerokość dopasowana do oryginalnych pól w ORYG, DBF)
_POLA_DOPISYWANE = ['id', 'nadlesn', 'nr_dzialki', 'nr_kont']


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.pushButton_oryg.clicked.connect(self._wybierz_oryg)
        self.ui.pushButton_nowa.clicked.connect(self._wybierz_nowa)
        self.ui.pushButton_wyjscie.clicked.connect(self._wybierz_wyjscie)
        self.ui.lineEdit_oryg.textChanged.connect(self._aktualizuj)
        self.ui.lineEdit_nowa.textChanged.connect(self._na_zmiane_nowej)
        self.ui.lineEdit_wyjscie.textChanged.connect(self._aktualizuj)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

        aktywna = self.iface.activeLayer()
        if aktywna is not None:
            try:
                sc = aktywna.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    self.ui.lineEdit_nowa.setText(sc)
            except Exception:
                pass

        self._aktualizuj()

    def _folder_startowy(self):
        for pole in [self.ui.lineEdit_nowa, self.ui.lineEdit_oryg]:
            sc = pole.text().strip()
            if sc and os.path.isfile(sc):
                return os.path.dirname(sc)
        for lyr in QgsProject.instance().mapLayers().values():
            try:
                sc = lyr.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    return os.path.dirname(sc)
            except Exception:
                pass
        return ''

    def _wybierz_oryg(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż warstwę ORYG (dawne użytki)',
            self._folder_startowy(), 'Shapefile (*.shp)')[0]
        if sc:
            self.ui.lineEdit_oryg.setText(sc)

    def _wybierz_nowa(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż warstwę NOWA (aktualne użytki)',
            self._folder_startowy(), 'Shapefile (*.shp)')[0]
        if sc:
            self.ui.lineEdit_nowa.setText(sc)

    def _wybierz_wyjscie(self):
        sc = QFileDialog.getSaveFileName(
            self, 'Zapisz wynik jako',
            self._folder_startowy(), 'Shapefile (*.shp)')[0]
        if sc:
            if not sc.lower().endswith('.shp'):
                sc += '.shp'
            self.ui.lineEdit_wyjscie.setText(sc)

    def _na_zmiane_nowej(self):
        sc = self.ui.lineEdit_nowa.text().strip()
        if sc and os.path.isfile(sc) and \
                not self.ui.lineEdit_wyjscie.text().strip():
            kat = os.path.dirname(sc)
            nazwa = os.path.splitext(os.path.basename(sc))[0]
            self.ui.lineEdit_wyjscie.setText(
                os.path.join(kat, nazwa + '_AKTUALNA.shp'))
        self._aktualizuj()

    def _aktualizuj(self):
        ok = bool(self.ui.lineEdit_oryg.text().strip()) and \
            bool(self.ui.lineEdit_nowa.text().strip()) and \
            bool(self.ui.lineEdit_wyjscie.text().strip())
        self.ui.pushButton_ok.setEnabled(ok)

    def oryg_sc(self):
        return self.ui.lineEdit_oryg.text().strip()

    def nowa_sc(self):
        return self.ui.lineEdit_nowa.text().strip()

    def wyjscie_sc(self):
        return self.ui.lineEdit_wyjscie.text().strip()


def uruchom(iface):
    """ Pokazuje dialog wyboru warstw ORYG/NOWA i pliku wynikowego, po czym
    wywołuje AktualizujEwidencjeNctwo. """
    dlg = _Dialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False
    return AktualizujEwidencjeNctwo(
        iface, dlg.oryg_sc(), dlg.nowa_sc(), dlg.wyjscie_sc())


def _geometrie_oryg(oryg, transform):
    """ Zwraca słownik {fid: geometria} warstwy ORYG, przetransformowane do
    CRS warstwy NOWA (jeśli się różnią - w tych danych oba układy to
    EPSG:2180, ale pod inną etykietą realizacji ETRS89/ETRF2000-PL, więc
    transformacja i tak wychodzi praktycznie tożsamościowa). """
    wynik = {}
    for f in oryg.getFeatures():
        geom = f.geometry()
        if transform is not None:
            geom = QgsGeometry(geom)
            geom.transform(transform)
        wynik[f.id()] = geom
    return wynik


def _nakladajace_sie(nowa, oryg_geom, postep=None):
    """ Dla każdego poligonu NOWEJ warstwy zwraca listę wszystkich
    nakładających się konturów ORYG jako (oryg_fid, powierzchnia_części
    wspólnej), posortowaną malejąco wg powierzchni. Potrzebujemy pełnej
    listy (nie tylko najlepszego dopasowania), bo przy numeracji nr_kont
    w grupie działki liczy się też 2., 3. itd. najlepsze nałożenie. """
    si = QgsSpatialIndex()
    for fid, geom in oryg_geom.items():
        si.addFeature(fid, geom.boundingBox())

    wynik = {}
    n = max(nowa.featureCount(), 1)
    for i, f in enumerate(nowa.getFeatures()):
        geom = f.geometry()
        pary = []
        for oid in si.intersects(geom.boundingBox()):
            og = oryg_geom[oid]
            if not geom.intersects(og):
                continue
            try:
                pow = geom.intersection(og).area()
            except Exception:
                continue
            if pow > 0:
                pary.append((oid, pow))
        pary.sort(key=lambda x: x[1], reverse=True)
        wynik[f.id()] = pary
        if postep is not None and i % 100 == 0:
            postep.setValue(int(10 + 55 * i / n))
    return wynik


def _przypisz_nr_kont(nakladanie, grupa_wg_nowa, oryg_nr_kont, oryg_nr_dzialki,
                       nowa_pow):
    """ Numeruje nr_kont wg zasady "największe nałożenie dziedziczy stary
    numer konturu": w obrębie grupy (ta sama przypisana nr_dzialki) dopasuj
    zachłannie pary (nowy poligon, stary kontur) w kolejności malejącej
    powierzchni części wspólnej - każdy stary kontur oddaje swój numer co
    najwyżej jednemu nowemu poligonowi (temu z największym nałożeniem).
    Poligony z grupy, które nie dostały numeru tą drogą (bo użytek się
    podzielił na więcej części), dostają nowe numery kontynuujące numerację
    w tej samej grupie, od największego już zajętego numeru w górę -
    zaczynając od największego "osieroconego" fragmentu. """
    oryg_wg_dzialki = {}
    for oid, nr_dz in oryg_nr_dzialki.items():
        oryg_wg_dzialki.setdefault(nr_dz, []).append(oid)

    nowa_wg_dzialki = {}
    for fid, nr_dz in grupa_wg_nowa.items():
        nowa_wg_dzialki.setdefault(nr_dz, []).append(fid)

    wynik = {}
    for nr_dz, nowa_fidy in nowa_wg_dzialki.items():
        oryg_w_grupie = set(oryg_wg_dzialki.get(nr_dz, []))

        pary_grupy = []
        for fid in nowa_fidy:
            for oid, pow in nakladanie[fid]:
                if oid in oryg_w_grupie:
                    pary_grupy.append((fid, oid, pow))
        pary_grupy.sort(key=lambda x: x[2], reverse=True)

        przypisane_nowa = set()
        przypisane_oryg = set()
        for fid, oid, _pow in pary_grupy:
            if fid in przypisane_nowa or oid in przypisane_oryg:
                continue
            wynik[fid] = oryg_nr_kont[oid]
            przypisane_nowa.add(fid)
            przypisane_oryg.add(oid)

        reszta = [fid for fid in nowa_fidy if fid not in przypisane_nowa]
        if reszta:
            nastepny = max(
                (oryg_nr_kont[oid] for oid in oryg_w_grupie), default=0) + 1
            reszta.sort(key=lambda fid: nowa_pow[fid], reverse=True)
            for fid in reszta:
                wynik[fid] = nastepny
                nastepny += 1

    return wynik


def AktualizujEwidencjeNctwo(iface, oryg_sc, nowa_sc, wyjscie_sc):  # noqa
    """ Dopisuje do kopii warstwy NOWA (aktualne użytki) cztery pola z
    warstwy ORYG (dawne użytki): id, nadlesn, nr_dzialki, nr_kont - dobierane
    wg największego nałożenia powierzchniowego, bo geometrie obu warstw się
    różnią (NOWA ma więcej, nieco innych poligonów).

    id/nadlesn/nr_dzialki: wartości z konturu ORYG, który najbardziej
    nakłada się na dany poligon NOWA.

    nr_kont: w obrębie grupy o tej samej przypisanej nr_dzialki, kontur ORYG
    oddaje swój numer temu poligonowi NOWA, z którym ma największą część
    wspólną (czyli "największemu kawałkowi" po podziale użytku) - reszta
    (nowe, dodatkowe fragmenty powstałe z podziału) dostaje kolejne wolne
    numery w tej samej grupie.

    Poligony NOWA, które w ogóle nie nakładają się z żadnym konturem ORYG
    (nowe działki bez odpowiednika w starej ewidencji), zostają z pustymi
    (NULL) polami - zgłaszane w podsumowaniu do ręcznej weryfikacji.

    Oryginalne warstwy nie są modyfikowane - wynik trafia do wyjscie_sc.
    """
    QgsMessageLog.logMessage(
        '------ AKTUALIZACJA EWIDENCJI N-CTWO --------- ', 'Las-R', Qgis.Info)

    oryg = QgsVectorLayer(oryg_sc, 'oryg_uzytki', 'ogr')
    nowa = QgsVectorLayer(nowa_sc, 'nowa_uzytki', 'ogr')

    if not oryg.isValid():
        iface.messageBar().pushCritical(
            'BŁĄD', 'Nie udało się wczytać warstwy ORYG')
        QgsMessageLog.logMessage('------ KONIEC (błąd) -------- \n', 'Las-R')
        return False
    if not nowa.isValid():
        iface.messageBar().pushCritical(
            'BŁĄD', 'Nie udało się wczytać warstwy NOWA')
        QgsMessageLog.logMessage('------ KONIEC (błąd) -------- \n', 'Las-R')
        return False

    pola_oryg = {f.name() for f in oryg.fields()}
    brakujace = [p for p in _POLA_DOPISYWANE if p not in pola_oryg]
    if brakujace:
        iface.messageBar().pushCritical(
            'BŁĄD',
            'Warstwie ORYG brakuje kolumn: ' + ', '.join(brakujace))
        QgsMessageLog.logMessage('------ KONIEC (błąd) -------- \n', 'Las-R')
        return False

    postep = PasekPostepu(iface).stworz_pasek('Aktualizacja ewidencji...')

    transform = None
    if oryg.crs().authid() != nowa.crs().authid():
        transform = QgsCoordinateTransform(
            oryg.crs(), nowa.crs(), QgsProject.instance())

    oryg_geom = _geometrie_oryg(oryg, transform)
    oryg_id = {}
    oryg_nadlesn = {}
    oryg_nr_dzialki = {}
    oryg_nr_kont = {}
    for f in oryg.getFeatures():
        oryg_id[f.id()] = f['id']
        oryg_nadlesn[f.id()] = f['nadlesn']
        oryg_nr_dzialki[f.id()] = f['nr_dzialki']
        oryg_nr_kont[f.id()] = f['nr_kont']

    postep.setValue(10)
    nakladanie = _nakladajace_sie(nowa, oryg_geom, postep)
    postep.setValue(65)

    nowa_pow = {}
    grupa_wg_nowa = {}
    nadlesn_wg_nowa = {}
    id_wg_nowa = {}
    sieroty = []
    for fid, pary in nakladanie.items():
        if not pary:
            sieroty.append(fid)
            continue
        best_oid = pary[0][0]
        grupa_wg_nowa[fid] = oryg_nr_dzialki[best_oid]
        nadlesn_wg_nowa[fid] = oryg_nadlesn[best_oid]
        id_wg_nowa[fid] = oryg_id[best_oid]

    for f in nowa.getFeatures():
        nowa_pow[f.id()] = f.geometry().area()

    postep.setValue(70)
    nr_kont_wg_nowa = _przypisz_nr_kont(
        nakladanie, grupa_wg_nowa, oryg_nr_kont, oryg_nr_dzialki, nowa_pow)
    postep.setValue(80)

    pola_wyjsciowe = nowa.fields()
    nowe_pola = [
        QgsField('id', QVariant.Int),
        QgsField('nadlesn', QVariant.Int),
        QgsField('nr_dzialki', QVariant.Int),
        QgsField('nr_kont', QVariant.Int),
    ]

    wyj = QgsVectorLayer(
        QgsWkbTypes.displayString(nowa.wkbType()) + '?crs=' +
        nowa.crs().authid(),
        'wynik', 'memory')
    wyj.startEditing()
    wyj.dataProvider().addAttributes(list(pola_wyjsciowe) + nowe_pola)
    wyj.updateFields()

    nowe_feat = []
    for f in nowa.getFeatures():
        nf = QgsFeature(wyj.fields())
        nf.setGeometry(f.geometry())
        nf.setAttributes(
            list(f.attributes()) + [
                id_wg_nowa.get(f.id()),
                nadlesn_wg_nowa.get(f.id()),
                grupa_wg_nowa.get(f.id()),
                nr_kont_wg_nowa.get(f.id()),
            ])
        nowe_feat.append(nf)

    wyj.dataProvider().addFeatures(nowe_feat)
    wyj.commitChanges()

    postep.setValue(90)
    QgsVectorFileWriter.writeAsVectorFormat(
        wyj, wyjscie_sc, 'UTF-8', nowa.crs(), 'ESRI Shapefile')

    postep.setValue(100)
    iface.messageBar().clearWidgets()

    warstwa = QgsVectorLayer(wyjscie_sc, os.path.splitext(
        os.path.basename(wyjscie_sc))[0], 'ogr')
    QgsProject.instance().addMapLayer(warstwa)

    zaktualizowane = len(nowa_pow) - len(sieroty)
    if sieroty:
        QgsMessageLog.logMessage(
            'Poligony bez odpowiednika w ORYG (fid): ' +
            ', '.join(str(x) for x in sieroty), 'Las-R', Qgis.Warning)
        iface.messageBar().pushWarning(
            'OK z uwagami',
            'Zaktualizowano ' + str(zaktualizowane) + ' poligonów, ' +
            str(len(sieroty)) + ' nie nakłada się z żadnym konturem ORYG '
            '(puste pola - patrz log Las-R) - ' + os.path.basename(
                wyjscie_sc))
    else:
        iface.messageBar().pushSuccess(
            'OK',
            'Zaktualizowano ewidencję dla ' + str(zaktualizowane) +
            ' poligonów - ' + os.path.basename(wyjscie_sc))

    QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
    return True
