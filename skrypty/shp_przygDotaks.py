import os

from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QDialog, QFileDialog
from qgis.core import (
    Qgis, QgsFeature, QgsField, QgsFields, QgsMessageLog, QgsProject,
    QgsSpatialIndex, QgsVectorLayer,
)
import processing

from .baza_wrapper import Baza
from .shp_dopisz_kody import DopiszKody
from .ui.ui_przygDotaks import Ui_Dialog

_MIN_POW_HA = 0.01
_CRS = 'epsg:2180'

_TYP_POW_RB = {'INNE WYL', 'SUKCESJA', 'HAL', 'PŁAZ', 'ZRĄB'}

_ZABIEG_RB = {
    'IA', 'IB', 'IC',
    'IIA', 'IIB', 'IIC', 'IID', 'IIAU', 'IIBU', 'IICU', 'IIDU',
    'IIIA', 'IIIB', 'IIIAU', 'IIIBU',
    'IVA', 'IVB', 'IVC', 'IVD', 'IVAU', 'IVBU', 'IVCU', 'IVDU',
    'V',
}

_POLA_META = [
    QgsField('COUNTY_L', QVariant.String, '', 1),
    QgsField('COUNTY',   QVariant.String, '', 2),
    QgsField('DISTRICT', QVariant.String, '', 2),
    QgsField('MUNICIP',  QVariant.String, '', 3),
    QgsField('COMMUNITY',QVariant.String, '', 4),
    QgsField('GRP',      QVariant.String, '', 2),
    QgsField('L_EWID',   QVariant.String, '', 1),
    QgsField('UDZIAL',   QVariant.String, '', 5),
    QgsField('GAT',      QVariant.String, '', 10),
    QgsField('WIEK',     QVariant.Int),
    QgsField('ZADRZEW',  QVariant.Double, '', 10, 1),
    QgsField('POW_WYDZ', QVariant.Double, '', 10, 2),
    QgsField('TYP_POW',  QVariant.String, '', 20),
    QgsField('STRUKTUR', QVariant.String, '', 20),
    QgsField('SLMN_KOL', QVariant.Int),
    QgsField('STL',      QVariant.String, '', 20),
    QgsField('POKRYWA',  QVariant.String, '', 20),
    QgsField('ZABIEG',   QVariant.String, '', 20),
    QgsField('POW_ZAB',  QVariant.Double, '', 10, 4),
    QgsField('ODNOW',    QVariant.String, '', 20),
    QgsField('POW_ODN',  QVariant.Double, '', 10, 4),
    QgsField('AGROT',    QVariant.Double, '', 10, 4),
    QgsField('PIEL',     QVariant.Double, '', 10, 4),
    QgsField('INNE',     QVariant.String, '', 70),
]


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.pushButton_ls.clicked.connect(self._wybierz_ls)
        self.ui.pushButton_stare.clicked.connect(self._wybierz_stare)
        self.ui.pushButton_baza.clicked.connect(self._wybierz_baze)
        self.ui.lineEdit_ls.textChanged.connect(self._aktualizuj)
        self.ui.lineEdit_stare.textChanged.connect(self._aktualizuj)
        self.ui.lineEdit_baza.textChanged.connect(self._aktualizuj)

        ls_wykryta = self._wykryj_ls()
        if ls_wykryta:
            self.ui.lineEdit_ls.setText(ls_wykryta)

    def _folder_startowy(self):
        for lyr in QgsProject.instance().mapLayers().values():
            try:
                sc = lyr.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    return os.path.dirname(sc)
            except Exception:
                pass
        return ''

    def _wykryj_ls(self):
        shp_kat = self._folder_startowy()
        if shp_kat:
            kandydat = os.path.join(shp_kat, 'LS.shp')
            if os.path.isfile(kandydat):
                return kandydat
        return ''

    def _kat_proj(self):
        ls_sc = self.ui.lineEdit_ls.text().strip()
        if ls_sc and os.path.isfile(ls_sc):
            return os.path.dirname(os.path.dirname(ls_sc))
        return ''

    def _wybierz_ls(self):
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż warstwę LS nowe',
            self._folder_startowy(),
            'Shapefile (*.shp)',
        )[0]
        if sc:
            self.ui.lineEdit_ls.setText(sc)

    def _wybierz_stare(self):
        ls_sc = self.ui.lineEdit_ls.text().strip()
        start = os.path.dirname(ls_sc) if ls_sc and os.path.isfile(ls_sc) \
            else self._folder_startowy()
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż warstwę starych wydzieleń',
            start,
            'Shapefile (*.shp)',
        )[0]
        if sc:
            self.ui.lineEdit_stare.setText(sc)

    def _wybierz_baze(self):
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż bazę taksatora',
            self._kat_proj(),
            'Access MDB (*.mdb);;SQLite (*.sqlite)',
        )[0]
        if sc:
            self.ui.lineEdit_baza.setText(sc)

    def _aktualizuj(self):
        kat = self._kat_proj()
        self.ui.label_wyj.setText(
            os.path.join(kat, 'SHP_dotaks') if kat else '')
        ok = (bool(self.ui.lineEdit_ls.text().strip()) and
              bool(self.ui.lineEdit_stare.text().strip()) and
              bool(self.ui.lineEdit_baza.text().strip()))
        self.ui.pushButton_ok.setEnabled(ok)

    def ls_sc(self):
        return self.ui.lineEdit_ls.text().strip()

    def stare_sc(self):
        return self.ui.lineEdit_stare.text().strip()

    def baza_sc(self):
        return self.ui.lineEdit_baza.text().strip()


class PrzygotujDotaks:
    def __init__(self, iface):
        self.iface = iface

    def uruchom(self):
        dlg = _Dialog(self.iface)
        if dlg.exec_() != QDialog.Accepted:
            return

        ls_sc = dlg.ls_sc()
        stare_sc = dlg.stare_sc()
        baza_sc = dlg.baza_sc()

        ls = QgsVectorLayer(ls_sc, 'ls_tmp', 'ogr')
        if not ls.isValid():
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Nie można wczytać warstwy LS', Qgis.Critical, 10)
            return

        stare = QgsVectorLayer(stare_sc, 'stare_tmp', 'ogr')
        if not stare.isValid():
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Nie można wczytać warstwy starych wydzieleń',
                Qgis.Critical, 10)
            return

        kat_wyj = os.path.join(
            os.path.dirname(os.path.dirname(ls_sc)), 'SHP_dotaks')
        os.makedirs(kat_wyj, exist_ok=True)

        QgsMessageLog.logMessage(
            '--- PRZYGOTUJ DOTAKS ---', 'Las-R', Qgis.Info)

        bledy_geom = []
        bledy_ls = []
        self._sprawdz_ls(ls, bledy_ls)
        ls_proc = processing.run('native:fixgeometries', {
            'INPUT': ls, 'OUTPUT': 'memory:'})['OUTPUT']
        stare_fixed = self._sprawdz_i_napraw(stare, 'stare', bledy_geom)

        self._stworz_dotaks_nowe(ls_proc, stare_fixed, kat_wyj)
        self._stworz_dotaks_rb_nielas(
            ls_proc, stare_fixed, stare_sc, baza_sc, kat_wyj)
        self._stworz_dotaks_sprawdzenie(kat_wyj)
        self._pokaz_bledy_geom(bledy_geom, 'DOTAKS_geom_bledy')
        self._pokaz_bledy_geom(bledy_ls, 'LS_bledy_geom')

        self.iface.messageBar().pushMessage(
            'OK', 'Warstwy DOTAKS utworzone w SHP_dotaks', Qgis.Success, 10)
        QgsMessageLog.logMessage('--- KONIEC ---', 'Las-R', Qgis.Info)

    # ------------------------------------------------------------------
    # DOTAKS_nowe
    # ------------------------------------------------------------------

    def _stworz_dotaks_nowe(self, ls, stare, kat_wyj):
        diff = processing.run('native:difference', {
            'INPUT': ls,
            'OVERLAY': stare,
            'OUTPUT': 'memory:',
        })['OUTPUT']
        diff = self._napraw_geom(diff)

        single = processing.run('native:multiparttosingleparts', {
            'INPUT': diff,
            'OUTPUT': 'memory:',
        })['OUTPUT']

        single = self._policz_pow_graf(single)

        idx = QgsSpatialIndex(single.getFeatures())
        ids_do_usuniecia = []
        for feat in single.getFeatures():
            if (feat['POW_GRAF'] or 0) >= _MIN_POW_HA:
                continue
            geom = feat.geometry()
            kandydaci = idx.intersects(geom.boundingBox())
            dotyka = any(
                single.getFeature(k).geometry().intersects(geom)
                for k in kandydaci if k != feat.id()
            )
            if not dotyka:
                ids_do_usuniecia.append(feat.id())
        if ids_do_usuniecia:
            single.dataProvider().deleteFeatures(ids_do_usuniecia)

        dissolved = processing.run('native:dissolve', {
            'INPUT': single,
            'FIELD': [],
            'OUTPUT': 'memory:',
        })['OUTPUT']

        merged = processing.run('native:multiparttosingleparts', {
            'INPUT': dissolved,
            'OUTPUT': 'memory:',
        })['OUTPUT']

        merged = self._policz_pow_graf(merged)

        idx_stare = QgsSpatialIndex(stare.getFeatures())
        ids_do_usuniecia = []
        for feat in merged.getFeatures():
            if (feat['POW_GRAF'] or 0) >= 0.10:
                continue
            geom = feat.geometry()
            kandydaci = idx_stare.intersects(geom.boundingBox())
            dotyka_stare = any(
                stare.getFeature(k).geometry().intersects(geom)
                for k in kandydaci
            )
            if dotyka_stare:
                ids_do_usuniecia.append(feat.id())
        if ids_do_usuniecia:
            merged.dataProvider().deleteFeatures(ids_do_usuniecia)

        self._eksportuj(merged, kat_wyj, 'DOTAKS_nowe')

    # ------------------------------------------------------------------
    # DOTAKS_rb_nielas
    # ------------------------------------------------------------------

    def _stworz_dotaks_rb_nielas(self, ls, stare, stare_sc, baza_sc, kat_wyj):
        wpol = self._dopisz_metadane(stare, stare_sc, baza_sc)
        if wpol is None:
            return

        pasujace = [f for f in wpol.getFeatures()
                    if self._pasuje_rb_nielas(f)]

        wynik = QgsVectorLayer(
            f'MultiPolygon?crs={_CRS}', 'DOTAKS_rb_nielas', 'memory')
        wynik_data = wynik.dataProvider()
        wynik_data.addAttributes(wpol.fields().toList())
        wynik.updateFields()
        wynik_data.addFeatures(pasujace)

        clipped = processing.run('native:clip', {
            'INPUT': wynik,
            'OVERLAY': ls,
            'OUTPUT': 'memory:',
        })['OUTPUT']
        clipped = self._napraw_geom(clipped)

        clipped = self._policz_pow_graf(clipped)

        ids_do_usuniecia = [
            f.id() for f in clipped.getFeatures()
            if (f['POW_GRAF'] or 0) < 0.05
        ]
        if ids_do_usuniecia:
            clipped.dataProvider().deleteFeatures(ids_do_usuniecia)

        self._eksportuj(clipped, kat_wyj, 'DOTAKS_rb_nielas')

    def _pasuje_rb_nielas(self, feat):
        typ = (feat['TYP_POW'] or '').strip()
        if typ in _TYP_POW_RB:
            return True
        zabieg = (feat['ZABIEG'] or '').strip()
        if zabieg:
            kody = {z.strip() for z in zabieg.split(',')}
            if kody & _ZABIEG_RB:
                return True
        return False

    # ------------------------------------------------------------------
    # DOTAKS_sprawdzenie  (TODO)
    # ------------------------------------------------------------------

    def _stworz_dotaks_sprawdzenie(self, kat_wyj):
        pusty = QgsVectorLayer(
            f'MultiPolygon?crs={_CRS}', 'DOTAKS_sprawdzenie', 'memory')
        self._eksportuj(pusty, kat_wyj, 'DOTAKS_sprawdzenie')

    # ------------------------------------------------------------------
    # Pomocnicze
    # ------------------------------------------------------------------

    def _napraw_geom(self, lyr):
        return processing.run('native:fixgeometries', {
            'INPUT': lyr, 'OUTPUT': 'memory:'})['OUTPUT']

    def _sprawdz_ls(self, lyr, bledy):
        check = processing.run('native:checkvalidity', {
            'INPUT_LAYER': lyr,
            'METHOD': 1,
            'VALID_OUTPUT': 'memory:',
            'INVALID_OUTPUT': 'memory:',
            'ERROR_OUTPUT': 'memory:',
        })
        for feat in check['INVALID_OUTPUT'].getFeatures():
            bledy.append(('ls', feat.geometry()))

    def _sprawdz_i_napraw(self, lyr, etykieta, bledy):
        check = processing.run('native:checkvalidity', {
            'INPUT_LAYER': lyr,
            'METHOD': 1,
            'VALID_OUTPUT': 'memory:',
            'INVALID_OUTPUT': 'memory:',
            'ERROR_OUTPUT': 'memory:',
        })
        for feat in check['INVALID_OUTPUT'].getFeatures():
            bledy.append((etykieta, feat.geometry()))
        return processing.run('native:fixgeometries', {
            'INPUT': lyr,
            'OUTPUT': 'memory:',
        })['OUTPUT']

    def _pokaz_bledy_geom(self, bledy, nazwa):
        if not bledy:
            return
        warstwa = QgsVectorLayer(f'Polygon?crs={_CRS}', nazwa, 'memory')
        prov = warstwa.dataProvider()
        prov.addAttributes([QgsField('ZRODLO', QVariant.String, '', 20)])
        warstwa.updateFields()
        feats = []
        for etykieta, geom in bledy:
            f = QgsFeature()
            f.setGeometry(geom)
            f.setAttributes([etykieta])
            feats.append(f)
        prov.addFeatures(feats)
        QgsProject.instance().addMapLayer(warstwa)
        QgsMessageLog.logMessage(
            f'DOTAKS: {len(bledy)} ficzerów z błędną geometrią → warstwa DOTAKS_geom_bledy',
            'Las-R', Qgis.Warning)

    def _dopisz_metadane(self, wydz, wydz_path, baza_sc):
        d = DopiszKody(self.iface)
        d.wydz = wydz
        d.wydz_path = wydz_path
        d.baza = Baza(baza_sc)

        if not d.pobierzBaze():
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Nie udało się pobrać danych z bazy', Qgis.Critical, 10)
            return None

        wpol = QgsVectorLayer(f'MultiPolygon?crs={_CRS}', 'meta_tmp', 'memory')
        wpol_data = wpol.dataProvider()
        wpol_data.addAttributes(wydz.fields().toList())
        wpol.updateFields()
        wpol_data.addFeatures(list(wydz.getFeatures()))

        obecne = [x.name() for x in wpol.fields()]
        nowe = QgsFields()
        for p in _POLA_META:
            if p.name() not in obecne:
                nowe.append(p)
        if d.przestoje_flag:
            nowe.append(QgsField('PRZEST', QVariant.Double, 'double', 10, 4))
        wpol_data.addAttributes(nowe)
        wpol.updateFields()

        fnm = wpol_data.fieldNameMap()
        sl_dop = {}
        for feat in wpol.getFeatures():
            adr = feat['ADR_LES']
            if adr not in d.sl:
                sl_dop[feat.id()] = {fnm['SLMN_KOL']: 0}
                continue
            gat = d.isNone(d.sl[adr][4])
            if gat != ' ':
                gat = gat[:1].upper() + gat[1:].lower()
            dop = {
                fnm['TYP_POW']:  d.isNone(d.sl[adr][0]),
                fnm['STL']:      d.isNone(d.sl[adr][1]),
                fnm['POW_WYDZ']: d.isNone(d.sl[adr][2], typ='i'),
                fnm['UDZIAL']:   d.isNone(d.sl[adr][3]),
                fnm['GAT']:      d.isNone(gat),
                fnm['WIEK']:     d.isNone(d.sl[adr][5], typ='i'),
                fnm['ZADRZEW']:  round(d.isNone(d.sl[adr][6], typ='i'), 1),
                fnm['STRUKTUR']: d.isNone(d.sl[adr][8]),
                fnm['L_EWID']:   'N' if adr in d.nielesne else 'T',
                fnm['POKRYWA']:  d.isNone(d.sl[adr][9]),
                fnm['SLMN_KOL']: d.kody(
                    d.isNone(d.sl[adr][4]),
                    d.isNone(d.sl[adr][5], typ='i'),
                    d.isNone(d.sl[adr][8]),
                    d.isNone(d.sl[adr][0]),
                ),
            }
            if adr in d.dopis:
                dp = d.dopis[adr]
                if 'AGROT' in dp:
                    dop[fnm['AGROT']] = dp['AGROT']
                if 'PIEL' in dp:
                    dop[fnm['PIEL']] = dp['PIEL']
                if d.przestoje_flag:
                    dop[fnm['PRZEST']] = d.isNone(
                        dp.get('PRZEST', 0), typ='i')
                if 'INNE' in dp:
                    dop[fnm['INNE']] = ','.join(
                        [d.isNone(x) for x in dp['INNE']])
                for kk in ['ODNOW', 'ZABIEG']:
                    if kk in dp:
                        try:
                            dop[fnm[kk]] = ','.join(
                                [x[0] for x in dp[kk]])
                            dop[fnm['POW_' + kk[:3]]] = max(
                                [x[1] for x in dp[kk]])
                        except Exception:
                            QgsMessageLog.logMessage(
                                'Niedopisane zabiegi w wydz: ' + adr,
                                'Las-R', Qgis.Warning)
            sl_dop[feat.id()] = dop
        for fid, attrs in sl_dop.items():
            wpol_data.changeAttributeValues({fid: attrs})

        return wpol

    def _policz_pow_graf(self, lyr):
        if 'POW_GRAF' not in [f.name() for f in lyr.fields()]:
            lyr.dataProvider().addAttributes(
                [QgsField('POW_GRAF', QVariant.Double, 'double', 10, 4)])
            lyr.updateFields()
        fnm = lyr.dataProvider().fieldNameMap()
        lyr.dataProvider().changeAttributeValues({
            f.id(): {fnm['POW_GRAF']: f.geometry().area() / 10000}
            for f in lyr.getFeatures()
        })
        return lyr

    def _eksportuj(self, lyr, kat_wyj, nazwa):
        wyj_sc = os.path.join(kat_wyj, nazwa + '.shp')
        processing.run('native:savefeatures', {
            'INPUT': lyr,
            'OUTPUT': wyj_sc,
        })
        QgsProject.instance().addMapLayer(
            QgsVectorLayer(wyj_sc, nazwa, 'ogr'))
