from qgis.core import Qgis, QgsMessageLog, QgsFeatureRequest,  QgsGeometry, \
    QgsSpatialIndex, QgsField, QgsFeature, QgsVectorLayer, QgsProject
from collections import Counter
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QVariant


class SprawdzWydzielenia():
    """Klasa poboczna wymaga aby klasa dziedzicząca miałą już dodany wskaznik
    do wydz i bazy taksatora. Sprawdza poprawność pól w wydzieleniach, czy nie
    ma niepołączonych wydzieleń."""

    def __init__(self):
        pass

    def poprawne_wydz(self):
        """Metoda grupujaca wszystkie sprawdzenia danych i bazy"""
        spr = [
            self.spr_baza_polacz,
            self.spr_popr,
            self.spr_kolumn,
            self.spr_crs,
            self.spr_wydz_baza,
            self.spr_wydz_duble,
            self.spr_wydz_na_nielasach,
        ]

        self.wypis_sprawdzenia_wydz = ''

        komunikaty = [
            'Połączenie z bazą: OK',
            'Sprawdzenie poprawności warstwy wydz: OK',
            'Sprawdzenie obecności niezbędnych kolumn: OK',
            'Sprawdzenie układu wspł. (EPSG:2180) : OK',
            'Porównanie wydzieleń w warstwie z bazą: OK',
            'Sprawdzenie zdublowanych wydzieleń w warstwie: OK',
            'Sprawdzanie wydz innych niż D-STAN, na użytkach nieleśnych: OK',
        ]

        for i, s in enumerate(spr):
            tt = s
            if not tt():
                # jeżeli są rozbieżności między bazą a warstwą zapytaj czy
                # użytkownik chce kontynuować procedurę
                if i == 4:
                    message = QMessageBox()
                    message.setIcon(QMessageBox.Information)
                    message.setWindowTitle('Błąd')
                    message.setText(
                        'W bazie lub w warstwie są niełączące się wydzielenia'
                        ', kontynuować?')
                    message.addButton('Przerwij', QMessageBox.ActionRole)
                    message.addButton('Kontynuuj', QMessageBox.ActionRole)
                    pok_rap = message.exec_()

                    if pok_rap == 1:
                        self.wypis_sprawdzenia_wydz += \
                            '[BŁĄD] w bazie lub warstwie są niepołączone ' + \
                            'wydzielenia!\n'
                        return False

                # jeżeli są inne rozbieżności, kończymy
                else:
                    self.przerwij()
                    return False
            else:
                QgsMessageLog.logMessage(
                    komunikaty[i],
                    'Las-R',
                    Qgis.Info
                )
                self.wypis_sprawdzenia_wydz += komunikaty[i] + '\n'
        return True

    def przerwij(self):
        if self.baza.con:
            self.baza.zamknij()
        QgsMessageLog.logMessage(
            'Warstwa wydzieleń niepoprawna!',
            'Las-R')

    def spr_baza_polacz(self):
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                'BAZA',
                'Nie udało się połączyć ze wskazaną bazą!',
                Qgis.Critical,
                10)
            QgsMessageLog.logMessage(
                        'Brak dostepu do bazy',
                        'Las-R')
            return False
        return True

    def spr_popr(self):
        if not self.wydz.isValid():
            if not self.wydz.isValid():
                self.iface.messageBar().pushMessage(
                    'Wydzielenia',
                    'Nie mogę otworzyć warstwy do odczytu',
                    Qgis.Critical,
                    10)
                return False
        return True

    def spr_crs(self):
        """Metoda sprwdza układ wspł. warstwy, jeżeli nie jest to EPSG:2180,
        zwraca False"""
        if self.wydz.crs().authid() != 'EPSG:2180':
            self.iface.messageBar().pushMessage(
                'Wydzielenia',
                'Warstwa ma inny układ współrzędnych niż PUWG92 (EPSG:2180)',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_kolumn(self):
        pola = [x for x in ['WYDZ', 'ODDZ', 'ADR_LES']
                if x not in self.wydz.dataProvider().fieldNameMap()]
        if len(pola) > 0:
            self.iface.messageBar().pushMessage(
                'Wydzielenia',
                'Brak kolumn '+', '.join(pola)+' w warstwie',
                Qgis.Critical,
                10)
            return False
        return True

    def spr_wydz_baza(self):
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                               ).setSubsetOfAttributes(
                                                   ['ADR_LES'],
                                                   self.wydz.fields()
                                               )
        adr_w = [x['ADR_LES'] for x in self.wydz.getFeatures(request)]
        adr_b = self.baza.pobierz_wydzielenia()
        brakiw = [x for x in adr_w if x not in adr_b]
        brakib = [x for x in adr_b if x not in adr_w]

        QgsMessageLog.logMessage(
            '   Znaleziono poligonów w shp: ' + str(len(adr_w)),
            'Las-R',
            Qgis.Info
        )
        self.wypis_sprawdzenia_wydz +=  \
            '\n   Znaleziono poligonów w shp: ' + str(len(adr_w))
        QgsMessageLog.logMessage(
            '   Znaleziono wydzieleń w shp: ' + str(len(set(adr_w))),
            'Las-R',
            Qgis.Info
        )
        self.wypis_sprawdzenia_wydz +=  \
            '\n   Znaleziono wydzieleń w shp: ' + str(len(set(adr_w)))
        QgsMessageLog.logMessage(
            '   Znaleziono wydzieleń w bazie: ' + str(len(adr_b)),
            'Las-R',
            Qgis.Info
        )
        self.wypis_sprawdzenia_wydz +=  \
            '\n   Znaleziono wydzieleń w bazie: ' + str(len(adr_b)) + '\n\n'

        if len(brakiw) > 0:
            self.iface.messageBar().pushMessage(
                'BAZA',
                'W shp znajdują się wydzielenia, które nie są dopisane do ' +
                'Bazy! Patrz log Las-R',
                Qgis.Critical,
                10)

            self.wypis_sprawdzenia_wydz +=  \
                '\nW shp znajdują się wydzielenia, które nie są dopisane do ' +\
                'Bazy! Patrz log Las-R\n'
            QgsMessageLog.logMessage('Brakujące wydzielenia w bazie:',
                                     'Las-R',
                                     Qgis.Critical)
            self.wypis_sprawdzenia_wydz +=  'Brakujące wydzielenia w bazie:\n'
            for b in brakiw:
                QgsMessageLog.logMessage(b, 'Las-R', Qgis.Critical)
            self.wypis_sprawdzenia_wydz += b + '\n'

        if len(brakib) > 0:
            self.iface.messageBar().pushMessage(
                'BAZA',
                'W bazie znajdują się wydzielenia, które nie są dopisane do ' +
                'warstwy! Patrz log Las-R',
                Qgis.Critical,
                10)

            QgsMessageLog.logMessage('Brakujące wydzielenia w warstwie:',
                                     'Las-R',
                                     Qgis.Critical)
            for b in brakib:
                QgsMessageLog.logMessage(b, 'Las-R', Qgis.Critical)

        if len(brakib) > 0 or len(brakiw) > 0:
            return False

        return True

    def spr_wydz_duble(self):
        request = QgsFeatureRequest().setFlags(QgsFeatureRequest.NoGeometry
                                               ).setSubsetOfAttributes(
                                                   ['ADR_LES'],
                                                   self.wydz.fields()
                                               )
        adr_w = [x['ADR_LES'] for x in self.wydz.getFeatures(request)]
        adr_b = self.baza.pobierz_wydzielenia()

        if len(adr_w) != len(set(adr_b)):
            self.iface.messageBar().pushMessage(
                'wydzielenia [shp]',
                'Połącz wydzielenia w multipoligony! (Spis w logu)',
                Qgis.Critical,
                10)

            QgsMessageLog.logMessage(
                '\nNiepołączone wydzielenia: \n' + '\n'.join(
                    [y[0] + '   (x' + str(y[1]) + ')'
                     for y in Counter(adr_w).most_common() if y[1] > 1]),
                'Las-R'
            )
            return False
        return True

    def spr_wydz_na_nielasach(self):
        rozl = self.baza.pobierz_rozliczenie_wydz()
        if len(rozl) == 0:
            return True

        tab = self.baza.pobierz_wydz_na_innych_uz()

        if len(tab) > 0:
            self.iface.messageBar().pushMessage(
                'WYDZIELENIA NIELEŚNE',
                'Odnaleziono wydzielenia nieleśne na użytkach nieleśnych',
                Qgis.Critical,
                10)

            QgsMessageLog.logMessage(
                '\nWydzielenia nieleśne na nielasach:\n' +
                '\n'.join('  '.join(map(str, y)) for y in tab),
                'Las-R'
            )
            return False

        return True


def sprawdz_odl_wydz(iface, wydz):
    """Funkcja sprawdza czy w multipoligonach wydzieleń nie ma większych
    odległości między najbliższymi częsciami niż 30m. Jeżeli takie
    występują zostają zaraportowane użytkownikowi. Pomijane są sprawdzenia
    w Lz.
    INPUT:
        iface,
        wskaznik do warstwy wydz z wydz wielopolignowymi
        """
    # zmienna z wypisem do raportu
    wyps = '\n\n----[ SPRAWDZENIE ODLEGŁOŚCI W WYDZIELENIACH]----\n'

    sl_wydz = {}  # sl z wydz w postaci {id: feat}
    for f in wydz.getFeatures():
        sl_wydz[f.id()] = f

    odl_wydz = {}
    f_przek_odl = []
    for f in sl_wydz.values():
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

            odl_wydz[f['ADR_LES']] = max(odl)

            if max(odl) > 29.999:
                f_przek_odl.append(f)

    # tabela z odległościami wiekszymi niz 30 m w wydzieleniach
    wydz_odl_przekrocz = sorted([[k, v] for k, v in
                                 odl_wydz.items()
                                 if v > 29.999],
                                reverse=True,
                                key=lambda x: x[0])

    if len(wydz_odl_przekrocz) > 0:
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
        for i, it in enumerate(f_przek_odl):
            feat = QgsFeature()
            feat.setGeometry(it.geometry())
            feat.setFields(wydz_bodl.fields())
            feat['ID'] = i
            feat['ADR_LES'] = it['ADR_LES']
            try:
                feat['ODLEGŁOŚCI'] = odl_wydz[it['ADR_LES']]
            except:  # nopep8
                feat['ODLEGŁOŚCI'] = 999
            fs.append(feat)

        wydz_bodl.dataProvider().addFeatures(fs)
        wydz_bodl.commitChanges()

        QgsMessageLog.logMessage(
            '\nWydzielenia z przekroczonymi odległościami: \n\t' +
            '\n'.join([x[0]+' - '+str(round(x[1], 1))+' m'
                         for x in wydz_odl_przekrocz]),
            'Las-R',
            Qgis.Warning
        )

        QgsProject.instance().addMapLayer(wydz_bodl)

        wyps += '\nWydzielenia z przekroczonymi odległościami: \n' + \
            '\n'.join([x[0]+' - '+str(round(x[1], 1))+' m'
                         for x in wydz_odl_przekrocz])

    else:
        wydruk = sorted([[k, v] for k, v in odl_wydz.items()],
                        reverse=True,
                        key=lambda x: x[1])[:10]

        QgsMessageLog.logMessage(
            'Wydzielenia z największymi odległościami: \n' +
            '\n'.join([x[0]+' - '+str(round(x[1], 1))+' m'
                       for x in wydruk]),
            'Las-R',
            Qgis.Info
        )
        wyps += 'Wydzielenia z największymi odległościami: \n' + \
            '\n'.join([x[0]+' - '+str(round(x[1], 1))+' m'
                       for x in wydruk])

    wyps += '\n----[ KONIEC ]----\n'
    return len(wydz_odl_przekrocz), wyps


def sprawdz_odl_lz(iface, wydz):
    """Funkcja sprawdza odległości poszczególnych Lz od wydzieleń w warstwie
    Jeżeli są mniejsze od 30m raportuje bledy
    INPUT:
    iface,
    wskaznik do warstwy wydz
        """

    sl_wydz = {}  # sl z wydz w postaci {id: feat}
    sl_lz = {}  # slownik z lz dla calego obiektu
    # zmienna z wypisem do raportuj
    wyps = '\n\n----[ SPRAWDZENIE ODLEGŁOŚCI LZ OD WYDZIELEŃ ]----\n'

    si = QgsSpatialIndex()
    for f in wydz.getFeatures():
        si.insertFeature(f)
        sl_wydz[f.id()] = f
        if f['WYDZ'] == 'Lz':
            sl_lz[f.id()] = f

    lz_odl_przekrocz = []  # tablica z bliskimi odległościami do
    # wydzieleń w postaci : [[geometry, odl], [geometry, odl]]

    # sprawdz po kolei wszystkie Lz czy spełniają kryterium odległościowe
    for idik, feat in sl_lz.items():
        for part in feat.geometry().asMultiPolygon():
            geom = QgsGeometry.fromPolygonXY(part)
            ids = si.intersects(geom.boundingBox())
            for id in ids:
                short_line = geom.shortestLine(
                    sl_wydz[id].geometry()).length()
                if short_line < 30 and idik != id:
                    lz_odl_przekrocz.append(
                        [geom, short_line, feat['ADR_LES']]
                    )

    lz_odl_przekrocz = sorted(lz_odl_przekrocz,
                              reverse=True,
                              key=lambda x: x[1]
                              )

    if len(lz_odl_przekrocz) > 0:
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
        for i, it in enumerate(lz_odl_przekrocz):
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
            str(len(lz_odl_przekrocz)),
            'Las-R',
            Qgis.Warning
        )
        wyps += '\nLz z za bliskimi odległościami do wydzieleń: ' + \
            str(len(lz_odl_przekrocz)),
        wyps += '\n'.join([x[2]+'\t'+str(x[1]) for x in lz_odl_przekrocz])

        QgsProject.instance().addMapLayer(lz_bodl)

    else:
        QgsMessageLog.logMessage(
            'Odległości Lz od wydzieleń: OK',
            'Las-R',
            Qgis.Info
        )
        wyps += 'Lz w odległości większej niż 30 m od wydzieleń - OK'

    wyps += '\n----[ KONIEC ]----\n'

    return len(lz_odl_przekrocz), wyps


def sprawdz_pnsw(wydz, pnsw, baza=False):  # noqa
    """ Funkcja sprawdza czy warstwa pnsw zawiera sie w wydz """

    wyps = '----[ SPRAWDZENIE WARSTWY PNSW ]----\n'
    bezbledow = True

    crs_ok = True
    if pnsw.crs().authid() != 'EPSG:2180':
        wyps += 'WARSTWA NIE JEST W UKŁADZIE PUWG-92!!!\n'
        wyps += '(Pomijam sprawdzanie zawierania się PNSW w wydzieleniach, ' +\
            'oraz dopisanie ADR_LES do warstwy PNSW)\n'
        crs_ok = False

    if 3 != len([x.name() for x in pnsw.dataProvider().fields().toList()
                 if x.name() in ['NR_PNSW', 'ADR_BDL', 'KOD_PNSW', ]]):
        wyps += 'BRAK NIEZBĘDNYCH KOLUMN: KOD_PNSW, NR_PNSW, ADR_BDL' +\
            '\n----[ KONIEC ]----\n\n'
        return False, wyps

    if crs_ok:
        # zbuduj indeks przestrzenny dla wydz
        si = QgsSpatialIndex()
        sl_w = {}  # slownik z feat wydz {id: wydz feat, ... }

        # slownik z poprawionymi adr_les i nr pnsw z shp do sprawdzenia z baza
        # {adr_les:nr_pnws: kod_pnsw_b, }
        sl_pnsw = {}

        fmi = pnsw.dataProvider().fieldNameMap()
        for wfeat in wydz.getFeatures():
            si.insertFeature(wfeat)
            sl_w[wfeat.id()] = wfeat

        pnsw.startEditing()
        podm_adr = 0
        for feat in pnsw.getFeatures():
            ids = si.intersects(feat.geometry().boundingBox())
            for id in ids:
                if feat.geometry().intersects(sl_w[id].geometry()):
                    inter = feat.geometry().intersection(sl_w[id].geometry())
                    # jeżeli pnsw lezy w wiekszosci na tym wydz dopisz adr_les
                    if (inter.area()/feat.geometry().area()) > 0.6:
                        pnsw.dataProvider().changeAttributeValues(
                            {feat.id(): {fmi['ADR_BDL']: sl_w[id]['ADR_LES']}}
                             )
                        podm_adr += 1

                    if 0.1 < (inter.area()/feat.geometry().area()) < 0.98999:
                        wyps += sl_w[id]['ADR_LES'] + \
                            ' PNSW nie zawiera sie w wydzieleniu\n'

            # zbuduj slownik ze struktura porownawcza dla bazy
            sl_pnsw[feat['ADR_BDL']+':'+str(feat['NR_PNSW'])] = \
                feat['KOD_PNSW']

        pnsw.commitChanges()

        if podm_adr > 0:
            wyps += '\nPodmieniono ADR_LES: ' + str(podm_adr) + '\n'
            wyps += \
                'Pamiętaj, że zmiany dotyczą tylko i wyłącznie warstwy!!!\n\n'

    if baza is not False:

        bpnsw = baza.pobierz_pnsw()
        bwydz_org = baza.pobierz_wydzielenia()
        bwydz = {v: k for k, v in bwydz_org.items()}

        pnsw_b = {bwydz[x[0]]+':'+str(x[1]): x[2] for x in bpnsw}
        braki_baza = [k+' - '+v for k, v in sl_pnsw.items() if k not in pnsw_b]
        braki_shp = [k+' - '+v for k, v in pnsw_b.items() if k not in sl_pnsw]

        if len(braki_baza) > 0:
            wyps += 'PNSW niedopisane do bazy:\n'
            wyps += '\n'.join(braki_baza) + '\n\n'

        if len(braki_shp) > 0:
            wyps += 'PNSW niedodane do shp:\n'
            wyps += '\n'.join(braki_shp) + '\n\n'

    if crs_ok and bezbledow and len(braki_baza+braki_shp) == 0:
        wyps += 'Wastwa uzupełniona poprawnie - OK\n'

    wyps += '\n----[ KONIEC ]----\n\n'
    return True, wyps


def isNone(a):
    if a in [None, 'NULL', '', ]:
        return ''
    elif isinstance(a, QVariant):
        if a.isNull():
            return ''
    else:
        return a


def sprawdz_linie(linie):
    """ Funkcja sprawdza czy warstwa ma odpowiednie kolumny oraz czy są one
    wypełnione a nie puste"""

    wyps = '----[ SPRAWDZENIE WARSTWY LINI ]----\n'

    if linie.crs().authid() != 'EPSG:2180':
        wyps += 'WARSTWA NIE JEST W UKŁADZIE PUWG-92!!!\n'

    if 2 != len([x.name() for x in linie.dataProvider().fields().toList()
                 if x.name() in ['KOD', 'SZER', ]]):
        wyps += 'BRAK NIEZBĘDNYCH KOLUMN: KOD, SZER\n----[ KONIEC ]----\n\n'
        return False, wyps

    for feat in linie.getFeatures():
        if isNone(feat['KOD']) == '':
            wyps += 'Brak wpisanych kodów lub szerokości\n' + \
                '\n\n WARSTWA NIEPOPRAWNA!!!\n\n' + \
                '----[ KONIEC ]----\n\n'
            return False, wyps

    wyps += 'Wastwa uzupełniona poprawnie - OK\n----[ KONIEC ]----\n\n'
    return True, wyps
