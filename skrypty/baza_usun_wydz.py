from qgis.core import Qgis, QgsMessageLog
from PyQt5.QtWidgets import QMessageBox

from .baza_wrapper import Baza, znajdz_baze_do_wydz
from . import kopie_manipulacyjne


def usun_wydz(iface):
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
            "BAZA", "Nie znalazłem żadnych wydzieleń w bazie", Qgis.Warning, 10
        )
        return False

    spis_wydz_lyr = [f["ADR_LES"] for f in lyr.getFeatures()]
    brak_baza = [vv for fi, vv in f_arod.items() if fi not in spis_wydz_lyr]

    QgsMessageLog.logMessage(
        'usun_wydz: w bazie ' + str(len(f_arod)) + ' wydzieleń, '
        'brakuje w warstwie ' + str(len(brak_baza)),
        'Las-R', Qgis.Info
    )

    if len(brak_baza) == 0:
        iface.messageBar().pushMessage(
            "BRAK", "Nie ma wydzieleń do usunięcia", Qgis.Warning, 10
        )
        return True

    tresc = (
        'W bazie znaleziono ' + str(len(brak_baza)) + ' wydzieleń, '
        'których nie ma już w zaznaczonej warstwie.\n\n'
        'Te wydzielenia zostaną TRWALE USUNIĘTE z bazy, wraz z '
        'powiązanymi rekordami (gatunki, zabiegi, błędy itd.), oraz '
        'opróżnionymi przez to oddziałami/leśnictwami.\n\n'
    )
    if len(brak_baza) == len(f_arod):
        tresc += (
            'UWAGA: to jest CAŁA zawartość wydzieleń w bazie (100%) - '
            'sprawdź, czy wskazano właściwą warstwę/bazę!\n\n'
        )
    tresc += (
        'Przed usunięciem zostanie zrobiona kopia bazy i warstwy WYDZ w '
        'folderze Kopie_manipulacyjne (w katalogu bazy), ale tej operacji '
        'nie da się wycofać inaczej, niż przywracając tę kopię.\n\n'
        'Czy na pewno usunąć?'
    )

    odp = QMessageBox.question(
        iface.mainWindow(),
        'Skasuj wydzielenia w bazie',
        tresc,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    if odp != QMessageBox.Yes:
        iface.messageBar().pushMessage(
            "PRZERWANO", "Nie usunięto żadnych rekordów", Qgis.Info, 10
        )
        return False

    folder_kopii = kopie_manipulacyjne.zrob_kopie_manipulacyjna(
        baza_sc, [lyr], 'usun_wydz_z_bazy'
    )
    if folder_kopii is None:
        iface.messageBar().pushMessage(
            "BŁĄD", "Nie udało się utworzyć kopii bezpieczeństwa - "
            "przerwano, nic nie usunięto", Qgis.Critical, 10
        )
        return False

    res = baza.usun_rekordy(brak_baza)
    if res:
        iface.messageBar().pushMessage(
            "OK", "Usunięto " + str(len(brak_baza)) + " wydzieleń z bazy "
            "(kopia zapasowa zachowana)", Qgis.Success, 10
        )
        return True

    iface.messageBar().pushMessage(
        "BŁĄD", "Coś poszło nie tak, zmiany wycofane - sprawdź log Las-R",
        Qgis.Critical, 10
    )
    return False
