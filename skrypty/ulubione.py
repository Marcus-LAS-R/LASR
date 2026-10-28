# -*- coding: utf-8 -*-
"""Ulubione skrypty - submenu na samej górze menu LAS-R.

- dodawanie / usuwanie: PPM na skrypcie w menu LAS-R (także w samych
  Ulubionych) albo okno "Zarządzaj ulubionymi..." (wszystkie skrypty z
  wyszukiwaniem, kolejność przeciąganiem albo ↑ ↓, separatory),
- lista identyfikatorów akcji w ustawieniach profilu QGIS (QgsSettings
  'LasR/ulubione') - przeżywa aktualizację i ponowną instalację wtyczki;
  dawne identyfikatory przepisywane na nowe (indeks_skryptow.nowy_id),
  skrypty usunięte z wtyczki znikają bez błędu,
- domyślnie pusta (podpowiedź w submenu)."""
from PyQt5.QtCore import QEvent, QObject, Qt, QTimer
from PyQt5.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QPushButton, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout,
)
from .przyciski import QDialogButtonBox
from qgis.core import QgsApplication, QgsSettings

from . import indeks_skryptow as ix
from .spis_skryptow import SEP

KLUCZ = 'LasR/ulubione'
SEPARATOR = '-'
TEKST_SEPARATORA = '──────────────'


def wczytaj():
    v = QgsSettings().value(KLUCZ, [])
    if v is None:
        return []
    if isinstance(v, str):
        v = [v] if v else []
    return [SEPARATOR if x == SEPARATOR else ix.nowy_id(str(x)) for x in v]


def zapisz(lista):
    QgsSettings().setValue(KLUCZ, list(lista))


class Ulubione(QObject):
    """Submenu Ulubione + PPM w menu wtyczki."""

    def __init__(self, plugin, menu, daj_spis):
        super().__init__(menu)
        self.plugin = plugin
        self.menu = menu
        self.daj_spis = daj_spis
        self.menu.setToolTipsVisible(True)
        self._menu_z_filtrem = []
        self._podepnij(plugin.menu)
        # przepisanie dawnych identyfikatorów od razu do ustawień
        lista = wczytaj()
        if lista != QgsSettings().value(KLUCZ, []):
            zapisz(lista)
        self.odbuduj()

    # ------------------------------------------------------------- menu

    def _skrypty(self):
        return {w.id: w for w in self.daj_spis()}

    def lista(self):
        """Zapisana lista bez skryptów, których już nie ma."""
        skrypty = self._skrypty()
        return [x for x in wczytaj() if x == SEPARATOR or x in skrypty]

    def odbuduj(self):
        self.menu.clear()
        skrypty = self._skrypty()
        # separator dopiero przed kolejnym skryptem - bez separatorów na
        # początku, na końcu i podwójnych
        dodane = 0
        sep = False
        for x in self.lista():
            if x == SEPARATOR:
                sep = dodane > 0
                continue
            if sep:
                self.menu.addSeparator()
                sep = False
            self.menu.addAction(skrypty[x].akcja)
            dodane += 1
        if not dodane:
            a = self.menu.addAction('(pusto - PPM na skrypcie w menu → '
                                    'Dodaj do ulubionych)')
            a.setEnabled(False)
        self.menu.addSeparator()
        a = self.menu.addAction('Zarządzaj ulubionymi...')
        a.setToolTip('Dodawanie, usuwanie i kolejność ulubionych skryptów')
        a.triggered.connect(self.zarzadzaj)

    def przelacz(self, id_):
        lista = wczytaj()
        if id_ in lista:
            lista.remove(id_)
        else:
            lista.append(id_)
        zapisz(lista)
        # odroczone - PPM mogło przyjść z otwartego właśnie submenu
        QTimer.singleShot(0, self.odbuduj)

    # --------------------------------------------------------------- PPM

    def _podepnij(self, menu):
        menu.installEventFilter(self)
        self._menu_z_filtrem.append(menu)
        for a in menu.actions():
            if a.menu() is not None and a.menu() is not menu:
                self._podepnij(a.menu())

    def sprzataj(self):
        for m in self._menu_z_filtrem:
            try:
                m.removeEventFilter(self)
            except RuntimeError:
                pass
        self._menu_z_filtrem = []

    def eventFilter(self, obiekt, event):
        """PPM na skrypcie w menu: zamiast uruchomienia (QMenu uruchamia
        akcję także prawym przyciskiem) - Dodaj / Usuń z ulubionych."""
        typ = event.type()
        if isinstance(obiekt, QMenu) and typ in (
                QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
                QEvent.ContextMenu):
            if typ != QEvent.ContextMenu and event.button() != Qt.RightButton:
                return False
            akcja = obiekt.actionAt(event.pos())
            id_ = akcja.objectName() if akcja is not None else ''
            if id_ not in self._skrypty():
                return False
            if typ == QEvent.MouseButtonRelease:
                jest = id_ in wczytaj()
                m = QMenu(obiekt)
                m.addAction(
                    QgsApplication.getThemeIcon('/mIconFavorites.svg'),
                    'Usuń z ulubionych' if jest else 'Dodaj do ulubionych',
                    lambda: self.przelacz(id_))
                m.exec_(event.globalPos())
            return True
        return False

    # ------------------------------------------------------------ okno

    def zarzadzaj(self):
        dlg = OknoUlubionych(self.plugin.iface.mainWindow(),
                             self.daj_spis(), self.lista())
        if dlg.exec_() == QDialog.Accepted:
            zapisz(dlg.wynik())
            QTimer.singleShot(0, self.odbuduj)


class OknoUlubionych(QDialog):
    """Lewa strona - wszystkie skrypty (drzewo menu, wyszukiwanie jak w
    pasku QGIS); prawa - ulubione (kolejność przeciąganiem albo ↑ ↓)."""

    def __init__(self, parent, spis, lista):
        super().__init__(parent)
        self.setWindowTitle('Ulubione skrypty Las-R')
        self.spis = spis
        self.po_id = {w.id: w for w in spis}
        glowny = QVBoxLayout(self)
        uklad = QHBoxLayout()
        glowny.addLayout(uklad, 1)

        lewa = QVBoxLayout()
        lewa.addWidget(QLabel('Wszystkie skrypty'))
        self.szukaj = QLineEdit()
        self.szukaj.setPlaceholderText('szukaj: nazwa, dawna nazwa, słowo '
                                       'kluczowe...')
        self.szukaj.setClearButtonEnabled(True)
        self.szukaj.textChanged.connect(self._filtruj)
        lewa.addWidget(self.szukaj)
        self.drzewo = QTreeWidget()
        self.drzewo.setHeaderHidden(True)
        self.drzewo.itemDoubleClicked.connect(lambda *_: self._dodaj())
        lewa.addWidget(self.drzewo, 1)
        uklad.addLayout(lewa, 1)

        srodek = QVBoxLayout()
        srodek.addStretch(1)
        for tekst, f, tip in (
                ('Dodaj →', self._dodaj, 'Dodaj zaznaczony skrypt '
                 '(albo dwuklik)'),
                ('← Usuń', self._usun, 'Usuń z ulubionych (albo Delete)'),
                ('↑', lambda: self._przesun(-1), 'W górę'),
                ('↓', lambda: self._przesun(1), 'W dół'),
                ('Separator', self._separator, 'Dodaj linię oddzielającą')):
            b = QPushButton(tekst)
            b.setToolTip(tip)
            b.clicked.connect(f)
            srodek.addWidget(b)
        srodek.addStretch(1)
        uklad.addLayout(srodek)

        prawa = QVBoxLayout()
        prawa.addWidget(QLabel('Ulubione (kolejność - przeciągnij)'))
        self.lista = QListWidget()
        self.lista.setDragDropMode(QAbstractItemView.InternalMove)
        self.lista.setDefaultDropAction(Qt.MoveAction)
        self.lista.installEventFilter(self)
        prawa.addWidget(self.lista, 1)
        uklad.addLayout(prawa, 1)

        przyciski = QDialogButtonBox(QDialogButtonBox.Ok |
                                     QDialogButtonBox.Cancel)
        przyciski.accepted.connect(self.accept)
        przyciski.rejected.connect(self.reject)
        glowny.addWidget(przyciski)

        self._zbuduj_drzewo()
        for x in lista:
            self._wstaw(x)
        self.resize(820, 520)

    def _zbuduj_drzewo(self):
        grupy = {}
        for w in self.spis:
            czesci = w.sciezka.split(SEP)
            grupa = SEP.join(czesci[:-1]) or 'Menu LAS-R'
            if grupa not in grupy:
                grupy[grupa] = QTreeWidgetItem(self.drzewo, [grupa])
                grupy[grupa].setFlags(Qt.ItemIsEnabled)
            it = QTreeWidgetItem(grupy[grupa], [w.nazwa])
            it.setData(0, Qt.UserRole, w.id)
            if w.tip:
                it.setToolTip(0, w.tip)
        self.drzewo.expandAll()

    def _filtruj(self, tekst):
        pasujace = {w.id for w, _d in ix.szukaj(self.spis, tekst)} \
            if tekst.strip() else None
        for i in range(self.drzewo.topLevelItemCount()):
            grupa = self.drzewo.topLevelItem(i)
            widoczne = 0
            for j in range(grupa.childCount()):
                it = grupa.child(j)
                ok = pasujace is None or it.data(0, Qt.UserRole) in pasujace
                it.setHidden(not ok)
                widoczne += ok
            grupa.setHidden(not widoczne)

    def _wstaw(self, id_, wiersz=None):
        if id_ == SEPARATOR:
            it = QListWidgetItem(TEKST_SEPARATORA)
        else:
            w = self.po_id.get(id_)
            if w is None:
                return
            it = QListWidgetItem(w.nazwa)
            it.setToolTip(w.sciezka)
        it.setData(Qt.UserRole, id_)
        if wiersz is None:
            self.lista.addItem(it)
        else:
            self.lista.insertItem(wiersz, it)
        self.lista.setCurrentItem(it)

    def wynik(self):
        return [self.lista.item(i).data(Qt.UserRole)
                for i in range(self.lista.count())]

    def _dodaj(self):
        it = self.drzewo.currentItem()
        id_ = it.data(0, Qt.UserRole) if it is not None else None
        if not id_:
            return
        if id_ in self.wynik():
            self.lista.setCurrentRow(self.wynik().index(id_))
            return
        r = self.lista.currentRow()
        self._wstaw(id_, r + 1 if r >= 0 else None)

    def _usun(self):
        r = self.lista.currentRow()
        if r >= 0:
            self.lista.takeItem(r)

    def _przesun(self, o):
        r = self.lista.currentRow()
        if r < 0 or not 0 <= r + o < self.lista.count():
            return
        it = self.lista.takeItem(r)
        self.lista.insertItem(r + o, it)
        self.lista.setCurrentRow(r + o)

    def _separator(self):
        r = self.lista.currentRow()
        self._wstaw(SEPARATOR, r + 1 if r >= 0 else None)

    def eventFilter(self, obiekt, event):
        if obiekt is self.lista and event.type() == QEvent.KeyPress and \
                event.key() == Qt.Key_Delete:
            self._usun()
            return True
        return super().eventFilter(obiekt, event)
