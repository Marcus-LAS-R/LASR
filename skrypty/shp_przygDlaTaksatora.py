import glob
import os
import re
import shutil

import openpyxl
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QListWidgetItem, QMessageBox
from qgis.core import Qgis, QgsMessageLog, QgsProject

from .baza_wrapper import Baza
from .ui.ui_przygDlaTaksatora import Ui_Dialog

_WARSTWY_SHP = ['LS', 'DZKAT', 'LZ_potencjalne', 'OBR', '99']
_WARSTWY_DOTAKS = ['DOTAKS_nowe', 'DOTAKS_rb_nielas', 'DOTAKS_sprawdzenie']
_WARSTWY_STARE = ['WYDZ_POL_stare']
_ROZSZERZENIA = ['.shp', '.dbf', '.shx', '.prj', '.cpg', '.qpj', '.qml']

_SQL_UZYTKI = (
    "SELECT * FROM "
    "[suma użytków LS w poszczególnych obrębach geodezyjnych]"
)

_SQL_GMINA = """
SELECT DISTINCT F_MUNICIPALITY.MUNICIPALITY_NAME
FROM F_COMMUNITY
INNER JOIN F_MUNICIPALITY
ON F_COMMUNITY.MUNICIPALITY_CD = F_MUNICIPALITY.MUNICIPALITY_CD
AND F_COMMUNITY.DISTRICT_CD = F_MUNICIPALITY.DISTRICT_CD
AND F_COMMUNITY.COUNTY_CD = F_MUNICIPALITY.COUNTY_CD
"""

_SQL_POWIAT = """
SELECT DISTINCT F_DISTRICT.DISTRICT_NAME
FROM F_COMMUNITY
INNER JOIN F_DISTRICT
ON F_COMMUNITY.DISTRICT_CD = F_DISTRICT.DISTRICT_CD
AND F_COMMUNITY.COUNTY_CD = F_DISTRICT.COUNTY_CD
"""

_ZASTAPIENIA = str.maketrans(
    'ąćęłńóśźżĄĆĘŁŃÓŚŹŻ',
    'acelnoszzACELNOSZZ',
)

_H_SINGLE = 210
_H_BATCH = 390
_Y_BTN_SINGLE = 168
_Y_BTN_BATCH = 348


def _normalizuj_nazwe(nazwa):
    nazwa = re.sub(r'\bobszar\s+wiejski\b', 'OW', nazwa, flags=re.IGNORECASE)
    nazwa = re.sub(r'\bob\.?\s*wiej\.?\b', 'OW', nazwa, flags=re.IGNORECASE)
    return nazwa.strip().translate(_ZASTAPIENIA).replace(' ', '_')


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._ostatnia_baza = ''
        self._nazwa = ''

        self._single_widgets = [
            self.ui.label_folder, self.ui.lineEdit_folder, self.ui.pushButton_folder,
            self.ui.label_baza, self.ui.lineEdit_baza, self.ui.pushButton_baza,
            self.ui.label_wyj_opis, self.ui.label_wyj,
        ]
        self._batch_widgets = [
            self.ui.label_powiat, self.ui.lineEdit_powiat, self.ui.pushButton_powiat,
            self.ui.listWidget_gminy,
        ]

        self.ui.checkBox_wsadowo.toggled.connect(self._przelacz_tryb)
        self.ui.pushButton_folder.clicked.connect(self._wybierz_folder)
        self.ui.pushButton_baza.clicked.connect(self._wybierz_baze)
        self.ui.pushButton_powiat.clicked.connect(self._wybierz_powiat)
        self.ui.lineEdit_folder.textChanged.connect(self._na_zmiane_folderu)
        self.ui.lineEdit_baza.textChanged.connect(self._aktualizuj)
        self.ui.lineEdit_powiat.textChanged.connect(self._na_zmiane_powiatu)
        self.ui.listWidget_gminy.itemChanged.connect(self._aktualizuj)

        wykryty = self._wykryj_folder_proj()
        if wykryty:
            self.ui.lineEdit_folder.setText(wykryty)

    # ------------------------------------------------------------------
    # tryb przełącznik
    # ------------------------------------------------------------------

    def _przelacz_tryb(self, wsadowo):
        for w in self._single_widgets:
            w.setVisible(not wsadowo)
        for w in self._batch_widgets:
            w.setVisible(wsadowo)
        h = _H_BATCH if wsadowo else _H_SINGLE
        y_btn = _Y_BTN_BATCH if wsadowo else _Y_BTN_SINGLE
        self.setFixedSize(520, h)
        self.ui.pushButton_ok.move(100, y_btn)
        self.ui.pushButton_cancel.move(360, y_btn)
        if wsadowo and not self.ui.lineEdit_powiat.text().strip():
            wykryty = self._wykryj_folder_powiat()
            if wykryty:
                self.ui.lineEdit_powiat.setText(wykryty)
        self._aktualizuj()

    # ------------------------------------------------------------------
    # auto-wykrywanie
    # ------------------------------------------------------------------

    def _folder_startowy(self):
        for lyr in QgsProject.instance().mapLayers().values():
            try:
                sc = lyr.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    return os.path.dirname(sc)
            except Exception:
                pass
        return ''

    def _wykryj_folder_proj(self):
        for lyr in QgsProject.instance().mapLayers().values():
            try:
                sc = lyr.dataProvider().dataSourceUri().split('|')[0]
                if not sc or not os.path.isfile(sc):
                    continue
                kat = os.path.dirname(sc)
                for kandydat in [kat, os.path.dirname(kat)]:
                    if os.path.isfile(os.path.join(kandydat, 'SHP', 'LS.shp')):
                        return kandydat
            except Exception:
                pass
        return ''

    def _wykryj_folder_powiat(self):
        for lyr in QgsProject.instance().mapLayers().values():
            try:
                sc = lyr.dataProvider().dataSourceUri().split('|')[0]
                if not sc or not os.path.isfile(sc):
                    continue
                # warstwy są w SHP/ → 2 poziomy wyżej = powiat
                kat_shp = os.path.dirname(sc)
                powiat = os.path.dirname(os.path.dirname(kat_shp))
                if os.path.isdir(powiat):
                    return powiat
            except Exception:
                pass
        return ''

    def _wykryj_baze(self, folder):
        pliki = glob.glob(os.path.join(folder, '*.mdb'))
        pliki += glob.glob(os.path.join(folder, '*.sqlite'))
        if not pliki:
            return ''
        return max(pliki, key=os.path.getmtime)

    def _pobierz_nazwe(self, baza_sc):
        try:
            baza = Baza(baza_sc)
            if not baza.polacz():
                return ''
            wyniki = baza.pobierz(_SQL_GMINA)
            baza.zamknij()
            if not wyniki:
                return ''
            return '_i_'.join(_normalizuj_nazwe(w[0]) for w in wyniki if w[0])
        except Exception:
            return ''

    # ------------------------------------------------------------------
    # single mode
    # ------------------------------------------------------------------

    def _na_zmiane_folderu(self, folder):
        if folder and os.path.isdir(folder):
            baza = self._wykryj_baze(folder)
            if baza:
                self.ui.lineEdit_baza.setText(baza)
        self._aktualizuj()

    def _wybierz_folder(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder projektu', self._folder_startowy())
        if sc:
            self.ui.lineEdit_folder.setText(sc)

    def _wybierz_baze(self):
        folder = self.ui.lineEdit_folder.text().strip()
        start = folder if folder and os.path.isdir(folder) \
            else self._folder_startowy()
        sc = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę taksatora', start,
            'Access MDB (*.mdb);;SQLite (*.sqlite)')[0]
        if sc:
            self.ui.lineEdit_baza.setText(sc)

    # ------------------------------------------------------------------
    # batch mode
    # ------------------------------------------------------------------

    def _wybierz_powiat(self):
        sc = QFileDialog.getExistingDirectory(
            self, 'Wskaż folder powiatu', self._folder_startowy())
        if sc:
            self.ui.lineEdit_powiat.setText(sc)

    def _na_zmiane_powiatu(self, folder):
        self.ui.listWidget_gminy.clear()
        if not folder or not os.path.isdir(folder):
            self._aktualizuj()
            return
        for gmina in self._skanuj_powiat(folder):
            nazwa_gminy, folder_proj, baza_sc = gmina
            item = QListWidgetItem(
                f'{nazwa_gminy}  →  {os.path.basename(baza_sc)}')
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setCheckState(Qt.Checked)
            item.setData(Qt.UserRole, (folder_proj, baza_sc))
            self.ui.listWidget_gminy.addItem(item)
        self._aktualizuj()

    def _skanuj_powiat(self, folder_powiat):
        wyniki = []
        try:
            nazwy = sorted(os.listdir(folder_powiat))
        except OSError:
            return wyniki
        for nazwa in nazwy:
            subfolder = os.path.join(folder_powiat, nazwa)
            if not os.path.isdir(subfolder):
                continue
            if not os.path.isfile(os.path.join(subfolder, 'SHP', 'LS.shp')):
                continue
            baza = self._wykryj_baze(subfolder)
            if not baza:
                continue
            wyniki.append((nazwa, subfolder, baza))
        return wyniki

    # ------------------------------------------------------------------
    # wspólne
    # ------------------------------------------------------------------

    def _aktualizuj(self):
        if self.ui.checkBox_wsadowo.isChecked():
            self.ui.pushButton_ok.setEnabled(self._ile_zaznaczonych() > 0)
        else:
            baza_sc = self.ui.lineEdit_baza.text().strip()
            if baza_sc and os.path.isfile(baza_sc):
                if baza_sc != self._ostatnia_baza:
                    self._nazwa = self._pobierz_nazwe(baza_sc)
                    self._ostatnia_baza = baza_sc
                nazwa_folderu = (self._nazwa + '_SHP_w_teren'
                                 if self._nazwa else 'SHP_w_teren')
                self.ui.label_wyj.setText(
                    os.path.join(os.path.dirname(baza_sc), nazwa_folderu))
            else:
                self.ui.label_wyj.setText('')
            ok = (bool(self.ui.lineEdit_folder.text().strip()) and bool(baza_sc))
            self.ui.pushButton_ok.setEnabled(ok)

    def _ile_zaznaczonych(self):
        return sum(
            1 for i in range(self.ui.listWidget_gminy.count())
            if self.ui.listWidget_gminy.item(i).checkState() == Qt.Checked
        )

    # ------------------------------------------------------------------
    # gettery
    # ------------------------------------------------------------------

    def is_wsadowy(self):
        return self.ui.checkBox_wsadowo.isChecked()

    def folder_proj(self):
        return self.ui.lineEdit_folder.text().strip()

    def baza_sc(self):
        return self.ui.lineEdit_baza.text().strip()

    def folder_wyj(self):
        return self.ui.label_wyj.text()

    def nazwa(self):
        return self._nazwa

    def folder_powiat(self):
        return self.ui.lineEdit_powiat.text().strip()

    def wybrane_gminy(self):
        wynik = []
        for i in range(self.ui.listWidget_gminy.count()):
            item = self.ui.listWidget_gminy.item(i)
            if item.checkState() == Qt.Checked:
                wynik.append(item.data(Qt.UserRole))
        return wynik


class PrzygotujDlaTaksatora:
    def __init__(self, iface):
        self.iface = iface

    def uruchom(self):
        dlg = _Dialog(self.iface)
        if dlg.exec_() != QDialog.Accepted:
            return

        if dlg.is_wsadowy():
            self._uruchom_wsadowo(dlg.wybrane_gminy(), dlg.folder_powiat())
        else:
            self._uruchom_pojedynczo(
                dlg.folder_proj(), dlg.baza_sc(),
                dlg.folder_wyj(), dlg.nazwa())

    def _uruchom_pojedynczo(self, folder_proj, baza_sc, kat_wyj, nazwa):
        QgsMessageLog.logMessage('--- PRZYGOTUJ DLA TAKSATORA ---', 'Las-R', Qgis.Info)
        kat_shp_wyj = os.path.join(kat_wyj, 'SHP')
        os.makedirs(kat_shp_wyj, exist_ok=True)
        skopiowane = self._kopiuj_warstwy(folder_proj, kat_shp_wyj)
        self._eksportuj_uzytki(baza_sc, kat_wyj, nazwa)
        QgsMessageLog.logMessage(
            f'Skopiowano {skopiowane} warstw(y) do {kat_shp_wyj}', 'Las-R', Qgis.Info)
        QgsMessageLog.logMessage('--- KONIEC ---', 'Las-R', Qgis.Info)
        self.iface.messageBar().pushMessage(
            'OK',
            f'Warstwy i tabela użytków zapisane w {os.path.basename(kat_wyj)}',
            Qgis.Success, 10)

    def _uruchom_wsadowo(self, gminy, folder_powiat):
        QgsMessageLog.logMessage(
            f'--- PRZYGOTUJ DLA TAKSATORA (wsadowo, {len(gminy)} jednostek) ---',
            'Las-R', Qgis.Info)

        # tryb nazewnictwa: community (obręby) lub municipality (gminy)
        tryb_community = all(
            self._ile_rekordow_community(baza_sc) == 1
            for _, baza_sc in gminy
        )
        QgsMessageLog.logMessage(
            f'Tryb nazewnictwa: {"COMMUNITY" if tryb_community else "MUNICIPALITY"}',
            'Las-R', Qgis.Info)

        # pobierz nazwy dla każdej jednostki
        nazwy = {}
        for folder_proj, baza_sc in gminy:
            nazwy[baza_sc] = (self._pobierz_nazwe_community(baza_sc)
                              if tryb_community
                              else self._pobierz_nazwe_z_bazy(baza_sc))

        # sprawdź duplikaty tylko w trybie municipality
        if not tryb_community:
            lista_nazw = list(nazwy.values())
            duplikaty = sorted({n for n in lista_nazw if lista_nazw.count(n) > 1})
            if duplikaty:
                msg = QMessageBox(self.iface.mainWindow())
                msg.setIcon(QMessageBox.Warning)
                msg.setWindowTitle('Uwaga — duplikaty nazw')
                msg.setText(
                    'Następujące nazwy gmin się powtarzają:\n'
                    + ', '.join(duplikaty)
                    + '\n\nDane zostaną nadpisane. Kontynuować?'
                )
                msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                msg.setDefaultButton(QMessageBox.No)
                if msg.exec_() != QMessageBox.Yes:
                    return

        nazwa_powiatu = self._pobierz_nazwe_powiatu(gminy[0][1])
        nazwa_kat_powiat = (nazwa_powiatu + '_SHP_w_teren'
                            if nazwa_powiatu else 'SHP_w_teren')
        kat_powiat_wyj = os.path.join(folder_powiat, nazwa_kat_powiat)
        os.makedirs(kat_powiat_wyj, exist_ok=True)

        bledy = []
        for folder_proj, baza_sc in gminy:
            try:
                nazwa = nazwy[baza_sc]
                nazwa_folderu = (nazwa + '_SHP_w_teren') if nazwa else 'SHP_w_teren'
                kat_wyj = os.path.join(kat_powiat_wyj, nazwa_folderu)
                kat_shp_wyj = os.path.join(kat_wyj, 'SHP')
                os.makedirs(kat_shp_wyj, exist_ok=True)
                self._kopiuj_warstwy(folder_proj, kat_shp_wyj)
                self._eksportuj_uzytki(baza_sc, kat_wyj, nazwa)
                QgsMessageLog.logMessage(
                    f'OK: {os.path.basename(folder_proj)}', 'Las-R', Qgis.Info)
            except Exception as e:
                bledy.append(os.path.basename(folder_proj))
                QgsMessageLog.logMessage(
                    f'BŁĄD ({os.path.basename(folder_proj)}): {e}',
                    'Las-R', Qgis.Critical)

        QgsMessageLog.logMessage('--- KONIEC ---', 'Las-R', Qgis.Info)
        if bledy:
            self.iface.messageBar().pushMessage(
                'Częściowy błąd',
                f'Błędy w: {", ".join(bledy)}. Reszta OK.',
                Qgis.Warning, 15)
        else:
            self.iface.messageBar().pushMessage(
                'OK',
                f'Przetworzono {len(gminy)} jednostek → {nazwa_kat_powiat}',
                Qgis.Success, 10)

    def _pobierz_nazwe_powiatu(self, baza_sc):
        try:
            baza = Baza(baza_sc)
            if not baza.polacz():
                return ''
            wyniki = baza.pobierz(_SQL_POWIAT)
            baza.zamknij()
            if not wyniki:
                return ''
            return '_i_'.join(_normalizuj_nazwe(w[0]) for w in wyniki if w[0])
        except Exception:
            return ''

    def _ile_rekordow_community(self, baza_sc):
        try:
            baza = Baza(baza_sc)
            if not baza.polacz():
                return 0
            wynik = baza.pobierz("SELECT COUNT(*) FROM F_COMMUNITY")
            baza.zamknij()
            return wynik[0][0] if wynik else 0
        except Exception:
            return 0

    def _pobierz_nazwe_community(self, baza_sc):
        try:
            baza = Baza(baza_sc)
            if not baza.polacz():
                return ''
            wyniki = baza.pobierz("SELECT COMMUNITY_NAME FROM F_COMMUNITY")
            baza.zamknij()
            if not wyniki:
                return ''
            return '_i_'.join(_normalizuj_nazwe(w[0]) for w in wyniki if w[0])
        except Exception:
            return ''

    def _pobierz_nazwe_z_bazy(self, baza_sc):
        try:
            baza = Baza(baza_sc)
            if not baza.polacz():
                return ''
            wyniki = baza.pobierz(_SQL_GMINA)
            baza.zamknij()
            if not wyniki:
                return ''
            return '_i_'.join(_normalizuj_nazwe(w[0]) for w in wyniki if w[0])
        except Exception:
            return ''

    def _kopiuj_warstwy(self, folder_proj, kat_shp_wyj):
        skopiowane = 0
        kat_shp = os.path.join(folder_proj, 'SHP')
        for nazwa in _WARSTWY_SHP:
            if self._kopiuj_shp(kat_shp, nazwa, kat_shp_wyj):
                skopiowane += 1
        kat_dotaks = os.path.join(folder_proj, 'SHP_dotaks')
        if os.path.isdir(kat_dotaks):
            for nazwa in _WARSTWY_DOTAKS:
                if self._kopiuj_shp(kat_dotaks, nazwa, kat_shp_wyj):
                    skopiowane += 1
        kat_stare = os.path.join(folder_proj, 'SHP_stare')
        if os.path.isdir(kat_stare):
            for nazwa in _WARSTWY_STARE:
                if self._kopiuj_shp(kat_stare, nazwa, kat_shp_wyj):
                    skopiowane += 1
        return skopiowane

    def _kopiuj_shp(self, kat_zrodlo, nazwa, kat_wyj):
        shp_zrodlo = os.path.join(kat_zrodlo, nazwa + '.shp')
        if not os.path.isfile(shp_zrodlo):
            QgsMessageLog.logMessage(
                f'Brak pliku: {shp_zrodlo}', 'Las-R', Qgis.Warning)
            return False
        for ext in _ROZSZERZENIA:
            src = os.path.join(kat_zrodlo, nazwa + ext)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(kat_wyj, nazwa + ext))
        return True

    def _eksportuj_uzytki(self, baza_sc, kat_wyj, nazwa):
        baza = Baza(baza_sc)
        if not baza.polacz():
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Nie można połączyć się z bazą danych', Qgis.Critical, 10)
            return
        try:
            baza.cur.execute(_SQL_UZYTKI)
            naglowki = [col[0] for col in baza.cur.description]
            wiersze = baza.cur.fetchall()
        finally:
            baza.zamknij()
        if not wiersze:
            QgsMessageLog.logMessage(
                'Brak danych z kwerendy użytków', 'Las-R', Qgis.Warning)
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Użytki wg obrębów'
        ws.append(naglowki)
        for wiersz in wiersze:
            ws.append(list(wiersz))
        nazwa_pliku = (nazwa + '_zestawienie_powierzchni.xlsx'
                       if nazwa else 'zestawienie_powierzchni.xlsx')
        wb.save(os.path.join(kat_wyj, nazwa_pliku))
