from qgis.core import Qgis, QgsProject, QgsMessageLog, QgsSpatialIndex, \
    QgsVectorLayer, QgsField, QgsFeature
from collections import Counter
from PyQt5.QtCore import QVariant


def SprWydzOddz(iface):  # noqa

    QgsMessageLog.logMessage(
        '------ SPRAWDŹ WYDZIELENIA W ODDZIAŁACH --------- ',
        'LasR',
        Qgis.Info
    )

    spis_warstw = [x.name() for x in
                   QgsProject.instance().mapLayers().values()]

    # SPRAWDZ WARUNKI POCZATKOWE ----------------------
    # Sprawdz czy w TOC jest tylko jedna warstwa z nazwa ODDZ
    go = False
    policz_warstwy = Counter(spis_warstw)
    if 'ODDZ' in policz_warstwy:
        if policz_warstwy['ODDZ'] == 1:
            go = True
            oddz = [x for x in QgsProject.instance().mapLayers().values()
                    if x.name() == 'ODDZ'][0]

    if not go:
        QgsMessageLog.logMessage(
            'W TOC może znajdować się tylko i aż jedna warstwa ODDZ',
            'LasR',
            Qgis.Critical
        )
        iface.messageBar().pushMessage(
            'ODDZ',
            'W TOC może znajdować się tylko i aż jedna warstwa ODDZ',
            Qgis.Critical,
            10)
        return

    if iface.activeLayer().name() == 'ODDZ':
        QgsMessageLog.logMessage(
            'Aktywną warstwą powinny być wydzielenia',
            'LasR',
            Qgis.Critical
        )
        iface.messageBar().pushMessage(
            'Aktywna warstwa',
            'jako aktywna warstwa powinny być zaznaczone wydzielenia',
            Qgis.Critical,
            10)
        return

    wydz = iface.activeLayer()
    pola_w = [x.name() for x in wydz.fields()]
    pola_o = [x.name() for x in oddz.fields()]
    brak_pola = [[], []]

    brakw = [x for x in ['ODDZ', 'MUNICIP', 'COMMUNITY']
             if x not in pola_w]
    if len(brakw) > 0:
        brak_pola[0].append(wydz.name())
        brak_pola[1].append(brakw)

    brako = [x for x in ['ODDZ', 'MUNICIP', 'COMMUNITY']
             if x not in pola_o]
    if len(brako) > 0:
        brak_pola[0].append(oddz.name())
        brak_pola[1].append(brako)

    if len(brak_pola[0]) > 0:
        for i in range(len(brak_pola[0])):
            QgsMessageLog.logMessage(
                'W warstwie ' + brak_pola[0][i] +
                ' brakuje kolumn: ' + ', '.join(brak_pola[1][i]),
                'LasR',
                Qgis.Critical
            )

        iface.messageBar().pushMessage(
            'BRAK KOLUMN',
            '(Sprawdź log LasR)',
            Qgis.Critical,
            10)
        return

    # ------ KONIEC WARUNKOW POCZATKOWYCH ---------------

    # zbuduj indeks przestrzenny dla wydzielen
    si = QgsSpatialIndex()
    sl_wydz = {}

    for f in wydz.getFeatures():
        si.insertFeature(f)
        sl_wydz[f.id()] = f

    # sprawdz przeciecia wydzielen z poszczegolnymi oddzialami
    f_przec = []
    for foddz in oddz.getFeatures():
        ids = si.intersects(foddz.geometry().boundingBox())

        for idk in ids:
            if sl_wydz[idk].geometry().intersects(foddz.geometry()):
                inter = sl_wydz[idk].geometry().intersection(foddz.geometry())
                if inter.area() > 1:
                    if abs(inter.area()-sl_wydz[idk].geometry().area()) > 1:
                        if idk not in [x.id() for x in f_przec]:
                            f_przec.append(sl_wydz[idk])

    if len(f_przec) > 0:
        iface.messageBar().pushMessage(
            'ZNALEZIONO PRZECIĘCIA',
            'do TOC dodano warstwę z wydzieleniami przykrywającymi '
            'granice oddziałów',
            Qgis.Warning,
            10
        )

        polyLyr = QgsVectorLayer(
                "MultiPolygon?crs=epsg:2180",
                "WYDZ_przecinające_ODDZ",
                "memory")

        polylyr_dp = polyLyr.dataProvider()
        polyLyr.startEditing()
        polylyr_dp.addAttributes([
            QgsField("ID", QVariant.Int),
        ])
        polyLyr.updateFields()

        fs = []
        for i, it in enumerate(f_przec):
            feat = QgsFeature()
            feat.setGeometry(it.geometry())
            feat.setFields(polyLyr.fields())
            feat['ID'] = i
            fs.append(feat)

        polylyr_dp.addFeatures(fs)
        polyLyr.commitChanges()
        QgsProject.instance().addMapLayer(polyLyr)

    else:
        iface.messageBar().pushMessage(
            'OK',
            'Wydzielenia leżą w oddziałach',
            Qgis.Success,
            10
        )

    QgsMessageLog.logMessage(
        '------ KONIEC --------- \n',
        'LasR',
        Qgis.Info
    )
