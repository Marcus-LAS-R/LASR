from qgis.core import Qgis
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
    }

    if sl[co][0] in [x.name() for x in lyr.fields()]:
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
