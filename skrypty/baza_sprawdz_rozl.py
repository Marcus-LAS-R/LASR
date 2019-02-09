import os
import platform
from qgis.core import Qgis
from PyQt5.QtWidgets import QMessageBox

from .baza_rozlicz_pow_wydz import SprawdzRozliczenie
from .baza_wrapper import Baza, znajdz_baze_do_wydz
from .pw import PasekPostepu


def sprawdz_rozliczenie_bazy(iface):

    # wskaż bazę którą chcesz sprawdzać
    baza_sc = znajdz_baze_do_wydz(iface)

    baza = Baza(baza_sc)
    if not baza.polacz():
        iface.messageBar().pushMessage(
            'BŁĄÐ', 'Nie można otworzyć bazy!', Qgis.Critical, 10)
        return False

    postep = PasekPostepu(iface).stworz_pasek(
        'Sprawdzanie rozliczenia bazy: ' + baza_sc
    )

    postep.setValue(20)

    oroz = SprawdzRozliczenie(postep, baza)
    oroz.przetworz_baze()
    oroz.przelicz_rozliczenie()
    oroz.oblicz_staty()
    oroz.zestaw_staty()

    wypis = oroz.zwroc_wypis()

    iface.messageBar().clearWidgets()

    sc = os.path.join(
        os.path.dirname(baza.baza),
        'raport_spr_rozliczPow_'+baza.czas+'.txt')

    plik = open(sc, 'w')

    plik.write(wypis)
    plik.close()

    message = QMessageBox()
    message.setIcon(QMessageBox.Information)
    message.setWindowTitle('Raport')
    message.setText('Czy pokazać raport z rozliczenia powierzchni?')
    message.addButton(u"Zamknij", QMessageBox.ActionRole)
    message.addButton(u"Zamknij i pokaż raport", QMessageBox.ActionRole)
    pok_rap = message.exec_()

    if pok_rap == 1:
        if platform.system()[:3] == 'Win':
            os.startfile(sc)
        else:
            import subprocess
            subprocess.call(['kate', sc])

    iface.messageBar().pushMessage(
        'OK', 'Sprawdzanie powierzchni zakończone!', Qgis.Success, 10)
