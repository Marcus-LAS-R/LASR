from qgis.core import Qgis, QgsVectorLayer, QgsFeatureRequest, QgsMessageLog
import os
import processing
from PyQt5.QtWidgets import QFileDialog, QMessageBox

_WARSTWY = [
    'adr_upul',
    'granice_wydzielen',
    'kasowniki',
    'notatki',
    'obiekty_liniowe',
    'pnsw',
]


def _znajdz_duplikaty(layer):
    """Zwraca listę fid-ów do usunięcia — obiekty o identycznej geometrii
    (WKT) i identycznych atrybutach jak obiekt już wcześniej napotkany.
    Zostawia jeden egzemplarz każdego unikalnego zestawu."""
    widziane = set()
    do_usuniecia = []
    for feat in layer.getFeatures():
        key = (
            feat.geometry().asWkt(),
            tuple(str(a) for a in feat.attributes()),
        )
        if key in widziane:
            do_usuniecia.append(feat.id())
        else:
            widziane.add(key)
    return do_usuniecia


def _usun_duplikaty(layer, fids):
    layer.startEditing()
    layer.deleteFeatures(fids)
    return layer.commitChanges()


def polacz_warstwy(iface):
    QgsMessageLog.logMessage(
        '--- POŁĄCZ POMIARY OD TAKSATORÓW ---', 'Las-R', Qgis.Info
    )

    projects_folder = QFileDialog.getExistingDirectory(
        iface.mainWindow(), "Wybierz katalog: ")

    if not projects_folder:
        return

    # folder na polaczone warstwy - jeden poziom wyzej niz wskazany katalog
    folder = os.path.abspath(
        os.path.join(projects_folder, '..', 'pomiary'))

    if os.path.isdir(folder) and os.listdir(folder):
        odp = QMessageBox.question(
            iface.mainWindow(),
            'Nadpisać?',
            'Folder "' + folder + '" już istnieje i zawiera dane.\n\n'
            'Czy nadpisać jego zawartość?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if odp != QMessageBox.Yes:
            QgsMessageLog.logMessage(
                'Przerwano — użytkownik nie zgodził się na nadpisanie '
                'folderu ' + folder,
                'Las-R', Qgis.Info
            )
            return

    if not os.path.isdir(folder):
        os.mkdir(folder)

    polaczone = []
    pominiete = []
    usuniete_dubli = {}  # {nazwa_warstwy: ile_usunieto}

    # znajdz wszystkie projekty w podanym katalogu.
    for pl in _WARSTWY:
        lacz = []
        for root, dirs, files in os.walk(projects_folder):
            for ff in files:
                if ff == pl + '.shp':
                    lacz.append(os.path.join(root, ff))

        if len(lacz) == 0:
            QgsMessageLog.logMessage(
                'Brak plików "' + pl + '.shp" we wskazanym katalogu — '
                'pomijam', 'Las-R', Qgis.Warning
            )
            pominiete.append(pl)
            continue

        QgsMessageLog.logMessage(
            'Łączę ' + str(len(lacz)) + ' plik(ów) "' + pl + '.shp"',
            'Las-R', Qgis.Info
        )

        try:
            processing.run(
                'native:mergevectorlayers',
                {'LAYERS': lacz,
                 'CRS': 'EPSG:2180',
                 'OUTPUT': os.path.join(folder, pl + '.shp')
                 }
            )
            polaczone.append(pl)
        except Exception as e:  # nopep8
            QgsMessageLog.logMessage(
                'BŁĄD łączenia "' + pl + '.shp": ' + str(e),
                'Las-R', Qgis.Critical
            )
            pominiete.append(pl)
            continue

        # kontrola duplikatów (identyczna geometria + atrybuty) w warstwie,
        # ktora wlasnie powstala ze scalenia plikow od kilku taksatorow
        warstwa = QgsVectorLayer(
            os.path.join(folder, pl + '.shp'), pl, 'ogr')
        dubl_fids = _znajdz_duplikaty(warstwa)

        if len(dubl_fids) == 0:
            continue

        QgsMessageLog.logMessage(
            'Znaleziono ' + str(len(dubl_fids)) + ' duplikatów w "' +
            pl + '.shp"', 'Las-R', Qgis.Warning
        )

        odp = QMessageBox.question(
            iface.mainWindow(),
            'Duplikaty',
            'W warstwie "' + pl + '" znaleziono ' + str(len(dubl_fids)) +
            ' zdublowanych obiektów (identyczna geometria i atrybuty).\n\n'
            'Usunąć duplikaty?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if odp == QMessageBox.Yes:
            if _usun_duplikaty(warstwa, dubl_fids):
                usuniete_dubli[pl] = len(dubl_fids)
                QgsMessageLog.logMessage(
                    'Usunięto ' + str(len(dubl_fids)) + ' duplikatów z "' +
                    pl + '.shp"', 'Las-R', Qgis.Info
                )
            else:
                QgsMessageLog.logMessage(
                    'Nie udało się usunąć duplikatów z "' + pl + '.shp"',
                    'Las-R', Qgis.Critical
                )
        else:
            QgsMessageLog.logMessage(
                'Duplikaty w "' + pl + '.shp" pozostawione na żądanie '
                'użytkownika', 'Las-R', Qgis.Info
            )

    flaga = 'OK'
    wiad = 'Połączono warstwy'
    kol = Qgis.Success

    if 'adr_upul' in polaczone:
        karty = QgsVectorLayer(
            os.path.join(folder, 'adr_upul.shp'), 'karty', 'ogr')
        request = QgsFeatureRequest().setFlags(
            QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
                ['ODDZ'], karty.fields()
            )

        for feat in karty.getFeatures(request):
            if str(feat['ODDZ']).isdigit():
                flaga = 'UWAGA'
                wiad = 'Połączono warstwy, znaleziono cyferki w polu ODDZ'
                kol = Qgis.Warning

    if usuniete_dubli:
        wiad += ' (usunięto duplikaty: ' + ', '.join(
            k + '=' + str(v) for k, v in usuniete_dubli.items()
        ) + ')'

    if pominiete:
        wiad += ' (pominięto: ' + ', '.join(pominiete) + ')'
        if flaga == 'OK':
            flaga = 'UWAGA'
            kol = Qgis.Warning

    QgsMessageLog.logMessage(
        '--- KONIEC --- ' + wiad, 'Las-R', Qgis.Info
    )

    iface.messageBar().pushMessage(flaga, wiad, kol)
