import os
from qgis.utils import iface
from qgis.PyQt.QtWidgets import QMenu, QToolButton
from qgis.core import Qgis, QgsRasterLayer, QgsProject
from os import path
import glob


class QmlCacheModule():
    module_name = "Szybkie ładowanie styli qml"

    def __init__(self, parent):
        self.parent = parent

        pth = path.abspath(path.join(path.dirname(__file__), '..', 'ico'))
        self.action = self.parent.add_action(
            path.join(pth, 'layers.png'),
            self.module_name,
            callback=lambda: None,
            parent=iface.mainWindow(),
            checkable=True,
        )

        self.toolButton = self.parent.toolbar.widgetForAction(self.action)
        self.toolButton.setPopupMode(QToolButton.InstantPopup)

        self.actionMenu = None
        self.initMenu()

    def initMenu(self):
        self.action.setMenu(QMenu())
        self.actionMenu = self.action.menu()

        fls = glob.glob(path.join(path.dirname(__file__), 'qml', '*.qml'))

        for service in fls:
            nm = os.path.basename(service)
            action = self.actionMenu.addAction(nm)
            action.setData(service)
            action.triggered.connect(
                lambda checked,
                action=action: self.setQml(checked, action)
            )

    def setQml(self, checked, menu_action):
        params = menu_action.data()
        try:
            print(params)
            iface.activeLayer().loadNamedStyle(params)
            iface.activeLayer().triggerRepaint()
            iface.mapCanvas().refresh()
        except Exception as e:
            iface.messageBar().pushMessage(
                'Wczytanie qml', f'Nie udało się podczytać stylu {os.path.basename(params)} do warstwy {self.iface.activeLayer().name()}',
                level=Qgis.Warning
            )
