import os
import shutil
import tempfile
import platform
from datetime import date, datetime
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from qgis.core import Qgis, QgsMessageLog
from .baza_wrapper import Baza
from .pw import PasekPostepu

_SZABLONY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'szablony')
_BAZA_KONTROLI = os.path.join(_SZABLONY_DIR, 'baza_kontroli_upul.mdb')

_MAPA_PU_BAZA_KONTROLI = os.path.join(
    os.path.expanduser('~'),
    'AppData', 'Roaming', 'QGIS', 'QGIS3', 'profiles', 'default',
    'python', 'plugins', 'Mapa_PU', 'szablony', 'baza_kontroli_upul.mdb'
)


class _Kolumna:
    """Nazwa kolumny z szablonu opisu błędu (@kolumna → standaryzowana)."""
    def __init__(self, name: str):
        self.name = name.replace('.', '').replace(',', '')
        self.standardized = name.replace('.', '').replace(',', '').replace('@', '').upper()


class _Sql:
    def __init__(self, kolejnosc: int, query: str):
        self.kolejnosc = kolejnosc
        self.query = query.replace('"', "'")


class _KontrolaOpisu:
    def __init__(self, id_: int, nazwa: str, opis_bledu: str, dodatkowa: bool):
        self.id = id_
        self.nazwa = nazwa
        self.opis_bledu = opis_bledu
        self.dodatkowa = dodatkowa
        self.queries = []
        self.errors = []

    @property
    def is_error(self):
        return len(self.errors) > 0

    def dodaj_sql(self, sql: _Sql):
        self.queries.append(sql)


def _formatuj_blad(wiersz, opis: str) -> str:
    """Zamienia @nazwa_kolumny w szablonie opisu na wartości z wiersza
    (wg metodologii Mapa PU: cursor_description pyodbc).
    """
    try:
        kol_szabl = [_Kolumna(n) for n in opis.split() if n.startswith('@')]
        kol_wiersz = [_Kolumna(n[0]) for n in wiersz.cursor_description]
        idx_adres = [i for i, k in enumerate(kol_wiersz)
                     if k.standardized.startswith('ADRES')]
        for kol in kol_szabl:
            idx = [i for i, k in enumerate(kol_wiersz)
                   if k.standardized == kol.standardized]
            if idx:
                val = wiersz[idx[0]]
                opis = opis.replace(kol.name, str(val) if val is not None else '')
        if idx_adres:
            return f'Adres: {wiersz[idx_adres[0]]}  Opis: {opis}'
        return f'Opis: {opis}'
    except Exception as e:
        return f'[błąd formatowania: {e}]'


def _zaladuj_kontrole(baza_kontroli: Baza) -> list:
    """Pobiera aktywne kontrole z bazy_kontroli_upul.mdb."""
    sql = (
        "SELECT grupy_kontroli.id, kontrole.id, kwerendy_kontroli.kolejnoscwykonania, "
        "kontrole.nazwa, kwerendy_kontroli.nazwa, kwerendy_kontroli.sql_access, "
        "kontrole.opisbledu, kontrole.dodatkowa "
        "FROM (grupy_kontroli INNER JOIN kontrole "
        "  ON grupy_kontroli.id = kontrole.idgrupykontroli) "
        "INNER JOIN kwerendy_kontroli "
        "  ON kontrole.id = kwerendy_kontroli.idkontrole "
        "WHERE (((kwerendy_kontroli.sql_access) Is Not Null) "
        "  AND ((kontrole.aktywna)=True)) "
        "ORDER BY grupy_kontroli.kolejnoscwykonania, kontrole.kolejnoscwykonania, "
        "kwerendy_kontroli.kolejnoscwykonania;"
    )
    wiersze = baza_kontroli.pobierz(sql)
    if not wiersze:
        return []
    lista = []
    for w in wiersze:
        kontrola = next((k for k in lista if k.id == w[1]), None)
        if kontrola is None:
            kontrola = _KontrolaOpisu(w[1], w[3], w[6], bool(w[7]))
            lista.append(kontrola)
        kontrola.dodaj_sql(_Sql(w[2], w[5]))
    return lista


def _wykonaj_kontrole(baza_upul: Baza, kontrole: list, pasek) -> None:
    """Uruchamia wszystkie kontrole na kopii bazy UPUL."""
    n = len(kontrole)
    for i, kontrola in enumerate(kontrole):
        if pasek:
            pasek.setValue(int((i / n) * 100))
        count = len(kontrola.queries)
        for sql in kontrola.queries:
            try:
                if sql.kolejnosc == count:
                    baza_upul.cur.execute(sql.query)
                    for w in baza_upul.cur.fetchall():
                        kontrola.errors.append(
                            _formatuj_blad(w, kontrola.opis_bledu)
                        )
                else:
                    baza_upul.cur.execute(sql.query)
                    baza_upul.con.commit()
            except Exception as e:
                QgsMessageLog.logMessage(
                    f'Kontrola opisów [{kontrola.nazwa}]: {e}',
                    'Las-R', Qgis.Warning
                )


def _zapisz_raport(kontrole: list, baza_sc: str,
                   baza_kontroli_sc: str, czas: str) -> str:
    nazwa_bazy = os.path.splitext(os.path.basename(baza_sc))[0]
    rap_sc = os.path.join(
        os.path.dirname(baza_sc),
        f'kontrola_opisow_{nazwa_bazy}_{czas}.txt'
    )
    lp = '=' * 72
    l  = '-' * 72
    nl = '\r\n'

    obligatoryjne = [k for k in kontrole if not k.dodatkowa]
    pomocnicze    = [k for k in kontrole if k.dodatkowa]

    with open(rap_sc, 'w', encoding='utf-8') as plik:
        plik.write(f'KONTROLA OPISU TAKSACYJNEGO{nl}')
        plik.write(lp + nl)
        plik.write(f'Baza UPUL:     {baza_sc}{nl}')
        plik.write(f'Baza kontroli: {baza_kontroli_sc}{nl}')
        plik.write(f'Data:          {date.today()}{nl}')
        plik.write(lp + nl + nl)

        for sekcja, lista in (('OBLIGATORYJNE', obligatoryjne),
                               ('POMOCNICZE',    pomocnicze)):
            if not lista:
                continue
            plik.write(lp + nl)
            plik.write(f'KONTROLE {sekcja}{nl}')
            plik.write(lp + nl)
            for k in lista:
                plik.write(l + nl)
                plik.write(f'{k.nazwa}{nl}')
                plik.write(l + nl)
                plik.write(
                    f'Wynik: {"OK" if not k.is_error else "Stwierdzono błędy"}{nl}'
                )
                for blad in k.errors:
                    plik.write(f'  {blad}{nl}')

        ile_k    = len(kontrole)
        ile_err  = sum(1 for k in kontrole if k.is_error)
        ile_wier = sum(len(k.errors) for k in kontrole)
        plik.write(nl + lp + nl)
        plik.write(
            f'Wykonano kontroli: {ile_k} | Z błędami: {ile_err} | '
            f'Błędnych wierszy łącznie: {ile_wier}{nl}'
        )

    return rap_sc


def _sprawdz_aktualizacje(iface) -> bool:
    """Porównuje mtime bazy kontroli w szablony/ z wersją w Mapa_PU.
    Zwraca False jeśli użytkownik wybrał Porzuć — wtedy KontrolaOpisow kończy działanie.
    """
    if not os.path.exists(_BAZA_KONTROLI) or not os.path.exists(_MAPA_PU_BAZA_KONTROLI):
        return True

    mtime_local  = os.path.getmtime(_BAZA_KONTROLI)
    mtime_mapaPU = os.path.getmtime(_MAPA_PU_BAZA_KONTROLI)

    if mtime_local == mtime_mapaPU:
        return True

    dt_local  = datetime.fromtimestamp(mtime_local).strftime('%Y-%m-%d %H:%M')
    dt_mapaPU = datetime.fromtimestamp(mtime_mapaPU).strftime('%Y-%m-%d %H:%M')
    czy_nowsza = 'nowsza' if mtime_mapaPU > mtime_local else 'starsza'

    msg = QMessageBox(iface.mainWindow())
    msg.setIcon(QMessageBox.Question)
    msg.setWindowTitle('Baza kontroli — inna wersja')
    msg.setText(
        f'We wtyczce Mapa_PU znajduje się inna baza kontrolna opisu taksacyjnego\n'
        f'({czy_nowsza}: Mapa_PU {dt_mapaPU}, bieżąca {dt_local}).\n\n'
        f'Czy skopiować tę bazę do szablonu kontroli?'
    )
    btn_tak  = msg.addButton('Tak',    QMessageBox.AcceptRole)
    btn_nie  = msg.addButton('Nie',    QMessageBox.RejectRole)
    btn_por  = msg.addButton('Porzuć', QMessageBox.DestructiveRole)
    btn_tak.setToolTip('Zarchiwizuj bieżącą bazę i skopiuj wersję z Mapa_PU')
    btn_nie.setToolTip('Kontynuuj kontrolę wg bieżącej bazy w szablonach')
    btn_por.setToolTip('Przerwij działanie skryptu')
    msg.exec_()

    klikniety = msg.clickedButton()

    if klikniety == btn_nie:
        return True

    if klikniety != btn_tak:
        return False

    # TAK — kopia zapasowa bieżącej + kopiuj z Mapa_PU
    znacznik  = datetime.now().strftime('%d-%m-%Y')
    backup_sc = os.path.join(_SZABLONY_DIR, f'baza_kontroli_upul_{znacznik}.mdb')
    try:
        shutil.copy2(_BAZA_KONTROLI, backup_sc)
        shutil.copy2(_MAPA_PU_BAZA_KONTROLI, _BAZA_KONTROLI)
        iface.messageBar().pushMessage(
            'LASR',
            f'Skopiowano bazę z Mapa_PU. Kopia zapasowa: {os.path.basename(backup_sc)}',
            Qgis.Success, 8
        )
    except Exception as e:
        iface.messageBar().pushMessage(
            'BŁĄD', f'Nie udało się zaktualizować bazy kontroli: {e}',
            Qgis.Critical, 10
        )
        return False

    return True


def KontrolaOpisow(iface):
    if not _sprawdz_aktualizacje(iface):
        return

    # wybór bazy UPUL
    baza_sc = QFileDialog().getOpenFileName(
        iface.mainWindow(),
        'Wskaż bazę Taksatora (UPUL)',
        '',
        'Access MDB (*.mdb)',
    )[0]
    if not baza_sc:
        return

    # auto-find baza kontroli; jeśli brak — dialog
    baza_kontroli_sc = _BAZA_KONTROLI
    if not os.path.exists(baza_kontroli_sc):
        baza_kontroli_sc = QFileDialog().getOpenFileName(
            iface.mainWindow(),
            'Wskaż bazę kontroli (baza_kontroli_upul.mdb)',
            '',
            'Access MDB (*.mdb)',
        )[0]
        if not baza_kontroli_sc:
            return

    # załaduj kontrole z bazy kontroli
    baza_kontroli = Baza(baza_kontroli_sc)
    if not baza_kontroli.polacz():
        iface.messageBar().pushMessage(
            'BŁĄD', f'Nie można połączyć się z bazą kontroli: {baza_kontroli_sc}',
            Qgis.Critical, 10
        )
        return

    kontrole = _zaladuj_kontrole(baza_kontroli)
    baza_kontroli.zamknij()

    if not kontrole:
        iface.messageBar().pushMessage(
            'BŁĄD', 'Baza kontroli nie zawiera żadnych aktywnych kontroli.',
            Qgis.Warning, 10
        )
        return

    # kopia bazy UPUL do tmp
    tmp_dir = tempfile.mkdtemp(prefix='lasr_kontrola_')
    tmp_baza = os.path.join(tmp_dir, os.path.basename(baza_sc))
    try:
        shutil.copy2(baza_sc, tmp_baza)
    except Exception as e:
        iface.messageBar().pushMessage(
            'BŁĄD', f'Nie można skopiować bazy do tmp: {e}',
            Qgis.Critical, 10
        )
        return

    # połącz z kopią
    baza_upul = Baza(tmp_baza)
    czas = baza_upul.czas
    if not baza_upul.polacz():
        iface.messageBar().pushMessage(
            'BŁĄD', f'Nie można połączyć się z kopią bazy: {tmp_baza}',
            Qgis.Critical, 10
        )
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return

    # pasek postępu
    pw = PasekPostepu(iface)
    pasek = pw.stworz_pasek(f'Kontrola opisów ({len(kontrole)} kontroli)…')

    try:
        _wykonaj_kontrole(baza_upul, kontrole, pasek)
    finally:
        baza_upul.zamknij()
        shutil.rmtree(tmp_dir, ignore_errors=True)
        pw.clear()

    # raport
    rap_sc = _zapisz_raport(kontrole, baza_sc, baza_kontroli_sc, czas)

    ile_err  = sum(1 for k in kontrole if k.is_error)
    ile_wier = sum(len(k.errors) for k in kontrole)

    poziom = Qgis.Success if ile_err == 0 else Qgis.Warning
    iface.messageBar().pushMessage(
        'Kontrola opisów',
        f'Kontroli z błędami: {ile_err}, błędnych wierszy: {ile_wier}. '
        f'Raport: {rap_sc}',
        poziom, 10
    )

    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle('Kontrola opisów taksacyjnych')
    msg.setText(
        f'Kontrola zakończona.\n'
        f'Kontroli z błędami: {ile_err}\n'
        f'Błędnych wierszy: {ile_wier}\n\n'
        f'Pokazać raport?'
    )
    msg.addButton('Nie', QMessageBox.ActionRole)
    msg.addButton('Tak', QMessageBox.ActionRole)
    if msg.exec_() == 1 and platform.system()[:3] == 'Win':
        os.startfile(rap_sc)
