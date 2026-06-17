from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsLayerTreeGroup, \
    QgsLayerTreeLayer
from PyQt5.QtWidgets import QInputDialog
import os

# kolumny z klasą użytku gruntowego, w zależności od wersji/źródła danych
_KLU_POLA = ['AU', 'G5OFU', 'OFU']

# Dopasuj style: fragment nazwy warstwy w TOC (bez rozróżniania wielkości
# liter) -> plik .qml z folderu qml/. Dopasowanie po "zawiera się w nazwie",
# np. klucz 'WYDZ' dopasuje też warstwy 'WYDZ_POL_3_KOLORY' czy 'kopia_WYDZ'.
# TODO: uzupełnić wg rzeczywistych nazw warstw używanych w projektach.
DOPASOWANIE_STYLI = {
    'UZYTKI': 'KLU.qml',
    'KLU': 'KLU.qml',
    'WYDZ': 'WYDZ_POL.qml',
    'DZKAT': 'DZKAT.qml',
    'F_OCHRONY': 'FOP.qml',
    'FOP': 'FOP.qml',
    'OBR': 'OBR.qml',
    'PNSW': 'PNSW.qml',
    'ODDZ': 'OBR.qml',
}


def rysuj(iface, co):
    lyr = iface.activeLayer()
    if not lyr.isValid():
        iface.messageBar().pushMessage(
            'Brak warstwy',
            'Czy napewno zaznaczyłeś/aś warstwę?',
            Qgis.Critical,
            10
        )

    if co == 'ls':
        _rysuj_klu(iface, lyr)
        return

    sl = {
        'gat': ['SLMN_KOL', 'WYDZ_POL.qml'],
        'orto': ['ADR_LES', 'WYDZ_ORTO.qml'],
        'stl': ['STL', 'WYDZ_STL.qml'],
        'zab': ['ZABIEG', 'WYDZ_ZAB.qml'],
        'dzkat': ['PARCELNR', 'DZKAT.qml'],
    }

    if sl[co][0] in [x.name() for x in lyr.fields()] or co == 'dzkat':
        plugin_dir = os.path.dirname(__file__)
        lyr.loadNamedStyle(os.path.join(plugin_dir, '..', 'qml',
                                        sl[co][1]))
        iface.mapCanvas().refreshAllLayers()

    else:
        iface.messageBar().pushMessage(
            'Brak kolumn',
            'Nie znaleziono kolumny '+sl[co][0]+' w zaznaczonej warstwie!',
            Qgis.Critical,
            10
        )


def _rysuj_klu(iface, lyr):
    """Rysuje KLU.qml kategoryzując po AU, G5OFU lub OFU — w zależności od
    tego, która z tych kolumn jest obecna w warstwie. Jeśli jest ich kilka,
    pyta użytkownika którą użyć.
    """
    wszystkie_pola = [x.name() for x in lyr.fields()]
    kandydaci = [p for p in _KLU_POLA if p in wszystkie_pola]

    if len(kandydaci) == 0:
        iface.messageBar().pushMessage(
            'Brak kolumn',
            'Nie znaleziono żadnej z kolumn ' + ', '.join(_KLU_POLA) +
            ' w zaznaczonej warstwie!',
            Qgis.Critical,
            10
        )
        return

    if len(kandydaci) == 1:
        pole = kandydaci[0]
    else:
        pole, ok = QInputDialog.getItem(
            iface.mainWindow(),
            'Kolumna klasy użytku',
            'Znaleziono kilka kolumn z klasą użytku gruntowego.\n'
            'Wybierz, która ma być użyta do kategoryzacji KLU:',
            kandydaci,
            0,
            False
        )
        if not ok:
            return

    plugin_dir = os.path.dirname(__file__)
    lyr.loadNamedStyle(os.path.join(plugin_dir, '..', 'qml', 'KLU.qml'))
    if pole != 'AU':
        renderer = lyr.renderer()
        if renderer is not None and hasattr(renderer, 'setClassAttribute'):
            renderer.setClassAttribute(pole)
    iface.mapCanvas().refreshAllLayers()


def dopasuj_style(iface):
    """Dla każdej warstwy w projekcie (TOC) sprawdza, czy jej nazwa zawiera
    któryś z kluczy z DOPASOWANIE_STYLI (bez rozróżniania wielkości liter)
    i jeśli tak — wczytuje odpowiadający jej plik .qml.
    """
    if not DOPASOWANIE_STYLI:
        iface.messageBar().pushMessage(
            'Dopasuj style',
            'Słownik DOPASOWANIE_STYLI w shp_symbolizacja.py jest pusty — '
            'nie ma czego dopasować.',
            Qgis.Warning,
            10
        )
        return

    plugin_dir = os.path.dirname(__file__)
    dopasowane = []
    bledy = []
    niedopasowane = []

    for lyr in QgsProject.instance().mapLayers().values():
        nazwa = lyr.name().upper()
        klucz = next(
            (k for k in DOPASOWANIE_STYLI if k.upper() in nazwa), None
        )
        if klucz is None:
            niedopasowane.append(lyr.name())
            continue

        sciezka = os.path.join(plugin_dir, '..', 'qml', DOPASOWANIE_STYLI[klucz])
        try:
            lyr.loadNamedStyle(sciezka)
            lyr.triggerRepaint()
            dopasowane.append(lyr.name())
        except Exception as e:
            bledy.append(f'{lyr.name()}: {e}')

    iface.mapCanvas().refreshAllLayers()

    if dopasowane:
        iface.messageBar().pushMessage(
            'Dopasuj style',
            f'Zastosowano styl dla {len(dopasowane)} warstw(y): '
            + ', '.join(dopasowane),
            Qgis.Success,
            10
        )
    if bledy:
        iface.messageBar().pushMessage(
            'Dopasuj style — błędy',
            '; '.join(bledy),
            Qgis.Critical,
            10
        )
    if not dopasowane and not bledy:
        iface.messageBar().pushMessage(
            'Dopasuj style',
            'Żadna warstwa w projekcie nie dopasowała się do słownika stylów.',
            Qgis.Warning,
            10
        )


def PokazWezly(iface):
    plug = os.path.dirname(__file__)

    root = QgsProject.instance().layerTreeRoot()

    # sprawdź czy juz nie ma węzełków, jeżeli są usuń
    for ro in root.children():
        if isinstance(ro, QgsLayerTreeGroup):
            if ro.name() == 'LAS-R_Węzełki':
                root.removeChildNode(ro)
                return

    # jeżeli nie ma, wyszukaj wszystkie warstwy, dla których obsługujemy węzły
    # dodaj symbolizację i dodaj do grupy
    war = []
    for lyr in iface.mapCanvas().layers():
        # obsługa wyjątku dla wszystkich wartw, którenie są wektorami
        try:
            if lyr.wkbType() in [2, 3, 5, 6]:
                pass
        except:  # nopep8
            continue

        if lyr.wkbType() in [2, 3, 5, 6] and \
                '_las-r_węzełki' not in lyr.name():
            lyrw = QgsVectorLayer(
                lyr.source(),
                lyr.name() + '_las-r_węzełki',
                lyr.providerType()
            )
            war.append(lyrw)

    if len(war) > 0:
        gr = root.insertGroup(0, 'LAS-R_Węzełki')
        for w in war:
            lyrw = QgsProject.instance().addMapLayer(w, False)
            if lyrw.wkbType() in [2, 5]:
                lyrw.loadNamedStyle(os.path.join(
                    plug, '..', 'qml', 'vertices_lft.qml'))
            else:
                lyrw.loadNamedStyle(os.path.join(
                    plug, '..', 'qml', 'vertices_aft.qml'))

            gr.insertChildNode(0, QgsLayerTreeLayer(lyrw))
