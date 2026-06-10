import os
import glob
import shutil
from qgis.core import QgsVectorLayer, QgsFeature, Qgis, QgsSpatialIndex, \
    QgsRectangle, QgsCoordinateReferenceSystem, QgsVectorFileWriter, \
    QgsMessageLog, QgsProject
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QVariant
import processing

from .ui.ui_wyszukaj_lz import Ui_Dialog


class WyszukajLz():
    def __init__(self, iface):
        self.iface = iface
        QgsMessageLog.logMessage('---[ Wyznacz potencjalne Lz ]---',
                                 'Las-R', Qgis.Info)

        self.ls = False
        self.uz = False
        self.oddz = False

        self.kat = ''  # katalog z ls
        self.tempkat = ''  # katalog temp w katalogu z ls
        self.odl_min = 15  # domyslna odl potencjalnych lz od ls

        self.ls_si = QgsSpatialIndex()
        self.oddz_si = QgsSpatialIndex()
        self.ls_diss_si = QgsSpatialIndex()  # SI z diss poly z ls
        self.uz_diss_si = QgsSpatialIndex()

        self.ls_fts = {}  # slownik z featurami ls
        self.ls_fts_pow = {}  # proporcjonalna pow rej [ha] per singlepart ls
        self.uz_fts = {}  # slownik z featurami uz
        self.ls_diss = {}  # sl z diss feat ls
        self.oddz_fts = {}  # sl w featsami oddz
        self.lzp = []  # lista z potencjalnymi lzami w postaci feat

        self.uz_pole = ''  # pole w uzytkach przetrzymujace klasę gr

    def pobierz_dane(self):
        """ Metoda pobiera informacje na temat danych od użytkownika na temat
        warstw (Ls i ODDZ PGLLPl), sprawdza czy warstwa Ls posiada odpowienią
        strukturę i czy pola w niezbędnych kolumnach są wypełnione
        """

        lyrs = [x for x in QgsProject.instance().mapLayers().values()]
        ls = [x for x in lyrs if x.name()[:2].upper() == 'LS']
        oddz = [x for x in lyrs if x.name()[:4].upper() == 'ODDZ']
        uz = [x for x in lyrs if x.name()[:4].upper() in ['UZYT', 'UŻYT']]

        if len(ls) > 0:
            self.ls = ls[0]
        if len(uz) > 0:
            self.uz = uz[0]
        if len(oddz) > 0:
            self.oddz = oddz[0]

        # pobierz dane od użytkownika
        self.pd = PobierzDane(self.ls, self.uz, self.oddz)
        self.pd.exec_()

        if not self.pd.kontynuuj:
            return False

        # sprawdz czy uzyszkodnik chce sprawdzac ls razem z oddzialami PGLLP
        if self.pd.ui.lineEdit_oddz.text() != '':
            self.oddz = QgsVectorLayer(self.pd.ui.lineEdit_oddz.text(),
                                       'oddz', 'ogr')
        else:
            self.oddz = False

        # sprawdz czy warstwa ls jest poprawna i ma wszystkie niezbedne pola
        self.ls = QgsVectorLayer(self.pd.ui.lineEdit_ls.text(), 'lssy', 'ogr')
        if not self.ls.isValid():
            self.ls = False

        pola_ls = [x.name() for x in self.ls.dataProvider().fields().toList()]
        if len([x for x in pola_ls if x in ['AU', 'SQ', 'LAND_AR']]) != 3:
            self.ls = False
            self.iface.messageBar().pushMessage(
                'LS',
                'Brak wymaganych pól w tabeli atrybutów [AU, SQ, LAND_AR]',
                Qgis.Critical,
                10
            )
            QgsMessageLog.logMessage(
                'Brak wymaganych pól w tabeli atrybutów [AU, SQ, LAND_AR]'
                '\n---[ KONIEC ]---',
                'Las-R', Qgis.Critical
            )
            return False

        if self.uz is not False:
            wszystkie_pola = [x.name() for x in
                              self.uz.dataProvider().fields().toList()]
            pola_uz_wyb = [p for p in wszystkie_pola
                           if p in ['AU', 'G5OFU', 'OFU']]

            if len(pola_uz_wyb) == 1:
                self.uz_pole = pola_uz_wyb[0]
            else:
                # 0 znanych kolumn → pytaj o dowolną kolumnę z warstwy
                # 2+ znanych kolumn → pytaj którą z nich użyć
                kandydaci = pola_uz_wyb if pola_uz_wyb else wszystkie_pola
                wybrane = self.pd.wybierz_pole_uz(kandydaci)
                if not wybrane:
                    self.iface.messageBar().pushMessage(
                        'UŻYTKI',
                        'Nie wybrano kolumny z klasą użytku — analiza przerwana',
                        Qgis.Warning,
                        10
                    )
                    return False
                self.uz_pole = wybrane

        lsc = self.ls.dataProvider().dataSourceUri().split("|")[0]
        self.kat = os.path.dirname(lsc)
        QgsMessageLog.logMessage(
            'Scieżka katalogu: ' + self.kat,
            'Las-R', Qgis.Info
        )

        # odl podana przez uzyt.
        self.odl_min = int(self.pd.ui.lineEdit_odl.text())

        return True

    def isNone(self, a):
        if a in [None, 'NULL', '', ]:
            return ''
        elif isinstance(a, QVariant):
            if a.isNull():
                return ''
        else:
            return a

    def zabuduj_strukt(self):  # noqa
        """Metoda buduje indeksy przestrzenne dla warstw o ile istnieją"""
        self.crs = QgsCoordinateReferenceSystem("epsg:2180")

        # stworz katalog tymczasowy, wyczysc stare pliki jesli istnieja
        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)
        else:
            for f in glob.glob(os.path.join(self.tempkat, 'ls*')) + \
                     glob.glob(os.path.join(self.tempkat, 'uz*')):
                try:
                    os.remove(f)
                except (PermissionError, OSError):
                    pass

        self.struk_oddz()
        self.struk_ls()
        if self.uz is not False:
            self.struk_uz()

        del self.w_ls_diss

    def struk_oddz(self):
        if self.oddz is not False:
            for feat in self.oddz.getFeatures():
                self.oddz_si.insertFeature(feat)
                self.oddz_fts[feat.id()] = feat

        QgsMessageLog.logMessage(
            'Wczytano oddziałów: ' + str(len(self.oddz_fts)),
            'Las-R', Qgis.Info
        )

    def struk_ls(self):
        # Multipolygony dzielimy na singleparty przed indeksem.
        # LAND_AR na featurach zostaje oryginalne; proporcjonalna pow każdej
        # części trafia do ls_fts_pow (używanego wyłącznie do obliczeń).
        next_id = 0
        for feat in self.ls.getFeatures():
            if feat['AU'] != 'Ls':
                continue
            geom = feat.geometry()
            parts = geom.asGeometryCollection() if geom.isMultipart() else [geom]
            total_area = geom.area() or 1.0
            orig_land_ar = feat['LAND_AR'] or 0.0
            for part_geom in parts:
                if part_geom.area() == 0:
                    continue
                part_feat = QgsFeature(feat.fields())
                part_feat.setId(next_id)
                part_feat.setAttributes(feat.attributes())
                part_feat.setGeometry(part_geom)
                ratio = part_geom.area() / total_area
                self.ls_fts_pow[next_id] = orig_land_ar * ratio
                self.ls_si.insertFeature(part_feat)
                self.ls_fts[next_id] = part_feat
                next_id += 1

        QgsMessageLog.logMessage(
            'Wczytano fragmentów LS (Ls): ' + str(next_id),
            'Las-R', Qgis.Info
        )

        # stwórz warstwy tymczasowe dla lasów z uzytków i ls
        self.lswybr = QgsVectorLayer(
            "MultiPolygon?crs=epsg:2180&index=yes",
            "LS_wybrane_ls",
            "memory"
        )
        self.lswybr.startEditing()
        self.lswybr.dataProvider().addAttributes(
            self.ls.dataProvider().fields().toList()
        )
        self.lswybr.updateFields()
        self.lswybr.addFeatures(self.ls_fts.values())
        self.lswybr.commitChanges()

        QgsVectorFileWriter.writeAsVectorFormat(
            self.lswybr,
            os.path.join(self.tempkat, "Ls_wybr.shp"),
            "UTF-8",
            self.crs,
            "ESRI Shapefile")

        self.lswybr = QgsVectorLayer(
            os.path.join(self.tempkat, "Ls_wybr.shp"),
            "LS_wybrane_ls",
            "ogr"
        )

        processing.run("native:dissolve",
                    {'INPUT':self.lswybr,
                        'FIELD': [],
                        'SEPARATE_DISJOINT':True,
                        'OUTPUT': os.path.join(self.tempkat, 'ls_diss.shp')
                        })

        # processing.run(
            # 'saga:polygondissolveallpolygons',
            # {'POLYGONS': self.lswybr,
             # 'BND_KEEP': False,
             # 'DISSOLVED': os.path.join(self.tempkat, 'ls_diss.shp')
             # }
        # )

        processing.run("native:multiparttosingleparts", {
                        'OUTPUT': os.path.join(
                            self.tempkat,
                            'ls_diss_single.shp'),
                        'INPUT': os.path.join(
                            self.tempkat, 'ls_diss.shp')
                        })

        # wczytaj warstwe ls single partow
        self.w_ls_diss = QgsVectorLayer(
            os.path.join(self.tempkat, 'ls_diss_single.shp'),
            'ls_diss_single',
            'ogr'
        )

        for feat in self.w_ls_diss.getFeatures():
            self.ls_diss_si.insertFeature(feat)
            self.ls_diss[feat.id()] = feat

    def struk_uz(self):
        for feat in self.uz.getFeatures():
            if feat[self.uz_pole] == 'Ls':
                self.uz_fts[feat.id()] = feat

        QgsMessageLog.logMessage(
            'Znalazłem Ls w UZYTKACH:' + str(len(self.uz_fts.keys())),
            'Las-R', Qgis.Info
        )

        if len(self.uz_fts.keys()) == 0:
            return

        self.uzwybr = QgsVectorLayer(
            "MultiPolygon?crs=epsg:2180&index=yes",
            "UZYTKI_wybrane_ls",
            "memory"
        )
        self.uzwybr.startEditing()
        self.uzwybr.dataProvider().addAttributes(
            self.uz.dataProvider().fields().toList()
        )
        self.uzwybr.updateFields()
        self.uzwybr.addFeatures(self.uz_fts.values())
        self.uzwybr.commitChanges()

        QgsVectorFileWriter.writeAsVectorFormat(
            self.uzwybr,
            os.path.join(self.tempkat, "uz_wybr.shp"),
            "UTF-8",
            self.crs,
            "ESRI Shapefile")

        self.uzwybr = QgsVectorLayer(
            os.path.join(self.tempkat, "uz_wybr.shp"),
            "uz_wybr",
            "ogr"
        )

        if len(self.uz_fts.keys()) > 1:
            processing.run("native:dissolve",
                        {'INPUT':self.uzwybr,
                            'FIELD':[],
                            'SEPARATE_DISJOINT':True,
                            'OUTPUT': os.path.join(self.tempkat, 'uz_diss.shp')
                            })

            # processing.run(
                # 'saga:polygondissolveallpolygons',
                # {'POLYGONS': self.uzwybr,
                 # 'BND_KEEP': False,
                 # 'DISSOLVED': os.path.join(self.tempkat, 'uz_diss.shp')
                 # }
            # )
        else:
            for roz in ['shp', 'shx', 'prj', 'dbf']:
                shutil.copy(os.path.join(self.tempkat, "uz_wybr."+roz),
                            os.path.join(self.tempkat, "uz_diss."+roz))

        if len(self.uz_fts.keys()) > 1:
            processing.run("native:multiparttosingleparts", {
                'OUTPUT': os.path.join(
                    self.tempkat,
                    'uz_diss_single.shp'),
                'INPUT': os.path.join(
                    self.tempkat, 'uz_diss.shp')
            })
        else:
            for roz in ['shp', 'shx', 'prj', 'dbf']:
                shutil.copy(os.path.join(self.tempkat, "uz_diss."+roz),
                            os.path.join(self.tempkat, "uz_diss_single."+roz))

        processing.run(
            "native:difference",
            {'INPUT':os.path.join(self.tempkat, 'uz_diss_single.shp'),
             'OVERLAY':self.w_ls_diss,
             'OUTPUT': os.path.join(self.tempkat, 'uz_diss_single_diff.shp'),
             'GRID_SIZE': None
             })

        # processing.run("saga:difference", {
            # 'A': os.path.join(self.tempkat, 'uz_diss_single.shp'),
            # 'B': self.w_ls_diss,
            # 'SPLIT': True,
            # 'RESULT': os.path.join(self.tempkat, 'uz_diss_single_diff.shp')
        # })

        # wczytaj warstwe ls single partow
        w_uz_diss = QgsVectorLayer(
            os.path.join(self.tempkat, 'uz_diss_single_diff.shp'),
            'uz_diss_single_diff',
            'ogr'
        )

        self.uz_fts = {}  # kasujemy slownik poprzednich featurkow, sa zbedne
        for feat in w_uz_diss.getFeatures():
            self.uz_diss_si.insertFeature(feat)
            self.uz_fts[feat.id()] = feat

        del w_uz_diss

    def wybierz_potencjalne_lz(self):
        """Metoda wybiera z warstwy Ls potencjalne poligony z odpowiednią
        wielkością pow Rejestrowej w bazie"""

        # wybierz polaczone featurki z ls_diss ktore maja pow graf mniejsza niz
        # 20 ar, to powinno zapewnic ze nie pominiemy ls ktory powinien byc lz
        f_diss = [feat for feat in self.ls_diss.values()
                  if feat.geometry().area() < 2000]

        for f in f_diss:
            # sprawdz czy skladowe ls maja w sumie pow rej mniejsza niz 10 ar
            ids_ls = self.ls_si.intersects(f.geometry().boundingBox())

            pow_skl_ls = 0
            tab_ls = []  # tabela z ls skladowymi
            for id in ids_ls:
                # jezeli pow ls przecina sie z analizowanym terenem dodaj do
                # sumy pow do sprawdzenia
                inter = self.ls_fts[id].geometry().intersection(f.geometry())
                if (inter.area()/self.ls_fts[id].geometry().area()) > 0.9:
                    # sprawdzamy tylko i wylacznie ls!!!
                    if self.ls_fts[id]['AU'] == 'Ls':
                        pow_skl_ls += self.ls_fts_pow[id]
                        tab_ls.append(self.ls_fts[id])

            # pow skladowych ls jest mniejsza niz 10 ar, sprawdz sasiedztwo
            if 0 < pow_skl_ls < 0.1:
                lz = self.sprawdz_sasiedztwo_plz(tab_ls)

                # jezeli lz zwrocily True i niepusta listę dodaj do
                # pozostałych.
                if lz[0]:
                    self.lzp += lz[1]

    def sprawdz_sasiedztwo_plz(self, tab_ls):  # noqa
        """Sprawdzenie sąsiedztwa dla potencjalnych Lz, jeżeli odległość do
        najbliższego jest większa niż wybrana przez użytkownika (domyślnie 15m)
        uzytek klasyfikowany jest jako Lz
        dane wejsciowe:
            f - singlepart feat ls z pow rej mniejsza niz 10 ar -
                ale nie sprawdzonym sasiedztwem
            tab_id - tabela z id wlasciwych ls wchodzacych w tego singleparta

        dane wyjsciowe:
            [True/False, # w zaleznoscie czy sa lz czy nie
             [feat, feat,...]  # lista feat spełniających warunki,
                               # jeżeli nie ma, pusta lista
        """

        # za kazdym przebiegiem budowany jest nowy boundingbox a nastepnie
        # sprawdane sa nowe ls o ile w nim wystepuja, najpierw z single
        # sprawdzana jest odleglosc a potem juz z konkretnymi featurami pow
        # rejestrowa.

        lsy = list(tab_ls)  # lista ls w klastrze
        lsy_id = [ff.id() for ff in tab_ls]  # lista id ls w klastrze

        zmiana = True  # czy w petli nastapila jakakolwiek zmiana
        zmiana_licz = 0  # numer przebiegu, zabezpiecznie przed zapetleniem
        pow_rej_ls = sum([self.ls_fts_pow[x.id()] for x in lsy])  # pow rej kompleksu

        # iteruj po kolei ls i sprawdzaj sasiedztwo, jezeli nie dojda nowe ls
        # ktore przekraczaja 10 ar, zwroc jako Lz
        while zmiana and zmiana_licz < 100:
            rect = self.stworz_bboxa(lsy)
            zmiana = False
            zmiana_licz += 1

            # sprawdz o ile wskazano oddz pgllp czy nic sie nie styka
            if self.oddz is not False:
                ids = self.oddz_si.intersects(rect)
                for id in ids:
                    for ls in lsy:
                        otemp = \
                            round(ls.geometry().shortestLine(
                                self.oddz_fts[id].geometry()).length(), 2)
                        if otemp < self.odl_min:
                            try:
                                QgsMessageLog.logMessage(
                                    'Potencjalny Lz, blisko PGL LP: ' +
                                    str(otemp) + 'm \t\tuz:' +
                                    ls['LANDID'] + ",\t oddz:" +
                                    self.oddz_fts[id]['adr_for'],
                                    'Las-R', Qgis.Info
                                )
                            except:  # nopep8
                                pass
                            return [False, []]

            # sprawdzamy czy kompleks nie lezy za blisko innych uzytków
            if self.uz is not False:
                ids = self.uz_diss_si.intersects(rect)
                for id in ids:
                    for ls in lsy:
                        otemp = \
                            round(ls.geometry().shortestLine(
                                self.uz_fts[id].geometry()).length(), 2)
                        if otemp < self.odl_min and \
                                self.uz_fts[id].geometry().area()/10000 > 0.1:
                            try:
                                QgsMessageLog.logMessage(
                                    'Potencjalny Lz, blisko uzytku: ' +
                                    str(otemp) + 'm \t\tuz:' +
                                    ls['LANDID'],
                                    'Las-R', Qgis.Info
                                )
                            except:  # nopep8
                                pass
                            return [False, []]

            # sprawdz czy sa jakies ls w powiekszonym zasiegu i nie sa to juz
            # wyselekcjonowane ls
            idst = self.ls_si.intersects(rect)
            ids = [x for x in idst if x not in lsy_id]

            # brak nowych ls w zasiegu, zwracamy odkryty klaster
            if len(ids) == 0:
                return [True, lsy]

            for id in ids:
                # jezeli juz dodalismy w tym przebiegu ten ls, pomijamy
                if id in lsy_id:
                    continue

                for ls in lsy:
                    otemp = \
                        ls.geometry().shortestLine(self.ls_fts[id].geometry()
                                                   ).length()
                    if otemp < self.odl_min:
                        if pow_rej_ls + self.ls_fts_pow[id] > 0.1:
                            return [False, []]
                        else:
                            lsy.append(self.ls_fts[id])
                            lsy_id.append(id)
                            pow_rej_ls += self.ls_fts_pow[id]
                            zmiana = True
                            break

        return [True, lsy]

    def stworz_bboxa(self, flist):
        """Metoda tworzy boundingBox'a na podstawie listy feat, z poszerzeniem
        zadanym przez uzytkownika
        """
        rect = [
            flist[0].geometry().boundingBox().xMinimum(),
            flist[0].geometry().boundingBox().yMinimum(),
            flist[0].geometry().boundingBox().xMaximum(),
            flist[0].geometry().boundingBox().yMaximum(),
        ]

        for feat in flist[1:]:
            if feat.geometry().boundingBox().xMinimum() < rect[0]:
                rect[0] = feat.geometry().boundingBox().xMinimum()
            if feat.geometry().boundingBox().yMinimum() < rect[1]:
                rect[1] = feat.geometry().boundingBox().yMinimum()
            if feat.geometry().boundingBox().xMaximum() > rect[2]:
                rect[2] = feat.geometry().boundingBox().xMaximum()
            if feat.geometry().boundingBox().yMaximum() > rect[3]:
                rect[3] = feat.geometry().boundingBox().yMaximum()

        return QgsRectangle(rect[0]-self.odl_min,
                            rect[1]-self.odl_min,
                            rect[2]+self.odl_min,
                            rect[3]+self.odl_min,
                            )

    def stworz_warstwe_lz(self):
        """Metoda tworzy warstwę wirtualną Lz i dodaje ją do projektu """

        self.iface.messageBar().pushMessage(
            'LZ',
            'Zakończono pomyślnie! Odnaleziono Lz : ' + str(len(self.lzp)),
            Qgis.Success,
            10
        )

        QgsMessageLog.logMessage(
            'Zakończono pomyślnie! Odnaleziono Lz : ' + str(len(self.lzp)),
            'Las-R', Qgis.Info
        )

        if len(self.lzp) == 0:
            return

        lzp = QgsVectorLayer(
                "Polygon?crs=epsg:2180",
                "LZ_pot",
                "memory")

        lzp.startEditing()
        lzp.dataProvider().addAttributes(self.ls.dataProvider().fields())
        lzp.updateFields()

        land_pow_idx = self.ls.dataProvider().fields().indexFromName('LAND_POW')
        if land_pow_idx >= 0:
            for f in self.lzp:
                f.setAttribute(land_pow_idx, round(f.geometry().area() / 10000, 4))

        lzp.dataProvider().addFeatures(self.lzp)
        lzp.commitChanges()

        # zapisz dane w warstwach na dysku
        crs = QgsCoordinateReferenceSystem("epsg:2180")

        QgsVectorFileWriter.writeAsVectorFormat(
            lzp,
            os.path.join(self.kat, "LZ_potencjalne.shp"),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        # dodaj do TOC
        self.lz_lyr = self.iface.addVectorLayer(
            os.path.join(self.kat, "LZ_potencjalne.shp"),
            "LZ_potencjalne",
            "ogr"
        )

        # zwolnij uchwyty do plikow tymczasowych przed usunieciem
        if hasattr(self, 'lswybr'):
            del self.lswybr
        if hasattr(self, 'uzwybr'):
            del self.uzwybr

        # sprzatamy po sobie
        lista = glob.glob(os.path.join(self.tempkat, 'ls*'))
        lista += glob.glob(os.path.join(self.tempkat, 'uz*'))
        for ll in lista:
            try:
                os.remove(ll)
            except (PermissionError, OSError):
                pass
        try:
            os.removedirs(self.tempkat)
        except:  # nopep8
            pass

        QgsMessageLog.logMessage('---[ KONIEC ]---',
                                 'Las-R', Qgis.Info)


class PobierzDane(QDialog):
    def __init__(self, ls=False, uz=False, oddz=False):
        super(PobierzDane, self).__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ls = ls
        self.uz = uz
        self.oddz = oddz
        self.kontynuuj = False
        self.kat = ''

        if ls:
            if self.ls.isValid():
                self.ui.lineEdit_ls.setText(
                    self.ls.dataProvider().dataSourceUri().split("|")[0]
                )
                lsc = self.ls.dataProvider().dataSourceUri().split("|")[0]
                self.kat = os.path.dirname(lsc)

        if uz:
            if self.uz.isValid():
                self.ui.lineEdit_uz.setText(
                    self.uz.dataProvider().dataSourceUri().split("|")[0]
                )
                lsc = self.uz.dataProvider().dataSourceUri().split("|")[0]
                self.kat = os.path.dirname(lsc)

        if oddz:
            self.sprawdz_oddz()
        elif self.kat:
            candidates = glob.glob(os.path.join(self.kat, '*PGLLP*.shp'))
            if candidates:
                pgllp = QgsVectorLayer(candidates[0], 'pgllp', 'ogr')
                if pgllp.isValid():
                    self.oddz = pgllp
                    self.sprawdz_oddz()

        self.ui.pushButton_ls.clicked.connect(self.wybierz_ls)
        self.ui.pushButton_uz.clicked.connect(self.wybierz_uz)
        self.ui.pushButton_oddz.clicked.connect(self.wybierz_oddz)
        self.ui.pushButton_ok.clicked.connect(self.zatwierdz)
        self.ui.pushButton_anuluj.clicked.connect(self.porzuc)

    def wybierz_oddz(self):
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę ODDZ PGLLP',
                                                self.kat,
                                                "ESRI shp (*.shp)")[0]

        self.oddz = QgsVectorLayer(warstwa, "oddz_pgllp", "ogr")

        if not self.oddz.isValid():
            return

        QgsMessageLog.logMessage(
            'Wybrano warstwę oddziałów: ' + warstwa, 'Las-R', Qgis.Info
        )
        self.sprawdz_oddz()

    def wybierz_ls(self):
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę Ls',
                                                self.kat,
                                                "ESRI shp (*.shp)")[0]
        try:
            self.ls = QgsVectorLayer(warstwa, "ls", "ogr")
            self.ui.lineEdit_ls.setText(
                self.ls.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Nie udało się otworzyć podanej warstwy')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

    def wybierz_uz(self):
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę użytków',
                                                self.kat,
                                                "ESRI shp (*.shp)")[0]
        try:
            self.uz = QgsVectorLayer(warstwa, "uzytki", "ogr")

            self.ui.lineEdit_uz.setText(
                self.uz.dataProvider().dataSourceUri().split("|")[0])

        except:  # nopep8
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Bl�d')
            message.setText('Nie uda�o si� otworzy� podanej warstwy')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

    def wybierz_pole_uz(self, dostepne_pola):
        """Pyta uzytkownika ktora kolumne uzyc jako klase uzytku gruntowego."""
        from PyQt5.QtWidgets import QInputDialog
        if not dostepne_pola:
            return None
        opis = ('Wybierz kolumne zawierajaca klase uzytku gruntowego\n'
                '(szukana wartosc: "Ls"):')
        pole, ok = QInputDialog.getItem(
            self,
            'Kolumna uzytku gruntowego',
            opis,
            dostepne_pola,
            0,
            False
        )
        return pole if ok else None

    def sprawdz_oddz(self):
        """ Metoda sprawdza czy użyszkodnik nie chce dodać warstwy oddziałów
        dla całej PL, co spowoduje zawieszenie się QGISa
        """

        self.ui.label_uwagi.setText('')
        if self.oddz.extent().height() / 1000 < 155 and \
                self.oddz.extent().width() / 1000 < 155:
            self.ui.lineEdit_oddz.setText(
                self.oddz.dataProvider().dataSourceUri().split("|")[0]
            )
        else:
            self.ui.lineEdit_oddz.setText('')
            self.ui.label_uwagi.setText(
                'UWAGA '
                'Warstwa z zasięgiem oddziałów dla całej PL nie jest'
                ' obecnie wspierana.'
            )

    def zatwierdz(self):
        if '' not in [self.ui.lineEdit_ls.text(),
                      # self.ui.lineEdit_oddz.text(),
                      self.ui.lineEdit_odl.text(),
                      ] \
                and self.ui.lineEdit_odl.text().isdigit():
            self.kontynuuj = True
            self.hide()
        else:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Sprawdź wprowadzone dane, coś nie gra...')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

    def porzuc(self):
        self.kontynuuj = False
        self.hide()
