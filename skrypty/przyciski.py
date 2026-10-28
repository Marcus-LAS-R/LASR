# -*- coding: utf-8 -*-
"""Polskie napisy na standardowych przyciskach okien wtyczki.

Standardowe przyciski Qt (Yes, No, Cancel, Abort...) tłumaczy QGIS, ale
tylko przy polskim interfejsie - przy angielskim (userLocale=en_US) wtyczka
pokazywała "Yes/Abort". Ładowanie qtbase_pl.qm zmieniłoby język całego
QGIS-a, więc wtyczka sama podmienia napisy na swoich oknach.

Moduł daje klasy o tych samych nazwach co w Qt - wystarczy import:
    from .przyciski import QMessageBox, QDialogButtonBox, QInputDialog
- QMessageBox: statyczne question/warning/information/critical i instancje
  (napisy podmieniane przy pokazaniu okna),
- QDialogButtonBox: napisy podmieniane przy pokazaniu,
- QInputDialog: statyczne getItem/getText z OK/Anuluj.
Podmieniany jest tylko napis domyślny (angielski albo z tłumaczenia Qt) -
własne etykiety (setText("Przygotuj"), addButton("Kontynuuj")) zostają.

Słownik przycisków wtyczki (ujednolicony):
- pytanie: Tak / Nie (pytanie o nadpisanie: Tak / Przerwij),
- ostrzeżenie w trakcie procesu: Kontynuuj / Przerwij,
- okno startowe: czynność (Uruchom, Przygotuj...) / Anuluj,
- informacja: OK albo Zamknij (Zamknij i pokaż raport).
"""
from qgis.PyQt import QtWidgets

_MB = QtWidgets.QMessageBox
_BB = QtWidgets.QDialogButtonBox

# nazwa przycisku standardowego (wspólna dla QMessageBox i QDialogButtonBox)
ETYKIETY = {
    'Ok': 'OK',
    'Save': 'Zapisz',
    'SaveAll': 'Zapisz wszystko',
    'Open': 'Otwórz',
    'Yes': 'Tak',
    'YesToAll': 'Tak dla wszystkich',
    'No': 'Nie',
    'NoToAll': 'Nie dla wszystkich',
    'Abort': 'Przerwij',
    'Retry': 'Ponów',
    'Ignore': 'Pomiń',
    'Close': 'Zamknij',
    'Cancel': 'Anuluj',
    'Discard': 'Odrzuć',
    'Help': 'Pomoc',
    'Apply': 'Zastosuj',
    'Reset': 'Resetuj',
    'RestoreDefaults': 'Przywróć domyślne',
}

# napisy domyślne Qt (angielskie i z polskiego tłumaczenia Qt) - tylko je
# podmieniamy, żeby nie ruszać własnych etykiet
_DOMYSLNE = {
    'ok', 'save', 'save all', 'open', 'yes', 'yes to all', 'no',
    'no to all', 'abort', 'retry', 'ignore', 'close', 'cancel', 'discard',
    "don't save", 'close without saving', 'help', 'apply', 'reset',
    'restore defaults',
    'zapisz', 'zapisz wszystko', 'otwórz', 'tak', 'tak dla wszystkich',
    'nie', 'nie dla wszystkich', 'przerwij', 'ponów', 'zignoruj', 'pomiń',
    'zamknij', 'anuluj', 'odrzuć', 'nie zapisuj', 'zamknij bez zapisywania',
    'pomoc', 'zastosuj', 'resetuj', 'przywróć domyślne', 'przywróć domyślnie',
}


def _po_polsku(klasa):
    return {int(getattr(klasa, n)): t for n, t in ETYKIETY.items()}


_PL_MB = _po_polsku(_MB)
_PL_BB = _po_polsku(_BB)


def _domyslny(tekst):
    return tekst.replace('&', '').strip().lower() in _DOMYSLNE


def spolszcz(okno):
    """Polskie napisy na standardowych przyciskach QMessageBox albo
    QDialogButtonBox (także zwykłych klas Qt, np. z plików ui_*.py)."""
    if isinstance(okno, _MB):
        slownik = _PL_MB
    elif isinstance(okno, _BB):
        slownik = _PL_BB
    else:
        return okno
    for b in okno.buttons():
        tekst = slownik.get(int(okno.standardButton(b)))
        if tekst and _domyslny(b.text()):
            b.setText(tekst)
    return okno


class QMessageBox(_MB):

    def showEvent(self, zdarzenie):
        spolszcz(self)
        super().showEvent(zdarzenie)

    @staticmethod
    def _okno(ikona, parent, title, text, buttons, defaultButton):
        okno = QMessageBox(ikona, title, text, buttons, parent)
        if defaultButton != _MB.NoButton:
            okno.setDefaultButton(defaultButton)
        return _MB.StandardButton(okno.exec_())

    @staticmethod
    def question(parent, title, text,
                 buttons=_MB.StandardButtons(_MB.Yes | _MB.No),
                 defaultButton=_MB.NoButton):
        return QMessageBox._okno(_MB.Question, parent, title, text, buttons,
                                 defaultButton)

    @staticmethod
    def information(parent, title, text, buttons=_MB.Ok,
                    defaultButton=_MB.NoButton):
        return QMessageBox._okno(_MB.Information, parent, title, text,
                                 buttons, defaultButton)

    @staticmethod
    def warning(parent, title, text, buttons=_MB.Ok,
                defaultButton=_MB.NoButton):
        return QMessageBox._okno(_MB.Warning, parent, title, text, buttons,
                                 defaultButton)

    @staticmethod
    def critical(parent, title, text, buttons=_MB.Ok,
                 defaultButton=_MB.NoButton):
        return QMessageBox._okno(_MB.Critical, parent, title, text, buttons,
                                 defaultButton)


class QDialogButtonBox(_BB):

    def showEvent(self, zdarzenie):
        spolszcz(self)
        super().showEvent(zdarzenie)


class QInputDialog(QtWidgets.QInputDialog):

    @staticmethod
    def _okno(parent, title, label):
        d = QtWidgets.QInputDialog(parent)
        d.setWindowTitle(title)
        d.setLabelText(label)
        d.setOkButtonText('OK')
        d.setCancelButtonText('Anuluj')
        return d

    @staticmethod
    def getItem(parent, title, label, items, current=0, editable=True,
                *args, **kwargs):
        d = QInputDialog._okno(parent, title, label)
        items = list(items)
        d.setComboBoxItems(items)
        d.setComboBoxEditable(editable)
        if items and 0 <= current < len(items):
            d.setTextValue(items[current])
        ok = d.exec_() == QtWidgets.QDialog.Accepted
        return (d.textValue() if ok else
                (items[current] if items and 0 <= current < len(items)
                 else '')), ok

    @staticmethod
    def getText(parent, title, label, echo=QtWidgets.QLineEdit.Normal,
                text='', *args, **kwargs):
        d = QInputDialog._okno(parent, title, label)
        d.setTextEchoMode(echo)
        d.setTextValue(text)
        ok = d.exec_() == QtWidgets.QDialog.Accepted
        return (d.textValue() if ok else ''), ok
