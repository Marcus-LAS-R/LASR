import os
from qgis.core import QgsVectorLayer, Qgis, QgsField, QgsMessageLog, \
    QgsProject, QgsCoordinateReferenceSystem, QgsVectorFileWriter, \
    QgsGeometry, QgsFeature, QgsPointXY, QgsFeatureRequest, \
    QgsExpression
from PyQt5.QtCore import QVariant
import processing

from . import shp_wyszukaj_lz


def stworz_linie(kat):
    lin = QgsVectorLayer("LineString?crs=epsg:2180&field=ID:integer"
                         "&index=yes", 'lin', 'memory'
                         )
    lin_pola = [
        QgsField("KOD", QVariant.String, len=25),
        QgsField("SZER", QVariant.Double, "double", 10, 4),
    ]

    lin.startEditing()
    lin.dataProvider().addAttributes(lin_pola)
    lin.updateFields()
    lin.commitChanges()

    crs = QgsCoordinateReferenceSystem("epsg:2180")
    QgsVectorFileWriter.writeAsVectorFormat(
        lin,
        os.path.join(os.path.join(kat, "LINIE.shp")),
        "UTF-8",
        crs,
        "ESRI Shapefile")


def stworz_pnsw(kat):
    pnsw = QgsVectorLayer("Polygon?crs=epsg:2180&field=ID:integer"
                          "&index=yes", 'pnsw', 'memory'
                          )
    pnsw_pola = [
        QgsField("ADR_BDL", QVariant.String, len=25),
        QgsField("KOD_PNSW", QVariant.String, len=12),
        QgsField("NR_PNSW", QVariant.Int),
        QgsField("NR_EW", QVariant.String, len=25),
        QgsField("ADR_ADM", QVariant.String, len=25),
        QgsField("POW_GRAF", QVariant.Double, "double", 10, 4),
    ]

    pnsw.startEditing()
    pnsw.dataProvider().addAttributes(pnsw_pola)
    pnsw.updateFields()

    pnsw.commitChanges()
    crs = QgsCoordinateReferenceSystem("epsg:2180")
    QgsVectorFileWriter.writeAsVectorFormat(
        pnsw,
        os.path.join(os.path.join(kat, "PNSW.shp")),
        "UTF-8",
        crs,
        "ESRI Shapefile")


def stworz_maske(wydz):
    ls_sciezka = wydz.dataProvider().dataSourceUri().split("|")[0]
    kat = os.path.dirname(ls_sciezka)
    e = wydz.extent()
    xmin = e.xMinimum() - 4000
    xmax = e.xMaximum() + 4000
    ymin = e.yMinimum() - 4000
    ymax = e.yMaximum() + 4000

    mf = QgsFeature()
    geom = QgsGeometry().fromPolygonXY([[
        QgsPointXY(xmin, ymin),
        QgsPointXY(xmin, ymax),
        QgsPointXY(xmax, ymax),
        QgsPointXY(xmax, ymin),
        QgsPointXY(xmin, ymin),
    ]])
    mf.setGeometry(geom)

    maska_temp = QgsVectorLayer('Polygon?crs=epsg:2180&index=yes',
                                'maska_temp', 'memory'
                                )
    maska_temp.startEditing()
    maska_temp.addFeatures([mf, ])
    maska_temp.commitChanges()

    processing.run('native:difference', {
        'INPUT': maska_temp,
        'OVERLAY': wydz,
        'OUTPUT': os.path.join(kat, 'MASKA.shp'),
    })


def stworz_99(wydz):
    # stworz polaczona warstwe wydzielen z kodem GRP 99
    ls_sciezka = wydz.dataProvider().dataSourceUri().split("|")[0]
    kat = os.path.dirname(ls_sciezka)
    expr = QgsExpression('"GRP" = 99')
    req = QgsFeatureRequest(expr)
    feats = [x for x in wydz.getFeatures(req)]
    QgsMessageLog.logMessage(
        'Odnaleziono użytków ze współwłasnością: ' + str(len(feats)),
        'Las-R',
        Qgis.Info
    )

    w99 = QgsVectorLayer('MultiPolygon?crs=epsg:2180&index=yes',
                         '99temp', 'memory'
                         )

    if len(feats) == 0:
        crs = QgsCoordinateReferenceSystem("epsg:2180")
        QgsVectorFileWriter.writeAsVectorFormat(
            w99,
            os.path.join(os.path.join(kat, "99.shp")),
            "UTF-8",
            crs,
            "ESRI Shapefile")
        return

    w99.startEditing()
    w99.dataProvider().addFeatures(feats)
    w99.commitChanges()

    processing.run('native:dissolve', {
        'INPUT': w99,
        'FIELD': 'GRP',
        'OUTPUT': os.path.join(kat, '99.shp'),
    })


def stworz_pozaewid(wydz):
    # stworz polaczona warstwe wydzielen z kodem GRP 99
    ls_sciezka = wydz.dataProvider().dataSourceUri().split("|")[0]
    kat = os.path.dirname(ls_sciezka)
    expr = QgsExpression('"AU" != \'Ls\'')
    req = QgsFeatureRequest(expr)
    feats = [x for x in wydz.getFeatures(req)]
    QgsMessageLog.logMessage(
        'Odnaleziono użytków pozaewidencyjnych: ' + str(len(feats)),
        'Las-R',
        Qgis.Info
    )
    if len(feats) == 0:
        return

    pet = QgsVectorLayer('MultiPolygon?crs=epsg:2180&index=yes',
                         'pozaewid_temp', 'memory'
                         )
    pet.startEditing()
    pet.dataProvider().addFeatures(feats)
    pet.commitChanges()

    processing.run('native:dissolve', {
        'INPUT': pet,
        'FIELD': '',
        'OUTPUT': os.path.join(kat, 'pozaewidencyjne.shp'),
    })


def przygotuj_do_terenu(iface):  # noqa
    QgsMessageLog.logMessage(
        '------ PYRZGOTUJ LS DO TERENU --------- ',
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

    # ----------------------------
    stworz_maske(ls)
    stworz_99(ls)
    stworz_pozaewid(ls)

    # dodaj przetworzona warstwe oddz
    # if os.path.isfile(os.path.join(kat, 'OBR.shp')):
        # obr = qgsvectorlayer(
            # os.path.join(kat, 'obr.shp'), 'obr', 'ogr'
        # )

        # crs = QgsCoordinateReferenceSystem("epsg:2180")
        # QgsVectorFileWriter.writeAsVectorFormat(
            # obr,
            # os.path.join(os.path.join(kat, "ODDZ.shp")),
            # "UTF-8",
            # crs,
            # "ESRI Shapefile")

    maska = QgsVectorLayer(
        os.path.join(os.path.join(kat, "MASKA.shp")),
        'MASKA', 'ogr')
    QgsProject.instance().addMapLayer(maska)

    w99 = QgsVectorLayer(
        os.path.join(os.path.join(kat, "99.shp")),
        '99', 'ogr')
    if w99.isValid():
        QgsProject.instance().addMapLayer(w99)

    pozaewidencyjne = QgsVectorLayer(
        os.path.join(os.path.join(kat, "pozaewidencyjne.shp")),
        'pozaewidencyjne', 'ogr')
    if pozaewidencyjne.isValid():
        QgsProject.instance().addMapLayer(pozaewidencyjne)

    lz = shp_wyszukaj_lz.WyszukajLz(iface)
    if lz.pobierz_dane():
        lz.zabuduj_strukt()
        lz.wybierz_potencjalne_lz()
        lz.stworz_warstwe_lz()

    QgsMessageLog.logMessage(
        '------ KONIEC --------- ',
        'Las-R',
        Qgis.Info
    )

def przygotuj_wydz_do_ciecia(iface):  # noqa
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
    # UWAGA: jako INPUT podajemy obiekt warstwy (ls), nie samą ścieżkę
    # (ls_sciezka) - processing otwiera ścieżkę od nowa z domyślnym
    # kodowaniem, gubiąc ręczne ustawienie kodowania (np. UTF-8) zrobione
    # przez użytkownika we właściwościach warstwy LS
    wydz_sc = os.path.join(kat, 'WYDZ.shp')
    processing.run("native:multiparttosingleparts", {
        'OUTPUT': wydz_sc,
        'INPUT': ls,
    })

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
            if w in sl_woj:
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

    # dodaj warstwe PNSW do katalogu
    stworz_pnsw(kat)
    # dodaj warstwe lini
    stworz_linie(kat)
    stworz_pozaewid(ls)

    # usuniete  przywrocone na zyczenie wiceprezesa (niezdecydowany jakis?)
    # dodaj przetworzona warstwe oddz
    if os.path.isfile(os.path.join(kat, 'OBR.shp')):
        obr = QgsVectorLayer(
            os.path.join(kat, 'OBR.shp'), 'OBR', 'ogr'
        )

        # nazwy pola z kodem TERYT obrebu roznia sie miedzy zrodlami danych,
        # ale maja te sama strukture - dopasowanie bez wzgledu na wielkosc
        # liter, bo stare shp/dbf czesto wymuszaja same wielkie litery
        nazwy_pol = {
            x.name().lower(): x.name()
            for x in obr.dataProvider().fields().toList()
        }
        adr_adm = ''
        for kandydat in ('idobrebu', 'jpt_kod_je', 'g5nro'):
            if kandydat in nazwy_pol:
                adr_adm = nazwy_pol[kandydat]
                break

        oddz_fields = [
            QgsField("MUNICIP", QVariant.String, len=3),
            QgsField("COMMUNITY", QVariant.String, len=4),
            QgsField("ODDZ", QVariant.String, len=6),
        ]

        crs = QgsCoordinateReferenceSystem("epsg:2180")
        QgsVectorFileWriter.writeAsVectorFormat(
            obr,
            os.path.join(os.path.join(kat, "ODDZ.shp")),
            "UTF-8",
            crs,
            "ESRI Shapefile")

        oddz = QgsVectorLayer(
            os.path.join(os.path.join(kat, "ODDZ.shp")), 'ODDZ', 'ogr')

        oddz.startEditing()
        oddz.dataProvider().addAttributes(oddz_fields)
        oddz.commitChanges()
        fnm = oddz.dataProvider().fieldNameMap()

        # jezeil mamy kolumne z adr adm dopisz doWarstwy kody z municip i
        # community, oraz wpisz wszedzie oddz 1
        if adr_adm != '':
            for feat in oddz.getFeatures():
                try:
                    municip = feat[adr_adm][4:8].replace('_', '')
                except:  # nopep8
                    municip = ''
                try:
                    comm = feat[adr_adm][-4:]
                except:  # nopep8
                    comm = ''
                oddz.dataProvider().changeAttributeValues(
                    {feat.id(): {
                        fnm['MUNICIP']: municip,
                        fnm['COMMUNITY']: comm,
                    }})

        _skasuj = [fnm[x.name()] for x in oddz.fields()
                   if x.name() not in [y.name() for y in oddz_fields]]
        oddz.startEditing()
        oddz.dataProvider().deleteAttributes(_skasuj)
        oddz.commitChanges()

        QgsProject.instance().addMapLayer(oddz)

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

    # dodaj warstwe pnsw i lini to TOC
    pnsw = QgsVectorLayer(
        os.path.join(os.path.join(kat, "PNSW.shp")),
        'PNSW', 'ogr')
    QgsProject.instance().addMapLayer(pnsw)

    linie = QgsVectorLayer(
        os.path.join(os.path.join(kat, "LINIE.shp")),
        'LINIE', 'ogr')
    QgsProject.instance().addMapLayer(linie)

    pozaewidencyjne = QgsVectorLayer(
        os.path.join(os.path.join(kat, "pozaewidencyjne.shp")),
        'pozaewidencyjne', 'ogr')
    if pozaewidencyjne.isValid():
        QgsProject.instance().addMapLayer(pozaewidencyjne)

    QgsMessageLog.logMessage(
        '------ KONIEC --------- ',
        'Las-R',
        Qgis.Info
    )
