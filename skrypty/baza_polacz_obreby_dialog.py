import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QListWidgetItem

from .ui.ui_baza_polacz_obreby import Ui_Dialog
from .baza_wrapper import Baza

# rozpoznawane przedrostki w nazwach eksportowanych baz - czysto
# informacyjne, nie wplywaja na laczenie
_PRZEDROSTKI_BAZ = (
    ('CALOSC_', 'CAŁOŚĆ'),
    ('WYBRANE_', 'WYBRANE'),
)


def _etykieta_bazy(sciezka):
    """Zwraca czytelna etykiete pliku bazy do listy w dialogu - rozpoznaje
    przedrostki eksportu (CALOSC_ - baza wyeksportowana z całości,
    WYBRANE_ - baza wyeksportowana dla wybranych obrębów), w przeciwnym
    razie zwraca sama nazwe pliku."""
    nazwa = os.path.basename(sciezka)
    nazwa_wielka = nazwa.upper()
    for przedrostek, etykieta in _PRZEDROSTKI_BAZ:
        if nazwa_wielka.startswith(przedrostek):
            return f'[{etykieta}] {nazwa[len(przedrostek):]}'
    return nazwa


class WyborObrebowDialog(QDialog):
    def __init__(self, iface, lista_baz):
        super().__init__(iface.mainWindow())
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.lista_baz = lista_baz
        # {baza_sc: [(COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD, COMMUNITY_CD,
        #             COMMUNITY_NAME), ...]}
        self.obreby_per_baza = {}
        # {baza_sc: set(tuple)|None} - None = wszystkie obreby zaznaczone
        # (brak filtra), zgodnie z konwencja Laczenie.dozwolone_obreby
        self.wybor_per_baza = {}
        self._laduje = False

        for baza_sc in lista_baz:
            baza = Baza(baza_sc)
            obreby = []
            if baza.polacz():
                pob = baza.pobierz_obreby()
                obreby = pob if pob is not False else []
                baza.zamknij()
            self.obreby_per_baza[baza_sc] = obreby
            self.wybor_per_baza[baza_sc] = None

        for baza_sc in lista_baz:
            self.ui.listWidget_bazy.addItem(_etykieta_bazy(baza_sc))

        self.ui.listWidget_bazy.currentRowChanged.connect(self._pokaz_baze)
        self.ui.listWidget_obreby.itemChanged.connect(self._zapisz_stan_biezacej_bazy)
        self.ui.pushButton_zaznacz_wszystkie.clicked.connect(
            lambda: self._zaznacz_wszystkie(True))
        self.ui.pushButton_odznacz_wszystkie.clicked.connect(
            lambda: self._zaznacz_wszystkie(False))
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

        if lista_baz:
            self.ui.listWidget_bazy.setCurrentRow(0)

    def _pokaz_baze(self, row):
        if row < 0 or row >= len(self.lista_baz):
            return
        baza_sc = self.lista_baz[row]
        obreby = self.obreby_per_baza.get(baza_sc, [])
        wybor = self.wybor_per_baza.get(baza_sc)  # None = wszystko zaznaczone

        self._laduje = True
        self.ui.listWidget_obreby.clear()
        for county, district, municip, community, nazwa in obreby:
            klucz = (county, district, municip, community)
            etykieta = f'{county}.{district}.{municip}.{community} — {nazwa}'
            item = QListWidgetItem(etykieta)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            zaznaczony = wybor is None or klucz in wybor
            item.setCheckState(Qt.Checked if zaznaczony else Qt.Unchecked)
            item.setData(Qt.UserRole, klucz)
            self.ui.listWidget_obreby.addItem(item)
        self._laduje = False

    def _zapisz_stan_biezacej_bazy(self, *_):
        if self._laduje:
            return
        row = self.ui.listWidget_bazy.currentRow()
        if row < 0 or row >= len(self.lista_baz):
            return
        baza_sc = self.lista_baz[row]

        n = self.ui.listWidget_obreby.count()
        zaznaczone = set()
        wszystkie_zaznaczone = True
        for i in range(n):
            item = self.ui.listWidget_obreby.item(i)
            klucz = item.data(Qt.UserRole)
            if item.checkState() == Qt.Checked:
                zaznaczone.add(klucz)
            else:
                wszystkie_zaznaczone = False

        # None = brak filtra (kanoniczna reprezentacja "wszystko dozwolone",
        # spojna z Laczenie.dozwolone_obreby)
        self.wybor_per_baza[baza_sc] = None if wszystkie_zaznaczone else zaznaczone

    def _zaznacz_wszystkie(self, stan):
        self._laduje = True
        checked = Qt.Checked if stan else Qt.Unchecked
        for i in range(self.ui.listWidget_obreby.count()):
            self.ui.listWidget_obreby.item(i).setCheckState(checked)
        self._laduje = False
        self._zapisz_stan_biezacej_bazy()

    def wybor(self):
        """Zwraca {baza_sc: set(tuple)|None} - wybór obrębów per baza."""
        self._zapisz_stan_biezacej_bazy()
        return self.wybor_per_baza
