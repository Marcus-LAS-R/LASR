import os
import json

import requests
import processing
import openpyxl

from urllib.parse import quote

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QFileDialog, QProgressDialog, QApplication
from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsFeature,
    QgsProject,
)

from .ui.ui_pobierz_BDL import Ui_Dialog

# Zapytanie o geometrie i podstawowe dane wydzielen w zadanej obwiedni.
# inSR=2180 (obwiednia podawana w ukladzie warstwy wejsciowej), outSR=102100
# (Web Mercator) - zgodnie ze sprawdzonym oryginalnym skryptem; wynikowe
# geometrie sa przeliczane do EPSG:2180 lokalnie w _scal_do_warstwy, zeby nie
# zgadywac czy serwer akceptuje inny outSR.
_URL_GEOM = (
    'https://mapserver.bdl.lasy.gov.pl/ArcGIS/rest/services/'
    'Mapa_podstawowa_BDL/MapServer/21/query?f=json&returnGeometry=true'
    '&geometry=%7Bxmin%3A{}%2Cymin%3A{}%2Cxmax%3A{}%2Cymax%3A{}%7D'
    '&geometryType=esriGeometryEnvelope&inSR=2180'
    '&outFields=arodes_int_num%2Cadress_forest%2Ca_year%2Cowner_cat_name'
    '&outSR=102100'
)
_HEADERS_GEOM = {
    'Accept': '*/*',
    'Accept-Language': 'pl-PL,pl;q=0.7',
    'Connection': 'keep-alive',
    'Origin': 'https://www.bdl.lasy.gov.pl',
    'Referer': 'https://www.bdl.lasy.gov.pl/',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-site',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# Zapytanie o pelny opis taksacyjny pojedynczego wydzielenia.
_URL_OPIS = (
    'https://www.bdl.lasy.gov.pl/portal/BULiGL.BDL.Reports/Map/'
    'StandDescriptionData?arodesIntNum={}&aYear={}&adressForest={}'
    '&jointOwnership=false&label=owner_cat_name'
)
_HEADERS_OPIS = {
    'Accept': '*/*',
    'Accept-Language': 'pl-PL,pl;q=0.7',
    'Connection': 'keep-alive',
    'Cookie': 'conditionsAccepted=true; tutorial=true; standDescriptionInfo=true',
    'Referer': 'https://www.bdl.lasy.gov.pl/portal/mapy',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-GPC': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Not.A/Brand";v="8", "Chromium";v="114"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# Kategorie opisu taksacyjnego zwracane przez _URL_OPIS - kazda zapisywana
# do osobnego pliku XLSX o tej samej nazwie (do importu do bazy).
_KATEGORIE = [
    'headerLNP', 'generalData', 'generalData2', 'layer', 'layerSpecies',
    'arodCues',
]


def _generuj_siatke(lyr, rozmiar):
    """ Generuje siatke prostokatow (native:creategrid) pokrywajaca
    obwiednie warstwy `lyr`, po czym zwraca tylko obwiednie (QgsRectangle)
    tych oczek, ktore faktycznie przecinaja sie z geometria warstwy -
    odpowiednik recznych krokow 2-3 z instrukcji (wygeneruj siatke, usun
    poligony nieprzecinajace sie z AOI). """
    extent = lyr.extent()
    extent_str = '{},{},{},{} [{}]'.format(
        extent.xMinimum(), extent.xMaximum(),
        extent.yMinimum(), extent.yMaximum(),
        lyr.crs().authid())

    wynik = processing.run("native:creategrid", {
        'TYPE': 2,  # Rectangle (Polygon)
        'EXTENT': extent_str,
        'HSPACING': rozmiar,
        'VSPACING': rozmiar,
        'HOVERLAY': 0,
        'VOVERLAY': 0,
        'CRS': lyr.crs(),
        'OUTPUT': 'memory:',
    })
    siatka = wynik['OUTPUT']

    aoi_geoms = [f.geometry() for f in lyr.getFeatures()]
    if not aoi_geoms:
        return []
    aoi = QgsGeometry.unaryUnion(aoi_geoms)

    return [
        f.geometry().boundingBox()
        for f in siatka.getFeatures()
        if f.geometry().intersects(aoi)
    ]


def _pobierz_geometrie(komorki, tempkat, postep):
    """ Sciaga geometrie+podstawowe dane dla kazdego oczka siatki (jeden
    request na oczko, zapis surowej odpowiedzi do temp/{i}.geojson - jak w
    oryginalnym skrypcie). Zwraca (lista_plikow, lista_indeksow_ucietych,
    czy_kontynuowac) - uciete to oczka gdzie serwer zwrocil
    exceededTransferLimit (ponad 1000 wydzielen w oczku). """
    pliki = []
    uciete = []
    for i, bbox in enumerate(komorki):
        if postep is not None and not postep(i, len(komorki), 'geometrie'):
            return pliki, uciete, False

        url = _URL_GEOM.format(
            bbox.xMinimum(), bbox.yMinimum(),
            bbox.xMaximum(), bbox.yMaximum())
        try:
            res = requests.get(url, headers=_HEADERS_GEOM, timeout=30)
        except requests.RequestException as e:
            QgsMessageLog.logMessage(
                'Błąd sieci przy pobieraniu oczka ' + str(i) + ': ' + str(e),
                'Las-R', Qgis.Warning)
            break
        if res.status_code != 200:
            QgsMessageLog.logMessage(
                'Oczko ' + str(i) + ': serwer zwrócił HTTP ' +
                str(res.status_code), 'Las-R', Qgis.Warning)
            break

        sciezka = os.path.join(tempkat, str(i) + '.geojson')
        with open(sciezka, 'w', encoding='utf-8') as f:
            f.write(res.text)
        pliki.append(sciezka)

        try:
            if json.loads(res.text).get('exceededTransferLimit'):
                uciete.append(i)
        except ValueError:
            pass

    return pliki, uciete, True


def _scal_do_warstwy(pliki):
    """ Wczytuje kazdy plik geojson (format Esri JSON - obslugiwany przez
    sterownik OGR ESRIJSON), odrzuca duplikaty po arodes_int_num i laczy
    wszystko w jedna warstwe pamieciowa w EPSG:2180 (przeliczajac geometrie
    z Web Mercator, w ktorym odpowiada serwer). Zwraca None, jesli nic nie
    udalo sie wczytac. """
    transformacja = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem('EPSG:3857'),
        QgsCoordinateReferenceSystem('EPSG:2180'),
        QgsProject.instance())

    polaczona = None
    widziane = set()
    for sciezka in pliki:
        lyr = QgsVectorLayer(sciezka, 'komorka', 'ogr')
        if not lyr.isValid():
            continue
        if polaczona is None:
            polaczona = QgsVectorLayer(
                'Polygon?crs=EPSG:2180', 'wydzielenia_bdl', 'memory')
            polaczona.dataProvider().addAttributes(lyr.fields())
            polaczona.updateFields()

        for f in lyr.getFeatures():
            aid = f['arodes_int_num']
            if aid in widziane:
                continue
            widziane.add(aid)

            geom = QgsGeometry(f.geometry())
            geom.transform(transformacja)
            nowa = QgsFeature(polaczona.fields())
            nowa.setGeometry(geom)
            nowa.setAttributes(f.attributes())
            polaczona.dataProvider().addFeature(nowa)

    if polaczona is not None:
        polaczona.updateExtents()
    return polaczona


def _pobierz_opisy(polaczona, postep):
    """ Dla kazdego wydzielenia w polaczonej warstwie sciaga pelny opis
    taksacyjny i rozbija go na kategorie (_KATEGORIE) - kazdy wiersz
    dostaje 'aint' (arodes_int_num) i 'kolej' (kolejnosc w ramach
    wydzielenia), tak jak w oryginalnym skrypcie. Zwraca slownik
    {kategoria: [wiersze]}. """
    wyniki = {k: [] for k in _KATEGORIE}
    if polaczona is None:
        return wyniki

    cechy = list(polaczona.getFeatures())
    for i, f in enumerate(cechy):
        if postep is not None and not postep(i, len(cechy), 'opisy'):
            break

        aid = f['arodes_int_num']
        url = _URL_OPIS.format(aid, f['a_year'], quote(str(f['adress_forest'])))
        try:
            res = requests.get(url, headers=_HEADERS_OPIS, timeout=30)
        except requests.RequestException as e:
            QgsMessageLog.logMessage(
                'Błąd sieci przy pobieraniu opisu ' + str(aid) + ': ' +
                str(e), 'Las-R', Qgis.Warning)
            break
        if res.status_code != 200:
            QgsMessageLog.logMessage(
                'Opis ' + str(aid) + ': serwer zwrócił HTTP ' +
                str(res.status_code), 'Las-R', Qgis.Warning)
            break

        try:
            val = json.loads(res.text)
        except ValueError:
            continue

        for kategoria in _KATEGORIE:
            if kategoria not in val:
                continue
            for kolej, wiersz in enumerate(val[kategoria]):
                wiersz = dict(wiersz)
                wiersz['aint'] = aid
                wiersz['kolej'] = kolej
                wyniki[kategoria].append(wiersz)

    return wyniki


def _zapisz_xlsx(wyniki, folder):
    for kategoria, wiersze in wyniki.items():
        if not wiersze:
            continue
        nazwy_pol = []
        for wiersz in wiersze:
            for klucz in wiersz.keys():
                if klucz not in nazwy_pol:
                    nazwy_pol.append(klucz)

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = kategoria[:31]  # limit arkusza Excela to 31 znakow
        ws.append(nazwy_pol)
        for wiersz in wiersze:
            ws.append([wiersz.get(k, '') for k in nazwy_pol])
        wb.save(os.path.join(folder, kategoria + '.xlsx'))


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        aktywna = self.iface.activeLayer()
        if aktywna is not None:
            try:
                sc = aktywna.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    self.ui.lineEdit_warstwa.setText(sc)
            except Exception:
                pass

        self.ui.pushButton_warstwa.clicked.connect(self._wybierz_warstwe)
        self.ui.pushButton_folder.clicked.connect(self._wybierz_folder)
        self.ui.lineEdit_warstwa.textChanged.connect(self._na_zmiane_warstwy)
        self.ui.lineEdit_folder.textChanged.connect(self._aktualizuj)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

        self._na_zmiane_warstwy()
        self._aktualizuj()

    def _folder_startowy(self):
        sc = self.ui.lineEdit_warstwa.text().strip()
        if sc and os.path.isfile(sc):
            return os.path.dirname(sc)
        return ''

    def _wybierz_warstwe(self):
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż warstwę zasięgu (OBR/GMIN)',
            self._folder_startowy(),
            'Shapefile (*.shp)',
        )[0]
        if sc:
            self.ui.lineEdit_warstwa.setText(sc)

    def _wybierz_folder(self):
        sc = QFileDialog.getExistingDirectory(
            self,
            'Wskaż folder wyjściowy',
            self.ui.lineEdit_folder.text().strip() or self._folder_startowy(),
        )
        if sc:
            self.ui.lineEdit_folder.setText(sc)

    def _na_zmiane_warstwy(self):
        sc = self.ui.lineEdit_warstwa.text().strip()
        if sc and os.path.isfile(sc) and not self.ui.lineEdit_folder.text().strip():
            # domyslnie na poziomie bazy (o katalog wyzej od folderu SHP),
            # nie w samym folderze SHP - tak jak inne skrypty tego projektu
            # szukaja bazy (patrz baza_wrapper.znajdz_baze_do_wydz, poz=1)
            self.ui.lineEdit_folder.setText(os.path.normpath(
                os.path.join(os.path.dirname(sc), '..', 'Dane_BDL')))
        self._aktualizuj()

    def _aktualizuj(self):
        ok = bool(self.ui.lineEdit_warstwa.text().strip()) and \
            bool(self.ui.lineEdit_folder.text().strip())
        self.ui.pushButton_ok.setEnabled(ok)

    def warstwa_sc(self):
        return self.ui.lineEdit_warstwa.text().strip()

    def rozmiar(self):
        return self.ui.spinBox_rozmiar.value()

    def folder(self):
        return self.ui.lineEdit_folder.text().strip()


def uruchom(iface):
    """ Pokazuje dialog wyboru warstwy zasiegu (OBR/GMIN), rozmiaru oczka
    siatki i folderu wyjsciowego, po czym uruchamia PobierzBDL. """
    dlg = _Dialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False

    lyr = QgsVectorLayer(dlg.warstwa_sc(), 'zasieg_bdl', 'ogr')
    if not lyr.isValid():
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie można wczytać wskazanej warstwy',
            Qgis.Critical,
            10)
        return False

    return PobierzBDL(iface, lyr, rozmiar=dlg.rozmiar(), folder=dlg.folder())


def PobierzBDL(iface, lyr, rozmiar=2000, folder=None):  # noqa
    """ Sciaga z Banku Danych o Lasach (bdl.lasy.gov.pl) geometrie i opisy
    taksacyjne wydzielen przecinajacych sie z warstwa `lyr` (OBR lub GMIN,
    musi byc w EPSG:2180). Dzieli zasieg na siatke o boku `rozmiar` metrow
    (limit serwera to ok. 1000 wydzielen/oczko), sciaga kazde oczko osobno,
    laczy w jedna warstwe (bez duplikatow po arodes_int_num) i zapisuje do
    folderu wyjsciowego: SHP/wszystko_BDL.shp (EPSG:2180, UTF-8) + po
    jednym XLSX na kazda kategorie opisu (headerLNP, generalData,
    generalData2, layer, layerSpecies, arodCues) - gotowe do
    zaimportowania do bazy. """
    QgsMessageLog.logMessage(
        '------ ŚCIĄGNIJ DANE Z BDL --------- ',
        'Las-R',
        Qgis.Info
    )

    if not lyr.isValid():
        iface.messageBar().pushMessage(
            'BŁĄD', 'Brak poprawnej warstwy zasięgu', Qgis.Critical, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    if lyr.crs().authid() != 'EPSG:2180':
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Warstwa zasięgu musi być w układzie EPSG:2180 (jest: ' +
            lyr.crs().authid() + ')',
            Qgis.Critical,
            10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    if not folder:
        iface.messageBar().pushMessage(
            'BŁĄD', 'Nie wskazano folderu wyjściowego', Qgis.Critical, 10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    if not os.path.isdir(folder):
        os.makedirs(folder)
    tempkat = os.path.join(folder, 'temp')
    if not os.path.isdir(tempkat):
        os.makedirs(tempkat)

    komorki = _generuj_siatke(lyr, rozmiar)
    if not komorki:
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Siatka nie przecina się z warstwą zasięgu',
            Qgis.Critical,
            10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    progress = QProgressDialog(
        'Pobieranie geometrii z BDL...', 'Przerwij', 0, len(komorki),
        iface.mainWindow())
    progress.setWindowModality(Qt.WindowModal)
    progress.setMinimumDuration(0)
    progress.setValue(0)

    def _postep(i, n, etap):
        etykieta = 'Pobieranie geometrii z BDL...' if etap == 'geometrie' \
            else 'Pobieranie opisów z BDL...'
        progress.setLabelText(etykieta + ' (' + str(i + 1) + '/' + str(n) + ')')
        progress.setMaximum(n)
        progress.setValue(i)
        QApplication.processEvents()
        return not progress.wasCanceled()

    pliki, uciete, kontynuowac = _pobierz_geometrie(komorki, tempkat, _postep)

    if uciete:
        QgsMessageLog.logMessage(
            'Oczka siatki z uciętymi wynikami (ponad limit serwera - '
            'zmniejsz rozmiar oczka i uruchom ponownie): ' +
            ', '.join(str(i) for i in uciete),
            'Las-R',
            Qgis.Warning
        )

    polaczona = _scal_do_warstwy(pliki)
    if polaczona is None or polaczona.featureCount() == 0:
        progress.close()
        iface.messageBar().pushMessage(
            'BRAK DANYCH',
            'Nie udało się pobrać żadnych wydzieleń z BDL',
            Qgis.Warning,
            10)
        QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
        return False

    kat_shp = os.path.join(folder, 'SHP')
    if not os.path.isdir(kat_shp):
        os.makedirs(kat_shp)
    QgsVectorFileWriter.writeAsVectorFormat(
        polaczona,
        os.path.join(kat_shp, 'wszystko_BDL.shp'),
        'UTF-8',
        QgsCoordinateReferenceSystem('EPSG:2180'),
        'ESRI Shapefile')

    if not kontynuowac:
        progress.close()
        iface.messageBar().pushMessage(
            'PRZERWANO',
            'Pobrano geometrie dla ' + str(polaczona.featureCount()) +
            ' wydzieleń przed przerwaniem - opisy (XLSX) NIE zostały '
            'pobrane',
            Qgis.Warning,
            10)
        QgsMessageLog.logMessage(
            '------ KONIEC (przerwano) -------- \n', 'Las-R', Qgis.Info)
        return True

    wyniki = _pobierz_opisy(polaczona, _postep)
    _zapisz_xlsx(wyniki, folder)
    progress.close()

    iface.messageBar().pushMessage(
        'OK',
        'Pobrano ' + str(polaczona.featureCount()) + ' wydzieleń z BDL do ' +
        folder,
        Qgis.Success,
        10)
    QgsMessageLog.logMessage('------ KONIEC -------- \n', 'Las-R', Qgis.Info)
    return True
