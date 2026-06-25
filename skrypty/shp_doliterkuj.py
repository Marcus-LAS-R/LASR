import os
import datetime
import processing
from operator import itemgetter

from qgis.core import Qgis, QgsMessageLog, QgsVectorFileWriter, \
    QgsCoordinateReferenceSystem, QgsVectorLayer

from .shp_literkuj import LITERY


def _ma_juz_litere(wartosc):
    """ Czy pole WYDZ jest juz wypelnione (nie jest puste/NULL)? Wzorowane
    1:1 na warunku z shp_literkuj.Literkuj, dla zgodnosci zachowania na
    tych samych danych (shapefile/DBF). """
    return str(wartosc) not in ["", " ", 'NULL', None]


def _nastepna_wolna_litera(uzyte):
    """ Pierwsza litera z LITERY jeszcze nie uzyta w danej grupie
    (MUNICIP, COMMUNITY, ODDZ) - albo None, jesli wszystkie 87 zajete. """
    for l in LITERY:
        if l not in uzyte:
            return l
    return None


def Doliterkuj(iface, lyr=False):  # noqa
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

    fnm = lyr.dataProvider().fieldNameMap()
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
        wolna = _nastepna_wolna_litera(uzyte)
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
