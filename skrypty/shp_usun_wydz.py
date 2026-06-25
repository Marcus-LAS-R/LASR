from qgis.core import Qgis, QgsMessageLog, QgsProject
from PyQt5.QtWidgets import QMessageBox

from .baza_wrapper import Baza, znajdz_baze_do_wydz
from . import kopie_manipulacyjne


def _znajdz_pnsw():
    """ Warstwa PNSW musi byc wczytana w TOC (tak jak przy "Dopisz/
    uzupelnij PNSW") - powiazanie z WYDZ dziala tylko po atrybucie
    ADR_BDL, ktory "Dopisz/uzupelnij PNSW" wpisuje jako kopie
    WYDZ.ADR_LES. Bez tej warstwy/kolumny PNSW trzeba wyczyscic recznie. """
    lyrs = QgsProject.instance().mapLayers().values()
    pnsw = [x for x in lyrs if x.name()[:4].upper() == 'PNSW']
    return pnsw[0] if len(pnsw) == 1 else None


def usun_wydz_z_warstwy(iface):
    """ Odwrotnosc baza_usun_wydz.usun_wydz - tam baza byla "do
    wyczyszczenia" wzgledem warstwy, tutaj warstwa WYDZ jest "do
    wyczyszczenia" wzgledem bazy. Usuwa z warstwy WYDZ (i powiazanych po
    ADR_BDL=ADR_LES poligonow PNSW, jesli ta warstwa jest wczytana) te
    wydzielenia, ktorych ADR_LES nie istnieje w bazie. """
    lyr = iface.activeLayer()

    if lyr is None or not lyr.isValid():
        iface.messageBar().pushMessage(
            "BŁĄD", "Zaznacz poprawną warstwę WYDZ", Qgis.Critical, 10
        )
        return False

    if "ADR_LES" not in [x.name() for x in lyr.fields()]:
        iface.messageBar().pushMessage(
            "BŁĄD", "W zaznaczonej warstwie brakuje kolumny ADR_LES",
            Qgis.Critical, 10
        )
        return False

    baza_sc = znajdz_baze_do_wydz(iface, lyr)
    if baza_sc is False:
        iface.messageBar().pushMessage(
            "BRAK BAZY", "Bez bazy ani rusz!", Qgis.Critical, 10
        )
        return False

    baza = Baza(baza_sc)
    if not baza.polacz():
        iface.messageBar().pushMessage(
            "BAZA", "Nie mogłem podłączyć się do bazy", Qgis.Critical, 10
        )
        return False

    f_arod = baza.pobierz_wydzielenia()
    if f_arod is False:
        iface.messageBar().pushMessage(
            "BAZA", "Nie znalazłem żadnych wydzieleń w bazie - sprawdź, "
            "czy to właściwa baza (nic nie usunięto)", Qgis.Critical, 10
        )
        return False

    znane_w_bazie = set(f_arod.keys())

    wszystkie = list(lyr.getFeatures())
    do_usun_wydz = [f for f in wszystkie if f["ADR_LES"] not in znane_w_bazie]
    do_usun_adr = {f["ADR_LES"] for f in do_usun_wydz}

    QgsMessageLog.logMessage(
        'usun_wydz_z_warstwy: w warstwie ' + str(len(wszystkie)) +
        ' wydzieleń, brakuje w bazie ' + str(len(do_usun_wydz)),
        'Las-R', Qgis.Info
    )

    if len(do_usun_wydz) == 0:
        iface.messageBar().pushMessage(
            "BRAK", "Nie ma wydzieleń do usunięcia z warstwy", Qgis.Warning, 10
        )
        return True

    pnsw = _znajdz_pnsw()
    pnsw_ma_adr_bdl = pnsw is not None and \
        "ADR_BDL" in [x.name() for x in pnsw.fields()]
    do_usun_pnsw = []
    if pnsw_ma_adr_bdl:
        do_usun_pnsw = [p for p in pnsw.getFeatures()
                        if p["ADR_BDL"] in do_usun_adr]

    tresc = (
        'W warstwie WYDZ znaleziono ' + str(len(do_usun_wydz)) +
        ' wydzieleń, których nie ma w bazie.\n\n'
        'Te wydzielenia zostaną TRWALE USUNIĘTE z warstwy WYDZ'
    )
    if pnsw is None:
        tresc += (
            ' (warstwa PNSW nie jest wczytana w projekcie - nie da się '
            'jej teraz wyczyścić, trzeba to zrobić ręcznie/później!)'
        )
    elif not pnsw_ma_adr_bdl:
        tresc += (
            ' (warstwa PNSW nie ma kolumny ADR_BDL - nie da się jej '
            'teraz wyczyścić, trzeba to zrobić ręcznie/później!)'
        )
    else:
        tresc += ', wraz z ' + str(len(do_usun_pnsw)) + \
            ' powiązanymi z nimi poligonami PNSW'
    tresc += '.\n\n'

    if len(do_usun_wydz) == len(wszystkie):
        tresc += (
            'UWAGA: to jest CAŁA zawartość warstwy WYDZ (100%) - sprawdź, '
            'czy wskazano właściwą bazę!\n\n'
        )

    tresc += (
        'Przed usunięciem zostanie zrobiona kopia bazy i warstw(y) w '
        'folderze Kopie_manipulacyjne (w katalogu bazy), ale tej operacji '
        'nie da się wycofać inaczej, niż przywracając tę kopię.\n\n'
        'Czy na pewno usunąć?'
    )

    odp = QMessageBox.question(
        iface.mainWindow(),
        'Skasuj wydzielenia w warstwie',
        tresc,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    if odp != QMessageBox.Yes:
        iface.messageBar().pushMessage(
            "PRZERWANO", "Nie usunięto żadnych obiektów", Qgis.Info, 10
        )
        return False

    folder_kopii = kopie_manipulacyjne.zrob_kopie_manipulacyjna(
        baza_sc, [lyr, pnsw if pnsw_ma_adr_bdl else None],
        'usun_wydz_z_warstwy'
    )
    if folder_kopii is None:
        iface.messageBar().pushMessage(
            "BŁĄD", "Nie udało się utworzyć kopii bezpieczeństwa - "
            "przerwano, nic nie usunięto", Qgis.Critical, 10
        )
        return False

    lyr.startEditing()
    lyr.dataProvider().deleteFeatures([f.id() for f in do_usun_wydz])
    lyr.commitChanges()

    ile_pnsw = 0
    if pnsw_ma_adr_bdl and len(do_usun_pnsw) > 0:
        pnsw.startEditing()
        pnsw.dataProvider().deleteFeatures([p.id() for p in do_usun_pnsw])
        pnsw.commitChanges()
        ile_pnsw = len(do_usun_pnsw)

    iface.mapCanvas().refreshAllLayers()

    iface.messageBar().pushMessage(
        "OK",
        "Usunięto " + str(len(do_usun_wydz)) + " wydzieleń z warstwy" +
        (' i ' + str(ile_pnsw) + ' poligonów PNSW' if ile_pnsw else ''),
        Qgis.Success, 10
    )
    return True
