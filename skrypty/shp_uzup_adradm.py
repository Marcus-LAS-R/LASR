from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QInputDialog
from qgis.utils import iface
from qgis.core import QgsField, QgsFeatureRequest

from .funkcje import rozbij_adres_gmina_obreb

_KANDYDACI_POLA_ZRODLOWEGO = ['G5IDD', 'IDENTYFIKA', 'G5NRO']


def DodajIUzupelnijAdm():
    lyr = iface.activeLayer()
    try:
        if not lyr.isValid():
            iface.messageBar().pushWarning('BŁĄD', "Niepoprawna warstwa...")
            return
    except Exception:
        iface.messageBar().pushWarning('BŁĄD', "Niepoprawna warstwa...")
        return

    flds = [x.name().upper() for x in lyr.dataProvider().fields().toList()]

    nowe_pola = [
        QgsField(nazwa, QVariant.String, len=dlugosc)
        for nazwa, dlugosc in (('MUNICIP', 3), ('COMMUNITY', 4))
        if nazwa not in flds
    ]
    if nowe_pola:
        lyr.startEditing()
        lyr.dataProvider().addAttributes(nowe_pola)
        lyr.updateFields()
        lyr.commitChanges()
        flds = [x.name().upper() for x in lyr.dataProvider().fields().toList()]

    pole = next((k for k in _KANDYDACI_POLA_ZRODLOWEGO if k in flds), None)
    if pole is None:
        kols = sorted(lyr.dataProvider().fieldNameMap().keys())
        kol, ok = QInputDialog.getItem(
            None,
            'Wybierz kolumne z adresem administracyjnym',
            'Nazwa kloumny',
            kols, 0, False
        )
        if not ok:
            return
        pole = kol

    sl = {}
    req = QgsFeatureRequest().setFlags(
        QgsFeatureRequest.NoGeometry).setSubsetOfAttributes(
            [pole, 'COMMUNITY', 'MUNICIP'], lyr.fields())

    fnm = lyr.dataProvider().fieldNameMap()
    for feat in lyr.getFeatures(req):
        wynik = rozbij_adres_gmina_obreb(feat[pole])
        if wynik is None:
            continue
        gmina, obreb, _ = wynik
        sl[feat.id()] = {
            fnm['COMMUNITY']: obreb,
            fnm['MUNICIP']: gmina.replace('_', '')
        }

    lyr.startEditing()
    lyr.dataProvider().changeAttributeValues(sl)
    lyr.commitChanges()

    iface.messageBar().pushSuccess(
        'Sukces', f'Uzupełniono {len(sl)} rekordów.'
    )
