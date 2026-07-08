from PyQt5.QtWidgets import QDialog

from .ui.ui_baza_polacz_grupy import Ui_Dialog
from .baza_polacz_rejestr import GRUPA2_DZIECI, GRUPA3_DZIECI

# mapowanie nazwy atrybutu slownika remapu (Laczenie.sl_*) na checkbox,
# ktorego wlasciciel go buduje - uzywane do automatycznego wyprowadzania
# zaleznosci z FK zdefiniowanych w rejestrze
_SLOWNIK_DO_CHECKBOXA = {
    'sl_arodes': 'checkBox_f_arodes',
    'sl_parcel': 'checkBox_f_parcel',
    'sl_addr': 'checkBox_v_address',
}


class WyborGrupDialog(QDialog):
    def __init__(self, iface):
        super().__init__(iface.mainWindow())
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # zaleznosci wyprowadzone automatycznie z FK w rejestrze (nie
        # recznie wypisywane), zeby nie rozjezdzaly sie z rejestrem przy
        # kolejnych dopiskach tabel w przyszlosci
        self._zaleznosci = self._wyprowadz_zaleznosci()

        for nazwa_zalezna, wymagane in self._zaleznosci.items():
            cb = getattr(self.ui, nazwa_zalezna)
            cb.toggled.connect(self._wymus_zaleznosci)
            for w in wymagane:
                getattr(self.ui, w).toggled.connect(self._wymus_zaleznosci)
        self.ui.groupBox_grupa2.toggled.connect(self._wymus_zaleznosci)
        self.ui.groupBox_grupa3.toggled.connect(self._wymus_zaleznosci)

        self.ui.pushButton_ok.clicked.connect(self.accept)
        self.ui.pushButton_cancel.clicked.connect(self.reject)
        self._wymus_zaleznosci()

    def _wyprowadz_zaleznosci(self):
        """{'checkBox_f_arod_land_use': ['checkBox_f_arodes', 'checkBox_f_parcel'], ...}
        - dla kazdej tabeli z >=1 FK wymaganym (wymagane=True), wymaga
        zaznaczenia checkboxa wlasciciela odpowiedniego slownika."""
        zaleznosci = {}
        for t in GRUPA2_DZIECI + GRUPA3_DZIECI:
            wymagane_cb = sorted({
                _SLOWNIK_DO_CHECKBOXA[fk.slownik]
                for fk in t.fk
                if fk.wymagane and fk.slownik in _SLOWNIK_DO_CHECKBOXA
            })
            if wymagane_cb:
                zaleznosci['checkBox_' + t.klucz] = wymagane_cb
        return zaleznosci

    def _spelnione(self, wymagane):
        return all(
            getattr(self.ui, w).isChecked() and getattr(self.ui, w).isEnabled()
            for w in wymagane
        )

    def _wymus_zaleznosci(self, *_):
        # kilka przebiegow - zaleznosci lancuchowe (np. f_arod_land_use
        # zalezy od f_parcel, ktory jest w osobnej grupie) moga wymagac
        # wiecej niz jednego przebiegu do ustabilizowania
        for _ in range(4):
            zmieniono = False
            for nazwa_zalezna, wymagane in self._zaleznosci.items():
                cb = getattr(self.ui, nazwa_zalezna)
                dostepna = self._spelnione(wymagane)
                if cb.isEnabled() != dostepna:
                    cb.setEnabled(dostepna)
                    zmieniono = True
                if not dostepna and cb.isChecked():
                    cb.setChecked(False)
                    zmieniono = True
            if not zmieniono:
                break

    def wybor(self):
        """Zwraca {klucz_tabeli: bool} - efektywny wybor (grupa AND
        tabela), zgodny z kluczami w baza_polacz_rejestr.rejestr_domyslny()."""
        wynik = {
            'f_arodes': self._efektywny('checkBox_f_arodes', 'groupBox_grupa3'),
            'f_parcel': self._efektywny('checkBox_f_parcel', 'groupBox_grupa2'),
            'v_address': self._efektywny('checkBox_v_address', 'groupBox_grupa2'),
        }
        for t in GRUPA2_DZIECI:
            wynik[t.klucz] = self._efektywny('checkBox_' + t.klucz, 'groupBox_grupa2')
        for t in GRUPA3_DZIECI:
            wynik[t.klucz] = self._efektywny('checkBox_' + t.klucz, 'groupBox_grupa3')
        return wynik

    def _efektywny(self, nazwa_cb, nazwa_grupy):
        return (
            getattr(self.ui, nazwa_grupy).isChecked() and
            getattr(self.ui, nazwa_cb).isChecked()
        )
