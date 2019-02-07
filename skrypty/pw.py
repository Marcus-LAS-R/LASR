from PyQt5.QtWidgets import QProgressBar
from qgis.core import Qgis
from PyQt5.QtCore import Qt
# from qgis.core import Qgis


class PasekPostepu():
    def __init__(self, iface):
        self.iface = iface

    def stworz_pasek(self, tekst='', mini=0, maxi=100):
        self.tekst = tekst
        self.progressBar = QProgressBar(self.iface.messageBar())
        self.progressBar.setMinimum(mini)
        self.progressBar.setMaximum(maxi)
        self.progressBar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.progressMessageBarItem = \
            self.iface.messageBar().createMessage(self.tekst)
        self.progressMessageBarItem.layout().addWidget(self.progressBar)
        self.iface.messageBar().pushWidget(
            self.progressMessageBarItem,
            Qgis.Info,
        )

        return self.progressBar

    def clear(self):
        self.iface.messageBar().clearWidgets()

    def setMaximum(self, value):
        self.progressBar.setMaximum(value)

    def setMinimum(self, value):
        self.progressBar.setMinimum(value)
