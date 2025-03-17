from qgis.core import Qgis, QgsVectorLayer, QgsFeatureRequest
import os
import processing
from PyQt5.QtWidgets import QFileDialog


def polacz_warstwy(iface):
    projects_folder = QFileDialog.getExistingDirectory(
        iface.mainWindow(), "Wybierz katalog: ")

    # sprawdz czy istnieje, a jak nie to stworz folder na polaczone
    folder = os.path.abspath(
        os.path.join(projects_folder, '..', 'teren_polaczone'))
    if not os.path.exists(folder):
        os.mkdir(folder)

    pliki = [
        'adr_upul',
        'granice_wydzielen',
        'kasowniki',
        'notatki',
        'obiekty_liniowe',
        'pnsw',
    ]

    # znajdz wszystkie projekty w podanym katalogu.
    for pl in pliki:
        lacz = []
        for root, dirs, files in os.walk(projects_folder):
            for ff in files:
                if ff == pl + '.shp':
                    lacz.append(os.path.join(root, ff))
        processing.run(
            'native:mergevectorlayers',
            {'LAYERS': lacz,
             'CRS': 'EPSG:2180',
             'OUTPUT': os.path.join(folder, pl + '.shp')
             }
        )

    karty = QgsVectorLayer(os.path.join(folder, 'adr_upul.shp'),
                           'karty', 'ogr')
    request = QgsFeatureRequest().setFlags(
        QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
            ['ODDZ'], karty.fields()
        )

    flaga = 'OK'
    wiad = 'Połączono warstwy'
    kol = Qgis.Success
    for feat in karty.getFeatures(request):
        if str(feat['ODDZ']).isdigit():
            flaga = 'UWAGA'
            wiad = 'Połączono warstwy, znaleziono cyferki w polu ODDZ'
            kol = Qgis.Warning

    iface.messageBar().pushMessage(flaga, wiad, kol)
