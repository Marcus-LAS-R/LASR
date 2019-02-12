from qgis.core import QgsVectorLayer, Qgis, QgsVectorFileWriter, \
    QgsCoordinateReferenceSystem, QgsMessageLog
import os
import glob
import processing


class EksportujKML():
    def __init__(self, iface):
        self.iface = iface
        self.nowy_temp = True  # trig przy towrzeniu nowego katalogu temp

    def pobierzDane(self):
        """Metoda wyświetla dialog dla użytkownika a następnie przepisuje
        podane dane"""

        k = self.iface.activeLayer()
        try:
            if not k.isValid():
                self.ls = False
                return False
            else:
                self.ls = k
        except:  # nopep8
            pass

        # nazwa warstwy
        self.nazwa = self.ls.name()

        lsc = self.ls.dataProvider().dataSourceUri().split("|")[0]
        self.kat = os.path.dirname(lsc)
        return True

        # return self.dd.poprawne

    def przetworz(self):
        """ Metoda przetwarza warstwy poly na linie przy uzyciu algorytmu z
        zestawu alg sagi"""

        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)
            self.nowy_temp = True

        processing.run(
            'saga:convertpolygonstolines',
            {'POLYGONS': self.ls,
             'LINES': os.path.join(self.tempkat, '__'+self.nazwa+'_lines.shp')
             }
        )

        self.ls_lines = QgsVectorLayer(
            os.path.join(self.tempkat, '__'+self.nazwa+'_lines.shp'),
            'ls_lines',
            'ogr'
        )

        processing.run(
            'saga:polygondissolveallpolygons',
            {'POLYGONS': self.ls,
             'BND_KEEP': False,
             'DISSOLVED': os.path.join(self.tempkat,
                                       '__'+self.nazwa+'_diss.shp')
             }
        )

        processing.run(
            'saga:polygonpartstoseparatepolygons',
            {
                'POLYGONS': os.path.join(self.tempkat,
                                         '__'+self.nazwa+'_diss.shp'),
                'LAKES': True,
                'PARTS': os.path.join(self.tempkat,
                                      '__'+self.nazwa+'_diss_single.shp')
            }
        )

        self.ls_diss = QgsVectorLayer(
            os.path.join(self.tempkat, '__'+self.nazwa+'_diss_single.shp'),
            'ls_diss',
            'ogr'
        )

        processing.run(
            'saga:convertpolygonstolines',
            {'POLYGONS': os.path.join(self.tempkat,
                                      '__'+self.nazwa+'_diss_single.shp'),
             'LINES': os.path.join(self.tempkat,
                                   '__'+self.nazwa+'_diss_single_lines.shp')
             }
        )

        self.ls_diss_lines = QgsVectorLayer(
            os.path.join(self.tempkat,
                         '__'+self.nazwa+'_diss_single_lines.shp'),
            'ls_diss_lines',
            'ogr'
        )

        self.warstwy = [
            self.ls,
            self.ls_diss,
            self.ls_lines,
            self.ls_diss_lines,
        ]

    def zapisz_kml(self):
        """Metoda zapisuje przetworzone warstwy do plików KML"""

        # nazwy warstw
        war = [
            self.nazwa + '_poly',
            self.nazwa + '_poly_diss',
            self.nazwa + '_lines',
            self.nazwa + '_lines_diss',
        ]

        for ilyr, lyr in enumerate(self.warstwy):
            if ilyr < 2:
                definicja = "Polygon?crs=epsg:2180&index=yes"
            else:
                definicja = "LineString?crs=epsg:2180&index=yes"

            tab = []
            for feat in lyr.getFeatures():
                tab.append(feat)

            # posortuj po LANDID o ile istnieje
            if 'LANDID' in [x.name() for x in
                            lyr.dataProvider().fields().toList()]:
                tab = sorted(tab, key=lambda x: x['LANDID'])

            czesc = 1
            feats = []
            licz = 0
            for feat in tab:
                feats.append(feat)
                licz += 1

                if licz == 1999:
                    nazwa = war[ilyr] + '_' + str(czesc) + '.kml'
                    self.zapisz_cz([feats, czesc, nazwa, definicja, lyr])
                    czesc += 1
                    licz = 0
                    feats = []

            # koncowka
            if licz > 0:
                nazwa = war[ilyr] + '_' + str(czesc) + '.kml'
                self.zapisz_cz([feats, czesc, nazwa, definicja, lyr])

        self.sprzatnij()

    def zapisz_cz(self, dane):
        """ Metoda zapisuje dane do kml, dane wsadowe to tablica:
            [ [feats], czesc, nazwa pliku, lyr ]
        """
        crs = QgsCoordinateReferenceSystem("epsg:4326")

        feats = dane[0]
        nazwa = dane[2]
        definicja = dane[3]
        lyr = dane[4]

        lyrb = QgsVectorLayer(definicja, "lyr", "memory")

        lyrb.startEditing()
        lyrb.dataProvider().addAttributes(
            lyr.dataProvider().fields().toList()
        )
        lyrb.updateFields()
        lyrb.dataProvider().addFeatures(feats)
        lyrb.commitChanges()

        try:
            QgsVectorFileWriter.writeAsVectorFormat(
                lyrb,
                os.path.join(self.kat, nazwa),
                "UTF-8",
                crs,
                "KML")
        except:  # nopep8
            QgsMessageLog.logMessage(
                'Nie udało się zapisać ' + nazwa,
                "Las-R"
            )

    def sprzatnij(self):
        """ Metoda kasuje pliki tymczasowe i proboje skasowac katalog """
        del self.ls_diss, self.ls_lines, self.ls_diss_lines

        lista = glob.glob(os.path.join(self.tempkat, '*.*'))

        # skasuj jeżeli katalog jest pusty
        try:
            for ll in lista:
                os.remove(ll)
            os.removedirs(self.tempkat)
        except:  # nopep8
            pass

        self.iface.messageBar().pushMessage(
            'OK',
            'Warstwy zapisanow w katalogu z warstwą',
            Qgis.Success,
            15
        )
