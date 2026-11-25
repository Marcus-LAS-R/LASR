# -*- coding: utf-8 -*-
"""Przebieg prac - panel z kolejnymi krokami trzech procesów (Przygotowanie
danych, Rozliczenie powierzchni, Aktualizacja UPUL), po prawej stronie,
otwierany z menu ("Przebieg prac" nad Edytorem opisu).

- przycisk kroku uruchamia TĘ SAMĄ akcję co menu (identyfikator akcji =
  nazwa atrybutu w las_r.py, jak w Ulubionych / wyszukiwarce),
- ptaszek przy kroku zaznacza się przy uruchomieniu: z panelu - w tej
  zakładce, z menu / wyszukiwarki - w każdym procesie, w którym skrypt
  jest krokiem; kontrole, narzędzia i opcjonalne bez automatycznego
  ptaszka; kliknięcie w ptaszek przełącza go ręcznie; krok można puścić
  ponownie; "Wyczyść postęp" - osobno dla zakładki,
- stan w projekcie QGIS (.qgz, wpis 'LasR' / 'przebieg_<proces>') - po
  zmianie projekt oznaczony jako zmieniony, przy innym projekcie panel
  pokazuje jego postęp.

Kolejność kroków - lista PROCESY niżej (zmiana bez ruszania kodu)."""
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import (
    QCheckBox, QDockWidget, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSizePolicy, QStackedWidget, QStyle, QStyleOptionButton,
    QTabWidget, QToolButton, QVBoxLayout, QWidget,
)
from qgis.core import QgsProject

KROK, KONTROLA, NARZEDZIE, OPCJA = 'krok', 'kontrola', 'narzedzie', 'opcja'
PODPIS = {KONTROLA: 'kontrola', NARZEDZIE: 'narzędzie'}


def _k(*ids):
    return [(KROK, i) for i in ids]


# (id procesu, nazwa zakładki, [(nagłówek części albo None, [(typ, id)])])
PROCESY = [
    ('przygotowanie', 'Przygotowanie danych', [
        (None, _k('a_utworz_baze_gml', 'kas_op', 'kas_niels',
                  'spr_popraw_ls', 'a_eksport_shp_gml', 'przyg_dzewid',
                  'przyg_ls_test', 'a_snapuj_nowy', 'przyg_teren',
                  'a_przyg_dla_taksatora')),
        ('Kontrole', [(KONTROLA, 'dop_dzkat'), (KONTROLA, 'spr_kontr_ls')]),
        ('Opcjonalne', [(OPCJA, 'a_przygotuj_baze_ewid'),
                        (OPCJA, 'przyg_ls_wydz')]),
    ]),
    ('rozliczenie', 'Rozliczenie powierzchni', [
        ('Cięcie i przygotowanie bazy',
         _k('lacz_karty', 'przyg_ciec', 'a_usun_nadm_adr')
         + [(KONTROLA, 'przyg_klep')]
         + _k('zanum', 'dop_w_o', 'zalit', 'dop_adrles', 'dopisz_wydz',
              'rozlicz_wydz', 'dop_pnsw', 'przyg_rap')),
        ('Poprawa i uzupełnienie bazy',
         _k('a_fstspec', 'klon', 'a_dop_ros', 'dop_fo', 'dop_zab_nowe')),
        ('Opcjonalne / naprawcze', [(OPCJA, 'kasr'), (OPCJA, 'kasw'),
                                    (OPCJA, 'dolit'), (OPCJA, 'przelit')]),
    ]),
    ('aktualizacja', 'Aktualizacja UPUL', [
        ('Aktualizacja bazy i tworzenie DOTAKS',
         _k('a_aktualizacja_baz', 'a_przyg_dotaks')),
        ('Cięcie i uzupełnienie bazy',
         _k('a_przyg_stare_wydz')
         + [(NARZEDZIE, 'a_warstwa_opisow'),
            (KONTROLA, 'a_sprawdz_polozenie_opisow')]
         + _k('a_dopisz_dane_wydz', 'a_dop_adrles_stare_wydz',
              'a_synchronizuj_wydz', 'a_dop_w_o_upul', 'a_dolit_upul',
              'a_dop_adrles_upul', 'a_uzup_wydz_nowe',
              'a_dopisz_opisy_taks', 'a_utworz_klon_txt', 'klon')),
        ('Opcjonalne', [(OPCJA, 'a_aktualizuj_strukture'),
                        (OPCJA, 'a_aktualizacja_shp'),
                        (OPCJA, 'a_pobierz_bdl'),
                        (OPCJA, 'a_utworz_baze_bdl'),
                        (OPCJA, 'a_usun_nadm_adr')]),
    ]),
]

ZAKRES = 'LasR'

ZIELONY = '#d9f2d9'
NASTEPNY = '#1f5fa8'
NAGLOWEK = '#e4ecf5'
KONTROLNY = '#fff3d6'


def wszystkie_id():
    return {i for _p, _n, czesci in PROCESY for _t, poz in czesci
            for _typ, i in poz}


def kroki_procesu(proces):
    """Identyfikatory kroków (auto-ptaszek) procesu w kolejności."""
    return [i for p, _n, czesci in PROCESY if p == proces
            for _t, poz in czesci for typ, i in poz if typ == KROK]


# ------------------------------------------------------- stan w projekcie

def wczytaj_stan(proces):
    lista, _ok = QgsProject.instance().readListEntry(
        ZAKRES, f'przebieg_{proces}')
    return set(lista or [])


def zapisz_stan(proces, wykonane):
    # writeEntry oznacza projekt jako zmieniony
    QgsProject.instance().writeEntry(ZAKRES, f'przebieg_{proces}',
                                     sorted(wykonane))


# ------------------------------------------------------------ zwijanie

SZER_ZWINIETEGO = 26
QWIDGETSIZE_MAX = 16777215


class PasekZwiniety(QPushButton):
    """Wąski pionowy pasek z obróconym tytułem - kliknięcie rozwija panel."""

    def __init__(self, tytul, parent=None):
        super().__init__(parent)
        self._tytul = tytul
        self.setToolTip(f'Rozwiń panel "{tytul}"')
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(SZER_ZWINIETEGO)

    def sizeHint(self):
        return QSize(SZER_ZWINIETEGO, 200)

    def minimumSizeHint(self):
        return QSize(SZER_ZWINIETEGO, 60)

    def paintEvent(self, _ev):
        p = QPainter(self)
        opt = QStyleOptionButton()
        self.initStyleOption(opt)
        opt.text = ''
        self.style().drawControl(QStyle.CE_PushButton, opt, p, self)
        f = p.font()
        f.setBold(True)
        p.setFont(f)
        # tekst od góry do dołu (obrót o 90 st. w prawo)
        p.translate(self.width(), 0)
        p.rotate(90)
        p.drawText(8, 0, self.height() - 16, self.width(),
                   Qt.AlignLeft | Qt.AlignVCenter, '▾  ' + self._tytul)
        # (▾ po obrocie o 90 st. wskazuje w lewo - kierunek rozwinięcia)
        p.end()


class PasekTytulu(QWidget):
    """Pasek tytułu panelu: tytuł + Zwiń / Odepnij / Zamknij. Puste
    miejsce przepuszcza mysz do QDockWidget (przeciąganie panelu)."""

    def __init__(self, dock, tytul):
        super().__init__(dock)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 2, 2)
        lay.setSpacing(1)
        lbl = QLabel(tytul)
        lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay.addWidget(lbl, 1)
        styl = dock.style()

        def przycisk(ikona, tip, slot, tekst=None):
            b = QToolButton(self)
            if tekst:
                b.setText(tekst)
            else:
                b.setIcon(styl.standardIcon(ikona))
            b.setToolTip(tip)
            b.setAutoRaise(True)
            b.setFixedSize(20, 20)
            b.clicked.connect(slot)
            lay.addWidget(b)
            return b

        self.btn_zwin = przycisk(None, 'Zwiń panel do wąskiego paska',
                                 dock.zwin, tekst='▸')
        przycisk(QStyle.SP_TitleBarNormalButton, 'Odepnij / przypnij panel',
                 lambda: dock.setFloating(not dock.isFloating()))
        przycisk(QStyle.SP_TitleBarCloseButton, 'Zamknij panel', dock.close)


# ------------------------------------------------------------------ panel

class PanelPrzebiegu(QDockWidget):
    """Zakładki procesów; akcje skryptów z daj_akcje() -> {id: QAction}."""

    TYTUL = 'Przebieg prac'

    def __init__(self, iface, daj_akcje):
        super().__init__(self.TYTUL, iface.mainWindow())
        self.setObjectName('LasR_PrzebiegPrac')
        self.iface = iface
        self.akcje = daj_akcje()
        self._z_panelu = None   # proces, z którego zakładki puszczono krok
        self._wiersze = {}      # proces -> [(typ, id, nr, ptaszek, przycisk)]
        self.zakladki = QTabWidget()
        self.zakladki.setDocumentMode(True)
        # zwijanie: stos [zakładki, pionowy pasek] + własny pasek tytułu
        self._zwiniety = False
        self._szer_rozwiniety = 0
        self.pasek = PasekZwiniety(self.TYTUL)
        self.pasek.clicked.connect(self.rozwin)
        self.stos = QStackedWidget()
        self.stos.addWidget(self.zakladki)
        self.stos.addWidget(self.pasek)
        self.setWidget(self.stos)
        self.tytul_pelny = PasekTytulu(self, self.TYTUL)
        self.tytul_pusty = QWidget(self)   # zwinięty - bez paska tytułu
        self.tytul_pusty.setFixedHeight(0)
        self.tytul_pusty.hide()
        self.setTitleBarWidget(self.tytul_pelny)
        # odpięty panel się nie zwija (zwinięcie dotyczy krawędzi okna)
        self.topLevelChanged.connect(self._zmiana_odpiecia)
        for proces, nazwa, czesci in PROCESY:
            self.zakladki.addTab(self._zakladka(proces, czesci), nazwa)
        # ptaszek także przy uruchomieniu z menu / wyszukiwarki
        self._podpiete = []
        for id_ in wszystkie_id():
            a = self.akcje.get(id_)
            if a is not None:
                f = (lambda _c=False, i=id_: self._uruchomiono(i))
                a.triggered.connect(f)
                self._podpiete.append((a, f))
        prj = QgsProject.instance()
        prj.readProject.connect(self.odswiez)
        prj.cleared.connect(self.odswiez)
        self.odswiez()

    # ----------------------------------------------------------- zwijanie

    def zwin(self):
        if self._zwiniety or self.isFloating():
            return
        self._zwiniety = True
        self._szer_rozwiniety = self.width()
        self.tytul_pelny.hide()
        self.setTitleBarWidget(self.tytul_pusty)
        self.stos.setCurrentWidget(self.pasek)
        self.setMinimumWidth(SZER_ZWINIETEGO)
        self.setMaximumWidth(SZER_ZWINIETEGO)

    def rozwin(self):
        if not self._zwiniety:
            return
        self._zwiniety = False
        self.setMinimumWidth(0)
        self.setMaximumWidth(QWIDGETSIZE_MAX)
        self.stos.setCurrentWidget(self.zakladki)
        self.tytul_pusty.hide()
        self.setTitleBarWidget(self.tytul_pelny)
        self.tytul_pelny.show()
        if self._szer_rozwiniety > SZER_ZWINIETEGO and not self.isFloating():
            okno = self.iface.mainWindow()
            okno.resizeDocks([self], [self._szer_rozwiniety], Qt.Horizontal)

    def _zmiana_odpiecia(self, odpiety):
        if odpiety:
            self.rozwin()
        self.tytul_pelny.btn_zwin.setEnabled(not odpiety)

    # ------------------------------------------------------------- budowa

    def _zakladka(self, proces, czesci):
        tresc = QWidget()
        lay = QVBoxLayout(tresc)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(3)
        wiersze = []
        nr = 0
        for tytul, pozycje in czesci:
            if tytul:
                lbl = QLabel(tytul)
                f = lbl.font()
                f.setBold(True)
                lbl.setFont(f)
                lbl.setStyleSheet(f'background: {NAGLOWEK}; color: #1a2a3a; '
                                  'padding: 3px 6px; border-radius: 3px;')
                lay.addSpacing(4)
                lay.addWidget(lbl)
            for typ, id_ in pozycje:
                if typ == KROK:
                    nr += 1
                w = self._wiersz(proces, typ, id_, nr if typ == KROK else None)
                wiersze.append(w)
                lay.addLayout(w[5])
        lay.addSpacing(8)
        btn = QPushButton('Wyczyść postęp')
        btn.setToolTip('Usuwa wszystkie ptaszki w tej zakładce (projekt '
                       'zostanie oznaczony jako zmieniony)')
        btn.clicked.connect(lambda _c=False, p=proces: self.wyczysc(p))
        lay.addWidget(btn, 0, Qt.AlignLeft)
        lay.addStretch(1)
        self._wiersze[proces] = wiersze
        przewijanie = QScrollArea()
        przewijanie.setWidgetResizable(True)
        przewijanie.setFrameShape(QFrame.NoFrame)
        przewijanie.setWidget(tresc)
        return przewijanie

    def _wiersz(self, proces, typ, id_, nr):
        akcja = self.akcje.get(id_)
        wiersz = QHBoxLayout()
        wiersz.setSpacing(4)
        if typ in (KONTROLA, NARZEDZIE):
            wiersz.addSpacing(18)  # wcięcie - punkt między krokami
        ptaszek = QCheckBox()
        ptaszek.setToolTip('Wykonano - kliknij, żeby zaznaczyć / odznaczyć '
                           'ręcznie')
        ptaszek.clicked.connect(
            lambda stan, p=proces, i=id_: self.oznacz(p, i, stan))
        wiersz.addWidget(ptaszek)
        lbl_nr = QLabel(f'{nr}.' if nr else '')
        lbl_nr.setFixedWidth(22)
        lbl_nr.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        wiersz.addWidget(lbl_nr)
        tekst = akcja.text().replace('&', '') if akcja is not None else id_
        if typ in PODPIS:
            tekst = f'▸ {tekst}  ({PODPIS[typ]})'
        btn = QPushButton(tekst)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn.setStyleSheet('text-align: left; padding: 3px 6px;')
        if akcja is None:
            btn.setEnabled(False)
            btn.setToolTip('Skryptu nie ma w tej wersji wtyczki')
        else:
            tip = akcja.toolTip()
            btn.setToolTip(tip if tip != akcja.text() else '')
            btn.clicked.connect(
                lambda _c=False, p=proces, a=akcja: self._uruchom(p, a))
        wiersz.addWidget(btn, 1)
        return (typ, id_, nr, ptaszek, btn, wiersz)

    # ------------------------------------------------------------- stan

    def _uruchom(self, proces, akcja):
        """Przycisk panelu: ptaszek tylko w tej zakładce (flaga sprawdzana
        w _uruchomiono, wołanym synchronicznie przez trigger)."""
        self._z_panelu = proces
        try:
            akcja.trigger()
        finally:
            self._z_panelu = None

    def _uruchomiono(self, id_):
        procesy = [self._z_panelu] if self._z_panelu else \
            [p for p, _n, _c in PROCESY]
        for p in procesy:
            if id_ in kroki_procesu(p):
                self.oznacz(p, id_, True)

    def oznacz(self, proces, id_, stan):
        wykonane = wczytaj_stan(proces)
        if (id_ in wykonane) == bool(stan):
            self.odswiez()
            return
        if stan:
            wykonane.add(id_)
        else:
            wykonane.discard(id_)
        zapisz_stan(proces, wykonane)
        self.odswiez()

    def wyczysc(self, proces):
        if wczytaj_stan(proces):
            zapisz_stan(proces, set())
        self.odswiez()

    def odswiez(self, *_args):
        for proces, wiersze in self._wiersze.items():
            wykonane = wczytaj_stan(proces)
            nastepny = next((i for i in kroki_procesu(proces)
                             if i not in wykonane), None)
            for typ, id_, _nr, ptaszek, btn, _w in wiersze:
                zrobione = id_ in wykonane
                ptaszek.setChecked(zrobione)
                styl = 'text-align: left; padding: 3px 6px;'
                if zrobione:
                    styl += f' background: {ZIELONY}; color: #1b3d1b;'
                elif typ == KROK and id_ == nastepny:
                    styl += (f' border: 2px solid {NASTEPNY}; '
                             'font-weight: bold;')
                elif typ in (KONTROLA, NARZEDZIE):
                    styl += f' background: {KONTROLNY}; color: #4a3a10;'
                btn.setStyleSheet(styl)

    # ---------------------------------------------------------- sprzątanie

    def sprzataj(self):
        for a, f in self._podpiete:
            try:
                a.triggered.disconnect(f)
            except (TypeError, RuntimeError):
                pass
        self._podpiete = []
        prj = QgsProject.instance()
        for sygnal in (prj.readProject, prj.cleared):
            try:
                sygnal.disconnect(self.odswiez)
            except (TypeError, RuntimeError):
                pass
