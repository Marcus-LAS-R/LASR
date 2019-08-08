import os
import glob
import platform
from datetime import datetime
from collections import Counter, defaultdict
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from PyQt5.QtCore import QVariant
from qgis.core import QgsSpatialIndex, QgsField, QgsFeature, Qgis, \
    QgsVectorLayer, QgsMessageLog, QgsProject, QgsWkbTypes, QgsFields, \
    QgsFeatureRequest, QgsVectorFileWriter, QgsCoordinateReferenceSystem, \
    QgsGeometry

from .baza_wrapper import Baza
from .baza_przetworz import Przetworz
from .funkcje import usun_wasy, isNone
from .ui.ui_sprawdz_ls import Ui_Dialog
from .pw import PasekPostepu
# import processing  # import przeniesiony do metody - pytest probemy!
# import subprocess  # import niezbedny przy wysietleniu raportu na maszynach
#                      bez windowsa


class recursivedefaultdict(defaultdict):
    def __init__(self):
        self.default_factory = type(self)


class SprawdzLs(object):
    def __init__(self, i):
        self.iface = i

    def sprawdz_warstwy(self):
        k = False  # klasouzytki - warstwa
        d = False  # dzialki - warstwa

        QgsMessageLog.logMessage(
            '\n-----[ SPRAWDZENIE LS ]-----', 'Las-R', Qgis.Info
        )

        for key, lyr in QgsProject.instance().mapLayers().items():
            if key[:5] == 'DZKAT':
                d = lyr
            if key[:3] == 'KLU':
                k = lyr

        self.a = AnalizujKlus(self.iface, k, d)
        return True

    def wczytaj(self):
        if not self.a.pobierz_dane_od_uzytkownika():
            return False
        self.postep = PasekPostepu(self.iface).stworz_pasek('Generowanie Ls')
        self.a.przetworz()
        self.postep.setValue(5)
        return True

    def sprawdz(self):
        if not self.a.sprawdz_warunki():
            return False
        return True

    def przygotuj(self):
        self.postep.setValue(10)
        self.a.przygotuj_tabele()
        self.a.przygotuj_do_analizy()
        if not self.a.geop_przetworz():
            return False
        self.a.zaladuj_strukture()
        self.postep.setValue(15)
        return True

    def przetworz(self):
        self.a.przetworz_strukture()
        self.postep.setValue(70)
        self.a.generuj_warstwy()
        self.postep.setValue(80)
        self.a.generuj_raport()
        self.postep.setValue(100)

        self.iface.messageBar().clearWidgets()

        self.iface.messageBar().pushMessage(
            'OK', 'Przetworzono warstwę KLU!', Qgis.Success, 10
        )

        QgsMessageLog.logMessage(
            '\n-----[ KONIEC ]-----', 'Las-R', Qgis.Info
        )

        message = QMessageBox()
        message.setIcon(QMessageBox.Information)
        message.setWindowTitle('Raport')
        message.setText('Czy wyświetlić raport z generowania Ls-ów?')
        message.addButton(u"Zamknij", QMessageBox.ActionRole)
        message.addButton(u"Zamknij i pokaż raport", QMessageBox.ActionRole)
        pok_rap = message.exec_()

        if pok_rap == 1:
            if platform.system()[:3] == 'Win':
                os.startfile(self.a.rap_sc)
            else:
                import subprocess
                subprocess.call(['kate', self.a.rap_sc])


class AnalizujKlus(object):
    def __init__(self, i, k, d):
        self.iface = i
        self.klu = k
        self.dzkat = d

        # katalog gdzie bedą zapisywane wszystkie warstwy i raporty
        # uzupelniany w metodzie generuj_warstwy
        self.kat = ''

        # slownik z obiektami PrzetworzKlu dla każdego parcelid z warswy
        # działek, całość zestawiana jest w metodzie zaladuj_strukture
        self.strukt = {}

        # lista parcelid, dla ktorych PrzetworzKlu zwróciło False w metodzie
        # is_valid() - raportowanie dla użytkownia, brak przetworzenia
        self.bledne = []

        self.lyrw = False  # warstwa wyjsciowa
        self.bledy_topo = []  # lista feats, ktore przecinaja sie z innymi
        self.iatr = False  # indeks pól w warstwie wyjsciowej
        self.county = ''  # kod wojewodztwa
        self.district = ''  # kod powiatu
        self.dz_nieles = []  # lista dzialek nielesnych

        # self.indeks = QgsSpatialIndex()
        self.sf = {}  # slownik z singleparts features w postaci{id: feature, }
        self.sl_sf_na_dzkat = {}  # slownik {PARCELID: [id1, id2, ..]}

        # sl z wartosciami klu i odpowiadajacymi mu au sq w postaci tablicy
        # {'RV': ['R', 'V'], ...}
        self.sl_klu = {}

        self.czas = datetime.now().isoformat(
                        ).replace(":", "")[:-7].replace('-', '')

        self.kolumny_dz = [
            QgsField("COUNTY", QVariant.String, len=2),
            QgsField("DISTRICT", QVariant.String, len=2),
            QgsField("MUNICIP", QVariant.String, len=3),
            QgsField("COMMUNITY", QVariant.String, len=4),
            QgsField("PARCELNR", QVariant.String, len=20),
            QgsField("PARCELID", QVariant.String, len=50),
            QgsField("GRP", QVariant.String, len=2),
            QgsField("ARK", QVariant.String, len=12),
            QgsField("NIELES", QVariant.String, len=3),
            QgsField("UWAGI", QVariant.String, len=150),
            QgsField("PARCEL_AR", QVariant.Double, "double", 10, 4),
            QgsField("PARCEL_POW", QVariant.Double, "double", 10, 4),
        ]

        self.kolumny_ls = [
            QgsField("AU", QVariant.String, len=10),
            QgsField("SQ", QVariant.String, len=10),
            QgsField("SPRAWDZ", QVariant.String, len=150),
            QgsField("LANDID", QVariant.String, len=50),
            QgsField("LAND_AR", QVariant.Double, "double", 10, 4),
            QgsField("LAND_POW", QVariant.Double, "double", 10, 4),
        ]

    def pobierz_dane_od_uzytkownika(self):
        self.dd = PobierzDane(self.klu, self.dzkat)
        self.dd.exec_()

        if self.dd.kontynuuj:
            return True
        return False

    def przetworz(self):
        self.klu = QgsVectorLayer(self.dd.ui.lineEdit_klu.text(), 'klu', 'ogr')
        self.dzkat = QgsVectorLayer(self.dd.ui.lineEdit_dzkat.text(),
                                    'dz', 'ogr')

        self.klu.dataProvider().setEncoding('UTF-8')
        # sprawdzenie czy warstwy sa poprawne znajduje sie w metodzie
        # sprawdz_warunki ponizej, ktora powinna byc uruchomiona po tej.

        # w zaleznosci od platformy znajdz odpowiednie bazy taksatora
        if platform.system()[:3] == 'Win':
            self.bazy = glob.glob(
                os.path.join(self.dd.ui.lineEdit_bazy.text(),
                             '*.mdb'))
        else:
            self.bazy = glob.glob(
                os.path.join(self.dd.ui.lineEdit_bazy.text(),
                             '*.sqlite'))

        self.typ = self.dd.ui.comboBox_ident.currentText()[:3]
        self.wl = self.dd.ui.comboBox_wlas.currentText()[:2]
        self.landid = self.dd.ui.comboBox_landid.currentText()
        self.sq = self.dd.ui.comboBox_sq.currentText()
        self.au = self.dd.ui.comboBox_au.currentText()

        # Pobierz dane z baz danych
        self.uzytki = []
        self.wlasnosci = []

        QgsMessageLog.logMessage(
            'Znaleziono bazy: '+', '.join(self.bazy),
            "Las-R",
            Qgis.Info
        )
        for baza in self.bazy:
            b = Baza(baza)
            if b.polacz():
                self.uzytki += b.uzytki()
                self.wlasnosci += b.wlasnosci()
            else:
                QgsMessageLog.logMessage(
                    'Nie udało połączyć się z: ' + baza,
                    "Las-R",
                    Qgis.Warning
                )
                self.iface.messageBar.pushWarning(
                    'Uwaga',
                    'Nie udało się odczytać bazy: ' +
                    baza,
                    Qgis.Warning
                )

    def przygotuj_tabele(self):
        QgsMessageLog.logMessage(
            'Przetwarzam dane z bazy danych...', 'Las-R', Qgis.Info
        )
        self.p = Przetworz()
        self.p.dodaj_uzytki(self.uzytki)
        self.p.dodaj_wlasnosci(self.wlasnosci)
        self.p.przetworz_dzialki()
        self.p.przetworz_uzytkowanie()

    def sprawdz_warunki(self):
        """Sprawdz czy warstwy maja odpowiednie struktury"""
        if not self.klu.isValid() or not self.dzkat.isValid():
            return False

        if len([x.name() for x in self.kolumny_dz
                if x.name() in self.dzkat.dataProvider().fields()]) == 12:
            return False

        # sprawdz czy w dzkat nie ma zdublowanych wartosci w parcelid
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                               ).setSubsetOfAttributes(
                                                   ['PARCELID'],
                                                   self.dzkat.fields()
                                               )
        policz = Counter([x['PARCELID'] for x in
                          self.dzkat.getFeatures(request)]).most_common()
        nad = [isNone(x[0]) for x in policz if x[1] > 2]

        if len(nad) > 0:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'Uwaga',
                'Znaleziono zdublowanych działek w wartwie DZKAT: \n' +
                str(len(nad)) + '    (patrz log LAS-R)',
                Qgis.Critical,
                0
            )
            QgsMessageLog.logMessage(
                '   Znaleziono zdublowanych działek w shp: \n' +
                '(puste lista poniżej oznacza, niewypełnioną kolumnę '
                'PARCELID)\n' +
                '\n'.join(nad) + '\n---------------------',
                'Las-R',
                Qgis.Critical
            )
            return False

        return True

    def przygotuj_do_analizy(self):
        """ W zaleznosci od wyboru uzytkownika robimy dissolve po au i sq albo
        LANDID. W drugim przypadku dodajemy brakujace pola sq i au,
        uzupelniamy je ze slownika i kontynuujemy sciezke programu"""

        pola = [x.name() for x in self.klu.dataProvider().fields()]
        pola_dodaj = []
        if 'SQ' not in pola:
            pola_dodaj.append(QgsField("SQ", QVariant.String, len=10))
        if 'AU' not in pola:
            pola_dodaj.append(QgsField("AU", QVariant.String, len=10))
        if 'KLU' not in pola:
            pola_dodaj.append(QgsField("KLU", QVariant.String, len=15))

        if len(pola_dodaj) > 0:
            self.klu.startEditing()
            self.klu.dataProvider().addAttributes(pola_dodaj)
            self.klu.updateFields()
            self.klu.commitChanges()

        # jezeli wybrano LANDID
        if self.typ == 'LAN':
            self.sq = 'SQ'
            self.au = 'AU'

        klu_fnm = self.klu.dataProvider().fieldNameMap()
        iau = klu_fnm['AU']
        isq = klu_fnm['SQ']
        iklu = klu_fnm['KLU']

        for f in self.klu.getFeatures():
            zau, zsq = '', ''
            if self.typ == 'LAN':
                if f[self.landid] in self.p.uzytki:
                    zsq = isNone(self.p.uzytki[f[self.landid]][1])
                    zau = isNone(self.p.uzytki[f[self.landid]][0])
                else:
                    zsq = 'xxx'
                    zau = 'xxx'
            else:
                zsq = f[self.sq]
                zau = f[self.au]

            val_klu = isNone(zau) + isNone(zsq)
            attr = {iau: zau, isq: zsq, iklu: val_klu}

            # dodaj do warstwy polaczone pole z AU i SQ oraz stworz slownik na
            # podstawie ktorego dopiszemy odpowiednie kolumny po dissolvie
            if val_klu not in self.sl_klu:
                self.sl_klu[val_klu] = [zau, zsq]

            self.klu.dataProvider().changeAttributeValues({f.id(): attr})

    def geop_przetworz(self):  # noqa
        """metoda wykonuje dissolve na warstwie klu nastepnie intersect z
        dzialkami, a potem rozbija wynik na singleparts, gotowe do analizy
        porownawczej z baza. Nie zwraca żadnej wartości"""
        import processing

        # utworz katalog temp w katalogu z warstwa
        sciezka = self.klu.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)

        # v.dissolve
        alg_params = {
            'GRASS_MIN_AREA_PARAMETER': 0.1,
            'GRASS_OUTPUT_TYPE_PARAMETER': 0,
            'GRASS_REGION_PARAMETER': None,
            'GRASS_SNAP_TOLERANCE_PARAMETER': 0.2,
            'GRASS_VECTOR_DSCO': '',
            'GRASS_VECTOR_EXPORT_NOCAT': False,
            'GRASS_VECTOR_LCO': '',
            'column': 'KLU',
            'input': self.klu,
            'output': os.path.join(self.tempkat,
                                   '__klu_dissolve_' +
                                   self.czas + '.shp')
        }
        processing.run('grass7:v.dissolve', alg_params)

        templyr1 = QgsVectorLayer(
            os.path.join(self.tempkat, '__klu_dissolve_' + self.czas + '.shp'),
            'templyr_diss',
            'ogr')

        # wykonaj przeciecie z warstwa dzialek a nastepnie kontynuuj analize
        alg_params = {
            '-t': False,
            'GRASS_MIN_AREA_PARAMETER': 0.1,
            'GRASS_OUTPUT_TYPE_PARAMETER': 0,
            'GRASS_REGION_PARAMETER': None,
            'GRASS_SNAP_TOLERANCE_PARAMETER': 0.2,
            'GRASS_VECTOR_DSCO': '',
            'GRASS_VECTOR_EXPORT_NOCAT': False,
            'GRASS_VECTOR_LCO': '',
            'ainput': templyr1,
            'atype': 0,
            'binput': self.dzkat,
            'btype': 0,
            'operator': 0,
            'snap': 0.2,
            'output': os.path.join(
                self.tempkat, '__LS_multiparts_'+self.czas+'.shp')
        }
        processing.run('grass7:v.overlay', alg_params)

        ovrlyr = QgsVectorLayer(
            os.path.join(self.tempkat, '__LS_multiparts_'+self.czas+'.shp'),
            'templyr_ovr',
            'ogr')

        ovrlyr.dataProvider().setEncoding('UTF-8')

        # sprawdz czy warstwy zostały wygenerowane poprawnie
        if not ovrlyr.isValid():
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się poprawnie przetworzyc warstw...'
                ' Sprawdź czy masz uruchomionego qgisa z grass\'em',
                Qgis.Critical, 10
            )
            return False

        fnm = ovrlyr.dataProvider().fieldNameMap()
        ovrlyr.startEditing()
        for old, id in fnm.items():
            if old[:2] in ['a_', 'b_', ]:
                ovrlyr.renameAttribute(id, old[2:])
        ovrlyr.commitChanges()

        # dodaj 2 potrzebne kolumny i rozkoduj do nich dane z dissolva
        pola = [x.name() for x in ovrlyr.dataProvider().fields()]
        pola_dodaj = []
        if 'SQ' not in pola:
            pola_dodaj.append(QgsField("SQ", QVariant.String, len=10))
        if 'AU' not in pola:
            pola_dodaj.append(QgsField("AU", QVariant.String, len=10))

        if len(pola_dodaj) > 0:
            ovrlyr.startEditing()
            ovrlyr.dataProvider().addAttributes(pola_dodaj)
            ovrlyr.updateFields()
            ovrlyr.commitChanges()

        klu_fnm = ovrlyr.dataProvider().fieldNameMap()
        iau = klu_fnm['AU']
        isq = klu_fnm['SQ']

        sl_podm = {}
        for f in ovrlyr.getFeatures():
            zsq = 'xxx'
            zau = 'xxx'
            it = isNone(f['KLU']).replace('?', 'Ł')
            if it in self.sl_klu:
                val = self.sl_klu[it]
                zsq = val[1]
                zau = val[0]

            sl_podm[f.id()] = {iau: zau, isq: zsq}

        for fid, sl in sl_podm.items():
            ovrlyr.dataProvider().changeAttributeValues({fid: sl})

        # narazie pomijamy automatyczne rozbicie na singlepartsy, algorytm nie
        # uwzględnia samoprzecinających się poligonów i przez to generuj
        # problemy
        processing.run("native:multiparttosingleparts", {
                       'OUTPUT': os.path.join(
                           self.tempkat,
                           '__LS_singleparts_'+self.czas+'.shp'),
                       # 'INPUT': os.path.join(
                        # self.tempkat, '__LS_multiparts_'+self.czas+'.shp'),
                       'INPUT': ovrlyr
                       })

        self.singleparts = QgsVectorLayer(
            os.path.join(self.tempkat, '__LS_singleparts_'+self.czas+'.shp'),
            'Ls_singleparts',
            'ogr')

        # self.singleparts.dataProvider().setEncoding('UTF-8')
        # if platform.system()[:3] == 'Win':
            # crs = QgsCoordinateReferenceSystem("epsg:2180")
            # QgsVectorFileWriter.writeAsVectorFormat(
                # self.singleparts,
                # os.path.join(
                    # self.tempkat, '__LS_singleparts_'+self.czas+'.shp'),
                # "UTF-8",
                # crs,
                # "ESRI Shapefile")

        return True

    def geop_przetworz_old(self):
        """metoda wykonuje dissolve na warstwie klu nastepnie intersect z
        dzialkami, a potem rozbija wynik na singleparts, gotowe do analizy
        porownawczej z baza. Nie zwraca żadnej wartości"""

        # import modulu umieszony w metodzie czasowo, inaczej bruzdzil przy
        # tesowaniu.
        # TODO: przeniesc jako import na poczatek pliku po zakonczeniu
        # testowania
        import processing

        sciezka = self.klu.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)

        processing.run("native:dissolve", {
                        'INPUT': sciezka+'.shp',
                        'FIELD': ['AU', 'SQ'],
                        'OUTPUT': os.path.join(self.tempkat,
                                               '__klu_dissolve_' +
                                               self.czas + '.shp')
        })

        templyr = QgsVectorLayer(
            os.path.join(self.tempkat, '__klu_dissolve_' + self.czas + '.shp'),
            'templyr_diss',
            'ogr')

        if platform.system()[:3] == 'Win':
            templyr.dataProvider().setEncoding('ISO-8859-2')

        do_usun = [k for k, v in
                   enumerate(templyr.dataProvider().fields().toList())
                   if v.name() not in ['SQ', 'AU', ]]
        templyr.startEditing()
        templyr.dataProvider().deleteAttributes(do_usun)
        templyr.commitChanges()

        processing.run("saga:intersect", {
                        'A': templyr,
                        'B': self.dzkat,
                        'SPLIT': False,
                        'RESULT': os.path.join(
                            self.tempkat, '__LS_multiparts_'+self.czas+'.shp'
                        )
        })

        templyr = QgsVectorLayer(
            os.path.join(self.tempkat, '__LS_multiparts_'+self.czas+'.shp'),
            'templyr_multi',
            'ogr')

        if platform.system()[:3] == 'Win':
            templyr.dataProvider().setEncoding('ISO-8859-2')

        # narazie pomijamy automatyczne rozbicie na singlepartsy, algorytm nie
        # uwzględnia samoprzecinających się poligonów i przez to generuj
        # problemy
        processing.run("native:multiparttosingleparts", {
                       'OUTPUT': os.path.join(
                           self.tempkat,
                           '__LS_singleparts_'+self.czas+'.shp'),
                       'INPUT': templyr
                       })

        # # Rozbij uzytki na single parts
        # self.singleparts = QgsVectorLayer(
        #    'Polygon?crs=epsg:2180&index=yes'
        #    '__LS_singleparts_'+self.czas,
        #    'ogr')

        self.singleparts = QgsVectorLayer(
            os.path.join(self.tempkat, '__LS_singleparts_'+self.czas+'.shp'),
            'Ls_singleparts',
            'ogr')

        if platform.system()[:3] == 'Win':
            self.singleparts.dataProvider().setEncoding('ISO-8859-2')

        self.singleparts.startEditing()
        feats = []
        nrf = self.singleparts.featureCount() + 100000
        print(nrf)
        fnm = self.singleparts.dataProvider().fieldNameMap()
        for f in self.singleparts.getFeatures():
            # rozbij poligony z selfintersect na multipoligony za potem zapisz
            # jako pojedyncze featurki
            ng = f.geometry().buffer(0, 0)
            ng.convertToMultiType()

            # sprawdz wasy w pierwszej czesci poligonu
            geom_ok = usun_wasy(
                QgsGeometry().fromMultiPolygonXY(
                    [ng.asMultiPolygon()[0]]
                )
            )
            self.singleparts.dataProvider().changeAttributeValues(
                {f.id(): {fnm['SQ']: isNone(f['SQ']).upper()}}
            )

            if len(ng.asMultiPolygon()) > 1:
                # import pdb; from PyQt5.QtCore import pyqtRemoveInputHook
                # pyqtRemoveInputHook()
                # pdb.set_trace()
                print('Zmina feat z id: ' + str(nrf))
                self.singleparts.changeGeometry(f.id(), geom_ok)

                for i, part in enumerate(ng.asMultiPolygon()[1:]):
                    # nf = QgsFeature(nrf)
                    # nf.setFields(
                        # self.singleparts.dataProvider().fields()
                    # )
                    nf = f
                    nf['SQ'] = isNone(f['SQ']).upper()
                    geom_n = QgsGeometry().fromMultiPolygonXY([part])
                    geom_n.convertToMultiType()
                    geom_ok = usun_wasy(geom_n)

                    nf.clearGeometry()
                    nf.setGeometry(geom_ok)
                    nf.setId(nrf)
                    feats.append(nf)
                    nrf += 1

            elif len(ng.asMultiPolygon()) == 1:
                self.singleparts.changeGeometry(f.id(), geom_ok)

        self.singleparts.addFeatures(feats)
        self.singleparts.commitChanges()

        crs = QgsCoordinateReferenceSystem("epsg:2180")
        QgsVectorFileWriter.writeAsVectorFormat(
            self.singleparts,
            os.path.join(
                self.tempkat, '__LS_singleparts_'+self.czas+'.shp'),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        # if platform.system()[:3] == 'Win':
        #     self.singleparts.dataProvider().setEncoding('ISO-8859-2')

    def zaladuj_strukture(self):
        """Metoda zestawia do słownika obiekty PrzetworzKlu dla każdej z
        działek
        """
        sl_dzkat = {}
        for feat in self.dzkat.getFeatures():
            sl_dzkat[feat['PARCELID']] = feat

        sl_single = {}
        for feat in self.singleparts.getFeatures():
            if feat['PARCELID'] not in sl_single:
                sl_single[feat['PARCELID']] = []
            sl_single[feat['PARCELID']].append(feat)

        for key, val in sl_dzkat.items():
            k = []
            if key in sl_single:
                k = sl_single[key]

            self.strukt[key] = PrzetworzKlu(val, k, self.p, self.wl)

    def przetworz_strukture(self):
        """ Metoda przetwarza strukturę wg ścieżki dla każdej z działki
        generując niezbędne dane do raportów oraz wynikowe klu do ostatecznych
        warstw.
        """
        for key, val in self.strukt.items():
            # jezeli uzytki nie sa valid - pomijamy raportujemy uzyszkodnikowi
            if not val.is_valid():
                self.bledne.append(key)
                continue

            trig = 0  # trig, jezeli jest jeden ls na calosci, badz juz dopis.
            val.przetworz()
            val.sprawdz_topologie()
            if not val.s_czy_dz_w_bazie():
                continue

            if val.s_czy_ls_na_calosci():
                trig = 1  # jeden ls na calosci dzialki, skopiowany z geom dz.

            if trig == 0:
                if val.s_czy_jeden_ls():
                    trig = 2  # jeden ls na calej dzialce - zlokalizowany

            if trig in [0, 2]:
                val.s_dopisz_uzyt()
                val.sprawdz_mikro()

            val.polacz_ostateczne()
            val.dopisz_uwagi_pow()

    def generuj_warstwy(self):
        """Generuje 3 ostateczne warstwy: ostateczne, do sprawdzenia, bledy i
        dodaje je do mapy
        """
        sciezka = self.dzkat.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        crs = QgsCoordinateReferenceSystem("epsg:2180")

        # tablice z odpowiednimi featurami
        poprawne = []
        do_spr = []
        bledne = []

        # przygotuj warstwe poprawnych LS
        self.lyrls = QgsVectorLayer("MultiPolygon?crs=epsg:2180&index=yes",
                                    "LS_"+self.czas,
                                    "memory"
                                    )

        self.lyrls.startEditing()
        self.lyrls.dataProvider().addAttributes(
            self.kolumny_dz + self.kolumny_ls
        )
        self.lyrls.updateFields()

        # przygotuj warstwe do_spr
        self.lyrspr = QgsVectorLayer("MultiPolygon?crs=epsg:2180&index=yes",
                                     "LS_DO_SPRAWDZENIA__"+self.czas,
                                     "memory"
                                     )
        self.lyrspr.startEditing()
        self.lyrspr.dataProvider().addAttributes(
            self.kolumny_dz + self.kolumny_ls
        )
        self.lyrspr.updateFields()

        # przygotuj warstwe bledow
        self.lyrbl = QgsVectorLayer("MultiPolygon?crs=epsg:2180&index=yes",
                                    "LS_BLEDY_"+self.czas,
                                    "memory"
                                    )
        self.lyrbl.startEditing()
        self.lyrbl.dataProvider().addAttributes(
            self.kolumny_dz + self.kolumny_ls)
        self.lyrbl.updateFields()

        # wyciagnij ostateczne featurki
        for sit in self.strukt.values():
            p, s, b = sit.zwroc_ostateczne()
            poprawne += [x for x in p.values()]
            bledne += b
            do_spr += s

        # oblicz powierzchnie poly w warstwach bledów i do_spr
        for x in bledne:
            x['LAND_POW'] = round(x.geometry().area() / 10000, 4)
        for x in do_spr:
            x['LAND_POW'] = round(x.geometry().area() / 10000, 4)

        # dodaj do warstw
        self.lyrbl.dataProvider().addFeatures(bledne)
        self.lyrspr.dataProvider().addFeatures(do_spr)
        self.lyrls.dataProvider().addFeatures(poprawne)

        # zapisz zmiany do warstw w pamieci
        self.lyrls.commitChanges()
        self.lyrbl.commitChanges()
        self.lyrspr.commitChanges()

        QgsVectorFileWriter.writeAsVectorFormat(
            self.lyrls,
            os.path.join(self.kat, "LS_"+self.czas+".shp"),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        self.lyrls = QgsVectorLayer(
            os.path.join(self.kat, "LS_"+self.czas+".shp"),
            "LS_"+self.czas,
            "ogr"
        )

        # sprawdz czy zapisaly się nam wszystkie featurki
        if self.lyrls.featureCount() == len(poprawne):
            QgsMessageLog.logMessage(
                "Warstwa  ls zapisana! "
                "(i nawet nic nie oszukałem na brakujących Featurach)",
                "Las-R",
                Qgis.Info)
        else:
            QgsMessageLog.logMessage(
                "Warstwa  ls zapisana! "
                "(QGIS naciął użyszkodnika na "+str(abs(
                    self.lyrls.featureCount()-len(poprawne))) +
                ' Featury) - dodaję do ostatecznej warstwy'
                '\nPamiętaj, że pominięte mogą zostać poligony z xx w AU i SQ',
                "Las-R",
                Qgis.Warning)

            # request = QgsFeatureRequest().setFlags(
            #     QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
            #         ['LANDID'],
            #         self.lyrls.fields()
            #     )

            # spróbuj dopisać do warstwy brakujące featurki
            trig = 0
            while self.lyrls.featureCount() < len(poprawne) or trig < 3:
                wpisane = [
                    x['LANDID'] for x in self.lyrls.getFeatures()
                ]
                braki = [x for x in poprawne if x['LANDID'] not in wpisane]

                # for x in braki:
                #    p = x.geometry().boundingBox().asPolygon()
                #    box = [
                #        QgsPointXY(float(x.split(' ')[-2]),
                #                   float(x.split(' ')[-1]))
                #        for x in p.split(',')
                #    ]
                #    x.setGeometry(QgsGeometry().fromMultiPolygonXY([[box]]))

                if len(braki) > 0:
                    self.lyrls.startEditing()
                    self.lyrls.dataProvider().addFeatures(braki)
                    self.lyrls.commitChanges()
                    if trig > 1:
                        QgsMessageLog.logMessage(
                            "Numer iteracji do zapisania: " + str(trig),
                            "Las-R",
                            Qgis.Info)
                    trig += 1
                else:
                    trig = 999

            if 10 > trig > 0:
                QgsMessageLog.logMessage(
                    "Niepoprawne wydzielenia: " +
                    '\n'.join([x.name() for x in braki]),
                    "Las-R",
                    Qgis.Critical)

        # Przelicz powierzchnie graficzna - zmienia sie ze wzg na uklad wsp
        self.lyrls.startEditing()
        pow_ind = self.lyrls.dataProvider().fieldNameIndex('LAND_POW')
        for feat in self.lyrls.getFeatures():
            self.lyrls.dataProvider().changeAttributeValues(
                {feat.id(): {pow_ind: feat.geometry().area()/10000}}
            )
            # gpopr = usun_wasy(gtemp)
            # self.lyrls.changeGeometry(feat.id(), gpopr)
        self.lyrls.commitChanges()

        # usun zbedne kolumny z warstwy z bledami i feat do spr
        self.lyrspr.startEditing()
        self.lyrbl.startEditing()

        do_usun = [k for k, v in enumerate(self.kolumny_dz + self.kolumny_ls)
                   if v.name() not in [
                       'SQ', 'AU', 'PARCELID', 'SPRAWDZ', 'LAND_POW', ]
                   ]
        self.lyrspr.dataProvider().deleteAttributes(do_usun)
        self.lyrbl.dataProvider().deleteAttributes(do_usun)

        self.lyrbl.commitChanges()
        self.lyrspr.commitChanges()

        QgsVectorFileWriter.writeAsVectorFormat(
            self.lyrbl,
            os.path.join(self.kat, "LS_BLEDY_"+self.czas+".shp"),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        print("Warstwa błędów ls zapisana!")
        QgsMessageLog.logMessage("Warstwa błędów ls zapisana!", "Las-R",
                                 Qgis.Info)
        self.lyrbl = self.iface.addVectorLayer(
            os.path.join(self.kat,
                         "LS_BLEDY_"+self.czas+".shp"),
            "LS_BLEDY_"+self.czas,
            "ogr"
        )

        QgsVectorFileWriter.writeAsVectorFormat(
            self.lyrspr,
            os.path.join(self.kat, "LS_DO_SPRAWDZENIA_"+self.czas+".shp"),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        print("Warstwa do sprawdzenia zapisana!")
        QgsMessageLog.logMessage("Warstwa do sprawdzenia zapisana!",
                                 "Las-R",
                                 Qgis.Info)
        self.lyrspr = self.iface.addVectorLayer(
            os.path.join(self.kat, "LS_DO_SPRAWDZENIA_"+self.czas+".shp"),
            "LS_DO_SPRAWDZENIA_"+self.czas,
            "ogr"
        )

        # dodaj warstwy do ramki
        QgsProject.instance().addMapLayer(self.lyrbl)
        QgsProject.instance().addMapLayer(self.lyrls)
        QgsProject.instance().addMapLayer(self.lyrspr)

        print("Warstwa Ls zapisana!")
        QgsMessageLog.logMessage("Warstwa Ls zapisana!",
                                 "Las-R",
                                 Qgis.Info)

    def generuj_raport(self):
        """Generuje raport na podstawie danych zebranych ze słowników uwagi
        dla każdej z działek, zapisuje go na dysku i pyta użytkownika czy chce
        go wyświetlić w jego edytorze tekstu.
        """
        raport = GenerujRaport(self.strukt, self.wl, self.p)
        raport.zestaw_dane()
        rap_out = raport.generuj_raport()

        self.rap_sc = os.path.join(
            self.kat, "ls_raport_"+self.czas+".txt")

        # open(self.rap_sc, 'wb').write(rap_out.encode('cp1250'))

        plik = open(self.rap_sc, 'w', encoding='cp1250')
        plik.write(rap_out)
        plik.close()


class PrzetworzKlu(object):
    def __init__(self, d, k, p, wl='OF'):
        # d-feature z analizowana dzialka i struktura pol zgodna ze skryptem
        # k-tablica z featurami klu na tej dzialce, wszystkie musza byc
        # przykryte przez poligon dzialki, oraz byc singlepart
        # p - przetworzona baza przez klase Przetworz
        # wl - typ własności działek jaki interesuje uzytkownika ('OF', 'Ws')
        self.dz = d
        self.klus = k
        # wskaznik do slownikow na podstawie bazy
        self.p = p
        self.wl = wl

        # kolejnosc id w poszczegolnych warstwach w celu zapewnienia spojnosci
        # danych, wymagane przy tworzeniu nowych featurow
        self.fid = 0

        # nazwy pol przetrzymujacych uzytki
        self.sq = 'SQ'
        self.au = 'AU'

        # tablica z polami, ktore maja znajdowac sie w ostatecznych danych
        # zwracanych uzytkownikowi, dodaje sie je metodą add_fields
        self.fields_def = [
            # QgsField('PARCELID', QVariant.String, len=30),
            # QgsField('AU', QVariant.String, len=10),
            # QgsField('SQ', QVariant.String, len=10),
            # QgsField('SPRAWDZ', QVariant.String, len=230),
            QgsField("COUNTY", QVariant.String, len=2),
            QgsField("DISTRICT", QVariant.String, len=2),
            QgsField("MUNICIP", QVariant.String, len=3),
            QgsField("COMMUNITY", QVariant.String, len=4),
            QgsField("PARCELNR", QVariant.String, len=20),
            QgsField("PARCELID", QVariant.String, len=50),
            QgsField("GRP", QVariant.String, len=2),
            QgsField("ARK", QVariant.String, len=12),
            QgsField("NIELES", QVariant.String, len=3),
            QgsField("UWAGI", QVariant.String, len=150),
            QgsField("PARCEL_AR", QVariant.Double, "double", 10, 4),
            QgsField("PARCEL_POW", QVariant.Double, "double", 10, 4),
            QgsField("AU", QVariant.String, len=10),
            QgsField("SQ", QVariant.String, len=10),
            QgsField("SPRAWDZ", QVariant.String, len=150),
            QgsField("LANDID", QVariant.String, len=50),
            QgsField("LAND_AR", QVariant.Double, "double", 10, 4),
            QgsField("LAND_POW", QVariant.Double, "double", 10, 4),
        ]

        # PARCELID wyciagniety z dzialki w metodzie przetworz
        self.pid = ''

        # slownik z uzytkami na dzialce i zsumowanymi powierzchniami, obliczany
        # w metodzie przetworz
        # sl = {LANDID: 4,3222, LANDID: 0.0002, ....}
        self.sl_klus_pow = {}

        # slownik z featurami pogrupowanymi po LANDID, w postaci:
        # obliczany w metodzie przetworz
        # sl = {LANDID: [f1, f2, f3], LANDID2: [f4, f5,...],}
        self.sl_klus_grupy = {}

        # poprawne klu
        self.klus_popr = []  # KLU, wstępnie przetworzone, sprawdzone mikro,
        #                      dopisane z bazy
        self.klus_bledy = []  # tabel z featurami sklasyfikowanymi jako bledy
        self.klus_do_spr = []  # lista z featurami do sprawdzenia
        self.poprawne = {}  # ostateczne poprawne/przetworzone KLU do zwrotu
        #                     w postaci slownika { LANDID: feat, ...}

        # tabela z rozbieznosciam powierzchniowymi, w postaci [LANDID, LANDID]
        self.rozb_pow = []

        # tabela z brakujacymi ls na dzialce, wg bazy,
        # w postaci [LANDID, LANDID]
        self.braki_warstwa = []

        # tabela z przetworzonymi id klu
        # w postaci [1, 22, 11, ...]
        self.klus_id_przetworzone = []

        # tablica z uwagami do raportu, grupowana wg skrotow ponizej:
        # pow - rozbieznosc powierzchni miedzy baza a grafika   OK
        #      {  landid: [pow graf, pow bazy], ... }
        # podmsq - podmieniony SQ w Ls, dostosowany do bazy     OK
        #       {landid: [sq przed, sq po], ...}
        # podmau - podmieniony AU, dostosowany do bazy          OK
        #       landid: [au przed, au po]
        # brakb - brak uzytku w bazie, jest w grafice           OK
        #       [landid, landid]
        # brakg - brak uzytku w grafice, jest w bazie
        #       [landid, landid]
        # brakdzb - brak dzkat w bazie, jest w grafice          OK
        #       True/False
        # mikro - mikroluz do usuniecia przez uzytkownika,      OK
        #       generowane jako nowa warstwa z uwagami
        #       [landid, landid, ... ]
        # dubb - zdublowane ls, klu w bazie                     OK
        #       [landid, landid, ...]
        # podm - ls z podmieniona grafika na kontur z dzialki   OK
        #       (tylko przy 1 ls)
        #       True/False
        # op - dzialka z wlasnoscia OP                          OK
        #       True/False
        # opif - dzialka z wlasnoscia OPiF                      OK
        #       True/False
        #
        self.uwagi = recursivedefaultdict()

        # ustaw najistotniejsze tablic i wartości w uwagach
        self.uwagi['mikro'] = []
        self.uwagi['pow'] = {}
        self.uwagi['dubb'] = []
        self.uwagi['brakdzb'] = []
        self.uwagi['brakb'] = []
        self.uwagi['op'] = False
        self.uwagi['podm'] = False
        self.uwagi['opif'] = False

        # True jezeli na dzialce nie ma zadnych klu
        self.bez_uzytkow = False

    def nazwa_sq_au(self, s, a):
        self.sq = s
        self.au = a

    def is_valid(self):
        if self.dz.geometry().wkbType() not in [QgsWkbTypes.Polygon,
                                                QgsWkbTypes.MultiPolygon]:
            return False

        if 'PARCELID' not in [x.name() for x in
                              self.dz.fields().toList()]:
            return False

        # jezeli na dzialce sa zadeklarowane klus, sprawdz poprawnosc
        if len(self.klus) > 0:
            if len([y for y in ['PARCELID', self.sq, self.au] if y in
                    [x.name() for x in self.klus[0].fields().toList()]]) != 3:
                return False

            # jezeli na dzialce znajduja sie uzytki z innej dzialki
            if set([self.dz['PARCELID']]) != set([x['PARCELID']
                                                  for x in self.klus]):
                return False

        return True

    def przetworz(self):
        """ Ustawia self.pid w obiekcie oraz oblicza slowniki dla powierzchni i
        liczby uzytkow na dzialce, wykorzystywane potem w analizie mikro oraz
        usuwaniu niepotrzebnych urzytkow"""
        self.pid = self.dz['PARCELID']

        # oblicz sumaryczna powierzchnie dla uzytku na dzialce, sumujac
        # wszystkie multipoligony
        if len(self.klus) == 0:
            self.bez_uzytkow = True
            return False

        self.sl_klus_pow = {self.stworz_landid(x): 0 for x in self.klus}
        self.sl_klus_grupy = {self.stworz_landid(x): [] for x in self.klus}
        for f in self.klus:
            self.sl_klus_pow[self.stworz_landid(f)] += \
                round(f.geometry().area()/10000, 4)
            self.sl_klus_grupy[self.stworz_landid(f)].append(f)

        if self.pid in self.p.dz_op:
            self.uwagi['op'] = True

        if self.pid in self.p.dz_opif:
            self.uwagi['opif'] = True

        # lista zdublowanych ls w bazie na tej dzialce
        self.uwagi['dubb'] = [x for x in self.p.ls_podwojne
                              if '.'.join(x.split('.')[:2]) == self.pid]

        return True

    def sprawdz_topologie(self):
        """Metoda sprawdza czy klu nakladaja sie na siebie, w przypadku gdy
        jeden z poligonow jest przykryty przez inny wiekszy, ten mniejszy
        jest klasyfikowany jako blad i przerzucany do warstwy bledow i pomijany
        w dalszej obrobce. Jezeli dwa poligony nachodza na siebie tylko troche
        ich czesc wspolna jest dodana do warstwy bledow jako do sprawdzenia"""

        if len(self.klus) < 2:
            return

        self.do_usun = []
        for i in range(len(self.klus)-1):
            for j in range(i+1, len(self.klus)):
                if self.klus[i].geometry().intersects(self.klus[j].geometry()):
                    inter = self.klus[i].geometry().intersection(
                        self.klus[j].geometry())
                    if round(inter.area(), 3) < 0.1:
                        pass
                    else:
                        try:
                            du, ds = self.s_topo_inter(i, j, inter)
                            self.klus_do_spr += ds
                        except:  # nopep8
                            QgsMessageLog.logMessage(
                                'Nieudane sprawdzenie topo: ' + self.pid,
                                'Las-R'
                            )

        self.s_do_usuniecia(self.do_usun)

    def s_do_usuniecia(self, do_usun, uw='przecina się z innym'):
        """Metoda usuwa z tabeli klus przekazane w tabeli f.id() i kopiuje
        je z odpowiednia struktura do tabeli klus_bledy, o ile uwaga nie
        jest rowna OK, wtedy dany featurek jest tylko usuwany z tabeli klus
        """

        # usun z listy klus featurki sklasyfikowane jako bledy
        self.do_usun = sorted(list(set(do_usun)), reverse=True)
        for i in self.do_usun:
            if uw != 'OK':
                f = self.new_feat(au=self.klus[i]['AU'],
                                  sq=self.isNone(self.klus[i]['SQ']),
                                  uw='nakłada się z innym')
                f.setGeometry(self.klus[i].geometry())
                self.klus_bledy.append(f)

            del self.klus[i]

    def s_topo_inter(self, i, j, inter):  # noqa
        """Metoda sprawdza, ktorego z idealnie nakladajacych sie poligonow
        wybrac do usuniecia z przyszlych analiz"""

        feat_do_spr = []  # tabela z przecieciem jako featurem do sprawdzenia
        inter_area = round(inter.area(), 3)

        # jezeli ktory z klus ma powierzchnie mniejsza niz 21 m2 zostawiamy
        # sprawdzanie nakladan, zajmie sie tym klasa sprawdzania mikrouzytkow
        if min([round(self.klus[i].geometry().area(), 3),
                round(self.klus[j].geometry().area(), 3)]) < 21:
            return

        landid_i = self.pid + '.' + \
            self.klus[i][self.au] + \
            self.isNone(self.klus[i][self.sq])
        landid_j = self.pid + '.' + \
            self.klus[j][self.au] + \
            self.isNone(self.klus[j][self.sq])

        # powierzchnia przeciecia jest taka sama jak
        # powierzchnia obu klu
        if round(self.klus[i].geometry().area(), 3) == \
                inter_area and \
                round(self.klus[j].geometry().area(), 3) == \
                inter_area:

            # jezeli oba sa w bazie wybieramy nielesnego
            if landid_i in self.p.uzytki and landid_j in \
                    self.p.uzytki:

                # jezeli tylko jeden z klu jest w bazie, to go
                # zostawiamy
                if self.klus[i][self.au] != 'Ls' and \
                        self.klus[j][self.au] == 'Ls':
                    self.do_usun.append(i)
                elif self.klus[j][self.au] != 'Ls' and \
                        self.klus[i][self.au] == 'Ls':
                    self.do_usun.append(j)

                # jezeli oba powyzsze sa ls-ami, niech uzytkownik zdecyduje
                else:
                    f = self.new_feat(
                        uw='nałożone poligony o tym samym kształcie')
                    f.setGeometry(inter)
                    feat_do_spr.append(f)

            elif landid_i in self.p.uzytki and landid_j not in \
                    self.p.uzytki:
                self.do_usun.append(j)

            elif landid_i not in self.p.uzytki and landid_j in \
                    self.p.uzytki:
                self.do_usun.append(i)

        # powierzchnia jednego badz drugiego jest taka sama jak przeciecia
        elif round(self.klus[i].geometry().area(), 3) == inter_area:
            # jezeli uzytek jest w bazie to usuwamy albo do sprawdzenia
            if landid_i in self.p.uzytki:
                if len(self.sl_klus_grupy[landid_i]) > 1:
                    self.do_usun.append(i)
                else:
                    f = self.new_feat(
                        uw='nałożona część poligonu, na inny cały')
                    f.setGeometry(inter)
                    feat_do_spr.append(f)

            # jak uzytku nie ma w bazie to do usuniecia
            else:
                self.do_usun.append(i)

        elif round(self.klus[j].geometry().area(), 3) == inter_area:
            # jezeli uzytek jest w bazie to usuwamy albo do sprawdzenia
            if landid_j in self.p.uzytki:
                if len(self.sl_klus_grupy[landid_j]) > 1:
                    self.do_usun.append(j)
                else:
                    f = self.new_feat(
                        uw='nałożona część poligonu, na inny cały')
                    f.setGeometry(inter)
                    feat_do_spr.append(f)

            # jak uzytku nie ma w bazie to do usuniecia
            else:
                self.do_usun.append(j)

        # oba poligony przecinaja sie na czesci swoich powierzchni, uzytkownik
        # musi zdecydowac ktora granica przebiegu jest właściwa
        else:
            f = self.new_feat(
                uw='nałożona część poligonów')
            f.setGeometry(inter)
            feat_do_spr.append(f)

        return self.do_usun, feat_do_spr

    def s_czy_dz_w_bazie(self):
        self.uwagi['brakdzb'] = False
        if self.pid in self.p.dzialki.keys():
            return True

        return False

    def s_czy_ls_na_calosci(self):
        """Metoda sprawdza czy uzytek znajduje sie na calej dzialce, jest jeden
        w zbiorze uzytkow w bazie, jezeli tak to podmienia jego grafike na
        kontur dzialki"""

        self.uwagi['podm'] = False
        if self.pid in self.p.sl_pow_ls_dzkat:
            if self.p.sl_pow_ls_dzkat[self.pid][0] == \
                    self.p.sl_pow_ls_dzkat[self.pid][1]:
                f = self.new_feat(au='Ls', sq=self.p.sl_ls_na_dz[self.pid][0])
                f.setGeometry(self.dz.geometry())
                self.klus_popr.append(f)
                self.uwagi['podm'] = True
                self.klus = []
                return True
        return False

    def s_czy_jeden_ls(self):
        """Metoda sprawdza czy w bazie jest jeden ls, jezeli tak, sprawdza czy
        na dzialce znajduje sie jeden ls o tej samej klasie"""
        # sprawdz czy w bazie znajduje sie tylko jeden ls na dzewid
        if self.pid not in self.p.sl_ls_na_dz:
            return False
        if len(self.p.sl_ls_na_dz[self.pid]) > 1:
            return False

        # jeżeli na dzialce jest wiecej niz jedna klasa uzytkow w graf, ale
        # jeden ls - w ktorym sprawdzimy sq czy jest zgodny z baza
        if len(self.sl_klus_grupy.keys()) > 1 and \
                len(set([x.split('.')[-1] for x in self.sl_klus_grupy.keys()
                         if x.split('.')[-1][:2] == 'Ls'])) == 1:
            pass
        # jezeli na dzialce w graf jest jeden uzytek - niekoniecznie ls -
        # sprawdzimy czy przypadkiem nie jest to nieprzemianowany Ls
        elif len(self.sl_klus_grupy.keys()) == 1:
            pass
        else:
            return False

        self.do_usun = []
        for ii, klu in enumerate(self.klus):
            uw = ''  # uwagi do wpisania do warstwy
            trig = False  # czy dodać uzupelniony Ls

            # stworz landid poprawny i zgodny z baza
            landid = self.pid + '.Ls' + self.p.sl_ls_na_dz[self.pid][0]

            if len(set([x for x in self.sl_klus_pow.keys()
                        if x.split('.')[-1][:2] == 'Ls'])) == 1:
                # jezeli jest Ls ale ma inna klase - podmien SQ i dodaj do
                # raportu rozbieznosci
                if klu['AU'] == 'Ls' and \
                        klu['SQ'] != self.p.sl_ls_na_dz[self.pid][0]:

                    self.uwagi['podmsq'][landid] = [
                        self.isNone(klu['SQ']),
                        self.isNone(self.p.sl_ls_na_dz[self.pid][0])
                    ]
                    uw = 'Podmieniono SQ na zgodny z bazą; '
                    trig = True

            # jezeli na dzialce jest tylko jeden inny uzytek, podmien na
            # brakujacy ls, o ile nie jest bledem topo
            elif len(set([x for x in self.sl_klus_pow.keys()])) == 1:
                self.uwagi['podmau'][landid] = [
                    klu['AU'] + self.isNone(klu['SQ']),
                    'Ls' + self.p.sl_ls_na_dz[self.pid][0]
                ]
                uw = 'Podmieniono AU i SQ na zgodny z bazą; '
                trig = True

            if trig:
                f = self.new_feat('Ls',
                                  self.p.sl_ls_na_dz[self.pid][0],
                                  uw=uw)
                f.setGeometry(klu.geometry())
                self.klus_popr.append(f)
                self.do_usun.append(ii)

        self.s_do_usuniecia(self.do_usun, 'OK')
        return True

    def s_dopisz_uzyt(self):
        """Metoda dopisuje do wszystkich klu w tablicy klus, dane z bazy i
        uwagi, i przerzuca je do tablicy klus_popr, z odpowiednimi adnotacjami
        """

        self.do_usun = []
        for ii, klu in enumerate(self.klus):
            landid = self.pid + '.' + \
                klu['AU'] + \
                self.isNone(klu['SQ'])

            uw = ''
            dop1 = klu[self.au]
            dop2 = klu[self.sq]
            if landid not in self.p.uzytki:
                uw = 'Brak w bazie; '

                # dopisz landid do tablicy uwag
                if 'brakb' not in self.uwagi:
                    self.uwagi['brakb'] = []
                if landid not in self.uwagi['brakb']:
                    self.uwagi['brakb'].append(landid)

            else:
                dop1 = self.p.uzytki[landid][0]
                dop2 = self.p.uzytki[landid][1]

            f = self.new_feat(au=dop1, sq=dop2, uw=uw)
            f.setGeometry(klu.geometry())
            self.klus_popr.append(f)
            self.do_usun.append(ii)

        # usun dopisane uzytki z puli klu
        self.s_do_usuniecia(self.do_usun, 'OK')

    def add_fields(self, new_fields):
        """ Metoda dodająca pola, które mają się znaleźć w ostatecznej wersji
        każdego feat, zwracanego użytkownikowi. Jeżeli pola nie zostaną podane
        klasa będzie korzystała ze zdefiniowanych na początku niezbędnych pól,
        które są wymagane do działania: [AU, SQ, PARCELID, SPRAWDZ].

        Przekazywana tabela powinna wyglądać: [QgsField(), QgsField(), ...]
        """
        # sprawdz czy podne pola zawieraja niezbędne minimum:
        policz_niezb = len([x.name() for x in new_fields if x.name() in
                            [y.name() for y in self.fields_def]
                            ])

        if policz_niezb != len(self.fields_def):
            return False

        self.fields_def = new_fields

    def new_feat(self, au=False, sq=False, uw=False):
        f = QgsFeature(self.fid)
        self.fid += 1
        fds = QgsFields()
        for fi in self.fields_def:
            fds.append(fi)

        f.setFields(fds)
        f.setAttribute(f.fieldNameIndex('PARCELID'), self.pid)
        if au:
            f.setAttribute(f.fieldNameIndex('AU'), au)
        if sq:
            f.setAttribute(f.fieldNameIndex('SQ'), sq)
        if uw:
            f.setAttribute(f.fieldNameIndex('SPRAWDZ'), uw)
        return f

    def stworz_landid(self, f):
        """metoda tworzy LANDID na podstawie danych podanego feature'a"""
        return f['PARCELID'] + '.' + f['AU'] + self.isNone(f['SQ'])

    def isNone(self, a):
        if a in [None, 'NULL', '', ]:
            return ''
        elif isinstance(a, QVariant):
            if a.isNull():
                return ''
        else:
            return a

    def sprawdz_mikro(self):
        """ Metoda sprawdza czy w uzupełnionej tabeli klus_popr znajdują się
        jakieś mikroużytki a następnie sprawdza czy da się je usunąć automaty-
        cznie. Jeżeli nie zwracana jest tabela z featurami do sprawdzenia przez
        użytkownika.
        """
        if len(self.klus_popr) < 1:
            return

        d = SprawdzMikro(self.klus_popr)

        if d.przetworz():
            popr, spr, usun = d.zwroc_wyn()

            if len(popr) < len(self.klus_popr):
                self.klus_popr = popr

            self.klus_do_spr += spr
            self.klus_bledy += usun

    def polacz_ostateczne(self):  # noqa
        """Metoda zestawia klu z tablic z poprawnymi, blednymi i do sprawdzenia
        poligonami, łączy je na podstawie landid, uzupełnia tablice uwagi o
        info na temat obecnosci użytków w bazie, podwojnych użytkow w bazie,
        rozbieżności powierzchni międz bazą a grafiką, obecności mikrusów.
        """
        spis_klu = [self.stworz_landid(x) for x in self.klus_popr]
        ile_klu = [x[0] for x in Counter(spis_klu).most_common() if x[1] > 1]

        # zmienna z uwagą do spradzenia geometrii, gdy przy laczeniu cos
        # pojdzie nie tak jak trzeba i nie dostaniemy kodu 0
        blad_lacz = \
            'geometria do sprawdzenia z w warstwą orginalną'
        # tablica z poprawnymi klu połącznymi w multipoly i posiadajace juz
        # poprawne, i niezdublowane uwagi
        self.poprawne = {}

        for i, y in enumerate(spis_klu):
            if y not in self.poprawne:
                self.poprawne[y] = self.klus_popr[i]
                continue

            # if y == '24171420001.16224/1.LsIV':
                # import pdb; from PyQt5.QtCore import pyqtRemoveInputHook
                # pyqtRemoveInputHook()
                # pdb.set_trace()

            # jezeli uzytek jest mikrusem dodaj uwage do slownika, ale jeżeli
            # nie jest jedynym poligonem z tego klu
            if self.klus_popr[i].geometry().area() < 21 and y in ile_klu:
                if y not in self.uwagi['mikro']:
                    self.uwagi['mikro'].append(y)
                    try:
                        self.poprawne[y]['SPRAWDZ'] += 'Mikroużytek do spr.; '
                    except:  # nopep8
                        self.poprawne[y]['SPRAWDZ'] = 'Mikroużytek do spr.; '

            elif y in ile_klu:
                # dodaj nowa geometrie do bazy
                geom_baza = self.poprawne[y].geometry()
                geom_dolacz = self.klus_popr[i].geometry()

                # jezeli czesci sie stykaja - union, niestykaja - dodaj part
                result = ''
                if geom_baza.intersects(geom_dolacz):
                    new_geom = geom_baza.combine(geom_dolacz)
                else:
                    result = geom_baza.addPartGeometry(geom_dolacz)  # noqa
                    new_geom = geom_baza
                    # TODO: Obczaić kody do tych resultów, z tym że raczej nie
                    # występują, jeszcze się nie spotkałem...

                    # OK Spotkałem się, wygląda na to, że łaczenie jest
                    # poprawne, ale potem generuje geometrię która nie
                    # przechodzi kontroli geos.
                    # Dodałem informację dla usera o sprawdzeniu geometrii

                # TODO: Przetestować toto, fix na szybko dla Marka
                new_geom.convertToMultiType()
                if not new_geom.isNull():
                    try:
                        gpopr = usun_wasy(new_geom)
                    except:  # nopep8
                        gpopr = geom_baza
                        result = '9'
                else:
                    gpopr = geom_baza
                    result = '9'

                # usun powtarzajace sie wierzcholki i mikrowasy
                self.poprawne[y].clearGeometry()
                self.poprawne[y].setGeometry(gpopr)

                # sprawdz czy w tej czesci nie ma jakichs nowych uwag, jezeli
                # sa dodaj do wczesniejszych na koncu
                u_nowe = []
                u_stare = ''
                if isinstance(self.klus_popr[i]['SPRAWDZ'], str):
                    u_nowe = self.klus_popr[i]['SPRAWDZ'].split('; ')
                if isinstance(self.poprawne[y]['SPRAWDZ'], str):
                    u_stare = self.poprawne[y]['SPRAWDZ']

                if result not in ['', 0]:
                    u_nowe.append(blad_lacz)
                    QgsMessageLog.logMessage(
                        self.isNone(self.poprawne[y]['PARCELID']) +
                        ' - GEOMETRIA DO SPRAWDZENIA!',
                        'Las-R'
                    )

                # sprawdz czy sa jakies nowe uwagi, jezeli tak, dodaj
                trig_dopisz = False
                for u in u_nowe:
                    if u not in u_stare:
                        u_stare += u + '; '
                        trig_dopisz = True

                if trig_dopisz:
                    self.poprawne[y]['SPRAWDZ'] = u_stare

    def dopisz_uwagi_pow(self):  # noqa
        """Metoda sprawdza czy połączone klu w słowniku poprawne, nie odbiegają
        za bardzo od powierzchni rejestrowych zapisanych w bazie, oraz czy Ls
        na działce są napewno wycięte, a nie tylko skopiowane z kontury działki
        """

        # sprawdzenie czy powierzchnie nie roznia sie za bardzo
        for landid, item in self.poprawne.items():

            # dopisz landid i informacje wyciagniete z dzialki
            item.setAttribute(item.fieldNameIndex('LANDID'), landid)
            item.setAttribute(item.fieldNameIndex('COUNTY'), landid[:2])
            item.setAttribute(item.fieldNameIndex('DISTRICT'), landid[2:4])
            item.setAttribute(item.fieldNameIndex('MUNICIP'), landid[4:7])
            item.setAttribute(item.fieldNameIndex('COMMUNITY'), landid[7:11])

            for x in ['PARCELNR', 'PARCELID', 'GRP', 'ARK', 'NIELES', 'UWAGI',
                      'PARCEL_AR', 'PARCEL_POW']:
                item.setAttribute(item.fieldNameIndex(x), self.dz[x])

            # pow graf uzytku
            item.setAttribute(item.fieldNameIndex('LAND_POW'),
                              round(item.geometry().area()/10000, 4))

            # jezeli nie ma uzytku w bazie nie ma co sprawdzac
            if landid not in self.p.uzytki.keys():
                continue

            # dopisz dane z bazy
            item.setAttribute(item.fieldNameIndex('LAND_AR'),
                              self.p.uzytki[landid][2])

            # jezeli obie powierzchnie sa ponizej 20 ar - pomijamy uwagi
            if max(item.geometry().area(), self.p.uzytki[landid][2]) < 0.2:
                continue

            # sprawdzamy tylko i wyłącznie Ls
            if item['AU'] != 'Ls':
                continue

            if abs(item.geometry().area()/10000 -
                   self.p.uzytki[landid][2]) > 0.15:

                if 'pow' not in self.uwagi:
                    self.uwagi['pow'] = {}

                if landid not in self.uwagi['pow']:
                    self.uwagi['pow'][landid] = [
                        round(item.geometry().area()/10000, 4),
                        self.p.uzytki[landid][2]
                    ]

                    uw = self.isNone(item['SPRAWDZ'])

                    uw += 'Duża rozbieżność pow. rej/graf; '

                    # sprawdz czy pow graf uz==pow graf dz, a w bazie nie
                    if round(self.dz.geometry().area(), 3) == \
                            round(item.geometry().area(), 3):
                        powi = self.p.uzytki[landid]
                        if powi[2] < self.dz['PARCEL_AR']:
                            uw += 'Prawdopodobnie niewycięty Ls; '

                    item.setAttribute(item.fieldNameIndex('SPRAWDZ'), uw)

    def zwroc_ostateczne(self):
        """Metoda zwraca ostateczne wersje przetworzonych uzytków w postaci
        jednego słownika i dwóch tabel:
        1) poprawnych klu, (dict)
        2) poligonów oznaczających miejsca do sprawdzenia,
        3) blędne klu/mikro/inne, które zostały zakwalifikowane jako błędy i
        usunięte z warstwy poprawnych klu.
        """
        return self.poprawne, self.klus_do_spr, self.klus_bledy


class SprawdzMikro(object):
    def __init__(self, tab, baza_uz=[]):
        # tablica ze wszystkimi poprawnymi klu (duze i male razem, nieposort.)
        self.klus_popr = tab
        # tablica z uztykami wpisanymi do bazy
        self.baza_klu = baza_uz

        # tablica z przetworzonymi klu po poprawkach mikro
        self.feat_popr = []

        self.pid = ''
        if len(tab) > 0:
            self.pid = tab[0]['PARCELID']

        self.do_usun = []  # f.id() do usuniecia z klus_popr
        # [[f.id(), f.id()], ...] id laczonego, id bazowego
        self.do_polacz = []

        # tabele z przetworzonymi feat zwracanymi uzytkownikowi
        self.feat_do_usun = []
        self.feat_popr = []
        self.feat_do_spr = []

        # sl z sasiadami dla kazdego klu
        self.sl_sasiadow = {}

    def is_valid(self):  # noqa
        """Metoda sprawdza mikrouzytki i o ile takie istnieją w tablicy
        zwraca True"""

        # sprawdz czy na dzialce sa klu mniejsze niz 21 m2 jezeli nie, pomin
        # sprawdzanie mikrouzytkow na dzialce
        self.p_min_klu_pow = sorted([f.geometry().area()
                                     for f in self.klus_popr
                                     if f.geometry().area() < 21])
        if len(self.p_min_klu_pow) < 1:
            return False
        else:
            self.p_min_klu = [f for f in self.klus_popr
                              if f.geometry().area() < 21]

        # jeżeli na dzialce jest tylko jeden uzytek, poniechaj
        if len(self.klus_popr) < 2:
            return False

        return True

    def zbuduj_strukture(self):
        # Jezeli na dzialce sa mikrouzytki zbuduj indeks przestrzenny
        # poprawnych klus
        self.si = QgsSpatialIndex()
        self.slk = {}
        for k in self.klus_popr:
            if k.id() not in self.slk:
                self.slk[k.id()] = k
                self.si.addFeature(k)
            else:
                print('---BLAD---|powtorzony id:'+self.pid+str(k.id()))

        # oblicz powierzchnie sumaryczna dla wszystkich klu
        # {landid: 2.223, landid: 9.332, ...}
        self.sl_pow_popr_klu = {}
        # slownik z liczba poprawnych klu na dzialce
        # {landid: 2, landid: 6, ... }
        self.sl_ile_popr_klu = {}

        for klu in self.klus_popr:
            landid = self.pid + '.' + klu['AU'] + self.isNone(klu['SQ'])

            if landid not in self.sl_pow_popr_klu:
                self.sl_pow_popr_klu[landid] = 0.0
            self.sl_pow_popr_klu[landid] += klu.geometry().area() / 10000

            if landid not in self.sl_ile_popr_klu:
                self.sl_ile_popr_klu[landid] = 0
            self.sl_ile_popr_klu[landid] += 1

            self.sl_sasiadow[klu.id()] = []

    def isNone(self, a):
        if a in [None, 'NULL', '', ]:
            return ''
        elif isinstance(a, QVariant):
            if a.isNull():
                return ''
        else:
            return a

    def przetworz_mikro(self):
        # sprawdz sasiedztwa wszystkich malych klus na dzialce
        for k in self.p_min_klu:
            landid = self.pid + '.' + k['AU'] + self.isNone(k['SQ'])
            polacz = False  # flaga do polaczenia lub usuniecia

            # jezeli uzytek jest w bazie
            if 'Brak w bazie; ' not in self.isNone(k['SPRAWDZ']):
                # jezeli uzytek ma mala pow w bazie - zostaw
                if self.sl_ile_popr_klu[landid] < 2 and \
                        self.sl_pow_popr_klu[landid] < 0.006:
                    # na dzialce jest zlokalizowany maly uzytek, olac
                    self.feat_popr.append(k)

                elif self.sl_ile_popr_klu[landid] > 1 and \
                        self.sl_pow_popr_klu[landid] > 0.006:
                    # jezeli mikrus jest < 5% pow calego uzytku - skasuj
                    if (k.geometry().area()/10000) / \
                            self.sl_pow_popr_klu[landid] < 0.05:
                        polacz = True

            # jezeli mikrusa nie ma w bazie, skasuj/polacz
            else:
                polacz = True

            # jezeli oznaczony do usuniecia z poprawnej warstwy - usun
            if polacz:
                self.polacz_klu(k)

    def polacz_klu(self, k):  # noqa
        ids = self.si.intersects(k.geometry().boundingBox())

        # jezeli powierzchnia jest za mala, pomijamy - generuje bledy
        if k.geometry().area() < 0.0000001:
            self.do_usun.append(k.id())

        # znajdz sasiadow z ktorymi dzieli najwiecej miejsca
        p_area = []  # tablica z przecieciami powierzchniowymi[[id, pow], ...]
        p_line = []  # tablica z przecieciami liniowymi [[id, len], ...]
        for id in ids:
            if id == k.id():
                pass
            else:
                geom = self.slk[id].geometry()
                if geom.intersects(k.geometry()):
                    # informacje o przecieciu
                    inter = geom.intersection(k.geometry())
                    self.sl_sasiadow[k.id()].append(id)

                    # jezeli przeciecie jest powierzchniowe i nie calkowite do
                    # sprawdzenia przez uzyszkodnika
                    # jezeli przeciecie jest powierzchniowe
                    if round(inter.area(), 3) > 0.000:
                        p_area.append([id, round(inter.area(), 3)])

                    # jezeli tylko liniowe
                    else:
                        p_line.append([id, inter.length()])

        # jezeli przecina sie z jednym  dolacz do niego, niezaleznie od tego
        # czy stylka sie na wiekszej dlugosci z czym innym
        if len(p_area) == 1:
            # jezeli powierzchnia przeciecia jest taka sama jak pow
            # sprawdzanego klu, a pow 2 przecinajacego sie uzytku jest wieksza
            # to usun analizowany klu
            if round(k.geometry().area(), 3) == round(p_area[0][1], 3) and \
                    round(self.slk[p_area[0][0]].geometry().area(), 3) > \
                    p_area[0][1]:
                self.do_usun.append(k.id())

            # jezeli powierzchnia jest taka sama jak innego klu tzn ze jest to
            # blad nachodzenia 2 klu na siebie - do wyjasnienia!
            if round(self.slk[p_area[0][0]].geometry().area(), 3) >= \
                    round(p_area[0][1], 3):
                    # round(k.geometry().area(), 3) == round(p_area[0][1], 3):
                self.do_polacz.append([k.id(), p_area[0][0]])
            else:
                uw = self.isNone(k['SPRAWDZ'])
                k.setAttribute(k.fieldNameIndex('SPRAWDZ'),
                               uw+'Mikro do spr (wystaje poza jeden); ')
                self.feat_do_spr.append(k)

        # jezeli mikrus pokrywa sie z innymi uzytkami w 100%, usuwamy -
        # sprawdzilismy wczesniej czy aby nie jest niezbedny
        elif len(p_area) > 1:
            if sum([x[1] for x in p_area]) == round(k.geometry().area(), 3):
                self.do_usun.append(k.id())

        # jezeli mikrus z niczym sie nie przecina, dolacz do sasiada z ktorym
        # dzieli najwiecej wspolnego miejsca
        else:
            if len(p_line) > 0:
                p_line = sorted(p_line, key=lambda x: x[1], reverse=True)
                znikajace = self.do_usun + [x[0] for x in self.do_polacz]

                if p_line[0][0] not in znikajace:
                    # jezeli mikrus styka sie z innym uzytkiem na obwodzie
                    # mniejszym niz 5% usuwamy
                    if (p_line[0][1]/k.geometry().length()) < 0.05:
                        self.do_usun.append(k.id())
                    else:
                        self.do_polacz.append([k.id(), p_line[0][0]])

                else:
                    if len(p_line) == 2 and p_line[1][0] not in znikajace:
                        self.do_polacz.append([k.id(), p_line[1][0]])
                    elif len(p_line) == 1 and p_line[0][0] in znikajace:
                        self.do_usun.append(k.id())
                    else:
                        uw = self.isNone(k['SPRAWDZ'])
                        k.setAttribute(k.fieldNameIndex('SPRAWDZ'),
                                       uw+'Mikro do spr(stykanie liniowe); ')
                        self.feat_do_spr.append(k)

            else:
                self.do_usun.append(k.id())

        # jezeli z niczym nie sasiaduje - usuwamy
        if len(ids) == 1:
            self.do_usun.append(k.id())

    def process(self):
        """Metoda usuwa, bądź łączy mikrouzytki z warstwy klus_popr wg podanych
        tabel (generowanych w s_mikro). """

        poprawione = []
        # polacz geom featurow przeznaczonych do laczenia
        for it in self.do_polacz:
            # jezeli feature do laczenia znalazl sie jednak na liscie do
            # usuniecia przesun mikrusa na warstwe do sprawdzenia
            if it[1] in self.do_usun:
                # sprawdz czy wszyscy sasiedzi sa mikro, jezeli tak, usun.
                sas = [x for x in self.sl_sasiadow[it[0]]
                       if x not in [y.id() for y in self.p_min_klu]]
                if len(sas) == 0:
                    self.do_usun.append(it[0])
                else:
                    uw = self.isNone(self.slk[it[0]]['SPRAWDZ'])
                    self.slk[it[0]].setAttribute(
                        self.slk[it[0]].fieldNameIndex('SPRAWDZ'),
                        uw+'Mikro do spr (łączenie/usuwanie); ')
                    self.feat_do_spr.append(self.slk[it[0]])

            else:
                feat_baza = self.slk[it[1]]
                g_bazy = self.slk[it[1]].geometry()
                g_lacz = self.slk[it[0]].geometry()

                # geometria po union
                try:
                    g_union = g_bazy.combine(g_lacz)

                    zabezp = 0
                    while g_union.removeDuplicateNodes(0.0000001) and \
                            zabezp < 20:
                        zabezp += 1

                    if g_union.isGeosValid():

                        # wyczyść a potem ustaw nowa geometrie
                        feat_baza.clearGeometry()
                        feat_baza.setGeometry(g_union)

                        self.slk[it[1]].clearGeometry()
                        self.slk[it[1]].setGeometry(g_union)

                        # jezeli laczonego uzytku jeszcze nia ma w usunietych
                        # dodaj do usuniecia
                        if it[0] not in self.do_usun:
                            self.do_usun.append(it[0])

                    else:
                        uw = self.isNone(self.slk[it[0]]['SPRAWDZ'])
                        self.slk[it[0]].setAttribute(
                            self.slk[it[0]].fieldNameIndex('SPRAWDZ'),
                            uw+'Mikro do spr (niepopr geom po polaczeniu); ')
                        self.feat_do_spr.append(self.slk[it[0]])

                    if it[1] not in poprawione:
                        poprawione.append(it[1])

                except:  # noqa
                    # jezeli nie udało się przeprowadzić combine, zostawiamy
                    # baze nietknieta a laczony mikrus dodajemy do sprawdzenia
                    g_union = g_bazy

                    if it[1] not in poprawione:
                        poprawione.append(it[1])

                    uw = self.isNone(self.slk[it[0]]['SPRAWDZ'])
                    self.slk[it[0]].setAttribute(
                        self.slk[it[0]].fieldNameIndex('SPRAWDZ'),
                        uw+'Mikro do spr (błąd przy łączeniu); ')
                    self.feat_do_spr.append(self.slk[it[0]])

        for id in poprawione:
            self.feat_popr.append(self.slk[id])

    def zestaw_tablice(self):
        """Metoda ustawia ostateczne tablice ktore zostana zwrocone jako wynik
        z juz poprawionymi geometriami i pogrupowanymi danymi"""

        # id featurow juz dopisanych do poprawnej tabeli klu
        obecne = [f.id() for f in self.feat_popr]
        id_do_spr = [f.id() for f in self.feat_do_spr]
        id_mikrusow = [f.id() for f in self.p_min_klu]

        for feat in self.klus_popr:
            # jezeli feat jest juz w obecnych lub do spr - pomin
            if feat.id() in obecne + id_do_spr:
                pass

            elif feat.id() in self.do_usun:

                uw = self.isNone(feat['SPRAWDZ'])
                feat.setAttribute(feat.fieldNameIndex('SPRAWDZ'),
                                  uw+'Mikro do spr; ')
                # jezeli feat ma pow wiecej niz 1 m2, może okazać sie że jest
                # poprawną resztką Ls - użyszkodnik sprawdzi
                if feat.geometry().area() > 1:
                    if feat.id() not in id_do_spr:
                        self.feat_do_spr.append(feat)
                        id_do_spr.append(feat.id())
                else:
                    self.feat_do_usun.append(feat)

            elif feat.id() not in id_mikrusow:
                self.feat_popr.append(feat)

    def przetworz(self):
        """ Metoda zbiorcza przetwarza wczytane klu wg poprawnej kolejnosci
        zdarzen"""

        if not self.is_valid():
            return False

        self.zbuduj_strukture()
        self.przetworz_mikro()
        self.process()
        self.zestaw_tablice()
        return True

    def zwroc_wyn(self):
        """ Metoda zwraca 3 listy: poprawne klu, do sprawdzenia, i usuniete"""

        return self.feat_popr, self.feat_do_spr, self.feat_do_usun


class GenerujRaport():
    def __init__(self, struk, wl, p):
        """ konstruktor pobiera słownik z obiektami PrzetworzKlu w postaci:
            {parcelid: PrzetworzKlu, ...} już z przetworzonymi i ostatecznymi
            klu oraz uwagami do powyższych, oraz typ wlasnosci działek jaki
            wybrał użytkownik (OF - pryw i współwłasności, lub cokolwiek innego
            ). p - obiekt przetworzonej bazy danych.
            Klasa generuj wypis do pliku txt na podstawie danych z bazy i shp
            """

        self.s = struk
        self.wl = wl
        self.p = p

        self.wypis = 'RAPORT\n\n'

        # tablica ze wszystkimi poprawnymi uzytkami, z warstwy LS
        self.uzytki = []

        self.ls_w_shp = []
        self.ls_w_bazie = []
        self.brakujace_ls_w_shp = []
        self.brakujace_ls_w_bazie = []
        self.pow_zerowe_baza = []
        self.lista_mikro = []
        self.lista_zm_sq = []
        self.lista_zm_au = []
        self.lista_bez_uzytkow = []  # lista PARCELID bez uzytkow
        self.lista_podm_ls = []
        self.ile_podm_ls = 0
        self.rozb_pow = []

    def zestaw_dane(self):
        """Metoda zbiorcza do zestawienia wszystkich niezbednych tablic
        """
        self.zestaw_uzytki()
        self.zestaw_liste_ls_w_shp()
        self.zestaw_ile_ls_bazie()
        self.zestaw_liste_brakujacych_ls_w_shp()
        self.zestaw_liste_brakujacych_ls_w_bazie()
        self.zestaw_liste_zerowych_ls_w_bazie()
        self.zestaw_liste_mikro()
        self.zestaw_liste_zmienionych_sq()
        self.zestaw_liste_zmienionych_au()
        self.policz_podm_ls()

    def zestaw_uzytki(self):
        for ob in self.s.values():
            oki, do_spr, bl = ob.zwroc_ostateczne()
            self.uzytki += [x for x in oki.values()]

            # uwagi pow dla wydzielen
            self.rozb_pow += [[k, v[0], v[1]] for k, v in
                              ob.uwagi['pow'].items()]

    def zestaw_liste_ls_w_shp(self):
        if self.wl == 'OF':
            # ile ls w shp
            self.ls_w_shp = [x for x in self.uzytki
                             if x['AU'] == 'Ls' and
                             x['PARCELID'][4:] not in self.p.dz_op]

        else:
            # ile ls w shp
            self.ls_w_shp = [x for x in self.uzytki
                             if x['AU'] == 'Ls']

    def zestaw_ile_ls_bazie(self):
        if self.wl == 'OF':
            self.ls_w_bazie = len(
                [k for k in self.p.ls
                 if self.p.uzytki[k][3][4:] not in self.p.dz_op]
            ) + len(self.p.ls_podwojne)

        else:
            self.ls_w_bazie = len(self.p.ls) + len(self.p.ls_podwojne)

    def zestaw_liste_brakujacych_ls_w_shp(self):
        if self.wl == 'OF':
            self.brakujace_ls_w_shp = [
                [k, self.p.uzytki[k][2]] for k in self.p.ls
                if k not in [x['LANDID'] for x in self.ls_w_shp] and
                self.p.uzytki[k][3][4:] not in self.p.dz_op
            ]
        else:
            self.brakujace_ls_w_shp = [
                [k, self.p.uzytki[k][2]] for k in self.p.ls
                if k not in [x['LANDID'] for x in self.ls_w_shp]
            ]
            # [
            # [k, v[2]] for k, v in self.p.uzytki.items()
            # if k not in self.p.ls
            # ]

    def zestaw_liste_brakujacych_ls_w_bazie(self):
        if self.wl == 'OF':
            self.brakujace_ls_w_bazie = [
                [x['LANDID'], str(round(x.geometry().area()/10000, 4))]
                for x in self.ls_w_shp
                if x['LANDID'] not in self.p.ls and
                x['PARCELID'][4:] not in self.p.dz_op
            ]

        else:
            self.brakujace_ls_w_bazie = [
                [x['LANDID'], str(round(x.geometry().area()/10000, 4))]
                for x in self.ls_w_shp
                if x['LANDID'] not in self.p.ls
            ]

    def zestaw_liste_zerowych_ls_w_bazie(self):
        if self.wl == 'OF':
            # zestaw liste landid z powierzchniami zerowymi w bazie
            self.pow_zerowe_baza = [k for k in self.p.ls
                                    if self.p.uzytki[k][2] < 0.0001 and
                                    self.p.uzytki[k][3][4:]
                                    not in self.p.dz_op]

        else:
            # zestaw liste landid z powierzchniami zerowymi w bazie
            self.pow_zerowe_baza = [k for k in self.p.ls
                                    if self.p.uzytki[k][2] < 0.0001]

    def zestaw_liste_mikro(self):
        if self.wl == 'OF':
            mikro = [
                x.uwagi['mikro'] for x in self.s.values()
                if len(x.uwagi['mikro']) > 0 and
                x.uwagi['op'] is False
            ]
        else:
            mikro = [
                x.uwagi['mikro'] for x in self.s.values()
                if len(x.uwagi['mikro']) > 0
            ]

        for xx in mikro:
            self.lista_mikro += xx

    def zestaw_liste_zmienionych_sq(self):
        if self.wl == 'OF':
            sl = [
                x.uwagi['podmsq'] for x in self.s.values()
                if len(x.uwagi['podmsq']) > 0 and
                x.uwagi['op'] is False
            ]
        else:
            sl = [
                x.uwagi['podmsq'] for x in self.s.values()
                if len(x.uwagi['podmsq']) > 0
            ]
        for x in sl:
            self.lista_zm_sq += [[k, v[0], v[1]] for k, v in x.items()]

    def zestaw_liste_zmienionych_au(self):
        if self.wl == 'OF':
            sl = [
                x.uwagi['podmau'] for x in self.s.values()
                if len(x.uwagi['podmau']) > 0 and
                x.uwagi['op'] is False
            ]
        else:
            sl = [
                x.uwagi['podmau'] for x in self.s.values()
                if len(x.uwagi['podmau']) > 0
            ]

        for x in sl:
            self.lista_zm_au += [[k, v[0], v[1]] for k, v in x.items()]

    def policz_podm_ls(self):
        if self.wl == 'OF':
            self.lista_podm_ls = [
                x for x in self.s.values()
                if x.uwagi['podm'] is True and x.uwagi['op'] is False
            ]
            self.ile_podm_ls = len(self.lista_podm_ls)
        else:
            self.lista_podm_ls = [
                x for x in self.s.values() if x.uwagi['podm']
            ]
            self.ile_podm_ls = len(self.lista_podm_ls)

    def zestaw_liste_bez_uzytkow(self):
        if self.wl == 'OF':
            self.lista_bez_uzytkow = [x.pid for x in self.s.values()
                                      if x.bez_uzytkow and
                                      not x.uwagi['op']]
        else:
            self.lista_bez_uzytkow = [x.pid for x in self.s.values()
                                      if x.bez_uzytkow]

    def generuj_raport(self):  # noqa
        """Metoda generuj raport zapisany w zmiennej self.wypis"""
        self.wypis += 'Ls w shp: ' + str(len(self.ls_w_shp)) + '\n'
        self.wypis += 'Ls w bazie: ' + str(self.ls_w_bazie) + '\n\n'

        if len(self.p.ls_podwojne) > 0:
            self.wypis += '-->Dzkat ze zdublowanymi Ls w bazie: ' + \
                str(len(self.p.ls_podwojne)) + '\n'

        if len(self.pow_zerowe_baza) > 0:
            self.wypis += '-->Ls z zerową pow w bazie: ' + \
                str(len(self.pow_zerowe_baza)) + '\n'

        if len(self.lista_mikro) > 0:
            self.wypis += 'Ls z mikro pow po rozbiciu na poligony: ' + \
                str(len(self.lista_mikro)) + '\n'

        if self.ile_podm_ls > 0:
            self.wypis += 'Działki z zastąpionymi Ls-ami: ' + \
                str(self.ile_podm_ls) + '\n'

        if len(self.lista_bez_uzytkow) > 0:
            self.wypis += 'Działki bez Ls-ów: ' + \
                str(len(self.lista_bez_uzytkow)) + '\n'

        self.wypis += '\nBrakujących Ls-ów w [w shp]: ' + \
            str(len(self.brakujace_ls_w_shp)) + '\n'

        self.wypis += 'Brakujących Ls-ów [w bazie]: ' + \
            str(len(self.brakujace_ls_w_bazie)) + '\n\n'

        self.wypis == '\n\n'

        if len(self.p.ls_podwojne) > 0:
            self.wypis += '---POWÓJNE LS [BAZA]----------\n'
            self.wypis += 'Podwójne Ls-y: ' + \
                str(len(self.p.ls_podwojne)) + '\n\n'
            sort_temp = sorted(self.p.ls_podwojne)
            self.wypis += '\n'.join(sort_temp)
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.brakujace_ls_w_shp) > 0:
            self.wypis += '---BRAKUJĄCE LSy [W SHP]----------\n'
            self.wypis += 'Brakujących Ls-ów: ' + \
                str(len(self.brakujace_ls_w_shp)) + '\n\n'
            sort_temp = sorted(self.brakujace_ls_w_shp, key=lambda x: x[0])
            self.wypis += '\n'.join([
                '\t'.join([x[0], str(x[1])]) for x in
                sorted(sort_temp, key=lambda x: 0 if 'Ls' in x[0] else 1)
            ])
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.brakujace_ls_w_bazie) > 0:
            self.wypis += '---BRAKUJĄCE LSy [W BAZIE]--------\n'
            self.wypis += 'Brakujących Ls-ów: ' + \
                str(len(self.brakujace_ls_w_bazie)) + '\n\n'
            # sort_temp = sorted(self.brakujace_ls_w_bazie, key=lambda x: x[0])
            self.wypis += '\n'.join([
                '\t'.join([x[0], str(x[1])]) for x in
                # sorted(sort_temp, key=lambda x: 0 if 'Ls' in x[0] else 1)
                self.brakujace_ls_w_bazie
            ])
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.lista_bez_uzytkow) > 0:
            self.wypis += '---DZIALKI BEZ UŻYTKÓW------------\n'
            self.wypis += 'Dzialki z brakujacymi Ls-ami: ' + \
                str(len(self.lista_bez_uzytkow)) + '\n\n'
            self.wypis += '\n'.join([x for x in
                                     sorted(self.lista_bez_uzytkow)])
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.lista_bez_uzytkow) > 0:
            self.wypis += '---DZIALKI Z PODMIENIONYMI LSami--\n'
            self.wypis += 'Dzialki z zastąpionymi Ls-ami: ' + \
                str(len(self.ile_podm_ls)) + '\n\n'
            self.wypis += '\n'.join([x for x in
                                     sorted(self.lista_podm_ls)])
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.lista_zm_sq) > 0:
            self.wypis += '---PODMIENIONE KLASY LS [W SHP]---\n'
            self.wypis += 'Lsy w warstwie z podmienionymi SQ: ' + \
                str(len(self.lista_zm_sq)) + '\n\n'
            self.wypis += 'landid\tstary sq\tnowy sq\n'
            self.wypis += '\n'.join([
                '\t'.join(x) for x in
                sorted(self.lista_zm_sq, key=lambda x: x[0])
            ])
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.lista_zm_au) > 0:
            self.wypis += '---PRZEMIANOWANE NA LS [W SHP]----\n'
            self.wypis += 'Lsy w warstwie z podmienionymi AU/SQ: ' + \
                str(len(self.lista_zm_au)) + '\n\n'
            self.wypis += 'landid\tstary aU\tnowy au\n'
            self.wypis += '\n'.join([
                '\t'.join(x) for x in
                sorted(self.lista_zm_au, key=lambda x: x[0])
            ])
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.pow_zerowe_baza) > 0:
            self.wypis += '---LSy z ZEROWĄ POW---------------\n'
            self.wypis += 'Ls z zerową pow w bazie: ' + \
                str(len(self.pow_zerowe_baza)) + '\n\n'
            self.wypis += '\n'.join(self.pow_zerowe_baza)
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.lista_mikro) > 0:
            self.wypis += '---MIKRO LSy (<21 m2)-------------\n'
            self.wypis += 'Mikro Ls, po rozbiciu Ls na poligony: ' + \
                str(len(self.lista_mikro)) + '\n\n'
            self.wypis += '\n'.join(self.lista_mikro)
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        if len(self.rozb_pow) > 0:
            self.wypis += '---LS ZE ZNACZNĄ RÓŻNICĄ POW.-----\n'
            self.wypis += 'Ls z dużą rozbieżnością powierzchni: ' + \
                str(len(self.rozb_pow)) + '\n\n'
            self.wypis += 'adr_les\tpow_graf\tpow_rej\troznica\n'
            try:

                rr = sorted([x + [round(abs(x[1] - x[2]), 4)]
                             for x in self.rozb_pow
                             ],
                            reverse=True, key=lambda x: x[3])
                self.wypis += '\n'.join(["\t".join(map(str, x)) for x in rr])
            except:  # nopep8
                self.wypis += 'Coś poszło nie tak jak powinno!'
            self.wypis += '\n' + 33 * '-' + '\n\n\n'

        self.wypis += '\n-----[ KONIEC RAPORTU ]------'
        return self.wypis


class PobierzDane(QDialog):
    def __init__(self, k=False, d=False):
        super(PobierzDane, self).__init__()

        self.kontynuuj = False
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.lyrk = k
        self.lyrd = d
        self.pola = []
        self.ile_baz = 0
        self.ui.comboBox_ident.setDisabled(True)

        # Jezeli jest warstwa klu, odczytaj jej dane
        if self.lyrk is not False:
            if self.lyrk.isValid():
                self.ui.lineEdit_klu.setText(
                    self.lyrk.dataProvider().dataSourceUri().split("|")[0])
                self.ui.comboBox_ident.setDisabled(False)
                self.wczytaj_pola()

        # Jezeli jest warstwa dzkat, odczytaj jej dane
        if self.lyrd is not False:
            if self.lyrd.isValid():
                self.ui.lineEdit_dzkat.setText(
                    self.lyrd.dataProvider().dataSourceUri().split("|")[0])

        self.ui.pushButton_klu.clicked.connect(self.pobierz_klu)
        self.ui.pushButton_dzkat.clicked.connect(self.pobierz_dzkat)
        self.ui.pushButton_bazy.clicked.connect(self.pobierz_bazy)
        self.ui.comboBox_ident.currentTextChanged.connect(self.identyfikuj)
        self.ui.pushButton_ok.clicked.connect(self.zatwierdz)

    def zatwierdz(self):
        self.kontynuuj = True

    def wczytaj_pola(self):
        """Metoda uzupelnia comboboxy na podstawie podanej warstwy"""
        # wybierz nazwy pol z warstwy, ktore nie sa numeryczne
        self.pola = ['---'] + [x.name() for x in self.lyrk.dataProvider(
                                    ).fields().toList() if not x.isNumeric()]

        # wyczysc wszystkie comboboxy z kolumnami
        comboboxy = [
            self.ui.comboBox_sq,
            self.ui.comboBox_au,
            self.ui.comboBox_landid,
        ]

        # wyczysc i dodaj przetworzone pola do comboboxow
        for x in comboboxy:
            x.clear()
            x.addItems(self.pola)

    def pobierz_klu(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę i ją przetwarza"""
        if self.lyrd:
            kat = os.path.dirname(
                self.lyrd.dataProvider().dataSourceUri().split("|")[0])

        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę',
                                                kat,
                                                "ESRI shp (*.shp)")[0]
        try:
            self.lyrk = QgsVectorLayer(warstwa, "klu", "ogr")
            self.ui.lineEdit_klu.setText(
                self.lyrk.dataProvider().dataSourceUri().split("|")[0])
            self.ui.comboBox_ident.setDisabled(False)
            self.wczytaj_pola()
        except:  # nopep8
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText(
                'Nie udało się odnaleźć podanej warstwy')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

            self.lyrk = False
            self.ui.comboBox_ident.setDisabled(True)

    def pobierz_dzkat(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę i ją przetwarza"""
        if self.lyrk:
            kat = os.path.dirname(
                self.lyrk.dataProvider().dataSourceUri().split("|")[0])
        warstwa = QFileDialog().getOpenFileName(self,
                                                'Wskaż warstwę',
                                                kat,
                                                "ESRI shp (*.shp)")[0]
        try:
            self.lyrd = QgsVectorLayer(warstwa, "dz", "ogr")
            self.ui.lineEdit_dzkat.setText(
                self.lyrd.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText(
                'Nie udało się odnaleźć podanej warstwy')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

            self.lyrd = False

    def pobierz_bazy(self):
        """Metoda pobiera wskazany przez użytkownika katalog"""
        kat = ""
        if self.lyrk:
            kat = os.path.dirname(self.lyrk.dataProvider().dataSourceUri(
                                                            ).split("|")[0])
        bazy_kat = QFileDialog().getExistingDirectory(
            self,
            "Katalog z bazami danych",
            kat)

        if platform.system()[:3] == 'Win':
            self.ile_baz = len(glob.glob(os.path.join(bazy_kat, '*.mdb')))
        else:
            self.ile_baz = len(glob.glob(os.path.join(bazy_kat, '*.sqlite')))
        # self.ile_baz = len(glob.glob(os.path.join(bazy_kat, '*.mdb')))

        if self.ile_baz > 0:
            self.ui.label_bazy.setText("Znalazałem baz: "+str(self.ile_baz))
            self.ui.lineEdit_bazy.setText(bazy_kat)

        else:
            self.ui.label_bazy.setText("Nie znaleziono baz danych")

    def identyfikuj(self):
        """ Metoda sprawdza wybór uzytkownika i
            udostepnia odpowiednie pola do wyboru"""
        if self.ui.comboBox_ident.currentText() == '---':
            self.ui.groupBox_adradm.setDisabled(True)
            self.ui.groupBox_kol.setDisabled(True)
            self.ui.pushButton_ok.setDisabled(True)
        elif self.ui.comboBox_ident.currentText()[:3] == 'AU ':
            self.ui.groupBox_adradm.setDisabled(True)
            self.ui.pushButton_ok.setDisabled(False)
            self.ui.groupBox_kol.setDisabled(False)
        elif self.ui.comboBox_ident.currentText()[:3] == 'LAN':
            self.ui.groupBox_adradm.setDisabled(False)
            self.ui.pushButton_ok.setDisabled(False)
            self.ui.groupBox_kol.setDisabled(True)
