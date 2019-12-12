import os
from qgis.core import QgsProject, QgsFeatureRequest, QgsSpatialIndex, \
    QgsMessageLog, QgsWkbTypes, QgsVectorLayer, QgsField
from collections import Counter
from PyQt5.QtCore import QVariant


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

    def zalozenia_poczatkowe(self):
        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        self.wydz = [x for x in lyrs if x.name()[:4].upper() == 'WYDZ']
        if len(self.wydz) != 1:
            self.iface.messageBar().pushWarning(
                'Wydzielenia',
                'Nazwa tylko jednej  warstwy w TOC powinna zaczynać się od WYDZ'
            )
            return False
        self.wydz = self.wydz[0]
        self.kat = os.path.dirname(self.wydz.dataProvider().dataSourceUri(
            ).split("|")[0])

        self.akt = self.iface.activeLayer()
        fex = next(self.akt.getFeatures()).geometry().wkbType()
        if fex not in [QgsWkbTypes.Point, QgsWkbTypes.MultiPoint]:
            self.iface.messageBar().pushWarning(
                'Aktywna warstwa', 'Zaznacz warstwę punktową z nr kart')
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
            aa = str(feat['ADR_LES'])
            self.slwydz[aa] = feat
            self.slkart[aa] = []
            wydz.append(aa)
            if aa in ['', None, 'NULL']:
                self.iface.messageBar().pushWarning(
                    'Błędny ADR_LES', 'Niezakodowana kolumna ADR_LES w WYDZ')
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
            adr = str(feat['ADR_LES'])
            rext = feat.geometry().boundingBox()
            ids = self.si.intersects(rext)

            for it in ids:
                fk = self.slpkt[it]
                if feat.geometry().intersects(fk.geometry()):
                    self.slkart[adr] += [[str(fk['oddz']), str(fk['wydz'])]]

    def raport_spis_kart(self):
        rap_out = 'MUNICIP\tCOMMUNITY\tODDZ\tWYDZ\tNR_ROBO\n'
        tab = []
        for key, val in self.slkart.items():
            tp = [key[3:6], key[6:10], key[13:17], key[18:20], ]
            t = [tp+['-'.join(x)] for x in val]
            if len(val) == 0:
                t = [tp + ['', ]]
            tab += t
        tout = sorted(tab, key=lambda x: ''.join(x[:3])+x[3][::-1])
        rap_out += '\n'.join((['\t'.join(x) for x in tout]))
        open(os.path.join(self.kat,
                          'raport_nr_robocze.csv'), 'w').write(rap_out)

    def raport_rozbieznosci(self):
        wps = '-----RAPORT--------\n\n'
        wps += 'Liczba wydzieleń: ' + str(len(self.slwydz)) + '\n'
        wps += 'Liczba kart: ' + str(len(self.slpkt)) + '\n\n'

        if len(self.zdublowane_adr) > 0:
            wps += '---[ Zdublowane adr_les ]---\n'
            wps += '\n'.join(self.zdublowane_adr)
            wps += '\n\n* (wypisuje tylko 30 pierwszych)\n'
            wps += '\n\n'

        wps += '---[ wydzielenia bez nr roboczego ]---\n'
        wydz_bez = [k for k, v in self.slkart.items() if len(v) == 0]
        if len(wydz_bez) == 0:
            wps += '(Brak takowych)\n'
        else:
            wps += 'Liczba: '+str(len(wydz_bez)) + '\n\n'
            wps += '\n'.join(wydz_bez)
        wps += '\n\n'

        wps += '---[ wydzielenia z kilkoma nr roboczymi ]---\n'
        wydz_wiela = [k for k, v in self.slkart.items() if len(v) > 1]
        if len(wydz_wiela) == 0:
            wps += '(Brak takowych)\n'
        else:
            wps += 'Liczba: '+str(len(wydz_wiela)) + '\n\n'
            wps += '\n'.join(wydz_wiela)
        wps += '\n\n'
        open(os.path.join(self.kat, 'raport_spr_ciecia.txt'), 'w').write(wps)

        if len(wydz_bez) > 0:
            lyrbez = QgsVectorLayer(
                "MultiPolygon?crs=epsg:2180",
                "WYDZ_bez_kart",
                "memory")
            lyrbez_dp = lyrbez.dataProvider()
            lyrbez.startEditing()
            lyrbez_dp.addAttributes(self.wydz.dataProvider().fields().toList())
            lyrbez.updateFields()
            lyrbez_dp.addFeatures([x for x in self.slwydz.values()
                                if x['ADR_LES'] in wydz_bez])
            lyrbez.commitChanges()
            QgsProject.instance().addMapLayer(lyrbez)

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
            lyrwiela_dp.addFeatures([x for x in self.slwydz.values()
                                if x['ADR_LES'] in wydz_wiela])
            lyrwiela.commitChanges()
            QgsProject.instance().addMapLayer(lyrwiela)

        self.iface.messageBar().pushSuccess(
            'OK', 'Sprawdzanie kart zakończone, znaleziono wydz bez kart: ' +\
            str(len(wydz_bez)) + ', wydz z wieloma kartami: ' + \
            str(len(wydz_wiela))
        )
