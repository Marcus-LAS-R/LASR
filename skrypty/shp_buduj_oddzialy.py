import os

from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QDialog, QFileDialog
from qgis.core import (
    Qgis, QgsMessageLog, QgsVectorLayer, QgsVectorFileWriter,
    QgsField, QgsFeature, QgsGeometry, QgsSpatialIndex, QgsProject,
    QgsCoordinateTransform, QgsWkbTypes,
)
import processing

from .ui.ui_aktualizuj_ewidencje import Ui_Dialog
from .pw import PasekPostepu

# pola wymagane w warstwie ORYG (oddziały) - to one trafiają do wynikowej
# warstwy oddziałów (żadne pole z wydzieleń nie ma sensu na poziomie
# oddziału, więc w odróżnieniu od shp_aktualizuj_ewidencje nie przepisujemy
# tu nic z warstwy NOWA poza geometrią)
_POLA_WYMAGANE = ['id', 'nr_wew']


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle('Zbuduj oddziały z wydzieleń')

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
            self, 'Wskaż warstwę ORYG (dawne oddziały)',
            self._folder_startowy(), 'Shapefile (*.shp)')[0]
        if sc:
            self.ui.lineEdit_oryg.setText(sc)

    def _wybierz_nowa(self):
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż warstwę NOWA (aktualne wydzielenia)',
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
            self.ui.lineEdit_wyjscie.setText(
                os.path.join(kat, 'a_oddz_pol.shp'))
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
    """ Pokazuje dialog wyboru warstwy ORYG (oddziały), warstwy NOWA
    (wydzielenia) i pliku wynikowego, po czym wywołuje
    BudujOddzialyZWydzielen. """
    dlg = _Dialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False
    return BudujOddzialyZWydzielen(
        iface, dlg.oryg_sc(), dlg.nowa_sc(), dlg.wyjscie_sc())


def _geometrie_oryg(oryg, transform):
    """ Zwraca słownik {fid: geometria} warstwy ORYG, przetransformowane do
    CRS warstwy NOWA - identyczna logika jak w shp_aktualizuj_ewidencje.py
    (zduplikowana zamiast importu w poprzek modułów, zgodnie z konwencją
    projektu). """
    wynik = {}
    for f in oryg.getFeatures():
        geom = f.geometry()
        if transform is not None:
            geom = QgsGeometry(geom)
            geom.transform(transform)
        wynik[f.id()] = geom
    return wynik


def _warstwa_z_wybranych(zrodlo, ids, nazwa):
    """ Tworzy warstwe memory z podzbiorem obiektow zrodla (po QGIS feature
    id) - z zachowaniem wszystkich pol i geometrii oryginalu - do zapisania
    jako shp z problematycznymi obiektami do recznej weryfikacji. """
    ids = set(ids)
    lyr = QgsVectorLayer(
        QgsWkbTypes.displayString(zrodlo.wkbType()) + '?crs=' +
        zrodlo.crs().authid(), nazwa, 'memory')
    lyr.dataProvider().addAttributes(zrodlo.fields())
    lyr.updateFields()
    feats = []
    for f in zrodlo.getFeatures():
        if f.id() in ids:
            nf = QgsFeature(lyr.fields())
            nf.setGeometry(f.geometry())
            nf.setAttributes(f.attributes())
            feats.append(nf)
    lyr.dataProvider().addFeatures(feats)
    return lyr


def _najlepszy_oddzial(wydz, oryg_geom, postep=None):
    """ Dla każdego wydzielenia NOWEJ warstwy zwraca fid oddziału ORYG,
    z którym ma największą część wspólną (albo None, jeśli w ogóle się nie
    nakłada z żadnym oddziałem ORYG). """
    si = QgsSpatialIndex()
    for oid, geom in oryg_geom.items():
        si.addFeature(oid, geom.boundingBox())

    wynik = {}
    n = max(wydz.featureCount(), 1)
    for i, f in enumerate(wydz.getFeatures()):
        geom = f.geometry()
        best_oid, best_pow = None, 0.0
        for oid in si.intersects(geom.boundingBox()):
            og = oryg_geom[oid]
            if not geom.intersects(og):
                continue
            try:
                pow = geom.intersection(og).area()
            except Exception:
                continue
            if pow > best_pow:
                best_pow = pow
                best_oid = oid
        wynik[f.id()] = best_oid
        if postep is not None and i % 100 == 0:
            postep.setValue(int(10 + 50 * i / n))
    return wynik


def BudujOddzialyZWydzielen(iface, oryg_sc, nowa_sc, wyjscie_sc):  # noqa
    """ Buduje warstwę oddziałów (a_oddz_pol) sklejając wydzielenia z
    warstwy NOWA (a_wydz_pol) w grupy wg dawnej warstwy oddziałów ORYG
    (a_oddz_pol_ORYG) - oddziały nie istnieją wprost w danych wydzieleń,
    więc przynależność każdego wydzielenia do oddziału ustalana jest przez
    największe nałożenie powierzchniowe z ORYG (ta sama zasada co w
    "Zaktualizuj użytki wg ORYG").

    Sklejone grupy wydzieleń dostają metadane (id, nr_wew) dopasowanego
    oddziału ORYG. Wydzielenia bez żadnego nałożenia (sieroty) oraz
    oddziały ORYG, do których nie trafiło żadne wydzielenie (np. zniesione/
    scalone), są pomijane w wyniku wynikowej warstwy oddziałów, ale
    zapisywane jako osobne warstwy shp (<wyjście>_SIEROTY.shp /
    <wyjście>_ODDZ_PUSTE.shp) obok głównego wyniku i dodawane do projektu -
    do wizualnej weryfikacji zamiast szukania po FID z logu.

    Oryginalne warstwy nie są modyfikowane - wynik trafia do wyjscie_sc.
    """
    QgsMessageLog.logMessage(
        '------ BUDOWA ODDZIAŁÓW Z WYDZIELEŃ --------- ', 'Las-R', Qgis.Info)

    oryg = QgsVectorLayer(oryg_sc, 'oddz_oryg', 'ogr')
    wydz = QgsVectorLayer(nowa_sc, 'wydz_nowa', 'ogr')

    if not oryg.isValid():
        iface.messageBar().pushCritical(
            'BŁĄD', 'Nie udało się wczytać warstwy ORYG (oddziały)')
        QgsMessageLog.logMessage('------ KONIEC (błąd) -------- \n', 'Las-R')
        return False
    if not wydz.isValid():
        iface.messageBar().pushCritical(
            'BŁĄD', 'Nie udało się wczytać warstwy NOWA (wydzielenia)')
        QgsMessageLog.logMessage('------ KONIEC (błąd) -------- \n', 'Las-R')
        return False

    pola_oryg = {f.name() for f in oryg.fields()}
    brakujace = [p for p in _POLA_WYMAGANE if p not in pola_oryg]
    if brakujace:
        iface.messageBar().pushCritical(
            'BŁĄD',
            'Warstwie ORYG (oddziały) brakuje kolumn: ' +
            ', '.join(brakujace))
        QgsMessageLog.logMessage('------ KONIEC (błąd) -------- \n', 'Las-R')
        return False

    postep = PasekPostepu(iface).stworz_pasek('Budowa oddziałów...')

    transform = None
    if oryg.crs().authid() != wydz.crs().authid():
        transform = QgsCoordinateTransform(
            oryg.crs(), wydz.crs(), QgsProject.instance())

    oryg_geom = _geometrie_oryg(oryg, transform)
    oryg_id = {}
    oryg_nrwew = {}
    for f in oryg.getFeatures():
        oryg_id[f.id()] = f['id']
        oryg_nrwew[f.id()] = f['nr_wew']

    postep.setValue(10)
    grupa_wg_wydz = _najlepszy_oddzial(wydz, oryg_geom, postep)
    postep.setValue(60)

    sieroty = [fid for fid, oid in grupa_wg_wydz.items() if oid is None]
    oddz_uzyte = {oid for oid in grupa_wg_wydz.values() if oid is not None}
    oddz_puste = set(oryg_geom.keys()) - oddz_uzyte

    # warstwa posrednia (memory) - kopia wydzielen NOWA z dopisanym tymczasowym
    # polem "_oryg_id" (fid oddzialu ORYG) do grupowania w native:dissolve
    posrednia = QgsVectorLayer(
        QgsWkbTypes.displayString(wydz.wkbType()) + '?crs=' +
        wydz.crs().authid(), 'wydz_grupy', 'memory')
    posrednia.startEditing()
    posrednia.dataProvider().addAttributes([QgsField('_oryg_id', QVariant.Int)])
    posrednia.updateFields()

    nowe_feat = []
    for f in wydz.getFeatures():
        oid = grupa_wg_wydz.get(f.id())
        if oid is None:
            continue
        nf = QgsFeature(posrednia.fields())
        nf.setGeometry(f.geometry())
        nf['_oryg_id'] = oid
        nowe_feat.append(nf)
    posrednia.dataProvider().addFeatures(nowe_feat)
    posrednia.commitChanges()

    postep.setValue(70)
    wynik_dissolve = processing.run('native:dissolve', {
        'INPUT': posrednia,
        'FIELD': ['_oryg_id'],
        'OUTPUT': 'memory:',
    })['OUTPUT']

    postep.setValue(85)

    pola_wyjsciowe = [
        QgsField('id', QVariant.Int),
        QgsField('nr_wew', QVariant.Int),
    ]
    wyj = QgsVectorLayer(
        QgsWkbTypes.displayString(wynik_dissolve.wkbType()) + '?crs=' +
        wydz.crs().authid(), 'a_oddz_pol', 'memory')
    wyj.startEditing()
    wyj.dataProvider().addAttributes(pola_wyjsciowe)
    wyj.updateFields()

    finalne_feat = []
    for f in wynik_dissolve.getFeatures():
        oid = f['_oryg_id']
        nf = QgsFeature(wyj.fields())
        nf.setGeometry(f.geometry())
        nf['id'] = oryg_id[oid]
        nf['nr_wew'] = oryg_nrwew[oid]
        finalne_feat.append(nf)
    wyj.dataProvider().addFeatures(finalne_feat)
    wyj.commitChanges()

    postep.setValue(95)
    QgsVectorFileWriter.writeAsVectorFormat(
        wyj, wyjscie_sc, 'UTF-8', wydz.crs(), 'ESRI Shapefile')

    postep.setValue(100)
    iface.messageBar().clearWidgets()

    warstwa = QgsVectorLayer(wyjscie_sc, os.path.splitext(
        os.path.basename(wyjscie_sc))[0], 'ogr')
    QgsProject.instance().addMapLayer(warstwa)

    folder_wyj = os.path.dirname(wyjscie_sc)
    baza = os.path.splitext(os.path.basename(wyjscie_sc))[0]

    if sieroty:
        sc_sieroty = os.path.join(folder_wyj, baza + '_SIEROTY.shp')
        QgsVectorFileWriter.writeAsVectorFormat(
            _warstwa_z_wybranych(wydz, sieroty, 'sieroty'),
            sc_sieroty, 'UTF-8', wydz.crs(), 'ESRI Shapefile')
        QgsProject.instance().addMapLayer(
            QgsVectorLayer(sc_sieroty, baza + '_SIEROTY', 'ogr'))
        QgsMessageLog.logMessage(
            'Wydzielenia bez nałożenia z żadnym oddziałem ORYG (fid): ' +
            ', '.join(str(x) for x in sieroty) + ' - zapisane do ' +
            sc_sieroty, 'Las-R', Qgis.Warning)
    if oddz_puste:
        sc_puste = os.path.join(folder_wyj, baza + '_ODDZ_PUSTE.shp')
        QgsVectorFileWriter.writeAsVectorFormat(
            _warstwa_z_wybranych(oryg, oddz_puste, 'oddz_puste'),
            sc_puste, 'UTF-8', oryg.crs(), 'ESRI Shapefile')
        QgsProject.instance().addMapLayer(
            QgsVectorLayer(sc_puste, baza + '_ODDZ_PUSTE', 'ogr'))
        QgsMessageLog.logMessage(
            'Oddziały ORYG bez żadnego dopasowanego wydzielenia (fid ORYG): '
            + ', '.join(str(x) for x in sorted(oddz_puste)) +
            ' - zapisane do ' + sc_puste, 'Las-R', Qgis.Warning)

    if sieroty or oddz_puste:
        iface.messageBar().pushWarning(
            'OK z uwagami',
            'Zbudowano ' + str(len(finalne_feat)) + ' oddziałów - ' +
            str(len(sieroty)) + ' wydzieleń bez dopasowania, ' +
            str(len(oddz_puste)) + ' oddziałów ORYG pominiętych - warstwy '
            'z tymi obiektami dodane do projektu (' + baza +
            '_SIEROTY / _ODDZ_PUSTE) - ' + os.path.basename(wyjscie_sc))
    else:
        iface.messageBar().pushSuccess(
            'OK',
            'Zbudowano ' + str(len(finalne_feat)) + ' oddziałów - ' +
            os.path.basename(wyjscie_sc))

    QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
    return True
