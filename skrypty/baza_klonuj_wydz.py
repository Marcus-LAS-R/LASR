import os
from PyQt5.QtWidgets import QFileDialog, QDialog, QMessageBox, QDockWidget, \
    QAction, QAbstractItemView, QDialogButtonBox, QLabel, QTableWidget, \
    QTableWidgetItem, QVBoxLayout
from qgis.core import Qgis, QgsMessageLog, QgsRectangle, QgsFeatureRequest
from qgis.gui import QgsMapToolEmitPoint

from .ui.ui_baza_klonuj import Ui_Ui_Dialog as Ui_Dialog
from .baza_wrapper import Baza
from .funkcje import isNone

from qgis.PyQt.uic import loadUiType

FORM_CLASS, _ = loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui',  'ui_klonuj_dock.ui'))

# tabele opisu wydzielenia czyszczone w celu przed wpisaniem kopii
# (kolejność: najpierw tabele zależne)
_TABELE_OPISU = (
    'F_STOREY_SPECIES', 'F_AROD_STOREY', 'F_AROD_GOAL', 'F_AROD_STAND_PEC',
)


class Klonuj():
    def __init__(self, iface):
        """ Konstruktor """
        self.iface = iface  # potrzebne do wyświetlania paska

        self.wydz = {}  # {adr_les: arodes_int_num}
        self.instr = []  # [[adr_les_org, adr_les_klon], ...] oba adr w bazie!!
        self.bledy = 0  # liczba bledów podczas klonowania
        self.sklonowano = 0  # liczba poprawnych operacji
        self.pominieto = 0  # cele z istniejącym opisem pominięte
        self._tabela = ''  # tabela w trakcie zapisu (do komunikatu błędu)

    def dane_dock(self, baza, z, do):
        self.baza = Baza(baza)
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Nie mogłem połączyć się z bazą',
                Qgis.Critical,
                0
            )
            return False

        # wczytaj dane z docka
        self.instr = [[z, dd] for dd in do]

        # jezeli odnaleziono niepoprawna strukturę...
        if set([len(x) for x in self.instr]) != set([2]):
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'w pliku z instrukcjami odnaleziono niepoprawną strukturę '
                'danych. Sprawdź czy wszystkie adresy oddzielone są tab-ami i'
                ' na końcu nie ma pustej linii!',
                Qgis.Critical,
                0
            )
            return False

        return True

    def dane_konf(self, baza, plik):
        self.baza = Baza(baza)
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Nie mogłem połączyć się z bazą',
                Qgis.Critical,
                0
            )
            return False

        # wczytaj dane z pliku
        instr = open(plik, 'r').readlines()

        if len(instr) > 0:
            self.instr = [x.rstrip('\r\n ').split('\t') for x in instr]

        # jeżeli nie odnaleziono żadnych instrukcji
        if len(self.instr) == 0:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'w pliku z instrukcjami nie odnaleziono żadnych adresów.',
                Qgis.Critical,
                0
            )
            return False

        # jezeli odnaleziono niepoprawna strukturę...
        if set([len(x) for x in self.instr]) != set([2]):
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'w pliku z instrukcjami odnaleziono niepoprawną strukturę '
                'danych. Sprawdź czy wszystkie adresy oddzielone są tab-ami i'
                ' na końcu nie ma pustej linii!',
                Qgis.Critical,
                0
            )
            return False
        return True

    def pobierz_dane(self):
        """ Metoda pobiera od użyszkodnia ścieżkę do bazy oraz ścieżkę do pliku
        tekstowego z instrukcjami do klonownia """
        self.pobierz_dane = PobierzDane()
        self.pobierz_dane.exec_()

        if self.pobierz_dane.porzucone:
            return False

        self.baza = Baza(self.pobierz_dane.ui.lineEdit_baza.text())
        if not self.baza.polacz():
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Nie mogłem połączyć się z bazą',
                Qgis.Critical,
                0
            )
            return False

        # wczytaj dane z pliku
        instr = open(
            self.pobierz_dane.ui.lineEdit_wydz.text(), 'r').readlines()

        if len(instr) > 0:
            self.instr = [x.rstrip('\r\n ').split('\t') for x in instr]

        # jeżeli nie odnaleziono żadnych instrukcji
        if len(self.instr) == 0:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'w pliku z instrukcjami nie odnaleziono żadnych adresów.',
                Qgis.Critical,
                0
            )
            return False

        # jezeli odnaleziono niepoprawna strukturę...
        if set([len(x) for x in self.instr]) != set([2]):
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'w pliku z instrukcjami odnaleziono niepoprawną strukturę '
                'danych. Sprawdź czy wszystkie adresy oddzielone są tab-ami i'
                ' na końcu nie ma pustej linii!',
                Qgis.Critical,
                0
            )
            return False

        return True

    def sprawdz_dane(self):
        """ Metoda sprawdza czy wskazana baza i plik tekstowy jest
        kompatybilny, jeżeli tak zwraca True. Kopia bazy - osobno
        (zrob_kopie), dopiero po decyzji użytkownika o nadpisaniu.
        """
        self.wydz = self.baza.pobierz_wydzielenia() or {}

        # sprawdz czy wszystkie adresy lesne sa w bazie
        nieobecne = []  # tab z adresami lesnymi nieobecnymi w bazie
        for x in self.instr:
            if x[0] not in self.wydz:
                nieobecne.append(x[0])
            if x[1] not in self.wydz:
                nieobecne.append(x[1])

        if len(nieobecne) > 0:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Brak w bazie adr les: ' +
                ', '.join(nieobecne),
                Qgis.Critical,
                0
            )
            return False
        return True

    def zrob_kopie(self):
        self.baza.utworz_kopie('klonowanie_wydz')

    def _rodzaj_pow(self, aid):
        w = self.baza.pobierz(
            'select AREA_TYPE_CD from F_SUBAREA where ARODES_INT_NUM = ' +
            str(aid) + ';')
        return isNone(w[0][0]) if w else ''

    def _ma_opis(self, aid):
        """Wydzielenie ma opis, jeśli ma rodzaj powierzchni albo choć jeden
        wpis w tabelach opisu (piętra, gatunki, cele, osobliwości)."""
        if self._rodzaj_pow(aid).strip():
            return True
        for tabela in _TABELE_OPISU:
            w = self.baza.pobierz(
                f'select count(*) from {tabela} where ARODES_INT_NUM = '
                f'{aid};')
            if w and w[0][0]:
                return True
        return False

    def wydzielenia_z_opisem(self):
        """Zwraca [(adr_les celu, stary rodzaj pow., nowy rodzaj pow.)]
        dla celów, które mają już opis w bazie (do ewentualnego
        nadpisania)."""
        wynik = []
        widziane = set()
        for z, do in self.instr:
            if z == do or do in widziane:
                continue
            widziane.add(do)
            if self._ma_opis(self.wydz[do]):
                wynik.append((do, self._rodzaj_pow(self.wydz[do]),
                               self._rodzaj_pow(self.wydz[z])))
        return wynik

    def klonuj(self, pomin=()):
        """ Metoda zbiorcza dla klonowania danych z bazy. Każda para
        (źródło -> cel) w jednej transakcji: najpierw usuwany jest
        dotychczasowy opis celu (piętra, gatunki, cele, osobliwości), potem
        wpisywana kopia źródła - błąd wycofuje całą parę. Cele z `pomin`
        (adr_les) nie są ruszane. """
        pomin = set(pomin)
        for kl in self.instr:
            z, do = kl
            if z == do:
                continue
            if do in pomin:
                self.pominieto += 1
                continue
            self._tabela = ''
            try:
                self._usun_opis_celu(do)
                self.k_subarea(z, do)
                self.k_arod_goal(z, do)
                self.k_arod_stand_pec(z, do)
                self.k_arod_storey(z, do)
                self.k_storey_spec(z, do)
                self.baza.con.commit()
                self.sklonowano += 1
            except Exception as e:
                self.baza.con.rollback()
                self.blad(kl, self._tabela, e)

    def wyswietl_info(self):
        pomin = (f', pominięto (istniejący opis): {self.pominieto}'
                 if self.pominieto else '')
        if self.bledy > 0:
            self.iface.messageBar().pushMessage(
                'Sklonowano '+str(self.sklonowano)+' wydzieleń' + pomin +
                '. Błędów podczas '
                'klonowania: '+str(self.bledy)+' (Szczegóły w logu Las-R)',
                Qgis.Warning,
                0
            )
            return

        self.iface.messageBar().pushMessage(
            'Sklonowano wydzieleń: '+str(self.sklonowano) + pomin,
            Qgis.Success,
            10
        )

    def blad(self, kl, kwer, wyjatek=None):
        self.bledy += 1

        if self.bledy == 1:
            QgsMessageLog.logMessage(
                '--------------\n'
                'Kolejność modyfikowania tabel przy klonowaniu wydzielenia:\n'
                'usunięcie opisu celu\nf_subarea\nf_arod_goal\n'
                'f_arod_stand_spec\nf_arod_storey\nf_storey_spec\n'
                '-------------\n'
                '(w nawiasach podano ARODES_INT_NUM; błąd wycofuje całą parę '
                '- opis celu zostaje bez zmian)\n',
                'Las-R'
            )

        QgsMessageLog.logMessage(
            'Błąd klonowania: ' + kl[0] + ' (' + str(self.wydz[kl[0]]) + ')' +
            ' --> ' + kl[1] + ' (' + str(self.wydz[kl[1]]) + ')' +
            ' | tabela: ' + kwer +
            (f' | {wyjatek}' if wyjatek is not None else ''),
            'Las-R'
        )

    def _wykonaj(self, sql, parametry=()):
        self.baza.cur.execute(sql, parametry)

    def _usun_opis_celu(self, do):
        self._tabela = 'usunięcie opisu celu'
        for tabela in _TABELE_OPISU:
            self._wykonaj(
                f'delete from {tabela} where ARODES_INT_NUM = ?',
                (self.wydz[do],))

    def k_subarea(self, z, do):
        # z - z jakiego adresy kopiujemy
        # do - do jakiego adresu kopiujemy ...
        self._tabela = 'f_subarea'
        kolumny = [
            'DAMAGE_DEGREE_CD', 'CAUSE_CD', 'AREA_TYPE_CD', 'POSITION_CD',
            'RELIEF_CD', 'SITE_TYPE_CD', 'DEGRADATION_CD', 'VEG_COVER_CD',
            'STAND_STRUCT_CD', 'SLOPE_CD', 'EXPOSURE_CD', 'MOISTURE_CD',
            'SOIL_PEC_CD', 'SOIL_SUBTYPE_CD', 'PLANT_COMM_CD',
            'FOREST_FUNC_CD', 'ROTATION_AGE', 'DEAD_WOOD',
        ]
        item = self.baza.cur.execute(
            'select ' + ', '.join(kolumny + ['SUBAREA_INFO']) +
            ' from F_SUBAREA where ARODES_INT_NUM = ?',
            (self.wydz[z],)).fetchall()
        if not item:
            raise ValueError('brak wiersza F_SUBAREA w wydzieleniu źródłowym')
        item = item[0]
        wartosci = list(item[:len(kolumny)])

        # SUBAREA_INFO - nie nadpisuj opisu wydzielenia docelowego
        # pustą/NULL wartością, jeśli źródło go nie ma (inaczej klonowanie
        # kasuje istniejący, ręcznie wpisany opis).
        subarea_info = item[len(kolumny)]
        if subarea_info is not None and str(subarea_info).strip() != '':
            kolumny.append('SUBAREA_INFO')
            wartosci.append(subarea_info)

        ustawienia = ', '.join(f'{kolumna} = ?' for kolumna in kolumny)
        wartosci.append(self.wydz[do])
        self._wykonaj(
            f'update f_subarea set {ustawienia} where ARODES_INT_NUM = ?',
            tuple(wartosci))

    def k_arod_goal(self, z, do):
        self._tabela = 'f_arod_goal'
        item = self.baza.cur.execute(
            'select GOAL_TYPE_FL, SPECIES_CD, GOAL_RANK_ORDER from F_AROD_GOAL '
            'where ARODES_INT_NUM = ?', (self.wydz[z],)).fetchall()
        # wydzielenia nielesne lener, inne_wyl - bez celów
        for it in item:
            self._wykonaj(
                'insert into f_arod_goal (GOAL_TYPE_FL, ARODES_INT_NUM, '
                'SPECIES_CD, GOAL_RANK_ORDER) values (?,?,?,?)',
                (it[0], self.wydz[do], it[1], it[2]))

    def k_arod_stand_pec(self, z, do):
        self._tabela = 'f_arod_stand_pec'
        item = self.baza.cur.execute(
            'select FOREST_PEC_CD, PEC_RANK_ORDER from F_AROD_STAND_PEC '
            'where ARODES_INT_NUM = ?', (self.wydz[z],)).fetchall()
        for it in item:
            self._wykonaj(
                'insert into f_arod_stand_pec (FOREST_PEC_CD, ARODES_INT_NUM, '
                'PEC_RANK_ORDER) values (?,?,?)',
                (it[0], self.wydz[do], it[1]))

    def k_arod_storey(self, z, do):
        self._tabela = 'f_arod_storey'
        item = self.baza.cur.execute(
            'select STOREY_CD, STOREY_RANK_ORDER, STANDDENSITY_INDEX, '
            'MIXTURE_CD, DENSITY_CD, TREE_STOCK_CD, SILV_QUALITY_CD, '
            'LOCATION_CD from F_AROD_STOREY where ARODES_INT_NUM = ?',
            (self.wydz[z],)).fetchall()
        for it in item:
            self._wykonaj(
                'insert into f_arod_storey (ARODES_INT_NUM, STOREY_CD, '
                'STOREY_RANK_ORDER, STANDDENSITY_INDEX, MIXTURE_CD, '
                'DENSITY_CD, TREE_STOCK_CD, SILV_QUALITY_CD, LOCATION_CD) '
                'values (?,?,?,?,?,?,?,?,?)',
                (self.wydz[do],) + tuple(it))

    def k_storey_spec(self, z, do):
        self._tabela = 'f_storey_species'
        kolumny = [
            'STOREY_CD', 'SPECIES_RANK_ORDER', 'SPECIES_CD', 'PART_CD',
            'SPECIES_AGE', 'BHD', 'HEIGHT', 'VOLUME', 'SITE_CLASS_CD',
            'TECHN_QUALITY_CD', 'INCREMENT_CURRENT', 'VOLUME_TEMP',
            'INCREMENT_CURRENT_AREA',
        ]
        item = self.baza.cur.execute(
            'select ' + ', '.join(kolumny) + ' from F_STOREY_SPECIES '
            'where ARODES_INT_NUM = ?', (self.wydz[z],)).fetchall()
        cur_ind = self.baza.cur.execute(
            'select max(spec_stor_int_num) from f_storey_species'
        ).fetchall()[0][0] or 0

        sql = ('insert into f_storey_species (SPEC_STOR_INT_NUM, '
               'ARODES_INT_NUM, ' + ', '.join(kolumny) + ') values (' +
               ','.join('?' for _ in range(len(kolumny) + 2)) + ')')
        for it in item:
            cur_ind += 1
            self._wykonaj(sql, (cur_ind, self.wydz[do]) + tuple(it))


class PobierzDaneDock(QDockWidget, FORM_CLASS):
    def __init__(self, iface, parent=None):
        super(PobierzDaneDock, self).__init__(parent)
        self.setupUi(self)
        self.valid = False
        self.porzucone = True
        self.iface = iface
        self.kat = ''

        self.pushButton_anuluj.clicked.connect(self.porzuc)
        self.pushButton_baza.clicked.connect(self.kat_baza)
        self.pushButton_plik.clicked.connect(self.kat_warstwa)
        self.toolButton_usun.clicked.connect(self.skasuj)

        self.akcja_z = QAction('wskaż', self.iface.mainWindow())
        self.akcja_z.triggered.connect(self.klik_zrodlo)
        self.toolButton_z.setDefaultAction(self.akcja_z)

        self.akcja_do = QAction('wskaż', self.iface.mainWindow())
        self.akcja_do.triggered.connect(self.klik_do)
        self.toolButton_do.setDefaultAction(self.akcja_do)

        self.toolButton_usun.clicked.connect(self.usun)
        self.pushButton_uruchom.clicked.connect(self.klonuj)

    def usun(self):
        pass

    def kat_baza(self):
        sc = QFileDialog().getOpenFileName(
            self, 'Wskaż bazę Taksatora', self.kat, "Access MDB (*.mdb)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.lineEdit_baza.setText(sc)

    def kat_warstwa(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż plik z instrukcjami',
                                           self.kat,
                                           "instrukcje (*.txt)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.lineEdit_plik.setText(sc)

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if self.radioButton_k.isChecked():
            if os.path.isfile(self.lineEdit_plik.text()) and \
                    os.path.isfile(self.lineEdit_baza.text()):
                self.valid = True
                self.porzucone = False
            else:
                message = QMessageBox()
                message.setIcon(QMessageBox.Information)
                message.setWindowTitle('Błąd')
                message.setText(
                    'Nie udało się odnaleźć wszystkich podanych plików!')
                message.addButton(u"Zamknij", QMessageBox.ActionRole)
                message.exec_()
                return False
        else:
            if not os.path.isfile(self.lineEdit_baza.text()):
                return False
            if self.lineEdit_z.text() in ['', ' ']:
                return False
            if self.listWidget.count() == 0:
                return False

        return True

    def klik_zrodlo(self):
        self.tz = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.iface.mapCanvas().setMapTool(self.tz)
        self.tz.canvasClicked.connect(self.pobierz_z)

    def klik_do(self):
        self.ta = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.iface.mapCanvas().setMapTool(self.ta)
        self.ta.canvasClicked.connect(self.pobierz_do)

    def pobierz_z(self, koord):
        rec = QgsRectangle(koord[0]-0.1, koord[1]-0.1,
                           koord[0]+0.1, koord[1]+0.1)
        req = QgsFeatureRequest().setFilterRect(rec)
        f = ''
        if not self.iface.activeLayer():
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Niepoprawna warstwa', Qgis.Critical, 10
            )
            return False

        for fd in self.iface.activeLayer().getFeatures(req):
            f = fd['ADR_LES']

        if f in ['', None, 'NULL']:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Na pewno wskazałeś warstwę z kolumną ADR_LES?',
                Qgis.Critical,
                0
            )
        self.lineEdit_z.setText(f)

    def pobierz_do(self, koord):
        rec = QgsRectangle(koord[0]-0.1, koord[1]-0.1,
                           koord[0]+0.1, koord[1]+0.1)
        req = QgsFeatureRequest().setFilterRect(rec)
        f = ''
        if not self.iface.activeLayer():
            self.iface.messageBar().pushMessage(
                'BŁĄD', 'Niepoprawna warstwa', Qgis.Critical, 10
            )
            return False
        for fd in self.iface.activeLayer().getFeatures(req):
            f = fd['ADR_LES']

        if f == self.lineEdit_z.text():
            return

        if f not in ['', None, 'NULL']:
            self.listWidget.addItem(f)
        else:
            self.iface.messageBar().pushMessage(
                "BŁĄD",
                'Na pewno wskazałeś warstwę z kolumną ADR_LES?',
                Qgis.Critical,
                0
            )

    def skasuj(self):
        itms = self.listWidget.selectedItems()

        for i in range(self.listWidget.count()-1, -1, -1):
            if self.listWidget.item(i) in itms:
                self.listWidget.takeItem(i)

    def klonuj(self):
        klon = Klonuj(self.iface)
        if not self.sprawdz_ok():
            if not self.radioButton_k.isChecked():
                self.iface.messageBar().pushMessage(
                    'BŁĄD', 'Wskaż bazę, wydzielenie źródłowe i co najmniej '
                    'jedno wydzielenie docelowe.', Qgis.Critical, 10)
            return
        tryb_plik = self.radioButton_k.isChecked()
        if tryb_plik:
            wyn = klon.dane_konf(
                self.lineEdit_baza.text(), self.lineEdit_plik.text()
            )
        else:
            wyn = klon.dane_dock(
                self.lineEdit_baza.text(),
                self.lineEdit_z.text(),
                [self.listWidget.item(x).text()
                 for x in range(self.listWidget.count())]
            )

        if not wyn:
            return
        if not klon.sprawdz_dane():
            klon.baza.zamknij()
            return

        # cele z istniejącym opisem - decyzja użytkownika
        pomin = set()
        z_opisem = klon.wydzielenia_z_opisem()
        if z_opisem:
            decyzja = NadpisanieDialog(z_opisem, self).wybor()
            if decyzja == 'anuluj':
                klon.baza.zamknij()
                return
            if decyzja == 'pomin':
                pomin = {x[0] for x in z_opisem}

        klon.zrob_kopie()
        klon.klonuj(pomin)
        klon.baza.zamknij()
        klon.wyswietl_info()
        if not tryb_plik:
            self.listWidget.clear()


class NadpisanieDialog(QDialog):
    """Lista wydzieleń docelowych, które mają już opis w bazie, i wybór:
    nadpisz / pomiń / anuluj."""

    def __init__(self, wiersze, parent=None):
        super().__init__(parent)
        self._wybor = 'anuluj'
        self.setWindowTitle('Wydzielenia z istniejącym opisem')
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        opis = QLabel(
            f'{len(wiersze)} wydzieleń docelowych ma już opis w bazie. '
            '"Nadpisz" - ich dotychczasowy opis (piętra, gatunki, cele, '
            'osobliwości i dane F_SUBAREA) zostanie zastąpiony kopią. '
            '"Pomiń" - te wydzielenia zostaną bez zmian, pozostałe zostaną '
            'sklonowane. "Anuluj" - nic nie zostanie zmienione.')
        opis.setWordWrap(True)
        layout.addWidget(opis)

        tabela = QTableWidget(len(wiersze), 3)
        tabela.setHorizontalHeaderLabels(
            ['adr_les', 'stary rodzaj powierzchni', 'nowy rodzaj powierzchni'])
        tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabela.verticalHeader().setVisible(False)
        for i, (adr, stary, nowy) in enumerate(wiersze):
            tabela.setItem(i, 0, QTableWidgetItem(adr))
            tabela.setItem(i, 1, QTableWidgetItem(stary))
            tabela.setItem(i, 2, QTableWidgetItem(nowy))
        tabela.resizeColumnsToContents()
        tabela.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(tabela, 1)

        przyciski = QDialogButtonBox()
        for tekst, wartosc in (('Nadpisz', 'nadpisz'), ('Pomiń', 'pomin'),
                               ('Anuluj', 'anuluj')):
            rola = (QDialogButtonBox.RejectRole if wartosc == 'anuluj'
                    else QDialogButtonBox.AcceptRole)
            btn = przyciski.addButton(tekst, rola)
            btn.clicked.connect(lambda _, w=wartosc: self._ustaw(w))
        layout.addWidget(przyciski)

    def _ustaw(self, wartosc):
        self._wybor = wartosc
        if wartosc == 'anuluj':
            self.reject()
        else:
            self.accept()

    def wybor(self):
        self.exec_()
        return self._wybor


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
        self.ui.pushButton_baza.clicked.connect(self.kat_baza)
        self.ui.pushButton_wydz.clicked.connect(self.kat_warstwa)

    def porzuc(self):
        self.porzucone = True
        self.hide()

    def sprawdz_ok(self):
        if os.path.isfile(self.ui.lineEdit_wydz.text()) and \
                os.path.isfile(self.ui.lineEdit_baza.text()):
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

    def kat_baza(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż bazę Taksatora',
                                           self.kat,
                                           "Access MDB (*.mdb)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_baza.setText(sc)

    def kat_warstwa(self):
        sc = QFileDialog().getOpenFileName(self,
                                           'Wskaż plik z instrukcjami',
                                           self.kat,
                                           "instrukcje (*.txt)")[0]
        if sc != '':
            self.kat = os.path.dirname(sc)
            self.ui.lineEdit_wydz.setText(sc)
