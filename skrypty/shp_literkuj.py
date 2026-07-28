import os
import glob
import datetime
import processing
from qgis.core import (
    Qgis, QgsMessageLog, QgsVectorLayer, QgsProject, QgsFeature, QgsField,
    QgsGeometry,
)
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QVariant
from operator import itemgetter

from . import kopie_manipulacyjne
from .funkcje import wyczysc_katalog_temp


def _zgadnij_baze(warstwa_sc):
    """ Probuje odgadnac plik bazy (.mdb) polozony katalog wyzej od
    wskazanej warstwy SHP (typowy uklad katalogow w tym projekcie) - zwraca
    sciezke tylko gdy znaleziono dokladnie jeden plik .mdb, w przeciwnym
    razie pusty string. Duplikat funkcji z shp_doliterkuj.py (import
    zwrotny niemozliwy - ten modul importuje LITERY stamtad). """
    if not warstwa_sc or not os.path.isfile(warstwa_sc):
        return ''
    kat = os.path.dirname(warstwa_sc)
    kandydaci = glob.glob(os.path.join(kat, '..', '*.mdb'))
    if len(kandydaci) == 1:
        return os.path.abspath(kandydaci[0])
    return ''

# kolejnosc liter przydzielanych wydzieleniom w obrebie grupy (oddz/gmina/
# obreb) - uzywana tez przez shp_doliterkuj.py do kontynuacji literacji
LITERY = [
    "a", "b", "c", "d", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o",
    "p", "r", "s", "t", "w", "x", "y", "z", "ax", "bx", "cx", "dx", "fx",
    "gx", "hx", "ix", "jx", "kx", "lx", "mx", "nx", "ox", "px", "rx", "sx",
    "tx", "wx", "xx", "yx", "zx", "ay", "by", "cy", "dy", "fy", "gy", "hy",
    "iy", "jy", "ky", "ly", "my", "ny", "oy", "py", "ry", "sy", "ty", "wy",
    "xy", "yy", "zy", "az", "bz", "cz", "dz", "fz", "gz", "hz", "iz", "jz",
    "kz", "mz", "nz", "oz", "pz", "rz", "sz", "tz", "wz", "xz", "yz", "zz"
]


def _puste(wartosc):
    """ Czy wartosc pola WYDZ oznacza brak przypisanej litery? `str(None)`
    daje 'None', ktore nie jest rownoznaczne literalowi None ani 'NULL' -
    porownanie trzeba zrobic przed rzutowaniem na str, inaczej prawdziwy
    NULL zostaje pomylony z "wydz ma juz litere". """
    if wartosc is None:
        return True
    return str(wartosc) in ["", " ", "NULL"]


def Literkuj(iface, lyr=False):  # noqa
    if lyr is False:
        lyr = iface.activeLayer()

    lit = LITERY

    QgsMessageLog.logMessage(
        '------ LITERKUJ WYDZIELENIA --------- ',
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

    # zdefiniuj nizbedne pola w warstwie
    pola = [
        'COMMUNITY',
        'MUNICIP',
        'WYDZ',
        'ODDZ',
    ]
    sl = {}  # slownik z zaliterkowanymi wydz {feat.id: 'lit', ...}
    tab = []  # tabela z danymi do sortowania kolejnosci wydz

    # sprawdz czy mamy wszystkie pola w bazie
    braki = [x for x in pola if x not in [y.name() for y in lyr.fields()]]
    if len(braki) > 0:
        iface.messageBar().pushMessage(
            'BRAK KOLUMN',
            'Brakuje kolumn w zaznaczonej warstwie: '+', '.join(braki),
            Qgis.Critical,
            10)
        return False

    wymus_od_nowa = False
    ma_litery = any(
        not _puste(f['WYDZ']) and str(f['WYDZ']).upper() != 'LZ'
        for f in lyr.getFeatures()
    )
    if ma_litery:
        monit = QMessageBox(iface.mainWindow())
        monit.setWindowTitle('Wydzielenia już uzupełnione')
        monit.setText(
            'W warstwie są już wydzielenia z wpisaną literą (WYDZ) - "Lz" '
            'nie liczy się jako wpisana litera i zawsze zostaje bez zmian.'
            '\n\nCo zrobić?'
        )
        btn_porzuc = monit.addButton('Porzuć', QMessageBox.RejectRole)
        btn_doliteruj = monit.addButton('Doliteruj', QMessageBox.AcceptRole)
        btn_doliteruj.setToolTip('Na podstawie SHP')
        btn_nadpisz = monit.addButton('Nadpisz', QMessageBox.DestructiveRole)
        btn_nadpisz.setToolTip('Literuje wszystko od początku')
        monit.setDefaultButton(btn_porzuc)
        monit.exec_()
        klikniety = monit.clickedButton()

        if klikniety == btn_doliteruj:
            from .shp_doliterkuj import Doliterkuj
            QgsMessageLog.logMessage(
                '------ KONIEC (przekazano do Doliterkuj) -------- \n',
                'Las-R',
                Qgis.Info
            )
            return Doliterkuj(iface, lyr)
        elif klikniety == btn_nadpisz:
            wymus_od_nowa = True
        else:
            iface.messageBar().pushMessage(
                'ANULOWANO',
                'Literowanie przerwane przez użytkownika',
                Qgis.Warning,
                10)
            QgsMessageLog.logMessage(
                '------ KONIEC (anulowano) -------- \n',
                'Las-R',
                Qgis.Info
            )
            return False

    oddz_puste = sum(1 for f in lyr.getFeatures() if _puste(f['ODDZ']))
    if oddz_puste > 0:
        odp = QMessageBox.question(
            iface.mainWindow(),
            'Puste pole ODDZ',
            'W warstwie jest ' + str(oddz_puste) + ' wydzieleń bez '
            'uzupełnionego pola ODDZ - literowanie w takich grupach może '
            'być nieprzewidywalne.\n\nKontynuować mimo to?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if odp != QMessageBox.Yes:
            iface.messageBar().pushMessage(
                'ANULOWANO',
                'Literowanie przerwane przez użytkownika',
                Qgis.Warning,
                10)
            QgsMessageLog.logMessage(
                '------ KONIEC (anulowano) -------- \n',
                'Las-R',
                Qgis.Info
            )
            return False

    fnm = lyr.dataProvider().fieldNameMap()  # slownik kolejnosci nazw w shp
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

    tab = sorted(tab, key=itemgetter(1), reverse=True)
    tab = sorted(tab, key=itemgetter(5))
    tab = sorted(tab, key=itemgetter(6))
    tab = sorted(tab, key=itemgetter(3))

    obr = ""
    gmi = ""
    oddz = ""
    iwydz = 0
    message_trig = 0
    przekroczone_grupy = []

    for it in tab:
        if oddz != it[3]:
            iwydz = 0
            oddz = it[3]
        if gmi != it[5]:
            iwydz = 0
            gmi = it[5]
        if obr != it[6]:
            iwydz = 0
            obr = it[6]

        if str(it[4]).upper() != 'LZ':
            if not _puste(it[4]) and not wymus_od_nowa:
                # jezeli wydz ma litere, nie zmieniamy
                pass
            else:
                if iwydz < 87:
                    wpis = lit[iwydz]
                    iwydz += 1
                else:
                    wpis = "xxx"
                    if message_trig == 0:
                        QgsMessageLog.logMessage(
                            'Lista wydzielen z błędnymi kodami:',
                            'Las-R',
                            Qgis.Warning
                        )

                    message_trig += 1
                    QgsMessageLog.logMessage(
                        ' '.join([str(gmi), str(obr), str(oddz), 'xxx']),
                        'Las-R',
                        Qgis.Warning
                    )
                    if (gmi, obr, oddz) not in przekroczone_grupy:
                        przekroczone_grupy.append((gmi, obr, oddz))
                sl[it[0]] = {fnm['WYDZ']: wpis}
        else:
            sl[it[0]] = {fnm['WYDZ']: 'Lz'}

    if message_trig > 0:
        sciezka_wydz = lyr.dataProvider().dataSourceUri().split("|")[0][:-4]
        oddz_shp = os.path.join(os.path.dirname(sciezka_wydz), 'ODDZ.shp')

        warstwa_przekr = QgsVectorLayer(
            'Polygon?crs=' + lyr.crs().authid(),
            'Oddziały - przekroczono literki', 'memory')
        pr_przekr = warstwa_przekr.dataProvider()
        pr_przekr.addAttributes([
            QgsField('COMMUNITY', QVariant.String),
            QgsField('MUNICIP', QVariant.String),
            QgsField('ODDZ', QVariant.String),
        ])
        warstwa_przekr.updateFields()

        if os.path.isfile(oddz_shp):
            warstwa_oddz_zrodlo = QgsVectorLayer(oddz_shp, 'oddz_zrodlo', 'ogr')
            nowe_featury = []
            for g, o, od in przekroczone_grupy:
                geometrie = [
                    f.geometry() for f in warstwa_oddz_zrodlo.getFeatures()
                    if str(f['MUNICIP']) == str(g)
                    and str(f['COMMUNITY']) == str(o)
                    and str(f['ODDZ']) == str(od)
                ]
                if not geometrie:
                    continue
                nf = QgsFeature(warstwa_przekr.fields())
                nf.setGeometry(
                    geometrie[0] if len(geometrie) == 1
                    else QgsGeometry.unaryUnion(geometrie))
                nf.setAttributes([g, o, od])
                nowe_featury.append(nf)
            pr_przekr.addFeatures(nowe_featury)
        else:
            QgsMessageLog.logMessage(
                'Nie znaleziono ODDZ.shp obok warstwy wydzieleń - '
                'pominięto zaznaczenie oddziałów na mapie',
                'Las-R', Qgis.Warning)

        warstwa_przekr.updateExtents()
        QgsProject.instance().addMapLayer(warstwa_przekr)

        lista_grup = '\n'.join(
            'Gmina: ' + str(g) + ', obręb: ' + str(o) + ', oddział: ' + str(od)
            for g, o, od in przekroczone_grupy[:15]
        )
        if len(przekroczone_grupy) > 15:
            lista_grup += '\n... oraz ' + \
                str(len(przekroczone_grupy) - 15) + ' innych (patrz log Las-R)'

        odp = QMessageBox.question(
            iface.mainWindow(),
            'Lista literek przekroczona',
            'Literkowanie przekroczy dostępną listę literek dla ' +
            str(message_trig) + ' wydzieleń w:\n\n' + lista_grup +
            '\n\nKontynuować literowanie?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if odp != QMessageBox.Yes:
            iface.messageBar().pushMessage(
                'ANULOWANO',
                'Literowanie przerwane przez użytkownika',
                Qgis.Warning,
                10)
            QgsMessageLog.logMessage(
                '------ KONIEC (anulowano) -------- \n',
                'Las-R',
                Qgis.Info
            )
            return False

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

        # kopia bezpieczeństwa PRZED dissolve - ten sam wzorzec co inne
        # operacje niszczące w tej wtyczce
        # (kopie_manipulacyjne.zrob_kopie_manipulacyjna)
        baza_do_kopii = _zgadnij_baze(sciezka + '.shp') or (sciezka + '.shp')
        folder_kopii = kopie_manipulacyjne.zrob_kopie_manipulacyjna(
            baza_do_kopii, [lyr], 'literkuj')
        if folder_kopii is None:
            iface.messageBar().pushMessage(
                'BŁĄD', 'Nie udało się utworzyć kopii bezpieczeństwa - '
                'przerwano scalanie fragmentów Lz (litery zostały już '
                'przypisane i zapisane)',
                Qgis.Critical, 10)
            QgsMessageLog.logMessage(
                '------ KONIEC (błąd kopii bezpieczeństwa) -------- \n',
                'Las-R', Qgis.Info)
            return True

        # zrob dissolva na warstwie wydz
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
            'Warstwa zaliterkowana bez problemów (połączono Lz)',
            Qgis.Success,
            10)

    else:
        iface.messageBar().pushMessage(
            'LICZBA WYDZIELEŃ',
            'Przekroczono liczbę wydzieleń obsługiwaną w '
            'jednym oddziale, (Patrz log Las-R)',
            Qgis.Warning,
            10)

    QgsMessageLog.logMessage(
        '------ KONIEC -------- \n',
        'Las-R',
        Qgis.Info
    )
