"""Monit wspólny dla Podziel obiekt (UPUL/ISL, gminami, obrębami): w bazie
źródłowej są obręby/działki gmin, których NIE MA w słowniku F_MUNICIPALITY.
Użytkownik decyduje, czy dopisać je (z nazwą) do baz wynikowych. Słownika
skrypty dzielące nigdy nie okrajają."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QDialog, QLabel, QTableWidget, QTableWidgetItem,
    QVBoxLayout,
)
from ...przyciski import QDialogButtonBox

from ..core import rozdziel as R

DOPISZ, NIE_DOPISUJ = 'dopisz', 'nie'


class BrakGminDialog(QDialog):
    def __init__(self, parent, tytul, brak, nazwy=None):
        """brak: {(COUNTY, DISTRICT, MUNICIP): liczba działek},
        nazwy: {klucz: podpowiedź nazwy} (np. z GMIN.shp)."""
        super().__init__(parent)
        nazwy = nazwy or {}
        self.decyzja = None
        self._klucze = sorted(brak)
        self.setWindowTitle(tytul + ' - gminy spoza słownika')
        self.resize(640, 360)
        lay = QVBoxLayout(self)

        lab = QLabel(
            f'W bazie są obręby/działki {len(brak)} gmin, których NIE MA '
            'w słowniku gmin F_MUNICIPALITY.\n\n'
            'Dopisać je do słownika w bazach wynikowych? Nazwę można '
            'poprawić w tabeli (maks. 30 znaków). Baza źródłowa nie jest '
            'zmieniana.')
        lab.setWordWrap(True)
        lab.setStyleSheet('color: #b00000; font-weight: bold;')
        lay.addWidget(lab)

        self.tabela = QTableWidget(len(self._klucze), 3)
        self.tabela.setHorizontalHeaderLabels(
            ['Gmina (WW PP GGR)', 'Działek', 'Nazwa do słownika'])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionMode(QAbstractItemView.NoSelection)
        for w, k in enumerate(self._klucze):
            for kol, tekst in ((0, ' '.join(k)), (1, str(brak[k]))):
                it = QTableWidgetItem(tekst)
                it.setFlags(Qt.ItemIsEnabled)
                if kol == 1:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabela.setItem(w, kol, it)
            nazwa = nazwy.get(k) or R.podpowiedz_nazwy_gminy(k)
            self.tabela.setItem(w, 2, QTableWidgetItem((nazwa or '')[:30]))
        self.tabela.resizeColumnsToContents()
        self.tabela.horizontalHeader().setStretchLastSection(True)
        lay.addWidget(self.tabela, 1)

        przyciski = QDialogButtonBox(QDialogButtonBox.Cancel)
        b_tak = przyciski.addButton('Dopisz do baz wynikowych',
                                    QDialogButtonBox.AcceptRole)
        b_nie = przyciski.addButton('Nie dopisuj',
                                    QDialogButtonBox.AcceptRole)
        b_tak.clicked.connect(lambda: self._zamknij(DOPISZ))
        b_nie.clicked.connect(lambda: self._zamknij(NIE_DOPISUJ))
        przyciski.rejected.connect(self.reject)
        lay.addWidget(przyciski)

    def _zamknij(self, decyzja):
        self.decyzja = decyzja
        self.accept()

    def nowe_gminy(self):
        """{klucz: nazwa} - gdy decyzja == DOPISZ."""
        wyn = {}
        for w, k in enumerate(self._klucze):
            it = self.tabela.item(w, 2)
            wyn[k] = (it.text().strip() if it else '')[:30]
        return wyn


def zapytaj_o_gminy(parent, tytul, baza, nazwy=None):
    """Sprawdza słownik gmin bazy źródłowej (połączonej). Zwraca:
    {} - nic nie brakuje albo "Nie dopisuj", {klucz: nazwa} - do dopisania,
    None - użytkownik przerwał."""
    brak = R.gminy_spoza_slownika(baza)
    if not brak:
        return {}
    dlg = BrakGminDialog(parent, tytul, brak, nazwy)
    if dlg.exec_() != QDialog.Accepted:
        return None
    return dlg.nowe_gminy() if dlg.decyzja == DOPISZ else {}


def opis_dopisanych(nazwa_bazy, dopisane, nowe_gminy):
    """Linia do raportu."""
    if dopisane is None:
        return (f'{nazwa_bazy}: BŁĄD dopisywania gmin do F_MUNICIPALITY - '
                'szczegóły w logu Las-R')
    return (f'{nazwa_bazy}: dopisano do F_MUNICIPALITY: ' +
            ', '.join(f'{"".join(k)} {nowe_gminy.get(k, "")}'.strip()
                      for k in dopisane))
