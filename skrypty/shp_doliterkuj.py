import os
import datetime
import processing
from operator import itemgetter

from PyQt5.QtWidgets import QDialog, QFileDialog, QLineEdit, QTableWidgetItem
from qgis.core import Qgis, QgsMessageLog, QgsVectorFileWriter, \
    QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject

from .shp_literkuj import LITERY
from .ui.ui_shp_doliterkuj import Ui_Dialog

_H_BASE = 230
_H_OD = 410
_Y_BTN_BASE = 176
_Y_BTN_OD = 356


def _ma_juz_litere(wartosc):
    """ Czy pole WYDZ jest juz wypelnione (nie jest puste/NULL)? Wzorowane
    1:1 na warunku z shp_literkuj.Literkuj, dla zgodnosci zachowania na
    tych samych danych (shapefile/DBF). """
    return str(wartosc) not in ["", " ", 'NULL', None]


def _jest_puste(wartosc):
    """ Odwrotnosc _ma_juz_litere - przydatna gdy sprawdzamy puste pole
    inne niz WYDZ (np. recznie uzupelniany ODDZ). """
    return not _ma_juz_litere(wartosc)


def _znajdz_oddzialy_bez_litery(sciezka, oddz_reczny=None):
    """ Skanuje warstwe wskazana sciezka (bez wczytywania do projektu) i
    zwraca posortowana liste (MUNICIP, COMMUNITY, ODDZ, ile_do_doliterowania)
    dla grup, w ktorych jest przynajmniej jedno wydzielenie bez przypisanej
    litery (pole WYDZ puste, inne niz 'Lz'). Uzywana do zaprezentowania
    listy oddzialow w dialogu. Jesli podano oddz_reczny, puste pole ODDZ
    jest traktowane tak, jakby juz bylo uzupelnione ta wartoscia (zeby
    tabela pokazywala docelowe grupowanie, a nie puste ODDZ). """
    if not sciezka or not os.path.isfile(sciezka):
        return []
    lyr = QgsVectorLayer(sciezka, 'skan_doliterkuj', 'ogr')
    if not lyr.isValid():
        return []
    pola_wymagane = {'MUNICIP', 'COMMUNITY', 'ODDZ', 'WYDZ'}
    nazwy_pol = {f.name() for f in lyr.fields()}
    if not pola_wymagane.issubset(nazwy_pol):
        return []
    liczniki = {}
    for f in lyr.getFeatures():
        wartosc = f['WYDZ']
        if str(wartosc).upper() == 'LZ':
            continue
        if _ma_juz_litere(wartosc):
            continue
        oddz = f['ODDZ']
        if oddz_reczny and _jest_puste(oddz):
            oddz = oddz_reczny
        klucz = (f['MUNICIP'], f['COMMUNITY'], oddz)
        liczniki[klucz] = liczniki.get(klucz, 0) + 1
    return sorted(
        ((*klucz, ile) for klucz, ile in liczniki.items()),
        key=lambda g: (str(g[0]), str(g[1]), str(g[2])))


def _nastepna_wolna_litera(uzyte, litery=LITERY):
    """ Pierwsza litera z `litery` jeszcze nie uzyta w danej grupie
    (MUNICIP, COMMUNITY, ODDZ) - albo None, jesli wszystkie zajete.
    `litery` moze byc obcietym fragmentem LITERY (np. od litery startowej
    wskazanej w dialogu), zeby wymusic doliterowywanie od danego miejsca. """
    for l in litery:
        if l not in uzyte:
            return l
    return None


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self._grupy = []

        aktywna = self.iface.activeLayer()
        if aktywna is not None:
            try:
                sc = aktywna.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    self.ui.lineEdit_warstwa.setText(sc)
            except Exception:
                pass

        self.ui.pushButton_warstwa.clicked.connect(self._wybierz_warstwe)
        self.ui.checkBox_od.toggled.connect(self._przelacz_od)
        self.ui.lineEdit_warstwa.textChanged.connect(self._na_zmiane_warstwy)
        self.ui.checkBox_oddz_reczny.toggled.connect(
            self.ui.lineEdit_oddz_reczny.setEnabled)
        self.ui.checkBox_oddz_reczny.toggled.connect(self._na_zmiane_oddz_reczny)
        self.ui.lineEdit_oddz_reczny.textChanged.connect(self._na_zmiane_oddz_reczny)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

        self._przelacz_od(False)
        self._aktualizuj()

    def _folder_startowy(self):
        sc = self.ui.lineEdit_warstwa.text().strip()
        if sc and os.path.isfile(sc):
            return os.path.dirname(sc)
        for lyr in QgsProject.instance().mapLayers().values():
            try:
                sc = lyr.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    return os.path.dirname(sc)
            except Exception:
                pass
        return ''

    def _wybierz_warstwe(self):
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż warstwę wydzieleń',
            self._folder_startowy(),
            'Shapefile (*.shp)',
        )[0]
        if sc:
            self.ui.lineEdit_warstwa.setText(sc)

    def _na_zmiane_warstwy(self):
        if self.ui.checkBox_od.isChecked():
            self._wypelnij_tabele()
        self._aktualizuj()

    def _na_zmiane_oddz_reczny(self):
        if self.ui.checkBox_od.isChecked():
            self._wypelnij_tabele()
        self._aktualizuj()

    def _przelacz_od(self, wlaczone):
        self.ui.tableWidget_oddzialy.setVisible(wlaczone)
        wys = _H_OD if wlaczone else _H_BASE
        y_btn = _Y_BTN_OD if wlaczone else _Y_BTN_BASE
        self.setFixedSize(560, wys)
        self.ui.pushButton_ok.move(20, y_btn)
        self.ui.pushButton_cancel.move(290, y_btn)
        if wlaczone:
            self._wypelnij_tabele()
        self._aktualizuj()

    def _wypelnij_tabele(self):
        sc = self.ui.lineEdit_warstwa.text().strip()
        self._grupy = _znajdz_oddzialy_bez_litery(sc, self.oddz_reczny())
        tabela = self.ui.tableWidget_oddzialy
        tabela.setRowCount(len(self._grupy))
        for i, (municip, community, oddz, ile) in enumerate(self._grupy):
            for col, wartosc in enumerate([municip, community, oddz, ile]):
                tabela.setItem(i, col, QTableWidgetItem(str(wartosc)))
            tabela.setCellWidget(i, 4, QLineEdit())

    def _aktualizuj(self):
        ok = bool(self.ui.lineEdit_warstwa.text().strip())
        if self.ui.checkBox_oddz_reczny.isChecked():
            ok = ok and bool(self.ui.lineEdit_oddz_reczny.text().strip())
        if self.ui.checkBox_od.isChecked():
            ok = ok and len(self._grupy) > 0
        self.ui.pushButton_ok.setEnabled(ok)

    def warstwa_sc(self):
        return self.ui.lineEdit_warstwa.text().strip()

    def oddz_reczny(self):
        if not self.ui.checkBox_oddz_reczny.isChecked():
            return None
        wartosc = self.ui.lineEdit_oddz_reczny.text().strip()
        return wartosc or None

    def od_litery_wg_oddz(self):
        """ Zwraca None, jesli checkbox 'Doliterkuj od...' jest wylaczony,
        albo slownik {(ODDZ, MUNICIP, COMMUNITY): litera_startowa} z
        wartosciami wpisanymi w tabeli (pomijajac puste pola - te oddzialy
        beda doliterowane normalnie, od pierwszej wolnej litery). """
        if not self.ui.checkBox_od.isChecked():
            return None
        wynik = {}
        tabela = self.ui.tableWidget_oddzialy
        for i, (municip, community, oddz, _ile) in enumerate(self._grupy):
            edit = tabela.cellWidget(i, 4)
            wartosc = edit.text().strip().lower() if edit else ''
            if wartosc:
                wynik[(oddz, municip, community)] = wartosc
        return wynik


def uruchom(iface):
    """ Pokazuje dialog wyboru warstwy i opcji 'Doliterkuj od...', po czym
    wywoluje Doliterkuj na wybranej warstwie. """
    dlg = _Dialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False

    warstwa_sc = dlg.warstwa_sc()
    od_litery = dlg.od_litery_wg_oddz()
    oddz_reczny = dlg.oddz_reczny()

    lyr = _znajdz_warstwe_w_toc(warstwa_sc)
    if lyr is None:
        lyr = QgsVectorLayer(warstwa_sc, 'wydz_doliterkuj', 'ogr')
    if not lyr.isValid():
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie można wczytać wskazanej warstwy',
            Qgis.Critical,
            10)
        return False

    return Doliterkuj(iface, lyr, od_litery=od_litery, oddz_reczny=oddz_reczny)


def _znajdz_warstwe_w_toc(sciezka):
    """ Jesli wskazany plik jest juz wczytany do projektu (TOC), zwroc ten
    sam obiekt warstwy - zeby edycje od razu byly widoczne na mapie, zamiast
    dzialac "pod spodem" na osobnej, niewyswietlanej kopii warstwy. """
    sciezka = os.path.normcase(os.path.abspath(sciezka))
    for kandydat in QgsProject.instance().mapLayers().values():
        try:
            sc = kandydat.dataProvider().dataSourceUri().split('|')[0]
            if sc and os.path.normcase(os.path.abspath(sc)) == sciezka:
                return kandydat
        except Exception:
            pass
    return None


def Doliterkuj(iface, lyr=False, od_litery=None, oddz_reczny=None):  # noqa
    """ Kontynuacja literacji wydzielen - w odroznieniu od
    shp_literkuj.Literkuj NIE dotyka wydzielen, ktore juz maja litere
    (lub 'Lz') - przypisuje litery tylko nowo dodanym poligonom z pustym
    polem WYDZ, pomijajac przy wyborze litery te, ktore w danej grupie
    (MUNICIP, COMMUNITY, ODDZ) sa juz w uzyciu. Dziala na warstwie
    przygotowanej tak samo jak do Literkuj (te same kolumny), na koniec
    rowniez robi backup do temp/ i dissolve (scala fragmenty 'Lz'). """
    if lyr is False:
        lyr = iface.activeLayer()

    QgsMessageLog.logMessage(
        '------ DOLITERUJ WYDZIELENIA --------- ',
        'Las-R',
        Qgis.Info
    )

    if not lyr.isValid():
        QgsMessageLog.logMessage(
            'Brak zaznaczonej poprawnej warstwy',
            'Las-R',
            Qgis.Critical
        )
        QgsMessageLog.logMessage(
            '------ KONIEC -------- \n',
            'Las-R',
            Qgis.Info
        )
        return False

    pola = [
        'COMMUNITY',
        'MUNICIP',
        'WYDZ',
        'ODDZ',
    ]

    braki = [x for x in pola if x not in [y.name() for y in lyr.fields()]]
    if len(braki) > 0:
        iface.messageBar().pushMessage(
            'BRAK KOLUMN',
            'Brakuje kolumn w zaznaczonej warstwie: '+', '.join(braki),
            Qgis.Critical,
            10)
        return False

    if od_litery:
        nieprawidlowe = sorted({w for w in od_litery.values() if w not in LITERY})
        if nieprawidlowe:
            iface.messageBar().pushMessage(
                'BŁĄD',
                'Nieprawidłowe litery startowe: ' + ', '.join(nieprawidlowe),
                Qgis.Critical,
                10)
            return False

    fnm = lyr.dataProvider().fieldNameMap()

    if oddz_reczny:
        do_uzupelnienia = {
            f.id(): {fnm['ODDZ']: oddz_reczny}
            for f in lyr.getFeatures() if _jest_puste(f['ODDZ'])
        }
        if do_uzupelnienia:
            lyr.startEditing()
            lyr.dataProvider().changeAttributeValues(do_uzupelnienia)
            lyr.commitChanges()
            QgsMessageLog.logMessage(
                'Uzupełniono ODDZ="' + oddz_reczny + '" dla ' +
                str(len(do_uzupelnienia)) + ' wydzieleń',
                'Las-R',
                Qgis.Info
            )

    tab = []
    for f in lyr.getFeatures():
        tab.append([
            f.id(),
            f.geometry().boundingBox().yMaximum(),
            f.geometry().boundingBox().xMaximum(),
            f['ODDZ'],
            f['WYDZ'],
            f['MUNICIP'],
            f['COMMUNITY'],
        ])

    # przebieg wstepny - litery juz uzyte w kazdej grupie (ODDZ, MUNICIP,
    # COMMUNITY), zeby doliterowywanie nie nadpisalo/zduplikowalo
    # istniejacej literacji
    uzyte_w_grupie = {}
    for it in tab:
        if _ma_juz_litere(it[4]):
            klucz = (it[3], it[5], it[6])
            uzyte_w_grupie.setdefault(klucz, set()).add(str(it[4]))

    tab = sorted(tab, key=itemgetter(1), reverse=True)
    tab = sorted(tab, key=itemgetter(5))
    tab = sorted(tab, key=itemgetter(6))
    tab = sorted(tab, key=itemgetter(3))

    sl = {}  # slownik z nowo doliterowanymi wydz {feat.id: {pole: wartosc}}
    message_trig = 0

    for it in tab:
        wartosc = it[4]

        if str(wartosc).upper() == 'LZ':
            sl[it[0]] = {fnm['WYDZ']: 'Lz'}
            continue

        if _ma_juz_litere(wartosc):
            # wydzielenie ma juz litere - nie ruszamy oryginalnej literacji
            continue

        klucz = (it[3], it[5], it[6])
        uzyte = uzyte_w_grupie.setdefault(klucz, set())
        litery_zestaw = LITERY
        if od_litery and klucz in od_litery:
            litery_zestaw = LITERY[LITERY.index(od_litery[klucz]):]
        wolna = _nastepna_wolna_litera(uzyte, litery_zestaw)
        if wolna is None:
            wpis = "xxx"
            if message_trig == 0:
                QgsMessageLog.logMessage(
                    'Lista wydzielen z błędnymi kodami:',
                    'Las-R',
                    Qgis.Warning
                )
            message_trig += 1
            QgsMessageLog.logMessage(
                ' '.join([str(it[5]), str(it[6]), str(it[3]), 'xxx']),
                'Las-R',
                Qgis.Warning
            )
        else:
            wpis = wolna
            uzyte.add(wolna)

        sl[it[0]] = {fnm['WYDZ']: wpis}

    if len(sl) == 0:
        iface.messageBar().pushMessage(
            'OK',
            'Nie znaleziono nowych (pustych) wydzieleń do doliterowania',
            Qgis.Info,
            10)
        QgsMessageLog.logMessage(
            '------ KONIEC -------- \n',
            'Las-R',
            Qgis.Info
        )
        return True

    lyr.startEditing()
    for key, val in sl.items():
        lyr.dataProvider().changeAttributeValues({key: val})
    lyr.commitChanges()

    if message_trig == 0:
        sciezka = lyr.dataProvider().dataSourceUri().split("|")[0][:-4]
        kat = os.path.dirname(sciezka)
        tempkat = os.path.join(kat, 'temp')

        czas = datetime.datetime.now().isoformat(
                        ).replace(":", "")[:-7].replace('-', '')

        if not os.path.isdir(tempkat):
            os.mkdir(tempkat)

        crs = QgsCoordinateReferenceSystem("epsg:2180")

        # stworz kopie warstwy wydz w tempie (przed dissolve)
        QgsVectorFileWriter.writeAsVectorFormat(
            lyr,
            os.path.join(tempkat, 'wydz_backup_'+czas+'.shp'),
            "UTF-8", crs, "ESRI Shapefile")

        # zrob dissolva na warstwie wydz (scala fragmenty Lz)
        processing.run("native:dissolve", {
            'INPUT': sciezka+'.shp',
            'FIELD': ['MUNICIP', 'COMMUNITY', 'ODDZ', 'WYDZ', 'GRP'],
            'OUTPUT': os.path.join(tempkat,
                                   'wydz_dissolve_lz_' +
                                   czas + '.shp')
        })

        wydz_diss = QgsVectorLayer(
            os.path.join(tempkat, 'wydz_dissolve_lz_' + czas + '.shp'),
            'Ls_singleparts', 'ogr')

        lyr.startEditing()
        lyr.dataProvider().truncate()
        lyr.dataProvider().addFeatures(
            [x for x in wydz_diss.dataProvider().getFeatures()]
        )
        lyr.commitChanges()

        iface.messageBar().pushMessage(
            'OK',
            'Doliterowano ' + str(len(sl)) + ' wydzieleń bez problemów '
            '(połączono Lz)',
            Qgis.Success,
            10)

    else:
        iface.messageBar().pushMessage(
            'LICZBA WYDZIELEŃ',
            'Przekroczono liczbę wydzieleń obsługiwaną w '
            'jednym oddziale, (Patrz log Las-R)',
            Qgis.Warning,
            10)
        plugin_dir = os.path.dirname(__file__)
        lyr.loadNamedStyle(
            os.path.join(plugin_dir, '..', 'qml', 'WYDZ_xxx.qml'
                         )
        )
        iface.mapCanvas().refreshAllLayers()

    QgsMessageLog.logMessage(
        '------ KONIEC -------- \n',
        'Las-R',
        Qgis.Info
    )
    return True
