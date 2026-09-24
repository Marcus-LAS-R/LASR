""" Usuwa z warstwy adr_upul (karty adresowe z pomiarow terenowych) punkty
lezace geometrycznie poza warstwa OBR (obreby opracowania). Obie warstwy
brane z TOC po nazwie; przy wiecej niz jednej pasujacej uzytkownik
wybiera wlasciwa. Porownanie odbywa sie zawsze w PUWG 1992 (EPSG:2180) -
kazda warstwa przeliczana ze swojego wlasnego ukladu, sama warstwa
adr_upul nie jest reprojektowana (kasowane sa tylko punkty). Punkt na
granicy obrebu zostaje. """

from qgis.core import (
    Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsGeometry,
    QgsProject, QgsSpatialIndex, QgsVectorDataProvider, QgsVectorLayer,
    QgsWkbTypes,
)
from PyQt5.QtWidgets import QMessageBox

from .funkcje import wybierz_warstwe_z_kandydatow
from . import kopie_manipulacyjne

_CRS_92 = QgsCoordinateReferenceSystem('EPSG:2180')


def _geometrie_w_92(lyr):
    """ {fid: QgsGeometry w EPSG:2180} dla wszystkich obiektow warstwy
    (pomija puste geometrie) """
    tr = QgsCoordinateTransform(lyr.crs(), _CRS_92, QgsProject.instance())
    wyn = {}
    for f in lyr.getFeatures():
        g = f.geometry()
        if g is None or g.isEmpty():
            continue
        g = QgsGeometry(g)  # kopia - transform() modyfikuje w miejscu
        g.transform(tr)
        wyn[f.id()] = g
    return wyn


def usun_nadmiarowe_adr_upul(iface):
    bar = iface.messageBar()
    lyrs = list(QgsProject.instance().mapLayers().values())

    adr = wybierz_warstwe_z_kandydatow(
        iface, [x for x in lyrs if x.name().upper() == 'ADR_UPUL'],
        'adr_upul')
    if adr is None:
        bar.pushMessage(
            'BŁĄD', 'Nie wybrano warstwy adr_upul (brak w TOC?)',
            Qgis.Critical, 10)
        return False

    obr = wybierz_warstwe_z_kandydatow(
        iface, [x for x in lyrs if x.name().upper() == 'OBR'], 'OBR')
    if obr is None:
        bar.pushMessage(
            'BŁĄD', 'Nie wybrano warstwy OBR (brak w TOC?)',
            Qgis.Critical, 10)
        return False

    # --- walidacja wejscia ---------------------------------------------
    for lyr in (adr, obr):
        if not isinstance(lyr, QgsVectorLayer) or not lyr.isValid():
            bar.pushMessage(
                'BŁĄD', f'Warstwa {lyr.name()} jest niepoprawna',
                Qgis.Critical, 10)
            return False
        if not lyr.crs().isValid():
            bar.pushMessage(
                'BŁĄD',
                f'Warstwa {lyr.name()} nie ma zdefiniowanego układu '
                'współrzędnych - nie mogę przeliczyć do PUWG 1992',
                Qgis.Critical, 10)
            return False

    if adr.geometryType() != QgsWkbTypes.PointGeometry:
        bar.pushMessage(
            'BŁĄD', 'Warstwa adr_upul musi być warstwą punktową',
            Qgis.Critical, 10)
        return False
    if obr.geometryType() != QgsWkbTypes.PolygonGeometry:
        bar.pushMessage(
            'BŁĄD', 'Warstwa OBR musi być warstwą poligonową',
            Qgis.Critical, 10)
        return False
    if adr.isEditable():
        bar.pushMessage(
            'BŁĄD',
            'Warstwa adr_upul jest w trybie edycji - zapisz lub porzuć '
            'zmiany i uruchom ponownie',
            Qgis.Critical, 10)
        return False
    if not (adr.dataProvider().capabilities() &
            QgsVectorDataProvider.DeleteFeatures):
        bar.pushMessage(
            'BŁĄD', 'Warstwa adr_upul nie pozwala na usuwanie obiektów',
            Qgis.Critical, 10)
        return False

    # --- wyszukanie punktow poza OBR (w EPSG:2180) ------------------------
    try:
        g_obr = _geometrie_w_92(obr)
        g_adr = _geometrie_w_92(adr)
    except Exception as e:
        bar.pushMessage(
            'BŁĄD', f'Nie udało się przeliczyć geometrii do PUWG 1992: {e}',
            Qgis.Critical, 10)
        return False

    if not g_obr:
        bar.pushMessage(
            'BŁĄD', 'Warstwa OBR nie zawiera żadnych poligonów',
            Qgis.Critical, 10)
        return False

    si = QgsSpatialIndex()
    for fid, g in g_obr.items():
        si.addFeature(fid, g.boundingBox())

    wszystkie = adr.featureCount()
    do_usun = []
    for fid, g in g_adr.items():
        kand = si.intersects(g.boundingBox())
        if not any(g_obr[k].intersects(g) for k in kand):
            do_usun.append(fid)

    if not do_usun:
        bar.pushMessage(
            'OK', 'Wszystkie punkty adr_upul leżą w obrębie warstwy OBR - '
            'nic do usunięcia', Qgis.Success, 10)
        return True

    # --- potwierdzenie ----------------------------------------------------
    tresc = (
        f'Znaleziono {len(do_usun)} z {wszystkie} punktów warstwy adr_upul '
        'leżących poza warstwą OBR.\n\n'
        'Zostaną one TRWALE USUNIĘTE z pliku warstwy.\n'
        'Przed usunięciem zostanie utworzona kopia warstwy w folderze '
        'Kopie_manipulacyjne.\n\nCzy kontynuować?'
    )
    if len(do_usun) == wszystkie:
        tresc = (
            'UWAGA! Poza warstwą OBR leżą WSZYSTKIE punkty adr_upul '
            '(100%). Najpewniej wskazano złą warstwę OBR albo warstwy '
            'mają źle zdefiniowane układy współrzędnych.\n\n' + tresc)

    odp = QMessageBox.question(
        iface.mainWindow(), 'Usuń nadmiarowe adr_upul', tresc,
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    if odp != QMessageBox.Yes:
        return False

    # --- kopia i usuniecie ------------------------------------------------
    if kopie_manipulacyjne.zrob_kopie_manipulacyjna(
            None, [adr], 'usun_nadmiarowe_adr_upul') is None:
        bar.pushMessage(
            'BŁĄD', 'Nie udało się utworzyć kopii warstwy - nic nie '
            'usunięto (szczegóły w logu Las-R)', Qgis.Critical, 10)
        return False

    if not adr.dataProvider().deleteFeatures(do_usun):
        bar.pushMessage(
            'BŁĄD', 'Usuwanie punktów z adr_upul nie powiodło się',
            Qgis.Critical, 10)
        return False

    adr.updateExtents()
    adr.triggerRepaint()
    bar.pushMessage(
        'OK', 'Usunięto punkty adr_upul leżące poza OBR: '
        f'{len(do_usun)} (kopia w Kopie_manipulacyjne)', Qgis.Success, 10)
    return True
