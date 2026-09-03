import os

from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.QtCore import QVariant
from qgis.core import (
    Qgis, QgsFeature, QgsMessageLog, QgsProject, QgsVectorFileWriter,
    QgsVectorLayer, QgsField, QgsFields,
)
import processing

from .baza_wrapper import Baza
from .shp_dopisz_kody import DopiszKody
from . import kasowniki
from . import warstwa_opisow_dock as opis
from .ui.ui_przygCiecieStUPUL import Ui_Dialog

_TEMP = 'WYDZ_POL_stare_multipart'

_KOLUMNY_POL = [
    QgsField('ADR_LES',  QVariant.String, '', 25),
    QgsField('ODDZ',     QVariant.String, '', 6),
    QgsField('WYDZ',     QVariant.String, '', 4),
    QgsField('TYP_POW',  QVariant.String, '', 20),
    QgsField('UDZIAL',   QVariant.String, '', 5),
    QgsField('GAT',      QVariant.String, '', 10),
    QgsField('WIEK',     QVariant.Int),
    QgsField('ZADRZEW',  QVariant.Double, '', 10, 1),
    QgsField('ZABIEG',   QVariant.String, '', 20),
    QgsField('STL',      QVariant.String, '', 20),
    QgsField('GRP',      QVariant.String, '', 2),
    QgsField('POW_WYDZ', QVariant.String, '', 10, 4),
]

# mapowanie starych nazw pól (stary UPUL) na nowe
_MAPA_STARYCH_POL = [
    ('COUNTY_CD',  'COUNTY',    2),
    ('DISTRICT_C', 'DISTRICT',  2),
    ('MUNICIPALI', 'MUNICIP',   3),
    ('COMMUNITY_', 'COMMUNITY', 4),
]


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.pushButton_wydz.clicked.connect(self._wybierz_wydz)
        self.ui.pushButton_baza.clicked.connect(self._wybierz_baze)
        self.ui.lineEdit_wydz.textChanged.connect(self._aktualizuj_ok)
        self.ui.lineEdit_baza.textChanged.connect(self._aktualizuj_ok)

    def _folder_startowy(self):
        for lyr in QgsProject.instance().mapLayers().values():
            try:
                sc = lyr.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    return os.path.dirname(sc)
            except Exception:
                pass
        return ''

    def _folder_wydz(self):
        start = self._folder_startowy()
        shp = os.path.join(os.path.dirname(start), 'SHP')
        return shp if os.path.isdir(shp) else start

    def _wybierz_wydz(self):
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż warstwę starych wydzieleń',
            self._folder_wydz(),
            'Shapefile (*.shp)',
        )[0]
        if sc:
            self.ui.lineEdit_wydz.setText(sc)

    def _wybierz_baze(self):
        wydz_sc = self.ui.lineEdit_wydz.text().strip()
        start = ''
        if wydz_sc and os.path.isfile(wydz_sc):
            start = os.path.dirname(os.path.dirname(wydz_sc))
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż bazę taksatora',
            start,
            'Access MDB (*.mdb);;SQLite (*.sqlite)',
        )[0]
        if sc:
            self.ui.lineEdit_baza.setText(sc)
            self.ui.label_wyj.setText(
                os.path.join(os.path.dirname(sc), 'SHP_stare'))

    def _aktualizuj_ok(self):
        ok = bool(self.ui.lineEdit_wydz.text().strip()) and \
             bool(self.ui.lineEdit_baza.text().strip())
        self.ui.pushButton_ok.setEnabled(ok)

    def wydz_sc(self):
        return self.ui.lineEdit_wydz.text().strip()

    def baza_sc(self):
        return self.ui.lineEdit_baza.text().strip()


class PrzygotujCiecieStUPUL:
    def __init__(self, iface):
        self.iface = iface

    def uruchom(self):
        dlg = _Dialog(self.iface)
        if dlg.exec_() != QDialog.Accepted:
            return

        wydz_path = dlg.wydz_sc()
        baza_sc = dlg.baza_sc()

        wydz = QgsVectorLayer(wydz_path, 'wydz_tmp', 'ogr')
        if not wydz.isValid():
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Nie można wczytać wskazanej warstwy', Qgis.Critical, 10)
            return

        kat_wyj = os.path.join(os.path.dirname(baza_sc), 'SHP_stare')
        os.makedirs(kat_wyj, exist_ok=True)

        QgsMessageLog.logMessage(
            '--- PRZYGOTUJ CIECIE ST UPUL ---', 'Las-R', Qgis.Info)

        wpol_temp = self._dopisz_metadane(wydz, wydz_path, baza_sc)
        if wpol_temp is None:
            return

        wydz_pol_sc = os.path.join(kat_wyj, 'WYDZ_POL_stare.shp')
        wpol_uproszczona = self._buduj_pol_uproszczona(wpol_temp, wydz_pol_sc)

        wydz_pkt_sc = os.path.join(kat_wyj, 'WYDZ_PKT_stare.shp')
        self._buduj_pkt(wpol_uproszczona, wydz_pkt_sc)

        self._utworz_warstwe_kas(wpol_temp, kat_wyj, baza_sc)
        del wpol_temp

        wydz_pol = QgsVectorLayer(wydz_pol_sc, 'WYDZ_POL_stare', 'ogr')
        QgsProject.instance().addMapLayer(wydz_pol)
        wydz_pkt = QgsVectorLayer(wydz_pkt_sc, 'WYDZ_PKT_stare', 'ogr')
        QgsProject.instance().addMapLayer(wydz_pkt)
        self._utworz_warstwy_opis(os.path.dirname(baza_sc))

        self.iface.messageBar().pushMessage(
            'OK', 'Warstwy utworzone w folderach SHP_stare i SHP_opis',
            Qgis.Success, 10)
        QgsMessageLog.logMessage('--- KONIEC ---', 'Las-R', Qgis.Info)

    def _utworz_warstwy_opis(self, kat_root):
        """Tworzy folder SHP_opis (siostrzany do SHP_stare) z pustymi
        warstwami "grupy opis" (opis_klon/opis_pkt/opis_notatki, patrz
        warstwa_opisow_dock.py) - gotowymi do podjęcia przez dockwidget
        "Warstwy do opisów" bez ręcznego tworzenia ich od zera. Nie
        nadpisuje plików, jeśli już istnieją (np. z poprzedniego
        uruchomienia)."""
        kat_opis = os.path.join(kat_root, opis.NAZWA_FOLDER_OPIS)
        for nazwa, typ_geom_txt, pola in opis.WARSTWY_OPIS:
            sciezka = os.path.join(kat_opis, nazwa + '.shp')
            if os.path.isfile(sciezka):
                continue
            opis._utworz_warstwe(sciezka, typ_geom_txt, pola, nazwa)

    def _utworz_warstwe_kas(self, wpol_temp, kat_wyj, baza_sc):
        """Generuje warstwę kasowników (KAS_stare) na podstawie tej samej
        wieloczęściowej warstwy, z której budowane są WYDZ_POL_stare/
        WYDZ_PKT_stare - patrz kasowniki.py (port z wtyczki LCH). Jeśli w
        folderze SHP (siostrzanym do SHP_stare) jest LINIE.shp, dodatkowo
        dokładane są kasowniki na przecięciach z tą warstwą."""
        linie_sc = os.path.join(
            os.path.dirname(baza_sc), 'SHP', 'LINIE.shp')
        if not os.path.isfile(linie_sc):
            linie_sc = None

        try:
            kas = kasowniki.GenerujKasowniki(
                wpol_temp, kat_wyj, nazwa='KAS_stare', linie_sc=linie_sc)
        except Exception:
            QgsMessageLog.logMessage(
                'Nie udało się wygenerować warstwy KAS_stare', 'Las-R',
                Qgis.Warning)
            return

        if kas.warstwa is not None:
            QgsProject.instance().addMapLayer(kas.warstwa)

    def _normalizuj_stara_struktura(self, wpol, wpol_data):
        obecne = [f.name() for f in wpol.fields()]
        if 'COUNTY' in obecne or 'COUNTY_CD' not in obecne:
            return
        QgsMessageLog.logMessage(
            'Wykryto starą strukturę warstwy WYDZ — remapowanie pól', 'Las-R', Qgis.Info)
        nowe = [
            QgsField(nowe_n, QVariant.String, '', dl)
            for _, nowe_n, dl in _MAPA_STARYCH_POL
            if nowe_n not in obecne
        ]
        wpol_data.addAttributes(nowe)
        wpol.updateFields()
        fnm = wpol_data.fieldNameMap()
        for feat in wpol.getFeatures():
            attrs = {}
            for stare_n, nowe_n, _ in _MAPA_STARYCH_POL:
                val = feat[stare_n]
                if isinstance(val, str):
                    val = val.strip()
                attrs[fnm[nowe_n]] = val
            wpol_data.changeAttributeValues({feat.id(): attrs})

    def _buduj_pol_uproszczona(self, src, wyj_sc):
        """Buduje uproszczoną warstwę poligonową (tylko pola z _KOLUMNY_POL)
        i zapisuje ją na dysk pod wyj_sc - zawsze jawnie w UTF-8 (nie
        zdajemy się na domyślne kodowanie processing/OGR, które na tym
        systemie to Windows-1250 i psuje polskie znaki w dalszych
        narzędziach). Zwraca warstwę pamięciową (do dalszego użycia, np.
        point on surface bez ponownego wczytywania z dysku)."""
        # geometrie moga byc MultiPolygon (brak wczesniejszego rozbicia na
        # singleparts) - warstwa pomocnicza musi to dopuszczac
        wyj = QgsVectorLayer('MultiPolygon?crs=epsg:2180', 'pol_uproszczona', 'memory')
        wyj_data = wyj.dataProvider()
        wyj_data.addAttributes(_KOLUMNY_POL)
        wyj.updateFields()

        nazwy = [f.name() for f in _KOLUMNY_POL]
        feats = []
        for feat in src.getFeatures():
            nf = QgsFeature(wyj.fields())
            nf.setGeometry(feat.geometry())
            for n in nazwy:
                nf[n] = feat[n]
            feats.append(nf)
        wyj_data.addFeatures(feats)

        QgsVectorFileWriter.writeAsVectorFormatV3(
            wyj, wyj_sc, QgsProject.instance().transformContext(),
            opis._opcje_zapisu())
        return wyj

    def _buduj_pkt(self, wpol_uproszczona, wyj_sc):
        """WYDZ_PKT_stare = point on surface WYDZ_POL_stare (ta sama
        uproszczona struktura pól, nie pełny zestaw z wpol_temp). Liczone
        w pamięci (bez pośredniego zapisu na dysk) i zapisywane jawnie w
        UTF-8, tym samym mechanizmem co _buduj_pol_uproszczona."""
        wynik = processing.run('native:pointonsurface', {
            'INPUT': wpol_uproszczona,
            'OUTPUT': 'memory:',
        })['OUTPUT']

        QgsVectorFileWriter.writeAsVectorFormatV3(
            wynik, wyj_sc, QgsProject.instance().transformContext(),
            opis._opcje_zapisu())

    def _dopisz_metadane(self, wydz, wydz_path, baza_sc):
        d = DopiszKody(self.iface)
        d.wydz = wydz
        d.wydz_path = wydz_path
        d.baza = Baza(baza_sc)

        if not d.pobierzBaze():
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Nie udało się pobrać danych z bazy', Qgis.Critical, 10)
            return None

        wpol = QgsVectorLayer('MultiPolygon?crs=epsg:2180', _TEMP, 'memory')
        wpol_data = wpol.dataProvider()
        wpol_data.addAttributes(wydz.fields().toList())
        wpol.updateFields()
        wpol_data.addFeatures(list(wydz.getFeatures()))

        self._normalizuj_stara_struktura(wpol, wpol_data)
        self._dodaj_pola(wpol, wpol_data, d.przestoje_flag)
        self._zapisz_atrybuty(wpol, wpol_data, d)
        return wpol

    def _dodaj_pola(self, wpol, wpol_data, przestoje_flag):
        obecne = [x.name() for x in wpol.fields()]
        pola = [
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
            QgsField('POW_WYDZ', QVariant.String, '', 10, 4),
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
        ]
        if przestoje_flag:
            pola.append(QgsField('PRZEST', QVariant.Double, '', 10, 4))
        pola.append(QgsField('INNE', QVariant.String, '', 70))

        nowe = QgsFields()
        for p in pola:
            if p.name() not in obecne:
                nowe.append(p)
        wpol_data.addAttributes(nowe)
        wpol.updateFields()

    def _zapisz_atrybuty(self, wpol, wpol_data, d):
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
                fnm['POW_WYDZ']: str(round(
                    d.isNone(d.sl[adr][2], typ='i'), 4)),
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
