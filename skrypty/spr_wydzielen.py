from .sprawdzenia_warstw import SprawdzWydzielenia
from .baza_wrapper import Baza, znajdz_baze_do_wydz
from qgis.core import QgsGeometry, QgsSpatialIndex, Qgis, QgsMessageLog, \
    QgsField, QgsFeature, QgsVectorLayer, QgsProject
from PyQt5.QtCore import QVariant


class KontrolaWydzielen(SprawdzWydzielenia):
    def __init__(self, iface):
        self.iface = iface
        super()

        QgsMessageLog.logMessage(
                '\n\n--- SPRAWDZENIE WYDZIELEŃ ---\n',
                'LasR',
                Qgis.Info
        )

        self.wydz = self.iface.activeLayer()
        self.si = QgsSpatialIndex()
        self.sl_wydz = {}  # sl z wydz w postaci {id: feat}
        self.sl_adr = {}  # sl z adr_les oraz id (adr_les: id)
        self.sl_lz = {}  # slownik z lz dla calego obiektu
        self.wydz_przek_odl = []  # lista z featurami z przekr odl w wydz

        for f in self.wydz.getFeatures():
            self.si.insertFeature(f)
            self.sl_wydz[f.id()] = f
            if f['WYDZ'] == 'Lz':
                self.sl_lz[f.id()] = f

        self.wydz = self.iface.activeLayer()
        baza_sc = znajdz_baze_do_wydz(self.iface)
        if baza_sc:
            self.baza = Baza(baza_sc)

    def sprawdz_odl_wydz(self):
        """Metoda sprawdza czy w multipoligonach wydzieleń nie ma większych
        odległości między najbliższymi częsciami niż 30m. Jeżeli takie
        występują zostają zaraportowane użytkownikowi. Pomijane są sprwdzenia
        w Lz."""

        self.odl_wydz = {}
        self.f_przek_odl = []
        for f in self.sl_wydz.values():
            if len(f.geometry().asMultiPolygon()) > 1 and f['WYDZ'] != 'Lz':
                # dopisz poszczegolne czesci do tabeli jako pojedyncze poly
                tab = [QgsGeometry.fromPolygonXY(g) for g in
                       f.geometry().asMultiPolygon()]

                # sprawdz odległości pomiędzy wszystkimi poligonami
                odl = []
                for i in range(len(tab)-1):
                    odli = []
                    for j in range(len(tab)):
                        if i != j:
                            odli.append(tab[i].shortestLine(tab[j]).length())
                    odl.append(min(odli))

                self.odl_wydz[f['ADR_LES']] = max(odl)

                if max(odl) > 29.99:
                    self.f_przek_odl.append(f)

        # tabela z odległościami wiekszymi niz 30 m w wydzieleniach
        self.wydz_odl_przekrocz = sorted([[k, v] for k, v in
                                          self.odl_wydz.items()
                                          if v > 29.999],
                                         reverse=True,
                                         key=lambda x: x[0])
        return len(self.wydz_odl_przekrocz)

    def sprawdz_odl_lz(self):
        """Metoda sprawdza odległości poszczególnych Lz od wydzieleń w warstwie
        Jeżeli są mniejsze od 30m raportuje bledy"""

        self.lz_odl_przekrocz = []  # tablica z bliskimi odległościami do
        # wydzieleń w postaci : [[geometry, odl], [geometry, odl]]

        # sprawdz po kolei wszystkie Lz czy spełniają kryterium odległościowe
        for idik, feat in self.sl_lz.items():
            for part in feat.geometry().asMultiPolygon():
                geom = QgsGeometry.fromPolygonXY(part)
                ids = self.si.intersects(geom.boundingBox())
                for id in ids:
                    short_line = geom.shortestLine(
                        self.sl_wydz[id].geometry()).length()
                    if short_line < 30 and idik != id:
                        self.lz_odl_przekrocz.append([geom, short_line])

        self.lz_odl_przekrocz = sorted(self.lz_odl_przekrocz,
                                       reverse=True,
                                       key=lambda x: x[1]
                                       )
        return len(self.lz_odl_przekrocz)

    def pokaz_bledy(self):
        """Metoda dodaje warstwy w geometrią pokazującą błędy odległościowe
        w warstwie"""

        if len(self.wydz_odl_przekrocz) > 0:
            wydz_bodl = QgsVectorLayer(
                    "Polygon?crs=epsg:2180",
                    "WYDZ_błędy_odległości",
                    "memory")

            wydz_bodl.startEditing()
            wydz_bodl.dataProvider().addAttributes([
                QgsField("ID", QVariant.Int),
                QgsField("ADR_LES", QVariant.String, len=25),
                QgsField("ODLEGŁOŚCI", QVariant.Double, 'double', 10, 1),
            ])
            wydz_bodl.updateFields()

            fs = []
            for i, it in enumerate(self.wydz_przek_odl):
                feat = QgsFeature()
                feat.setGeometry(it.geometry())
                feat.setFields(wydz_bodl.fields())
                feat['ID'] = i
                feat['ADR_LES'] = it['ADR_LES']
                try:
                    feat['ODLEGŁOŚCI'] = self.odl_wydz[it['ADR_LES']]
                except:  # nopep8
                    feat['ODLEGŁOŚCI'] = 999
                fs.append(feat)

            wydz_bodl.dataProvider().addFeatures(fs)
            wydz_bodl.commitChanges()

            QgsMessageLog.logMessage(
                '\nWydzielenia z przekroczonymi odległościami: \n\t' +
                '\n\t'.join([x[0]+' - '+str(round(x[1], 1))+' m'
                             for x in self.wydz_odl_przekrocz]),
                'LasR',
                Qgis.Warning
            )

            QgsProject.instance().addMapLayer(wydz_bodl)

        else:
            wydruk = sorted([[k, v] for k, v in self.odl_wydz.items()],
                            reverse=True,
                            key=lambda x: x[1])[:10]

            QgsMessageLog.logMessage(
                'Wydzielenia z największymi odległościami: \n' +
                '\n'.join([x[0]+' - '+str(round(x[1], 1))+' m'
                           for x in wydruk]),
                'LasR',
                Qgis.Info
            )

        if len(self.lz_odl_przekrocz) > 0:
            lz_bodl = QgsVectorLayer(
                    "Polygon?crs=epsg:2180",
                    "Lz_blisko_wydzieleń",
                    "memory")

            lz_bodl.startEditing()
            lz_bodl.dataProvider().addAttributes([
                QgsField("ID", QVariant.Int),
                QgsField("ODLEGŁOŚCI", QVariant.Double, 'double', 10, 1),
            ])
            lz_bodl.updateFields()

            fs = []
            for i, it in enumerate(self.lz_odl_przekrocz):
                feat = QgsFeature()
                feat.setGeometry(it[0])
                feat.setFields(lz_bodl.fields())
                feat['ID'] = i
                try:
                    feat['ODLEGŁOŚCI'] = it[1]
                except:  # nopep8
                    feat['ODLEGŁOŚCI'] = 999
                fs.append(feat)

            lz_bodl.dataProvider().addFeatures(fs)
            lz_bodl.commitChanges()

            QgsMessageLog.logMessage(
                '\nLz z za bliskimi odległościami do wydzieleń: ' +
                str(len(self.lz_odl_przekrocz)),
                'LasR',
                Qgis.Warning
            )

            QgsProject.instance().addMapLayer(lz_bodl)

        else:
            QgsMessageLog.logMessage(
                'Odległości Lz od wydzieleń: OK',
                'LasR',
                Qgis.Info
            )

        QgsMessageLog.logMessage(
                '\n\n--- KONIEC ---\n',
                'LasR',
                Qgis.Info
        )
