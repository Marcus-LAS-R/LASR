from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QWidget,
)


class KorektaGminDialog(QDialog):
    """Dialog korekty MUNICIPALITY_CD dla gmin (F_COMMUNITY), których
    trójka (COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD) nie istnieje w
    słowniku F_MUNICIPALITY bazy docelowej/szablonu. Liczba wierszy jest
    znana dopiero w runtime (zależy od znalezionych niedopasowań), więc
    zbudowany ręcznie w kodzie, bez osobnego pliku ui_*.py - jak
    WyborObrebowDialog w baza_polacz_obreby_dialog.py."""

    def __init__(self, iface, niepasujace, gminy_valid):
        """niepasujace: {(county, district, municip): {nazwa, ...}} - klucze
        (COUNTY_CD, DISTRICT_CD, MUNICIPALITY_CD) starych gmin bez
        odpowiednika w słowniku, wartość to zbiór napotkanych nazw gminy
        (do wyświetlenia). gminy_valid: zbiór (county, district, municip)
        ze słownika F_MUNICIPALITY - do walidacji wpisywanej poprawki."""
        super().__init__(iface.mainWindow())
        self.gminy_valid = gminy_valid
        self.pola = {}  # {(county,district,stary_municip): QLineEdit}

        self.setWindowTitle('Aktualizuj strukturę bazy — korekta gmin')
        self.resize(580, 480)
        layout = QVBoxLayout(self)

        naglowek = QLabel(
            'Poniższe gminy (z F_COMMUNITY starych baz) nie istnieją w '
            'słowniku F_MUNICIPALITY bazy docelowej/szablonu. Podaj '
            'poprawny numer gminy (MUNICIPALITY_CD, 3 cyfry) dla każdej z '
            'nich - zostanie użyty zarówno w tworzonej tabeli F_COMMUNITY, '
            'jak i w adresach leśnych (ADRESS_FOREST) wydzieleń tej gminy.')
        naglowek.setWordWrap(True)
        layout.addWidget(naglowek)

        obszar = QScrollArea()
        obszar.setWidgetResizable(True)
        kontener = QWidget()
        kontener_layout = QVBoxLayout(kontener)

        for klucz in sorted(niepasujace):
            county, district, stary_municip = klucz
            nazwy = ', '.join(sorted(niepasujace[klucz]))
            wiersz = QHBoxLayout()
            etykieta = QLabel(
                county + '/' + district + '/' + stary_municip + ' — ' + nazwy + ':')
            etykieta.setMinimumWidth(300)
            etykieta.setWordWrap(True)
            pole = QLineEdit()
            pole.setMaxLength(3)
            pole.setPlaceholderText('nowy kod')
            pole.setFixedWidth(100)
            pole.textChanged.connect(self._aktualizuj_ok)
            wiersz.addWidget(etykieta)
            wiersz.addWidget(pole)
            kontener_layout.addLayout(wiersz)
            self.pola[klucz] = pole

        kontener_layout.addStretch(1)
        obszar.setWidget(kontener)
        layout.addWidget(obszar, 1)

        self.label_status = QLabel('')
        self.label_status.setWordWrap(True)
        layout.addWidget(self.label_status)

        przyciski = QHBoxLayout()
        self.pushButton_ok = QPushButton('Dalej')
        self.pushButton_ok.setEnabled(False)
        self.pushButton_cancel = QPushButton('Anuluj')
        przyciski.addWidget(self.pushButton_ok)
        przyciski.addWidget(self.pushButton_cancel)
        layout.addLayout(przyciski)

        self.pushButton_ok.clicked.connect(self.accept)
        self.pushButton_cancel.clicked.connect(self.reject)

        self._aktualizuj_ok()

    def _aktualizuj_ok(self, *_):
        ok = True
        bledne = 0
        for (county, district, _stary), pole in self.pola.items():
            nowy = pole.text().strip()
            if nowy == '' or (county, district, nowy) not in self.gminy_valid:
                ok = False
                if nowy != '':
                    bledne += 1
        if bledne:
            self.label_status.setText(
                str(bledne) + ' wpisanych kodów nadal nie istnieje w '
                'słowniku F_MUNICIPALITY.')
        else:
            self.label_status.setText('')
        self.pushButton_ok.setEnabled(ok)

    def wybor(self):
        """Zwraca {(county,district,stary_municip): nowy_municip}."""
        return {
            klucz: pole.text().strip()
            for klucz, pole in self.pola.items()
        }
