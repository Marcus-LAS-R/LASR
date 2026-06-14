import os
from qgis.core import QgsSpatialIndex, QgsProject, Qgis, QgsLayoutSize, \
    QgsUnitTypes, QgsGeometry, QgsLayoutExporter, QgsMessageLog
from .funkcje import isNone, oblicz_odl
from .pw import PasekPostepu
from PyQt5.QtWidgets import QDialog
from .ui.ui_raport_wyles import Ui_Dialog


class RaportWylesien():
    def __init__(self, iface):
        self.iface = iface

        # przypisanie odnosników do layoutu karty w którym będziemy zmieniać
        # dane w odpowiednich polach i ustawiać mapę
        self.mn = QgsProject.instance().layoutManager()
        self.lay = False

        # nazwa gminy do wpisania na karcie, potem do zmodyfikowania w
        # formularzu wyświelanym użytkownikowi
        self.gmina = 'k'

        # type generowania kart 0 - wszystkie, 1- tylko zaznaczone
        self.typ = 0

        # warstwa z intersectem wydz i dzkat, z niej bedą wybierane featurki do
        # generowania kart
        self.wyles = False
        # warstwa z wybranym featurkiem do wylesienia, do naniesienia na mapę
        self.wylesw = False
        # warstwa z pkt granicznymi działek na ktorych leża wylesienia
        self.pktgran = False
        self.si = False  # Spatial index dla pkt

        # warstwa z pkt granicznymi ktore będą rysowane naMapie
        self.pktgranw = False
        # warstwa z obrebami ewid
        self.obrewid = False

        # slownik z kodami i nazwami obrębów ewidencyjnych w postaci:
        # 'GGGOOOO': 'Nazwa obrębu',
        self.obr_sl = {}

        # lista wymaganych warstw w projekcie
        self.war_wym = [
            'pkt_gran_wyb',
            'pkt_gran',
            'fr_do_wyl',
            'inne_wyl',
            'KLU_AFT',
            'granica obrębu ewid.',
            'granica klasoużytku',
            'granica działki ewid.'
        ]

        # lista z uwagami z tworzenia kart, wymagającymi uwagi użytkownika
        self.uwagi = []

    def sprawdz_dane(self):  # noqa
        '''Metoda sprawdza czy do projektu dodany jest odpowiedni layout,
        warstwy z odpowiednimi polami,
        '''

        # jezeli w projekcie nie ma zadnego layoutu o odpowiedniej nazwie
        # to nie ma co sprawdzać dalej...
        if len(self.mn.layouts()) != 1:
            self.iface.messageBar().pushMessage(
                'Błąd',
                'Obsługiwany jest tylko jeden layout w pliku projektu',
                Qgis.Critical,
                0
            )
            return False

        if self.mn.layouts()[0].name() != 'karta':
            self.iface.messageBar().pushMessage(
                'Błąd',
                'W projekcie powinieneś mieć layout "karta", napewno masz '
                'otwarty projekt do generowania kart wylesień?',
                Qgis.Critical,
                0
            )
            return False
        self.lay = self.mn.layouts()[0]

        # sprawdz czy w projekcie sa dodane odpowiednie warstwy
        warstwy = [lyr.name() for lyr in
                   QgsProject.instance().mapLayers().values()
                   if lyr.name() in self.war_wym]

        if len(warstwy) != len(self.war_wym):
            self.iface.messageBar().pushMessage(
                'Uwaga',
                'Nie odnaleziono niezbędnych warstw w projekcie: [' +
                ', '.join([x for x in self.war_wym if x not in warstwy]) + ']',
                Qgis.Critical,
                0
            )
            return False

        # przypisz odwołania do warstw
        for key, val in QgsProject.instance().mapLayers().items():
            if val.name() == 'inne_wyl':
                self.wyles = val
            if val.name() == 'fr_do_wyl':
                self.wylesw = val
            if val.name() == 'pkt_gran':
                self.pktgran = val
            if val.name() == 'pkt_gran_wyb':
                self.pktgranw = val
            if val.name() == 'granica obrębu ewid.':
                self.obrewid = val

        # sprawdz czy w warstwach sa wszystkie niezbedne kolumny, jak tak to
        # zwracamy true i lecimy z generowaniem
        # TODO: dopisac to sprawdzenie, na spokojnie

        # stworz spatial ind dla pkt granicznych innych wylesien
        self.si = QgsSpatialIndex(self.pktgran)

        # stworz slownik dla obrębów
        pole = [x.name() for x in self.obrewid.dataProvider().fields().toList()
                if x.name() in ['G5NAZ', 'jpt_nazwa_']]
        if len(pole) == 0:
            self.iface.messageBar().pushMessage(
                'Uwaga',
                'Warstwa obrębu ewid powinna zawierać kolumnę z nazwą obrębu ',
                '[G5NAZ lub jpt_nazwa_]',
                Qgis.Critical,
                0
            )
            return False
        pole = pole[0]

        for feat in self.obrewid.getFeatures():
            self.obr_sl[feat['MUNICIP']+feat['COMMUNITY']] = isNone(feat[pole])

        # utworz katalog na karty
        sciezka = self.wyles.dataProvider().dataSourceUri().split("|")[0][:-4]
        self.kat = os.path.dirname(sciezka)
        self.kartkat = os.path.join(self.kat, '..', 'karty')
        if not os.path.isdir(self.kartkat):
            os.mkdir(self.kartkat)

        p = PobierzDane()
        p.exec_()

        if p.porzucone:
            return False

        self.gmina = isNone(p.ui.lineEdit.text())
        if p.ui.radioButton_wyb.isChecked():
            self.typ = 1

        return True

    def ustaw_karte(self, feat):  # noqa
        '''Metoda ustawia kartę do odpowiedniego featura, dopisuje niezbędne
        info do layoutu
        '''

        # ustaw zasięg mapy do przekazanego featura i ustaw skale na 2k
        it = self.lay.itemById('GLOWNA')
        it.setExtent(feat.geometry().boundingBox())
        it.attemptResize(
            QgsLayoutSize(193.802, 210.578, QgsUnitTypes.LayoutMillimeters)
        )
        it.setScale(2000)

        # wyczyść warstwy i skopiuj featurki do pokazania na mape
        self.wyczysc_warstwy_karty()

        # poligon
        self.wylesw.startEditing()
        self.wylesw.addFeatures([feat])
        self.wylesw.commitChanges()

        # pkt graniczne
        idik = self.si.intersects(feat.geometry().buffer(2, 1).boundingBox())
        lista = []  # lista z featurami pktowymi
        for id in idik:
            f = self.pktgran.getFeature(id)
            if f.geometry().buffer(1, 1).intersects(feat.geometry()):
                lista.append(f)

        if len(lista) > 0:
            self.pktgranw.startEditing()
            self.pktgranw.addFeatures(lista)
            self.pktgranw.commitChanges()

        # opis gminy
        it = self.lay.itemById('gmina')
        it.setText(self.gmina+' ('+isNone(feat['MUNICIP'])+')')

        # opis obrębu
        it = self.lay.itemById('obr_ewid')
        if feat['MUNICIP']+feat['COMMUNITY'] in self.obr_sl:
            it.setText(self.obr_sl[feat['MUNICIP'] + feat['COMMUNITY']] +
                       ' (' + isNone(feat['COMMUNITY']) + ')')
        else:
            it.setText(' (' + isNone(feat['COMMUNITY']) + ')')

        # nr dzialki
        it = self.lay.itemById('dz_ewid')
        it.setText(isNone(feat['PARCELNR']))

        # adres leśny
        it = self.lay.itemById('oddz')
        it.setText(isNone(feat['ODDZ']))
        it = self.lay.itemById('wydz')
        it.setText(isNone(feat['WYDZ']))

        # pkt graniczne, wsp
        wyps = []  # lista z linijkami do wypisu
        feat.geometry().convertToMultiType()
        for part in feat.geometry().asMultiPolygon():
            for p in part[0][:-1]:
                pgeom = QgsGeometry().fromPointXY(p)
                ids = self.si.intersects(
                    pgeom.buffer(1, 1).boundingBox())
                if len(ids) > 0:
                    odl = 99
                    pkt = False
                    for id in ids:
                        ptemp = self.pktgran.getFeature(id)
                        otemp = oblicz_odl(ptemp.geometry().asPoint(),
                                           pgeom.asPoint())
                        if otemp < odl:
                            odl = otemp
                            pkt = ptemp

                    w = pkt['numer']+'. ' + \
                        str(round(pkt.geometry().asPoint().x(), 2)) + ' ' + \
                        str(round(pkt.geometry().asPoint().y(), 2))
                    # jezeli na działce mamy 2 polozone blisko siebie węzełki
                    # pomijamy zdublowane wartości
                    if len(wyps) == 0:
                        wyps.append(w)
                    if w != wyps[-1]:
                        wyps.append(w)

        # wyczysc wszystkie dane z obu tablic
        it = self.lay.itemById('pkt2')
        it.setText('')
        it = self.lay.itemById('pkt1')
        it.setText('')

        if len(wyps) < 17:
            it.setText('\n'.join(wyps))
        elif 16 < len(wyps):
            it.setText('\n'.join(wyps[:16]))
            it = self.lay.itemById('pkt2')
            it.setText('\n'.join(wyps[16:]))

        if 31 < len(wyps):
            self.uwagi.append(
                feat['MUNICIP']+feat['COMMUNITY']+'.'+feat['PARCELNR'] +
                ' - poligon ma wiecej niż 32 pkt graniczne'
            )

    def wyczysc_warstwy_karty(self):
        '''Metoda czyści obie warstwy (pkt_gran i fr_do_wylesienia) z
        wszystkich featurkow
        '''
        for lyr in [self.pktgranw, self.wylesw]:
            id_kas = [f.id() for f in lyr.getFeatures()]
            if len(id_kas) > 0:
                lyr.startEditing()
                lyr.dataProvider().deleteFeatures(id_kas)
                lyr.commitChanges()

    def wyeksportuj_karte(self, feat):
        '''Metoda eksportuje karte w pdf do katalogu karty w folderze z
        projektem...
        '''
        exporter = QgsLayoutExporter(self.lay)
        nazwa = feat['MUNICIP'] + feat['COMMUNITY'] + '-' + feat['PARCELNR'] +\
            '_' + feat['ODDZ'] + feat['WYDZ']
        res = exporter.exportToImage(
            os.path.join(self.kartkat, nazwa.replace('/', '_') + '.tif'),
            QgsLayoutExporter.ImageExportSettings())

        if not res == QgsLayoutExporter.Success:
            self.uwagi.append('Błąd eksportu karty: '+nazwa)

    def generuj_karty(self):
        '''Metoda generuje karty dla wszystkich poligonów z warstwy wyles,
        o ile ich powierzchnia jest większa od 1 m2
        '''
        if self.typ == 0:
            generator = self.wyles.getFeatures()
            ile_poly = self.wyles.featureCount()
        elif self.typ == 1:
            ile_poly = len([x for x in self.wyles.getSelectedFeatures()])
            generator = self.wyles.getSelectedFeatures()

        postep = PasekPostepu(self.iface).stworz_pasek('Generowanie kart')
        postep.setValue(0)

        proc = 10
        for i, feat in enumerate(generator):
            if feat.geometry().area() > 0.9999:
                try:
                    self.ustaw_karte(feat)
                    self.wyeksportuj_karte(feat)
                except:  # nopep8
                    self.uwagi.append(
                        'Nie udało się wygenerować karty: ' +
                        feat['MUNICIP'] + feat['COMMUNITY'] +
                        '-' + feat['PARCELNR']
                    )

            if 100 * i / ile_poly > proc:
                postep.setValue(proc)
                proc += 10

        # wyczyść pasek postępu i dodaj wiadomość o wynikach
        self.iface.messageBar().clearWidgets()
        if len(self.uwagi) == 0:
            self.iface.messageBar().pushMessage(
                'OK',
                'Wyeksportowano '+str(ile_poly),
                Qgis.Success,
                0
            )
        else:
            self.iface.messageBar().pushMessage(
                'UWAGA',
                'Wyeksportowano '+str(ile_poly)+', zgłoszono: ' +
                str(len(self.uwagi)) + ' (patrz log LAS-R)',
                Qgis.Warning,
                0
            )

            QgsMessageLog.logMessage('Problemy podczas generowania', 'LAS-R')
            QgsMessageLog.logMessage('\n'.join(self.uwagi), 'LAS-R')


class PobierzDane(QDialog):
    def __init__(self):
        super(PobierzDane, self).__init__()

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # wartosc True jezeli uzytkownik zrezygnowal z przetwarzania
        self.porzucone = True

        # sygnały
        self.ui.pushButton_ok.clicked.connect(self.sprawdz_ok)
        self.ui.pushButton_porzuc.clicked.connect(self.porzuc)

    def porzuc(self):
        self.hide()

    def sprawdz_ok(self):
        self.porzucone = False
        self.hide()
