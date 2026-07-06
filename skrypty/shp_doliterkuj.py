import os
import glob
import datetime
import processing
from operator import itemgetter

from PyQt5.QtWidgets import QDialog, QFileDialog, QLineEdit, QTableWidgetItem
from qgis.core import Qgis, QgsMessageLog, QgsVectorFileWriter, \
    QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject

from .shp_literkuj import LITERY
from .baza_wrapper import Baza
from .ui.ui_shp_doliterkuj import Ui_Dialog

_Y_BAZA_ROW = 100
_ROW_H = 32
_ROW_ITEM_H = 22
_TABLE_GAP_TOP = 28
_TABLE_H = 220
_GAP_BASE = 54
_GAP_OD = 8
_BTN_H = 34
_MARGIN_BOTTOM = 20
_DIALOG_W = 560


def _ma_juz_litere(wartosc):
    """ Czy pole WYDZ jest juz wypelnione (nie jest puste/NULL)? Wzorowane
    1:1 na warunku z shp_literkuj.Literkuj, dla zgodnosci zachowania na
    tych samych danych (shapefile/DBF). """
    return str(wartosc) not in ["", " ", 'NULL', None]


def _tekst(wartosc):
    """ Normalizuje wartosc pola do porownan w kluczu grupy (ODDZ,
    MUNICIP, COMMUNITY) - usuwa biale znaki na koncach i rzutuje na str.
    Bez tego pola o stalej szerokosci (DBF) ze spacjami koncowymi w
    starych rekordach tworza "widmowa" osobna grupe dla nowo dodanych
    wydzielen (te same dane logicznie, inny klucz), przez co doliterowanie
    nie widzi juz uzytych liter i zaczyna literowac od "a" od nowa. """
    if wartosc is None:
        return ''
    return str(wartosc).strip()


def _klucz_grupy(oddz, municip, community):
    return (_tekst(oddz), _tekst(municip), _tekst(community))


def _znajdz_oddzialy_bez_litery(sciezka, oddz_reczny=None):
    """ Skanuje warstwe wskazana sciezka (bez wczytywania do projektu) i
    zwraca posortowana liste (MUNICIP, COMMUNITY, ODDZ, ile_do_doliterowania)
    dla grup, w ktorych jest przynajmniej jedno wydzielenie bez przypisanej
    litery (pole WYDZ puste, inne niz 'Lz'). Uzywana do zaprezentowania
    listy oddzialow w dialogu. Jesli podano oddz_reczny, ODDZ jest
    traktowany tak, jakby juz zostal nadpisany ta wartoscia (zeby tabela
    pokazywala docelowe grupowanie po nadpisaniu, a nie oryginalne ODDZ). """
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
        oddz = oddz_reczny if oddz_reczny else f['ODDZ']
        klucz = (_tekst(f['MUNICIP']), _tekst(f['COMMUNITY']), _tekst(oddz))
        liczniki[klucz] = liczniki.get(klucz, 0) + 1
    return sorted(
        ((*klucz, ile) for klucz, ile in liczniki.items()),
        key=lambda g: (str(g[0]), str(g[1]), str(g[2])))


def _rozbierz_adr_les(adr):
    """ Rozbija adres lesny (format budowany przez shp_adr_les.Zaadresuj:
    COUNTY_L(1)+DISTRICT(2)+MUNICIP(3)+COMMUNITY(4)+'-'+GRP(2)+ODDZ(4,
    wyrownane spacjami)+'-'+WYDZ(4, wyrownane spacjami)+'-00', razem 25
    znakow) na skladowe potrzebne do grupowania: (MUNICIP, COMMUNITY, ODDZ,
    WYDZ). Zwraca None, jesli adres ma nieoczekiwana dlugosc (uszkodzony
    lub inny format niz ten generowany przez wtyczke). """
    if not adr or len(adr) != 25:
        return None
    return (
        adr[3:6],
        adr[6:10],
        adr[13:17].strip(),
        adr[18:22].strip(),
    )


def _zgadnij_baze(warstwa_sc):
    """ Probuje odgadnac plik bazy (.mdb) polozony katalog wyzej od
    wskazanej warstwy SHP (typowy uklad katalogow w tym projekcie) - zwraca
    sciezke tylko gdy znaleziono dokladnie jeden plik .mdb, w przeciwnym
    razie pusty string (uzytkownik wskazuje baze recznie). """
    if not warstwa_sc or not os.path.isfile(warstwa_sc):
        return ''
    kat = os.path.dirname(warstwa_sc)
    kandydaci = glob.glob(os.path.join(kat, '..', '*.mdb'))
    if len(kandydaci) == 1:
        return os.path.abspath(kandydaci[0])
    return ''


def _uzyte_z_bazy(baza_sc):
    """ Buduje slownik {klucz_grupy: set(juz_uzyte_litery)} na podstawie
    adresow lesnych (F_ARODES.ADRESS_FOREST, ARODES_TYP_CD='WYDZIEL') z bazy
    Taksatora, zamiast skanowac warstwe SHP - przydatne, gdy robocza
    warstwa SHP moze nie zawierac wszystkich juz oficjalnie ustalonych
    wydzielen (np. jest czesciowa kopia). Zwraca None, jesli nie udalo sie
    polaczyc z baza. """
    baza = Baza(baza_sc)
    if not baza.polacz():
        return None

    wydzielenia = baza.pobierz_wydzielenia()
    baza.zamknij()
    if wydzielenia is False:
        wydzielenia = {}

    uzyte = {}
    for adr in wydzielenia.keys():
        rozbite = _rozbierz_adr_les(adr)
        if rozbite is None:
            continue
        municip, community, oddz, wydz = rozbite
        if not _ma_juz_litere(wydz):
            continue
        klucz = _klucz_grupy(oddz, municip, community)
        uzyte.setdefault(klucz, set()).add(wydz)
    return uzyte


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
        self.ui.pushButton_baza.clicked.connect(self._wybierz_baze)
        self.ui.radioButton_zrodloBaza.toggled.connect(self._na_zmiane_zrodlo)
        self.ui.checkBox_od.toggled.connect(self._przelacz_od)
        self.ui.lineEdit_warstwa.textChanged.connect(self._na_zmiane_warstwy)
        self.ui.lineEdit_baza.textChanged.connect(self._aktualizuj)
        self.ui.checkBox_oddz_reczny.toggled.connect(
            self.ui.lineEdit_oddz_reczny.setEnabled)
        self.ui.checkBox_oddz_reczny.toggled.connect(self._na_zmiane_oddz_reczny)
        self.ui.lineEdit_oddz_reczny.textChanged.connect(self._na_zmiane_oddz_reczny)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

        self._przelicz_layout()
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

    def _wybierz_baze(self):
        kat_start = os.path.dirname(self.ui.lineEdit_baza.text().strip()) \
            or self._folder_startowy()
        sc = QFileDialog.getOpenFileName(
            self,
            'Wskaż bazę Taksatora',
            kat_start,
            'Access MDB (*.mdb);;SQLite (*.sqlite)',
        )[0]
        if sc:
            self.ui.lineEdit_baza.setText(sc)

    def _na_zmiane_warstwy(self):
        if self.ui.radioButton_zrodloBaza.isChecked() and \
                not self.ui.lineEdit_baza.text().strip():
            zgadnieta = _zgadnij_baze(self.warstwa_sc())
            if zgadnieta:
                self.ui.lineEdit_baza.setText(zgadnieta)
        if self.ui.checkBox_od.isChecked():
            self._wypelnij_tabele()
        self._aktualizuj()

    def _na_zmiane_zrodlo(self, _checked=None):
        if self.ui.radioButton_zrodloBaza.isChecked() and \
                not self.ui.lineEdit_baza.text().strip():
            zgadnieta = _zgadnij_baze(self.warstwa_sc())
            if zgadnieta:
                self.ui.lineEdit_baza.setText(zgadnieta)
        self._przelicz_layout()
        self._aktualizuj()

    def _na_zmiane_oddz_reczny(self):
        if self.ui.checkBox_od.isChecked():
            self._wypelnij_tabele()
        self._aktualizuj()

    def _przelacz_od(self, wlaczone):
        self.ui.tableWidget_oddzialy.setVisible(wlaczone)
        if wlaczone:
            self._wypelnij_tabele()
        self._przelicz_layout()
        self._aktualizuj()

    def _przelicz_layout(self):
        """ Przelicza pionowe polozenie wierszy dialogu - dwa niezalezne
        przelaczniki (zrodlo=baza pokazuje dodatkowy wiersz z plikiem bazy;
        checkBox_od pokazuje tabele oddzialow) wplywaja na wysokosc, wiec
        pozycje licza sie dynamicznie zamiast na sztywno w pliku .ui. """
        baza_widoczna = self.ui.radioButton_zrodloBaza.isChecked()
        od_widoczne = self.ui.checkBox_od.isChecked()

        self.ui.lineEdit_baza.setVisible(baza_widoczna)
        self.ui.pushButton_baza.setVisible(baza_widoczna)

        y = _Y_BAZA_ROW + (_ROW_H if baza_widoczna else 0)
        self.ui.checkBox_oddz_reczny.move(20, y)
        self.ui.lineEdit_oddz_reczny.move(250, y)

        y += _ROW_H
        self.ui.checkBox_od.move(20, y)

        y_table = y + _TABLE_GAP_TOP
        self.ui.tableWidget_oddzialy.move(20, y_table)

        if od_widoczne:
            y_btn = y_table + _TABLE_H + _GAP_OD
        else:
            y_btn = y + _ROW_ITEM_H + _GAP_BASE

        self.ui.pushButton_ok.move(20, y_btn)
        self.ui.pushButton_cancel.move(290, y_btn)

        self.setFixedSize(_DIALOG_W, y_btn + _BTN_H + _MARGIN_BOTTOM)

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
        if self.ui.radioButton_zrodloBaza.isChecked():
            ok = ok and bool(self.ui.lineEdit_baza.text().strip())
        self.ui.pushButton_ok.setEnabled(ok)

    def warstwa_sc(self):
        return self.ui.lineEdit_warstwa.text().strip()

    def zrodlo_liter(self):
        return 'baza' if self.ui.radioButton_zrodloBaza.isChecked() else 'shp'

    def baza_sc(self):
        if not self.ui.radioButton_zrodloBaza.isChecked():
            return None
        return self.ui.lineEdit_baza.text().strip() or None

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
                wynik[_klucz_grupy(oddz, municip, community)] = wartosc
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
    zrodlo_liter = dlg.zrodlo_liter()
    baza_sc = dlg.baza_sc()

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

    return Doliterkuj(
        iface, lyr, od_litery=od_litery, oddz_reczny=oddz_reczny,
        zrodlo_liter=zrodlo_liter, baza_sc=baza_sc)


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


def Doliterkuj(iface, lyr=False, od_litery=None, oddz_reczny=None,
               zrodlo_liter='shp', baza_sc=None):  # noqa
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
            for f in lyr.getFeatures()
        }
        if do_uzupelnienia:
            lyr.startEditing()
            lyr.dataProvider().changeAttributeValues(do_uzupelnienia)
            lyr.commitChanges()
            QgsMessageLog.logMessage(
                'Nadpisano ODDZ="' + oddz_reczny + '" dla ' +
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
    # istniejacej literacji - albo z samej warstwy SHP, albo (na zyczenie
    # uzytkownika) z oficjalnych adresow lesnych w bazie Taksatora, gdyby
    # warstwa robocza nie zawierala wszystkich juz ustalonych wydzielen
    if zrodlo_liter == 'baza':
        if not baza_sc:
            iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie wskazano bazy z już zajętymi literami',
                Qgis.Critical,
                10)
            return False
        uzyte_w_grupie = _uzyte_z_bazy(baza_sc)
        if uzyte_w_grupie is None:
            iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się połączyć z bazą - sprawdź wskazany plik',
                Qgis.Critical,
                10)
            return False
    else:
        uzyte_w_grupie = {}
        for it in tab:
            if _ma_juz_litere(it[4]):
                klucz = _klucz_grupy(it[3], it[5], it[6])
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

        klucz = _klucz_grupy(it[3], it[5], it[6])
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
