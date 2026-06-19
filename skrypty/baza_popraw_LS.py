import os
import platform
import glob
import bisect
from collections import Counter
from datetime import datetime
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox

from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza
from .ui.ui_baza_popraw_ls import Ui_Dialog


def _sort_key(row):
    return tuple("" if v is None else str(v) for v in row)


def SprawdzBazy(iface):
    d = PobierzDane()
    d.exec_()

    if not d.kontynuuj:
        return

    bazy_kat = d.ui.lineEdit_bazy.text()
    wszystkie_uzytki = d.ui.checkBox_wszystkie.isChecked()

    if platform.system()[:3] == "Win":
        bazy_sc = glob.glob(os.path.join(bazy_kat, "*.mdb"))
    else:
        bazy_sc = glob.glob(os.path.join(bazy_kat, "*.sqlite"))

    if len(bazy_sc) == 0:
        iface.messageBar().pushMessage(
            "BŁĄD", "Nie znalazłem żadnej bazy taksatora...", Qgis.Critical, 10
        )
        return

    czas = datetime.now().isoformat().replace(":", "")[:-7]
    wypis = "-----[ RAPORT KONTROLI LS W BAZIE ]-----\n\n"
    if wszystkie_uzytki:
        wypis += (
            "(kontrola duplikatów i zerowych powierzchni rozszerzona na "
            "wszystkie użytki, nie tylko Ls)\n\n"
        )

    razem_podwojne = 0
    razem_zerowe = 0
    razem_scalone = 0
    razem_usuniete = 0

    for sc in bazy_sc:
        baza = Baza(sc)
        if not baza.polacz():
            QgsMessageLog.logMessage(
                "Nie mogłem połączyć się z bazą: " + sc, "Las-R"
            )
            wypis += "BAZA: " + sc + "\n  Nie udało się połączyć z bazą\n\n"
            continue

        QgsMessageLog.logMessage(
            "\n" + 20 * "-" + "\nPrzetwarzam bazę: " + sc, "Las-R", Qgis.Info
        )

        podwojne, zerowe = SprawdzBaze(baza, wszystkie_uzytki)
        razem_podwojne += len(podwojne)
        razem_zerowe += len(zerowe)

        wypis += "BAZA: " + sc + "\n"
        wypis += "  Zdublowane zestawy AREA_USE_CD+SOIL_QUALITY_CD: " + \
            str(len(podwojne)) + "\n"
        wypis += "  Rekordy z LAND_USE_AREA = 0: " + str(len(zerowe)) + "\n"

        if len(podwojne) > 0:
            wypis += "\n  ---PODWÓJNE ZESTAWY---\n"
            wypis += "  działka\tAREA_USE_CD\tSOIL_QUALITY_CD\tile\n"
            for wyr1, au, sq, ile in sorted(podwojne, key=_sort_key):
                wypis += "  " + "\t".join(
                    [str(wyr1), str(au), str(sq), str(ile)]
                ) + "\n"

        if len(zerowe) > 0:
            wypis += "\n  ---ZEROWE POWIERZCHNIE---\n"
            wypis += "  działka\tAREA_USE_CD\tSOIL_QUALITY_CD\n"
            for wyr1, au, sq in sorted(zerowe, key=_sort_key):
                wypis += "  " + "\t".join([str(wyr1), str(au), str(sq)]) + "\n"

        backup_zrobiony = False

        if len(podwojne) > 0 or len(zerowe) > 0:
            ile_arod = baza.pobierz("select count(*) from F_AROD_LAND_USE;")
            ile_arod = ile_arod[0][0] if ile_arod else 0
            if ile_arod > 0:
                QMessageBox.information(
                    iface.mainWindow(),
                    "F_AROD_LAND_USE",
                    "W tabeli F_AROD_LAND_USE znaleziono dane.\n"
                    "Pamiętaj po naprawie ponownie rozliczyć powierzchnię.",
                )
                wypis += (
                    "\n  UWAGA: F_AROD_LAND_USE zawiera dane (" +
                    str(ile_arod) + " wierszy) — po naprawie należy "
                    "ponownie rozliczyć powierzchnię\n"
                )

        if len(podwojne) > 0:
            odp = QMessageBox.question(
                iface.mainWindow(),
                "Naprawa duplikatów",
                "Baza: " + os.path.basename(sc) + "\n"
                "Znaleziono " + str(len(podwojne)) + " zdublowanych "
                "zestawów AREA_USE_CD+SOIL_QUALITY_CD.\n\n"
                "Zsumować powierzchnie (LAND_USE_AREA) i usunąć nadmiarowe "
                "rekordy?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if odp == QMessageBox.Yes:
                if not backup_zrobiony:
                    baza.utworz_kopie("popraw_ls")
                    backup_zrobiony = True
                scalone, usuniete, renum = NaprawDuplikaty(
                    baza, wszystkie_uzytki
                )
                razem_scalone += scalone
                wypis += (
                    "\n  NAPRAWIONO: scalono " + str(scalone) +
                    " zestawów, usunięto " + str(usuniete) +
                    " nadmiarowych rekordów, przenumerowano " +
                    str(renum) + " SHAPE_NR\n"
                )
            else:
                wypis += "\n  (naprawa duplikatów odrzucona przez " \
                    "użytkownika)\n"

        if len(zerowe) > 0:
            odp = QMessageBox.question(
                iface.mainWindow(),
                "Naprawa zerowych powierzchni",
                "Baza: " + os.path.basename(sc) + "\n"
                "Znaleziono " + str(len(zerowe)) + " rekordów z "
                "LAND_USE_AREA = 0.\n\n"
                "Usunąć te rekordy?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if odp == QMessageBox.Yes:
                if not backup_zrobiony:
                    baza.utworz_kopie("popraw_ls")
                    backup_zrobiony = True
                usuniete, renum = NaprawZerowe(baza, wszystkie_uzytki)
                razem_usuniete += usuniete
                wypis += (
                    "\n  NAPRAWIONO: usunięto " + str(usuniete) +
                    " rekordów, przenumerowano " + str(renum) +
                    " SHAPE_NR\n"
                )
            else:
                wypis += "\n  (naprawa zerowych powierzchni odrzucona " \
                    "przez użytkownika)\n"

        wypis += "\n" + 33 * "-" + "\n\n"

        QgsMessageLog.logMessage("\n" + 20 * "-", "Las-R", Qgis.Info)
        baza.zamknij()

    wypis += "\n-----[ KONIEC RAPORTU ]------"

    rap_sc = os.path.join(bazy_kat, "popraw_ls_kontrola_" + czas + ".txt")
    plik = open(rap_sc, "w", encoding="cp1250")
    plik.write(wypis)
    plik.close()

    iface.messageBar().clearWidgets()
    message = QMessageBox()
    message.setIcon(QMessageBox.Information)
    message.setWindowTitle("Raport")
    message.setText(
        "Kontrola zakończona.\nZdublowane zestawy: " + str(razem_podwojne) +
        " (scalono: " + str(razem_scalone) + ")" +
        "\nZerowe powierzchnie: " + str(razem_zerowe) +
        " (usunięto: " + str(razem_usuniete) + ")" +
        "\n\nPokazać raport?"
    )
    message.addButton("Nie", QMessageBox.ActionRole)
    message.addButton("Tak", QMessageBox.ActionRole)
    pok_rap = message.exec_()

    if pok_rap == 1:
        if platform.system()[:3] == "Win":
            os.startfile(rap_sc)
        else:
            import subprocess
            subprocess.call(["kate", rap_sc])

    iface.messageBar().pushMessage(
        "OK",
        "Kontrola zakończona — zdublowane: " + str(razem_podwojne) +
        ", zerowe pow.: " + str(razem_zerowe) + " (szczegóły w raporcie)",
        Qgis.Success,
        10,
    )


def SprawdzBaze(baza, wszystkie_uzytki=False):
    """Sprawdza pojedynczą bazę pod kątem:
    1) zdublowanych zestawów AREA_USE_CD+SOIL_QUALITY_CD na jednej działce
       (domyślnie tylko dla AREA_USE_CD='Ls', opcjonalnie dla wszystkich)
    2) rekordów w F_PARCEL_LAND_USE z LAND_USE_AREA = 0 (domyślnie tylko dla
       AREA_USE_CD='Ls', opcjonalnie dla wszystkich użytków — tak jak w
       kontroli duplikatów)

    Funkcja jest tylko kontrolna — nie zmienia danych w bazie.
    Zwraca [podwojne, zerowe], gdzie:
      podwojne = [[Wyr1, AREA_USE_CD, SOIL_QUALITY_CD, ile], ...]
      zerowe   = [[Wyr1, AREA_USE_CD, SOIL_QUALITY_CD], ...]
    """
    uzytki = baza.uzytki()
    # kolumny wiersza z Baza.uzytki():
    # 0 COUNTY_CD, 1 DISTRICT_CD, 2 MUNICIPALITY_CD, 3 COMMUNITY_CD,
    # 4 REG_SHEET_NR2, 5 PARCEL_NR, 6 PARCEL_INT_NUM, 7 PARCEL_AREA,
    # 8 SHAPE_NR, 9 AREA_USE_CD, 10 SOIL_QUALITY_CD, 11 LAND_USE_AREA,
    # 12 Wyr1

    sl_grupy = {}  # {PARCEL_INT_NUM: Counter({(AU, SQ): ile, ...})}
    sl_wyr1 = {}  # {PARCEL_INT_NUM: Wyr1}

    for row in uzytki:
        pid = row[6]
        au = row[9]
        sq = row[10]
        sl_wyr1[pid] = row[12]

        if not wszystkie_uzytki and au != "Ls":
            continue

        sl_grupy.setdefault(pid, Counter())[(au, sq)] += 1

    podwojne = []
    for pid, cnt in sl_grupy.items():
        for (au, sq), ile in cnt.items():
            if ile > 1:
                podwojne.append([sl_wyr1.get(pid, str(pid)), au, sq, ile])

    zerowe = [
        [row[12], row[9], row[10]]
        for row in uzytki
        if row[11] is not None and abs(row[11]) < 0.0001
        and (wszystkie_uzytki or row[9] == "Ls")
    ]

    return podwojne, zerowe


def NaprawDuplikaty(baza, wszystkie_uzytki=False):
    """Naprawia zdublowane zestawy AREA_USE_CD+SOIL_QUALITY_CD na działce:
    dla każdej grupy zostawia rekord z najniższym SHAPE_NR, wpisuje mu sumę
    LAND_USE_AREA z całej grupy, a pozostałe rekordy z grupy usuwa. Na końcu
    domyka dziury w numeracji SHAPE_NR powstałe przez usunięcie rekordów.

    Zwraca (ile_scalonych_grup, ile_usunietych_rekordow, ile_przenumerowanych)
    """
    sql = (
        "select PARCEL_INT_NUM, SHAPE_NR, AREA_USE_CD, SOIL_QUALITY_CD, "
        "LAND_USE_AREA from F_PARCEL_LAND_USE"
    )
    if not wszystkie_uzytki:
        sql += " where AREA_USE_CD = 'Ls'"
    sql += ";"
    rows = baza.pobierz(sql)

    sl_grupy = {}  # {(PARCEL_INT_NUM, AU, SQ_upper): [(SHAPE_NR, AREA), ...]}
    for pid, shape_nr, au, sq, area in rows:
        sq_n = sq.upper() if isinstance(sq, str) else sq
        sl_grupy.setdefault((pid, au, sq_n), []).append((shape_nr, area))

    usuniete_by_pid = {}  # {PARCEL_INT_NUM: {SHAPE_NR, ...}}
    ile_scalonych = 0
    ile_usunietych = 0

    for (pid, au, sq_n), grupa in sl_grupy.items():
        if len(grupa) < 2:
            continue

        grupa = sorted(grupa, key=lambda x: x[0])
        keep_shape_nr = grupa[0][0]
        suma = round(sum(a for _, a in grupa if a is not None), 4)

        baza.wpisz_tab((
            "update F_PARCEL_LAND_USE set LAND_USE_AREA = ? "
            "where PARCEL_INT_NUM = ? and SHAPE_NR = ?;",
            (suma, pid, keep_shape_nr),
        ))
        ile_scalonych += 1

        for shape_nr, _ in grupa[1:]:
            baza.wpisz(
                "delete * from F_PARCEL_LAND_USE where PARCEL_INT_NUM = " +
                str(pid) + " and SHAPE_NR = " + str(shape_nr) + ";"
            )
            usuniete_by_pid.setdefault(pid, set()).add(shape_nr)
            ile_usunietych += 1

    ile_renum = _renumeruj_shape_nr(baza, usuniete_by_pid)
    return ile_scalonych, ile_usunietych, ile_renum


def NaprawZerowe(baza, wszystkie_uzytki=False):
    """Usuwa z F_PARCEL_LAND_USE rekordy z LAND_USE_AREA = 0 (domyślnie
    tylko dla AREA_USE_CD='Ls', opcjonalnie dla wszystkich użytków) i domyka
    powstałe dziury w numeracji SHAPE_NR.

    Zwraca (ile_usunietych_rekordow, ile_przenumerowanych)
    """
    sql = (
        "select PARCEL_INT_NUM, SHAPE_NR, AREA_USE_CD, LAND_USE_AREA "
        "from F_PARCEL_LAND_USE"
    )
    if not wszystkie_uzytki:
        sql += " where AREA_USE_CD = 'Ls'"
    sql += ";"
    rows = baza.pobierz(sql)

    usuniete_by_pid = {}
    ile_usunietych = 0

    for pid, shape_nr, au, area in rows:
        if area is None or abs(area) >= 0.0001:
            continue

        baza.wpisz(
            "delete * from F_PARCEL_LAND_USE where PARCEL_INT_NUM = " +
            str(pid) + " and SHAPE_NR = " + str(shape_nr) + ";"
        )
        usuniete_by_pid.setdefault(pid, set()).add(shape_nr)
        ile_usunietych += 1

    ile_renum = _renumeruj_shape_nr(baza, usuniete_by_pid)
    return ile_usunietych, ile_renum


def _renumeruj_shape_nr(baza, usuniete_by_pid):
    """Po usunięciu rekordów z F_PARCEL_LAND_USE domyka dziury w numeracji
    SHAPE_NR, które właśnie powstały — przesuwa numery większe od usuniętego
    o liczbę usuniętych wpisów mniejszych od nich. Nie dotyka dziur, które
    istniały w bazie wcześniej i nie są związane z tą naprawą.

    usuniete_by_pid: {PARCEL_INT_NUM: {SHAPE_NR usuniętych, ...}}
    Zwraca liczbę przenumerowanych rekordów.
    """
    ile = 0
    for pid, usuniete in usuniete_by_pid.items():
        if len(usuniete) == 0:
            continue
        usuniete_sorted = sorted(usuniete)

        pozostale = baza.pobierz(
            "select SHAPE_NR from F_PARCEL_LAND_USE where PARCEL_INT_NUM = "
            + str(pid) + " order by SHAPE_NR;"
        )
        for (old_nr,) in pozostale:
            przesuniecie = bisect.bisect_left(usuniete_sorted, old_nr)
            new_nr = old_nr - przesuniecie
            if new_nr != old_nr:
                baza.wpisz(
                    "update F_PARCEL_LAND_USE set SHAPE_NR = " +
                    str(new_nr) + " where PARCEL_INT_NUM = " + str(pid) +
                    " and SHAPE_NR = " + str(old_nr) + ";"
                )
                ile += 1
    return ile


class PobierzDane(QDialog):
    def __init__(self):
        super(PobierzDane, self).__init__()

        self.kontynuuj = False
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        self.ui.pushButton_bazy.clicked.connect(self.pobierz_bazy)
        self.ui.pushButton_ok.clicked.connect(self.zatwierdz)
        self.ui.pushButton_porzuc.clicked.connect(self.porzuc)

    def pobierz_bazy(self):
        bazy_kat = QFileDialog().getExistingDirectory(
            self, "Katalog z bazami danych", ""
        )

        if platform.system()[:3] == "Win":
            ile_baz = len(glob.glob(os.path.join(bazy_kat, "*.mdb")))
        else:
            ile_baz = len(glob.glob(os.path.join(bazy_kat, "*.sqlite")))

        if ile_baz > 0:
            self.ui.label_bazy.setText("Znalazłem baz: " + str(ile_baz))
            self.ui.lineEdit_bazy.setText(bazy_kat)
            self.ui.pushButton_ok.setEnabled(True)
        else:
            self.ui.label_bazy.setText("Nie znaleziono baz danych")
            self.ui.lineEdit_bazy.setText(bazy_kat)
            self.ui.pushButton_ok.setEnabled(False)

    def zatwierdz(self):
        self.kontynuuj = True
        self.hide()

    def porzuc(self):
        self.hide()
