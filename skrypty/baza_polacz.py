import os
import glob
import platform
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from datetime import datetime
from shutil import copyfile
from qgis.core import Qgis, QgsMessageLog

from .pw import PasekPostepu
from .baza_wrapper import Baza
from .baza_kontrola_slownikow_wgSULMN import KontrolaSlownikowWiele
from .baza_polacz_rejestr import (
    F_COMMUNITY, F_PARCEL_NADRZEDNA, V_ADDRESS_NADRZEDNA,
    GRUPA2_DZIECI, GRUPA3_DZIECI, rejestr_domyslny)
from .baza_polacz_dialog import WyborGrupDialog
from .baza_polacz_obreby_dialog import WyborObrebowDialog


def _kontrola_duplikatow_generic(katalog_raportu, sciezki, pobierz_klucze_fn,
                                  prefiks_pliku, tytul, opis_kontroli,
                                  formatuj_klucz=str):
    """Silnik wspólny dla blokujących kontroli duplikatów (wydzielenia,
    działki, ...) - sprawdza, czy ten sam klucz naturalny występuje w
    więcej niż jednej z podanych baz. Zwraca (duplikaty, sciezka_raportu);
    duplikaty to dict {klucz: [sciezki_baz]} - pusty dict gdy brak
    duplikatów. pobierz_klucze_fn(Baza) -> list|False."""
    mapa = {}
    for baza_sc in sciezki:
        baza = Baza(baza_sc)
        if not baza.polacz():
            QgsMessageLog.logMessage(
                'Kontrola duplikatów (' + opis_kontroli + ') — nie udało '
                'się połączyć z bazą: ' + baza_sc, 'Las-R', Qgis.Warning
            )
            continue
        klucze = pobierz_klucze_fn(baza)
        baza.zamknij()
        if klucze is False:
            continue
        for k in klucze:
            mapa.setdefault(k, []).append(baza_sc)

    duplikaty = {k: bazy for k, bazy in mapa.items() if len(bazy) > 1}
    if not duplikaty:
        return {}, None

    czas = datetime.now().isoformat().replace(':', '')[:-7]
    rap_sc = os.path.join(katalog_raportu, prefiks_pliku + czas + '.txt')

    with open(rap_sc, 'w', encoding='utf-8') as plik:
        plik.write(tytul + '\r\n')
        plik.write('Łączenie przerwane - popraw dane u źródła i uruchom '
                    'ponownie.\r\n')
        plik.write('=' * 72 + '\r\n\r\n')
        for k in sorted(duplikaty, key=formatuj_klucz):
            plik.write(formatuj_klucz(k) + ':\r\n')
            for b in duplikaty[k]:
                plik.write('   ' + b + '\r\n')
            plik.write('\r\n')

    return duplikaty, rap_sc


def _klucze_wydzielen(baza):
    wydz = baza.pobierz_wydzielenia()
    return list(wydz.keys()) if wydz is not False else False


def _arodes_w_obrebach(baza, dozwolone):
    """Zwraca zbiór ARODES_INT_NUM (typu WYDZIEL) tej bazy, które mają
    >=1 użytek (F_AROD_LAND_USE) w którymś z dozwolonych obrębów."""
    sql = ('select l.ARODES_INT_NUM, p.COUNTY_CD, p.DISTRICT_CD, '
           'p.MUNICIPALITY_CD, p.COMMUNITY_CD from (F_AROD_LAND_USE as l '
           'inner join F_PARCEL as p on l.PARCEL_INT_NUM = p.PARCEL_INT_NUM);')
    wynik = baza.pobierz(sql)
    if wynik is False:
        return set()
    return {row[0] for row in wynik if tuple(row[1:5]) in dozwolone}


def _klucze_wydzielen_z_filtrem(obreby_wybrane):
    """Buduje pobierz_klucze_fn dla kontroli duplikatów wydzieleń,
    uwzględniając per-bazowy filtr obrębów (przez F_AROD_LAND_USE ->
    F_PARCEL) - żeby duplikat poza wybranymi obrębami (i tak niekopiowany)
    nie blokował łączenia."""
    def fn(baza):
        wydz = baza.pobierz_wydzielenia()
        if wydz is False:
            return False
        dozwolone = obreby_wybrane.get(baza.baza)
        if dozwolone is None:
            return list(wydz.keys())
        dozwolone_arodes = _arodes_w_obrebach(baza, dozwolone)
        return [adr for adr, aint in wydz.items() if aint in dozwolone_arodes]
    return fn


def _klucze_dzialek_z_filtrem(obreby_wybrane):
    """Jak wyżej, dla kontroli duplikatów działek."""
    def fn(baza):
        klucze = baza.pobierz_klucze_dzialek()
        if klucze is False:
            return False
        dozwolone = obreby_wybrane.get(baza.baza)
        if dozwolone is None:
            return klucze
        return [k for k in klucze if k[:4] in dozwolone]
    return fn


def _kontrola_duplikatow_wydzieln(katalog_raportu, sciezki, obreby_wybrane=None):
    """Sprawdza, czy to samo wydzielenie (ADRESS_FOREST z F_ARODES,
    ARODES_TYP_CD='WYDZIEL') występuje w więcej niż jednej z podanych baz.
    Jeśli podano obreby_wybrane ({baza_sc: set|None}), sprawdza tylko
    wydzielenia, które faktycznie zostaną skopiowane (w wybranych obrębach)."""
    pobierz_klucze_fn = (
        _klucze_wydzielen_z_filtrem(obreby_wybrane)
        if obreby_wybrane else _klucze_wydzielen)
    return _kontrola_duplikatow_generic(
        katalog_raportu, sciezki, pobierz_klucze_fn, 'duplikaty_wydzielen_',
        'DUPLIKATY WYDZIELEŃ (ADRESS_FOREST) W BAZACH WEJŚCIOWYCH',
        'wydzieleń')


def _kontrola_duplikatow_dzialek(katalog_raportu, sciezki, obreby_wybrane=None):
    """Sprawdza, czy ta sama działka (COUNTY_CD+DISTRICT_CD+
    MUNICIPALITY_CD+COMMUNITY_CD+PARCEL_NR z F_PARCEL) występuje w więcej
    niż jednej z podanych baz. Jeśli podano obreby_wybrane, sprawdza tylko
    działki w wybranych obrębach."""
    pobierz_klucze_fn = (
        _klucze_dzialek_z_filtrem(obreby_wybrane)
        if obreby_wybrane else Baza.pobierz_klucze_dzialek)
    return _kontrola_duplikatow_generic(
        katalog_raportu, sciezki, pobierz_klucze_fn,
        'duplikaty_dzialek_',
        'DUPLIKATY DZIAŁEK (COUNTY_CD+DISTRICT_CD+MUNICIPALITY_CD+'
        'COMMUNITY_CD+PARCEL_NR) W BAZACH WEJŚCIOWYCH',
        'działek',
        formatuj_klucz=lambda k: '.'.join(str(x) for x in k))


class PolaczBazy():
    def __init__(self, iface):
        self.iface = iface

        self.baza0 = False  # baza do ktorej kopiujemy reszte danych
        self.lista = []  # lista ze sciezkami do baz w katalogu
        self.wybrane = rejestr_domyslny()  # nadpisywane przez wybierz_grupy()
        # {baza_sc: set(tuple)|None} - nadpisywane przez wybierz_obreby();
        # None dla danej bazy = brak filtra (wszystkie obreby dozwolone)
        self.obreby_wybrane = {}
        self.postep = PasekPostepu(self.iface).stworz_pasek(
            'Kopiowanie baz TPU')
        self.postep.setValue(0)

    def pobierz_katalog(self):
        wzorzec = "*.mdb" if platform.system()[:3] == 'Win' else "*.sqlite"

        # Natywny selektor folderow na Windows pokazuje WYLACZNIE
        # podfoldery (nigdy pliki), wiec katalog z samymi bazami wyglada
        # pusty i user nie ma jak sie upewnic, ze trafil we wlasciwe
        # miejsce przed zatwierdzeniem. Wlasny (nie-natywny) QFileDialog w
        # trybie Directory + ShowDirsOnly=False pokazuje pliki pasujace do
        # filtra obok folderow (wyszarzone, niewybieralne - wybiera sie
        # nadal caly folder), wiec baza widac od razu.
        dlg = QFileDialog(self.iface.mainWindow(), "Katalog z bazami danych", '')
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setOption(QFileDialog.ShowDirsOnly, False)
        dlg.setOption(QFileDialog.DontUseNativeDialog, True)
        dlg.setNameFilter(wzorzec)
        # Wbudowane etykiety/przyciski Qt-owego (nie-natywnego) dialogu
        # potrafia zostac po angielsku (np. "Choose") jesli tlumaczenia Qt
        # nie sa zaladowane w tym procesie - wymuszamy polskie teksty
        # jawnie przez publiczne API zamiast liczyc na runtime Qt.
        dlg.setLabelText(QFileDialog.LookIn, "Szukaj w:")
        dlg.setLabelText(QFileDialog.FileName, "Folder:")
        dlg.setLabelText(QFileDialog.FileType, "Pliki typu:")
        dlg.setLabelText(QFileDialog.Accept, "Wybierz folder")
        dlg.setLabelText(QFileDialog.Reject, "Anuluj")
        if dlg.exec_() != QDialog.Accepted or not dlg.selectedFiles():
            return False
        bazy_kat = dlg.selectedFiles()[0]

        bTemp = glob.glob(os.path.join(bazy_kat, wzorzec))

        mess = ''
        if len(bTemp) == 0:
            mess = 'Nie odnalazłem żadnej bazy we wskazanym katalogu!'
        elif len(bTemp) == 1:
            mess = 'Do łącznia wymagane są przynajmniej ' + \
                'dwie bazy drogi użyszkodniku ;)'

        # sortujemy, zeby wybor bazy bazowej (lista[0]) byl deterministyczny
        # i przewidywalny dla uzytkownika, zamiast zalezec od kolejnosci
        # zwracanej przez system plikow
        bTemp.sort()
        self.lista = bTemp

        if mess != '':
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                mess,
                Qgis.Critical,
                0)
            return False

        self.iface.messageBar().pushMessage(
            'Połącz bazy TPU',
            'Znaleziono ' + str(len(self.lista)) + ' baz. Bazą bazową '
            '(do której zostaną dopisane pozostałe) będzie: ' +
            os.path.basename(self.lista[0]),
            Qgis.Info,
            10
        )

        return True

    def wybierz_obreby(self):
        """Pokazuje dialog wyboru obrębów (osobno dla każdej bazy z
        self.lista). Zwraca True i zapisuje wybór w self.obreby_wybrane,
        albo False jeśli użytkownik zrezygnował. To pierwszy, nadrzędny
        filtr - wywoływany przed wyborem grup tabel."""
        dlg = WyborObrebowDialog(self.iface, self.lista)
        if dlg.exec_() != QDialog.Accepted:
            return False
        self.obreby_wybrane = dlg.wybor()
        return True

    def wybierz_grupy(self):
        """Pokazuje dialog wyboru grup/tabel do łączenia. Zwraca True i
        zapisuje wybór w self.wybrane, albo False jeśli użytkownik
        zrezygnował."""
        dlg = WyborGrupDialog(self.iface)
        if dlg.exec_() != QDialog.Accepted:
            return False
        self.wybrane = dlg.wybor()
        return True

    def kontrola_duplikatow(self):
        """Sprawdza duplikaty wydzieleń (jeśli F_ARODES wybrane) i działek
        (jeśli F_PARCEL wybrane) między wszystkimi bazami z self.lista,
        respektując wybór obrębów (self.obreby_wybrane). Zwraca False i
        przerywa łączenie (bez możliwości kontynuowania), jeśli znajdzie
        duplikaty - w przeciwieństwie do kontroli słownikowej to kontrola
        blokująca."""
        katalog, _ = os.path.split(self.lista[0])
        if self.wybrane.get('f_arodes'):
            fn = (lambda k, s: _kontrola_duplikatow_wydzieln(
                k, s, self.obreby_wybrane))
            if not self._sprawdz_i_zglos(fn, katalog, 'wydzieleń'):
                return False
        if self.wybrane.get('f_parcel'):
            fn = (lambda k, s: _kontrola_duplikatow_dzialek(
                k, s, self.obreby_wybrane))
            if not self._sprawdz_i_zglos(fn, katalog, 'działek'):
                return False
        return True

    def _sprawdz_i_zglos(self, funkcja_kontroli, katalog, opis):
        duplikaty, rap_sc = funkcja_kontroli(katalog, self.lista)
        if not duplikaty:
            return True

        self.iface.messageBar().clearWidgets()
        self.iface.messageBar().pushMessage(
            'BŁĄD',
            'Znaleziono ' + str(len(duplikaty)) + ' zdublowanych ' + opis +
            ' w bazach wejściowych - łączenie przerwane. Raport: ' + rap_sc,
            Qgis.Critical, 0
        )
        return False

    def kontrola_wstepna(self):
        """Kontroluje słownikowo wszystkie bazy z self.lista przed łączeniem.
        Zwraca True jeśli można kontynuować łączenie (brak błędów albo
        użytkownik zdecydował się kontynuować mimo błędów), False gdy
        użytkownik zrezygnował."""
        katalog, _ = os.path.split(self.lista[0])
        ile_blednych, rap_sc = KontrolaSlownikowWiele(katalog, self.lista)

        if ile_blednych == 0:
            self.iface.messageBar().pushMessage(
                'Kontrola słownikowa',
                'Bazy wejściowe zgodne ze słownikiem, raport: ' + rap_sc,
                Qgis.Success, 5
            )
            return True

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle('Kontrola słownikowa baz wejściowych')
        msg.setText(
            'Kontrola słownikowa baz wejściowych wykryła ' +
            str(ile_blednych) + ' błędnych wartości.\n' +
            'Raport: ' + rap_sc + '\n\n' +
            'Błędne dane mogą zablokować dalszy import.\n' +
            'Kontynuować łączenie mimo błędów?'
        )
        msg.addButton('Nie', QMessageBox.ActionRole)
        tak = msg.addButton('Tak', QMessageBox.ActionRole)
        msg.exec_()
        return msg.clickedButton() == tak

    def stworz_docelowa(self):
        katalog, plik = os.path.split(self.lista[0])
        self.czas = \
            datetime.now().isoformat().replace(':', '')[:-7]

        if platform.system()[:3] == 'Win':
            plikn = 'baza_polaczona_' + self.czas + '.mdb'
        else:
            plikn = 'baza_polaczona_' + self.czas + '.sqlite'

        try:
            copyfile(self.lista[0], os.path.join(katalog, plikn))
        except Exception:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się skopiować bazy, masz prawa dostępu do zapisu?',
                Qgis.Critical, 0)
            return False

        self.baza0 = Baza(os.path.join(katalog, plikn))

        if self.baza0.polacz():
            self.postep.setValue(5)
            return True
        else:
            self.iface.messageBar().clearWidgets()
            self.iface.messageBar().pushMessage(
                'BŁĄD',
                'Nie udało się podłączyć do skopiowanej bazy',
                Qgis.Critical, 0)
            return False

    def przygotuj_kopiowanie(self):
        if not self.stworz_docelowa():
            return False
        return True

    def kopiuj(self):
        proc = int(90/len(self.lista))
        ust = 10
        bledy_wszystkie = []  # (baza_zrodlowa, tabela, opis_wiersza, blad)
        for bsc in self.lista[1:]:
            ust = ust + proc
            self.postep.setValue(ust)
            baza_zrodlowa = Baza(bsc)
            if baza_zrodlowa.polacz():
                lacz = Laczenie(
                    self.baza0, baza_zrodlowa, self.wybrane,
                    dozwolone_obreby=self.obreby_wybrane.get(bsc))
                lacz.p_f_max()
                lacz.p_f_arodes()
                lacz.p_f_community()
                lacz.p_pozostale_nadrzedne()
                lacz.p_tabele()
                lacz.d_tabele()
                for tabela, opis_wiersza, blad in lacz.l_bledy_wpisu:
                    bledy_wszystkie.append((bsc, tabela, opis_wiersza, blad))
                for baza_sc, tabela, blad in lacz.l_bledy_odczytu:
                    bledy_wszystkie.append(
                        (baza_sc, tabela, '(cała tabela - błąd odczytu)', blad))
                baza_zrodlowa.zamknij()

        self.postep.setValue(100)
        self.baza0.zamknij()
        self.iface.messageBar().clearWidgets()

        if bledy_wszystkie:
            katalog, _ = os.path.split(self.lista[0])
            rap_sc = self._zapisz_raport_bledow(katalog, bledy_wszystkie)
            self.iface.messageBar().pushMessage(
                'POŁĄCZONE Z BŁĘDAMI',
                'Łączenie zakończone, ale wystąpiło ' +
                str(len(bledy_wszystkie)) +
                ' błędów odczytu/zapisu. Raport: ' + rap_sc,
                Qgis.Warning,
                0
            )
        else:
            self.iface.messageBar().pushMessage(
                'POŁĄCZONE',
                'Łączenie ' + str(len(self.lista)) +
                ' baz zakończone powodzeniem',
                Qgis.Success,
                0
            )

    def _zapisz_raport_bledow(self, katalog, bledy):
        czas = datetime.now().isoformat().replace(':', '')[:-7]
        rap_sc = os.path.join(
            katalog, 'bledy_zapisu_laczenie_' + czas + '.txt')

        with open(rap_sc, 'w', encoding='utf-8') as plik:
            plik.write('BŁĘDY ZAPISU PRZY ŁĄCZENIU BAZ TPU\r\n')
            plik.write('=' * 72 + '\r\n\r\n')
            for baza_sc, tabela, opis_wiersza, blad in bledy:
                plik.write('Baza źródłowa: ' + baza_sc + '\r\n')
                plik.write('Tabela:        ' + tabela + '\r\n')
                plik.write('Wiersz:        ' + opis_wiersza + '\r\n')
                plik.write('Błąd:          ' + blad + '\r\n\r\n')

        return rap_sc


class Laczenie():
    def __init__(self, baza0, baza, wybrane=None, dozwolone_obreby=None):
        self.baza0 = baza0  # baza docelowa
        self.baza = baza  # baza z ktorej kopiujemy
        self.wybrane = wybrane if wybrane is not None else rejestr_domyslny()
        # None = brak filtra obrebow (wszystko dozwolone, zachowanie jak
        # dotychczas); w przeciwnym razie zbior krotek (COUNTY_CD,
        # DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD)
        self.dozwolone_obreby = dozwolone_obreby

        # pola ktorych wartosci maksymalne musimy znac
        self.maxint = -1  # max arodes_intnum w bazie0
        self.maxspecstor = -1  # spec_stor_int_num
        self.maxparcel = -1
        self.maxaddr = -1
        self.maxset = -1
        self.maxdamage = -1

        self.l_wpisanych_innych = []  # lista wpisanych adress_forest do bazy
        self.l_bledy_wpisu = []  # lista (tabela, opis_wiersza, blad) z d_tabele
        self.l_bledy_odczytu = []  # lista (baza_sc, tabela, blad) z odczytu

        self.sl_arodes = {}  # slownik z starym arodes: nowy arodes
        self.sl_parcel = {}
        self.sl_addr = {}
        self.f_arodes = []
        self.f_community_nowe = []
        self.f_parcel_nowe = []
        self.v_address_nowe = []

        # dzieci wybrane do skopiowania (Grupa 2 + Grupa 3), oraz bufor
        # odczytanych wierszy per-tabela - na instancji Laczenie, NIE na
        # wspoldzielonych obiektach rejestru (GRUPA2_DZIECI/GRUPA3_DZIECI sa
        # modul-poziomu singletonami uzywanymi ponownie dla kazdej kolejnej
        # bazy zrodlowej w PolaczBazy.kopiuj() - trzymanie tam bufora
        # wierszy byloby wyciekiem stanu miedzy bazami)
        self.dzieci = [t for t in (GRUPA2_DZIECI + GRUPA3_DZIECI)
                        if self.wybrane.get(t.klucz)]
        self._wiersze = {}

    def p_f_arodes(self):
        # pobierz arodesy z obu baz i sprawdz co sie powtarza aby nie dublowac
        # danych w bazie
        if not self.wybrane.get('f_arodes'):
            return  # sl_arodes/f_arodes/maxint zostaja w stanie poczatkowym

        # jawna lista kolumn (zamiast select *) w kolejnosci zgodnej z
        # insertem w d_tabele() - kolejnosc fizycznych kolumn w tabeli
        # moze sie roznic miedzy bazami, nazwy nie
        sql = ('select ARODES_INT_NUM, ADRESS_FOREST, ARODES_TYP_CD, '
               'ORDER_KEY, ADRESS_VALID, PROT_INT_NUM, TEMP_RAPORT '
               'from f_arodes order by arodes_int_num asc;')
        arod_org = self.baza0.pobierz(sql)
        arod_zrd = self.baza.pobierz(sql)

        if arod_org is False:
            self.l_bledy_odczytu.append(
                (self.baza0.baza, 'f_arodes',
                 'Nie udało się odczytać tabeli (baza docelowa)'))
            arod_org = []
        if arod_zrd is False:
            self.l_bledy_odczytu.append(
                (self.baza.baza, 'f_arodes',
                 'Nie udało się odczytać tabeli (baza źródłowa)'))
            arod_zrd = []

        sl_org_baza = {x[1] for x in arod_org}
        dozwolone_arodes = self._dozwolone_arodes_wydziel()

        # tutaj napewno nie bedzie Wydzielen ale moga zdarzyc sie oddzialy,
        # obreby lub lesnictwa
        for it in arod_zrd:
            # filtr obrebow dotyczy tylko wydzielen (WYDZIEL) - rekordy
            # administracyjne (oddzial/lesnictwo/obreb lesny) nie maja
            # odpowiednika w obrebie ewidencyjnym i nie sa filtrowane
            if (dozwolone_arodes is not None and it[2] == 'WYDZIEL'
                    and it[0] not in dozwolone_arodes):
                continue
            if it[1] not in sl_org_baza:
                self.maxint += 1
                self.f_arodes.append([self.maxint] + list(it[1:]))
                self.sl_arodes[it[0]] = self.maxint
            else:
                self.l_wpisanych_innych.append(it[1])

    def _dozwolone_arodes_wydziel(self):
        """Zwraca zbiór starych ARODES_INT_NUM (z bazy źródłowej) typu
        WYDZIEL, które mają >=1 użytek (F_AROD_LAND_USE) w wybranym
        obrębie. None gdy brak filtra obrębów (wszystko dozwolone)."""
        if self.dozwolone_obreby is None:
            return None
        sql = ('select l.ARODES_INT_NUM, p.COUNTY_CD, p.DISTRICT_CD, '
               'p.MUNICIPALITY_CD, p.COMMUNITY_CD from (F_AROD_LAND_USE as l '
               'inner join F_PARCEL as p on l.PARCEL_INT_NUM = p.PARCEL_INT_NUM);')
        wynik = self.baza.pobierz(sql)
        if wynik is False:
            self.l_bledy_odczytu.append(
                (self.baza.baza, 'F_AROD_LAND_USE/F_PARCEL',
                 'Nie udało się zweryfikować obrębów wydzieleń'))
            return set()
        return {row[0] for row in wynik if tuple(row[1:5]) in self.dozwolone_obreby}

    def _polacz_nadrzedna(self, definicja, licznik_poczatkowy, filtr_wiersza=None):
        """Generyczny odpowiednik p_f_arodes() dla nowych hierarchii kluczy
        surogatowych (F_PARCEL -> sl_parcel, V_ADDRESS -> sl_addr): jawna
        lista kolumn, opcjonalny dedup po kluczu naturalnym, renumeracja
        surogatu i budowa slownika remapu stary -> nowy."""
        sql = 'select ' + ', '.join(definicja.kolumny) + ' from ' + definicja.nazwa + ';'
        org = self.baza0.pobierz(sql)
        zrd = self.baza.pobierz(sql)
        if org is False:
            self.l_bledy_odczytu.append(
                (self.baza0.baza, definicja.nazwa,
                 'Nie udało się odczytać tabeli (baza docelowa)'))
            org = []
        if zrd is False:
            self.l_bledy_odczytu.append(
                (self.baza.baza, definicja.nazwa,
                 'Nie udało się odczytać tabeli (baza źródłowa)'))
            zrd = []

        if filtr_wiersza is not None:
            zrd = [w for w in zrd if filtr_wiersza(w)]

        istniejace = None
        if definicja.funkcja_klucza_dedup is not None:
            istniejace = {definicja.funkcja_klucza_dedup(w) for w in org}

        licznik = licznik_poczatkowy
        remap, nowe = {}, []
        for w in zrd:
            if istniejace is not None and definicja.funkcja_klucza_dedup(w) in istniejace:
                continue
            licznik += 1
            stary = w[definicja.indeks_klucza]
            wiersz = list(w)
            wiersz[definicja.indeks_klucza] = licznik
            nowe.append(wiersz)
            remap[stary] = licznik

        for fk in definicja.fk_wewnetrzne:
            idx = definicja.kolumny.index(fk.kolumna)
            for wiersz in nowe:
                wart = wiersz[idx]
                if wart not in (None, 0):
                    wiersz[idx] = remap.get(wart, wart)

        setattr(self, definicja.slownik_docelowy, remap)
        return nowe, licznik

    def p_pozostale_nadrzedne(self):
        """Grupa 2 (jeśli wybrana): F_PARCEL -> sl_parcel, V_ADDRESS ->
        sl_addr. Muszą zostać wywołane przed p_tabele()/d_tabele(), bo
        F_PARCEL_LAND_USE/V_PARCEL_PARTICIPATION/F_AROD_LAND_USE zależą od
        tych słowników."""
        if self.wybrane.get('f_parcel'):
            filtr = None
            if self.dozwolone_obreby is not None:
                dozwolone = self.dozwolone_obreby

                def filtr(w):
                    return (w[2], w[3], w[4], w[5]) in dozwolone
            self.f_parcel_nowe, self.maxparcel = self._polacz_nadrzedna(
                F_PARCEL_NADRZEDNA, self.maxparcel, filtr_wiersza=filtr)
        if self.wybrane.get('v_address'):
            # V_ADDRESS nie ma pol COUNTY/DISTRICT/MUNICIPALITY/COMMUNITY -
            # brak filtra obrebow, jego dzieci (V_PARCEL_PARTICIPATION) i tak
            # zostana odfiltrowane przez brak dzialki w sl_parcel
            self.v_address_nowe, self.maxaddr = self._polacz_nadrzedna(
                V_ADDRESS_NADRZEDNA, self.maxaddr)

    def p_f_community(self):
        """Grupa 1 (zawsze kopiowana): dedup po pelnym kluczu naturalnym
        (COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD) - duplikaty
        sa oczekiwane (wspolna geografia miedzy bazami tego samego
        nadlesnictwa) i pomijane cicho, bez raportowania."""
        sql = 'select ' + ', '.join(F_COMMUNITY.kolumny) + ' from F_COMMUNITY;'
        org = self.baza0.pobierz(sql)
        zrd = self.baza.pobierz(sql)
        if org is False:
            self.l_bledy_odczytu.append(
                (self.baza0.baza, 'F_COMMUNITY',
                 'Nie udało się odczytać tabeli (baza docelowa)'))
            org = []
        if zrd is False:
            self.l_bledy_odczytu.append(
                (self.baza.baza, 'F_COMMUNITY',
                 'Nie udało się odczytać tabeli (baza źródłowa)'))
            zrd = []
        if self.dozwolone_obreby is not None:
            zrd = [w for w in zrd
                   if F_COMMUNITY.funkcja_klucza_dedup(w) in self.dozwolone_obreby]
        istniejace = {F_COMMUNITY.funkcja_klucza_dedup(w) for w in org}
        self.f_community_nowe = [
            w for w in zrd if F_COMMUNITY.funkcja_klucza_dedup(w) not in istniejace]

    def p_tabele(self):
        for t in self.dzieci:
            sql = 'select ' + ', '.join(t.kolumny) + ' from ' + t.nazwa + ';'
            pob = self.baza.pobierz(sql)
            if pob is False:
                self.l_bledy_odczytu.append(
                    (self.baza.baza, t.nazwa, 'Nie udało się odczytać tabeli'))
                pob = []
            self._wiersze[t.klucz] = pob

    def p_f_max(self):
        # metoda pobiera nawieksze wartosci surogatow w bazie docelowej,
        # zeby wiedziec od czego zaczac numeracje nowych wierszy
        self.maxint = self._max('f_arodes', 'arodes_int_num', self.maxint)
        self.maxspecstor = self._max(
            'f_storey_species', 'spec_stor_int_num', self.maxspecstor)
        if self.wybrane.get('f_parcel'):
            self.maxparcel = self._max('f_parcel', 'parcel_int_num', self.maxparcel)
        if self.wybrane.get('v_address'):
            self.maxaddr = self._max('v_address', 'addr_nr', self.maxaddr)
        if self.wybrane.get('f_set'):
            self.maxset = self._max('f_set', 'set_int_num', self.maxset)
        if self.wybrane.get('f_arod_damage'):
            self.maxdamage = self._max(
                'f_arod_damage', 'damage_int_num', self.maxdamage)

    def _max(self, tabela, pole, domyslnie):
        wynik = self.baza0.pobierz('select max(' + pole + ') from ' + tabela + ';')
        if wynik is not False and wynik[0][0] is not None:
            return wynik[0][0]
        return domyslnie

    def _wpisz(self, sql, params, tabela, opis_wiersza):
        """Wykonuje insert z obsługą wyjątków - błąd nie przerywa całego
        łączenia, tylko jest zapamiętywany w self.l_bledy_wpisu."""
        try:
            self.baza0.cur.execute(sql, params)
            self.baza0.con.commit()
            return True
        except Exception as e:
            self.l_bledy_wpisu.append((tabela, opis_wiersza, str(e)))
            return False

    def d_tabele(self):
        # dopisz do bazy docelowej info z bazy zrodlowej
        for row in self.f_community_nowe:
            sql = ('insert into F_COMMUNITY (' + ', '.join(F_COMMUNITY.kolumny) +
                   ') values (' + '?,' * (len(row) - 1) + '?);')
            self._wpisz(sql, row, 'F_COMMUNITY', 'klucz=' + str(tuple(row[:4])))

        for row in self.f_arodes:
            sql = 'insert into f_arodes (ARODES_INT_NUM, ADRESS_FOREST, ' + \
                ' ARODES_TYP_CD, ORDER_KEY, ADRESS_VALID, PROT_INT_NUM, ' + \
                'TEMP_RAPORT) values (' + '?,'*(len(row)-1) + '?);'

            self._wpisz(sql, row, 'f_arodes', 'ADRESS_FOREST=' + str(row[1]))

        if self.wybrane.get('f_parcel'):
            self._wpisz_wiersze(F_PARCEL_NADRZEDNA, self.f_parcel_nowe)
        if self.wybrane.get('v_address'):
            self._wpisz_wiersze(V_ADDRESS_NADRZEDNA, self.v_address_nowe)

        for t in self.dzieci:
            self._polacz_dziecko(t)

    def _wpisz_wiersze(self, definicja, wiersze):
        for row in wiersze:
            sql = ('insert into ' + definicja.nazwa + ' (' +
                   ', '.join(definicja.kolumny) + ') values (' +
                   '?,' * (len(row) - 1) + '?);')
            opis = (definicja.kolumny[definicja.indeks_klucza] + '=' +
                    str(row[definicja.indeks_klucza]))
            self._wpisz(sql, row, definicja.nazwa, opis)

    def _polacz_dziecko(self, t):
        """Wpisuje wiersze jednej tabeli-dziecka, remapujac kazda kolumne
        FK przez odpowiedni slownik (sl_arodes/sl_parcel/sl_addr) i
        nadajac nowa wartosc wlasnego surogatu, jesli tabela go ma
        (analogicznie do dzisiejszego SPEC_STOR_INT_NUM)."""
        for row in self._wiersze.get(t.klucz, []):
            nag, its, pomin = [], [], False
            for kolumna, wartosc in zip(t.kolumny, row):
                if kolumna == t.wlasny_klucz:
                    continue  # dopisywane na koncu, po ew. pominieciu wiersza

                fk = next((f for f in t.fk if f.kolumna == kolumna), None)
                if fk is not None:
                    if wartosc in (None, 0) and not fk.wymagane:
                        nag.append(kolumna)
                        its.append(wartosc)
                        continue
                    slow = getattr(self, fk.slownik)
                    if wartosc not in slow:
                        pomin = True
                        break
                    nag.append(kolumna)
                    its.append(slow[wartosc])
                elif wartosc is not None:
                    nag.append(kolumna)
                    its.append(wartosc)

            if pomin:
                continue

            if t.wlasny_klucz:
                nowy = getattr(self, t.wlasny_klucz_licznik) + 1
                setattr(self, t.wlasny_klucz_licznik, nowy)
                nag.append(t.wlasny_klucz)
                its.append(nowy)

            sql = 'insert into ' + t.nazwa + ' (' + ','.join(nag) + \
                ') values (' + ','.join(['?'] * len(its)) + ');'
            opis = ','.join(n + '=' + str(v) for n, v in zip(nag, its))
            self._wpisz(sql, its, t.nazwa, opis)
