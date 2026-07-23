from math import sqrt
import os
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QVariant
from qgis.core import QgsGeometry, QgsFeature, QgsVectorFileWriter,\
    QgsSpatialIndex, QgsVectorLayer, Qgis, QgsProject, \
    QgsCoordinateReferenceSystem, QgsMessageLog, QgsFields, QgsField
import processing

from .ui.ui_shp_dosnapuj import Ui_Dialog
from .pw import PasekPostepu
from .funkcje import wyczysc_katalog_temp


class Dosnapuj:
    def __init__(self, fdz, fdzb, feat):
        self.fdz = fdz  # feature dzialki ewidencyjnej - orginał, linia
        # feature zbuforowanej granicy dzialki, kilka cm, poly
        self.fdzb = fdzb
        self.feat = feat  # feat fragmentu lini uzytku/wydzielenia do snapa

        self.snapowane = 0  # przysnapowane wierzcholki
        self.przedluzone = 0  # przedluzone odcinki
        self.niepoprawna = False  # flaga dla wystąpienia niepoprawnej geom

        # geom feat fragmentu linie
        self.fg = QgsGeometry().fromMultiPolylineXY(
            self.feat.geometry().asMultiPolyline())

        # przedluzenie poczatku lub konca lini
        self.pp_ext = False
        self.pk_ext = False

    def oblicz_odl(self, a, b):
        # zwraca odległość miedzy 2 podanymi QgsPointXY
        return sqrt((a.x()-b.x())**2 + (a.y()-b.y())**2)

    def spr_przedluzenie(self):
        # metoda sprawdza ktore konce stykaja sie z ramka dzialki i nalezy je
        # przedluzyc do granicy dzialki

        self.feat.geometry().convertToMultiType()
        # pkt poczatku i konca polilini
        self.pp = self.feat.geometry().asMultiPolyline()[0][0]
        self.pk = self.feat.geometry().asMultiPolyline()[0][-1]

        # geometrie dla pkt poczatkowego i koncowego
        pp_geom = QgsGeometry().fromPointXY(self.pp)
        pk_geom = QgsGeometry().fromPointXY(self.pk)

        if pp_geom.buffer(0.003, 1).intersects(self.fdzb.geometry()):
            # print('poczatek dotyka')
            self.pp_ext = True
        if pk_geom.buffer(0.003, 1).intersects(self.fdzb.geometry()):
            # print('koniec dotyka')
            self.pk_ext = True

        if self.pp_ext or self.pk_ext:
            return True
        return False

    def poly2line(self, geom):
        return QgsGeometry().fromPolylineXY(geom.asMultiPolygon()[0][0])

    def przedluz(self):  # noqa
        dz_ramka = QgsGeometry().fromPolylineXY(
            self.fdz.geometry().asMultiPolygon()[0][0]
        )
        # czasowa geom do wprowadzania nietrwalych zmian
        # fg = QgsGeometry().fromMultiPolylineXY(
        #     self.feat.geometry().asMultiPolyline())

        tab = []
        if self.pp_ext:
            tab.append('p')
        if self.pk_ext:
            tab.append('k')
        # print(tab)

        geom = False
        for t in tab:
            # temp zmienne do liczenia zmian
            _snap = 0
            _przed = 0

            fg = self.fg
            inter_beg = dz_ramka.intersection(fg)
            if t == 'p':
                fg = fg.extendLine(4, 0)  # przedluz linie na poczatku o 4 m
            else:
                fg = fg.extendLine(0, 4)  # przedluz linie na koncu o 4 m
            inter = dz_ramka.intersection(fg)
            # inter.convertToMultiType()
            geom = False
            # print(inter_beg.wkbType(), inter.wkbType())
            # if inter.isNull() or inter.wkbType() == 7:
            if inter_beg.wkbType() == inter.wkbType() or \
                    inter.wkbType() in [2, 7, ]:
                # przysnapuj pkt poczatkowy do ramki w najbliszym miejscu
                geom = self.r_snapuj(
                    self.fg, self.poly2line(self.fdz.geometry()), t)
                _snap += 1

            elif inter.wkbType() == 1:
                # przedłużoną odległość przytnij do granicy działki,
                # zbuforowaną o 3mm w celu uzyskania pewnosci ze przedluzone
                # linie napewno beda przecinac granice dzialki
                geom = fg.intersection(self.fdz.geometry().buffer(0.003, 1))
                _przed += 1

            elif inter.wkbType() == 4:
                # oblicz odległości do przecięć a nastepnie przedluz linie
                # tylko o polowę odległości miedzy 1 a 2 najblizszym pkt w celu
                # unikniecia przecinania lini w kilku miejscach z ramka dzialki
                if len(inter.asMultiPoint()) == 2:
                    geom = fg.intersection(
                        self.fdz.geometry().buffer(0.003, 1))
                    _przed += 1
                else:
                    odl = self.r_poprawna_odl(inter, t)
                    # skopiuj świeżą geometrię i przedłuż ją o wyliczoną odl
                    fg = self.fg
                    # fg = QgsGeometry().fromMultiPolylineXY(
                    #       self.feat.geometry().asMultiPolyline())
                    if odl is not False:
                        if t == 'p':
                            fg = fg.extendLine(odl, 0)
                        else:
                            fg = fg.extendLine(0, odl)
                        geom = fg.intersection(
                            self.fdz.geometry().buffer(0.003, 1))
                        _przed += 1

            # jezeli poprawiona geometria jest poprawna i dluższa od 0
            if geom is not False:
                if geom.isGeosValid() and geom.length() > 0:
                    self.fg = geom
                    if _przed > 0:
                        self.przedluzone += 1
                    if _snap > 0:
                        self.snapowane += 1
                else:
                    print('NIEPOPRAWNA GEOMETRIA!!!', self.feat.id())
                    self.niepoprawna = True

    def r_poprawna_odl(self, inter, poz):
        # oblicz odległości do przecięć a nastepnie przedluz linie
        # tylko o polowę odległości miedzy 1 a 2 najblizszym pkt w celu
        # unikniecia przecinania lini w kilku miejscach z ramka dzialki

        fg = QgsGeometry().fromMultiPolylineXY(
            self.feat.geometry().asMultiPolyline())
        pkt = False  # geometria do snapowania
        fg.convertToSingleType()
        if poz == 'p':
            pkt = QgsGeometry().fromPointXY(fg.asPolyline()[0])
        elif poz == 'k':
            pkt = QgsGeometry().fromPointXY(fg.asPolyline()[-1])
        else:
            print('nie rozpoznałem pozycji do przedlużenia, (p lub k)')
            return False

        # znajdz 2 najmniejsz odległości miedzy skrajnym pkt featura a
        # intersectami z granica poligonu
        odl = []
        for pi in inter.asMultiPoint():
            odl.append(self.oblicz_odl(pi, pkt.asPoint()))

        if len(odl) > 1:
            return (max(odl) - sorted(odl, reverse=True)[1]) / 2
        elif len(odl) == 1:
            return max(odl) + 0.001
        else:
            return False

    def r_snapuj(self, fgeom, dzgeom, poz):
        # metoda snapuje wskazana koncowke linie do granicy dzialki po
        # najblizszej odległości.
        # fgeom - geom liniowy do dociagniecia
        # dzgeom - geom liniowy granicy dzialki
        # poz - 'p' - pocztek, 'k' - koniec

        fgeom.convertToSingleType()
        pkt = False  # geometria do snapowania
        if poz == 'p':
            pkt = QgsGeometry().fromPointXY(fgeom.asPolyline()[0])
        elif poz == 'k':
            pkt = QgsGeometry().fromPointXY(fgeom.asPolyline()[-1])
        else:
            print('nie rozpoznałem pozycji do przedlużenia, (p lub k)')
            return False

        sline_geom = pkt.shortestLine(dzgeom)
        sline = sline_geom.asPolyline()
        spkt = ''
        # TODO: dodac przedluzenie do konca ktory jest snapowany bo czasami nie
        # lapie sie z granica dzialki
        if sline[0] != pkt.asPoint():
            spkt_ind = 0
        else:
            spkt_ind = 1

        sline_gfix = sline_geom.extendLine(0.003, 0.003)  # przedluz lin o 3mm
        spkt = sline_gfix.asPolyline()[spkt_ind]
        if poz == 'p':
            geom = QgsGeometry().fromPolylineXY([spkt, ] + fgeom.asPolyline())
        elif poz == 'k':
            geom = QgsGeometry().fromPolylineXY(fgeom.asPolyline() + [spkt, ])

        return geom


class Przyciagnij:
    # nazwa tymczasowego pola z id obiektu zrodlowego, uzywanego do
    # ponownego scalenia fragmentow tego samego obiektu po przebudowie
    # poligonow (zastepuje dawne, zaszyte na sztywno pole 'LANDID', ktore
    # nie istnieje w obecnym schemacie warstw)
    POLE_SRC_FID = '__SRCFID'
    # pole flagujace obiekty, dla ktorych nie udalo sie pewnie dopasowac
    # przebudowanej geometrii - dodawane z geometria oryginalna (przed
    # dociagnieciem), zeby nigdy po cichu nie zgubic obszaru
    POLE_WERYFIKUJ = 'DO_WERYF'

    def __init__(self, iface):
        # iface moze byc None (uzycie headless/wsadowe, np. z poziomu
        # orkiestratora hierarchii warstw) - wtedy pomijamy pasek postepu i
        # komunikaty w messageBar, dzialanie liczace pozostaje identyczne
        self.iface = iface
        self.dz = False
        self.snap = False
        self.snap_dist = 0.1  # ten snap jest metrach

        self.kat = ''
        self.tempkat = ''
        self.wyjscie_path = None  # None = domyslnie <kat>/DOCIAGNIETA.shp

        # warstwy niezbedne do snapowania powstale w processingu
        self.snap_lines = False
        self.dz_lines = False
        self.dz_buffer = False

        # warstwa z bledami liniowymi (niedosnapowanie)
        self.b_lin = []
        self.b_poly = 0  # zliczona liczba błędów generowania poly
        self.b_inter = 0  # zliczona liczba błędów nakładania

        self.popr_feat = []  # lista z popr poly, z dopisanymi attr

        self.fields = []  # tab z definicjami pol z org warstwy do dopisana
        self.postep = None

    def _postep(self, wartosc):
        if self.postep is not None:
            self.postep.setValue(wartosc)

    def ustaw_dane_bezposrednio(self, dz_path, snap_path, snap_dist=0.1,
                                wyjscie_path=None, tempkat=None):
        """Programowe (bez GUI) ustawienie danych wejsciowych - odpowiednik
        pobierz_dane()+sprawdz_dane(), do uzycia z poziomu skryptow/
        orkiestratora, np. przy naprawie calego lancucha warstw.

        dz_path - sciezka do warstwy nadrzednej (do ktorej dociagamy)
        snap_path - sciezka do warstwy podrzednej (dociaganej)
        snap_dist - odleglosc dociagania granicy [m]
        wyjscie_path - sciezka wyjsciowego shp, domyslnie <kat_dz>/DOCIAGNIETA.shp
        tempkat - wlasny katalog roboczy; domyslnie <kat_dz>/temp. Przy
            wielokrotnym wywolywaniu w petli (np. orkiestrator lancucha
            warstw) KAZDE wywolanie powinno dostac inny tempkat - QGIS/OGR
            trzyma uchwyty do plikow posrednich nawet po zakonczeniu
            przetwarzania, a Windows blokuje nadpisywanie otwartych plikow,
            wiec wspoldzielony katalog roboczy miedzy kolejnymi parami
            powoduje bledy zapisu.
        """
        self.snap_dist = snap_dist
        self.wyjscie_path = wyjscie_path

        self.dz = QgsVectorLayer(dz_path, 'dzewid', 'ogr')
        if not self.dz.isValid():
            print('BŁĄD: niepoprawna warstwa nadrzędna: ' + dz_path)
            return False

        self.snap = QgsVectorLayer(snap_path, 'snap', 'ogr')
        if not self.snap.isValid():
            print('BŁĄD: niepoprawna warstwa do dociągnięcia: ' + snap_path)
            return False

        sciezka = self.dz.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = tempkat or os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.makedirs(self.tempkat)

        self.fields = QgsFields(self.snap.dataProvider().fields())
        self.fields.append(QgsField(self.POLE_SRC_FID, QVariant.LongLong))
        self.fields.append(QgsField(self.POLE_WERYFIKUJ, QVariant.Int))

        return True

    def pobierz_dane(self):
        # pobranie lokalizacji warstwy dociaganej oraz dz ewid od uzytkownika
        # oraz wielkosci bufora snapowania domyslnie 10 cm
        self.pd = PobierzDane()
        self.pd.exec_()
        if self.pd.porzucone:
            return False
        return True

    def sprawdz_dane(self):
        # sprawdza czy wskazane dane od użytkownika mają poprawną geometrię i
        # nadają sie do przetwarzanie przez processing
        if self.pd.ui.lineEdit_cm.text().isdigit():
            self.snap_dist = int(self.pd.ui.lineEdit_cm.text()) / 100

        # nie sprawdzamy czy pliki istnieją, taka kontrola była w formularzu
        self.dz = QgsVectorLayer(self.pd.ui.lineEdit_dz.text(),
                                 'dzewid', 'ogr')
        if not self.dz.isValid():
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Niepoprawna warstwa działek',
                Qgis.Critical,
                10
            )
            return False

        self.snap = QgsVectorLayer(self.pd.ui.lineEdit_snap.text(),
                                   'snap', 'ogr')
        if not self.snap.isValid():
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Niepoprawna warstwa do dosnapowania',
                Qgis.Critical,
                10
            )
            return False

        # ustaw katalogi robocze i stworz katalog temp
        sciezka = self.dz.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)

        self.fields = QgsFields(self.snap.dataProvider().fields())
        self.fields.append(QgsField(self.POLE_SRC_FID, QVariant.LongLong))
        self.fields.append(QgsField(self.POLE_WERYFIKUJ, QVariant.Int))

        if self.iface is not None:
            self.postep = PasekPostepu(self.iface).stworz_pasek(
                'Snapowanie...')
        return True

    def _przetworz(self):  # noqa
        # przetworzenie obu warstw przez processing w celu rozbicia na czesci
        # uzytkowe, oraz zbudowanie niezbędnej struktury

        processing.run("native:multiparttosingleparts", {
                        'OUTPUT': os.path.join(
                            self.tempkat, '__snap_singleparts.shp'),
                        'INPUT': self.snap
                        })

        if not os.path.exists(os.path.join(self.tempkat,
                                           '__snap_singleparts.shp')):
            return False

        self._postep(5)
        processing.run(
            'native:polygonstolines',
            {'INPUT': os.path.join(self.tempkat, '__snap_singleparts.shp'),
             'OUTPUT': os.path.join(self.tempkat,
                                    '__snap_singleparts_lines.shp')
             }
        )

        if not os.path.exists(os.path.join(self.tempkat,
                                           '__snap_singleparts_lines.shp')):
            return False

        self._postep(10)
        processing.run(
            'native:polygonstolines',
            {'INPUT': self.dz,
             'OUTPUT': os.path.join(self.tempkat, '__dz_lines.shp')
             }
        )

        if not os.path.exists(os.path.join(self.tempkat, '__dz_lines.shp')):
            return False
        self.dz_lines = QgsVectorLayer(os.path.join(self.tempkat,
                                                    '__dz_lines.shp'),
                                       'dz_lines', 'ogr')

        self._postep(15)
        processing.run(
            'native:buffer',
            {'OUTPUT': os.path.join(self.tempkat,
                                    '__dz_lines_buffer_undiss.shp'),
             'INPUT': os.path.join(self.tempkat, '__dz_lines.shp'),
             'DISTANCE': self.snap_dist,
             'SEGMENTS': 1,
             'END_CAP_STYLE': 1,
             'JOIN_STYLE': 1,
             'MITER_LIMIT': 1,
             'DISSOLVE': True,
             }
        )

        self._postep(20)
        processing.run("native:multiparttosingleparts", {
            'INPUT': os.path.join(self.tempkat,
                                  '__dz_lines_buffer_undiss.shp'),
            'OUTPUT': os.path.join(self.tempkat, '__dz_lines_buffer.shp'),
                        })

        if not os.path.exists(os.path.join(self.tempkat,
                                           '__dz_lines_buffer.shp')):
            return False

        self.dz_buffer = QgsVectorLayer(os.path.join(self.tempkat,
                                                     '__dz_lines_buffer.shp'),
                                        'dz_buffer', 'ogr')

        self._postep(25)
        processing.run(
            'native:difference',
            {'INPUT': os.path.join(self.tempkat,
                                   '__snap_singleparts_lines.shp'),
             'OVERLAY': os.path.join(self.tempkat, '__dz_lines_buffer.shp'),
             'OUTPUT': os.path.join(self.tempkat,
                                    '__snap_singleparts_lines_difference.shp'),
             }
        )

        if not os.path.exists(os.path.join(
                self.tempkat, '__snap_singleparts_lines_difference.shp')):
            return False

        self._postep(30)
        processing.run("native:multiparttosingleparts", {
            'OUTPUT': os.path.join(
                self.tempkat,
                '__snap_singleparts_lines_difference_singleparts.shp'),
            'INPUT': os.path.join(self.tempkat,
                                  '__snap_singleparts_lines_difference.shp'),
                        })

        if not os.path.exists(
            os.path.join(
                self.tempkat,
                '__snap_singleparts_lines_difference_singleparts.shp')):
            return False

        self._postep(35)
        processing.run(
            "qgis:deleteduplicategeometries",
            {'INPUT': os.path.join(
                 self.tempkat,
                 '__snap_singleparts_lines_difference_singleparts.shp'),
             'OUTPUT': os.path.join(
                 self.tempkat,
                 '__snap_singleparts_lines_difference_singleparts_rmdup.shp'),
             }
        )

        if not os.path.exists(
            os.path.join(
                self.tempkat,
                '__snap_singleparts_lines_difference_singleparts_rmdup.shp')):
            return False

        self.snap_lines = QgsVectorLayer(
            os.path.join(
                self.tempkat,
                '__snap_singleparts_lines_difference_singleparts_rmdup.shp'),
            'snap_lines', 'ogr')

        return True

    def podociagaj(self):
        ''' Metoda dociąga/przedłuża końcowe pkt lini z warstwy snap_linie
        tak aby stykały się z granicami dzewid,
        '''
        self._postep(40)
        _dz_si = QgsSpatialIndex(self.dz)
        _dzb_si = QgsSpatialIndex(self.dz_buffer)

        snapy = 0
        przedl = 0

        feats_popr = []  # lista podociaganych featurkow
        for feat in self.snap_lines.getFeatures():
            # znajdz dzialke na ktorej lezy dany feature
            ids_dz = _dz_si.intersects(feat.geometry().boundingBox())
            if len(ids_dz) == 0:
                # jezeli zadna dz sie nie przecina olewamy featura
                self.b_lin.append(feat)
                continue
            elif len(ids_dz) == 1:
                fdz = next(self.dz.getFeatures(ids_dz))
            else:
                for id in ids_dz:
                    fdz = self.dz.getFeature(id)
                    if feat.geometry().buffer(0.003, 1).intersects(
                            fdz.geometry()):
                        break

            # znajdz bufor dz z ktora styka sie dany feature
            ids_dz = _dzb_si.intersects(feat.geometry().boundingBox())
            if len(ids_dz) == 0:
                # jezeli zadna dz sie nie przecina olewamy featura
                self.b_lin.append(feat)
                continue
            elif len(ids_dz) == 1:
                fdzb = next(self.dz_buffer.getFeatures(ids_dz))
            else:
                for id in ids_dz:
                    fdzb = self.dz_buffer.getFeature(id)
                    if feat.geometry().buffer(0.003, 1).intersects(
                            fdzb.geometry()):
                        break

            s = Dosnapuj(fdz, fdzb, feat)
            if s.spr_przedluzenie():
                s.przedluz()
                snapy += s.snapowane
                przedl += s.przedluzone

            featp = QgsFeature()
            featp.setGeometry(s.fg)
            # dodaj do list poprawnych, potem doda sie to do warstwy granic
            # liniowych dzewid i na podstwaie tego stworzy sie poprawne
            # poligony do projektu
            feats_popr.append(featp)

        # dodaj przysnapowane featury do warstwy granic dzialek
        self.dz_lines.startEditing()
        self.dz_lines.dataProvider().addFeatures(feats_popr)
        self.dz_lines.commitChanges()
        # izapisz je w osobnej warstwie
        slyr = QgsVectorLayer(
            'LineString?crs=epsg:2180&index=yes&field=ID:integer',
            '__SNAPOWANE', 'memory')
        slyr.dataProvider().addFeatures(feats_popr)
        crs = QgsCoordinateReferenceSystem("epsg:2180")
        QgsVectorFileWriter.writeAsVectorFormat(
            slyr,
            os.path.join(os.path.join(self.tempkat, "snapped.shp")),
            "UTF-8",
            crs,
            "ESRI Shapefile")
        if self.iface is not None:
            self.iface.addVectorLayer(
                os.path.join(os.path.join(self.tempkat, "snapped.shp")),
                'snapped', 'ogr')

        # jezeli zlokalizowalismy bledne snapowania, pokaz uzyszkodnikowi
        QgsProject.instance().addMapLayer(self.dz_lines)
        print('lini blednych: ' + str(len(self.b_lin)))
        print('poprawionych lini: ' + str(len(feats_popr)))
        if len(self.b_lin) > 0:
            blyr = QgsVectorLayer('LineString?crs=epsg:2180&index=yes'
                                  '&field=ID:integer',
                                  '__BLEDY_SNAPOWANIA', 'memory')
            blyr.dataProvider().addFeatures(self.b_lin)
            QgsProject.instance().addMapLayer(blyr)

        QgsMessageLog.logMessage(
            'Dosnapowano: '+str(snapy), 'LAS-R', Qgis.Info)
        QgsMessageLog.logMessage(
            'Przedłużono: '+str(przedl), 'LAS-R', Qgis.Info)

    def stworz_poligony(self):  # noqa
        self._postep(45)

        # zwezlowanie (noding) linii: tam gdzie linie sie krzyzuja/dotykaja
        # ma powstac wspolny wierzcholek. Dawniej robil to grass7:v.clean,
        # ale GRASS bywa niedostepny w trybie headless/wsadowym - unaryUnion
        # na liniach daje ten sam efekt natywnie przez GEOS (wezluje na
        # przecieciach i usuwa nakladajace sie duplikaty odcinkow), bez
        # zewnetrznej zaleznosci.
        linie = [f.geometry() for f in self.dz_lines.getFeatures()
                 if f.geometry() and not f.geometry().isEmpty()]
        zwezlowane = QgsGeometry.unaryUnion(linie)

        wezl_lyr = QgsVectorLayer('LineString?crs=epsg:2180', '__wezlowane',
                                  'memory')
        wezl_feats = []
        try:
            czesci = zwezlowane.asGeometryCollection()
        except Exception:
            czesci = [zwezlowane]
        for czesc in czesci:
            if czesc.isEmpty():
                continue
            f = QgsFeature()
            f.setGeometry(czesc)
            wezl_feats.append(f)
        wezl_lyr.dataProvider().addFeatures(wezl_feats)

        self._postep(55)
        p_lyr = processing.run('qgis:polygonize', {
            'INPUT': wezl_lyr,
            'KEEP_FIELDS': False,
            'OUTPUT': os.path.join(self.tempkat,
                                   '__polygonizer.shp')
        })

        p_lyr = QgsVectorLayer(os.path.join(self.tempkat, '__polygonizer.shp'),
                               'poligony_raw', 'ogr')
        p_si = QgsSpatialIndex(p_lyr)
        s_feat = {f.id(): f for f in p_lyr.getFeatures()}

        sl = {}  # sl z {snap_id: poly_id}
        l_poly = []  # lista ze spasowanymi poly
        b_poly = []  # tab z feat do sprawdzenia

        snap_single = QgsVectorLayer(
            os.path.join(self.tempkat, '__snap_singleparts.shp'),
            'snap_single', 'ogr')

        self._postep(60)
        for f in snap_single.getFeatures():
            ids = p_si.intersects(f.geometry().boundingBox())
            # tab z poly przecinajacymi sie z org uzytkiem, wybierzemy, tego
            # ktory ma najwieszka pow przeciecia
            tab = []
            for id in ids:
                fp = s_feat[id]
                tab.append([
                    fp.id(),
                    fp.geometry().intersection(f.geometry()).area(),
                    f.geometry().area()
                ])

            tab.sort(reverse=True, key=lambda x: x[1])

            # jak się nic nie przecina, pomin featurka - ale dodaj go do
            # wyniku z oryginalna geometria i flaga do weryfikacji, zamiast
            # po cichu gubic ten obszar
            if len(tab) < 1:
                b_poly.append(f)
                self._dodaj_fallback(f)
                continue

            # zdegenerowany (zerowej powierzchni) obiekt zrodlowy - nie da
            # sie dla niego policzyc sensownego stosunku pokrycia, oznacz do
            # weryfikacji zamiast dzielic przez zero
            if round(f.geometry().area(), 8) == 0:
                b_poly.append(f)
                continue

            fp = s_feat[tab[0][0]]  # pobierz dosnapowany feat o najw pow inter
            flaga = True  # domyslnie feat zawsze dodajemy do sprawdzenia

            # czasami bo wycieciu wasa z jednego uzytku robi sie kilka
            pow_zb = 0.0
            poly_ok = []  # tab z poprawnymi rozdzielonymi uztykami

            # przypadek gdy wszystko jest ok
            if 1.1 > (round(tab[0][1], 8)/round(tab[0][2], 8)) >= 0.9 and \
                    1.1 > tab[0][1]/fp.geometry().area() > 0.9:
                if tab[0][0] not in l_poly:
                    if f.id() not in sl:
                        sl[f.id()] = []
                    sl[f.id()].append(tab[0][0])
                    l_poly.append(fp)
                    self._dodaj_poly(f, fp)
                    flaga = False

            # przypadek gdy uzytek polaczony byl w jeden przez was ktory po
            # snapowaniu wyleciał
            elif 0.9 > (tab[0][1]/tab[0][2]) and len(tab) > 1:
                isn = 0
                while round(pow_zb, 8) < round(f.geometry().area(), 8):

                    if len(tab) - 1 <= isn:
                        break

                    t = tab[isn]
                    fp = s_feat[t[0]]
                    if fp.geometry().area() + pow_zb < \
                            1.05 * f.geometry().area() and \
                            t[1]/fp.geometry().area() > 0.95:
                        pow_zb += fp.geometry().area()

                        if f.id() not in sl:
                            sl[f.id()] = []
                        sl[f.id()].append(t[0])
                        poly_ok.append(fp)
                    else:
                        if isn == 0:
                            flaga = True
                        break
                    isn += 1

                if len(poly_ok) > 0:
                    for fp in poly_ok:
                        l_poly.append(fp)
                        self._dodaj_poly(f, fp)

                    # jezeli znalezlismy uzytek rozbity na czesci nie dodajemy
                    # go do sprawdzenia o ile roznica nie jest wieksze od pow
                    # orginału o 10 %
                    if 1.1 > pow_zb/f.geometry().area() > 0.9:
                        flaga = False
                    else:
                        flaga = True

            # jezeli pow przeciecia jest ok ale powierzchnia dosnapowanego
            # featurka jest wieksza, dodaj do sprawdzenia...
            elif tab[0][1]/fp.geometry().area() < 0.9 and \
                    1.1 > tab[0][1]/tab[0][2] > 0.9 and len(tab) == 1:
                flaga = True

            if flaga:
                b_poly.append(fp)
                # jezeli dla tego obiektu zrodlowego nic nie zostalo dodane
                # do wyniku (niepewne dopasowanie), dodaj go z oryginalna
                # geometria i flaga do weryfikacji - nie tracimy obszaru
                if f.id() not in sl:
                    self._dodaj_fallback(f)

        # plyr = QgsVectorLayer('Polygon?crs=epsg:2180&index=yes',
        #                       '__POLY_OK', 'memory')
        # plyr.dataProvider().addFeatures(l_poly)
        # QgsProject.instance().addMapLayer(plyr)

        if len(b_poly) > 0:
            self.b_poly = len(b_poly)
            bpoly = QgsVectorLayer('Polygon?crs=epsg:2180&index=yes&'
                                   'field=id:integer&field=uwaga:string',
                                   '__POLY_BLEDY', 'memory')
            bpoly.dataProvider().addFeatures(b_poly)
            QgsProject.instance().addMapLayer(bpoly)

        # sprawdz czy wygenerowane poprawne feats nie nakładają się na siebie
        self._postep(85)
        pop_si = QgsSpatialIndex()
        pop_sl = {}
        for i, feat in enumerate(self.popr_feat):
            pop_sl[i] = feat
            pop_si.addFeature(i, feat.geometry().boundingBox())

        inter_list = []  # lista z feat inter do wyswietlenia dla uzytkownika
        for ind, fe in pop_sl.items():
            ids = pop_si.intersects(fe.geometry().boundingBox())
            if len(ids) == 1:
                continue

            for id in ids:
                if id == ind:
                    continue
                inter = fe.geometry().intersection(pop_sl[id].geometry())
                if inter.area() > 0:
                    fint = QgsFeature()
                    fint.setGeometry(inter)
                    inter_list.append(fint)

        if len(inter_list) > 0:
            self.b_inter = len(inter_list)
            ilyr = QgsVectorLayer('Polygon?crs=epsg:2180&index=yes'
                                  '&field=id:integer',
                                  '__SNAP_overlaps', 'memory')
            ilyr.dataProvider().addFeatures(inter_list)
            QgsProject.instance().addMapLayer(ilyr)

    def _dodaj_poly(self, f, fp, weryfikuj=0):
        feat = QgsFeature()
        feat.setGeometry(fp.geometry())
        feat.setFields(self.fields)
        feat.setAttributes(f.attributes() + [f.id(), weryfikuj])
        self.popr_feat.append(feat)

    def _dodaj_fallback(self, f):
        """Gdy nie udalo sie pewnie dopasowac obiektu do zadnej przebudowanej
        geometrii - dodaj go do wyniku z ORYGINALNA (sprzed dociagniecia)
        geometria i flaga DO_WERYF=1, zamiast po cichu tracic ten obszar.
        Obiekt nadal trafia tez do b_poly/warstwy bledow do przegladu."""
        self._dodaj_poly(f, f, weryfikuj=1)

    def pokaz_warstwy(self):
        # metoda dodja warstwy do TOC i zapisuje na dysku, wyswietla niezbeden
        # informacje na temat bledow snapowania

        self._postep(95)
        plyr = QgsVectorLayer('Polygon?crs=epsg:2180&index=yes',
                              '__POLY_OK', 'memory')
        plyr.startEditing()
        plyr.dataProvider().addAttributes(self.fields)
        plyr.updateFields()
        plyr.dataProvider().addFeatures(self.popr_feat)
        plyr.commitChanges()

        wyjscie = self.wyjscie_path or os.path.join(self.kat,
                                                     "DOCIAGNIETA.shp")
        wyjscie_tmp = os.path.join(self.tempkat, '__dociagnieta_dissolve.shp')
        os.makedirs(os.path.dirname(wyjscie), exist_ok=True)

        # scal fragmenty nalezace do tego samego obiektu zrodlowego (ten
        # sam POLE_SRC_FID) - to zastepuje dawne dissolve po polu 'LANDID',
        # ktore nie istnieje w obecnym schemacie warstw
        processing.run("native:dissolve", {
            'INPUT': plyr,
            'FIELD': [self.POLE_SRC_FID],
            'OUTPUT': wyjscie_tmp,
        })

        # usun tymczasowe pole pomocnicze z wyniku koncowego
        processing.run("native:deletecolumn", {
            'INPUT': wyjscie_tmp,
            'COLUMN': [self.POLE_SRC_FID],
            'OUTPUT': wyjscie,
        })

        self.dociag = QgsVectorLayer(wyjscie, "DOCIAGNIETA", 'ogr')

        if self.iface is not None:
            QgsProject.instance().addMapLayer(self.dociag)
            self.iface.messageBar().clearWidgets()
            if self.b_inter == 0 and self.b_poly == 0:
                self.iface.messageBar().pushMessage(
                    'OK',
                    'Snapowanie zakończone sukcesem, brak uwag!',
                    Qgis.Success,
                    0
                )
            else:
                self.iface.messageBar().pushMessage(
                    'OK z problemami',
                    'Snapowanie zakończone sukcesem, błędy poligonowe: ' +
                    str(self.b_poly) + ', błędy nakładania: ' +
                    str(self.b_inter),
                    Qgis.Warning,
                    0
                )
        else:
            print('Dociągnięto -> %s (błędy poligonowe: %d, '
                  'błędy nakładania: %d)' %
                  (wyjscie, self.b_poly, self.b_inter))

        # posprzataj pliki posrednie z tempkat - ale zostaw "__dz_lines" i
        # "snapped", bo te dwie warstwy zostaly dodane do TOC (self.dz_lines
        # wyzej, "snapped" jako osobna warstwa) i nadal wskazuja na pliki
        # w tym katalogu
        wyczysc_katalog_temp(
            self.tempkat, zachowaj_nazwy=['__dz_lines', 'snapped'])


class PobierzDane(QDialog):
    def __init__(self):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # katalog który będzie uzupełniony po pierwszym wskazaniu warstwy, bazy
        self.kat = ''

        # wartosc True jezeli uzytkownik zrezygnowal z przetwarzania
        self.porzucone = True

        # trigger do sprawdzenia poprawnosci wpisanych danych przez
        # uzyszkodnika
        self.valid = False

        # sygnały
        self.ui.pushButton_ok.clicked.connect(self.sprawdz_ok)
        self.ui.pushButton_cancel.clicked.connect(self.porzuc)
        self.ui.pushButton_snap.clicked.connect(self.kat_snap)
        self.ui.pushButton_dz.clicked.connect(self.kat_dz)

        # znajdz warstwy w TOC

        sc_d = ''
        sc_l = ''
        for key, lyr in QgsProject.instance().mapLayers().items():
            if key[:5] == 'DZKAT':
                d = lyr
                sc_d = d.dataProvider().dataSourceUri().split("|")[0]
                self.kat = os.path.dirname(sc_d)
            if key[:2] == 'LS':
                ls = lyr
                sc_l = ls.dataProvider().dataSourceUri().split("|")[0]
                self.kat = os.path.dirname(sc_l)

        self.ui.lineEdit_dz.setText(sc_d)
        self.ui.lineEdit_snap.setText(sc_l)

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if os.path.isfile(self.ui.lineEdit_snap.text()) and \
                os.path.isfile(self.ui.lineEdit_dz.text()):
            self.valid = True
            self.porzucone = False
            self.hide()
        else:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText(
                'Nie udało się odnaleźć wszystkich podanych plików!')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

    def kat_snap(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż plik z dz ewid',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_snap.setText(sc)

    def kat_dz(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż plik z dz ewid',
                                           self.kat,
                                           "ESRI Shapefile (*.shp)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_dz.setText(sc)
