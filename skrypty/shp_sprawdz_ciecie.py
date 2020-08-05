import os
from collections import Counter

from qgis.core import QgsProject, QgsSpatialIndex, QgsFeatureRequest, \
    QgsMessageLog, QgsWkbTypes, QgsVectorLayer, Qgis, QgsField

from PyQt5.QtCore import QVariant

from .baza_wrapper import znajdz_baze_do_wydz, Baza


class SprawdzCiecie:
    def __init__(self, iface):
        self.iface = iface
        self.si = QgsSpatialIndex()  # si pkt
        self.wydz = False  # wastwa wydz
        self.akt = False  # warstwa pkt z nr kart
        self.slpkt = {}
        self.slwydz = {}  # {f.id(): feat, }
        self.slkart = {}  # {adr: [[oddz, wydz], [oddz, wydz]],
        self.zdublowane_adr = []
        self.l_pkt_przec = []  # lista z pkt ktore przecinaja sie z wydz

    def zalozenia_poczatkowe(self):
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        self.wydz = [x for x in lyrs if x.name().upper() == 'WYDZ']
        if len(self.wydz) != 1:
            self.iface.messageBar().pushWarning(
                'Wydzielenia',
                'Tylko jedna warstwa w TOC powinna nazywać '
                'się WYDZ'
            )
            return False

        self.wydz = self.wydz[0]
        self.kat = os.path.dirname(self.wydz.dataProvider().dataSourceUri(
            ).split("|")[0])

        self.akt = self.iface.activeLayer()
        ftype = next(self.akt.getFeatures()).geometry().wkbType()
        if ftype not in [QgsWkbTypes.Point, QgsWkbTypes.MultiPoint]:
            self.iface.messageBar().pushWarning(
                'Aktywna warstwa', 'Zaznacz warstwę punktową z nr kart')
            return False

        # sprawdz czy w warstwie jest kolumna z ID
        if 'ID' not in [x.name() for x in
                        self.wydz.dataProvider().fields().toList()]:
            self.wydz.startEditing()
            self.wydz.dataProvider().addAttributes(
                [QgsField("ID", QVariant.Int)]
            )
            self.wydz.updateFields()
            self.wydz.commitChanges()

        # uaktualnij na nowo kolumn ID
        self.wydz.startEditing()
        request = QgsFeatureRequest().setFlags(
            QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
                ['ID'], self.wydz.fields()
            )
        sl = {}
        fnm = self.wydz.dataProvider().fieldNameMap()
        for feat in self.wydz.getFeatures(request):
            sl[feat.id()] = {fnm['ID']: feat.id()}
        self.wydz.dataProvider().changeAttributeValues(sl)
        self.wydz.commitChanges()

        if len([x.name() for x in self.akt.dataProvider().fields().toList()
                if x.name().upper() in ['ODDZ', 'WYDZ']]) != 2:
            self.iface.messageBar().pushWarning(
                'Brak kolumn', 'Warstwa z nr kart powinna zawierać kolumny '
                '[WYDZ, ODDZ]')
            return False
        return True

    def zbuduj_strukture(self):
        if not self.wydz.isValid() or not self.akt.isValid():
            self.iface.messageBar().pushWarning(
                'Poprawność warstw', 'Czy warstwy na pewno są poprawne?')
            return False

        for feat in self.akt.getFeatures():
            self.si.insertFeature(feat)
            self.slpkt[feat.id()] = feat

        wydz = []
        for feat in self.wydz.getFeatures():
            aa = feat['ID']
            self.slwydz[aa] = feat
            self.slkart[aa] = []
            wydz.append(aa)
            if aa in ['', None, 'NULL']:
                self.iface.messageBar().pushWarning(
                    'Błędny ID', 'Niezakodowana kolumna ID w WYDZ')
                return False

        # sprawdz czy adr_les nie pokrywa się w jakims wydzieleniu
        duble = Counter(wydz).most_common(30)
        if duble[0][1] > 1:
            self.iface.messageBar().pushWarning(
                'Zdublowane adresy leśne',
                'W warstwie znajdują się zdublowane adresy leśne '
                '- raporty mogą być nieprawdziwe! (Patrz Log LAS-R)')
            QgsMessageLog.logMessage(
                'Zdublowane adresy leśne: (pierwsze 30)', 'Las-R', Qgis.Warning
            )
            for it in duble:
                if it[1] == 1:
                    break
                QgsMessageLog.logMessage(
                    it[0]+' - '+str(it[1]), 'Las-R', Qgis.Warning
                )
                self.zdublowane_adr.append(str(it[0])+'(x'+str(it[1])+')')
        return True

    def przetworz(self):
        for feat in self.slwydz.values():
            rext = feat.geometry().boundingBox()
            ids = self.si.intersects(rext)

            for it in ids:
                fk = self.slpkt[it]
                if feat.geometry().intersects(fk.geometry()):
                    self.l_pkt_przec.append(it)
                    self.slkart[feat.id()] += [[str(fk['oddz']),
                                                str(fk['wydz']),
                                                str(feat['ADR_LES']),
                                                ]]

    def raport_spis_kart(self):
        sc = znajdz_baze_do_wydz(self.iface, self.wydz, poz=1)
        adm = {}  # slownik z kodami administracyjnymi
        if sc:
            b = Baza(sc)
            if b.polacz():
                pob = b.pobierz_naglowek()
                pob = [] if pob is False else pob
            adm = {x[4]+x[5]: x[3] for x in pob}

        rap_out = 'MUNICIP\tCOMMUNITY\tODDZ\tWYDZ\tNR_ROBO\tOBR\n'
        tab = []

        for k, val in self.slkart.items():
            key = '---------------------'
            if len(val) > 0:
                if len(val[0][2]) > 20:
                    key = val[0][2]

            tp = [key[3:6], key[6:10], key[13:17], key[18:20], ]

            # nazwa obrebu adm
            obr = '---'
            if key[3:10] in adm:
                obr = adm[key[3:10]]

            t = [tp+['-'.join(x[:2])]+[obr] for x in val]
            if len(val) == 0:
                t = [tp + ['', obr]]
            tab += t
        tout = sorted(tab, key=lambda x: ''.join(x[:3])+x[3][::-1])
        rap_out += '\n'.join((['\t'.join(x) for x in tout]))
        open(os.path.join(self.kat, '..',
                          'raport_nr_robocze.csv'), 'w').write(rap_out)

        self.iface.messageBar().pushSuccess(
            'OK', 'Zapisano raport z kartami'
        )

    def raport_rozbieznosci(self):
        wydz_bez = [str(k) for k, v in self.slkart.items() if len(v) == 0]
        wydz_wiela = [str(k) for k, v in self.slkart.items() if len(v) > 1]
        lpoz = [v for k, v in self.slpkt.items()
                if k not in self.l_pkt_przec]

        plug = os.path.dirname(__file__)
        if len(wydz_bez) > 0:
            lyrbez = QgsVectorLayer(
                "MultiPolygon?crs=epsg:2180",
                "WYDZ_bez_kart",
                "memory")
            lyrbez_dp = lyrbez.dataProvider()
            lyrbez.startEditing()
            lyrbez_dp.addAttributes(self.wydz.dataProvider().fields().toList())
            lyrbez.updateFields()
            lyrbez_dp.addFeatures([x for k, x in self.slwydz.items()
                                   if str(k) in wydz_bez])
            lyrbez.commitChanges()
            lyrb = QgsProject.instance().addMapLayer(lyrbez)
            lyrb.loadNamedStyle(os.path.join(
                plug, '..', 'qml', 'poly_red_outline.qml'))

        if len(wydz_wiela) > 0:
            lyrwiela = QgsVectorLayer(
                "MultiPolygon?crs=epsg:2180",
                "WYDZ_z_wieloma_kartami",
                "memory")
            lyrwiela_dp = lyrwiela.dataProvider()
            lyrwiela.startEditing()
            lyrwiela_dp.addAttributes(
                self.wydz.dataProvider().fields().toList())
            lyrwiela.updateFields()
            lyrwiela_dp.addFeatures([x for k, x in self.slwydz.items()
                                     if str(k) in wydz_wiela])
            lyrwiela.commitChanges()
            lyrw = QgsProject.instance().addMapLayer(lyrwiela)
            lyrw.loadNamedStyle(os.path.join(
                plug, '..', 'qml', 'poly_green_outline.qml'))

        if len(lpoz) > 0:
            lyrpkt = QgsVectorLayer(
                "MultiPoint?crs=epsg:2180",
                "Pkt_poza_wydz",
                "memory")
            lyrpkt_dp = lyrpkt.dataProvider()
            lyrpkt.startEditing()
            lyrpkt_dp.addAttributes(
                self.akt.dataProvider().fields().toList())
            lyrpkt.updateFields()
            lyrpkt_dp.addFeatures(lpoz)
            lyrpkt.commitChanges()
            lyrp = QgsProject.instance().addMapLayer(lyrpkt)
            lyrp.loadNamedStyle(os.path.join(
                plug, '..', 'qml', 'point_drop_shadow_red.qml'))

        self.iface.messageBar().pushSuccess(
            'OK', 'Sprawdzanie kart zakończone, znaleziono wydz bez kart: ' +
            str(len(wydz_bez)) + ', wydz z wieloma kartami: ' +
            str(len(wydz_wiela)) + ', pkt poza wydz: ' + str(len(lpoz))
        )
