import os
import datetime
import processing
from qgis.core import Qgis, QgsMessageLog, QgsVectorFileWriter, \
    QgsCoordinateReferenceSystem, QgsVectorLayer
from operator import itemgetter


def Literkuj(iface, lyr=False):  # noqa
    if lyr is False:
        lyr = iface.activeLayer()

    lit = [
        "a", "b", "c", "d", "f", "g", "h", "i", "j", "k", "l", "m", "n", "o",
        "p", "r", "s", "t", "w", "x", "y", "z", "ax", "bx", "cx", "dx", "fx",
        "gx", "hx", "ix", "jx", "kx", "lx", "mx", "nx", "ox", "px", "rx", "sx",
        "tx", "wx", "xx", "yx", "zx", "ay", "by", "cy", "dy", "fy", "gy", "hy",
        "iy", "jy", "ky", "ly", "my", "ny", "oy", "py", "ry", "sy", "ty", "wy",
        "xy", "yy", "zy", "az", "bz", "cz", "dz", "fz", "gz", "hz", "iz", "jz",
        "kz", "mz", "nz", "oz", "pz", "rz", "sz", "tz", "wz", "xz", "yz", "zz"
    ]

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
            if str(it[4]) not in ["", " ", 'NULL', None]:
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
                sl[it[0]] = {fnm['WYDZ']: wpis}
        else:
            sl[it[0]] = {fnm['WYDZ']: 'Lz'}

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

        # stworz kopie warstwy wydz w tempie
        QgsVectorFileWriter.writeAsVectorFormat(
            lyr,
            os.path.join(tempkat, 'wydz_backup_'+czas+'.shp'),
            "UTF-8", crs, "ESRI Shapefile")

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
