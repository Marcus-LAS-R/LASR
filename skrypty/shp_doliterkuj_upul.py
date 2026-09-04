"""Doliteruj wydzielenia - wersja dla submenu Aktualizacja UPUL.

Osobny plik od skrypty/shp_doliterkuj.py (submenu Rozliczenie powierzchni,
używany też wewnętrznie przez shp_literkuj.py) - celowo NIE dzielą kodu,
żeby zmiany w jednym nie wpływały na drugi. Różnice względem wersji z
Rozliczenia powierzchni:

- Dialog ograniczony do wyboru warstwy WYDZ (bez wyboru źródła liter,
  ręcznego oddziału, "Doliterkuj od...") - litery zawsze czytane z
  warstwy SHP.
- Checkbox "Dopisz Lz na podstawie opis_pkt" (domyślnie włączony): jeśli
  obok warstwy WYDZ istnieje warstwa opisowa opis_pkt (patrz
  warstwa_opisow_dock.py), każde jeszcze niezaliterowane wydzielenie, na
  którym leży punkt GRUPA='LZ-Ł', dostaje WYDZ='Lz' przed literowaniem
  (i dzięki temu nie jest już literowane w dalszym kroku). Jeśli taki
  punkt leży na niezaliterowanym wydzieleniu, które ma już wypełnione
  ADR_LES (niespójny stan - adres zbudowany bez litery), operacja jest
  przerywana z komunikatem błędu zamiast cichego nadpisania.
"""
import os
import glob
import datetime
import processing
from operator import itemgetter

from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.core import (
    Qgis, QgsMessageLog, QgsSpatialIndex, QgsVectorLayer, QgsProject,
)

from .shp_literkuj import LITERY
from .ui.ui_shp_doliterkuj_upul import Ui_Dialog
from . import kopie_manipulacyjne
from . import warstwa_opisow_dock as opis
from .funkcje import wyczysc_katalog_temp

GRUPA_LZ = 'LZ-Ł'


def _ma_juz_litere(wartosc):
    """ Czy pole WYDZ jest juz wypelnione (nie jest puste/NULL)? Wzorowane
    1:1 na warunku z shp_literkuj.Literkuj, dla zgodnosci zachowania na
    tych samych danych (shapefile/DBF). """
    if wartosc is None:
        return False
    return str(wartosc) not in ["", " ", "NULL"]


def _oddz_nieprawidlowy(wartosc):
    """ Czy wartosc pola ODDZ NIE jest liczba naturalna z zakresu 1-9999?
    Jedyne dopuszczalne wartosci w kolumnie ODDZ to liczby calkowite
    1..9999 (np. '007' tez jest ok - liczy sie wartosc liczbowa). """
    if wartosc is None:
        return True
    tekst = str(wartosc).strip()
    if not tekst.isdigit():
        return True
    return not (1 <= int(tekst) <= 9999)


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


def _nastepna_wolna_litera(uzyte, litery=LITERY):
    """ Pierwsza litera z `litery` jeszcze nie uzyta w danej grupie
    (MUNICIP, COMMUNITY, ODDZ) - albo None, jesli wszystkie zajete. """
    for l in litery:
        if l not in uzyte:
            return l
    return None


def _zgadnij_baze(warstwa_sc):
    """ Probuje odgadnac plik bazy (.mdb) polozony katalog wyzej od
    wskazanej warstwy SHP (typowy uklad katalogow w tym projekcie) - zwraca
    sciezke tylko gdy znaleziono dokladnie jeden plik .mdb, w przeciwnym
    razie pusty string. Uzywana wylacznie do wskazania bazy przy kopii
    bezpieczenstwa. """
    if not warstwa_sc or not os.path.isfile(warstwa_sc):
        return ''
    kat = os.path.dirname(warstwa_sc)
    kandydaci = glob.glob(os.path.join(kat, '..', '*.mdb'))
    if len(kandydaci) == 1:
        return os.path.abspath(kandydaci[0])
    return ''


def _sciezka_opis_pkt(warstwa_sc):
    """ Sciezka do warstwy opis_pkt (patrz warstwa_opisow_dock.py) - w
    folderze SHP_opis, siostrzanym do folderu-nadrzednego wobec folderu z
    warstwa WYDZ (ten sam uklad katalogow, co przy tworzeniu warstw
    opisowych - patrz warstwa_opisow_dock._folder_opis). None, jesli plik
    nie istnieje - wtedy krok automatycznego wykrywania Lz jest pomijany
    bez bledu (nie kazdy projekt ma juz zalozone warstwy opisowe). """
    kat_wydz = os.path.dirname(warstwa_sc)
    kat_opis = os.path.join(os.path.dirname(kat_wydz), opis.NAZWA_FOLDER_OPIS)
    sc = os.path.join(kat_opis, opis.NAZWA_PUNKTY + '.shp')
    return sc if os.path.isfile(sc) else None


def _dopasuj_pkt_lz_do_wydz(pkt_lyr, wydz_fts, wydz_si):
    """ Dla kazdego punktu GRUPA='LZ-Ł' z warstwy opis_pkt znajduje
    dokladnie jedno wydzielenie, na ktorym lezy. Punkty poza WYDZ albo na
    wiecej niz jednym wydzieleniu (nakladajace sie poligony) sa pomijane -
    te przypadki wykrywa juz osobna kontrola geometrii (patrz
    shp_sprawdz_polozenie_opisow.py i baza_dopisz_opisy_taks.py). Zwraca
    liste feature'ow WYDZ trafionych przez dokladnie jeden punkt LZ-Ł. """
    if 'GRUPA' not in [f.name() for f in pkt_lyr.fields()]:
        return []
    wynik = []
    for pf in pkt_lyr.getFeatures():
        if str(pf['GRUPA']).strip() != GRUPA_LZ:
            continue
        geom = pf.geometry()
        if geom is None or geom.isEmpty():
            continue
        trafienia = [
            wydz_fts[wfid] for wfid in wydz_si.intersects(geom.boundingBox())
            if wydz_fts[wfid].geometry().contains(geom)
        ]
        if len(trafienia) == 1:
            wynik.append(trafienia[0])
    return wynik


class _Dialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.iface = iface
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        aktywna = self.iface.activeLayer()
        if aktywna is not None:
            try:
                sc = aktywna.dataProvider().dataSourceUri().split('|')[0]
                if sc and os.path.isfile(sc):
                    self.ui.lineEdit_warstwa.setText(sc)
            except Exception:
                pass

        self.ui.pushButton_warstwa.clicked.connect(self._wybierz_warstwe)
        self.ui.lineEdit_warstwa.textChanged.connect(self._aktualizuj)
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

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

    def _aktualizuj(self):
        self.ui.pushButton_ok.setEnabled(
            bool(self.ui.lineEdit_warstwa.text().strip()))

    def warstwa_sc(self):
        return self.ui.lineEdit_warstwa.text().strip()

    def wykryj_lz(self):
        return self.ui.checkBox_lz.isChecked()


def uruchom(iface):
    """ Pokazuje dialog wyboru warstwy (+ checkbox automatycznego Lz z
    opis_pkt), po czym wywoluje Doliterkuj na wybranej warstwie. """
    dlg = _Dialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False

    warstwa_sc = dlg.warstwa_sc()
    wykryj_lz = dlg.wykryj_lz()

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

    return Doliterkuj(iface, lyr, wykryj_lz=wykryj_lz)


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


def Doliterkuj(iface, lyr=False, wykryj_lz=True):  # noqa
    """ Kontynuacja literacji wydzielen - w odroznieniu od
    shp_literkuj.Literkuj NIE dotyka wydzielen, ktore juz maja litere
    (lub 'Lz') - przypisuje litery tylko nowo dodanym poligonom z pustym
    polem WYDZ, pomijajac przy wyborze litery te, ktore w danej grupie
    (MUNICIP, COMMUNITY, ODDZ) sa juz w uzyciu (zawsze na podstawie samej
    warstwy SHP). Dziala na warstwie przygotowanej tak samo jak do
    Literkuj (te same kolumny), na poczatku robi backup do temp/ (przed
    jakakolwiek modyfikacja warstwy), a na koniec dissolve (scala
    fragmenty 'Lz').

    Jesli wykryj_lz=True (domyslnie): przed literowaniem, o ile obok
    warstwy WYDZ istnieje warstwa opisowa opis_pkt (patrz
    warstwa_opisow_dock.py), kazde jeszcze niezaliterowane wydzielenie, na
    ktorym lezy punkt GRUPA='LZ-Ł', dostaje WYDZ='Lz' (i dzieki temu nie
    jest juz literowane w dalszym kroku). Jesli taki punkt lezy na
    niezaliterowanym wydzieleniu, ktore ma juz wypelnione ADR_LES
    (niespojny stan - adres zbudowany bez litery), operacja jest
    przerywana z komunikatem bledu zamiast cichego nadpisania. """
    if lyr is False:
        lyr = iface.activeLayer()

    QgsMessageLog.logMessage(
        '------ DOLITERUJ WYDZIELENIA (UPUL) --------- ',
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

    warstwa_sc = lyr.dataProvider().dataSourceUri().split('|')[0]

    zle_oddz = sorted(
        {str(f['ODDZ']).strip() for f in lyr.getFeatures()
         if _oddz_nieprawidlowy(f['ODDZ'])},
        key=lambda x: (len(x), x)
    )
    if zle_oddz:
        pokazane = zle_oddz[:20]
        wartosci = ', '.join(repr(v) for v in pokazane)
        if len(zle_oddz) > len(pokazane):
            wartosci += ', ...'
        QMessageBox.critical(
            iface.mainWindow(),
            'Nieprawidłowe wartości ODDZ',
            'W kolumnie ODDZ mogą być tylko liczby naturalne od 1 do 9999.'
            '\n\nZnaleziono nieprawidłowe wartości: ' + wartosci +
            '.\n\nPopraw oddziały przed doliterowaniem.'
        )
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nieprawidłowe wartości w kolumnie ODDZ - popraw oddziały przed '
            'doliterowaniem',
            Qgis.Critical,
            10)
        QgsMessageLog.logMessage(
            '------ KONIEC (nieprawidlowe ODDZ: ' + wartosci + ') -------- \n',
            'Las-R',
            Qgis.Info
        )
        return False

    # automatyczne wykrycie Lz na podstawie warstwy opisowej opis_pkt -
    # wylacznie odczyt na tym etapie, zeby walidacja zaszla PRZED
    # jakakolwiek modyfikacja warstwy (kopia bezpieczenstwa jeszcze nie
    # powstala)
    do_lz_id = set()
    if wykryj_lz:
        opis_pkt_sc = _sciezka_opis_pkt(warstwa_sc)
        if opis_pkt_sc:
            pkt_lyr = QgsVectorLayer(opis_pkt_sc, 'opis_pkt_doliterkuj', 'ogr')
            if pkt_lyr.isValid():
                wydz_fts = {f.id(): f for f in lyr.getFeatures()}
                wydz_si = QgsSpatialIndex()
                for f in wydz_fts.values():
                    wydz_si.insertFeature(f)

                ma_adr_les = 'ADR_LES' in [f.name() for f in lyr.fields()]
                juz_zaadresowane = []

                for wf in _dopasuj_pkt_lz_do_wydz(pkt_lyr, wydz_fts, wydz_si):
                    if _ma_juz_litere(wf['WYDZ']):
                        continue  # juz zaliterowane (w tym 'Lz') - nic do zrobienia
                    if ma_adr_les and str(wf['ADR_LES']).strip() not in (
                            '', 'None', 'NULL'):
                        juz_zaadresowane.append(wf)
                        continue
                    do_lz_id.add(wf.id())

                if juz_zaadresowane:
                    unikalne = sorted({
                        str(wf['ODDZ']).strip() + '/' +
                        str(wf['WYDZ']).strip() +
                        ' (ADR_LES=' + str(wf['ADR_LES']).strip() + ')'
                        for wf in juz_zaadresowane
                    }, key=lambda x: (len(x), x))
                    QMessageBox.critical(
                        iface.mainWindow(),
                        'LZ-Ł na już zaadresowanym wydzieleniu',
                        'Punkt opisowy LZ-Ł leży na niezaliterowanym '
                        'wydzieleniu, które ma już dopisany adres leśny '
                        '(ADR_LES) - to niespójny stan, popraw ręcznie '
                        'przed doliterowaniem.\n\nWydzielenia: ' +
                        ', '.join(unikalne)
                    )
                    iface.messageBar().pushMessage(
                        'BŁĄD',
                        'LZ-Ł na już zaadresowanym wydzieleniu - popraw '
                        'ręcznie (patrz komunikat)',
                        Qgis.Critical,
                        10)
                    QgsMessageLog.logMessage(
                        '------ KONIEC (LZ-Ł na już zaadresowanym WYDZ) '
                        '-------- \n',
                        'Las-R',
                        Qgis.Info
                    )
                    return False
            del pkt_lyr

    # kopia bezpieczeństwa PRZED jakąkolwiek modyfikacją warstwy
    # (ustawienie Lz z opis_pkt, przypisanie liter, dissolve) - ten sam
    # wzorzec co inne operacje niszczące w tej wtyczce
    # (kopie_manipulacyjne.zrob_kopie_manipulacyjna)
    sciezka = warstwa_sc[:-4]
    kat = os.path.dirname(sciezka)
    tempkat = os.path.join(kat, 'temp')
    czas = datetime.datetime.now().isoformat(
                    ).replace(":", "")[:-7].replace('-', '')

    if not os.path.isdir(tempkat):
        os.mkdir(tempkat)

    baza_do_kopii = _zgadnij_baze(sciezka + '.shp') or (sciezka + '.shp')
    folder_kopii = kopie_manipulacyjne.zrob_kopie_manipulacyjna(
        baza_do_kopii, [lyr], 'doliterkuj')
    if folder_kopii is None:
        iface.messageBar().pushMessage(
            'BŁĄD', 'Nie udało się utworzyć kopii bezpieczeństwa - '
            'operacja przerwana (żadne zmiany nie zostały zapisane)',
            Qgis.Critical, 10)
        QgsMessageLog.logMessage(
            '------ KONIEC (błąd kopii bezpieczeństwa) -------- \n',
            'Las-R', Qgis.Info)
        return False

    fnm = lyr.dataProvider().fieldNameMap()

    if do_lz_id:
        aktualizacja_lz = {fid: {fnm['WYDZ']: 'Lz'} for fid in do_lz_id}
        lyr.startEditing()
        lyr.dataProvider().changeAttributeValues(aktualizacja_lz)
        lyr.commitChanges()
        QgsMessageLog.logMessage(
            'Ustawiono WYDZ="Lz" wg punktów opisowych LZ-Ł dla ' +
            str(len(aktualizacja_lz)) + ' wydzieleń',
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
        wolna = _nastepna_wolna_litera(uzyte, LITERY)
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
        # zrob dissolva na warstwie wydz (scala fragmenty Lz) - kopia
        # bezpieczeństwa zrobiona wcześniej, przed jakąkolwiek modyfikacją
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

        # zwolnij uchwyt do warstwy posredniej przed czyszczeniem temp
        del wydz_diss
        wyczysc_katalog_temp(tempkat)

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
