import os
import glob
import platform

from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox

from qgis.core import (
    Qgis, QgsVectorLayer, QgsField, QgsMessageLog, QgsProject,
    QgsVectorFileWriter, QgsCoordinateReferenceSystem,
)
from PyQt5.QtCore import QVariant

from .baza_wrapper import Baza
from .funkcje import isNone
from .ui.ui_wydzielenia_ls import Ui_Dialog
from .przygotuj_ls import PrzygotujLs, AnalizujKlus, PrzetworzKlu


class PobierzDaneWydzielenia(QDialog):
    """Jak PobierzDane (przygotuj_ls.py), ale bez wyboru sposobu
    identyfikacji uzytkow - warstwa wydzielen niesie wylacznie kontur,
    bez zadnej klasyfikacji do odczytania."""

    def __init__(self, k=False, d=False):
        super(PobierzDaneWydzielenia, self).__init__()

        self.kontynuuj = False
        self.kat = ''
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.lyrk = k
        self.lyrd = d

        if self.lyrk is not False:
            if self.lyrk.isValid():
                self.ui.lineEdit_wydzielenia.setText(
                    self.lyrk.dataProvider().dataSourceUri().split("|")[0])

        if self.lyrd is not False:
            if self.lyrd.isValid():
                self.ui.lineEdit_dzkat.setText(
                    self.lyrd.dataProvider().dataSourceUri().split("|")[0])

        self.ui.pushButton_wydzielenia.clicked.connect(
            self.pobierz_wydzielenia)
        self.ui.pushButton_dzkat.clicked.connect(self.pobierz_dzkat)
        self.ui.pushButton_bazy.clicked.connect(self.pobierz_bazy)
        self.ui.lineEdit_wydzielenia.textChanged.connect(self._aktualizuj_ok)
        self.ui.lineEdit_dzkat.textChanged.connect(self._aktualizuj_ok)
        self.ui.lineEdit_bazy.textChanged.connect(self._aktualizuj_ok)
        self.ui.pushButton_ok.clicked.connect(self.zatwierdz)

        self._aktualizuj_ok()

    def zatwierdz(self):
        self.kontynuuj = True

    def pobierz_wydzielenia(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę"""
        if self.lyrd:
            self.kat = os.path.dirname(
                self.lyrd.dataProvider().dataSourceUri().split("|")[0])

        warstwa = QFileDialog().getOpenFileName(
            self, 'Wskaż warstwę wydzieleń', self.kat,
            "ESRI shp (*.shp)")[0]
        if warstwa == '':
            return
        try:
            self.lyrk = QgsVectorLayer(warstwa, "wydzielenia", "ogr")
            self.ui.lineEdit_wydzielenia.setText(
                self.lyrk.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Nie udało się odnaleźć podanej warstwy')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()
            self.lyrk = False

    def pobierz_dzkat(self):
        """Metoda pobiera wskazaną przez użytkownika warstwę"""
        if self.lyrk:
            self.kat = os.path.dirname(
                self.lyrk.dataProvider().dataSourceUri().split("|")[0])

        warstwa = QFileDialog().getOpenFileName(
            self, 'Wskaż warstwę', self.kat, "ESRI shp (*.shp)")[0]
        if warstwa == '':
            return
        try:
            self.lyrd = QgsVectorLayer(warstwa, "dz", "ogr")
            self.ui.lineEdit_dzkat.setText(
                self.lyrd.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Nie udało się odnaleźć podanej warstwy')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()
            self.lyrd = False

    def pobierz_bazy(self):
        """Metoda pobiera wskazany przez użytkownika katalog"""
        if self.lyrk:
            self.kat = os.path.dirname(
                self.lyrk.dataProvider().dataSourceUri().split("|")[0])

        bazy_kat = QFileDialog().getExistingDirectory(
            self, "Katalog z bazami danych", self.kat)
        if bazy_kat == '':
            return

        if platform.system()[:3] == 'Win':
            ile_baz = len(glob.glob(os.path.join(bazy_kat, '*.mdb')))
        else:
            ile_baz = len(glob.glob(os.path.join(bazy_kat, '*.sqlite')))

        if ile_baz > 0:
            self.ui.label_bazy.setText("Znalazłem baz: " + str(ile_baz))
            self.ui.lineEdit_bazy.setText(bazy_kat)
        else:
            self.ui.label_bazy.setText("Nie znaleziono baz danych")

    def _aktualizuj_ok(self, *_):
        ok = (self.ui.lineEdit_wydzielenia.text().strip() != '' and
              self.ui.lineEdit_dzkat.text().strip() != '' and
              self.ui.lineEdit_bazy.text().strip() != '')
        self.ui.pushButton_ok.setEnabled(ok)


class PrzetworzWydzielenia(PrzetworzKlu):
    """Jak PrzetworzKlu, ale z dodatkową obsługą działek mających w bazie
    więcej niż jeden rekord Ls o różnej bonitacji (SQ) - bez wskazówki
    graficznej nie da się automatycznie przypisać SQ do konkretnego
    kawałka geometrii, więc taka działka trafia do ręcznego przecięcia
    zamiast normalnej ścieżki dopasowania."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # feat-y do osobnej warstwy LS_do_przeciecia
        self.klus_do_przeciecia = []
        # klucze w self.poprawne, ktorym trzeba pozniej wyczyscic LANDID
        self._klucze_do_przeciecia = []

    def s_ma_wiele_sq(self):
        """Zwraca True jeśli działka ma w bazie więcej niż jeden rekord
        Ls (różne SOIL_QUALITY_CD) - nie da się automatycznie przypisać
        SQ do geometrii wydzielenia bez wskazówki graficznej."""
        return (self.pid in self.p.sl_ls_na_dz and
                len(self.p.sl_ls_na_dz[self.pid]) > 1)

    def s_dopisz_do_przeciecia(self):
        """Dla działki z wieloma SQ w bazie: tworzy placeholder-feature
        (AU='Ls' jak reszta, ale bez LANDID/SQ) łączący geometrię
        wszystkich self.klus (zwykle już 1 element dzięki dissolve po
        PARCELID w geop_przetworz) - dodaje do klus_do_przeciecia (nowa,
        trwała warstwa) i do self.poprawne pod syntetycznym kluczem, żeby
        pojawił się też w głównej warstwie LS."""
        geom = self.klus[0].geometry()
        for k in self.klus[1:]:
            geom = geom.combine(k.geometry())
        geom.convertToMultiType()

        f = self.new_feat(
            au='Ls',
            uw='Wiele SQ na działce - wymaga ręcznego przecięcia; ')
        f.setGeometry(geom)

        self.klus_do_przeciecia.append(f)

        klucz = self.pid + '.DOPRZECIECIA'
        self.poprawne[klucz] = f
        self._klucze_do_przeciecia.append(klucz)

    def dopisz_uwagi_pow(self):
        super().dopisz_uwagi_pow()
        # dopisz_uwagi_pow() bezwarunkowo wpisuje klucz slownika jako
        # LANDID - dla wpisow do przeciecia to syntetyczny klucz, ktory
        # trzeba wyczyscic z powrotem (LANDID ma zostac pusty). AU/SQ nie
        # sa tam w ogole dotykane (AU juz ustawione na 'Ls', SQ zostaje
        # puste), LAND_AR i tak zostaje pusty (syntetyczny klucz nigdy
        # nie pasuje do self.p.uzytki).
        for klucz in self._klucze_do_przeciecia:
            item = self.poprawne[klucz]
            item.setAttribute(item.fieldNameIndex('LANDID'), None)


class AnalizujWydzielenia(AnalizujKlus):
    """Jak AnalizujKlus, ale zrodlem geometrii jest warstwa wydzielen bez
    zadnej klasyfikacji uzytkow (nie KLU) - cala warstwa jest traktowana
    jako uzytek Ls, AU/SQ dociagane per dzialka z bazy taksatora."""

    def pobierz_dane_od_uzytkownika(self):
        self.dd = PobierzDaneWydzielenia(self.klu, self.dzkat)
        self.dd.exec_()

        if self.dd.kontynuuj:
            return True
        return False

    def przetworz(self):
        self.klu = QgsVectorLayer(
            self.dd.ui.lineEdit_wydzielenia.text(), 'wydzielenia', 'ogr')
        self.dzkat = QgsVectorLayer(
            self.dd.ui.lineEdit_dzkat.text(), 'dz', 'ogr')

        self.klu.dataProvider().setEncoding('UTF-8')

        if platform.system()[:3] == 'Win':
            self.bazy = glob.glob(
                os.path.join(self.dd.ui.lineEdit_bazy.text(), '*.mdb'))
        else:
            self.bazy = glob.glob(
                os.path.join(self.dd.ui.lineEdit_bazy.text(), '*.sqlite'))

        self.wl = self.dd.ui.comboBox_wlas.currentText()[:2]

        self.uzytki = []
        self.wlasnosci = []

        QgsMessageLog.logMessage(
            'Znaleziono bazy: ' + ', '.join(self.bazy), "Las-R", Qgis.Info)
        for baza in self.bazy:
            b = Baza(baza)
            if b.polacz():
                b.kapitaliki_w_klasach()
                b.napraw_area_use_myslnik()
                self.uzytki += b.uzytki()
                self.wlasnosci += b.wlasnosci()
            else:
                QgsMessageLog.logMessage(
                    'Nie udało połączyć się z: ' + baza, "Las-R",
                    Qgis.Warning)
                self.iface.messageBar.pushWarning(
                    'Uwaga', 'Nie udało się odczytać bazy: ' + baza,
                    Qgis.Warning)

    def przygotuj_do_analizy(self):
        """Nie derywujemy SQ/AU/KLU z warstwy wydzieleń - nie ma z czego
        (warstwa niesie wyłącznie kontur). AU jest ustawiane na sztywno
        'Ls' w geop_przetworz(), SQ dociągane później per działka."""
        pass

    def geop_przetworz(self):  # noqa
        """Jak AnalizujKlus.geop_przetworz, ale bez v.dissolve po klasie
        (wydzielenia nie mają pola do dissolve'a) i z dissolve po
        PARCELID PO intersekcie (scala pofragmentowane wydzielenia tej
        samej działki w jeden, ew. multipart, obiekt) zamiast
        multiparttosingleparts."""
        import processing

        sciezka = self.klu.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.tempkat = os.path.join(self.kat, 'temp')
        if not os.path.isdir(self.tempkat):
            os.mkdir(self.tempkat)

        # v.overlay: wydzielenia (self.klu) x dzialki, bez wczesniejszego
        # dissolve po klasie
        alg_params = {
            '-t': False,
            'GRASS_MIN_AREA_PARAMETER': 0.1,
            'GRASS_OUTPUT_TYPE_PARAMETER': 0,
            'GRASS_REGION_PARAMETER': None,
            'GRASS_SNAP_TOLERANCE_PARAMETER': 0.05,
            'GRASS_VECTOR_DSCO': '',
            'GRASS_VECTOR_EXPORT_NOCAT': False,
            'GRASS_VECTOR_LCO': '',
            'ainput': self.klu,
            'atype': 0,
            'binput': self.dzkat,
            'btype': 0,
            'operator': 0,
            'snap': 0.05,
            'output': os.path.join(
                self.tempkat, '__LS_overlay_' + self.czas + '.gpkg')
        }
        processing.run('grass7:v.overlay', alg_params)

        ovrlyr = QgsVectorLayer(
            os.path.join(self.tempkat, '__LS_overlay_' + self.czas + '.gpkg'),
            'templyr_ovr', 'ogr')
        ovrlyr.dataProvider().setEncoding('UTF-8')

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
            if old[:2] in ['a_', 'b_']:
                ovrlyr.renameAttribute(id, old[2:])
        ovrlyr.commitChanges()

        pola = [x.name() for x in ovrlyr.dataProvider().fields()]
        pola_dodaj = []
        if 'SQ' not in pola:
            pola_dodaj.append(QgsField("SQ", QVariant.String, len=10))
        if 'AU' not in pola:
            pola_dodaj.append(QgsField("AU", QVariant.String, len=10))
        if 'COMMUNITY' not in pola:
            pola_dodaj.append(QgsField("COMMUNITY", QVariant.String, len=4))

        if len(pola_dodaj) > 0:
            ovrlyr.startEditing()
            ovrlyr.dataProvider().addAttributes(pola_dodaj)
            ovrlyr.updateFields()
            ovrlyr.commitChanges()

        klu_fnm = ovrlyr.dataProvider().fieldNameMap()
        iau = klu_fnm['AU']
        isq = klu_fnm['SQ']
        icom = klu_fnm['COMMUNITY']

        sl_podm = {}
        for f in ovrlyr.getFeatures():
            # cala warstwa wydzielen to Ls - SQ nieznane na tym etapie,
            # dociagane pozniej per dzialka (PrzetworzWydzielenia)
            sl = {iau: 'Ls', isq: ''}
            if isNone(f['COMMUNITY']):
                if 'PARCELID' in pola:
                    sl[icom] = isNone(f['PARCELID'])[7:10]
            sl_podm[f.id()] = sl

        for fid, sl in sl_podm.items():
            ovrlyr.dataProvider().changeAttributeValues({fid: sl})

        # dissolve po PARCELID - scala pofragmentowane wydzielenia tej
        # samej dzialki w jeden (ew. multipart) obiekt, zamiast
        # multiparttosingleparts
        alg_params_diss = {
            'GRASS_MIN_AREA_PARAMETER': 0.1,
            'GRASS_OUTPUT_TYPE_PARAMETER': 0,
            'GRASS_REGION_PARAMETER': None,
            'GRASS_SNAP_TOLERANCE_PARAMETER': 0.05,
            'GRASS_VECTOR_DSCO': '',
            'GRASS_VECTOR_EXPORT_NOCAT': False,
            'GRASS_VECTOR_LCO': '',
            'column': 'PARCELID',
            'input': ovrlyr,
            'output': os.path.join(
                self.tempkat, '__LS_dissolve_pid_' + self.czas + '.gpkg')
        }
        processing.run('grass7:v.dissolve', alg_params_diss)

        dslyr = QgsVectorLayer(
            os.path.join(
                self.tempkat, '__LS_dissolve_pid_' + self.czas + '.gpkg'),
            'templyr_diss_pid', 'ogr')
        dslyr.dataProvider().setEncoding('UTF-8')

        if not dslyr.isValid():
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się scalić wydzieleń po PARCELID (dissolve)...'
                ' Sprawdź czy masz uruchomionego qgisa z grass\'em',
                Qgis.Critical, 10
            )
            return False

        # v.dissolve zachowuje zwykle tylko kolumne dissolve'a (PARCELID)
        # - dopisz z powrotem AU/SQ (stale dla calej warstwy, nic nie
        # trzeba wyszukiwac)
        pola2 = [x.name() for x in dslyr.dataProvider().fields()]
        pola_dodaj2 = []
        if 'SQ' not in pola2:
            pola_dodaj2.append(QgsField("SQ", QVariant.String, len=10))
        if 'AU' not in pola2:
            pola_dodaj2.append(QgsField("AU", QVariant.String, len=10))

        if len(pola_dodaj2) > 0:
            dslyr.startEditing()
            dslyr.dataProvider().addAttributes(pola_dodaj2)
            dslyr.updateFields()
            dslyr.commitChanges()

        dfnm = dslyr.dataProvider().fieldNameMap()
        diau = dfnm['AU']
        disq = dfnm['SQ']
        sl_podm2 = {
            f.id(): {diau: 'Ls', disq: ''} for f in dslyr.getFeatures()}
        dslyr.dataProvider().changeAttributeValues(sl_podm2)

        # nazwa zmiennej zachowana dla zgodnosci z reszta AnalizujKlus -
        # to juz nie singleparts, tylko 1 (ew. multipart) obiekt/dzialke
        self.singleparts = dslyr
        return True

    def zaladuj_strukture(self):
        """Jak AnalizujKlus.zaladuj_strukture, ale buduje
        PrzetworzWydzielenia zamiast PrzetworzKlu."""
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

            self.strukt[key] = PrzetworzWydzielenia(val, k, self.p, self.wl)

    def przetworz_strukture(self):
        """Jak AnalizujKlus.przetworz_strukture, z dodatkową gałęzią dla
        działek z wieloma SQ w bazie (patrz s_ma_wiele_sq/
        s_dopisz_do_przeciecia)."""
        for key, val in self.strukt.items():
            if not val.is_valid():
                self.bledne.append(key)
                continue

            trig = 0
            val.przetworz()
            val.sprawdz_topologie()
            if not val.s_czy_dz_w_bazie():
                continue

            if val.s_czy_ls_na_calosci():
                trig = 1

            wiele_sq = False
            if trig == 0:
                wiele_sq = val.s_ma_wiele_sq()
                if wiele_sq:
                    val.s_dopisz_do_przeciecia()
                elif val.s_czy_jeden_ls():
                    trig = 2

            if trig in [0, 2] and not wiele_sq:
                val.s_dopisz_uzyt()
                val.sprawdz_mikro()

            val.polacz_ostateczne()
            val.dopisz_uwagi_pow()

    def generuj_warstwy(self):
        super().generuj_warstwy()
        self._generuj_warstwe_do_przeciecia()

    def _generuj_warstwe_do_przeciecia(self):
        """Zbiera placeholdery z wszystkich PrzetworzWydzielenia i zapisuje
        jako trwałą warstwę LS_do_przeciecia (ten sam wzorzec co
        LS/LS_BLEDY/LS_DO_SPRAWDZENIA - memory jako bufor, potem zapis do
        .shp w self.kat, przeładowanie jako warstwa ogr, dodanie do
        projektu)."""
        do_przeciecia = []
        for sit in self.strukt.values():
            do_przeciecia += sit.klus_do_przeciecia

        if len(do_przeciecia) == 0:
            return

        crs = QgsCoordinateReferenceSystem("epsg:2180")

        lyr = QgsVectorLayer(
            "MultiPolygon?crs=epsg:2180&index=yes",
            "LS_DO_PRZECIECIA__" + self.czas, "memory")
        lyr.startEditing()
        lyr.dataProvider().addAttributes(self.kolumny_dz + self.kolumny_ls)
        lyr.updateFields()
        lyr.dataProvider().addFeatures(do_przeciecia)
        lyr.commitChanges()

        QgsVectorFileWriter.writeAsVectorFormat(
            lyr,
            os.path.join(self.kat, "LS_DO_PRZECIECIA_" + self.czas + ".shp"),
            "UTF-8", crs, "ESRI Shapefile")

        QgsMessageLog.logMessage(
            "Warstwa LS_DO_PRZECIECIA zapisana!", "Las-R", Qgis.Info)

        lyr = self.iface.addVectorLayer(
            os.path.join(self.kat, "LS_DO_PRZECIECIA_" + self.czas + ".shp"),
            "LS_DO_PRZECIECIA_" + self.czas,
            "ogr"
        )
        QgsProject.instance().addMapLayer(lyr)


class PrzygotujLsZWydzielen(PrzygotujLs):
    """Jak PrzygotujLs, ale zrodlem geometrii jest warstwa wydzielen
    (WYDZ...) zamiast KLU. wczytaj/sprawdz/przygotuj/przetworz
    dziedziczone bez zmian - cala roznica siedzi w self.a."""

    def sprawdz_warstwy(self):
        k = False  # wydzielenia - warstwa
        d = False  # dzialki - warstwa

        QgsMessageLog.logMessage(
            '\n-----[ SPRAWDZENIE LS Z WYDZIELEŃ ]-----', 'Las-R', Qgis.Info
        )

        for key, lyr in QgsProject.instance().mapLayers().items():
            if key[:5] == 'DZKAT':
                d = lyr
            if key[:4] == 'WYDZ':
                k = lyr

        self.a = AnalizujWydzielenia(self.iface, k, d)
        return True
