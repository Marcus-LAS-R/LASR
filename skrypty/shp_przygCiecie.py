import os
from qgis.core import QgsVectorLayer, Qgis, QgsField, QgsMessageLog, QgsProject
from PyQt5.QtCore import QVariant
import processing


def przygotujDoCiecia(iface):  # noqa
    QgsMessageLog.logMessage(
        '------ PYRZGOTUJ LS DO CIECIA --------- ',
        'Las-R',
        Qgis.Info
    )

    kolumny = [
        "COUNTY",
        "DISTRICT",
        "MUNICIP",
        "COMMUNITY",
        "PARCELNR",
        "PARCELID",
        "GRP",
        "PARCEL_AR",
        "PARCEL_POW",
        ]

    sl_woj = {
        "02": "D",
        "04": "C",
        "06": "L",
        "08": "F",
        "10": "E",
        "12": "K",
        "14": "W",
        "16": "O",
        "18": "R",
        "20": "B",
        "22": "G",
        "24": "S",
        "26": "T",
        "28": "N",
        "30": "P",
        "32": "Z",
        }

    ls = iface.activeLayer()
    ls_sciezka = ls.dataProvider().dataSourceUri().split("|")[0]
    kat = os.path.dirname(ls_sciezka)

    # ------ WARUNKI POCZATKOWE ------
    pls = [x.name() for x in ls.fields()]
    brakikol = [x for x in kolumny if x not in pls]
    if len(brakikol) > 0:
        QgsMessageLog.logMessage(
            'W warstwie brakuje kolumn: ' + ', '.join(brakikol),
            'Las-R',
            Qgis.Critical
        )
        iface.messageBar().pushMessage(
            'BŁĄD',
            'W warstwie brakuje niezbędnych kolumn: ' + ', '.join(brakikol),
            Qgis.Critical,
            10
        )
        return

        return

    # ----------------------------

    # sprawdz czy nie ma poprzedniej wersji pliku
    rozsz = ['shp', 'shx', 'dbf', 'prj', 'sbx', 'shx', ]
    try:
        for r in rozsz:
            if os.path.isfile(os.path.join(kat, 'WYDZ.'+r)):
                os.remove(os.path.join(kat, 'WYDZ.'+r))
    except:  # nopep8
        iface.messageBar().pushMessage(
            'BŁĄD',
            'Nie udało się usunąć poprzedniej wersji plików WYDZ, '
            'proszę ponownie uruchomić QGIS-a',
            Qgis.Critical,
            10
        )
        return

    # rozbij do singlepartow
    wydz_sc = os.path.join(kat, 'WYDZ.shp')
    processing.run("native:multiparttosingleparts", {
        'OUTPUT': wydz_sc,
        'INPUT': ls_sciezka,
    })

    # Rozbij uzytki na single parts
    wydz = QgsVectorLayer(wydz_sc, 'WYDZ', 'ogr')
    wydz.startEditing()

    kol = [
        "COUNTY",
        "DISTRICT",
        "MUNICIP",
        "COMMUNITY",
        "GRP",
    ]

    pola = [
        QgsField("COUNTY_L", QVariant.String, len=1),
        QgsField("ODDZ", QVariant.String, len=6),
        QgsField("WYDZ", QVariant.String, len=4),
        QgsField("ADR_LES", QVariant.String, len=25),
        QgsField("POW_GRAF", QVariant.Double, "double", 10, 4),
    ]

    # skasuj wszystkie niepotrzebne kolumny
    fnm = wydz.dataProvider().fieldNameMap()
    ind_skasuj = [fnm[x.name()] for x in wydz.fields() if x.name() not in kol]
    wydz.dataProvider().deleteAttributes(ind_skasuj)
    wydz.updateFields()

    # dodaj niezbedne pola
    wydz.dataProvider().addAttributes(pola)
    wydz.updateFields()

    woj = '-1'  # zmienna z literka wojewodztwa
    fnm = wydz.dataProvider().fieldNameMap()
    bledy_zerowe = False
    for f in wydz.getFeatures():
        if woj == '-1':
            w = str(f['COUNTY'])
            if w != 'NULL':
                woj = sl_woj[w]
            else:
                woj = '-1'

        wydz.dataProvider().changeAttributeValues({
            f.id(): {
                fnm['COUNTY_L']: woj,
                fnm['POW_GRAF']: f.geometry().area()/10000,
            }
        })

        if round(f.geometry().area() / 10000, 4) == 0.0000:
            bledy_zerowe = True

    wydz.commitChanges()
    if bledy_zerowe:
        iface.messageBar().pushMessage(
            'OSTRZEŻENIE',
            'Warstwa została utworzona ale znajdują się w niej poligony '
            'z zerową powierzchnią',
            Qgis.Warning,
            10
        )

    else:
        iface.messageBar().pushMessage(
            'OK',
            'Warstwa utworzona i dodana do TOC',
            Qgis.Success,
            10
        )

    QgsProject.instance().addMapLayer(wydz)

    QgsMessageLog.logMessage(
        '------ KONIEC --------- ',
        'Las-R',
        Qgis.Info
    )
