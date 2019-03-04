from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsLayerTreeGroup, \
    QgsLayerTreeLayer
import os


def rysuj(iface, co):
    lyr = iface.activeLayer()
    if not lyr.isValid():
        iface.messageBar().pushMessage(
            'Brak warstwy',
            'Czy napewno zaznaczyłeś/aś warstwę?',
            Qgis.Critical,
            10
        )

    sl = {
        'gat': ['SLMN_KOL', 'WYDZ_POL.qml'],
        'orto': ['ADR_LES', 'WYDZ_ORTO.qml'],
        'stl': ['STL', 'WYDZ_STL.qml'],
        'zab': ['ZABIEG', 'WYDZ_ZAB.qml'],
        'dzkat': ['PARCELNR', 'DZKAT.qml'],
        'ls': ['AU', 'KLU.qml'],
    }

    if sl[co][0] in [x.name() for x in lyr.fields()] or co in ['dzkat', 'ls']:
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
