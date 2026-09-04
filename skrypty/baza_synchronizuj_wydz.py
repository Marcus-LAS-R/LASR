import os
import glob

from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsVectorLayer
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QPushButton, QVBoxLayout,
)

from .baza_wrapper import Baza
from . import kopie_manipulacyjne

# indeksy w 25-znakowym adresie lesnym (patrz shp_adr_les.zbuduj_adres):
# TERYT(10) + '-' + GRP(2) + ODDZ(4) + '-' + WYDZ(4) + '-00'
_GRP_OD = 11
_GRP_DO = 13


def _klucz_bez_grupy(adres):
    """Adres bez 2-znakowej grupy (leśnictwa) - do wykrywania par, w
    których adres różni się WYŁĄCZNIE grupą."""
    return adres[:_GRP_OD] + adres[_GRP_DO:]


class _WyborDialog(QDialog):
    """ Wybór warstwy WYDZ (z TOC) i bazy Taksatora - identyczny wzorzec co
    w baza_usun_wydz._WyborDialog. """

    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.setWindowTitle('Usuń nadmiarowe WYDZ w bazie')
        self.setMinimumWidth(480)

        self._warstwy = [
            lyr for lyr in QgsProject.instance().mapLayers().values()
            if isinstance(lyr, QgsVectorLayer)
        ]

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            'Adresy leśne różniące się w bazie wyłącznie grupą (leśnictwem) '
            'względem zaznaczonej warstwy zostaną poprawione. Wydzielenia, '
            'których nie ma już w warstwie, zostaną trwale usunięte z bazy.'
        ))

        warstwa_row = QHBoxLayout()
        warstwa_row.addWidget(QLabel('Warstwa WYDZ:'))
        self.combo_warstwa = QComboBox()
        self.combo_warstwa.addItems([lyr.name() for lyr in self._warstwy])
        warstwa_row.addWidget(self.combo_warstwa, 1)
        layout.addLayout(warstwa_row)

        baza_row = QHBoxLayout()
        baza_row.addWidget(QLabel('Baza Taksatora:'))
        self.edit_baza = QLineEdit()
        baza_row.addWidget(self.edit_baza, 1)
        przegladaj_btn = QPushButton('Wybierz…')
        przegladaj_btn.clicked.connect(self._wybierz_baze)
        baza_row.addWidget(przegladaj_btn)
        layout.addLayout(baza_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if self._warstwy:
            indeks = next(
                (i for i, lyr in enumerate(self._warstwy)
                 if lyr.name().upper() == 'WYDZ'), 0)
            self.combo_warstwa.setCurrentIndex(indeks)

        self.combo_warstwa.currentIndexChanged.connect(self._zgadnij_baze)
        self._zgadnij_baze()

    def _zgadnij_baze(self):
        lyr = self.warstwa()
        if lyr is None:
            return
        try:
            sc = lyr.dataProvider().dataSourceUri().split('|')[0]
            kat = os.path.dirname(sc)
            poziom = '..' if lyr.name().upper() == 'ODDZ' else os.path.join('..', '..')
            kandydaci = glob.glob(os.path.join(kat, poziom, '*.mdb'))
        except Exception:
            kandydaci = []
        if len(kandydaci) == 1:
            self.edit_baza.setText(os.path.abspath(kandydaci[0]))

    def _wybierz_baze(self):
        kat_start = os.path.dirname(self.edit_baza.text().strip())
        sc, _ = QFileDialog.getOpenFileName(
            self, 'Wskaż bazę Taksatora', kat_start,
            'Access MDB (*.mdb);;SQLite (*.sqlite)')
        if sc:
            self.edit_baza.setText(sc)

    def warstwa(self):
        i = self.combo_warstwa.currentIndex()
        return self._warstwy[i] if 0 <= i < len(self._warstwy) else None

    def baza_sc(self):
        return self.edit_baza.text().strip() or None


def _znajdz_pary_grupy(brak_w_lyr, brak_w_bazie):
    """Wśród adresów obecnych tylko w bazie (brak_w_lyr) i obecnych tylko
    w warstwie (brak_w_bazie) szuka par różniących się WYŁĄCZNIE grupą -
    czyli mających identyczny klucz po usunięciu grupy z adresu. Dopuszcza
    tylko jednoznaczne pary (dokładnie 1 kandydat po każdej stronie danego
    klucza) - przy niejednoznaczności adresy zostają nietknięte i trafiają
    do zwykłego porównania (usunięcie/pozostawienie).

    Zwraca listę krotek (stary_adres, nowy_adres). """
    wg_klucza_baza = {}
    for adr in brak_w_lyr:
        wg_klucza_baza.setdefault(_klucz_bez_grupy(adr), []).append(adr)

    wg_klucza_lyr = {}
    for adr in brak_w_bazie:
        wg_klucza_lyr.setdefault(_klucz_bez_grupy(adr), []).append(adr)

    pary = []
    for klucz, adresy_baza in wg_klucza_baza.items():
        adresy_lyr = wg_klucza_lyr.get(klucz)
        if adresy_lyr and len(adresy_baza) == 1 and len(adresy_lyr) == 1:
            pary.append((adresy_baza[0], adresy_lyr[0]))
    return pary


def synchronizuj_wydz(iface):
    dlg = _WyborDialog(iface)
    if dlg.exec_() != QDialog.Accepted:
        return False

    lyr = dlg.warstwa()

    if lyr is None or not lyr.isValid():
        iface.messageBar().pushMessage(
            "BŁĄD", "Zaznacz poprawną warstwę WYDZ", Qgis.Critical, 10
        )
        return False

    if "ADR_LES" not in [x.name() for x in lyr.fields()]:
        iface.messageBar().pushMessage(
            "BŁĄD", "W wybranej warstwie brakuje kolumny ADR_LES",
            Qgis.Critical, 10
        )
        return False

    baza_sc = dlg.baza_sc()
    if not baza_sc:
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

    spis_wydz_lyr = {f["ADR_LES"] for f in lyr.getFeatures() if f["ADR_LES"]}

    brak_w_lyr = {vv for vv in f_arod if vv not in spis_wydz_lyr}
    brak_w_bazie = {adr for adr in spis_wydz_lyr if adr not in f_arod}

    pary_grupa = _znajdz_pary_grupy(brak_w_lyr, brak_w_bazie)
    adresy_do_zmiany = {stary for stary, _ in pary_grupa}

    brak_baza = [adr for adr in brak_w_lyr if adr not in adresy_do_zmiany]

    QgsMessageLog.logMessage(
        'synchronizuj_wydz: w bazie ' + str(len(f_arod)) + ' wydzieleń, '
        'do poprawy grupy ' + str(len(pary_grupa)) + ', '
        'do usunięcia ' + str(len(brak_baza)),
        'Las-R', Qgis.Info
    )

    if len(pary_grupa) == 0 and len(brak_baza) == 0:
        iface.messageBar().pushMessage(
            "BRAK", "Baza jest już zgodna z warstwą", Qgis.Warning, 10
        )
        return True

    tresc = ''
    if pary_grupa:
        tresc += (
            'W bazie znaleziono ' + str(len(pary_grupa)) + ' wydzieleń, '
            'których adres różni się od warstwy WYŁĄCZNIE grupą '
            '(leśnictwem) - zostanie on nadpisany adresem z warstwy.\n\n'
        )
    if brak_baza:
        tresc += (
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
        'Przed zmianami zostanie zrobiona kopia bazy i warstwy WYDZ w '
        'folderze Kopie_manipulacyjne (w katalogu bazy), ale tej operacji '
        'nie da się wycofać inaczej, niż przywracając tę kopię.\n\n'
        'Czy na pewno kontynuować?'
    )

    odp = QMessageBox.question(
        iface.mainWindow(),
        'Usuń nadmiarowe WYDZ w bazie',
        tresc,
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No
    )
    if odp != QMessageBox.Yes:
        iface.messageBar().pushMessage(
            "PRZERWANO", "Nie zmieniono żadnych rekordów", Qgis.Info, 10
        )
        return False

    folder_kopii = kopie_manipulacyjne.zrob_kopie_manipulacyjna(
        baza_sc, [lyr], 'synchronizuj_wydz_z_baza'
    )
    if folder_kopii is None:
        iface.messageBar().pushMessage(
            "BŁĄD", "Nie udało się utworzyć kopii bezpieczeństwa - "
            "przerwano, nic nie zmieniono", Qgis.Critical, 10
        )
        return False

    if pary_grupa:
        zmiany = {f_arod[stary]: nowy for stary, nowy in pary_grupa}
        if not baza.zmien_adresy(zmiany):
            iface.messageBar().pushMessage(
                "BŁĄD", "Coś poszło nie tak przy poprawie grup, zmiany "
                "wycofane - sprawdź log Las-R", Qgis.Critical, 10
            )
            return False

    if brak_baza:
        do_usun = [f_arod[adr] for adr in brak_baza]
        if not baza.usun_rekordy(do_usun):
            iface.messageBar().pushMessage(
                "BŁĄD", "Poprawiono grupy, ale usuwanie się nie powiodło - "
                "sprawdź log Las-R", Qgis.Critical, 10
            )
            return False

    iface.messageBar().pushMessage(
        "OK",
        f"Poprawiono grupę w {len(pary_grupa)} adresach, "
        f"usunięto {len(brak_baza)} wydzieleń z bazy "
        "(kopia zapasowa zachowana)", Qgis.Success, 10
    )
    return True
