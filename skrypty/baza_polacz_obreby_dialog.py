import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QVBoxLayout,
)

from .ui.ui_baza_polacz_obreby import Ui_Dialog
from .baza_wrapper import Baza

# rozpoznawane przedrostki w nazwach eksportowanych baz - czysto
# informacyjne, nie wplywaja na laczenie
_PRZEDROSTKI_BAZ = (
    ('CALOSC_', 'CAŁOŚĆ'),
    ('WYBRANE_', 'WYBRANE'),
)

_KOLUMNY_OBREBOW = 2


def _etykieta_bazy(sciezka):
    """Zwraca czytelna etykiete pliku bazy do naglowka bloku w dialogu -
    rozpoznaje przedrostki eksportu (CALOSC_ - baza wyeksportowana z
    calosci, WYBRANE_ - baza wyeksportowana dla wybranych obrebow), w
    przeciwnym razie zwraca sama nazwe pliku."""
    nazwa = os.path.basename(sciezka)
    nazwa_wielka = nazwa.upper()
    for przedrostek, etykieta in _PRZEDROSTKI_BAZ:
        if nazwa_wielka.startswith(przedrostek):
            return f'[{etykieta}] {nazwa[len(przedrostek):]}'
    return nazwa


def _etykiety_obr(obreby):
    """Zwraca liste etykiet (rownolegla do `obreby`) do checkboxow obrebow.
    Pelna forma WOJ.POW.GMI.OBREB — nazwa, albo skrocona GMI.OBREB — nazwa
    gdy wszystkie obreby na liscie maja to samo WOJ i POW (typowy
    przypadek — jedna baza to zwykle jedno nadlesnictwo, czyli jedno
    wojewodztwo/powiat, wiec te dwa czlony sa wtedy tylko szumem)."""
    grupy = {(county, district) for county, district, _, _, _ in obreby}
    skrot = len(grupy) <= 1
    etykiety = []
    for county, district, municip, community, nazwa in obreby:
        if skrot:
            etykiety.append(f'{municip}.{community} — {nazwa}')
        else:
            etykiety.append(
                f'{county}.{district}.{municip}.{community} — {nazwa}')
    return etykiety


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
        # {baza_sc: [(klucz, QCheckBox), ...]} - checkbox na obreb, w
        # siatce 2 kolumn wewnatrz bloku danej bazy
        self.checkboxy_per_baza = {}
        # {baza_sc: QCheckBox} - "duzy" checkbox w naglowku bloku, zaznacz/
        # odznacz wszystkie obreby TEJ jednej bazy naraz (tristate - pokazuje
        # tez stan czesciowy, gdy user odznaczyl tylko czesc obrebow)
        self.checkbox_baza_per_baza = {}
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

        # Pakowanie blokow do 2 kolumn metoda "dolóż do krótszej" (greedy,
        # od najwyzszego bloku) - zwykla siatka 2 kolumn wymusza wysokosc
        # wiersza na najwyzszym elemencie, co przy nierownych blokach
        # (jedna baza z 50 obrebami, druga z 2) zostawia ogromne puste
        # obszary w krotszej kolumnie. Wysokosc bloku szacowana liczba
        # wierszy checkboxow obrebow (+1 za naglowek), bez realnego layoutu.
        def _wiersze(baza_sc):
            n = len(self.obreby_per_baza.get(baza_sc, []))
            return -(-n // _KOLUMNY_OBREBOW)  # ceil(n / _KOLUMNY_OBREBOW)

        kolumny = [self.ui.layout_kolumna_lewa, self.ui.layout_kolumna_prawa]
        wysokosc_kolumn = [0, 0]
        for baza_sc in sorted(lista_baz, key=_wiersze, reverse=True):
            kol = 0 if wysokosc_kolumn[0] <= wysokosc_kolumn[1] else 1
            blok = self._zbuduj_blok_bazy(baza_sc)
            kolumny[kol].addWidget(blok)
            wysokosc_kolumn[kol] += _wiersze(baza_sc) + 1
        for kol in kolumny:
            kol.addStretch(1)

        self.ui.pushButton_zaznacz_wszystkie.clicked.connect(
            lambda: self._zaznacz_wszystkie(True))
        self.ui.pushButton_odznacz_wszystkie.clicked.connect(
            lambda: self._zaznacz_wszystkie(False))
        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)

    def _zbuduj_blok_bazy(self, baza_sc):
        """Buduje jeden blok: naglowek z duzym checkboxem (zaznacz/odznacz
        wszystkie obreby TEJ bazy) + nazwa pliku, ponizej siatka checkboxow
        obrebow (2 kolumny)."""
        obreby = self.obreby_per_baza.get(baza_sc, [])
        etykiety = _etykiety_obr(obreby)

        box = QGroupBox()
        # Domyslna ramka QGroupBox bywa ledwo widoczna w ciemnym motywie
        # QGIS (kolor ramki zblizony do tla) - wymuszamy kontrastowa ramke
        # niezaleznie od motywu, zeby bloki poszczegolnych baz dalo sie
        # latwo odroznic wzrokowo.
        box.setStyleSheet(
            "QGroupBox { border: 1px solid palette(mid); "
            "border-radius: 4px; margin-top: 4px; padding: 6px; }")
        box_layout = QVBoxLayout(box)

        naglowek = QHBoxLayout()
        checkbox_baza = QCheckBox()
        checkbox_baza.setTristate(True)
        checkbox_baza.setCheckState(Qt.Checked)
        checkbox_baza.stateChanged.connect(
            lambda stan, b=baza_sc: self._zaznacz_baze(b, stan))
        naglowek.addWidget(checkbox_baza)

        etykieta_nazwy = QLabel(_etykieta_bazy(baza_sc))
        czcionka = QFont()
        czcionka.setBold(True)
        etykieta_nazwy.setFont(czcionka)
        naglowek.addWidget(etykieta_nazwy, 1)
        box_layout.addLayout(naglowek)

        linia = QFrame()
        linia.setFrameShape(QFrame.HLine)
        linia.setFrameShadow(QFrame.Sunken)
        box_layout.addSpacing(2)
        box_layout.addWidget(linia)
        box_layout.addSpacing(4)

        siatka = QGridLayout()
        checkboxy = []
        for i, ((county, district, municip, community, _nazwa), etykieta) in \
                enumerate(zip(obreby, etykiety)):
            klucz = (county, district, municip, community)
            cb = QCheckBox(etykieta)
            cb.setChecked(True)
            cb.stateChanged.connect(
                lambda _stan, b=baza_sc: self._zapisz_stan_bazy(b))
            siatka.addWidget(cb, i // _KOLUMNY_OBREBOW, i % _KOLUMNY_OBREBOW)
            checkboxy.append((klucz, cb))
        box_layout.addLayout(siatka)
        box_layout.addStretch(1)

        self.checkboxy_per_baza[baza_sc] = checkboxy
        self.checkbox_baza_per_baza[baza_sc] = checkbox_baza
        return box

    def _zaznacz_baze(self, baza_sc, stan):
        """Handler duzego checkboxa w naglowku bloku - zaznacza/odznacza
        wszystkie obreby danej bazy. Stan czesciowy (PartiallyChecked) to
        tylko odczyt (ustawiany przez _odswiez_checkbox_baza), nie akcja
        usera - ignorowany tutaj."""
        if self._laduje or stan == Qt.PartiallyChecked:
            return
        self._laduje = True
        checked = stan == Qt.Checked
        for _klucz, cb in self.checkboxy_per_baza.get(baza_sc, []):
            cb.setChecked(checked)
        self._laduje = False
        self._zapisz_stan_bazy(baza_sc)

    def _odswiez_checkbox_baza(self, baza_sc):
        """Synchronizuje duzy checkbox w naglowku ze stanem obrebow -
        Checked gdy wszystkie zaznaczone, Unchecked gdy zadne, inaczej
        PartiallyChecked."""
        checkbox_baza = self.checkbox_baza_per_baza.get(baza_sc)
        checkboxy = self.checkboxy_per_baza.get(baza_sc, [])
        if checkbox_baza is None or not checkboxy:
            return
        zaznaczone = sum(1 for _k, cb in checkboxy if cb.isChecked())
        if zaznaczone == 0:
            nowy_stan = Qt.Unchecked
        elif zaznaczone == len(checkboxy):
            nowy_stan = Qt.Checked
        else:
            nowy_stan = Qt.PartiallyChecked
        if checkbox_baza.checkState() != nowy_stan:
            self._laduje = True
            checkbox_baza.setCheckState(nowy_stan)
            self._laduje = False

    def _zapisz_stan_bazy(self, baza_sc):
        if self._laduje:
            return
        checkboxy = self.checkboxy_per_baza.get(baza_sc, [])

        zaznaczone = set()
        wszystkie_zaznaczone = True
        for klucz, cb in checkboxy:
            if cb.isChecked():
                zaznaczone.add(klucz)
            else:
                wszystkie_zaznaczone = False

        # None = brak filtra (kanoniczna reprezentacja "wszystko dozwolone",
        # spojna z Laczenie.dozwolone_obreby)
        self.wybor_per_baza[baza_sc] = None if wszystkie_zaznaczone else zaznaczone
        self._odswiez_checkbox_baza(baza_sc)

    def _zaznacz_wszystkie(self, stan):
        self._laduje = True
        for checkboxy in self.checkboxy_per_baza.values():
            for _klucz, cb in checkboxy:
                cb.setChecked(stan)
        self._laduje = False
        for baza_sc in self.lista_baz:
            self._zapisz_stan_bazy(baza_sc)

    def wybor(self):
        """Zwraca {baza_sc: set(tuple)|None} - wybór obrębów per baza."""
        for baza_sc in self.lista_baz:
            self._zapisz_stan_bazy(baza_sc)
        return self.wybor_per_baza
