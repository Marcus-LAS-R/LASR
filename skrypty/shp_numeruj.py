from qgis.core import Qgis, QgsMessageLog
from operator import itemgetter


def Numeruj(iface):
    lyr = iface.activeLayer()

    QgsMessageLog.logMessage(
        '------ NUMERUJ ODDZIAŁY --------- ',
        'LasR',
        Qgis.Info
    )

    if not lyr.isValid():
        QgsMessageLog.logMessage(
            'Brak zaznaczonej poprawnej warstwy',
            'LasR',
            Qgis.Critical
        )
        QgsMessageLog.logMessage(
            '------ KONIEC -------- \n',
            'LasR',
            Qgis.Info
        )

    # zdefiniuj nizbedne pola w warstwie
    pola = [
        'COMMUNITY',
        'MUNICIP',
        'ODDZ',
    ]
    sl = {}  # slownik z zanumerowanymi oddz {feat.id: 'nr', ...}
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
            f['MUNICIP'],
            f['COMMUNITY'],
            f['ODDZ'],
        ])

    tab = sorted(tab, key=itemgetter(1), reverse=True)
    tab = sorted(tab, key=itemgetter(4))
    tab = sorted(tab, key=itemgetter(3))

    # ponumeruj oddz
    gmi = ""
    obr = ""
    oddz = 1
    puste = 0
    znumerowane = 0
    for t in tab:
        if 'NULL' in [str(t[3]), str(t[4])]:
            puste += 1

        if str(t[3]) != gmi or str(t[4]) != obr:
            gmi = t[3]
            obr = t[4]
            oddz = 1

        if t[5] not in ['NULL', '']:
            sl[t[0]] = {fnm['ODDZ']: str(oddz)}
            oddz += 1
        else:
            znumerowane += 1

    lyr.startEditing()
    for key, val in sl.items():
        lyr.dataProvider().changeAttributeValues({key: val})
    lyr.commitChanges()

    if puste == 0:
        iface.messageBar().pushMessage(
            'OK',
            'Warstwa zanumerowana bez problemów, zanumerowano: ' +
            str(len(sl))+' oddziałów',
            Qgis.Success,
            10)
    else:
        iface.messageBar().pushMessage(
            'PUSTE WIERSZE',
            'Zidentyfikowano puste wiersze, proszę sprawdzić poprawność '
            'warstwy! Zanumerowano: ' + str(len(sl))+' oddziałów',
            Qgis.Warning,
            10)

    if znumerowane > 0:
        QgsMessageLog.logMessage(
            'Pominięto zanumerowanych oddziałów: ' + str(znumerowane),
            'LasR',
            Qgis.Info
        )

    QgsMessageLog.logMessage(
        '------ KONIEC -------- \n',
        'LasR',
        Qgis.Info
    )
