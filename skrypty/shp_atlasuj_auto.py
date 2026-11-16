import os

from qgis.core import (
    QgsField, QgsVectorLayer, QgsGeometry, QgsRectangle, QgsFeature,
    QgsCoordinateReferenceSystem, QgsVectorFileWriter, QgsProject,
    QgsSpatialIndex, QgsWkbTypes,
)
from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QDialog
from .przyciski import QMessageBox

from . import kafelkowanie
from .ui.ui_atlasuj_auto import Ui_Dialog


# nachodzenie sasiednich stron atlasu (czesc wspolna do nawiazania) -
# ulamek wymiaru strony, z kazdej strony kafla
ZAKLADKA = 0.05

# wydzielenia odlegle od siebie najwyzej o tyle metrow tworza kompleks
# (droga czy row, ktore nie sa wydzieleniem, nie rozbijaja kompleksu)
PROG_KOMPLEKSU = 20.0

# pola numeracji wymagane w warstwie ATLAS_AFT
_POLA_NUMERACJI = ('STRONA', 'L', 'G', 'P', 'D')


def _plik_warstwy(lyr):
    """Znormalizowana ścieżka pliku warstwy ('' gdy brak)."""
    try:
        sc = lyr.dataProvider().dataSourceUri().split('|')[0]
    except Exception:
        return ''
    return os.path.normcase(os.path.abspath(sc)) if sc else ''


def _prostokat(bb):
    return (bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum())


class GenerujAtlasAuto:
    """ Automatycznie generuje pola atlasowe (jak "Rysuj pola atlasowe"),
    kafelkowanie.pokryj_atlas: rozproszone wydzielenia i kompleksy
    mieszczące się na jednej stronie - każde wydzielenie w całości na
    stronie; kompleks większy niż strona - regularna siatka stron
    nachodzących na siebie o ZAKLADKA wymiaru (pas wspólny do nawiązania),
    wydzielenia kompleksu są cięte krawędzią strony. Numeracja STRONA
    i sąsiedzi L/G/P/D powstają automatycznie (kafelkowanie.numeruj_kafle),
    bez ręcznego digitalizowania linii (jak w "Numeruj pola atlasu").
    """

    def __init__(self, iface):
        self.iface = iface
        self.lyr = False
        self.kat = ''
        self.rozm = []  # rozmiar kafla w metrach [szer, wys]
        self.pola = False

    def wybierz_warstwe(self):
        self.lyr = self.iface.activeLayer()
        if self.lyr is None or self.lyr.wkbType() not in [3, 6]:
            self.iface.messageBar().pushWarning(
                'Atlasuj automatycznie',
                'Zaznacz warstwę powierzchniową do zaatlasowania'
            )
            return False

        try:
            self.kat = os.path.dirname(
                self.lyr.dataProvider().dataSourceUri().split("|")[0])
        except:  # nopep8
            self.iface.messageBar().pushWarning(
                'Atlasuj automatycznie',
                'Nie udało się ustalić katalogu warstwy'
            )
            return False
        return True

    def pobierz_dane(self):
        self.d = PobierzDane()
        self.d.exec_()

        if self.d.porzuc:
            return False

        self.rozm = self.d.wynik
        return True

    def _kompleksy(self):
        """ Zwraca (bboxy wydzieleń, kompleksy) dla
        kafelkowanie.pokryj_atlas. Kompleks to wydzielenia oddalone od
        siebie najwyżej o PROG_KOMPLEKSU (łącznie przez łańcuch sąsiadów),
        więc droga albo rów, które nie są wydzieleniem, nie rozbijają
        kompleksu. Każdy kompleks to (bbox, przecina, [indeksy wydzieleń]),
        gdzie przecina(strona) sprawdza faktyczną geometrię wydzieleń
        kompleksu (przygotowanym silnikiem GEOS). """
        geometrie = []
        bboxy = []
        indeks = QgsSpatialIndex()
        for f in self.lyr.getFeatures():
            g = f.geometry()
            if g is None or g.isEmpty():
                continue
            indeks.addFeature(len(geometrie), g.boundingBox())
            geometrie.append(g)
            bboxy.append(_prostokat(g.boundingBox()))

        n = len(geometrie)
        rodzic = list(range(n))

        def korzen(i):
            while rodzic[i] != i:
                rodzic[i] = rodzic[rodzic[i]]
                i = rodzic[i]
            return i

        for i, g in enumerate(geometrie):
            x0, y0, x1, y1 = bboxy[i]
            okolica = QgsRectangle(x0 - PROG_KOMPLEKSU, y0 - PROG_KOMPLEKSU,
                                   x1 + PROG_KOMPLEKSU, y1 + PROG_KOMPLEKSU)
            for j in indeks.intersects(okolica):
                if j <= i:
                    continue
                ri, rj = korzen(i), korzen(j)
                if ri != rj and g.distance(geometrie[j]) <= PROG_KOMPLEKSU:
                    rodzic[ri] = rj

        grupy = {}
        for i in range(n):
            grupy.setdefault(korzen(i), []).append(i)

        silniki = {}

        def silnik(i):
            if i not in silniki:
                s = QgsGeometry.createGeometryEngine(geometrie[i].constGet())
                s.prepareGeometry()
                silniki[i] = s
            return silniki[i]

        def funkcja_przecina(czlonkowie):
            def przecina(strona):
                geom = QgsGeometry.fromRect(QgsRectangle(*strona))
                for i in czlonkowie:
                    b = bboxy[i]
                    if b[0] <= strona[2] and strona[0] <= b[2] and \
                            b[1] <= strona[3] and strona[1] <= b[3] and \
                            silnik(i).intersects(geom.constGet()):
                        return True
                return False
            return przecina

        kompleksy = []
        for czlonkowie in grupy.values():
            bbox = (min(bboxy[i][0] for i in czlonkowie),
                    min(bboxy[i][1] for i in czlonkowie),
                    max(bboxy[i][2] for i in czlonkowie),
                    max(bboxy[i][3] for i in czlonkowie))
            kompleksy.append((bbox, funkcja_przecina(czlonkowie), czlonkowie))
        return bboxy, kompleksy

    def generuj_pola(self):
        self.pola = QgsVectorLayer(
            "Polygon?crs=epsg:2180&index=yes", "ATLAS_AFT", "memory")
        self.pola.startEditing()
        self.pola.dataProvider().addAttributes([
            QgsField("STRONA", QVariant.Int),
            QgsField("L", QVariant.Int),
            QgsField("G", QVariant.Int),
            QgsField("P", QVariant.Int),
            QgsField("D", QVariant.Int),
            QgsField("ZROBIONE", QVariant.String, len=50),
        ])
        self.pola.updateFields()

        bboxy, kompleksy = self._kompleksy()
        kafle = kafelkowanie.pokryj_atlas(
            kompleksy, bboxy, self.rozm[0], self.rozm[1], ZAKLADKA)
        strony, sasiedzi = kafelkowanie.numeruj_kafle(kafle)

        nowe = []
        for i in sorted(range(len(kafle)), key=lambda i: strony[i]):
            x0, y0, x1, y1 = kafle[i]
            feat = QgsFeature()
            feat.setFields(self.pola.fields())
            feat.setGeometry(QgsGeometry.fromRect(
                QgsRectangle(x0, y0, x1, y1)))
            feat['STRONA'] = strony[i]
            for kierunek in 'LGPD':
                feat[kierunek] = sasiedzi[i][kierunek]
            nowe.append(feat)

        self.pola.dataProvider().addFeatures(nowe)
        self.pola.commitChanges()
        return len(kafle)

    def zapisz_warstwe(self):
        # usun poprzednia warstwe z TOC (zwalnia blokade pliku na Windows)
        # tylko warstwy z nadpisywanego pliku - nie zamykamy ATLAS_AFT
        # innych obiektów otwartych w tym samym projekcie
        plik = os.path.normcase(os.path.abspath(
            os.path.join(self.kat, 'ATLAS_AFT.shp')))
        stare = [l for l in QgsProject.instance().mapLayers().values()
                 if l.name() == 'ATLAS_AFT' and _plik_warstwy(l) == plik]
        if stare:
            QgsProject.instance().removeMapLayers([l.id() for l in stare])

        rozsz = ['shp', 'shx', 'dbf', 'prj', 'sbx', 'cpg', ]
        try:
            for r in rozsz:
                sciezka = os.path.join(self.kat, 'ATLAS_AFT.' + r)
                if os.path.isfile(sciezka):
                    os.remove(sciezka)
        except:  # nopep8
            self.iface.messageBar().pushCritical(
                'BŁĄD',
                'Nie udało się usunąć poprzedniej wersji plików '
                'ATLAS_AFT, proszę zamknąć warstwę w QGIS i ponownie '
                'uruchomić skrypt'
            )
            return False

        crs = QgsCoordinateReferenceSystem("epsg:2180")
        sciezka = os.path.join(self.kat, "ATLAS_AFT.shp")
        QgsVectorFileWriter.writeAsVectorFormat(
            self.pola, sciezka, "UTF-8", crs, "ESRI Shapefile")

        warstwa = QgsVectorLayer(sciezka, "ATLAS_AFT", "ogr")
        QgsProject.instance().addMapLayer(warstwa)

        plugin_dir = os.path.dirname(__file__)
        warstwa.loadNamedStyle(
            os.path.join(plugin_dir, '..', 'qml', 'ATLAS_AFT_spr.qml'))
        warstwa.triggerRepaint()
        return True

    def wyswietl_info(self, ile):
        if ile == 0:
            self.iface.messageBar().pushWarning(
                'Atlasuj automatycznie',
                'Warstwa wejściowa nie zawiera żadnych obiektów'
            )
            return

        self.iface.messageBar().pushSuccess(
            'OK',
            'Utworzono warstwę ATLAS_AFT z ' + str(ile) + ' polami'
        )


class PrzenumerujAtlas:
    """ Ponownie numeruje całą warstwę pól atlasu (STRONA i sąsiedzi
    L/G/P/D) po ręcznych poprawkach - przesunięciu, dorysowaniu albo
    usunięciu pól. Numeracja jak w "Atlasuj automatycznie"
    (kafelkowanie.numeruj_kafle): zespoły stykających się pól od góry,
    w zespole wierszami od góry, w wierszu od lewej. Pole bierze się pod
    uwagę po jego zasięgu (bbox). """

    TYTUL = 'Przenumeruj atlasy'

    def __init__(self, iface):
        self.iface = iface
        self.lyr = None
        self.ile = 0
        self.byla_edycja = False

    @staticmethod
    def _pasuje(lyr):
        return isinstance(lyr, QgsVectorLayer) and \
            lyr.geometryType() == QgsWkbTypes.PolygonGeometry and \
            all(lyr.fields().indexOf(p) != -1 for p in _POLA_NUMERACJI)

    def wybierz_warstwe(self):
        """ Aktywna warstwa, jeśli ma pola numeracji; w przeciwnym razie
        jedyna warstwa ATLAS_AFT w projekcie. """
        aktywna = self.iface.activeLayer()
        if self._pasuje(aktywna):
            self.lyr = aktywna
            return True

        atlasy = [l for l in QgsProject.instance().mapLayers().values()
                  if l.name() == 'ATLAS_AFT' and self._pasuje(l)]
        if len(atlasy) == 1:
            self.lyr = atlasy[0]
            return True

        self.iface.messageBar().pushWarning(
            self.TYTUL,
            'Zaznacz warstwę pól atlasu (poligony z polami '
            + ', '.join(_POLA_NUMERACJI) + ')'
        )
        return False

    def przenumeruj(self):
        fidy = []
        kafle = []
        for f in self.lyr.getFeatures():
            g = f.geometry()
            if g is None or g.isEmpty():
                continue
            fidy.append(f.id())
            kafle.append(_prostokat(g.boundingBox()))
        self.ile = len(kafle)
        if not kafle:
            self.iface.messageBar().pushWarning(
                self.TYTUL, 'Warstwa nie zawiera żadnych pól')
            return False

        strony, sasiedzi = kafelkowanie.numeruj_kafle(kafle)
        indeksy = {p: self.lyr.fields().indexOf(p) for p in _POLA_NUMERACJI}

        # w trybie edycji zmiany ida do bufora edycji (z cofaniem),
        # zapisuje je uzytkownik razem ze swoimi poprawkami
        byla_edycja = self.lyr.isEditable()
        if not byla_edycja and not self.lyr.startEditing():
            self.iface.messageBar().pushCritical(
                self.TYTUL, 'Nie można włączyć edycji warstwy')
            return False

        self.lyr.beginEditCommand(self.TYTUL)
        for i, fid in enumerate(fidy):
            wartosci = {indeksy['STRONA']: strony[i]}
            for kierunek in 'LGPD':
                wartosci[indeksy[kierunek]] = sasiedzi[i][kierunek]
            self.lyr.changeAttributeValues(fid, wartosci)
        self.lyr.endEditCommand()

        if not byla_edycja and not self.lyr.commitChanges():
            self.iface.messageBar().pushCritical(
                self.TYTUL, 'Nie udało się zapisać numeracji: '
                + '; '.join(self.lyr.commitErrors()))
            self.lyr.rollBack()
            return False

        self.lyr.triggerRepaint()
        self.byla_edycja = byla_edycja
        return True

    def wyswietl_info(self):
        tekst = 'Przenumerowano ' + str(self.ile) + ' pól atlasu'
        if self.byla_edycja:
            tekst += ' - warstwa jest w trybie edycji, zapisz zmiany'
        self.iface.messageBar().pushSuccess(self.TYTUL, tekst)


class PobierzDane(QDialog):
    def __init__(self):
        super(PobierzDane, self).__init__()

        self.porzuc = True
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # slownik standardowych rozmiarow papieru [szer, wys] w mm
        self.sl = {
            'A4': [210, 297],
            'A3': [297, 420],
        }

        self.rozmiar = []  # rozmiar papieru w mm
        self.wynik = []  # rozmiar kafla w metrach

        self.ui.pushButton_ok.clicked.connect(self.zatwierdz)
        self.ui.pushButton_porzuc.clicked.connect(self.porzucone)

    def porzucone(self):
        self.hide()

    def zatwierdz(self):
        if self.odczytaj_rozmiar():
            if self.obl_rozm():
                self.porzuc = False
                self.hide()

    def odczytaj_rozmiar(self):
        tekst = ''
        if self.ui.radioButton_a4.isChecked():
            self.rozmiar = self.sl['A4']
        if self.ui.radioButton_a3.isChecked():
            self.rozmiar = self.sl['A3']
        if self.ui.radioButton_inny.isChecked():
            rozm = self.ui.lineEdit_inny.text()
            if 'x' in rozm:
                w = rozm.split('x')
                if len(w) != 2:
                    tekst = 'Powinien być tylko JEDEN x!!!'
                elif w[0].isdigit() and w[1].isdigit():
                    self.rozmiar = [int(w[0]), int(w[1])]
                else:
                    tekst = 'Podany rozmiar nie składa się z samych cyfr ' \
                        'oddzielonych x'
            else:
                tekst = 'rozmiar powinien składać się z liczb całkowitych ' \
                    'oddzielonych x'

        if tekst == '':
            return True
        else:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText(tekst)
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

            return False

    def obl_rozm(self):
        # oblicz rozmiar kafla w metrach na podstawie formatu i skali

        skala = self.ui.lineEdit_skala.text()
        if not skala.isdigit():
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Skala ma być liczbą całkowitą!!!')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()

            return False

        papier = list(self.rozmiar)
        if not self.ui.radioButton_inny.isChecked() and \
                self.ui.radioButton_poziom.isChecked():
            papier = papier[::-1]

        self.wynik = kafelkowanie.rozmiar_kafla_z_skali(papier, int(skala))

        if self.wynik[0] < 1 or self.wynik[1] < 1:
            message = QMessageBox()
            message.setIcon(QMessageBox.Information)
            message.setWindowTitle('Błąd')
            message.setText('Wymiary mają być większe od zera!!!')
            message.addButton(u"Zamknij", QMessageBox.ActionRole)
            message.exec_()
            return False

        return True
