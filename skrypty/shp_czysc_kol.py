import os

from PyQt5.QtWidgets import QDialog
from qgis.core import QgsVectorLayer, QgsFeatureRequest, Qgis
from .ui.ui_czysc_kolumny import Ui_Dialog


def czysc_kolumny(iface):
    d = PobierzDane(iface)
    d.exec_()

    if not d.kontynuuj:
        return

    w = iface.activeLayer()
    fnm = w.dataProvider().fieldNameMap()
    request = QgsFeatureRequest().setFlags(
        QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
            ['ODDZ', 'WYDZ', 'ADR_LES'], w.fields()
        )

    w.startEditing()

    sla = {}
    for feat in w.getFeatures(request):
        sl = {}
        if d.ui.checkBox_oddz.isChecked() and 'ODDZ' in fnm:
            sl[fnm['ODDZ']] = ' '
        if d.ui.checkBox_adrles.isChecked() and 'ADR_LES' in fnm:
            sl[fnm['ADR_LES']] = ' '
        if d.ui.checkBox_wydz.isChecked() and 'WYDZ' in fnm:
            if feat['WYDZ'].upper() != 'LZ':
                sl[fnm['WYDZ']] = ' '
            elif d.ui.checkBox_lz.isEnabled() and d.ui.checkBox_lz.isChecked():
                sl[fnm['WYDZ']] = ' '
        sla[feat.id()] = sl

    w.dataProvider().changeAttributeValues(sla)
    w.commitChanges()

    omit = True
    if d.ui.checkBox_oddz_warstwa.isEnabled():
        if d.ui.checkBox_oddz_warstwa.isChecked():
            omit = False

    if omit:
        iface.messageBar().pushMessage(
            'OK', 'Skasowana zawartość w wybranych kolumnach', Qgis.Success, 10
        )
        return

    sciezka = iface.activeLayer().dataProvider().dataSourceUri()
    sc = os.path.dirname(sciezka.split("|")[0][:-4])
    o = QgsVectorLayer(os.path.join(sc, 'ODDZ.shp'), 'oddz', 'ogr')

    request = QgsFeatureRequest().setFlags(
        QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
            ['ODDZ'], o.fields()
        )

    oid = o.dataProvider().fieldNameIndex('ODDZ')
    o.startEditing()
    sl = {}
    for feat in o.getFeatures(request):
        sl[feat.id()] = {oid: ' '}

    o.dataProvider().changeAttributeValues(sl)
    o.commitChanges()

    iface.messageBar().pushMessage(
        'OK', 'Skasowana zawartość w wybranych kolumnach', Qgis.Success, 10
    )


class PobierzDane(QDialog):
    def __init__(self, iface):
        super(PobierzDane, self).__init__()

        self.iface = iface
        self.kontynuuj = False
        self.kat = ''
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        sciezka = self.iface.activeLayer().dataProvider().dataSourceUri()
        sc = os.path.dirname(sciezka.split("|")[0][:-4])
        if os.path.isfile(os.path.join(sc, 'ODDZ.shp')):
            self.ui.checkBox_oddz_warstwa.setEnabled(True)
        else:
            self.ui.checkBox_oddz_warstwa.setEnabled(False)

        self.ui.pushButton_ok.clicked.connect(self.kont)
        self.ui.pushButton_porzuc.clicked.connect(self.porzuc)

    def kont(self):
        self.kontynuuj = True
        self.hide()

    def porzuc(self):
        self.hide()
